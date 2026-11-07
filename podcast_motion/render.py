"""Render the motion-graphics video for the podcast clip (1920x1080, 30 fps).

  python render.py --stills    contact sheet of key moments -> build/contact_sheet.png
  python render.py             full video with audio -> output/enjoy_english_talks_part1.mp4
"""
import argparse
import math
import os
import subprocess
import sys
import time
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from gfx import (CYAN, FPS, GOLD, H, HOST_COLOR, HOST_NAME, INK, LANCZOS, W, WHITE, bubble, clamp01,
                 ease_in_out, ease_out_back, ease_out_cubic, emoji, lerp, panel, pill, place, portrait,
                 rounded_mask, scale_mask, smoothstep, solid, text_sprite, text_width)
from scenes import SCX, SCY, SX0, SX1, SY0, SY1
from storyboard import CHAPTERS, END, HOST_APPEAR, SCENES
from timeline import CAPTION_SIZE, CAPTION_WEIGHT, CHUNKS, VOICE_END, WORDS, speaker_levels, speaking
from transcribe import AUDIO

HERE = Path(__file__).resolve().parent
BUILD, OUTPUT = HERE / "build", HERE / "output"
OUT_FILE = OUTPUT / "enjoy_english_talks_part1.mp4"
N_FRAMES = round(END * FPS)

# ---------- background ----------

BG_STOPS = ((0.0, (3, 9, 36)), (0.5, (10, 40, 128)), (1.0, (32, 104, 236)))
LW, LH = 384, 216
_Y, _X = np.mgrid[0:LH, 0:LW].astype(np.float32) + 0.5
_X *= W / LW
_Y *= H / LH
_STOPS = [(p, np.array(c, np.float32) / 255) for p, c in BG_STOPS]
_V = np.sqrt((_X / W - 0.5) ** 2 + ((_Y / H - 0.5) * 0.85) ** 2)
_VIG = (1 - 0.42 * np.clip((_V - 0.28) / 0.5, 0, 1) ** 1.5)[..., None]
_DITHER = (np.random.default_rng(5).random((H, W, 3), dtype=np.float32) - 0.5) * 1.2
_LIGHT = np.array((90, 185, 255), np.float32) / 255
LIGHTS = ((0.8, 0.16, 0.07, 0.05, 0.28, 0.42, 0.0), (0.14, 0.86, 0.06, 0.05, 0.24, 0.2, 2.0))


def background(t):
    ph = 2 * math.pi * t / 40.0
    ang = math.radians(28 + 6 * math.sin(ph))
    dx, dy = math.cos(ang), -math.sin(ang)
    half = 0.5 * (W * abs(dx) + H * abs(dy))
    g = np.clip(((_X - W / 2) * dx + (_Y - H / 2) * dy) / half * 0.5 + 0.5, 0, 1)
    g = g * g * (3 - 2 * g)
    (p0, c0), (p1, c1), (p2, c2) = _STOPS
    rgb = c0 + (c1 - c0) * np.clip((g - p0) / (p1 - p0), 0, 1)[..., None] \
        + (c2 - c1) * np.clip((g - p1) / (p2 - p1), 0, 1)[..., None]
    for x, y, ax, ay, r, s, p in LIGHTS:
        lx, ly = (x + ax * math.sin(ph + p)) * W, (y + ay * math.cos(ph + p)) * H
        k = s * np.exp(-((_X - lx) ** 2 + (_Y - ly) ** 2) / (2 * (r * W) ** 2))
        rgb = 1 - (1 - rgb) * (1 - k[..., None] * _LIGHT)
    rgb = (rgb * _VIG * 255).astype(np.float32)
    full = np.stack([np.asarray(Image.fromarray(rgb[..., c], "F").resize((W, H), Image.Resampling.BILINEAR))
                     for c in range(3)], -1)
    return Image.fromarray(np.clip(full + _DITHER + 0.5, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


_rng = np.random.default_rng(11)
NP = 46
_PX, _PY = _rng.uniform(0, W, NP), _rng.uniform(0, H, NP)
_PVX, _PVY = _rng.uniform(-5, 5, NP), _rng.uniform(8, 24, NP)
_PR = _rng.choice([2, 3, 4], NP)
_PA, _PF, _PPH = _rng.uniform(0.15, 0.5, NP), _rng.uniform(0.2, 0.7, NP), _rng.uniform(0, 6.28, NP)


@lru_cache(maxsize=8)
def dot(r):
    s = 8 * r + 8
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((s / 2 - 2.6 * r, s / 2 - 2.6 * r, s / 2 + 2.6 * r, s / 2 + 2.6 * r), fill=44)
    d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=255)
    return solid((215, 235, 255), m.filter(ImageFilter.GaussianBlur(1.2)))


def particles(fr, t):
    for k in range(NP):
        a = _PA[k] * (0.55 + 0.45 * math.sin(2 * math.pi * _PF[k] * t + _PPH[k]))
        place(fr, dot(int(_PR[k])), (_PX[k] + _PVX[k] * t) % W, (_PY[k] - _PVY[k] * t) % H, 1, 0, a)


# ---------- stage board, top bar, chapter wipes ----------

@lru_cache(maxsize=1)
def board():
    return panel(SX1 - SX0, SY1 - SY0, 40, WHITE, 0.055, WHITE, 0.17, 2, 0.3, 0.6)


@lru_cache(maxsize=1)
def board_mask():
    m = Image.new("L", (W, H), 0)
    m.paste(rounded_mask(SX1 - SX0, SY1 - SY0, 40), (SX0, SY0))
    return m


def draw_board(fr, t):
    k = smoothstep(0, 0.7, t)
    place(fr, board(), SCX, SCY, 1 if k >= 1 else 0.97 + 0.03 * ease_out_cubic(k), 0, k)


def chapter_at(t):
    return max(i for i, (c, _) in enumerate(CHAPTERS) if c - 0.05 <= t or i == 0)


def chapter_pill(i):
    return pill(f"{i + 1:02d}  ·  {CHAPTERS[i][1]}", 24, WHITE, CYAN, 0.2, 0.6, False)


def draw_topbar(fr, t):
    k = ease_out_cubic(smoothstep(0.1, 0.8, t))
    dy = -40 * (1 - k)
    place(fr, emoji("headphone", 44, 0.3), 112, 60 + dy, 1 if k >= 1 else 1.0, 0, k)
    logo = text_sprite("Enjoy English Talks", 30, "Bold")
    place(fr, logo, 146 + logo.width / 2 - 14, 61 + dy, 1, 0, k)
    i = chapter_at(t)
    tc = CHAPTERS[i][0]
    p = smoothstep(tc, tc + 0.45, t) if i else 1.0
    new = chapter_pill(i)
    place(fr, new, SX1 - new.width / 2 + 28, 60 + dy + 26 * (1 - p), 1, 0, k * p)
    if i and p < 1:
        old = chapter_pill(i - 1)
        place(fr, old, SX1 - old.width / 2 + 28, 60 + dy - 26 * p, 1, 0, k * (1 - p))
    # progress bar with chapter ticks
    bar = Image.new("RGBA", (W, 6), (255, 255, 255, 30))
    fill = round(W * min(1, t / VOICE_END))
    if fill:
        grad = np.linspace(0, 1, fill, dtype=np.float32)[None, :, None]
        rgb = np.array(CYAN, np.float32) * (1 - grad) + np.array(GOLD, np.float32) * grad
        bar.paste(Image.fromarray(np.repeat(rgb, 6, 0).astype(np.uint8), "RGB"), (0, 0))
    for c, _ in CHAPTERS[1:]:
        x = round(W * c / VOICE_END)
        bar.paste((255, 255, 255, 200), (x - 1, 0, x + 2, 6))
    fr.alpha_composite(bar, (0, 0))


def draw_wipe(fr, t):
    for i, (tc, title) in enumerate(CHAPTERS):
        u = (t - (tc - 0.45)) / 0.95
        if i == 0 or not 0 <= u <= 1:
            continue
        cx = lerp(SX0 - 700, SX1 + 700, ease_in_out(u))
        half, skew = 560, 150
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([(cx - half + skew, SY0), (cx + half + skew, SY0), (cx + half - skew, SY1),
                                   (cx - half - skew, SY1)], fill=255)
        m = ImageChops.multiply(m, board_mask())
        xs = np.clip((np.arange(W, dtype=np.float32) - (cx - half - skew)) / (2 * (half + skew)), 0, 1)
        rgb = np.array((40, 150, 255), np.float32) * (1 - xs[:, None]) + np.array((90, 220, 255), np.float32) * xs[:, None]
        band = Image.fromarray(np.repeat(rgb[None].astype(np.uint8), H, 0), "RGB").convert("RGBA")
        band.putalpha(scale_mask(m, 0.97))
        num = text_sprite(f"{i + 1:02d}", 150, "Bold", WHITE, 0.3, 0)
        ttl = text_sprite(title, 66, "Bold", WHITE, 1.0, 0.35)
        band.alpha_composite(num, (round(cx - num.width / 2), round(SCY - 70 - num.height / 2)))
        band.alpha_composite(ttl, (round(cx - ttl.width / 2), round(SCY + 52 - ttl.height / 2)))
        band.putalpha(ImageChops.multiply(band.getchannel("A"), scale_mask(m, 1.0).point(lambda v: 255 if v else 0)))
        fr.alpha_composite(band)


# ---------- hosts ----------

AV_POS = {"bella": (214, 886), "aaron": (1706, 886)}
AV_D = 196
VOICE_FEATURES = BUILD / "voice_features.npz"


def voice_features():
    """Per-frame loudness and 24 spectrum bands of the voice, for the speaking rings."""
    if VOICE_FEATURES.exists() and VOICE_FEATURES.stat().st_mtime > AUDIO.stat().st_mtime:
        d = np.load(VOICE_FEATURES)
        return d["bands"], d["rms"]
    sr, hop, win = 48000, 1600, 4096
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(AUDIO), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    y = np.pad(np.frombuffer(raw, np.float32), (win, win + N_FRAMES * hop))
    idx = np.arange(N_FRAMES)[:, None] * hop + win + hop // 2 - win // 2 + np.arange(win)[None, :]
    frames = y[idx]
    spec = np.abs(np.fft.rfft(frames * np.hanning(win), axis=1))
    freqs = np.fft.rfftfreq(win, 1 / sr)
    edges = np.geomspace(90, 6000, 25)
    bands = np.stack([spec[:, (freqs >= a) & (freqs < b)].mean(1) for a, b in zip(edges[:-1], edges[1:])], 1)
    bands = np.log10(bands + 1e-7)
    lo, hi = np.percentile(bands, 30, axis=0), np.percentile(bands, 99, axis=0)
    bands = np.clip((bands - lo) / (hi - lo), 0, 1)
    rms = np.sqrt((frames[:, win // 2 - hop // 2: win // 2 + hop // 2] ** 2).mean(1))
    rms = np.clip(rms / np.percentile(rms[rms > 1e-4], 95), 0, 1)
    for n in range(1, N_FRAMES):  # fast attack, slower release
        bands[n] = np.maximum(bands[n], bands[n - 1] * 0.72)
        rms[n] = max(rms[n], rms[n - 1] * 0.8)
    BUILD.mkdir(exist_ok=True)
    np.savez(VOICE_FEATURES, bands=bands.astype(np.float32), rms=rms.astype(np.float32))
    return bands, rms


BANDS, RMS = voice_features()


def draw_bars(fr, x, y, sc, color, values, level):
    r = (AV_D / 2 + 8) * sc
    size = int(2 * (r + 64))
    ss, n = 2, 48
    m = Image.new("L", (size * ss, size * ss), 0)
    d = ImageDraw.Draw(m)
    c = size * ss / 2
    for k in range(n):
        ang = 2 * math.pi * k / n - math.pi / 2
        v = values[k if k < n // 2 else n - 1 - k]
        r0, r1 = (r + 6) * ss, (r + 6 + 6 + 44 * v) * ss
        d.line((c + r0 * math.cos(ang), c + r0 * math.sin(ang), c + r1 * math.cos(ang), c + r1 * math.sin(ang)),
               fill=255, width=6 * ss)
    m = m.resize((size, size), LANCZOS)
    place(fr, solid(color, scale_mask(m, 0.85 * level)), x, y)


def draw_hosts(fr, t, n):
    levels, cur = speaker_levels(t)
    if t > VOICE_END + 0.3:
        levels = {k: v * (1 - smoothstep(VOICE_END + 0.3, VOICE_END + 1.2, t)) for k, v in levels.items()}
    for name, (x, y) in AV_POS.items():
        p = clamp01((t - HOST_APPEAR[name]) / 0.55)
        if p <= 0:
            continue
        level = levels[name]
        talk = RMS[min(n, len(RMS) - 1)] if speaking(t, name) else 0.0
        sc = (0.84 + 0.16 * level) * ease_out_back(p, 1.7) * (1 + 0.025 * talk)
        bob = -5 * talk * level
        a = clamp01(p * 3)
        if level > 0.02 and p >= 1:
            draw_bars(fr, x, y + bob, sc, HOST_COLOR[name], BANDS[min(n, len(BANDS) - 1)] * (talk > 0.02), level)
        place(fr, portrait(name, AV_D, None, 6, 1.0), x, y + bob, sc, 0, a)
        if level > 0.01:
            place(fr, portrait(name, AV_D, HOST_COLOR[name], 6), x, y + bob, sc, 0, a * level)
        tag_off = pill(HOST_NAME[name], 22, WHITE, WHITE, 0.12, 0.35, True)
        tag_on = pill(HOST_NAME[name], 22, INK, HOST_COLOR[name], 0.96, 0.9, True)
        ty = y + AV_D / 2 * sc + 10
        place(fr, tag_off, x, ty, 1, 0, a * (1 - level))
        place(fr, tag_on, x, ty, 1, 0, a * level)


# ---------- captions ----------

CAP_CX, CAP_CY, CAP_W, CAP_H = SCX, 886, 1130, 172
LINE_H = 60


@lru_cache(maxsize=4)
def caption_panel(spk):
    return bubble(CAP_W, CAP_H, "left" if spk == "bella" else "right", (6, 14, 50), 0.74, 34, HOST_COLOR[spk], 0.9)


@lru_cache(maxsize=512)
def word_highlight(width, spk):
    return panel(width + 18, 58, 16, HOST_COLOR[spk], 0.22, HOST_COLOR[spk], 0.5, 2, 0, 0)


def chunk_window(i):
    c = CHUNKS[i]
    start = c.start - 0.15
    end = c.end + 1.0
    if i + 1 < len(CHUNKS):
        end = min(end, CHUNKS[i + 1].start - 0.15)
    return start, end


def draw_chunk(fr, i, t, alpha):
    c = CHUNKS[i]
    color = HOST_COLOR[c.spk]
    rise = 10 * (1 - ease_out_cubic(smoothstep(c.start - 0.15, c.start + 0.1, t)))
    y0 = CAP_CY - (len(c.lines) - 1) * LINE_H / 2 + rise
    for li, line in enumerate(c.lines):
        texts = [WORDS[k]["w"] for k in line]
        widths = [text_width(w, CAPTION_SIZE, CAPTION_WEIGHT) for w in texts]
        space = text_width(" ", CAPTION_SIZE, CAPTION_WEIGHT)
        x = CAP_CX - (sum(widths) + space * (len(widths) - 1)) / 2
        for k, w, wd in zip(line, texts, widths):
            # a word stays lit until the next one lights up (both shifted 0.04 s early)
            nxt = WORDS[k + 1]["s"] - 0.04 if k + 1 < len(WORDS) and k + 1 in c.words else WORDS[k]["e"] + 0.15
            s = WORDS[k]["s"] - 0.04
            cx, cy = x + wd / 2, y0 + li * LINE_H
            if s <= t < nxt:
                place(fr, word_highlight(round(wd), c.spk), cx, cy + 2, 1, 0, alpha)
                place(fr, text_sprite(w, CAPTION_SIZE, CAPTION_WEIGHT, color), cx, cy, 1, 0, alpha)
            elif t >= nxt:
                place(fr, text_sprite(w, CAPTION_SIZE, CAPTION_WEIGHT, WHITE), cx, cy, 1, 0, alpha)
            else:
                place(fr, text_sprite(w, CAPTION_SIZE, CAPTION_WEIGHT, WHITE, 0.5), cx, cy, 1, 0, alpha)
            x += wd + space


def draw_captions(fr, t):
    first = CHUNKS[0].start - 0.4
    k = smoothstep(first, first + 0.4, t) * (1 - smoothstep(VOICE_END + 0.4, VOICE_END + 1.0, t))
    if k <= 0:
        return
    levels, cur = speaker_levels(t)
    lv = levels["bella"] / max(1e-6, levels["bella"] + levels["aaron"])
    for spk, a in (("bella", lv), ("aaron", 1 - lv)):
        if a > 0.01:
            place(fr, caption_panel(spk), CAP_CX, CAP_CY, 1, 0, k * a)
    for i in range(len(CHUNKS)):
        start, end = chunk_window(i)
        if start <= t < end:
            a = smoothstep(start, start + 0.12, t) * (1 - smoothstep(end - 0.12, end, t))
            draw_chunk(fr, i, t, a * k)


# ---------- frames ----------

def compose(n):
    t = n / FPS
    fr = background(t)
    particles(fr, t)
    draw_board(fr, t)
    for scene in SCENES:
        scene.draw(fr, t)
    draw_wipe(fr, t)
    draw_topbar(fr, t)
    draw_hosts(fr, t, n)
    draw_captions(fr, t)
    rgb = fr.convert("RGB")
    fade = smoothstep(END - 0.7, END, t + 1 / FPS)
    if fade > 0:
        rgb = Image.blend(rgb, Image.new("RGB", rgb.size, (0, 0, 0)), fade)
    return rgb


def frame_bytes(n):
    return compose(n).tobytes()


def encode(path):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-tune", "animation",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           str(path)]
    t0 = time.time()
    with Pool(max(1, (os.cpu_count() or 2) - 2)) as pool, subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        for k, buf in enumerate(pool.imap(frame_bytes, range(N_FRAMES), chunksize=4)):
            proc.stdin.write(buf)
            if k % 600 == 0:
                print(f"  frame {k}/{N_FRAMES}  {time.time() - t0:.0f}s", flush=True)
        proc.stdin.close()
        if proc.wait():
            raise SystemExit("ffmpeg failed")


def contact_sheet(times, path, cols=4, thumb=(640, 360)):
    rows = math.ceil(len(times) / cols)
    sheet = Image.new("RGB", (cols * thumb[0], rows * (thumb[1] + 30)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    with Pool(max(1, (os.cpu_count() or 2) - 2)) as pool:
        frames = pool.map(compose, [round(t * FPS) for t in times])
    for k, (t, im) in enumerate(zip(times, frames)):
        x, y = (k % cols) * thumb[0], (k // cols) * (thumb[1] + 30)
        sheet.paste(im.resize(thumb, LANCZOS), (x, y + 30))
        d.text((x + 8, y + 8), f"{int(t // 60)}:{t % 60:05.2f}", fill=(235, 235, 235))
    sheet.save(path)
    print("wrote", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float, help="render these times (s) to build/contact_sheet.png")
    ap.add_argument("--frame", type=float, help="render one full-size frame to build/frame.png")
    args = ap.parse_args()
    BUILD.mkdir(exist_ok=True)
    if args.frame is not None:
        compose(round(args.frame * FPS)).save(BUILD / "frame.png")
        return
    if args.stills is not None:
        times = args.stills or [3.5, 10.5, 22.5, 24.35, 30.5, 41.0, 51.0, 63.5, 68.9, 77.8, 85.0, 98.9, 107.5, 113.6,
                                124.8, 127.9, 143.5, 166.0, 176.0, 186.0, 199.3, 211.6, 220.8, 227.9, 237.0, 243.8,
                                252.5, 265.6, 270.5, 277.2, 290.0, 299.0, 302.0]
        contact_sheet(times, BUILD / "contact_sheet.png")
        return
    OUTPUT.mkdir(exist_ok=True)
    video = BUILD / "video.mp4"
    print(f"rendering {N_FRAMES} frames")
    encode(video)
    subprocess.run([sys.executable, str(HERE / "mix.py")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(BUILD / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(OUT_FILE)], check=True)
    print("wrote", OUT_FILE.relative_to(HERE))


if __name__ == "__main__":
    main()
