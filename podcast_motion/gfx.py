"""Drawing helpers: easing, fonts, text, emoji, glass panels and compositing."""
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 30
LANCZOS, BICUBIC = Image.Resampling.LANCZOS, Image.Resampling.BICUBIC

WHITE = (255, 255, 255)
SOFT = (208, 224, 255)
INK = (16, 28, 78)
CYAN = (96, 206, 255)
GOLD = (255, 211, 92)
RED = (255, 96, 110)
GREEN = (86, 222, 150)
HOST_COLOR = {"bella": (255, 112, 166), "aaron": (255, 186, 52)}
HOST_NAME = {"bella": "Bella", "aaron": "Aaron"}


# ---------- easing ----------

def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def smoothstep(a, b, x):
    p = clamp01((x - a) / (b - a))
    return p * p * (3 - 2 * p)


def ease_out_cubic(p):
    return 1 - (1 - p) ** 3


def ease_in_cubic(p):
    return p ** 3


def ease_in_out(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def ease_out_back(p, s=1.70158):
    q = p - 1
    return 1 + (s + 1) * q ** 3 + s * q ** 2


def lerp(a, b, k):
    return a + (b - a) * k


def mix(c1, c2, k):
    return tuple(round(lerp(a, b, k)) for a, b in zip(c1, c2))


def pulse(dt, width=0.14):
    """Short bump peaking 0.1 s after a word starts; used to make text react to speech."""
    return math.exp(-((dt - 0.1) / width) ** 2) if -0.3 < dt < 0.6 else 0.0


# ---------- image basics ----------

def solid(rgb, mask):
    img = Image.new("RGBA", mask.size, tuple(rgb) + (0,))
    img.putalpha(mask)
    return img


def scale_mask(mask, k):
    return mask.point(lambda v: round(v * k))


def with_alpha(img, k):
    out = img.copy()
    out.putalpha(scale_mask(img.getchannel("A"), k))
    return out


def place(dst, src, cx, cy, scale=1.0, rotation=0.0, alpha=1.0):
    """Composite src centred at (cx, cy), scaled and rotated clockwise (degrees)."""
    if scale < 0.01 or alpha < 0.004:
        return
    if abs(scale - 1) < 1e-3 and abs(rotation) < 0.01:
        x0, y0 = round(cx - src.width / 2), round(cy - src.height / 2)
        sx0, sy0 = max(0, -x0), max(0, -y0)
        sx1, sy1 = min(src.width, dst.width - x0), min(src.height, dst.height - y0)
        if sx1 <= sx0 or sy1 <= sy0:
            return
        region = src if (sx0, sy0, sx1, sy1) == (0, 0, src.width, src.height) else src.crop((sx0, sy0, sx1, sy1))
        if alpha < 0.999:
            region = with_alpha(region, alpha)
        dst.alpha_composite(region, dest=(x0 + sx0, y0 + sy0))
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


# ---------- text ----------

@lru_cache(maxsize=None)
def font(weight, size):
    return ImageFont.truetype(str(HERE / "fonts" / f"Poppins-{weight}.ttf"), size)


def text_width(text, size, weight="Bold", tracking=0):
    return font(weight, size).getlength(text) + tracking * max(0, len(text) - 1)


@lru_cache(maxsize=8192)
def text_sprite(text, size, weight="Bold", color=WHITE, alpha=1.0, shadow=0.5, tracking=0):
    """Text on a transparent sprite; the sprite centre is the centre of the line box."""
    f = font(weight, size)
    asc, desc = f.getmetrics()
    pad = round(size * 0.45)
    w, h = math.ceil(text_width(text, size, weight, tracking)) + 2 * pad, asc + desc + 2 * pad
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    if tracking:
        x = pad
        for ch in text:
            draw.text((x, pad), ch, font=f, fill=255)
            x += f.getlength(ch) + tracking
    else:
        draw.text((pad, pad), text, font=f, fill=255)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = ImageChops.offset(mask, 0, max(1, round(size / 16))).filter(ImageFilter.GaussianBlur(size / 10))
        img = solid((0, 8, 40), scale_mask(sh, shadow))
    img.alpha_composite(solid(color, scale_mask(mask, alpha) if alpha < 1 else mask))
    return img


def wrap(text, size, weight, max_w):
    f = font(weight, size)
    lines, cur = [], []
    for word in text.split():
        if cur and f.getlength(" ".join(cur + [word])) > max_w:
            lines.append(cur)
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(cur)
    if len(lines) == 2:  # balance two lines
        words = lines[0] + lines[1]
        k = min(range(1, len(words)),
                key=lambda k: max(f.getlength(" ".join(words[:k])), f.getlength(" ".join(words[k:]))))
        lines = [words[:k], words[k:]]
    return [" ".join(line) for line in lines]


@lru_cache(maxsize=1024)
def text_block(text, size, weight="SemiBold", color=WHITE, max_w=1400, line_h=1.25, align="center", alpha=1.0,
               shadow=0.5):
    lines = [line for para in text.split("\n") for line in wrap(para, size, weight, max_w)]
    sprites = [text_sprite(line, size, weight, color, alpha, shadow) for line in lines]
    step = round(size * line_h)
    pad = sprites[0].height - step
    w = max(s.width for s in sprites)
    img = Image.new("RGBA", (w, step * len(lines) + pad), (0, 0, 0, 0))
    for k, s in enumerate(sprites):
        x = 0 if align == "left" else (w - s.width) // 2
        img.alpha_composite(s, (x, k * step))
    return img


# ---------- shapes ----------

def rounded_mask(w, h, r, pad=0, ss=2):
    m = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((pad * ss, pad * ss, (pad + w) * ss - 1, (pad + h) * ss - 1),
                                        radius=r * ss, fill=255)
    return m.resize((w + 2 * pad, h + 2 * pad), LANCZOS)


def _fill(mask, rgb, alpha, grad):
    ys = np.linspace(1 + grad / 2, 1 - grad / 2, mask.height, dtype=np.float32)[:, None]
    a = np.clip(np.asarray(mask, np.float32) / 255 * alpha * ys, 0, 1)
    return solid(rgb, Image.fromarray((a * 255 + 0.5).astype(np.uint8)))


def _shadow(outer, alpha, dy=14, blur=18):
    sh = ImageChops.offset(outer, 0, dy).filter(ImageFilter.GaussianBlur(blur))
    return solid((0, 4, 26), scale_mask(ImageChops.multiply(sh, ImageChops.invert(outer)), alpha))


@lru_cache(maxsize=512)
def panel(w, h, r=28, fill=WHITE, fill_a=0.11, border=WHITE, border_a=0.38, border_w=2, shadow_a=0.35, grad=0.5):
    pad = 40
    outer = rounded_mask(w, h, r, pad)
    inner = rounded_mask(w - 2 * border_w, h - 2 * border_w, max(1, r - border_w), pad + border_w)
    img = _shadow(outer, shadow_a) if shadow_a else Image.new("RGBA", outer.size, (0, 0, 0, 0))
    img.alpha_composite(_fill(inner, fill, fill_a, grad))
    img.alpha_composite(solid(border, scale_mask(ImageChops.subtract(outer, inner), border_a)))
    return img


@lru_cache(maxsize=256)
def glow(w, h, r, color, spread=18):
    """Outer glow plus an accent border; the inside stays clear so text on glass keeps its contrast."""
    pad = 40 + spread
    card = rounded_mask(w, h, r, pad)
    halo = rounded_mask(w + spread, h + spread, r + spread // 2, pad - spread // 2).filter(ImageFilter.GaussianBlur(spread))
    ring = ImageChops.subtract(card, rounded_mask(w - 6, h - 6, max(1, r - 3), pad + 3))
    return solid(color, ImageChops.lighter(ImageChops.multiply(halo, ImageChops.invert(card)), ring))


@lru_cache(maxsize=256)
def bubble(w, h, tail="left", fill=WHITE, fill_a=0.96, r=30, border=WHITE, border_a=0.0):
    ss, pad = 2, 40
    m = Image.new("L", ((w + 2 * pad) * ss, (h + 2 * pad) * ss), 0)
    d = ImageDraw.Draw(m)
    x0, y0, x1, y1 = pad * ss, pad * ss, (pad + w) * ss - 1, (pad + h) * ss - 1
    d.rounded_rectangle((x0, y0, x1, y1), radius=r * ss, fill=255)
    cx, cy, k = (x0 + x1) / 2, (y0 + y1) / 2, ss
    if tail == "left":
        d.polygon([(x0 + 8 * k, cy - 16 * k), (x0 - 26 * k, cy + 2 * k), (x0 + 8 * k, cy + 18 * k)], fill=255)
    elif tail == "right":
        d.polygon([(x1 - 8 * k, cy - 16 * k), (x1 + 26 * k, cy + 2 * k), (x1 - 8 * k, cy + 18 * k)], fill=255)
    elif tail == "down":
        d.polygon([(cx - 18 * k, y1 - 8 * k), (cx - 2 * k, y1 + 26 * k), (cx + 16 * k, y1 - 8 * k)], fill=255)
    elif tail == "up":
        d.polygon([(cx - 18 * k, y0 + 8 * k), (cx - 2 * k, y0 - 26 * k), (cx + 16 * k, y0 + 8 * k)], fill=255)
    mask = m.resize((w + 2 * pad, h + 2 * pad), LANCZOS)
    img = _shadow(mask, 0.4, 10, 14)
    img.alpha_composite(_fill(mask, fill, fill_a, 0.12))
    if border_a:
        inner = mask.filter(ImageFilter.MinFilter(5))
        img.alpha_composite(solid(border, scale_mask(ImageChops.subtract(mask, inner), border_a)))
    return img


@lru_cache(maxsize=512)
def pill(text, size=26, fg=WHITE, bg=CYAN, bg_a=0.24, border_a=0.7, upper=True, weight="SemiBold"):
    label = text.upper() if upper else text
    tracking = round(size * 0.08) if upper else 0
    tw = text_width(label, size, weight, tracking)
    w, h = round(tw + size * 1.6), round(size * 1.95)
    img = panel(w, h, h // 2, bg, bg_a, bg, border_a, 2, 0.25, 0.2).copy()
    ts = text_sprite(label, size, weight, fg, shadow=0.3 if fg == WHITE else 0, tracking=tracking)
    img.alpha_composite(ts, ((img.width - ts.width) // 2, (img.height - ts.height) // 2 + round(size * 0.04)))
    return img


# ---------- emoji and portraits ----------

@lru_cache(maxsize=512)
def emoji(name, size, shadow=0.4):
    src = Image.open(HERE / "assets" / "emoji" / f"{name}.png").convert("RGBA").resize((size, size), LANCZOS)
    pad = max(10, size // 6)
    out = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    if shadow:
        a = Image.new("L", out.size, 0)
        a.paste(src.getchannel("A"), (pad, pad + max(2, size // 20)))
        out = solid((0, 6, 32), scale_mask(a.filter(ImageFilter.GaussianBlur(max(2, size / 16))), shadow))
    out.alpha_composite(src, (pad, pad))
    return out


@lru_cache(maxsize=64)
def white_silhouette(name, size):
    img = emoji(name, size, shadow=0)
    return solid(WHITE, img.getchannel("A"))


@lru_cache(maxsize=64)
def portrait(name, d, ring=None, ring_w=6, dim=0.0):
    src = Image.open(HERE / "assets" / "hosts" / f"{name}.png").convert("RGB").resize((d, d), LANCZOS)
    if dim:
        src = ImageEnhance.Color(src).enhance(1 - 0.55 * dim)
        src = ImageEnhance.Brightness(src).enhance(1 - 0.45 * dim)
    pad, ss = 30, 3
    big = (d + 2 * pad) * ss
    circle = Image.new("L", (big, big), 0)
    ImageDraw.Draw(circle).ellipse((pad * ss, pad * ss, (pad + d) * ss - 1, (pad + d) * ss - 1), fill=255)
    circle = circle.resize((d + 2 * pad, d + 2 * pad), LANCZOS)
    out = _shadow(circle, 0.5, 10, 16)
    photo = Image.new("RGBA", circle.size, (0, 0, 0, 0))
    photo.paste(src, (pad, pad))
    photo.putalpha(ImageChops.multiply(photo.getchannel("A").point(lambda v: 255), circle))
    out.alpha_composite(photo)
    if ring:
        rm = Image.new("L", (big, big), 0)
        ImageDraw.Draw(rm).ellipse((pad * ss, pad * ss, (pad + d) * ss - 1, (pad + d) * ss - 1),
                                   outline=255, width=ring_w * ss)
        out.alpha_composite(solid(ring, rm.resize(circle.size, LANCZOS)))
    return out


@lru_cache(maxsize=64)
def icon_disc(name, d, bg=WHITE, bg_a=0.16):
    """An emoji inside a glass circle, used as a chat avatar for people other than the hosts."""
    img = panel(d, d, d // 2, bg, bg_a, WHITE, 0.45, 2, 0.35, 0.3).copy()
    e = emoji(name, round(d * 0.66), shadow=0.25)
    img.alpha_composite(e, ((img.width - e.width) // 2, (img.height - e.height) // 2))
    return img
