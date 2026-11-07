"""Word-level transcript of the voice track with faster-whisper -> data/whisper_words.json."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUDIO = HERE.parent / "audio" / "qaybo_5min" / "qayb_00.mp3"
OUT = HERE / "data" / "whisper_words.json"
SR = 16000


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def main():
    from faster_whisper import WhisperModel  # heavy; only needed here, other scripts import AUDIO

    model = WhisperModel(sys.argv[1] if len(sys.argv) > 1 else "medium.en", device="cpu", compute_type="int8")
    # No VAD and no conditioning on earlier text: short replies ("Really? Even you?") must not be dropped.
    segments, info = model.transcribe(load_audio(AUDIO), beam_size=5, word_timestamps=True, vad_filter=False,
                                      condition_on_previous_text=False,
                                      initial_prompt="Enjoy English Talks, a podcast with Bella and Aaron.")
    words = []
    for seg in segments:
        print(f"[{seg.start:7.2f}-{seg.end:7.2f}] {seg.text.strip()}", flush=True)
        words += [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)}
                  for w in seg.words if w.word.strip()]
    OUT.write_text(json.dumps({"duration": info.duration, "words": words}, indent=1))
    print("wrote", OUT, len(words), "words")


if __name__ == "__main__":
    main()
