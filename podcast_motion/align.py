"""Speaker labels and tighter word timings -> data/part<N>/words.json (run with PART=<n>).

The voice is split into phrases at pauses, each phrase gets a speaker embedding (wespeaker
ResNet34 via sherpa-onnx), and the phrases are clustered into Bella and Aaron. Pitch alone is not
enough here: Bella's falling sentence ends and Aaron's rising questions overlap in F0.
Word edges that whisper placed in silence are snapped to the speech envelope.
"""
import json
import re
import urllib.request
from pathlib import Path

import librosa
import numpy as np
import sherpa_onnx

from config import DATA, PART
from transcribe import LOOKAHEAD, SR
from voice import part_audio

HERE = Path(__file__).resolve().parent
MODEL = HERE / "build" / "models" / "wespeaker_en_voxceleb_resnet34_LM.onnx"
MODEL_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
             "wespeaker_en_voxceleb_resnet34_LM.onnx")
HOP = 160  # 10 ms at 16 kHz
MIN_GAP = 18  # frames of silence that end a phrase
# Times inside a phrase spoken by each host, per part; they seed the two speaker clusters.
ANCHORS = {1: {"bella": 3.0, "aaron": 27.0}, 2: {"bella": 2.0, "aaron": 12.0}}[PART]
TEXT_FIXES = {"Smalltalk,": ["small", "talk,"]}


def speech_mask(y):
    rms = librosa.feature.rms(y=y, frame_length=400, hop_length=HOP, center=True)[0]
    db = 20 * np.log10(rms + 1e-9)
    return db > np.percentile(db, 98) - 38


def phrases(speech):
    s = speech.copy()
    edges = np.flatnonzero(np.diff(np.r_[0, s.astype(int), 0]))
    starts, ends = edges[::2], edges[1::2]
    merged = []
    for a, b in zip(starts, ends):
        if merged and a - merged[-1][1] < MIN_GAP:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged if b - a >= 20]


def embeddings(y, regions):
    if not MODEL.exists():
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    ext = sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(MODEL), num_threads=8))
    out = []
    for a, b in regions:
        stream = ext.create_stream()
        stream.accept_waveform(sample_rate=SR, waveform=y[a * HOP:b * HOP].astype(np.float32))
        stream.input_finished()
        e = np.array(ext.compute(stream))
        out.append(e / np.linalg.norm(e))
    return np.array(out)


def label_regions(regions, emb):
    """2-means on the unit sphere seeded by the anchors; returns (labels, margins)."""
    def containing(t):
        return next(i for i, (a, b) in enumerate(regions) if a <= t * 100 < b)
    cb, ca = emb[containing(ANCHORS["bella"])], emb[containing(ANCHORS["aaron"])]
    weight = np.array([b - a for a, b in regions], float)[:, None]
    for _ in range(20):
        is_b = emb @ cb > emb @ ca
        cb = (emb[is_b] * weight[is_b]).sum(0)
        ca = (emb[~is_b] * weight[~is_b]).sum(0)
        cb, ca = cb / np.linalg.norm(cb), ca / np.linalg.norm(ca)
    margin = emb @ cb - emb @ ca
    labels = ["bella" if m > 0 else "aaron" for m in margin]
    # A weak phrase between two close phrases of the same speaker belongs to that speaker.
    for i in range(1, len(regions) - 1):
        close = regions[i][0] - regions[i - 1][1] < 40 and regions[i + 1][0] - regions[i][1] < 40
        if abs(margin[i]) < 0.1 and close and labels[i - 1] == labels[i + 1]:
            labels[i] = labels[i - 1]
    return labels, margin


def norm(text):
    return re.sub(r"[^a-z']", "", text.lower())


def clean_words(words):
    out = []
    for w in words:
        # whisper sometimes repeats the last word of a segment at the start of the next one
        if out and w["p"] < 0.1 and w["e"] - w["s"] < 0.1 and norm(w["w"]) == norm(out[-1]["w"]):
            continue
        parts = TEXT_FIXES.get(w["w"])
        if parts:
            step = (w["e"] - w["s"]) / len(parts)
            out += [dict(w, w=p, s=round(w["s"] + k * step, 3), e=round(w["s"] + (k + 1) * step, 3))
                    for k, p in enumerate(parts)]
        else:
            out.append(w)
    return out


def main():
    words = clean_words(json.loads((DATA / "whisper_words.json").read_text())["words"])
    y = part_audio(PART, SR, lookahead=LOOKAHEAD if PART > 1 else 0.0)[:, 0]
    speech = speech_mask(y)
    regions = phrases(speech)
    labels, margin = label_regions(regions, embeddings(y, regions))

    mids = np.array([(r[0] + r[1]) / 2 for r in regions])
    out = []
    for w in words:
        c = (w["s"] + w["e"]) * 50
        inside = [i for i, (a, b) in enumerate(regions) if a <= c < b]
        i = inside[0] if inside else int(np.argmin(np.abs(mids - c)))
        a, b = round(w["s"] * 100), round(w["e"] * 100)
        seg = speech[a:b]
        s, e = w["s"], w["e"]
        if seg.any():
            s = (a + int(np.argmax(seg))) / 100
            e = (a + len(seg) - int(np.argmax(seg[::-1]))) / 100
        spk = labels[i]
        if out and not out[-1]["w"].endswith((".", "?", "!")):
            spk = out[-1]["spk"]  # turns only change at the end of a sentence
        out.append({"w": w["w"], "s": round(s, 2), "e": round(e, 2), "spk": spk})
    (DATA / "words.json").write_text(
        "[\n" + ",\n".join(json.dumps(w) for w in out) + "\n]\n")

    print(f"{len(regions)} phrases, {len(out)} words; weakest margins:",
          ", ".join(f"{regions[i][0] / 100:.1f}s {margin[i]:+.2f}" for i in np.argsort(np.abs(margin))[:5]))
    turn = None
    for w in out:
        if w["spk"] != turn:
            print(f"\n{w['s']:7.2f} {w['spk'].upper():5}", end="")
            turn = w["spk"]
        print(" " + w["w"], end="")
    print()


if __name__ == "__main__":
    main()
