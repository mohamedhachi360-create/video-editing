"""Layout and animation shared by render_video.py and build_capcut_project.py.

Positions are pixels on the canvas with y pointing down; rotation is degrees clockwise
(the same convention CapCut uses for rotation).
"""
import math
from dataclasses import dataclass

W, H = 1920, 1080
FPS = 30
DURATION = 7.0
N_FRAMES = round(DURATION * FPS)

LABELS = ("1", "2", "3")
CARD_W, CARD_H, CARD_RADIUS = 440, 560, 36
CARD_SPACING = 520
CARD_CENTERS = tuple((W / 2 + (i - 1) * CARD_SPACING, H / 2) for i in range(3))
NUMBER_EM_PX = 300
NUMBER_OFFSET_Y = -24  # number centre relative to its card centre

# Timings are whole frames so clip edges and keyframes land exactly on rendered frames.
INTRO_START = tuple((10 + 7 * i) / FPS for i in range(3))
INTRO_DUR = 27 / FPS
POP_DELAY, POP_DUR = 10 / FPS, 17 / FPS
SHINE_DELAY, SHINE_DUR = 23 / FPS, 24 / FPS
FOCUS_START = tuple((77 + 18 * i) / FPS for i in range(3))
FOCUS_DUR = 24 / FPS
OUTRO_START = tuple((163 + 5 * i) / FPS for i in range(3))
OUTRO_DUR = 23 / FPS
NUMBER_OUT_DUR = 10 / FPS


def clamp01(x):
    return max(0.0, min(1.0, x))


def smoothstep(a, b, x):
    p = clamp01((x - a) / (b - a))
    return p * p * (3 - 2 * p)


def ease_out_cubic(p):
    return 1 - (1 - p) ** 3


def ease_in_cubic(p):
    return p ** 3


def ease_in_out_cubic(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def ease_out_back(p, s=1.70158):
    q = p - 1
    return 1 + (s + 1) * q ** 3 + s * q ** 2


def ease_in_back(p, s=1.70158):
    return (s + 1) * p ** 3 - s * p ** 2


@dataclass(frozen=True)
class Transform:
    x: float
    y: float
    scale: float
    rotation: float
    alpha: float = 1.0


def card_span(i):
    return INTRO_START[i], OUTRO_START[i] + OUTRO_DUR


def number_span(i):
    return INTRO_START[i] + POP_DELAY, OUTRO_START[i] + NUMBER_OUT_DUR


def focus_amount(i, t):
    u = (t - FOCUS_START[i]) / FOCUS_DUR
    return math.sin(math.pi * u) ** 2 if 0 < u < 1 else 0.0


def shine_progress(i, t):
    u = (t - INTRO_START[i] - SHINE_DELAY) / SHINE_DUR
    return u if 0 < u < 1 else None


def card_transform(i, t):
    cx, cy = CARD_CENTERS[i]
    p = clamp01((t - INTRO_START[i]) / INTRO_DUR)
    y = cy + 200 * (1 - ease_out_cubic(p))
    scale = 0.6 + 0.4 * ease_out_back(p, 1.6)
    rotation = -8 * (1 - ease_out_cubic(p))
    alpha = ease_out_cubic(clamp01(p / 0.4))

    settle = INTRO_START[i] + INTRO_DUR
    float_env = smoothstep(settle - 0.2, settle + 0.6, t) * (1 - smoothstep(OUTRO_START[i] - 0.6, OUTRO_START[i], t))
    y += 7 * math.sin(2 * math.pi * 0.45 * (t - settle)) * float_env
    scale *= 1 + 0.07 * focus_amount(i, t)

    r = clamp01((t - OUTRO_START[i]) / OUTRO_DUR)
    y -= 260 * ease_in_back(r, 1.3)
    scale *= 1 - 0.3 * ease_in_cubic(r)
    rotation += 6 * ease_in_cubic(r)
    alpha *= 1 - smoothstep(0.2, 1.0, r)
    return Transform(cx, y, scale, rotation, alpha)


def number_local(i, t):
    """Scale and rotation of the number relative to its card."""
    q = clamp01((t - INTRO_START[i] - POP_DELAY) / POP_DUR)
    scale = ease_out_back(q, 2.4)
    rotation = -14 * (1 - ease_out_cubic(q))
    r = clamp01((t - OUTRO_START[i]) / NUMBER_OUT_DUR)
    scale *= 1 - ease_in_back(r, 1.7)
    return scale, rotation


def number_transform(i, t):
    card = card_transform(i, t)
    scale, rotation = number_local(i, t)
    theta = math.radians(card.rotation)
    offset = NUMBER_OFFSET_Y * card.scale
    return Transform(card.x - offset * math.sin(theta), card.y + offset * math.cos(theta),
                     card.scale * scale, card.rotation + rotation, card.alpha)
