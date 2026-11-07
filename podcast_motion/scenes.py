"""Animated stage elements. A Scene is a time window holding elements that each appear on a cue."""
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gfx import (CYAN, GOLD, HOST_COLOR, INK, SOFT, WHITE, bubble, clamp01, ease_in_cubic, ease_in_out,
                 ease_out_back, ease_out_cubic, emoji, font, glow, icon_disc, lerp, mix, panel, pill, place,
                 portrait, pulse, scale_mask, smoothstep, solid, text_block, text_sprite,
                 white_silhouette, wrap)

STAGE = (80, 112, 1840, 736)
SX0, SY0, SX1, SY1 = STAGE
SCX, SCY = (SX0 + SX1) / 2, (SY0 + SY1) / 2
EXIT = 0.4  # scene exit animation
LEAD = 0.08  # elements start moving slightly before their word is spoken


def vstack(cy, heights, gap=24):
    total = sum(heights) + gap * (len(heights) - 1)
    y, out = cy - total / 2, []
    for h in heights:
        out.append(y + h / 2)
        y += h + gap
    return out


def row_x(n, spacing, cx=SCX):
    return [cx + (i - (n - 1) / 2) * spacing for i in range(n)]


class Scene:
    def __init__(self, start, end, els):
        self.start, self.end = start, end
        self.els = [e for e in els if e is not None]

    def draw(self, fr, t):
        if self.start <= t < self.end + EXIT:
            f = 1 - smoothstep(self.end, self.end + EXIT, t)
            for el in self.els:
                el.draw(fr, t, f)


class El:
    """Base element: appears at `cue` with an entrance animation and leaves at `until` or with its scene.

    moves: (t0, dur, x, y, scale, alpha) keyframes applied after the entrance.
    focus: (t0, t1) windows where the element is enlarged and glows.
    turn: (t0, dur, degrees) rotation.
    """
    anim, dur = "pop", 0.5

    def __init__(self, x, y, cue, *, until=None, anim=None, dur=None, float_amp=0.0, phase=None, rot0=None,
                 focus=(), shake=None, moves=(), turn=None):
        self.x, self.y, self.cue, self.until = x, y, cue - LEAD, until
        self.anim = anim or self.anim
        self.dur = dur or self.dur
        self.float_amp = float_amp
        self.phase = (x * 0.013 + y * 0.007) if phase is None else phase
        self.rot0 = rot0 if rot0 is not None else (-10 if self.anim == "pop" else 0)
        self.focus, self.shake, self.moves, self.turn = list(focus), shake, list(moves), turn

    def focus_amount(self, t):
        return max((smoothstep(a - 0.25, a + 0.1, t) * (1 - smoothstep(b - 0.1, b + 0.3, t))
                    for a, b in self.focus), default=0.0)

    def state(self, t, f):
        p = clamp01((t - self.cue) / self.dur)
        if p <= 0:
            return None
        q = clamp01((t - self.until) / 0.3) if self.until is not None else 0.0
        if q >= 1:
            return None
        x, y, sc, alpha = self.x, self.y, 1.0, 1.0
        for t0, d, mx, my, ms, ma in self.moves:
            k = ease_in_out(clamp01((t - t0) / d))
            if k <= 0:
                break
            x, y, sc, alpha = lerp(x, mx, k), lerp(y, my, k), lerp(sc, ms, k), lerp(alpha, ma, k)
        rot = 0.0
        a = self.anim
        if a == "pop":
            sc *= max(0.0, ease_out_back(p, 1.9))
            alpha *= clamp01(p * 3)
            rot = self.rot0 * (1 - ease_out_cubic(p))
        elif a == "rise":
            y += 34 * (1 - ease_out_cubic(p))
            alpha *= clamp01(p * 1.8)
        elif a == "fade":
            alpha *= smoothstep(0, 1, p)
        elif a in ("left", "right"):
            x += (-70 if a == "left" else 70) * (1 - ease_out_cubic(p))
            alpha *= clamp01(p * 1.8)
        elif a == "drop":
            y -= 90 * (1 - ease_out_back(p, 1.3))
            alpha *= clamp01(p * 2.5)
        elif a == "zoom":
            sc *= 0.6 + 0.4 * ease_out_cubic(p)
            alpha *= clamp01(p * 2)
        if q > 0:
            e = ease_in_cubic(q)
            alpha *= 1 - e
            sc *= 1 - 0.2 * e
        if self.turn:  # (start, duration, degrees): a full spin, e.g. "turns the wrong way"
            rot += self.turn[2] * ease_in_out(clamp01((t - self.turn[0]) / self.turn[1]))
        if self.float_amp:
            y += self.float_amp * math.sin(2 * math.pi * 0.3 * t + self.phase)
        fo = self.focus_amount(t) if self.focus else 0.0
        sc *= 1 + 0.07 * fo
        if self.shake and self.shake[0] <= t < self.shake[0] + self.shake[1]:
            u = (t - self.shake[0]) / self.shake[1]
            x += 14 * math.sin(u * 2 * math.pi * 5) * (1 - u)
        sc *= 0.94 + 0.06 * f
        y -= (1 - f) * 18
        return x, y, sc, rot, alpha * f, fo

    def not_before(self, t):
        self.cue = max(self.cue, t)

    def draw(self, fr, t, f):
        st = self.state(t, f)
        if st is not None:
            self.draw_at(fr, t, *st)

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        place(fr, self.sprite(t), x, y, sc, rot, alpha)

    def sprite(self, t):
        raise NotImplementedError


class Emoji(El):
    def __init__(self, name, x, y, cue, size=150, flash=None, **kw):
        kw.setdefault("float_amp", 5.0)
        super().__init__(x, y, cue, **kw)
        self.name, self.size, self.flash = name, size, flash

    def sprite(self, t):
        return emoji(self.name, self.size)

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        place(fr, self.sprite(t), x, y, sc, rot, alpha)
        if self.flash:  # e.g. "my brain went completely white"
            t0, t1 = self.flash
            k = smoothstep(t0, t0 + 0.25, t) * (1 - smoothstep(t1 - 0.3, t1, t))
            if k > 0:
                place(fr, white_silhouette(self.name, self.size), x, y, sc, rot, alpha * k * 0.92)


class Text(El):
    anim = "rise"

    def __init__(self, text, x, y, cue, size=40, weight="SemiBold", color=WHITE, max_w=1400, align="center",
                 anchor="center", **kw):
        super().__init__(x, y, cue, **kw)
        self.args = (text, size, weight, color, max_w, 1.25, align)
        self.anchor = anchor
        self.height = sum(len(wrap(p, size, weight, max_w)) for p in text.split("\n")) * size * 1.25

    def sprite(self, t):
        return text_block(*self.args)

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        img = self.sprite(t)
        if self.anchor == "left":
            x += img.width / 2 - self.args[1] * 0.45
        place(fr, img, x, y, sc, rot, alpha)


class Pill(El):
    anim = "rise"

    def __init__(self, text, x, y, cue, size=26, color=CYAN, fg=WHITE, bg_a=0.24, upper=True, **kw):
        super().__init__(x, y, cue, **kw)
        self.args = (text, size, fg, color, bg_a, 0.7, upper)

    def sprite(self, t):
        return pill(*self.args)


class Words(El):
    """Kinetic headline: each word rises in on its own cue; `pulses` make words bounce when spoken again."""

    def __init__(self, text, x, y, cues, size=80, weight="Bold", color=WHITE, max_w=1500, line_h=1.12,
                 pulses=(), pulse_color=GOLD, colors=None, **kw):
        lines = [line for para in text.split("\n") for line in wrap(para, size, weight, max_w)]
        n = sum(len(line.split()) for line in lines)
        if not isinstance(cues, (list, tuple)):
            cues = [cues + 0.09 * k for k in range(n)]
        assert len(cues) == n, (text, n, len(cues))
        super().__init__(x, y, cues[0], anim="rise", **kw)
        f = font(weight, size)
        space = f.getlength(" ")
        self.size, self.weight, self.color = size, weight, color
        self.pulses = [list(p) for p in pulses]
        assert all(len(p) == n for p in self.pulses), text
        self.pulse_color, self.colors = pulse_color, colors or {}
        lh = size * line_h
        self.height = lh * len(lines)
        self.items, widths = [], []
        k = 0
        for li, line in enumerate(lines):
            ws = line.split()
            ww = [f.getlength(w) for w in ws]
            lw = sum(ww) + space * (len(ws) - 1)
            widths.append(lw)
            xx = -lw / 2
            for w, wd in zip(ws, ww):
                self.items.append((w, xx + wd / 2, -self.height / 2 + lh / 2 + li * lh, cues[k] - LEAD, k))
                xx += wd + space
                k += 1
        self.width = max(widths)

    def not_before(self, t):
        self.cue = max(self.cue, t)
        self.items = [(w, dx, dy, max(c, t), k) for w, dx, dy, c, k in self.items]

    def draw(self, fr, t, f):
        q = clamp01((t - self.until) / 0.3) if self.until is not None else 0.0
        if q >= 1:
            return
        out = 1 - ease_in_cubic(q)
        flo = self.float_amp * math.sin(2 * math.pi * 0.3 * t + self.phase) if self.float_amp else 0.0
        fo = self.focus_amount(t) if self.focus else 0.0
        for w, dx, dy, c, k in self.items:
            p = clamp01((t - c) / 0.45)
            if p <= 0:
                continue
            bump = max([pulse(t - pl[k]) for pl in self.pulses] + [fo])
            lvl = round(bump * 4) / 4
            col = self.colors.get(k, self.color)
            if lvl:
                col = mix(col, self.pulse_color, lvl)
            sc = (0.92 + 0.08 * ease_out_back(p, 2.2)) * (1 + 0.12 * bump) * (0.94 + 0.06 * f) * (0.85 + 0.15 * out)
            if p >= 1 and not lvl and f >= 1 and out >= 1:
                sc = 1.0
            y = self.y + dy + self.size * 0.35 * (1 - ease_out_cubic(p)) - (1 - f) * 18 + flo
            place(fr, text_sprite(w, self.size, self.weight, col), self.x + dx * (0.94 + 0.06 * f), y, sc, 0,
                  clamp01(p * 2) * f * out)


class Card(El):
    """Glass card with an emoji, optional big word and a label."""

    def __init__(self, x, y, cue, w=340, h=300, emoji_name=None, emoji_size=130, label=None, label_size=32,
                 big=None, big_size=64, big_color=WHITE, accent=CYAN, fill_a=0.12, top=None, **kw):
        super().__init__(x, y, cue, **kw)
        self.w, self.h, self.accent, self.fill_a = w, h, accent, fill_a
        self.emoji_name, self.emoji_size, self.label, self.label_size = emoji_name, emoji_size, label, label_size
        self.big, self.big_size, self.big_color, self.top = big, big_size, big_color, top
        self._img = None

    def sprite(self, t):
        if self._img is None:
            img = panel(self.w, self.h, 30, WHITE, self.fill_a, WHITE, 0.42).copy()
            parts = []
            if self.top:
                parts.append((text_sprite(self.top, 24, "SemiBold", self.accent, tracking=3), 30))
            if self.emoji_name:
                parts.append((emoji(self.emoji_name, self.emoji_size), self.emoji_size))
            if self.big:
                parts.append((text_sprite(self.big, self.big_size, "Bold", self.big_color), self.big_size * 1.2))
            if self.label:
                tb = text_block(self.label, self.label_size, "SemiBold", WHITE, self.w - 40)
                parts.append((tb, len(wrap(self.label, self.label_size, "SemiBold", self.w - 40)) * self.label_size * 1.25))
            for (spr, _), y in zip(parts, vstack(img.height / 2, [h for _, h in parts], gap=12)):
                img.alpha_composite(spr, (round(img.width / 2 - spr.width / 2), round(y - spr.height / 2)))
            self._img = img
        return self._img

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        if fo > 0.01:
            place(fr, glow(self.w, self.h, 30, self.accent), x, y, sc, rot, alpha * fo)
        place(fr, self.sprite(t), x, y, sc, rot, alpha)


class Bubble(El):
    def __init__(self, text, x, y, cue, tail="left", fill=WHITE, text_color=INK, size=38, max_w=680,
                 weight="SemiBold", **kw):
        super().__init__(x, y, cue, **kw)
        self.text, self.tail, self.fill, self.text_color = text, tail, fill, text_color
        self.size, self.max_w, self.weight = size, max_w, weight
        lines = wrap(text, size, weight, max_w)
        self.w = round(max(font(weight, size).getlength(line) for line in lines) + 64)
        self.h = round(len(lines) * size * 1.3 + 36)
        self._img = None

    def sprite(self, t):
        if self._img is None:
            img = bubble(self.w, self.h, self.tail, self.fill).copy()
            tb = text_block(self.text, self.size, self.weight, self.text_color, self.max_w, 1.3, shadow=0)
            img.alpha_composite(tb, ((img.width - tb.width) // 2, (img.height - tb.height) // 2 + 2))
            self._img = img
        return self._img


class Portrait(El):
    def __init__(self, name, x, y, cue, d=220, **kw):
        super().__init__(x, y, cue, **kw)
        self.name, self.d = name, d

    def sprite(self, t):
        return portrait(self.name, self.d, HOST_COLOR[self.name], 6)


class Disc(El):
    def __init__(self, name, x, y, cue, d=120, **kw):
        super().__init__(x, y, cue, **kw)
        self.name, self.d = name, d

    def sprite(self, t):
        return icon_disc(self.name, self.d)


@lru_cache(maxsize=8)
def arrow_sprite(length, color):
    ss, th, head = 3, 14, 30
    w, h = length + 24, 2 * head + 24
    m = Image.new("L", (w * ss, h * ss), 0)
    d = ImageDraw.Draw(m)
    cy, x0, x1 = h * ss / 2, 12 * ss, (12 + length) * ss
    d.rounded_rectangle((x0, cy - th / 2 * ss, x1 - head * ss + 4 * ss, cy + th / 2 * ss), radius=th / 2 * ss, fill=255)
    d.polygon([(x1 - head * ss, cy - head * ss), (x1, cy), (x1 - head * ss, cy + head * ss)], fill=255)
    return solid(color, m.resize((w, h), Image.Resampling.LANCZOS))


class Arrow(El):
    anim = "left"

    def __init__(self, x, y, cue, length=110, color=SOFT, **kw):
        super().__init__(x, y, cue, **kw)
        self.length, self.color = length, color

    def sprite(self, t):
        return arrow_sprite(self.length, self.color)


# ---------- the door ----------

@lru_cache(maxsize=256)
def door_sprite(q, w, h, light10):
    """A door hinged on its left edge; q/40 is how far it is open, warm light spills out when open."""
    op, light = q / 40, light10 / 10
    ss, pad = 2, 90
    cw, ch = (w + 2 * pad) * ss, (h + 2 * pad) * ss
    x0, y0, x1, y1 = pad * ss, pad * ss, (pad + w) * ss, (pad + h) * ss
    k = op * light
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

    def mask(draw_fn):
        m = Image.new("L", (cw, ch), 0)
        draw_fn(ImageDraw.Draw(m))
        return m

    if k > 0.01:
        spill = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
        ImageDraw.Draw(spill).rectangle((pad, pad, pad + w, pad + h), fill=255)
        spill = spill.filter(ImageFilter.GaussianBlur(38)).resize((cw, ch), Image.Resampling.BILINEAR)
        img.alpha_composite(solid((255, 210, 120), scale_mask(spill, 0.9 * k)))
        floor = mask(lambda d: d.polygon([(x0, y1), (x1, y1), (x1 + 60 * ss, y1 + 60 * ss),
                                          (x0 - 60 * ss, y1 + 60 * ss)], fill=255))
        img.alpha_composite(solid((255, 220, 150), scale_mask(floor.filter(ImageFilter.GaussianBlur(14 * ss)), 0.45 * k)))
    img.alpha_composite(solid(mix((12, 24, 74), (255, 238, 196), k), mask(lambda d: d.rectangle((x0, y0, x1, y1), fill=255))))
    fw = 12 * ss
    frame = mask(lambda d: d.rectangle((x0 - fw, y0 - fw, x1 + fw, y1 + 2), fill=255))
    frame.paste(0, (x0, y0, x1, y1 + 2))
    img.alpha_composite(solid((236, 242, 255), frame))

    ang = math.radians(op * 80)
    pw = (x1 - x0) * math.cos(ang)
    dd = 30 * ss * math.sin(ang)

    def pt(u, v):
        top, bot = y0 - dd * u, y1 + dd * u
        return (x0 + pw * u, top + (bot - top) * v)

    if pw > 2:
        shade = 1 - 0.3 * math.sin(ang)
        img.alpha_composite(solid(tuple(round(c * shade) for c in (64, 122, 255)),
                                  mask(lambda d: d.polygon([pt(0, 0), pt(1, 0), pt(1, 1), pt(0, 1)], fill=255))))
        if pw > 30 * ss:
            for u0, u1, v0, v1 in ((0.17, 0.83, 0.07, 0.45), (0.17, 0.83, 0.55, 0.93)):
                poly = [pt(u0, v0), pt(u1, v0), pt(u1, v1), pt(u0, v1)]
                img.alpha_composite(solid((255, 255, 255), scale_mask(
                    mask(lambda d: d.polygon(poly, outline=255, width=3 * ss)), 0.35)))
            kx, ky = pt(0.86, 0.53)
            r = 9 * ss * max(0.5, math.cos(ang))
            img.alpha_composite(solid(GOLD, mask(lambda d: d.ellipse((kx - r, ky - 9 * ss, kx + r, ky + 9 * ss), fill=255))))
    return img.resize((w + 2 * pad, h + 2 * pad), Image.Resampling.LANCZOS)


class Door(El):
    anim = "zoom"

    def __init__(self, x, y, cue, keys=((0, 0.8),), w=220, h=340, light=1.0, **kw):
        super().__init__(x, y, cue, **kw)
        self.keys, self.w, self.h, self.light = list(keys), w, h, light

    def openness(self, t):
        v = self.keys[0][1]
        for tk, val in self.keys[1:]:
            v += (val - v) * ease_in_out(clamp01((t - tk) / 0.8))
        return v

    def sprite(self, t):
        return door_sprite(round(self.openness(t) * 40), self.w, self.h, round(self.light * 10))


# ---------- effects ----------

@lru_cache(maxsize=4)
def rays_sprite(r, color):
    size = 2 * r
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    n = 16
    for k in range(n):
        a0 = 2 * math.pi * k / n
        a1 = a0 + math.pi / n
        d.polygon([(r, r), (r + 2 * r * math.cos(a0), r + 2 * r * math.sin(a0)),
                   (r + 2 * r * math.cos(a1), r + 2 * r * math.sin(a1))], fill=255)
    yy, xx = np.mgrid[0:size, 0:size]
    fall = np.clip(1 - np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r, 0, 1) ** 1.4
    a = np.asarray(m, np.float32) / 255 * fall * 0.2 * 255
    return solid(color, Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)))


class Rays(El):
    anim = "fade"
    dur = 0.8

    def __init__(self, x, y, cue, r=520, color=GOLD, **kw):
        super().__init__(x, y, cue, **kw)
        self.r, self.color = r, color

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        place(fr, rays_sprite(self.r, self.color), x, y, sc, t * 6, alpha)


class Rain(El):
    anim = "drop"

    def __init__(self, x, y, cue, width=240, height=250, **kw):
        super().__init__(x, y, cue, **kw)
        rng = random.Random(7)
        self.width, self.height = width, height
        self.drops = [(rng.uniform(-width / 2, width / 2), rng.uniform(0, height), rng.uniform(420, 560))
                      for _ in range(28)]

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        layer = Image.new("L", (self.width + 20, self.height), 0)
        d = ImageDraw.Draw(layer)
        for dx, off, speed in self.drops:
            yy = (off + (t - self.cue) * speed) % self.height
            fade = min(1, yy / 40, (self.height - yy) / 50)
            d.line((dx + self.width / 2 + 10, yy, dx + self.width / 2 + 6, yy + 22), fill=round(235 * fade), width=4)
        place(fr, solid((170, 220, 255), layer), x, y + 60 + self.height / 2, 1, 0, alpha)
        place(fr, emoji("cloud_with_rain", 170), x, y, sc, rot, alpha)


class Hearts(El):
    anim = "fade"

    def __init__(self, x, y, cue, n=16, width=1300, **kw):
        super().__init__(x, y, cue, **kw)
        rng = random.Random(3)
        self.items = [(rng.uniform(-width / 2, width / 2), cue + k * 0.16, rng.choice((60, 76, 92)),
                       rng.uniform(0, 6.28)) for k in range(n)]

    def draw(self, fr, t, f):
        for dx, start, size, ph in self.items:
            age = t - start
            if 0 <= age <= 2.4:
                a = smoothstep(0, 0.25, age) * (1 - smoothstep(1.7, 2.4, age)) * f
                place(fr, emoji("red_heart", size, 0.25), self.x + dx + 26 * math.sin(age * 3 + ph),
                      self.y - age * 170, 0.6 + 0.4 * ease_out_back(clamp01(age / 0.4)), 0, a)


class Button(El):
    """Like / subscribe / share button that gets pressed at `click`."""

    def __init__(self, x, y, cue, click, emoji_name, label, color, w=380, h=124, **kw):
        super().__init__(x, y, cue, **kw)
        self.click, self.emoji_name, self.label, self.color, self.w, self.h = click, emoji_name, label, color, w, h
        self._imgs = {}

    def _img(self, pressed):
        if pressed not in self._imgs:
            base = panel(self.w, self.h, self.h // 2, self.color if pressed else WHITE, 0.95 if pressed else 0.12,
                         WHITE, 0.6, 2, 0.4, 0.3).copy()
            e = emoji(self.emoji_name, 74, 0.3)
            ts = text_sprite(self.label, 44, "Bold", WHITE)
            total = 74 + 18 + (ts.width - 40)
            ex = base.width / 2 - total / 2 + 37
            base.alpha_composite(e, (round(ex - e.width / 2), round(base.height / 2 - e.height / 2)))
            tx = ex + 37 + 18 + (ts.width - 40) / 2
            base.alpha_composite(ts, (round(tx - ts.width / 2), round(base.height / 2 - ts.height / 2) + 2))
            self._imgs[pressed] = base
        return self._imgs[pressed]

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        u = (t - self.click) / 0.5
        if 0 <= u < 1:
            sc *= 1 - 0.12 * math.sin(math.pi * min(1, u * 2.2)) + 0.05 * math.sin(math.pi * u) * (u > 0.45)
        k = smoothstep(self.click, self.click + 0.18, t)
        place(fr, self._img(False), x, y, sc, rot, alpha * (1 - k))
        if k > 0:
            place(fr, self._img(True), x, y, sc, rot, alpha * k)
        v = (t - self.click) / 0.7
        if 0 <= v < 1:
            place(fr, glow(self.w, self.h, self.h // 2, self.color, 14), x, y, sc * (1 + 0.35 * v), 0, alpha * (1 - v))


class Counter(El):
    """Elevator floor display that counts up."""
    anim = "zoom"

    def __init__(self, x, y, cue, floors, w=360, h=300, **kw):
        super().__init__(x, y, cue, **kw)
        self.floors, self.w, self.h = floors, w, h
        self._base = None

    def base(self):
        if self._base is None:
            img = panel(self.w, self.h, 34, (6, 14, 50), 0.75, WHITE, 0.45).copy()
            label = text_sprite("FLOOR", 26, "SemiBold", SOFT, tracking=6)
            img.alpha_composite(label, ((img.width - label.width) // 2 + 18, 40 + 26 - label.height // 2 + 6))
            tri = Image.new("L", img.size, 0)
            cx = img.width // 2 - label.width // 2 + 2
            ImageDraw.Draw(tri).polygon([(cx - 13, 40 + 44), (cx + 13, 40 + 44), (cx, 40 + 22)], fill=255)
            img.alpha_composite(solid(GOLD, tri))
            self._base = img
        return self._base

    def draw_at(self, fr, t, x, y, sc, rot, alpha, fo):
        place(fr, self.base(), x, y, sc, rot, alpha)
        cur = max((k for k, (tk, _) in enumerate(self.floors) if tk - LEAD <= t), default=None)
        if cur is None:
            return
        p = clamp01((t - self.floors[cur][0] + LEAD) / 0.28)
        e = ease_out_cubic(p)
        num = lambda n: text_sprite(str(n), 170, "Bold", GOLD if n == self.floors[-1][1] else WHITE)
        place(fr, num(self.floors[cur][1]), x, y + 30 + 50 * (1 - e) * sc, sc, 0, alpha * e)
        if cur > 0 and p < 1:
            place(fr, num(self.floors[cur - 1][1]), x, y + 30 - 50 * e * sc, sc, 0, alpha * (1 - e))
