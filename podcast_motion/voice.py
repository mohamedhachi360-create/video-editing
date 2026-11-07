"""Decoding the voice: one part's audio, and the full voice track of a video (recap + part)."""
import subprocess

import numpy as np

from config import AUDIO_END, CUTS, INTRO, MASTER, PART, RECAP, VOICE_START, audio_file

SLICE = 300.0  # the part files are consecutive 5-minute slices of MASTER


def decode(path, sr, channels=1, start=None, duration=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(start)] if start is not None else []) + ["-i", str(path)]
    cmd += (["-t", str(duration)] if duration is not None else []) + ["-ac", str(channels), "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels).copy()


def part_audio(part, sr, channels=1, end=None, lookahead=0.0):
    """Part audio at `sr`, cut at `end` seconds or extended `lookahead` seconds past its file.

    Audio past the end of the file comes from MASTER, aligned on the file's last second: the part
    files skip ~12 ms at each split, so joining two part files would click.
    """
    a = decode(audio_file(part), sr, channels)
    stop = round(end * sr) if end is not None else len(a) + round(lookahead * sr)
    if stop <= len(a):
        return a[:stop]
    window = decode(MASTER, sr, channels, start=part * SLICE - 6, duration=(stop - len(a)) / sr + 12)
    probe, ref = a[-sr:].mean(1), window.mean(1)[:10 * sr]
    n = len(ref) + len(probe)
    cc = np.fft.irfft(np.fft.rfft(ref, n) * np.conj(np.fft.rfft(probe, n)), n)
    k = int(np.argmax(cc[:len(ref) - len(probe)]))
    return np.concatenate([a, window[k + len(probe):]])[:stop]


def fade(x, sr, seconds):
    n = min(len(x) // 2, round(seconds * sr))
    ramp = np.linspace(0, 1, n, dtype=np.float32)[:, None]
    x[:n] *= ramp
    x[-n:] *= ramp[::-1]
    return x


def cut_time(t):
    """Seconds in the part's audio -> seconds after CUTS are removed."""
    return t - sum(min(b, max(a, t)) - a for a, b in CUTS)


def apply_cuts(x, sr):
    if not CUTS:
        return x
    edges = [0] + [round(v * sr) for cut in CUTS for v in cut] + [len(x)]
    return np.concatenate([fade(x[a:b].copy(), sr, 0.01) for a, b in zip(edges[::2], edges[1::2])])


def voice_track(sr, channels, total):
    """The voice as heard in the video, `total` samples long."""
    out = np.zeros((total, channels), np.float32)

    def put(x, t):
        i = round(t * sr)
        n = max(0, min(len(x), total - i))
        out[i:i + n] += x[:n]

    if RECAP:
        a, b = RECAP
        put(fade(part_audio(PART - 1, sr, channels)[round(a * sr):round(b * sr)], sr, 0.02), INTRO)
    main = apply_cuts(part_audio(PART, sr, channels, end=AUDIO_END), sr)
    put(fade(main, sr, 0.03) if AUDIO_END is not None else main, VOICE_START)
    return out
