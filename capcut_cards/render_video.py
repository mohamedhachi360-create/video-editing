"""Render the three-card motion graphic and the layers used by the CapCut project.

Outputs:
  output/three_cards_motion.mp4  final video (1920x1080, 30 fps, 7 s)
  output/preview.png             still with all three cards
  build/capcut_media/            background.mp4, card_1..3.png, cover.jpg for build_capcut_project.py

Usage: python render_video.py [--stills]   (--stills only writes build/contact_sheet.png)
"""
import argparse
import math
import os
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import motion as m

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
BUILD = HERE / "build"
MEDIA = BUILD / "capcut_media"
FONT = HERE / "fonts" / "Poppins-Bold.ttf"

LANCZOS = Image.Resampling.LANCZOS
BICUBIC = Image.Resampling.BICUBIC

SS = 2  # supersampling for the static sprites
PAD = 120  # room around a card for its shadow and glow
PW, PH = m.CARD_W + 2 * PAD, m.CARD_H + 2 * PAD

BG_STOPS = ((0.0, (2, 8, 34)), (0.55, (8, 44, 145)), (1.0, (35, 115, 255)))
LIGHT_RGB = (90, 185, 255)
# x, y, drift x, drift y, radius (fraction of width), strength, phase
LIGHTS = ((0.76, 0.2, 0.06, 0.05, 0.26, 0.5, 0.0), (0.18, 0.88, 0.05, 0.04, 0.22, 0.2, 1.9))
CARD_TINT = (225, 238, 255)
ACCENT = ((80, 214, 255), (88, 128, 255))


# ---------- image helpers ----------

def solid(rgb, alpha_mask):
    img = Image.new("RGBA", alpha_mask.size, tuple(rgb) + (0,))
    img.putalpha(alpha_mask)
    return img


def scale_mask(mask, k):
    return mask.point(lambda v: round(v * k))


def with_alpha(img, k):
    out = img.copy()
    out.putalpha(scale_mask(img.getchannel("A"), k))
    return out


def rounded(size, box, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, radius=radius, fill=255)
    return mask


def place(dst, src, cx, cy, scale, rotation, alpha=1.0):
    """Composite src onto dst with its centre at (cx, cy), scaled and rotated clockwise."""
    if scale < 1e-3 or alpha < 1e-3:
        return
    th = math.radians(rotation)
    c, s = math.cos(th), math.sin(th)
    hw, hh = src.width / 2, src.height / 2
    xs, ys = [], []
    for u, v in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
        xs.append(cx + scale * (c * u - s * v))
        ys.append(cy + scale * (s * u + c * v))
    x0, y0 = max(0, math.floor(min(xs))), max(0, math.floor(min(ys)))
    x1, y1 = min(dst.width, math.ceil(max(xs))), min(dst.height, math.ceil(max(ys)))
    if x1 <= x0 or y1 <= y0:
        return
    a, b, d, e = c / scale, s / scale, -s / scale, c / scale
    ox, oy = x0 - cx, y0 - cy
    region = src.transform((x1 - x0, y1 - y0), Image.Transform.AFFINE,
                           (a, b, hw + a * ox + b * oy, d, e, hh + d * ox + e * oy), resample=BICUBIC)
    if alpha < 0.999:
        region = with_alpha(region, alpha)
    dst.alpha_composite(region, dest=(x0, y0))


# ---------- background ----------

_YY, _XX = np.mgrid[0:m.H, 0:m.W].astype(np.float32) + 0.5
_STOPS = [(p, np.array(c, np.float32) / 255) for p, c in BG_STOPS]
_LIGHT = np.array(LIGHT_RGB, np.float32) / 255
_DITHER = (np.random.default_rng(3).random((m.H, m.W, 1), dtype=np.float32) - 0.5) * (1.5 / 255)
_v = np.sqrt((_XX / m.W - 0.5) ** 2 + ((_YY / m.H - 0.5) * 0.85) ** 2)
_VIGNETTE = (1 - 0.4 * np.clip((_v - 0.3) / 0.45, 0, 1) ** 1.5)[..., None]


def background(t):
    phase = 2 * math.pi * t / m.DURATION
    ang = math.radians(28 + 5 * math.sin(phase))
    dx, dy = math.cos(ang), -math.sin(ang)  # dark bottom-left -> bright top-right
    half = 0.5 * (m.W * abs(dx) + m.H * abs(dy))
    g = np.clip(((_XX - m.W / 2) * dx + (_YY - m.H / 2) * dy) / half * 0.5 + 0.5, 0, 1)
    g = g * g * (3 - 2 * g)
    (p0, c0), (p1, c1), (p2, c2) = _STOPS
    a = np.clip((g - p0) / (p1 - p0), 0, 1)[..., None]
    b = np.clip((g - p1) / (p2 - p1), 0, 1)[..., None]
    rgb = c0 + (c1 - c0) * a + (c2 - c1) * b
    for x, y, ax, ay, radius, strength, ph in LIGHTS:
        lx = (x + ax * math.sin(phase + ph)) * m.W
        ly = (y + ay * math.cos(phase + ph)) * m.H
        k = strength * np.exp(-((_XX - lx) ** 2 + (_YY - ly) ** 2) / (2 * (radius * m.W) ** 2))
        rgb = 1 - (1 - rgb) * (1 - k[..., None] * _LIGHT)
    return rgb * _VIGNETTE


_rng = np.random.default_rng(11)
_NP = 70
_PX, _PY = _rng.uniform(0, m.W, _NP), _rng.uniform(0, m.H, _NP)
_PVX, _PVY = _rng.uniform(-6, 6, _NP), _rng.uniform(10, 34, _NP)
_PR, _PA = _rng.uniform(1.2, 3.4, _NP), _rng.uniform(0.12, 0.5, _NP)
_PF, _PPH = _rng.uniform(0.25, 0.9, _NP), _rng.uniform(0, 2 * math.pi, _NP)


def particles(t):
    mask = Image.new("L", (m.W, m.H), 0)
    draw = ImageDraw.Draw(mask)
    for k in range(_NP):
        x = (_PX[k] + _PVX[k] * t) % m.W
        y = (_PY[k] - _PVY[k] * t) % m.H
        a = _PA[k] * (0.55 + 0.45 * math.sin(2 * math.pi * _PF[k] * t + _PPH[k]))
        r = _PR[k]
        draw.ellipse((x - 2.6 * r, y - 2.6 * r, x + 2.6 * r, y + 2.6 * r), fill=round(46 * a))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=round(255 * a))
    return solid((215, 235, 255), mask.filter(ImageFilter.GaussianBlur(1.2)))


# ---------- card sprites ----------

def _card_mask(size, scale, inset, radius):
    x0 = y0 = (PAD + inset) * scale
    x1 = (PAD + m.CARD_W - inset) * scale - 1
    y1 = (PAD + m.CARD_H - inset) * scale - 1
    return rounded(size, (x0, y0, x1, y1), radius * scale)


def build_card_sprites():
    big = (PW * SS, PH * SS)
    outer_big = _card_mask(big, SS, 0, m.CARD_RADIUS)
    inner_big = _card_mask(big, SS, 2, m.CARD_RADIUS - 2)
    ring_big = ImageChops.subtract(outer_big, inner_big)

    ys = (np.arange(PH * SS, dtype=np.float32) / SS - PAD) / m.CARD_H
    xs = (np.arange(PW * SS, dtype=np.float32) / SS - PAD) / m.CARD_W
    ry = np.clip(ys, 0, 1)[:, None]
    rx = np.clip(xs, 0, 1)[None, :]
    fill_a = np.clip(0.2 - 0.13 * ry + 0.05 * (1 - rx), 0, 1) * (np.asarray(inner_big, np.float32) / 255)
    border_a = np.clip(0.8 - 0.6 * ry, 0, 1) * (np.asarray(ring_big, np.float32) / 255)
    body_big = solid(CARD_TINT, Image.fromarray((fill_a * 255 + 0.5).astype(np.uint8), "L"))
    body_big.alpha_composite(solid((255, 255, 255), Image.fromarray((border_a * 255 + 0.5).astype(np.uint8), "L")))

    # accent bar under the number
    bw, bh, by = 88 * SS, 10 * SS, (PAD + m.CARD_H / 2 + 196) * SS
    bx0 = big[0] / 2 - bw / 2
    bar = rounded(big, (bx0, by - bh / 2, bx0 + bw - 1, by + bh / 2 - 1), bh / 2)
    t = np.clip((np.arange(big[0], dtype=np.float32) - bx0) / bw, 0, 1)[None, :, None]
    grad = np.array(ACCENT[0], np.float32) * (1 - t) + np.array(ACCENT[1], np.float32) * t
    grad = np.broadcast_to(grad, (big[1], big[0], 3)).astype(np.uint8)
    body_big.alpha_composite(solid(ACCENT[0], scale_mask(bar.filter(ImageFilter.GaussianBlur(8 * SS)), 0.7)))
    bar_img = Image.fromarray(grad, "RGB").convert("RGBA")
    bar_img.putalpha(bar)
    body_big.alpha_composite(bar_img)
    body = body_big.resize((PW, PH), LANCZOS)

    outer = outer_big.resize((PW, PH), LANCZOS)
    inner = inner_big.resize((PW, PH), LANCZOS)
    outside = ImageChops.invert(outer)

    # shadow and focus glow stay outside the glass so the card does not look dirty
    shadow = ImageChops.offset(outer, 0, 26).filter(ImageFilter.GaussianBlur(30))
    shadow = ImageChops.multiply(scale_mask(shadow, 0.6), outside)
    halo = _card_mask((PW, PH), 1, -8, m.CARD_RADIUS + 8).filter(ImageFilter.GaussianBlur(22))
    halo = ImageChops.multiply(scale_mask(halo, 0.95), outside)
    ring = ImageChops.subtract(outer, inner)
    inner_glow = ImageChops.multiply(scale_mask(ring.filter(ImageFilter.GaussianBlur(10)), 1.6), outer)
    bright = ImageChops.lighter(ring, scale_mask(inner_glow, 0.5))

    return {
        "shadow": solid((0, 3, 22), shadow),
        "glow": solid(LIGHT_RGB, halo),
        "body": body,
        "bright": solid((255, 255, 255), bright),
        "inner": np.asarray(inner, np.float32) / 255,
    }


def build_number_sprite(label):
    size = round(m.NUMBER_EM_PX * 1.3)
    font = ImageFont.truetype(str(FONT), m.NUMBER_EM_PX * SS)
    glyph = Image.new("L", (size * SS, size * SS), 0)
    # "mm" centres the line box (ascender..descender), like a CapCut text box
    ImageDraw.Draw(glyph).text((size * SS / 2, size * SS / 2), label, font=font, fill=255, anchor="mm")
    glyph = glyph.resize((size, size), LANCZOS)

    top, bottom = glyph.getbbox()[1], glyph.getbbox()[3]
    t = np.clip((np.arange(size, dtype=np.float32) - top) / (bottom - top), 0, 1)[:, None, None]
    rgb = np.array((255, 255, 255), np.float32) * (1 - t) + np.array((200, 222, 255), np.float32) * t
    fill = Image.fromarray(np.broadcast_to(rgb, (size, size, 3)).astype(np.uint8), "RGB").convert("RGBA")
    fill.putalpha(glyph)

    sprite = solid((0, 12, 60), scale_mask(ImageChops.offset(glyph, 0, 8).filter(ImageFilter.GaussianBlur(10)), 0.35))
    sprite.alpha_composite(solid((110, 195, 255), scale_mask(glyph.filter(ImageFilter.GaussianBlur(16)), 0.65)))
    sprite.alpha_composite(fill)
    return sprite


CARD = build_card_sprites()
NUMBERS = [build_number_sprite(label) for label in m.LABELS]
_SY, _SX = np.mgrid[0:PH, 0:PW].astype(np.float32)
_SHINE_U = ((_SX - PAD) + 0.45 * (_SY - PAD)) / (m.CARD_W + 0.45 * m.CARD_H)


def shine_layer(progress):
    c = -0.25 + 1.5 * m.ease_in_out_cubic(progress)
    band = 0.3 * np.exp(-((_SHINE_U - c) / 0.06) ** 2) + 0.12 * np.exp(-((_SHINE_U - c + 0.11) / 0.025) ** 2)
    alpha = Image.fromarray((band * CARD["inner"] * 255 + 0.5).astype(np.uint8), "L")
    return solid((255, 255, 255), alpha)


def card_layer(i, t):
    layer = CARD["shadow"].copy()
    focus = m.focus_amount(i, t)
    if focus > 0.002:
        layer.alpha_composite(with_alpha(CARD["glow"], focus))
    layer.alpha_composite(CARD["body"])
    if focus > 0.002:
        layer.alpha_composite(with_alpha(CARD["bright"], focus))
    progress = m.shine_progress(i, t)
    if progress is not None:
        layer.alpha_composite(shine_layer(progress))
    scale, rotation = m.number_local(i, t)
    place(layer, NUMBERS[i], PW / 2, PH / 2 + m.NUMBER_OFFSET_Y, scale, rotation)
    return layer


# ---------- frames ----------

def compose(t, cards=True):
    rgb = background(t) + _DITHER
    frame = Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").convert("RGBA")
    frame.alpha_composite(particles(t))
    if cards:
        for i in range(3):
            tr = m.card_transform(i, t)
            if tr.alpha > 0.002:
                place(frame, card_layer(i, t), tr.x, tr.y, tr.scale, tr.rotation, tr.alpha)
    return frame.convert("RGB")


def _full_frame(n):
    return compose(n / m.FPS).tobytes()


def _background_frame(n):
    return compose(n / m.FPS, cards=False).tobytes()


def encode(path, worker):
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{m.W}x{m.H}", "-r", str(m.FPS), "-i", "-",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-aq-mode", "3",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-movflags", "+faststart", str(path)]
    with Pool(min(12, os.cpu_count() or 1)) as pool, subprocess.Popen(cmd, stdin=subprocess.PIPE) as proc:
        for buf in pool.imap(worker, range(m.N_FRAMES), chunksize=2):
            proc.stdin.write(buf)
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit(f"ffmpeg failed while writing {path}")
    print("wrote", path.relative_to(HERE))


def contact_sheet(times, path, cols=4, thumb=(480, 270)):
    rows = math.ceil(len(times) / cols)
    sheet = Image.new("RGB", (cols * thumb[0], rows * (thumb[1] + 28)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for k, t in enumerate(times):
        x, y = (k % cols) * thumb[0], (k // cols) * (thumb[1] + 28)
        sheet.paste(compose(t).resize(thumb, LANCZOS), (x, y + 28))
        draw.text((x + 8, y + 6), f"t = {t:.2f}s", fill=(230, 230, 230))
    sheet.save(path)
    print("wrote", path.relative_to(HERE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stills", action="store_true", help="only write build/contact_sheet.png")
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    MEDIA.mkdir(parents=True, exist_ok=True)

    contact_sheet([0.55, 0.8, 1.05, 1.35, 1.7, 2.2, 2.95, 3.55, 4.15, 4.95, 5.6, 5.8, 6.0, 6.25, 6.45, 6.9],
                  BUILD / "contact_sheet.png")
    if args.stills:
        return

    preview = compose(4.95)
    preview.save(OUTPUT / "preview.png", optimize=True)
    preview.resize((960, 540), LANCZOS).save(MEDIA / "cover.jpg", quality=90)
    for i in range(3):
        card = Image.new("RGBA", (m.W, m.H), (0, 0, 0, 0))
        layer = CARD["shadow"].copy()
        layer.alpha_composite(CARD["body"])
        card.alpha_composite(layer, dest=(round(m.W / 2 - PW / 2), round(m.H / 2 - PH / 2)))
        card.save(MEDIA / f"card_{i + 1}.png", optimize=True)

    encode(OUTPUT / "three_cards_motion.mp4", _full_frame)
    encode(MEDIA / "background.mp4", _background_frame)


if __name__ == "__main__":
    main()
