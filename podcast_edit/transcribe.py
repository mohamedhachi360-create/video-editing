import numpy as np
import json, sys
from faster_whisper import WhisperModel
m = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(np.fromfile("vo16k.f32", dtype=np.float32), word_timestamps=True, vad_filter=True, beam_size=1)
out = []
for s in segs:
    out.append({"start": s.start, "end": s.end, "text": s.text.strip(),
                "words": [{"w": w.word, "s": w.start, "e": w.end} for w in s.words]})
    print(f"{s.start:8.2f} {s.text.strip()}", flush=True)
json.dump(out, open("transcript.json", "w"), indent=1)
print("DONE", info.duration)
