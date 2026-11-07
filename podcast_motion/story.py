"""Scene builders shared by the part storyboards, and the sound cues they add."""
from gfx import CYAN, SOFT, WHITE
from scenes import SCX, SCY, SX1, SY0, SY1, Bubble, Card, Disc, Emoji, Pill, Portrait, Scene, Text, Words, row_x, vstack
from timeline import WORDS, cue_end

SFX = []  # (name, time, gain dB)


def sfx(name, t, db):
    SFX.append((name, round(t, 3), db))


def pause_after(text, after):
    """Midpoint of the pause that follows `text` - a good moment for a chapter change."""
    end = cue_end(text, after)
    nxt = next(w["s"] for w in WORDS if w["s"] > end)
    return round((end + nxt) / 2, 2)



def sticker(name, x, y, c, size=130, label=None, label_size=28, db=-20, **kw):
    els = [Emoji(name, x, y, c, size=size, **kw)]
    if label:
        els.append(Text(label, x, y + size * 0.62 + label_size * 0.75, c + 0.1, size=label_size, max_w=430,
                        until=kw.get("until")))
    if db is not None:
        sfx("pop", c, db)
    return els


def title_scene(start, end, title, cues, *, size=80, kicker=None, kicker_cue=None, kicker_color=CYAN, sub=None,
                sub_cue=None, sub_size=40, emoji_name=None, emoji_cue=None, emoji_size=160, more=(), extra=(),
                under=(), pulses=(), title_color=WHITE, colors=None):
    parts = []
    if emoji_name:
        parts.append((Emoji(emoji_name, SCX, 0, emoji_cue, size=emoji_size), emoji_size))
        sfx("pop", emoji_cue, -19)
    if kicker:
        parts.append((Pill(kicker, SCX, 0, kicker_cue, color=kicker_color, upper=False, size=28), 52))
    words = Words(title, SCX, 0, cues, size=size, color=title_color, pulses=pulses, colors=colors)
    parts.append((words, words.height))
    if sub:
        s = Text(sub, SCX, 0, sub_cue, size=sub_size, weight="Medium", color=SOFT, max_w=1300)
        parts.append((s, s.height))
    parts += list(more)
    for (el, _), y in zip(parts, vstack(SCY, [h for _, h in parts], gap=24)):
        el.y = y
    return Scene(start, end, list(under) + [el for el, _ in parts] + list(extra))


def icon_scene(start, end, items, *, heading=None, heading_cues=None, heading_size=56, kicker=None, kicker_cue=None,
               kicker_color=CYAN, footer=None, footer_cue=None, card_w=None, card_h=290, emoji_size=130,
               label_size=32, focus=None, extra=()):
    els, top = [], SY0 + 62
    if kicker:
        els.append(Pill(kicker, SCX, top, kicker_cue, color=kicker_color, upper=False, size=28))
        top += 66
    if heading:
        wd = Words(heading, SCX, 0, heading_cues, size=heading_size, max_w=1500)
        wd.y = top + wd.height / 2 - 12
        els.append(wd)
        top = wd.y + wd.height / 2 + 28
    n = len(items)
    cw = card_w or min(380, int((1600 - 40 * (n - 1)) / n))
    bottom = SY1 - (78 if footer else 28)
    cy = (top + bottom) / 2
    for i, (x, (name, label, c)) in enumerate(zip(row_x(n, cw + 40), items)):
        fo = [focus[1:]] if focus and focus[0] == i else ()
        els.append(Card(x, cy, c, w=cw, h=card_h, emoji_name=name, emoji_size=emoji_size, label=label,
                        label_size=label_size, focus=fo))
        sfx("pop", c, -20)
    if footer:
        els.append(Text(footer, SCX, SY1 - 46, footer_cue, size=36, weight="Medium", color=SOFT))
    return Scene(start, end, els + list(extra))


def chat_line(side, who, text, y, c, *, label=None, fill=(255, 255, 255), size=42, max_w=680):
    """One line of a chat: an avatar (host portrait or emoji) and a speech bubble."""
    ax = 200 if side == "left" else SX1 - 120
    av = Portrait(who[1], ax, y, c - 0.1, d=136) if who[0] == "host" else Disc(who[1], ax, y, c - 0.1, d=136)
    b = Bubble(text, 0, y, c, tail=side, fill=fill, size=size, max_w=max_w, anim=side)
    b.x = ax + 100 + b.w / 2 if side == "left" else ax - 100 - b.w / 2
    els = [av, b]
    if label:
        els.append(Text(label, ax, y + 94, c, size=22, color=SOFT, max_w=240))
    sfx("pop", c, -18)
    return els
