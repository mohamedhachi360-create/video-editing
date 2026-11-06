#!/usr/bin/env python3
"""Animate the supplied podcast illustration without re-encoding its audio."""

import argparse
import math
import subprocess
from pathlib import Path

import cv2
import librosa
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d, median_filter

FPS = 24
LEVELS = 33


def decode(path: Path, sample_rate: int, cache: Path) -> np.ndarray:
    raw = cache / f"audio_{sample_rate}.f32"
    if not raw.exists():
        subprocess.run([
            "ffmpeg", "-v", "error", "-i", str(path), "-ar", str(sample_rate),
            "-ac", "1", "-f", "f32le", str(raw), "-y",
        ], check=True)
    return np.fromfile(raw, dtype=np.float32)


def audio_activity(audio: Path, cache: Path) -> tuple[np.ndarray, np.ndarray]:
    analysis = cache / "activity.npz"
    if analysis.exists():
        data = np.load(analysis)
        return data["envelope"], data["female_share"]

    samples = decode(audio, 24000, cache)
    duration = len(samples) / 24000
    frame_count = math.ceil(duration * FPS)
    padded = np.pad(samples, (0, frame_count * 1000 - len(samples)))
    rms = np.sqrt(np.mean(padded.reshape(frame_count, 1000) ** 2, axis=1) + 1e-10)
    rms = gaussian_filter1d(rms, 0.65)
    speech = rms[rms > 0.015]
    reference = np.percentile(speech, 90) if len(speech) else 0.1
    envelope = np.clip((rms - 0.012) / max(reference - 0.012, 0.02), 0, 1) ** 0.65
    envelope = gaussian_filter1d(envelope, 0.45)

    pitch_samples = decode(audio, 16000, cache)
    f0, voiced, _ = librosa.pyin(
        pitch_samples, fmin=65, fmax=400, sr=16000,
        frame_length=2048, hop_length=512,
    )
    pitch_rms = librosa.feature.rms(
        y=pitch_samples, frame_length=2048, hop_length=512,
    )[0]
    good = voiced & (pitch_rms > 0.025) & np.isfinite(f0)
    if np.count_nonzero(good) < 20:
        female_share = np.ones(frame_count, dtype=np.float32)
    else:
        times = np.arange(len(f0), dtype=np.float32) * 512 / 16000
        filled = np.interp(times, times[good], f0[good])
        filled = median_filter(filled, size=11, mode="nearest")
        low, high = math.log2(150), math.log2(190)
        share = np.clip((np.log2(np.maximum(filled, 1)) - low) / (high - low), 0, 1)
        share = gaussian_filter1d(share, 4.0)
        frame_times = np.arange(frame_count, dtype=np.float32) / FPS
        female_share = np.interp(frame_times, times, share).astype(np.float32)

    np.savez(analysis, envelope=envelope, female_share=female_share)
    print(f"Audio: {duration:.2f}s, {frame_count} frames; "
          f"female-led {np.mean(female_share > .5) * 100:.0f}%", flush=True)
    return envelope, female_share


def female_sprite(base: np.ndarray, opening: float) -> np.ndarray:
    x0, y0, x1, y1 = 330, 265, 450, 350
    roi = base[y0:y1, x0:x1].copy()
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    lower = 1 / (1 + np.exp(-(yy - 290) / 3.0))
    weight = lower * np.exp(-((xx - 390) / 50) ** 4 - ((yy - 307) / 37) ** 2)
    displacement = (opening * 22 - 14) * weight
    map_x = xx - x0
    map_y = yy - y0 - displacement
    return cv2.remap(roi, map_x.astype(np.float32), map_y.astype(np.float32),
                     cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def male_sprite(base: np.ndarray, opening: float) -> np.ndarray:
    x0, y0, x1, y1 = 1265, 270, 1380, 340
    roi = base[y0:y1, x0:x1].copy()
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    mouth_line = 296 + 0.16 * (xx - 1323)
    lower = 1 / (1 + np.exp(-(yy - mouth_line) / 2.5))
    weight = lower * np.exp(-((xx - 1323) / 45) ** 4 - ((yy - 307) / 27) ** 2)
    map_y = yy - y0 - opening * 7 * weight
    roi = cv2.remap(roi, (xx - x0).astype(np.float32), map_y.astype(np.float32),
                    cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if opening < 0.06:
        return roi

    scale = 4
    canvas = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    t = np.linspace(0, 1, 41)
    x = 1288 + 72 * t
    top = 285 + 12 * t + 11 * np.sin(np.pi * t)
    depth = 15 * opening * np.sin(np.pi * t) ** 0.8
    bottom = top + depth

    def points(xs, ys):
        return np.round(np.column_stack(((xs - x0) * scale, (ys - y0) * scale))).astype(np.int32)

    outline = np.concatenate((points(x, top), points(x[::-1], bottom[::-1])))
    cv2.fillPoly(canvas, [outline], (25, 18, 45), lineType=cv2.LINE_AA)
    if opening > 0.16:
        tooth_depth = np.minimum(4.2, 5 * opening) * np.sin(np.pi * t) ** 0.45
        teeth = np.concatenate((points(x, top + .6), points(x[::-1], (top + .6 + tooth_depth)[::-1])))
        cv2.fillPoly(canvas, [teeth], (215, 225, 235), lineType=cv2.LINE_AA)
    lip = points(x[3:-3], (bottom + 1.2)[3:-3])
    cv2.polylines(canvas, [lip], False, (55, 73, 185),
                  thickness=max(1, round(scale * 1.5)), lineType=cv2.LINE_AA)
    return cv2.resize(canvas, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA)


def make_sprites(base: np.ndarray):
    female = [female_sprite(base, i / (LEVELS - 1)) for i in range(LEVELS)]
    male = [male_sprite(base, i / (LEVELS - 1)) for i in range(LEVELS)]
    return female, male


def composite(base, sprites, female_open, male_open):
    frame = base.copy()
    female, male = sprites
    fi = int(np.clip(round(female_open * (LEVELS - 1)), 0, LEVELS - 1))
    mi = int(np.clip(round(male_open * (LEVELS - 1)), 0, LEVELS - 1))
    frame[265:350, 330:450] = female[fi]
    frame[270:340, 1265:1380] = male[mi]
    return frame


def save_preview(base, sprites, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (900, 600), "white")
    draw = ImageDraw.Draw(sheet)
    boxes = [(330, 265, 450, 350), (1265, 270, 1380, 340)]
    for row, opening in enumerate((0.0, 0.5, 1.0)):
        frame = composite(base, sprites, opening, opening)
        for col, box in enumerate(boxes):
            crop = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).crop(box)
            crop = crop.resize((360, 170))
            sheet.paste(crop, (col * 450 + 40, row * 200 + 25))
            draw.text((col * 450 + 40, row * 200 + 5),
                      f"{'Female' if col == 0 else 'Male'} - {opening:.1f}", fill="black")
    sheet.save(path)


def render(audio: Path, output: Path, base, sprites, envelope, female_share, limit=None):
    output.parent.mkdir(parents=True, exist_ok=True)
    count = len(envelope) if limit is None else min(len(envelope), round(limit * FPS))
    command = [
        "ffmpeg", "-v", "warning", "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{base.shape[1]}x{base.shape[0]}", "-r", str(FPS), "-i", "-",
        "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
        "-vf", "crop=1672:940:0:0", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "18", "-tune", "animation", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart",
    ]
    if limit is not None:
        command += ["-t", str(limit)]
    command += [str(output), "-y"]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for i in range(count):
            energy = float(envelope[i])
            share = float(female_share[i])
            # The quieter character keeps a small amount of natural mouth movement.
            female_open = energy * (0.12 + 0.88 * share)
            male_open = energy * (0.12 + 0.88 * (1 - share))
            frame = composite(base, sprites, female_open, male_open)
            process.stdin.write(frame.tobytes())
            if i % (FPS * 30) == 0:
                print(f"Rendered {i / FPS:.0f}s / {count / FPS:.0f}s", flush=True)
    finally:
        if process.stdin:
            process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("/tmp/cartoon_lipsync"))
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--limit", type=float)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    base = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if base is None or base.shape[:2] != (941, 1672):
        raise ValueError("Expected the original 1672x941 illustration")
    sprites = make_sprites(base)
    if args.preview:
        save_preview(base, sprites, args.output)
        return
    envelope, female_share = audio_activity(args.audio, args.cache)
    render(args.audio, args.output, base, sprites, envelope, female_share, args.limit)


if __name__ == "__main__":
    main()
