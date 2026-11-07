"""What appears on the stage and when. Cues are looked up in the transcript so visuals land on the words."""
from gfx import CYAN, GOLD, GREEN, HOST_COLOR, RED, SOFT, WHITE
from scenes import (SCX, SCY, SX1, SY0, SY1, Arrow, Bubble, Button, Card, Counter, Disc, Door, Emoji, Hearts, Pill,
                    Portrait, Rain, Rays, Scene, Text, Words, row_x, vstack)
from timeline import WORDS, cue, cue_end, spoken

BELLA, AARON = HOST_COLOR["bella"], HOST_COLOR["aaron"]
END = 304.0  # the voice ends at 299.4 s; a short end card follows
HOST_APPEAR = {"bella": 0.0, "aaron": cue("Hello, Bella")-0.35}
SFX = []  # (name, time, gain dB)


def sfx(name, t, db):
    SFX.append((name, round(t, 3), db))


def pause_after(text, after):
    """Midpoint of the pause that follows `text` - a good moment for a chapter change."""
    end = cue_end(text, after)
    nxt = next(w["s"] for w in WORDS if w["s"] > end)
    return round((end + nxt) / 2, 2)


CHAPTERS = [
    (0.0, "Welcome"),
    (pause_after("And how are you?", 22), "The elevator moment"),
    (pause_after("That's good news.", 113), "Small talk is a skill"),
    (pause_after("Yes, I need this.", 143), "A small request"),
    (pause_after("Okay, now let's start.", 167), "What is small talk?"),
    (pause_after("I closed the door.", 226), "Small words, big doors"),
    (pause_after("It's just a little shy.", 276), "5 easy ways"),
]
CH = [c for c, _ in CHAPTERS]


# ---------- builders ----------

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


# ---------- scenes ----------

SCENES = []
add = SCENES.append

# 1 Welcome
add(title_scene(0.0, 7.45, "Enjoy English Talks", spoken("Enjoy English Talks"), size=104,
                kicker="Welcome back to", kicker_cue=cue("welcome"),
                sub="where every conversation helps you learn", sub_cue=cue("where every"),
                emoji_name="headphone", emoji_cue=0.25, emoji_size=170,
                under=[Rays(SCX, SCY, cue("Enjoy"), r=560, color=CYAN)]))
sfx("chime", cue("Talks", 2) + 0.15, -18)

t_aaron = cue("I'm Aaron", 9)
add(Scene(7.45, 12.5, [
    Pill("Your hosts", SCX, SY0 + 62, 7.55, size=28),
    Portrait("bella", 650, 372, 7.55, d=250),
    Text("Bella", 650, 556, 7.7, size=52, weight="Bold", color=BELLA),
    Text("&", SCX, 372, t_aaron, size=72, weight="Bold", color=SOFT),
    Portrait("aaron", 1270, 372, t_aaron, d=250),
    Text("Aaron", 1270, 556, t_aaron + 0.12, size=52, weight="Bold", color=AARON),
    Bubble("How are you today, Bella?", 1270, 664, cue("How are you today"), tail="up", fill=AARON, size=32),
]))
sfx("pop", 7.55, -18)
sfx("pop", t_aaron, -18)

add(icon_scene(12.5, CH[1] - 0.1, [
    ("sunrise", "Woke up early", cue("woke", 15)),
    ("potted_plant", "“Good morning, plants!”", cue("plants", 19)),
    ("teacup_without_handle", "A cup of tea", cue("cup", 21)),
], heading="Bella's slow, quiet morning", heading_cues=cue("I'm really good", 12)))

# 2 The elevator moment
s = title_scene(CH[1] + 0.1, 32.95, "Something happened yesterday…", spoken("something happened yesterday", 25),
                emoji_name="anxious_face_with_sweat", emoji_cue=cue("I'm okay", 24),
                sub="…and I still feel a little strange about it.", sub_cue=cue("I still feel", 27))
s.els += sticker("red_question_mark", 1590, 300, cue("what happened", 30), size=120)
add(s)

add(icon_scene(32.95, 42.7, [
    ("elevator", "In the elevator", cue("elevator", 33)),
    ("office_building", "At work", cue("work", 34)),
    ("office_worker", "The new co-worker", cue("coworker", 35)),
    ("pizza", "The friendly one from Friday lunch", cue("Friday", 37)),
], heading="Aaron's elevator moment", heading_cues=33.1, focus=(2, cue("Yes, I remember", 39), cue_end("him?", 41))))
sfx("ding_elevator", cue("elevator", 33), -17)

t_white = cue("white", 48)
add(Scene(42.7, 56.15, [
    Pill("That's the problem", SCX, SY0 + 50, cue("That's the problem", 43), color=AARON, upper=False, size=28),
    *chat_line("left", ("emoji", "office_worker"), "Hey Aaron, how's it going?", 252, cue("hey Aaron", 44),
               label="New co-worker"),
    *sticker("brain", SCX, 432, cue("brain", 46), size=130, label="My brain went completely white!",
             flash=(t_white, t_white + 1.8)),
    *chat_line("right", ("host", "aaron"), "Yes.", 616, cue("yes.", 49), fill=AARON),
    Emoji("cross_mark", 1480, 578, cue("Yes?", 51), size=72, float_amp=0),
]))
sfx("scratch", cue_end("yes.", 49) + 0.12, -13)

floors = [(cue("Then we stood", 57) + 0.8 * k, k + 1) for k in range(6)]
add(Scene(56.15, 65.2, [
    Emoji("elevator", 380, 400, cue("I said yes", 56), size=200),
    Counter(760, 400, cue("I said yes", 56) + 0.15, floors),
    Words("6 floors…", 1390, 300, spoken("six floors", 58), size=100),
    Emoji("hourglass_not_done", 1135, 512, cue("longest", 62), size=96),
    Text("The longest elevator ride of my life", 1200, 520, cue("longest", 62), size=40, max_w=560, align="left",
         anchor="left"),
]))
sfx("pop", cue("longest", 62), -20)
sfx("ding_elevator", cue_end("life.", 63) + 0.1, -12)

add(title_scene(65.2, 69.85, "I'm sorry, but that's a little funny", spoken("I'm sorry, but that's a little funny", 66),
                size=78, kicker="Oh, Aaron…", kicker_cue=cue("Oh, Aaron", 65), kicker_color=BELLA,
                emoji_name="grinning_face_with_sweat", emoji_cue=cue("funny", 68)))

t_talked = cue_end("Nobody talked", 76)
add(icon_scene(69.85, 78.45, [
    ("input_numbers", "I looked at the numbers", cue("numbers", 74)),
    ("running_shoe", "He looked at his shoes", cue("shoes", 75)),
    ("zipper-mouth_face", "Nobody talked", cue("Nobody", 76)),
], heading="In the elevator, it was not funny", heading_cues=spoken("in the elevator, it was not funny", 71),
    kicker="It's funny now…", kicker_cue=cue("It's funny now", 70), kicker_color=AARON,
    extra=sticker("cricket", 1730, 668, t_talked, size=84, db=None)))
sfx("crickets", t_talked + 0.05, -14)

s = title_scene(78.45, 88.8, "This happens to so many people", spoken("this happens to so many people", 79),
                size=76, emoji_name="busts_in_silhouette", emoji_cue=cue("this happens", 79),
                sub="Not only English learners.", sub_cue=cue("Not only English", 81),
                more=[(Pill("Everyone has an elevator moment", SCX, 0, cue("Everyone has", 83), color=GOLD,
                            upper=False, size=30), 56)])
s.els += sticker("thinking_face", 1640, 300, cue("Really?", 86), size=110)
add(s)

add(Scene(88.8, 100.2, [
    Pill("Even me!", SCX, SY0 + 50, cue("Even me", 89), color=BELLA, upper=False, size=28),
    *sticker("woman_dancing", 1640, 238, cue("dance class", 91), size=118, label="At my dance class"),
    *chat_line("left", ("emoji", "man_dancing"), "How was your weekend?", 298, cue("asked me", 93),
               label="The nice man"),
    *chat_line("right", ("host", "bella"), "It was good.", 492, cue("I said, it was good", 95), fill=BELLA),
    *sticker("face_without_mouth", 560, 640, cue("nothing", 97), size=96),
    Text("…and then nothing. My mouth just stopped.", 640, 640, cue("nothing", 97), size=36, max_w=900,
         align="left", anchor="left"),
]))

t_turn = cue("turns", 101)
add(Scene(100.2, 110.5, [
    Emoji("man_dancing", 330, 292, cue("The man who", 100), size=150, turn=(t_turn, 1.0, -360)),
    Text("He always turns the wrong way", 330, 424, cue("always", 100), size=30, max_w=380),
    Pill("That's him!", SCX, 300, cue("That's him", 103), color=BELLA, upper=False, size=30),
    *sticker("face_with_tears_of_joy", 1560, 270, cue("laughed", 104), size=110, label="He laughed"),
    *chat_line("left", ("emoji", "man_dancing"), "Okay, see you next week!", 600, cue("okay, see you", 105)),
    Emoji("waving_hand", 910, 590, cue("next week", 106), size=84, rot0=-30),
    Text("So I know the feeling.", 1480, 600, cue("So I know", 108), size=40, weight="SemiBold", color=BELLA),
]))

s = title_scene(110.5, CH[2] - 0.1, "It's not only my brain", spoken("it's not only my brain", 111), size=84,
                emoji_name="brain", emoji_cue=cue("Hmm.", 110), sub="That's good news!",
                sub_cue=cue("That's good news", 113))
s.els += sticker("check_mark_button", s.els[0].x + 95, 0, cue("good news", 113), size=80, db=None)
s.els[-1].y = s.els[0].y + 50
add(s)
sfx("correct", cue("good news", 113), -15)

# 3 Small talk is a skill
add(icon_scene(CH[2] + 0.1, 125.45, [
    ("memo", "We don't plan small talk", cue("plan", 118)),
    ("sparkles", "We think it just happens", cue("just happens", 120)),
    ("guitar", "Small talk is a skill, like the guitar", cue("skill", 123)),
], heading="The problem is simple", heading_cues=spoken("the problem is simple", 116),
    kicker="It's not only your brain", kicker_cue=cue("It's not only your brain", 114), kicker_color=BELLA))

s = title_scene(125.45, 129.05, "Please don't talk about the F chord today!",
                spoken("please don't talk about the F chord today", 126), size=76,
                emoji_name="weary_face", emoji_cue=cue("Oh, please", 125))
s.els += sticker("guitar", 1600, 300, cue("chord", 127), size=150, rot0=-30, db=-20)
s.els += sticker("musical_notes", 1730, 200, cue("chord", 127) + 0.25, size=84, db=None)
add(s)

t_topic = cue("small talk", 135)
add(Scene(129.05, CH[3] - 0.1, [
    Rays(SCX, 292, t_topic, r=470, color=GOLD),
    Pill("Today's topic", SCX, SY0 + 58, cue("great topic", 131), size=28),
    Words("SMALL TALK", SCX, 286, spoken("small talk", 135), size=132, color=GOLD),
    Text("Short, friendly conversations…", SCX, 398, cue("short, friendly", 137), size=42, weight="Medium",
         color=SOFT),
    Card(600, 580, cue("work", 139), w=330, h=230, emoji_name="briefcase", emoji_size=100, label="At work"),
    Card(960, 580, cue("shop", 140), w=330, h=230, emoji_name="shopping_cart", emoji_size=100, label="In the shop"),
    Card(1320, 580, cue("elevator", 141), w=330, h=230, emoji_name="elevator", emoji_size=100,
         label="In the elevator", accent=AARON, focus=[(cue("The elevator!", 142), CH[3])]),
]))
sfx("chime", t_topic, -12)
for c in (cue("work", 139), cue("shop", 140), cue("elevator", 141)):
    sfx("pop", c, -20)

# 4 A small request
clicks = [cue("like button", 152) + 0.1, cue("subscribe", 154) + 0.35, cue("share", 158) + 0.45]
add(Scene(CH[3] + 0.1, CH[4] - 0.1, [
    Hearts(SCX, 730, cue("love our listeners", 164) - 0.15),
    Emoji("megaphone", 640, 196, cue("But first", 146), size=116),
    Words("A small request", 1050, 196, spoken("a small request", 147), size=72),
    Button(520, 400, cue("if you like", 150), clicks[0], "thumbs_up", "Like", (52, 120, 246)),
    Button(960, 400, cue("subscribe", 154) - 0.15, clicks[1], "bell", "Subscribe", (226, 48, 72), w=420),
    Button(1400, 400, cue("share", 158) - 0.1, clicks[2], "outbox_tray", "Share", (34, 168, 108)),
    Words("Thank you!", SCX, 556, spoken("thank you", 161), size=64, color=GOLD),
    Text("It helps us so much.", SCX, 622, cue("It helps us", 162), size=36, weight="Medium", color=SOFT),
    Pill("We love our listeners", SCX, 688, cue("We love", 164), color=RED, upper=False, size=28),
]))
for c in clicks:
    sfx("click", c, -9)
for c in (cue("if you like", 150), cue("subscribe", 154) - 0.15, cue("share", 158) - 0.1):
    sfx("pop", c, -20)

# 5 What is small talk?
s = title_scene(CH[4] + 0.1, 177.05, "What is small talk?", spoken("what is small talk", 170), size=100,
                emoji_name="thinking_face", emoji_cue=cue("Okay, so what", 169),
                sub="I know the words “small” and “talk”… but what is it really?", sub_cue=cue("I know the words", 172))
s.els += sticker("red_question_mark", 1600, 300, cue("really?", 175), size=130)
add(s)

add(icon_scene(177.05, 188.05, [
    ("sun_behind_cloud", "The weather", cue("weather", 182)),
    ("calendar", "The weekend", cue("weekend", 182)),
    ("spaghetti", "Food", cue("food", 183)),
    ("briefcase", "Work", cue("work", 184)),
], heading="Small talk is a short, easy conversation about simple things",
    heading_cues=spoken("small talk is a short, easy conversation about simple things", 177),
    footer="Nothing deep, nothing serious.", footer_cue=cue("Nothing deep", 185), card_h=250, emoji_size=116))

add(Scene(188.05, 200.5, [
    Pill("So it's not important talk?", SCX, SY0 + 50, cue("So it's not important", 188), color=AARON,
         upper=False, size=28),
    Words("It's not important talk, but it is important.", SCX, 236,
          spoken("it's not important talk, but it is important", 189), size=60, colors={6: GOLD, 7: GOLD}),
    Pill("That's the secret", SCX, 326, cue("That's the secret", 194), color=GOLD, upper=False, size=28),
    Card(610, 548, cue("words are small", 196), w=520, h=290, big="words", big_size=36,
         label="The words are small", accent=CYAN),
    Text("but", SCX, 548, cue("but the feeling", 197), size=40, weight="Bold", color=SOFT),
    Card(1310, 548, cue("feeling", 197), w=520, h=290, emoji_name="red_heart", emoji_size=110, big="FEELING",
         big_size=64, label="The feeling is BIG", accent=RED, focus=[(cue("big.", 198), CH[4] + 31)]),
]))
sfx("pop", cue("words are small", 196), -20)
sfx("pop", cue("feeling", 197), -18)

add(Scene(200.5, 212.15, [
    Pill("Explain that, please", SCX, SY0 + 50, cue("Explain that", 200), color=AARON, upper=False, size=28),
    Emoji("calendar", 560, 250, cue("how was your weekend", 203), size=90),
    Bubble("How was your weekend?", SCX, 250, cue("how was your weekend", 203), tail="down", size=40),
    Text("…is not really about the weekend.", SCX, 350, cue("not really asking", 205), size=34, weight="Medium",
         color=SOFT),
    Pill("It really means", SCX, 410, cue("You're saying", 207), size=28),
    Card(560, 596, cue("I see you", 208), w=340, h=220, emoji_name="eyes", emoji_size=96, label="I see you."),
    Card(960, 596, cue("You matter", 209), w=340, h=220, emoji_name="glowing_star", emoji_size=96,
         label="You matter."),
    Card(1360, 596, cue("I'm friendly", 210), w=340, h=220, emoji_name="smiling_face_with_smiling_eyes",
         emoji_size=96, label="I'm friendly."),
]))
for c in (cue("I see you", 208), cue("You matter", 209), cue("I'm friendly", 210)):
    sfx("pop", c, -19)

t_door = cue("the weekend is the door", 217)
t_closed = cue("closed the door", 226)
add(Scene(212.15, CH[5] - 0.1, [
    Words("The weekend is not the point.", SCX, 176, spoken("the weekend is not the point", 213), size=56),
    Pill("Exactly!", SCX, 258, cue("Exactly", 216), color=GREEN, upper=False, size=30, until=cue("The weekend", 221)),
    Door(600, 470, t_door, keys=[(0, 0.8), (t_closed, 0.0)], w=176, h=270,
         focus=[(cue("The weekend is the door", 221), cue_end("I like that", 223))]),
    Text("The weekend = the door", 600, 690, cue("door.", 218), size=34),
    Arrow(SCX, 470, cue("The person", 218)),
    Card(1320, 470, cue("person", 219), w=330, h=280, emoji_name="couch_and_lamp", emoji_size=170, fill_a=0.16,
         accent=GOLD),
    Text("The person = the room", 1320, 690, cue("room", 220), size=34),
    Pill("I closed the door", SCX, 258, t_closed - 0.6, color=AARON, upper=False, size=30),
]))
sfx("correct", cue("Exactly", 216), -16)
sfx("pop", t_door, -20)
sfx("pop", cue("person", 219), -20)
sfx("thud", t_closed + 0.5, -8)

# 6 Small words, big doors
t_open = cue("open again", 232)
add(Scene(CH[5] + 0.1, 239.75, [
    Door(500, 440, CH[5] + 0.2, keys=[(0, 0.22), (t_open - 0.2, 1.0)], w=200, h=310),
    Text("You closed the door a little…", 1240, 300, cue("You closed", 228), size=44, until=cue("Remember", 233)),
    Text("…but doors can open again!", 1240, 380, cue("doors can open", 231), size=44, color=GOLD,
         until=cue("Remember", 233)),
    Pill("Our old mantra", 1240, 230, cue("Remember our old mantra", 233), size=28),
    Words("Doors, not walls.", 1240, 342, spoken("doors, not walls", 235), size=90,
          pulses=[spoken("doors, not walls", 237)]),
    Emoji("door", 1090, 540, cue("Doors, not walls", 235), size=120),
    Emoji("check_mark_button", 1150, 485, cue("Doors, not walls", 235) + 0.2, size=56, float_amp=0),
    Emoji("brick", 1400, 540, cue("walls", 236), size=120),
    Emoji("cross_mark", 1460, 485, cue("walls", 236) + 0.2, size=56, float_amp=0),
]))
sfx("chime", t_open, -16)
sfx("pop", cue("Doors, not walls", 235), -19)
sfx("pop", cue("walls", 236), -19)

s = title_scene(239.75, 244.85, "I need something new for today", spoken("I need something new for today", 241),
                size=76, emoji_name="light_bulb", emoji_cue=cue("Okay, but", 240),
                sub="Something I can say in my head… in the elevator.", sub_cue=cue("Something I can say", 243))
s.els += sticker("elevator", 1640, 560, cue("elevator.", 244), size=110)
add(s)

m1 = spoken("small words open big doors", 248)
m2 = spoken("small words open big doors", 251)
add(Scene(244.85, 256.15, [
    Rays(1060, 420, m1[0] - 0.2, r=560, color=GOLD),
    Pill("I have one for you", SCX, SY0 + 50, cue("I have one", 245), color=BELLA, upper=False, size=28),
    Door(330, 440, m1[0] - 0.3, keys=[(0, 0.0), (m1[4] - 0.1, 1.0)], w=170, h=270),
    Words("SMALL WORDS\nOPEN BIG DOORS", 1060, 410, m1, size=118, colors={4: GOLD}, pulses=[m2]),
    *sticker("sparkles", 1690, 236, cue("Here it is", 247), size=100),
    Emoji("repeat_button", 860, 650, cue("Say it again", 255), size=64, float_amp=0),
    Pill("Say it again?", 1060, 650, cue("Say it again", 255), color=AARON, upper=False, size=30),
]))
sfx("chime", m1[0], -10)

m3 = spoken("small words open big doors", 256)
t_real = cue("real conversation", 264)
add(Scene(256.15, 266.45, [
    Words("Small words open big doors", SCX, 176, m3, size=64, color=GOLD),
    Emoji("sun_behind_cloud", 230, 318, cue("Nice weather", 259), size=96),
    Bubble("Nice weather!", 470, 318, cue("Nice weather", 259), tail="left", size=40),
    Emoji("calendar", 230, 458, cue("How was your weekend", 260), size=96),
    Bubble("How was your weekend?", 565, 458, cue("How was your weekend", 260), tail="left", size=40),
    Pill("Small words", 470, 590, cue("Small words.", 261), size=30),
    Arrow(1010, 440, cue("But they open", 263)),
    Door(1250, 430, cue("But they open", 263) - 0.2, keys=[(0, 0.0), (cue("open the door", 263), 1.0)], w=170,
         h=260),
    *sticker("speech_balloon", 1560, 330, t_real, size=120),
    Text("a real conversation", 1400, 662, t_real, size=40, weight="Bold", color=GOLD),
]))
sfx("pop", cue("Nice weather", 259), -18)
sfx("pop", cue("How was your weekend", 260), -18)

m4 = spoken("small words open big doors", 266)
add(Scene(266.45, CH[6] - 3.9, [
    Words("SMALL WORDS\nOPEN BIG DOORS", SCX, 320, m4, size=104, colors={4: GOLD}),
    Emoji("check_mark_button", 730, 520, cue("I can remember", 269), size=64, float_amp=0),
    Pill("I can remember that!", SCX, 520, cue("I can remember", 269), color=AARON, upper=False, size=30),
    Emoji("brain", 590, 640, cue("Even my white brain", 271), size=80),
    Text("Even my white brain can hold it.", SCX + 40, 640, cue("Even my white brain", 271), size=38,
         weight="Medium", color=SOFT),
]))
sfx("correct", cue("I can remember", 269), -15)

add(title_scene(CH[6] - 3.9, CH[6] - 0.1, "Your brain is not white", spoken("your brain is not white", 274),
                size=84, emoji_name="face_with_peeking_eye", emoji_cue=cue("It's just a little shy", 276),
                sub="It's just a little shy.", sub_cue=cue("It's just a little shy", 276)))

# 7 Five easy ways
five = spoken("five easy ways to make small talk", 279)
t_pop = spoken("five ways, five phrases", 282)
pops = [t_pop[0], t_pop[1], (t_pop[1] + t_pop[2]) / 2, t_pop[2], t_pop[3]]
t_first = cue("the first way", 292)
t_wd = cue("the weather door", 294)
t_rain = cue("door made of rain", 298)
xs = row_x(5, 296)
cards = []
for i in range(5):
    moves = [(t_first, 0.8, 470, 450, 1.3, 1.0)] if i == 0 else [(t_first, 0.6, xs[i], 600, 0.8, 0.0)]
    cards.append(Card(xs[i], 450, pops[i], w=244, h=290, top="WAY", big=str(i + 1), big_size=124, accent=GOLD,
                      moves=moves, focus=[(t_first, END)] if i == 0 else ()))
    sfx("pop", pops[i], -18)
add(Scene(CH[6] + 0.1, END - 4.0, [
    Words("5 easy ways to make small talk", SCX, 196, five, size=70, until=t_first),
    *cards,
    *sticker("office_worker", 1720, 660, cue("coworker", 288), size=88, until=t_first),
    Pill("Poor man!", 1540, 660, cue("Poor man", 289), color=AARON, upper=False, size=28, until=t_first),
    *sticker("red_heart", 1360, 660, cue("love it", 291), size=76, until=t_first),
    Words("The weather door", 1220, 196, spoken("the weather door", 294), size=80, color=GOLD),
    Door(1220, 500, t_wd, keys=[(0, 0.7)], w=168, h=250),
    Emoji("sun_behind_cloud", 1440, 360, t_wd + 0.3, size=110, until=t_rain),
    Rain(1220, 330, t_rain, width=230, height=250),
    Pill("A door made of rain?", 1220, 690, cue("Is it a door", 297), color=AARON, upper=False, size=28),
]))
sfx("pop", t_wd, -18)
sfx("whoosh_soft", t_first, -16)

# End card
add(Scene(END - 4.0, END + 1, [
    Emoji("headphone", SCX, 236, END - 3.9, size=130),
    Words("To be continued…", SCX, 392, END - 3.7, size=96),
    Text("Next: the weather door", SCX, 500, END - 3.2, size=40, weight="Medium", color=SOFT),
    Pill("Enjoy English Talks", SCX, 596, END - 2.9, color=GOLD, size=30, upper=False),
]))
sfx("jingle", END - 3.9, -10)

# Each scene's elements wait until the previous scene has mostly left the board.
for prev, nxt in zip(SCENES, SCENES[1:]):
    for el in nxt.els:
        el.not_before(prev.end + 0.3)
