"""Word-level transcript of a part with faster-whisper -> data/part<N>/whisper_words.json.

Run with PART=<n>. The audio runs 15 s past the end of the part's file, so a sentence cut by the
5-minute split can be finished (see config.AUDIO_END).
"""
import json
import sys

from config import DATA, PART
from voice import part_audio

SR = 16000
LOOKAHEAD = 15.0


def main():
    from faster_whisper import WhisperModel  # heavy; only needed here

    model = WhisperModel(sys.argv[1] if len(sys.argv) > 1 else "medium.en", device="cpu", compute_type="int8")
    audio = part_audio(PART, SR, lookahead=LOOKAHEAD if PART > 1 else 0.0)[:, 0]
    # No VAD and no conditioning on earlier text: short replies ("Really? Even you?") must not be dropped.
    segments, info = model.transcribe(audio, beam_size=5, word_timestamps=True, vad_filter=False,
                                      condition_on_previous_text=False,
                                      initial_prompt="Enjoy English Talks, a podcast with Bella and Aaron.")
    words = []
    for seg in segments:
        print(f"[{seg.start:7.2f}-{seg.end:7.2f}] {seg.text.strip()}", flush=True)
        words += [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)}
                  for w in seg.words if w.word.strip()]
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "whisper_words.json").write_text(json.dumps({"duration": info.duration, "words": words}, indent=1))
    print("wrote", DATA / "whisper_words.json", len(words), "words")


if __name__ == "__main__":
    main()
