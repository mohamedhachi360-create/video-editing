"""Mix the voice with the cued sound effects and a quiet music bed -> build/part<N>/mix.wav (48 kHz stereo).

The voice track is used as-is; music ducks under it and sound effects sit below it.
"""
from pathlib import Path

import numpy as np
import soundfile as sf

from config import BUILD
from storyboard import CHAPTERS, END, SCENES, SFX
from voice import decode, voice_track

HERE = Path(__file__).resolve().parent
AUDIO_DIR = HERE / "assets" / "audio"
OUT = BUILD / "mix.wav"
SR = 48000
MAX_LEN = {"ding_elevator": 1.6, "crickets": 1.7, "scratch": 0.9, "jingle": 2.0}  # seconds, faded out
MUSIC_DB, DUCK_DB = -31.0, -7.0  # bed level (RMS dBFS) and extra reduction while someone talks


def db(x):
    return 10 ** (x / 20)


def thud():
    """Soft low knock for the door closing."""
    t = np.arange(int(0.4 * SR)) / SR
    s = np.sin(2 * np.pi * (62 + 50 * np.exp(-t * 25)) * t) * np.exp(-t * 12)
    noise = np.convolve(np.random.default_rng(1).standard_normal(len(t)), np.ones(40) / 40, "same")
    s += 0.6 * noise * np.exp(-t * 45)
    return np.stack([s, s], 1).astype(np.float32)


def clip(name):
    s = thud() if name == "thud" else decode(AUDIO_DIR / f"{name}.mp3", SR, 2)
    env = np.abs(s).max(1)
    s = s[int(np.argmax(env > 0.02 * env.max())):]  # trim leading silence so the hit lands on the cue
    if name in MAX_LEN:
        s = s[:int(MAX_LEN[name] * SR)]
        n = min(len(s), int(0.4 * SR))
        s[-n:] *= np.linspace(1, 0, n, dtype=np.float32)[:, None]
    return s / max(1e-6, np.abs(s).max()) * db(-1)


def music_bed(total, voice):
    loop = decode(AUDIO_DIR / "music_chill_melody.mp3", SR, 2)
    xf = int(1.0 * SR)
    ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    bed = loop.copy()
    while len(bed) < total + xf:
        bed = np.concatenate([bed[:-xf], bed[-xf:] * (1 - ramp) + loop[:xf] * ramp, loop[xf:]])
    bed = bed[:total] * (db(MUSIC_DB) / np.sqrt(np.mean(loop ** 2)))
    # duck under the voice: 10 ms RMS envelope, fast attack, slow release
    hop = SR // 100
    v = np.zeros(total, np.float32)
    v[:len(voice)] = voice.mean(1)
    rms = np.sqrt(np.mean(v[:len(v) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    talk = (rms > 0.01).astype(np.float32)
    env = np.zeros_like(talk)
    for k in range(1, len(talk)):
        coef = 0.35 if talk[k] > env[k - 1] else 0.02
        env[k] = env[k - 1] + (talk[k] - env[k - 1]) * coef
    gain = db(DUCK_DB * np.interp(np.arange(total) / hop, np.arange(len(env)), env))
    t = np.arange(total) / SR
    gain *= np.clip(t / 2.0, 0, 1) * np.clip((END - t) / 3.5, 0, 1)
    return bed * gain[:, None].astype(np.float32)


def limit(x, thr=0.89):
    a = np.abs(x)
    over = a > thr
    x[over] = np.sign(x[over]) * (thr + (1 - thr) * np.tanh((a[over] - thr) / (1 - thr)))
    return x


def events():
    chapters = [c for c, _ in CHAPTERS[1:]]
    ev = list(SFX) + [("whoosh", c - 0.42, -11) for c in chapters]
    ev += [("whoosh_soft", s.start - 0.05, -22) for s in SCENES[1:]
           if min(abs(s.start - c) for c in chapters) > 0.6 and s.start < END - 4.5]
    return sorted(ev, key=lambda e: e[1])


def main():
    total = int(round(END * SR))
    voice = voice_track(SR, 2, total)
    out = voice + music_bed(total, voice)
    cache = {}
    for name, t, gain in events():
        if name not in cache:
            cache[name] = clip(name)
        s = cache[name] * db(gain)
        i = int(t * SR)
        n = min(len(s), total - i)
        out[i:i + n] += s[:n]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sf.write(OUT, limit(out), SR, subtype="PCM_16")
    print(f"wrote {OUT.relative_to(HERE)}: {total / SR:.1f} s, {len(events())} sound effects")


if __name__ == "__main__":
    main()
