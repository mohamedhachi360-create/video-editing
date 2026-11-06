#!/usr/bin/env python3
"""Render a 5-second 2D animated podcast scene (Bella & Aaron) to MP4.

Usage:
  python render_podcast_scene.py                 # full video -> bella_aaron_podcast_5s.mp4
  python render_podcast_scene.py --stills 0 2.5  # preview frames at given seconds
  python render_podcast_scene.py --no-audio      # silent video
"""
import argparse
import math
import os
import shutil
import subprocess
import tempfile
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1920, 1080
FPS = 24
DUR = 5.0
NFRAMES = int(FPS * DUR)
SS = 2  # supersampling factor for antialiasing

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO_SRC = os.path.join(HERE, "..", "audio", "01_master_cleaned.mp3")


# ---------------------------------------------------------------- helpers
def hexc(h, a=None):
    h = h.lstrip("#")
    c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return c if a is None else c + (a,)


def mix(c1, c2, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smoothstep(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def window(t, a, b, ramp=0.25):
    return smoothstep((t - a) / ramp) * smoothstep((b - t) / ramp)


def pulse(t, center, half=0.08):
    return clamp(1 - abs(t - center) / half)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(p, q, t):
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


def catmull(pts, n=10, closed=True):
    out = []
    L = len(pts)
    segs = range(L) if closed else range(L - 1)
    for i in segs:
        if closed:
            p0, p1, p2, p3 = pts[(i - 1) % L], pts[i], pts[(i + 1) % L], pts[(i + 2) % L]
        else:
            p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, L - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)
                for j in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


def egg(cx, cy, rx, ry, chin=10, taper=0.22, n=72):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = math.cos(a), math.sin(a)
        s = max(0.0, y)
        pts.append((cx + rx * x * (1 - taper * s * s) + chin * s * s, cy + ry * y))
    return pts


class Ctx:
    """Draws in local coordinates: origin (ox, oy) in world units, x mirrored by d."""

    def __init__(self, img, ox=0.0, oy=0.0, d=1, s=SS, blend=False):
        self.dr = ImageDraw.Draw(img, "RGBA") if blend else ImageDraw.Draw(img)
        self.ox, self.oy, self.d, self.s = ox, oy, d, s

    def p(self, x, y):
        return ((self.ox + self.d * x) * self.s, (self.oy + y) * self.s)

    def pts(self, pts):
        return [self.p(x, y) for x, y in pts]

    def poly(self, pts, fill):
        self.dr.polygon(self.pts(pts), fill=fill)

    def shape(self, pts, fill, n=10):
        self.poly(catmull(pts, n, True), fill)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        x, y = self.p(cx, cy)
        rx, ry = rx * self.s, ry * self.s
        self.dr.ellipse([x - rx, y - ry, x + rx, y + ry], fill=fill, outline=outline,
                        width=int(round(width * self.s)))

    def line(self, pts, fill, w, smooth=False, caps=True):
        if smooth and len(pts) > 2:
            pts = catmull(pts, 10, False)
        P = self.pts(pts)
        ww = max(1, int(round(w * self.s)))
        self.dr.line(P, fill=fill, width=ww, joint="curve")
        if caps and ww >= 3:
            r = ww / 2
            for x, y in (P[0], P[-1]):
                self.dr.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def rect(self, x0, y0, x1, y1, fill, r=0):
        a, b = self.p(x0, y0), self.p(x1, y1)
        box = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        if r:
            self.dr.rounded_rectangle(box, radius=r * self.s, fill=fill)
        else:
            self.dr.rectangle(box, fill=fill)


def vgrad(w, h, top, bot):
    y = np.linspace(0, 1, h)[:, None]
    g = (np.array(top) * (1 - y) + np.array(bot) * y).astype(np.uint8)
    return Image.fromarray(g.reshape(h, 1, 3), "RGB").resize((w, h))


# ---------------------------------------------------------------- palette
BELLA = dict(
    kind="bella", d=1, ox=500, oy=500,
    skin=hexc("#8d5a3b"), skin_sh=hexc("#70442b"), skin_dk=hexc("#5a341f"),
    blush=mix(hexc("#8d5a3b"), hexc("#c0604f"), 0.35),
    lip=hexc("#7c3a36"), lip_line=hexc("#3e1d1a"),
    hair=hexc("#3a2317"), hair_hi=hexc("#5c3a26"),
    cloth=hexc("#1f8f8c"), cloth_sh=hexc("#166f6c"), cloth_hi=hexc("#34aea8"),
    rx=74, ry=95,
)
AARON = dict(
    kind="aaron", d=-1, ox=1420, oy=500,
    skin=hexc("#c68e64"), skin_sh=hexc("#a8724d"), skin_dk=hexc("#8a5a3a"),
    blush=mix(hexc("#c68e64"), hexc("#d9735f"), 0.25),
    lip=hexc("#a4614f"), lip_line=hexc("#5a2e25"),
    hair=hexc("#231914"), hair_hi=hexc("#3b2c23"),
    cloth=hexc("#d9a12b"), cloth_sh=hexc("#b5841e"), cloth_hi=hexc("#ebbb4c"),
    rx=80, ry=99,
)
MOUTH_DARK = hexc("#3d1418")
TONGUE = hexc("#b5545a")
EYE_WHITE = hexc("#fbf6ef")
IRIS = hexc("#4a2c1a")
PUPIL = hexc("#140c08")
LID = hexc("#1e120c")


# ---------------------------------------------------------------- static background
def draw_window_view():
    w, h = 300, 490
    img = vgrad(w * SS, h * SS, hexc("#ffc98a"), hexc("#fff0d4"))
    c = Ctx(img, blend=True)
    for (x, y, rx, ry, col) in [(40, 470, 90, 80, "#9fb07a"), (150, 500, 110, 90, "#8ea36b"),
                                (270, 460, 80, 95, "#a5b783"), (220, 430, 50, 60, "#b4c28f"),
                                (80, 420, 45, 55, "#b0bf8c")]:
        c.ell(x, y, rx, ry, hexc(col, 230))
    c.ell(60, 60, 120, 120, (255, 252, 240, 120))
    return img


def foam(c, x0, y0, cols, rows, tw, th):
    c.rect(x0 - 10, y0 - 10, x0 + cols * tw + 10, y0 + rows * th + 10, hexc("#232c31"))
    top, left, right, bot = hexc("#55696e"), hexc("#4a5d63"), hexc("#36464c"), hexc("#2c3a3f")
    for r in range(rows):
        for q in range(cols):
            x, y = x0 + q * tw, y0 + r * th
            cx, cy = x + tw / 2, y + th / 2
            X0, Y0, X1, Y1 = x + 3, y + 3, x + tw - 3, y + th - 3
            c.poly([(X0, Y0), (X1, Y0), (cx, cy)], top)
            c.poly([(X0, Y0), (X0, Y1), (cx, cy)], left)
            c.poly([(X1, Y0), (X1, Y1), (cx, cy)], right)
            c.poly([(X0, Y1), (X1, Y1), (cx, cy)], bot)


def leaf(c, x, y, ang, length, width, col, vein=None):
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    tip = (x + dx * length, y + dy * length)
    m1 = (x + dx * length * 0.45 + px * width, y + dy * length * 0.45 + py * width)
    m2 = (x + dx * length * 0.45 - px * width, y + dy * length * 0.45 - py * width)
    c.shape([(x, y), m1, tip, m2], col, n=6)
    if vein:
        c.line([(x, y), (x + dx * length * 0.85, y + dy * length * 0.85)], vein, 1.5, caps=False)


def draw_background():
    img = vgrad(W * SS, H * SS, hexc("#ecdcc4"), hexc("#d9bf9d"))
    # warmer/brighter near the window, a bit darker to the right
    xg = np.linspace(1.0, 0.86, W * SS).astype(np.float32)
    arr = np.asarray(img).astype(np.float32) * xg[None, :, None]
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    c = Ctx(img, blend=True)

    # wainscot, floor
    c.rect(0, 610, W, 880, hexc("#b98a5e"))
    for x in range(0, W, 64):
        c.line([(x, 616), (x, 868)], hexc("#a57650"), 3, caps=False)
        c.line([(x + 3, 616), (x + 3, 868)], hexc("#c79a6d"), 1.5, caps=False)
    c.rect(0, 600, W, 616, hexc("#94663f"))
    c.rect(0, 880, W, H, hexc("#7b4f33"))
    for y in (920, 975, 1040):
        c.line([(0, y), (W, y)], hexc("#6c432a"), 2, caps=False)
    c.rect(0, 864, W, 884, hexc("#6a432b"))

    # window + curtains
    img.paste(draw_window_view(), (40 * SS, 100 * SS))
    c.rect(26, 92, 354, 106, hexc("#f5f0e8"))
    c.rect(26, 92, 44, 598, hexc("#f5f0e8"))
    c.rect(336, 92, 354, 598, hexc("#f5f0e8"))
    c.rect(185, 100, 195, 590, hexc("#f5f0e8"))
    c.rect(40, 340, 340, 350, hexc("#f5f0e8"))
    c.rect(18, 588, 362, 608, hexc("#efe7da"))
    c.rect(18, 608, 362, 614, hexc("#b9a58c"))
    c.poly([(14, 80), (118, 80), (104, 300), (126, 660), (8, 660)], (250, 242, 228, 175))
    for x in (34, 62, 92):
        c.line([(x, 84), (x + 4, 650)], (255, 250, 240, 120), 4, caps=False)
    c.poly([(306, 80), (372, 80), (380, 660), (316, 660), (326, 300)], (250, 242, 228, 160))
    c.line([(4, 80), (386, 80)], hexc("#3a2c24"), 6)
    c.ell(4, 80, 8, 8, hexc("#3a2c24"))
    c.ell(386, 80, 8, 8, hexc("#3a2c24"))

    # floor plant under the window
    c.shape([(110, 800), (190, 800), (180, 880), (120, 880)], hexc("#c46a45"))
    for i, a in enumerate([-2.4, -2.0, -1.7, -1.4, -1.1, -0.8, -2.7]):
        col = hexc("#4f8a4b") if i % 2 else hexc("#3f7440")
        leaf(c, 150, 800, a, 150 + 20 * (i % 3), 34, col, hexc("#2f5a31"))

    # acoustic foam
    foam(c, 690, 130, 6, 4, 90, 90)

    # pendant lamps
    for x in (780, 1140):
        c.line([(x, 0), (x, 70)], hexc("#1c1c1c"), 3, caps=False)
        c.poly([(x - 20, 70), (x + 20, 70), (x + 54, 124), (x - 54, 124)], hexc("#2b2b2b"))
        c.poly([(x - 12, 74), (x + 2, 74), (x - 30, 118), (x - 44, 118)], hexc("#3d3d3d"))
        c.ell(x, 124, 54, 8, hexc("#ffe2a8"))

    # framed art (abstract, palette-matched)
    c.rect(1530, 110, 1770, 280, hexc("#3b2a20"))
    c.rect(1542, 122, 1758, 268, hexc("#f3ece0"))
    c.rect(1562, 142, 1738, 248, hexc("#efdcc0"))
    c.ell(1620, 200, 42, 42, hexc("#c4643f"))
    c.ell(1690, 230, 52, 52, hexc("#1f8f8c"))
    c.rect(1562, 230, 1738, 248, hexc("#efdcc0"))
    c.rect(1650, 160, 1700, 190, hexc("#d9a12b"))
    c.line([(1575, 236), (1725, 236)], hexc("#3b2a20"), 2, caps=False)

    # shelves
    for y in (340, 520):
        c.rect(1490, y, 1860, y + 14, hexc("#8a5a37"))
        c.rect(1490, y + 14, 1860, y + 18, hexc("#5e3a22"))
        for x in (1520, 1830):
            c.poly([(x - 6, y + 14), (x + 6, y + 14), (x + 6, y + 40)], hexc("#2a2a2a"))
    # shelf 1: books, trailing plant, red studio light
    x = 1508
    for wd, ht, col in [(18, 72, "#c0573e"), (22, 84, "#3f6e8c"), (16, 64, "#d9a441"),
                        (26, 90, "#6b8f5e"), (20, 76, "#e8dcc6"), (18, 80, "#7a4b6b")]:
        c.rect(x, 340 - ht, x + wd, 340, hexc(col))
        c.rect(x + 3, 340 - ht + 10, x + wd - 3, 340 - ht + 13, hexc("#f0e6d2"))
        x += wd + 2
    c.poly([(x + 4, 340), (x + 24, 340), (x + 52, 268), (x + 34, 262)], hexc("#b36b3a"))
    c.shape([(1665, 300), (1717, 300), (1711, 340), (1671, 340)], hexc("#efe9e1"))
    vine = catmull([(1712, 330), (1735, 360), (1728, 400), (1740, 440), (1732, 470)], 6, False)
    c.line(vine, hexc("#3d6b3a"), 2.5, caps=False)
    for i, (vx, vy) in enumerate(vine[::4]):
        leaf(c, vx, vy, 0.6 if i % 2 else 2.4, 22, 9, hexc("#5a9a52"))
    for a in (-2.6, -2.1, -1.6, -1.1, -0.6):
        leaf(c, 1691, 302, a, 38, 12, hexc("#5a9a52"), hexc("#3d6b3a"))
    c.rect(1772, 300, 1836, 340, hexc("#2c1c1c"), r=8)
    c.rect(1780, 307, 1828, 333, hexc("#e0463a"), r=6)
    # shelf 2: speaker, records, cactus
    c.rect(1505, 432, 1572, 520, hexc("#2d2f34"), r=6)
    c.ell(1538, 462, 18, 18, hexc("#1b1c1f"))
    c.ell(1538, 462, 7, 7, hexc("#4a4d54"))
    c.ell(1538, 500, 10, 10, hexc("#1b1c1f"))
    for i, col in enumerate(["#d07a4b", "#2f6f7a", "#e2c27a"]):
        c.poly([(1600 + i * 14, 520), (1690 + i * 14, 520), (1676 + i * 14, 432), (1588 + i * 14, 432)],
               hexc(col))
    c.shape([(1752, 492), (1796, 492), (1790, 520), (1758, 520)], hexc("#c46a45"))
    c.shape([(1764, 494), (1762, 450), (1774, 440), (1786, 452), (1784, 494)], hexc("#6f9a5a"))
    c.shape([(1784, 470), (1798, 462), (1802, 476), (1786, 482)], hexc("#6f9a5a"))

    # big plant at far right
    c.shape([(1810, 790), (1900, 790), (1890, 880), (1820, 880)], hexc("#efe9e1"))
    for i, a in enumerate([-2.2, -1.9, -1.6, -1.3, -1.0, -2.5, -0.75]):
        col = hexc("#4f8a4b") if i % 2 else hexc("#3f7440")
        leaf(c, 1855, 790, a, 190 + 25 * (i % 3), 44, col, hexc("#2f5a31"))

    # soft wall shadows cast by the people (light from the window on the left)
    sh = Image.new("L", (W // 4, H // 4), 0)
    sd = ImageDraw.Draw(sh)
    for cx in (BELLA["ox"] + 70, AARON["ox"] + 80):
        sd.ellipse([(cx - 150) / 4, 230 / 4, (cx + 150) / 4, 760 / 4], fill=70)
    sh = sh.filter(ImageFilter.GaussianBlur(14)).resize((W * SS, H * SS), Image.BILINEAR)
    dark = Image.new("RGB", img.size, hexc("#5a3f2a"))
    img = Image.composite(dark, img, sh)

    # slight depth of field on the background
    return img.filter(ImageFilter.GaussianBlur(2.2 * SS / 2))


def draw_foreground():
    """Desk and static desk props, drawn over the characters' bodies."""
    fg = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    c = Ctx(fg)
    c.poly([(230, 700), (1690, 700), (1780, 795), (140, 795)], hexc("#b47e53"))
    c.poly([(230, 700), (1690, 700), (1700, 712), (220, 712)], hexc("#a06c45"))
    for y, x0, x1 in [(726, 300, 900), (744, 980, 1600), (762, 260, 760), (778, 1100, 1700), (735, 1300, 1620)]:
        c.line([(x0, y), (x1, y + 2)], hexc("#a77149"), 2, caps=False)
    c.rect(140, 795, 1780, 820, hexc("#8d5b38"))
    c.line([(140, 796), (1780, 796)], hexc("#d29d72"), 3, caps=False)
    c.rect(150, 820, 1770, H + 2, hexc("#6d4229"))
    c.rect(150, 820, 1770, 830, hexc("#4a2b19"))
    for x in range(170, 1770, 38):
        c.line([(x, 832), (x, H)], hexc("#5d3720"), 4, caps=False)
        c.line([(x + 4, 832), (x + 4, H)], hexc("#7c4e31"), 2, caps=False)

    # mixer
    c.poly([(868, 712), (1052, 712), (1068, 762), (852, 762)], hexc("#2d3036"))
    c.poly([(872, 712), (1048, 712), (1056, 738), (864, 738)], hexc("#3a3e45"))
    for i in range(8):
        x = 884 + i * 21
        c.ell(x, 722, 4.5, 3.5, hexc(["#e0b04a", "#4fb3a9", "#e06a4a", "#dddddd"][i % 4]))
        c.rect(x - 1.5, 740, x + 1.5, 756, hexc("#16181b"))
        c.rect(x - 5, 744 + (i * 5) % 9, x + 5, 749 + (i * 5) % 9, hexc("#c9ccd1"))
    c.ell(1040, 721, 3, 3, hexc("#59e07a"))

    # papers (Bella), phone (Aaron)
    c.poly([(560, 752), (668, 744), (676, 786), (566, 792)], hexc("#f4efe6"))
    c.poly([(574, 748), (680, 736), (690, 776), (582, 786)], hexc("#fbf8f2"))
    for k in range(5):
        y = 750 + k * 7
        c.line([(590, y + 0), (668, y - 8)], hexc("#c9c2b6"), 1.5, caps=False)
    c.poly([(1262, 760), (1318, 756), (1322, 782), (1266, 786)], hexc("#1d1f23"))

    # mugs
    for (x, col, hd) in [(745, "#c4643f", -1), (1178, "#efeae2", 1)]:
        c.rect(x - 22, 696, x + 22, 744, hexc(col), r=6)
        c.ell(x, 696, 22, 6, mix(hexc(col), (0, 0, 0), 0.25))
        c.ell(x, 697, 18, 4, hexc("#4a2c1c"))
        c.ell(x + hd * 26, 718, 10, 13, None, outline=hexc(col), width=5)
        c.rect(x - 22, 732, x + 22, 744, mix(hexc(col), (0, 0, 0), 0.12), r=4)
    return fg


def build_light():
    """Returns (beams, glows) as float32 HxWx3 maps in 0..1 for screen blending (world res)."""
    s = 4  # build at quarter res
    w, h = W // s, H // s

    def mask():
        return Image.new("L", (w, h), 0)

    beams = mask()
    bd = ImageDraw.Draw(beams)
    L = 1500
    for (y0, y1) in [(106, 338), (352, 586)]:
        for (x0, x1) in [(44, 183), (197, 336)]:
            # light falls down-right from each pane
            off = (x1 - 44) * 0.0
            pts = [(x1, y0), (x1, y1), (x1 + L, y1 + L * 0.42 + 80), (x1 + L, y0 + L * 0.42 + off)]
            bd.polygon([(px / s, py / s) for px, py in pts], fill=120)
    streaks = mask()
    sd = ImageDraw.Draw(streaks)
    for y0, wd in [(150, 18), (230, 10), (420, 22), (500, 12)]:
        pts = [(336, y0), (336, y0 + wd), (336 + L, y0 + wd + L * 0.42 + 30), (336 + L, y0 + L * 0.42)]
        sd.polygon([(px / s, py / s) for px, py in pts], fill=90)
    beams = ImageChops.add(beams.filter(ImageFilter.GaussianBlur(10)), streaks.filter(ImageFilter.GaussianBlur(3)))
    b = np.asarray(beams).astype(np.float32) / 255.0
    xs = np.linspace(0, W, w, dtype=np.float32)
    fall = np.clip(1.15 - (xs - 340) / 1500, 0.15, 1.0)
    b = b * fall[None, :]
    beam_rgb = np.array([1.0, 0.76, 0.48], np.float32)
    beams_map = b[..., None] * beam_rgb * 0.55

    g = mask()
    gd = ImageDraw.Draw(g)
    gd.ellipse([0, 60 / s, 400 / s, 640 / s], fill=150)              # window bloom
    for x in (780, 1140):
        gd.ellipse([(x - 80) / s, 90 / s, (x + 80) / s, 170 / s], fill=200)
    g = g.filter(ImageFilter.GaussianBlur(18))
    gwarm = np.asarray(g).astype(np.float32) / 255.0
    r = mask()
    ImageDraw.Draw(r).ellipse([1760 / s, 280 / s, 1850 / s, 360 / s], fill=200)
    gred = np.asarray(r.filter(ImageFilter.GaussianBlur(8))).astype(np.float32) / 255.0
    glows = gwarm[..., None] * np.array([1.0, 0.85, 0.6], np.float32) * 0.5 \
        + gred[..., None] * np.array([1.0, 0.3, 0.22], np.float32) * 0.5

    def up(a):
        return np.stack([np.asarray(Image.fromarray(a[..., k]).resize((W, H), Image.BILINEAR))
                         for k in range(3)], -1)

    return up(beams_map), up(glows)


# ---------------------------------------------------------------- characters
def draw_eye(c, x, y, rx, ry, blink, look, happy, lash_dir, lashes):
    if happy > 0.5:
        c.line([(x - rx, y + 3), (x, y - ry * 0.7), (x + rx, y + 3)], LID, 4, smooth=True)
        return
    h = ry * (1 - blink)
    if h < 2:
        c.line([(x - rx, y), (x, y + 2.5), (x + rx, y)], LID, 3.5, smooth=True)
        return
    c.ell(x, y, rx, h, EYE_WHITE)
    ir = rx * 0.62
    ix, iy = x + look, y + 1
    c.ell(ix, iy, ir, min(ir, h), IRIS)
    c.ell(ix, iy, ir * 0.5, min(ir * 0.5, h * 0.6), PUPIL)
    if h > 4:
        c.ell(ix - ir * 0.35, iy - ir * 0.4, 2.4, 2.4, (255, 255, 255))
    c.line([(x - rx - 1, y + 1), (x - rx * 0.4, y - h - 1), (x + rx * 0.5, y - h - 0.5), (x + rx + 1.5, y - 1)],
           LID, 3.5 if lashes else 3, smooth=True)
    if lashes:
        ex = x + lash_dir * rx
        c.line([(ex, y - 2), (ex + lash_dir * 7, y - 8)], LID, 2.5)


def draw_mouth(c, sp, mx, my, openness, mode, smile):
    if mode == "laugh":
        c.poly(catmull([(mx - 22, my - 5), (mx + 18, my - 6), (mx + 12, my + 10), (mx - 2, my + 16),
                        (mx - 16, my + 8)], 8), MOUTH_DARK)
        c.poly([(mx - 18, my - 5), (mx + 15, my - 6), (mx + 13, my - 1), (mx - 16, my)], (250, 246, 240))
        c.ell(mx - 2, my + 11, 9, 4, TONGUE)
        c.line([(mx - 23, my - 5), (mx - 2, my - 7), (mx + 19, my - 6)], sp["lip_line"], 3, smooth=True)
        return
    if openness < 0.1:
        c.ell(mx - 1, my + 4, 11, 4.5, sp["lip"])
        c.line([(mx - 17, my - 1 - 2 * smile), (mx - 2, my + 2 + 1.5 * smile), (mx + 14, my - 2 - 2 * smile)],
               sp["lip_line"], 3.5, smooth=True)
        return
    o = openness
    w = 15 + 2 * o
    pts = [(mx - w, my - 1), (mx - 2, my - 4), (mx + w - 2, my - 2),
           (mx + w - 5, my + 2 + 6 * o), (mx - 1, my + 4 + 15 * o), (mx - w + 3, my + 2 + 6 * o)]
    c.poly(catmull(pts, 8), sp["lip"])
    inner = [(mx - w + 4, my), (mx - 2, my - 1.5), (mx + w - 6, my - 0.5),
             (mx + w - 8, my + 2 + 4 * o), (mx - 1, my + 1 + 12 * o), (mx - w + 6, my + 2 + 4 * o)]
    c.poly(catmull(inner, 8), MOUTH_DARK)
    if o > 0.3:
        c.poly([(mx - w + 7, my - 0.5), (mx + w - 9, my), (mx + w - 10, my + 3), (mx - w + 8, my + 3)],
               (248, 244, 238))
    c.ell(mx - 1, my + 1 + 10 * o, 7, 2.5 * o + 0.5, TONGUE)


def draw_head(c, sp, st):
    k = sp["kind"]
    rx, ry, cy = sp["rx"], sp["ry"], -160
    if k == "aaron":
        c.ell(-50, -148, 13, 21, sp["skin_sh"])
    c.poly(egg(-4, cy + 3, rx, ry), sp["skin_sh"])
    c.poly(egg(2, cy - 2, rx - 3, ry - 3), sp["skin"])
    if k == "aaron":
        cap = [(-86, -150), (-88, -200), (-62, -250), (-10, -268), (46, -260), (80, -228), (88, -196),
               (74, -198), (58, -216), (28, -214), (0, -220), (-22, -210), (-30, -185), (-28, -142),
               (-38, -132), (-48, -168), (-66, -160), (-78, -120)]
        c.shape(cap, sp["hair"], 8)
        for pts in ([(-60, -246), (-10, -262), (40, -254)], [(-74, -220), (-40, -244), (6, -248)],
                    [(10, -236), (48, -240), (72, -222)]):
            c.line(pts, sp["hair_hi"], 3, smooth=True)
        c.ell(-52, -150, 12, 20, sp["skin"])
        c.ell(-50, -148, 6, 11, sp["skin_sh"])
    # blush
    c.ell(-6, -124, 16, 10, sp["blush"])
    c.ell(56, -126, 9, 8, sp["blush"])
    # eyes / brows
    happy = st["happy"]
    lashes = k == "bella"
    br = st["brow"]
    bw = 5 if lashes else 7
    c.line([(-20, -185 - br), (-4, -191 - br), (12, -188 - br * 0.6)], sp["hair"], bw, smooth=True)
    c.line([(38, -189 - br * 0.6), (50, -192 - br), (62, -186 - br)], sp["hair"], bw - 1, smooth=True)
    draw_eye(c, -3, -165, 14, 10, st["blink"], st["look"], happy, -1, lashes)
    draw_eye(c, 51, -166, 11, 9, st["blink"], st["look"] * 0.8, happy, 1, lashes)
    # nose
    c.line([(30, -160), (40, -138), (47, -124), (41, -117), (32, -119)], sp["skin_dk"], 3.5, smooth=True)
    c.ell(40, -121, 3, 2, sp["skin_dk"])
    draw_mouth(c, sp, 24, -97, st["mouth"], st["mouth_mode"], st["smile"])
    if k == "bella":
        front = [(-118, -150), (-108, -215), (-70, -258), (-10, -274), (50, -264), (90, -228), (100, -188),
                 (94, -172), (78, -196), (52, -222), (22, -214), (0, -228), (-24, -210), (-48, -192),
                 (-60, -160), (-64, -120), (-72, -80), (-96, -58), (-116, -100)]
        c.shape(front, sp["hair"], 8)
        for pts in ([(-30, -264), (-80, -232), (-100, -170), (-104, -110)],
                    [(10, -266), (58, -244), (88, -204)],
                    [(-10, -250), (-50, -228), (-70, -180), (-80, -110)],
                    [(30, -240), (60, -226), (80, -205)]):
            c.line(pts, sp["hair_hi"], 3.5, smooth=True)
        # little gold earring peeking under the hair
        c.ell(-66, -112, 4, 4, hexc("#d8b25a"))


def draw_back_hair(c, sp):
    back = [(0, -270), (-72, -254), (-114, -205), (-124, -140), (-122, -80), (-130, -28), (-110, -6),
            (-86, -22), (-64, -2), (-40, -20), (-16, -8), (8, -26), (34, -10), (60, -28), (84, -12),
            (102, -36), (96, -90), (100, -150), (104, -210), (72, -254)]
    c.shape(back, sp["hair"], 8)
    for pts in ([(-114, -110), (-104, -66), (-118, -26)], [(-90, -80), (-84, -44), (-94, -16)],
                [(92, -120), (98, -76), (88, -30)], [(74, -80), (66, -50), (72, -20)]):
        c.line(pts, sp["hair_hi"], 3.5, smooth=True)


HEAD_W, HEAD_TOP, HEAD_BOT = 360, 300, 40
PIVOT = (0, -70)


def paste_head_layer(frame, sp, st, body_y, drawer):
    layer = Image.new("RGBA", (HEAD_W * SS, (HEAD_TOP + HEAD_BOT) * SS), (0, 0, 0, 0))
    hc = Ctx(layer, ox=HEAD_W / 2, oy=HEAD_TOP, d=sp["d"])
    drawer(hc)
    angle = -sp["d"] * st["tilt"]
    if abs(angle) > 0.01:
        layer = layer.rotate(angle, resample=Image.BICUBIC,
                             center=((HEAD_W / 2) * SS, (HEAD_TOP + PIVOT[1]) * SS))
    px = int(round((sp["ox"] - HEAD_W / 2 + sp["d"] * st["head_dx"]) * SS))
    py = int(round((body_y - HEAD_TOP + st["head_dy"]) * SS))
    frame.paste(layer, (px, py), layer)


def draw_character_back(frame, sp, st):
    d, k = sp["d"], sp["kind"]
    by = sp["oy"] + st["body_dy"]
    c = Ctx(frame, ox=sp["ox"], oy=by, d=d, blend=True)
    # chair
    c.rect(-150, -40, 30, 250, hexc("#2a2c32"), r=40)
    c.rect(-142, -32, -120, 240, hexc("#3a3d45"), r=10)
    if k == "bella":
        paste_head_layer(frame, sp, st, by, lambda hc: draw_back_hair(hc, sp))
    # headphone band behind the neck
    c.line([(-46, 16), (-42, -14), (0, -28), (42, -14), (52, 16)], hexc("#25272c"), 9, smooth=True)
    # neck
    c.poly([(-24, -100), (26, -100), (30, 8), (-26, 8)], sp["skin"])
    c.ell(8, -60, 32, 16, sp["skin_sh"])
    # torso
    torso = [(-98, 60), (-86, 20), (-52, 4), (-20, 0), (30, 0), (64, 6), (90, 22), (104, 60), (106, 200),
             (100, 330), (-94, 330), (-104, 200)]
    c.shape(torso, sp["cloth"], 8)
    c.shape([(-98, 60), (-86, 20), (-64, 10), (-74, 70), (-80, 330), (-94, 330), (-104, 200)], sp["cloth_sh"], 8)
    c.line([(60, 10), (88, 26), (100, 60)], sp["cloth_hi"], 5, smooth=True)
    if k == "bella":
        c.poly([(-22, -1), (32, -1), (8, 60)], sp["skin"])
        c.line([(-14, 2), (6, 26), (26, 2)], hexc("#d8b25a"), 2, smooth=True, caps=False)
        c.ell(6, 29, 3.5, 3.5, hexc("#d8b25a"))
        c.poly([(-32, -3), (-8, -4), (6, 44), (-6, 34)], sp["cloth_hi"])
        c.poly([(44, -3), (22, -4), (10, 44), (22, 34)], sp["cloth_hi"])
        for y in (86, 124, 162):
            c.ell(8, y, 3.5, 3.5, sp["cloth_sh"])
    else:
        for x in range(-70, 100, 16):
            c.line([(x, 40), (x, 330)], sp["cloth_sh"], 2, caps=False)
        c.line([(-30, -2), (-14, 10), (4, 14), (22, 10), (36, -2)], sp["cloth_sh"], 13, smooth=True)
        c.line([(-30, -2), (-14, 10), (4, 14), (22, 10), (36, -2)], sp["cloth"], 5, smooth=True)
    # headphone cups resting on the collarbones
    c.ell(-46, 18, 19, 25, hexc("#2b2e34"))
    c.ell(-44, 18, 12, 17, hexc("#454a52"))
    c.ell(54, 20, 13, 22, hexc("#2b2e34"))
    paste_head_layer(frame, sp, st, by, lambda hc: draw_head(hc, sp, st))


def draw_hand(c, sp, wrist, ang, open_hand):
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    palm = (wrist[0] + dx * 13, wrist[1] + dy * 13)
    fingers = []
    spread = 0.24 if open_hand else 0.1
    flen = 17 if open_hand else 13
    for i in range(4):
        a = ang + (i - 1.5) * spread
        base = (palm[0] + px * (i - 1.5) * 5.5 + dx * 6, palm[1] + py * (i - 1.5) * 5.5 + dy * 6)
        fingers.append((base, (base[0] + math.cos(a) * flen, base[1] + math.sin(a) * flen)))
    ta = ang - 1.0
    tb = (palm[0] - px * 9, palm[1] - py * 9)
    thumb = (tb, (tb[0] + math.cos(ta) * 13, tb[1] + math.sin(ta) * 13))
    for a, b in fingers + [thumb]:
        c.line([a, b], sp["skin_sh"], 9)
    c.ell(palm[0], palm[1], 15, 15, sp["skin_sh"])
    c.ell(palm[0], palm[1], 13.5, 13.5, sp["skin"])
    for a, b in fingers + [thumb]:
        c.line([a, b], sp["skin"], 6.5)


def draw_arm(c, sp, S, E, Wr, open_hand=False):
    c.line([S, E, Wr], sp["cloth_sh"], 34)
    c.line([S, E, Wr], sp["cloth"], 29)
    ang = math.atan2(Wr[1] - E[1], Wr[0] - E[0])
    cuff0 = (Wr[0] - math.cos(ang) * 8, Wr[1] - math.sin(ang) * 8)
    c.line([cuff0, Wr], sp["cloth_sh"], 30)
    draw_hand(c, sp, Wr, ang, open_hand)


def draw_character_front(frame, sp, st):
    c = Ctx(frame, ox=sp["ox"], oy=sp["oy"] + st["body_dy"], d=sp["d"], blend=True)
    draw_arm(c, sp, (-56, 48), (0, 200), (112, 238))
    # the animated arm is the one on the microphone side, so it never crosses the chest
    g = st["arm_blend"]
    E = lerp2((92, 186), st["arm_E"], g)
    Wr = lerp2((176, 222), st["arm_W"], g)
    draw_arm(c, sp, (62, 42), E, Wr, open_hand=st["open_hand"] and g > 0.4)


def mic_points(adj):
    F = (122, -104 - 6 * adj)
    B = (212, -80 - 12 * adj)
    return F, B


def draw_mic(frame, sp, adj):
    c = Ctx(frame, ox=sp["ox"], oy=sp["oy"], d=sp["d"], blend=True)
    F, B = mic_points(adj)
    M = (B[0] + 6, B[1] + 10)
    C = (300, 206)
    J = (334, -24)
    rod = hexc("#1e1f22")
    for (a, b) in ((C, J), (J, M)):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        px, py = -math.sin(ang) * 5, math.cos(ang) * 5
        c.line([(a[0] + px, a[1] + py), (b[0] + px, b[1] + py)], rod, 4)
        c.line([(a[0] - px, a[1] - py), (b[0] - px, b[1] - py)], rod, 4)
    c.line(catmull([C, (326, 100), J, (290, -60), M], 8, False), hexc("#111214"), 2, caps=False)
    c.ell(J[0], J[1], 9, 9, hexc("#2c2e33"))
    c.rect(C[0] - 14, C[1] - 8, C[0] + 14, C[1] + 8, hexc("#2c2e33"), r=3)
    # capsule
    c.line([F, B], hexc("#2a2c30"), 46)
    G = lerp2(F, B, 0.45)
    c.line([F, G], hexc("#5a5e66"), 46)
    ang = math.atan2(B[1] - F[1], B[0] - F[0])
    px, py = -math.sin(ang), math.cos(ang)
    for k in range(1, 6):
        q = lerp2(F, G, k / 6)
        c.line([(q[0] + px * 21, q[1] + py * 21), (q[0] - px * 21, q[1] - py * 21)], hexc("#464a51"), 1.5,
               caps=False)
    R = lerp2(F, B, 0.47)
    c.line([(R[0] + px * 24, R[1] + py * 24), (R[0] - px * 24, R[1] - py * 24)], hexc("#9a9ea6"), 5)
    S = lerp2(F, B, 0.7)
    c.line([(S[0] + px * 32, S[1] + py * 32), (S[0] - px * 32, S[1] - py * 32)], hexc("#141517"), 6)
    c.line([lerp2(F, G, 0.15), lerp2(F, G, 0.85)], (255, 255, 255, 40), 6)


def draw_steam(frame, t):
    c = Ctx(frame, blend=True)
    for x, ph in ((745, 0.0), (1178, 1.7)):
        for j in range(2):
            pts = []
            for k in range(12):
                y = 690 - k * 7
                pts.append((x - 6 + 12 * j + 7 * math.sin(k * 0.55 + t * 2.6 + ph + j * 2), y - 3 * t % 7))
            for a in range(len(pts) - 1):
                alpha = int(60 * (1 - a / len(pts)))
                c.line([pts[a], pts[a + 1]], (255, 255, 255, alpha), 3, caps=False)


# ---------------------------------------------------------------- animation timeline
def bella_state(t, env, talk_slow):
    i = min(int(round(t * FPS)), len(env) - 1)
    o = float(env[i])
    gest = window(t, 0.5, 4.6, 0.45)
    osc = math.sin(2 * math.pi * 1.1 * t)
    return dict(
        tilt=2.0 * math.sin(2 * math.pi * 0.55 * t) + 2.5 * talk_slow[i] + 1.5 * o,
        head_dx=1.5 * math.sin(2 * math.pi * 0.4 * t), head_dy=-1.5 * o,
        body_dy=1.5 * math.sin(2 * math.pi * 0.3 * t),
        mouth=o, mouth_mode="talk", smile=1.0,
        blink=max(pulse(t, 1.55), pulse(t, 4.3)),
        brow=3.0 * o + 2.0 * window(t, 2.0, 2.8, 0.2),
        look=3.0, happy=0.0,
        arm_blend=gest,
        arm_E=(78 + 6 * osc, 178), arm_W=(148 + 12 * osc, 92 - 14 * math.sin(2 * math.pi * 1.6 * t + 0.4)),
        open_hand=True,
    )


def aaron_state(t):
    nod = window(t, 0.9, 2.4, 0.3) * max(0.0, math.sin(2 * math.pi * 1.5 * (t - 0.9)))
    laugh = window(t, 2.55, 3.75, 0.2)
    reach = window(t, 3.75, 5.6, 0.45)
    adj = smoothstep((t - 4.15) / 0.5) * reach
    bounce = laugh * abs(math.sin(2 * math.pi * 4.2 * t))
    F, B = mic_points(adj)
    grip = lerp2(F, B, 0.62)
    return dict(
        tilt=6.0 * nod - 5.0 * laugh + 1.5 * bounce + 1.0 * math.sin(2 * math.pi * 0.35 * t),
        head_dx=0.0, head_dy=-2.0 * bounce,
        body_dy=1.5 * math.sin(2 * math.pi * 0.3 * t + 1.0) - 3.0 * bounce,
        mouth=0.0, mouth_mode="laugh" if laugh > 0.35 else "closed", smile=1.0,
        blink=max(pulse(t, 0.7), pulse(t, 2.3), pulse(t, 4.65)),
        brow=2.5 * laugh + 1.5 * nod,
        look=3.0, happy=laugh,
        arm_blend=reach,
        arm_E=(120, 118), arm_W=(grip[0] - 8, grip[1] + 34),
        open_hand=True,
        mic_adj=adj,
    )


def camera_box(t):
    u = smoothstep(t / DUR)
    z = 1.0 + 0.09 * u
    cx = 960 + 6 * u + 1.2 * math.sin(2 * math.pi * 0.23 * t)
    cy = 540 - 22 * u + 0.8 * math.sin(2 * math.pi * 0.31 * t + 1)
    bw, bh = W / z, H / z
    x0 = clamp(cx - bw / 2, 0, W - bw)
    y0 = clamp(cy - bh / 2, 0, H - bh)
    return x0, y0, x0 + bw, y0 + bh


# ---------------------------------------------------------------- audio
def load_mouth_env(path):
    if not path or not os.path.exists(path):
        t = np.arange(NFRAMES) / FPS
        o = np.clip(0.5 + 0.5 * np.sin(t * 17) * np.sin(t * 5.3), 0, 1)
        return o.astype(np.float32)
    sr = 16000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-t", str(DUR + 0.2), "-i", path, "-ac", "1",
                          "-ar", str(sr), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    half = sr // FPS
    env = []
    for i in range(NFRAMES):
        t = i / FPS
        c = int(t * sr)
        seg = a[max(0, c - half // 2): c + half]
        rms = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
        env.append(rms / max(min(t + 0.04, 1.0), 0.3))  # undo the master's 1 s fade-in
    env = np.array(env)
    ref = np.percentile(env, 90) + 1e-6
    o = np.clip((env / ref - 0.2) / 0.7, 0, 1)
    out = o.copy()
    for i in range(1, len(o)):
        out[i] = 0.7 * o[i] + 0.3 * out[i - 1]
    return out.astype(np.float32)


# ---------------------------------------------------------------- frame rendering
G = {}


def setup(audio):
    G["bg"] = draw_background()
    G["fg"] = draw_foreground()
    G["beams"], G["glows"] = build_light()
    G["env"] = load_mouth_env(audio)
    k = 12
    G["talk_slow"] = np.convolve(G["env"], np.ones(k) / k, mode="same")
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    G["vig"] = (1 - 0.22 * np.clip(r2, 0, 2) ** 1.2)[..., None].astype(np.float32)
    rng = np.random.default_rng(7)
    dust = []
    while len(dust) < 90:
        x, y = rng.uniform(340, 1500), rng.uniform(100, 1000)
        if G["beams"][int(y), int(x)].sum() > 0.12:
            dust.append((x, y, rng.uniform(0, 6.28), rng.uniform(0.8, 2.2), rng.uniform(4, 14)))
    G["dust"] = dust


def render_frame(i):
    t = i / FPS
    frame = G["bg"].copy()
    sb = bella_state(t, G["env"], G["talk_slow"])
    sa = aaron_state(t)
    draw_character_back(frame, BELLA, sb)
    draw_character_back(frame, AARON, sa)
    frame.paste(G["fg"], (0, 0), G["fg"])
    draw_steam(frame, t)
    draw_mic(frame, BELLA, 0.0)
    draw_mic(frame, AARON, sa["mic_adj"])
    draw_character_front(frame, BELLA, sb)
    draw_character_front(frame, AARON, sa)

    box = camera_box(t)
    out = frame.resize((W, H), Image.LANCZOS, box=tuple(v * SS for v in box))
    x0, y0, x1, y1 = box
    flick = 0.86 + 0.09 * math.sin(2 * math.pi * 0.9 * t) + 0.05 * math.sin(2 * math.pi * 2.3 * t + 1)

    def crop(m):
        chans = [np.asarray(Image.fromarray(m[..., k]).resize((W, H), Image.BILINEAR, box=box))
                 for k in range(3)]
        return np.stack(chans, -1)

    light = np.clip(crop(G["beams"]) * flick + crop(G["glows"]), 0, 1)
    a = np.asarray(out).astype(np.float32) / 255.0
    a = 1 - (1 - a) * (1 - light)
    a = a * np.array([1.03, 1.0, 0.94], np.float32)
    a = a * G["vig"]
    a = (a - 0.5) * 1.04 + 0.5
    rng = np.random.default_rng(1000 + i)
    a += rng.normal(0, 0.008, (H, W, 1)).astype(np.float32)
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

    # dust motes floating in the sunbeams
    dr = ImageDraw.Draw(img, "RGBA")
    sx, sy = W / (x1 - x0), H / (y1 - y0)
    for (dx, dy, ph, rad, spd) in G["dust"]:
        wx = dx + spd * t + 6 * math.sin(t * 0.7 + ph)
        wy = dy - 0.4 * spd * t + 5 * math.sin(t * 0.9 + ph * 1.3)
        tw = 0.5 + 0.5 * math.sin(t * 2.2 + ph * 3)
        alpha = int(40 + 120 * tw * flick)
        px, py, r = (wx - x0) * sx, (wy - y0) * sy, rad * sx
        dr.ellipse([px - r, py - r, px + r, py + r], fill=(255, 240, 205, alpha))
    return img


def _worker(args):
    i, outdir = args
    render_frame(i).save(os.path.join(outdir, f"{i:04d}.png"), compress_level=1)
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", nargs="*", type=float)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "bella_aaron_podcast_5s.mp4"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()
    audio = None if args.no_audio else os.path.abspath(AUDIO_SRC)
    setup(audio)

    if args.stills is not None:
        for s in args.stills:
            i = min(int(round(s * FPS)), NFRAMES - 1)
            p = os.path.join(HERE, f"still_{s:.2f}s.png")
            render_frame(i).save(p)
            print(p)
        return

    tmp = tempfile.mkdtemp(prefix="podcast_frames_")
    try:
        with Pool(args.jobs) as pool:
            for n, _ in enumerate(pool.imap_unordered(_worker, [(i, tmp) for i in range(NFRAMES)]), 1):
                if n % 24 == 0:
                    print(f"rendered {n}/{NFRAMES} frames", flush=True)
        cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png")]
        if audio and os.path.exists(audio):
            cmd += ["-t", str(DUR), "-i", audio, "-af", f"afade=t=out:st={DUR - 0.4}:d=0.4",
                    "-c:a", "aac", "-b:a", "160k"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-t", str(DUR), "-movflags", "+faststart", args.out]
        subprocess.run(cmd, check=True)
        print(args.out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
