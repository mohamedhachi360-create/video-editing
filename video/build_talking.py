#!/usr/bin/env python3
"""Talking-cartoon video: original audio, untouched, drives a mouth on the still."""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path("/tmp/hoplite/workspace")
SRC_IMG = ROOT / ".hoplite/attachments/art_upload_10a02df5d9cc4672bf548e558ccee3c8/Warm Podcast Studio Conversation.png"
SRC_AUDIO = ROOT / ".hoplite/attachments/art_upload_01ad52db4d3a4b5b8e73a35d0490b145/audio_qaybo_5min_qayb_00 (1).mp3"
OUT = ROOT / "video/qayb_00_cartoon_hadlaya.mp4"
FPS = 24

# Mouth box measured from the source image.
Y0, Y1, X0, X1 = 274, 346, 346, 454


def load():
    return np.array(Image.open(SRC_IMG)).astype(np.float32)


def mouth_mask(src):
    ref = src[250, X0:X1]
    roi = src[Y0:Y1, X0:X1]
    delta = np.abs(roi - ref[None]).sum(2)
    m = ((delta > 42) & (np.arange(X0, X1)[None] < 446)).astype(np.uint8)
    acc = m.copy()
    rad = 14
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            if dy * dy + dx * dx > rad * rad:
                continue
            acc = np.maximum(acc, np.roll(np.roll(m, dy, 0), dx, 1))
    mask = np.array(
        Image.fromarray((acc * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2.2))
    ).astype(np.float32) / 255.0
    mask *= (np.arange(X0, X1)[None] < 445)
    return mask


def cheek_fill(src, mask):
    ref = src[250, X0:X1]
    blur = np.array(Image.fromarray(src.astype(np.uint8)).filter(ImageFilter.BoxBlur(16))).astype(np.float32)
    ratio = blur[Y0:Y1, X0:X1].mean(2) / (blur[250, X0:X1].mean(1)[None] + 1e-3)
    fill = ref[None] * np.clip(ratio, 0.86, 1.08)[..., None]
    region = src[Y0:Y1, X0:X1]
    m = mask[..., None]
    patched = region * (1 - m) + fill * m
    # Keep the thin highlight stroke at the cheek edge; it is not part of the mouth.
    xs = np.arange(X0, X1)[None]
    white = (
        (region[:, :, 0] > 210)
        & (region[:, :, 1] > 200)
        & (region[:, :, 2] > 185)
        & (xs > 424)
        & (xs < 442)
    )
    patched = np.where(white[..., None], region, patched)
    return patched


def render_mouth(base_region, mask, openness):
    """openness 0 = closed line, 1 = fully open speaking mouth."""
    region = base_region.copy()
    h, w = region.shape[:2]
    yy = np.arange(h)[:, None]
    xs = np.arange(w)[None, :]
    cx = 400.0 - X0
    nx = (xs - cx) / 46.0
    curve = (300.0 - Y0) + 5.0 * nx * nx
    dist = yy - curve
    # Closed lip thickness, then a dark gap that widens as she speaks.
    half = 2.4 + 2.2 * openness
    lip_a = np.clip(1.55 - np.abs(dist) / half, 0, 1)
    lip_a *= np.clip((1.0 - np.abs(nx)) / 0.14, 0, 1)
    lip_a = np.clip(lip_a, 0, 1) * (mask > 0.5)
    lip = np.array([146.0, 42.0, 34.0])
    shade = 1.04 + 0.1 * np.abs(nx) - 0.22 * np.clip(1.0 - np.abs(dist) / (half * 0.6), 0, 1)
    color = lip * shade[..., None]
    color += np.clip(1 - np.abs(dist + half * 0.5) / 1.2, 0, 1)[..., None] * np.array([36.0, 16.0, 8.0])
    gap_h = 0.6 + 6.5 * openness
    gap = np.clip(1 - np.abs(dist) / gap_h, 0, 1)
    gap *= np.clip((0.82 - np.abs(nx)) / 0.18, 0, 1)
    gap *= (mask > 0.6) * openness
    dark = np.array([48.0, 14.0, 14.0])
    color = color * (1 - gap[..., None]) + dark * gap[..., None]
    # A small tooth glint once the mouth is well open.
    tooth = (gap > 0.45) & (dist < -0.5) & (np.abs(nx) < 0.45)
    color = np.where(tooth[..., None], color * 0.3 + np.array([236.0, 230.0, 224.0]) * 0.7, color)
    a = np.clip(lip_a + gap * 0.6, 0, 1)
    region = region * (1 - a[..., None]) + color * a[..., None]
    return region


def envelope(audio_path, fps, n_frames):
    wav = "/tmp/verify/env.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path), "-ac", "1", "-ar", "16000", wav],
        check=True, capture_output=True,
    )
    with wave.open(wav) as w:
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        rate = w.getframerate()
    hop = rate / fps
    env = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        a = int(i * hop)
        b = int(min(len(samples), a + hop))
        if b > a:
            env[i] = np.sqrt(np.mean(samples[a:b] ** 2))
    # Smooth so the mouth doesn't chatter, then normalize speech vs silence.
    kernel = np.array([0.15, 0.7, 0.15])
    env = np.convolve(env, kernel, mode="same")
    noise = np.percentile(env, 20)
    peak = np.percentile(env, 96)
    env = np.clip((env - noise) / max(1.0, peak - noise), 0, 1)
    # Ease the curve so small sounds still move the mouth.
    return env ** 0.65


def main():
    src = load()
    mask = mouth_mask(src)
    base = cheek_fill(src, mask)
    duration = 300.016
    n = int(round(duration * FPS))
    print(f"frames: {n}", flush=True)
    env = envelope(SRC_AUDIO, FPS, n)

    # Pre-render a small set of mouth shapes and blend between neighbors.
    levels = np.linspace(0, 1, 9)
    shapes = [render_mouth(base, mask, float(v)) for v in levels]

    out_w, out_h = 1280, 720
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{out_w}x{out_h}", "-r", str(FPS),
        "-i", "-",
        "-i", str(SRC_AUDIO),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart",
        str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    frame = np.empty((out_h, out_w, 3), dtype=np.uint8)
    full = src.copy()
    for i, amp in enumerate(env):
        pos = amp * (len(levels) - 1)
        lo = int(np.floor(pos))
        hi = min(lo + 1, len(levels) - 1)
        t = pos - lo
        mouth = shapes[lo] * (1 - t) + shapes[hi] * t
        full[Y0:Y1, X0:X1] = mouth
        # A tiny head nod on louder syllables, kept subtle.
        shift = int(round(np.sin(i / 7.0) * amp * 1.5))
        img = np.roll(full, shift, axis=0) if shift else full
        small = np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((out_w, out_h), Image.BILINEAR))
        proc.stdin.write(small.tobytes())
        if i % (FPS * 30) == 0:
            print(f"{i}/{n}", flush=True)
    proc.stdin.close()
    err = proc.stderr.read().decode()
    code = proc.wait()
    if code != 0:
        print(err[-2000:], file=sys.stderr)
        sys.exit(code)
    print("done", OUT, flush=True)


if __name__ == "__main__":
    main()
