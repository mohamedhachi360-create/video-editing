"""The word-level transcript: cue lookups, speaker turns and caption chunks."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from gfx import font

HERE = Path(__file__).resolve().parent
WORDS = json.loads((HERE / "data" / "words.json").read_text())
VOICE_END = max(w["e"] for w in WORDS)


def norm(text):
    return re.sub(r"[^a-z0-9']", "", text.lower().replace("’", "'"))


def spoken(text, after=0.0, end=False):
    """Start time of each word of `text` where it is next spoken after `after` (or its end time)."""
    target = [norm(x) for x in text.split()]
    for i, w in enumerate(WORDS):
        if w["s"] < after - 1e-6:
            continue
        if all(i + k < len(WORDS) and norm(WORDS[i + k]["w"]) == tok for k, tok in enumerate(target)):
            if w["s"] - after > 15:
                break
            times = [WORDS[i + k]["e" if end else "s"] for k in range(len(target))]
            for k in range(1, len(times)):  # keep cues strictly increasing
                times[k] = max(times[k], times[k - 1] + 0.08)
            return times
    raise ValueError(f"{text!r} is not spoken within 15 s after {after}")


def cue(text, after=0.0):
    return spoken(text, after)[0]


def cue_end(text, after=0.0):
    return spoken(text, after, end=True)[-1]


@dataclass
class Turn:
    spk: str
    start: float
    end: float


TURNS = []
for w in WORDS:
    if TURNS and TURNS[-1].spk == w["spk"]:
        TURNS[-1].end = w["e"]
    else:
        TURNS.append(Turn(w["spk"], w["s"], w["e"]))


def speaker_levels(t, lead=0.15, fade=0.3):
    """How 'active' each host is at time t (0..1); crossfades as the turn changes."""
    k = 0
    while k + 1 < len(TURNS) and TURNS[k + 1].start - lead <= t:
        k += 1
    cur = TURNS[k].spk
    p = 1.0 if k == 0 else min(1.0, max(0.0, (t - (TURNS[k].start - lead)) / fade))
    prev = TURNS[k - 1].spk if k else cur
    levels = {"bella": 0.0, "aaron": 0.0}
    levels[cur] += p
    levels[prev] += 1 - p
    return levels, cur


def speaking(t, spk):
    """True while `spk` is inside a word (with a little slack)."""
    for w in WORDS:
        if w["s"] - 0.06 <= t <= w["e"] + 0.08:
            return w["spk"] == spk
        if w["s"] > t + 0.1:
            break
    return False


# ---------- captions ----------

CAPTION_SIZE = 44
CAPTION_WEIGHT = "SemiBold"
CAPTION_MAX_W = 1060


@dataclass
class Chunk:
    spk: str
    words: list = field(default_factory=list)
    lines: list = field(default_factory=list)  # list of lists of word indices into WORDS

    @property
    def start(self):
        return WORDS[self.words[0]]["s"]

    @property
    def end(self):
        return WORDS[self.words[-1]]["e"]


def _layout(indices):
    """Split a chunk into at most two lines, preferring a break after punctuation."""
    f = font(CAPTION_WEIGHT, CAPTION_SIZE)
    text = [WORDS[i]["w"] for i in indices]
    if f.getlength(" ".join(text)) <= CAPTION_MAX_W:
        return [list(indices)]
    best = None
    for k in range(1, len(indices)):
        w1, w2 = f.getlength(" ".join(text[:k])), f.getlength(" ".join(text[k:]))
        if max(w1, w2) > CAPTION_MAX_W:
            continue
        score = max(w1, w2) + (0 if text[k - 1].endswith((",", ".", "?", "!")) else 300)
        if best is None or score < best[0]:
            best = (score, k)
    if best is None:
        return None
    return [list(indices[:best[1]]), list(indices[best[1]:])]


def build_chunks():
    chunks, cur = [], []

    def flush():
        if cur:
            c = Chunk(WORDS[cur[0]]["spk"], list(cur))
            c.lines = _layout(cur)
            chunks.append(c)
            cur.clear()

    for i, w in enumerate(WORDS):
        if cur:
            prev = WORDS[cur[-1]]
            gap = w["s"] - prev["e"]
            sentence_end = prev["w"].endswith((".", "?", "!"))
            dur = prev["e"] - WORDS[cur[0]]["s"]
            if (w["spk"] != prev["spk"] or gap > 0.7
                    or (sentence_end and (dur > 1.6 or gap > 0.3))
                    or (prev["w"].endswith(",") and dur > 2.6 and gap > 0.15)):
                flush()
            elif _layout(cur + [i]) is None:
                # too long for two lines: end the chunk at its last comma if there is one
                cut = max((j for j in range(2, len(cur) - 1) if WORDS[cur[j]]["w"].endswith(",")), default=None)
                if cut is None:
                    flush()
                else:
                    rest = cur[cut + 1:]
                    del cur[cut + 1:]
                    flush()
                    cur.extend(rest)
        cur.append(i)
    flush()
    return chunks


CHUNKS = build_chunks()
