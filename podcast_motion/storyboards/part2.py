"""Part 2: way 1 (the weather door) and way 2 (the weekend question).

c(), sp(), ce() and gap() take the text and roughly when it is said in this part's audio (seconds, as in
data/part2/words.json) and return the time in the video.
"""
from config import INTRO
from gfx import CYAN, GOLD, GREEN, HOST_COLOR, RED, SOFT
from scenes import SCX, SY0, Bubble, Card, Door, Emoji, Pill, Rain, Rays, Scene, Text, Words, row_x
from story import chat_line, pause_after, sfx, sticker, title_scene
from timeline import VOICE_END, at, cue, cue_end, spoken

BELLA, AARON = HOST_COLOR["bella"], HOST_COLOR["aaron"]
END = round(VOICE_END + 4.6, 1)
HOST_APPEAR = {"bella": 0.15, "aaron": 0.3}


def c(text, t):
    return cue(text, at(t) - 0.6)


def sp(text, t):
    return spoken(text, at(t) - 0.6)


def ce(text, t):
    return cue_end(text, at(t) - 0.6)


def gap(text, t):
    return pause_after(text, at(t) - 0.6)


def pop(t, db=-20):
    sfx("pop", t, db)


def bubble_at(text, left, y, cue_t, **kw):
    """A speech bubble whose left edge is at `left`."""
    b = Bubble(text, 0, y, cue_t, **kw)
    b.x = left + b.w / 2
    return b


CHAPTERS = [
    (0.0, "Way 1 · The weather door"),
    (gap("I'm serious.", 67.09), "Mom, queen of the weather"),
    (gap("the weather teaches friendship.", 105.6), "The magic “right?”"),
    (gap("that's all.", 160.51), "Practice: one weather sentence"),
    (gap("You got it!", 201.42), "Way 2 · The weekend question"),
    (gap("That's my answer every Monday.", 266.9), "Rule: give one detail"),
]
CH = [t for t, _ in CHAPTERS]
PREVIEW_AT = c("On Friday", 231.26)

SCENES = []
add = SCENES.append

# ---------- intro and recap ----------

add(title_scene(0.0, INTRO - 0.05, "5 easy ways to make small talk", 0.5, size=80, kicker="Part 2", kicker_cue=0.3,
                emoji_name="headphone", emoji_cue=0.15, emoji_size=140, sub="Way 1 and way 2", sub_cue=1.1))
sfx("jingle", 0.1, -12)

t_rain = cue("rain", INTRO)
add(Scene(INTRO, gap("No, Aaron.", 0.37), [
    Pill("Previously…", SCX, SY0 + 50, INTRO + 0.1, size=28),
    Card(560, 440, INTRO + 0.15, w=300, h=360, top="WAY", big="1", big_size=150, accent=GOLD, focus=[(INTRO, END)]),
    Words("The weather door", 1240, 230, spoken("the weather door", INTRO), size=80, color=GOLD),
    Door(1240, 520, INTRO + 0.2, keys=[(0, 0.7)], w=150, h=230),
    Rain(1240, 350, t_rain, width=210, height=220),
    Pill("A door made of rain?", 1240, 690, cue("Is it a door", INTRO), color=AARON, upper=False, size=28),
    Emoji("cross_mark", 1420, 330, c("No, Aaron.", 0.37), size=90, float_amp=0),
]))
pop(c("No, Aaron.", 0.37), -18)

# ---------- 1 Way 1: the weather door ----------

add(Scene(gap("No, Aaron.", 0.37), gap("Everyone has an opinion.", 8.76), [
    Pill("The weather door means…", SCX, 180, c("The weather door means", 1.72), size=28),
    Emoji("sun_behind_cloud", 380, 282, c("start with the weather", 3.06), size=110),
    Words("Start with the weather", SCX + 40, 282, sp("start with the weather", 3.06), size=84),
    Text("It's the easiest door in the world.", SCX, 372, c("It's the easiest", 4.76), size=40, weight="Medium",
         color=SOFT),
    Card(650, 575, c("Everyone knows", 7.06), w=540, h=220, emoji_name="busts_in_silhouette", emoji_size=96,
         label="Everyone knows the weather"),
    Card(1270, 575, c("Everyone has an opinion", 8.76), w=540, h=220, emoji_name="speech_balloon", emoji_size=96,
         label="Everyone has an opinion"),
]))
pop(c("start with the weather", 3.06), -19)
pop(c("Everyone knows", 7.06))
pop(c("Everyone has an opinion", 8.76))

t_silence = c("Then silence", 14.75)
add(Scene(gap("Everyone has an opinion.", 8.76), gap("Then silence again.", 14.75), [
    Pill("But isn't that boring?", SCX, SY0 + 50, c("But isn't that boring", 11.06), color=AARON, upper=False, size=28),
    *chat_line("left", ("emoji", "office_worker"), "It's raining.", 300, c("It's raining.", 12.65), label="Co-worker"),
    *chat_line("right", ("host", "aaron"), "Yes.", 470, c("Yes.", 13.77), fill=AARON),
    Text("…then silence again.", SCX, 640, t_silence, size=44, weight="Medium", color=SOFT),
    *sticker("cricket", 1290, 640, t_silence + 0.3, size=80, db=None),
]))
sfx("crickets", ce("silence again", 14.75) + 0.05, -17)

t_ex = c("It's raining again", 23.24)
ex = bubble_at("It's raining again. I forgot my umbrella.", 600, 470, t_ex, tail="left", size=40, max_w=1100)
add(Scene(gap("Then silence again.", 14.75), gap("Now you give something.", 26.32), [
    Pill("Good question!", SCX, SY0 + 50, c("Good question", 16.94), color=BELLA, upper=False, size=28),
    Text("It's boring if you stop there.", SCX, 214, c("It's boring if", 18.21), size=40, weight="Medium", color=SOFT),
    Words("Add one small comment", SCX, 300, sp("add one small comment", 20.92), size=80, colors={3: GOLD}),
    Emoji("cloud_with_rain", 520, 470, t_ex, size=110),
    ex,
    Emoji("closed_umbrella", ex.x + ex.w / 2 + 80, 470, c("umbrella", 25.22), size=100, rot0=-25),
    Text("Now you give something.", SCX - 40, 640, c("Now you give", 26.32), size=46, weight="Bold", color=GOLD),
    Emoji("wrapped_gift", SCX + 330, 636, c("give something", 26.86), size=80),
]))
pop(t_ex, -18)
pop(c("umbrella", 25.22))
pop(c("give something", 26.86))

t_exactly = c("Exactly", 32.9)
rows = [("snowflake", "It's so cold today. I need more coffee.", c("It's so cold", 37.06)),
        ("sun", "Nice day, right? I want to go outside.", c("Nice day", 41.22)),
        ("hot_face", "Hot again. My plants are not happy.", c("Hot again", 44.48))]
els = [
    Pill("So I say the weather… and then something about me?", SCX, SY0 + 50, c("Oh, so I say", 27.56), color=AARON,
         upper=False, size=28, until=t_exactly),
    Pill("Exactly!", SCX, SY0 + 50, t_exactly, color=GREEN, upper=False, size=30),
    Card(660, 285, c("Weather plus you", 34.2), w=380, h=190, emoji_name="sun_behind_cloud", emoji_size=90,
         label="Weather", label_size=36),
    Text("+", SCX, 285, c("plus", 34.5), size=96, weight="Bold", color=GOLD),
    Card(1260, 285, c("you.", 34.94), w=380, h=190, emoji_name="person_raising_hand", emoji_size=90, label="You",
         label_size=36, accent=GOLD),
]
for k, (icon, text, t) in enumerate(rows):
    y = 460 + 98 * k
    els += [Emoji(icon, 420, y, t, size=74, float_amp=0), bubble_at(text, 500, y, t, tail="left", size=34)]
    pop(t, -19)
add(Scene(gap("Now you give something.", 26.32), gap("my plants are not happy.", 46.28), els))
sfx("correct", t_exactly, -15)
pop(c("Weather plus you", 34.2))
pop(c("you.", 34.94))

add(Scene(gap("my plants are not happy.", 46.28), gap("like you said.", 58.6), [
    Emoji("potted_plant", 640, 220, c("My plants are never", 48.69), size=120),
    *chat_line("right", ("host", "aaron"), "My plants are never happy.", 220, c("My plants are never", 48.69),
               fill=AARON),
    Text("Well… two and a half of them.", 1340, 318, c("two and a half", 51.38), size=32, weight="Medium",
         color=SOFT),
    *chat_line("left", ("host", "bella"), "Is the brown one still brown?", 430, c("Is the brown one", 53.11),
               fill=BELLA),
    Emoji("wilted_flower", 640, 610, c("It's still brown", 55.82), size=120),
    *chat_line("right", ("host", "aaron"), "It's still brown.", 580, c("It's still brown", 55.82), fill=AARON),
    Text("…but I talk to it now, like you said.", 1240, 676, c("I talk to it now", 57.44), size=32,
         weight="Medium", color=SOFT),
]))

add(Scene(gap("like you said.", 58.6), CH[1] - 0.1, [
    Emoji("wilted_flower", 520, 400, c("I say, good morning", 59.7), size=210),
    bubble_at("Good morning, plant. Please don't die.", 700, 290, c("I say, good morning", 59.7), tail="left",
              fill=AARON, size=44, max_w=900),
    Words("Small talk with a plant", 1200, 470, sp("small talk with a plant", 63.1), size=60),
    Pill("That's small talk practice. I'm serious.", 1200, 590, c("That's small talk practice", 65.34), color=BELLA,
         upper=False, size=30),
    Emoji("check_mark_button", 1200, 680, c("I'm serious", 67.09), size=64, float_amp=0),
]))
pop(c("I say, good morning", 59.7), -18)
sfx("correct", c("I'm serious", 67.09), -17)

# ---------- 2 Mom, queen of the weather ----------

cards = [("house_with_garden", "The neighbours", c("neighbors", 75.58)),
         ("postbox", "The postman", c("postman", 76.5)),
         ("bread", "The man who sells bread", c("bread", 77.74))]
add(Scene(CH[1] + 0.1, gap("sells bread.", 77.58), [
    Pill("A small story", SCX, SY0 + 50, c("let me tell you a small story", 69.18), color=BELLA, upper=False, size=28),
    Emoji("woman_farmer", 420, 330, c("My mom", 71.34), size=170),
    Text("My mom, in her garden", 420, 470, c("in her garden", 71.94), size=32),
    Words("talks to everyone about the weather", 1200, 250, sp("talks to everyone about the weather", 73.08),
          size=56, max_w=1050),
    *[Card(x, 520, t, w=320, h=230, emoji_name=icon, emoji_size=96, label=label, label_size=28)
      for x, (icon, label, t) in zip(row_x(3, 350, 1200), cards)],
]))
pop(c("My mom", 71.34), -18)
for _, _, t in cards:
    pop(t)

t_everyone = c("Everyone.", 80.46)
answers = [("sunflower", "gardens", c("gardens", 90.78)), ("dog_face", "dogs", c("dogs", 91.76)),
           ("beach_with_umbrella", "holidays", c("holidays", 92.72))]
mom = bubble_at("It's dry this week. My tomatoes are thirsty.", 470, 330, c("It's dry", 83.72), tail="left", size=40,
                max_w=1100)
add(Scene(gap("sells bread.", 77.58), gap("their holidays.", 92.54), [
    Pill("Everyone?", SCX, SY0 + 50, c("Everyone?", 79.0), color=AARON, upper=False, size=30, until=t_everyone),
    Pill("Everyone!", SCX, SY0 + 50, t_everyone, color=BELLA, upper=False, size=30),
    Text("And she always adds one thing:", SCX, 220, c("And she always adds", 81.65), size=38, weight="Medium",
         color=SOFT),
    Emoji("woman_farmer", 380, 330, c("It's dry", 83.72), size=110),
    mom,
    Emoji("tomato", mom.x + mom.w / 2 + 70, 330, c("tomatoes", 85.96), size=90),
    Text("And people always answer. They tell her about their…", SCX, 470, c("And people always answer", 87.74),
         size=36, weight="Medium", color=SOFT),
    *[el for x, (icon, label, t) in zip(row_x(3, 330), answers)
      for el in sticker(icon, x, 575, t, size=100, label=label, label_size=30)],
]))
pop(c("tomatoes", 85.96))

t_queen = c("She is the queen", 99.5)
add(Scene(gap("their holidays.", 92.54), gap("She is the queen.", 99.5), [
    Emoji("houses", SCX, 205, c("She knows", 93.79), size=120),
    Text("She knows the whole street now.", SCX, 315, c("She knows", 93.79), size=46, weight="Bold"),
    Rays(SCX, 470, t_queen - 0.2, r=440, color=GOLD),
    Emoji("crown", SCX, 455, t_queen, size=130),
    Words("Queen of the weather door", SCX, 610, sp("queen of the weather door", 97.46), size=72, color=GOLD),
]))
pop(c("She knows", 93.79), -19)
sfx("chime", t_queen, -13)

add(Scene(gap("She is the queen.", 99.5), CH[2] - 0.1, [
    Pill("Mom says", 650, 215, c("And she says", 101.46), color=BELLA, upper=False, size=28),
    Card(650, 455, c("the garden teaches", 102.24), w=540, h=330, emoji_name="seedling", emoji_size=120,
         big="Patience", big_size=56, label="The garden teaches patience", label_size=30),
    Pill("Bella thinks", 1270, 215, c("but I think", 104.2), color=BELLA, upper=False, size=28),
    Card(1270, 455, c("the weather teaches", 105.6), w=540, h=330, emoji_name="handshake", emoji_size=120,
         big="Friendship", big_size=56, big_color=GOLD, label="The weather teaches friendship", label_size=30,
         accent=GOLD, focus=[(c("friendship", 106.12), CH[2])]),
]))
pop(c("the garden teaches", 102.24))
pop(c("the weather teaches", 105.6))

# ---------- 3 The magic "right?" ----------

add(Scene(CH[2] + 0.1, gap("Or terrible weather, right?", 114.21), [
    Pill("What's the phrase for this one?", SCX, SY0 + 50, c("what's the phrase", 108.96), color=AARON,
         upper=False, size=28),
    Text("The phrase is…", SCX, 235, c("The phrase is", 111.22), size=40, weight="Medium", color=SOFT),
    Emoji("sun", 450, 370, c("nice weather", 112.5), size=110),
    Words("Nice weather, right?", SCX + 60, 370, sp("nice weather, right", 112.5), size=84, colors={2: GOLD}),
    Emoji("cloud_with_rain", 450, 560, c("terrible weather", 114.5), size=110),
    Words("Terrible weather, right?", SCX + 60, 560, sp("terrible weather, right", 114.5), size=84,
          colors={2: GOLD}),
]))
pop(c("nice weather", 112.5), -19)
pop(c("terrible weather", 114.5), -19)

t_magic = c("magic", 119.7)
add(Scene(gap("Or terrible weather, right?", 114.21), gap("people love to agree.", 123.43), [
    Rays(SCX, 290, t_magic - 0.2, r=420, color=GOLD),
    Words("…right?", SCX, 280, sp("right", 117.72), size=150, color=GOLD),
    Emoji("magic_wand", SCX + 300, 240, t_magic, size=110, rot0=-35),
    Text("That little “right?” at the end is magic.", SCX, 420, c("That little", 117.15), size=40, weight="Medium",
         color=SOFT),
    Card(650, 590, c("It asks", 120.85), w=560, h=190, emoji_name="handshake", emoji_size=80,
         label="It asks the other person to agree", label_size=30),
    Card(1270, 590, c("people love", 123.43), w=560, h=190, emoji_name="thumbs_up", emoji_size=80,
         label="People love to agree!", label_size=30, accent=GOLD),
]))
sfx("chime", t_magic, -15)
pop(c("It asks", 120.85))
pop(c("people love", 123.43))

add(Scene(gap("people love to agree.", 123.43), gap("this morning.", 132.32), [
    Pill("Let me try!", SCX, SY0 + 50, c("Let me try", 127.3), color=AARON, upper=False, size=30),
    Emoji("snowflake", 420, 300, c("Cold weather today", 129.37), size=110),
    *chat_line("right", ("host", "aaron"), "Cold weather today, right?", 300, c("Cold weather today", 129.37),
               fill=AARON),
    Emoji("dog_face", 420, 490, c("Max didn't want", 131.14), size=120),
    *chat_line("right", ("host", "aaron"), "Max didn't want to go outside this morning.", 490,
               c("Max didn't want", 131.14), fill=AARON, max_w=900),
]))

t_perfect = c("Perfect", 133.72)
t_tail = c("tail", 147.02)
add(Scene(gap("this morning.", 132.32), gap("He's proud of his tail.", 146.24), [
    Pill("Perfect!", SCX, SY0 + 50, t_perfect, color=GREEN, upper=False, size=30),
    Text("That's exactly how people use it.", SCX, 212, c("That's exactly how", 134.65), size=38, weight="Medium",
         color=SOFT),
    Card(650, 355, c("Weather, right?", 137.08), w=480, h=180, emoji_name="sun_behind_cloud", emoji_size=80,
         label="Weather, right?", label_size=34),
    Text("+", SCX, 355, c("And then", 138.74), size=90, weight="Bold", color=GOLD),
    Card(1270, 355, c("one thing about you", 139.3), w=480, h=180, emoji_name="person_raising_hand", emoji_size=80,
         label="One thing about you", label_size=34, accent=GOLD),
    Emoji("dog_face", 520, 590, c("Max is a great small-talk", 140.76), size=120, shake=(t_tail, 0.9)),
    Text("Max is a great small-talk topic!", 620, 560, c("Max is a great small-talk", 140.76), size=38, align="left",
         anchor="left"),
    Pill("Max is a great everything. He's proud of his tail!", 620 + 300, 640, c("Max is a great everything", 144.16),
         color=AARON, upper=False, size=26),
]))
sfx("correct", t_perfect, -15)
pop(c("Weather, right?", 137.08))
pop(c("one thing about you", 139.3))
pop(c("Max is a great small-talk", 140.76), -19)

add(Scene(gap("He's proud of his tail.", 146.24), CH[3] - 0.1, [
    Text("Wait… what if the person just says “yes”?", SCX, 180, c("what if the person", 148.74), size=40,
         color=AARON),
    *chat_line("left", ("emoji", "office_worker"), "Yes.", 305, c("says yes", 149.58), label="Co-worker"),
    Emoji("elevator", 640, 300, c("elevator", 151.56), size=100),
    Words("Then ask one small question", SCX, 440, sp("then you ask one small question", 152.66)[:1]
          + sp("ask one small question", 153.08), size=62, colors={4: GOLD}),
    bubble_at("Do you like the cold?", 300, 575, c("Do you like the cold", 155.62), tail="left", size=40),
    bubble_at("Do you have a dog?", 1000, 575, c("do you have a dog", 157.46), tail="left", size=40),
    Pill("One question. That's all.", SCX, 680, c("One question", 159.38), color=GOLD, upper=False, size=28),
]))
pop(c("Do you like the cold", 155.62), -19)
pop(c("do you have a dog", 157.46), -19)

# ---------- 4 Practice ----------

ex2 = bubble_at("It's cloudy. I think it will rain.", 520, 560, c("It's cloudy", 173.1), tail="left", size=40)
add(Scene(CH[3] + 0.1, gap("add one thing about you.", 176.68), [
    Pill("How do I practice this one?", SCX, SY0 + 50, c("How do I practice", 163.99), color=AARON, upper=False,
         size=28),
    Emoji("window", 380, 320, c("look out the window", 168.1), size=150),
    Text("Every morning, look out the window…", 1100, 230, c("Every morning", 166.46), size=40, weight="Medium",
         color=SOFT),
    Words("Say one weather sentence in English", 1100, 320, sp("say one weather sentence in English", 169.2), size=56,
          max_w=1250),
    Pill("Out loud!", 1100, 405, c("out loud", 171.96), color=GOLD, upper=False, size=30),
    Emoji("cloud_with_rain", 430, 560, c("It's cloudy", 173.1), size=100),
    ex2,
    Text("+ one thing about you", ex2.x + ex2.w / 2 + 250, 560, c("add one thing", 176.68), size=40, weight="Bold",
         color=GOLD),
]))
pop(c("look out the window", 168.1), -19)
pop(c("It's cloudy", 173.1), -19)

add(Scene(gap("add one thing about you.", 176.68), gap("ready for the elevator.", 192.34), [
    Emoji("mirror", 420, 360, c("In the mirror", 181.78), size=190),
    Text("Weather small talk… with myself!", 1150, 210, c("I do weather small talk", 179.28), size=44),
    Pill("In the mirror, like my morning routine", 1150, 300, c("In the mirror", 181.78), color=AARON, upper=False,
         size=28),
    Text("Just add the weather.", 1150, 410, c("Just add the weather", 188.1), size=50, weight="Bold", color=GOLD),
    Emoji("stopwatch", 950, 540, c("30 seconds", 189.62), size=100),
    Words("30 seconds", 1210, 540, sp("30 seconds", 189.62), size=80),
    Text("…and tomorrow you're ready for the elevator!", 1150, 660, c("And tomorrow", 190.88), size=36,
         weight="Medium", color=SOFT),
]))
pop(c("In the mirror", 181.78), -19)
pop(c("30 seconds", 189.62), -19)
sfx("ding_elevator", ce("elevator.", 192.92) + 0.1, -16)

t_doors = c("open big doors", 198.1)
add(Scene(gap("ready for the elevator.", 192.34), CH[4] - 0.1, [
    Words("Weather, right?", SCX, 220, sp("weather, right", 193.52), size=72, colors={1: GOLD}),
    Words("+ One thing about me", SCX, 312, [c("One thing about me", 195.88)] + sp("one thing about me", 195.88),
          size=56),
    Door(SCX, 480, c("Small words open", 197.31) - 0.2, keys=[(0, 0.0), (t_doors, 1.0)], w=150, h=230),
    Words("Small words open big doors", SCX, 655, sp("small words open big doors", 197.31), size=64, color=GOLD),
    *sticker("sparkles", 1430, 400, c("Beautiful", 200.36), size=90, db=None),
    Pill("Beautiful! You got it!", 1430, 500, c("Beautiful", 200.36), color=GREEN, upper=False, size=30),
]))
sfx("chime", t_doors, -14)
sfx("correct", c("Beautiful", 200.36), -15)

# ---------- 5 Way 2: the weekend question ----------

t_no = c("but no", 213.0)
add(Scene(CH[4] + 0.1, gap("but no.", 213.0), [
    Words("A question that everyone can answer", SCX, 220, sp("a question that everyone can answer", 203.36),
          size=64, max_w=1500),
    *sticker("pizza", 1460, 420, c("pizza", 209.41), size=150),
    bubble_at("Do you want pizza?", 760, 420, c("do you want pizza", 208.99), tail="right", fill=AARON, size=44),
    Emoji("cross_mark", 1560, 350, t_no, size=80, float_amp=0),
    Pill("A very good question… but no.", SCX, 620, c("That is a very good question", 210.85), color=BELLA,
         upper=False, size=30),
]))

add(Scene(gap("but no.", 213.0), gap("Did you have a weekend?", 220.94), [
    Card(560, 430, c("The second way", 214.46), w=300, h=360, top="WAY", big="2", big_size=150, accent=GOLD,
         focus=[(c("The second way", 214.46), END)]),
    Words("The weekend question", 1240, 250, sp("the weekend question", 216.34), size=80, color=GOLD),
    Emoji("calendar", 1240, 410, c("weekend question", 216.6), size=120),
    bubble_at("Did you have a weekend?", 940, 590, c("Did you have a weekend", 220.94), tail="right", fill=AARON,
              size=42),
    Text("Let me guess…", 1240, 500, c("Let me guess", 220.24), size=34, weight="Medium", color=SOFT),
]))
pop(c("The second way", 214.46), -18)
sfx("chime", c("the weekend question", 216.34), -14)

add(Scene(gap("Did you have a weekend?", 220.94), gap("On Friday.", 231.26), [
    Pill("Everyone has a weekend, Aaron!", SCX, SY0 + 50, c("Everyone has a weekend", 223.34), color=BELLA,
         upper=False, size=28),
    Emoji("grinning_squinting_face", 1360, SY0 + 50, c("Everyone has a weekend", 223.34) + 0.3, size=70,
          float_amp=0),
    Text("The question is:", SCX, 228, c("The question is", 225.5), size=40, weight="Medium", color=SOFT),
    Card(650, 470, c("how was your weekend", 226.72), w=560, h=330, top="ON MONDAY", emoji_name="spiral_calendar",
         emoji_size=110, label="How was your weekend?", label_size=38),
    Card(1270, 470, c("any plans for the weekend", 229.7), w=560, h=330, top="ON FRIDAY", emoji_name="partying_face",
         emoji_size=110, label="Any plans for the weekend?", label_size=38, accent=GOLD),
]))
pop(c("how was your weekend", 226.72))
pop(c("any plans for the weekend", 229.7))

add(Scene(gap("On Friday.", 231.26), gap("how's your week going?", 244.44), [
    Pill("Two questions!", SCX, SY0 + 50, c("Oh, two questions", 232.6), color=AARON, upper=False, size=28),
    Text("One for the start of the week, one for the end.", SCX, 220, c("One for the start", 234.38), size=36,
         weight="Medium", color=SOFT),
    Card(520, 470, c("Monday looks back", 238.22), w=400, h=320, top="MONDAY", emoji_name="calendar",
         emoji_size=100, label="Looks back: “How was your weekend?”", label_size=30),
    Card(1400, 470, c("Friday looks forward", 239.84), w=400, h=320, top="FRIDAY", emoji_name="partying_face",
         emoji_size=100, label="Looks forward: “Any plans for the weekend?”", label_size=30, accent=GOLD),
    Card(SCX, 470, c("how's your week going", 244.44), w=400, h=320, top="MIDWEEK", emoji_name="speech_balloon",
         emoji_size=100, label="“How's your week going?”", label_size=30, accent=GREEN,
         focus=[(c("how's your week going", 244.44), END)]),
]))
pop(c("Monday looks back", 238.22))
pop(c("Friday looks forward", 239.84))
pop(c("how's your week going", 244.44), -18)

t3 = c("three doors", 248.14)
add(Scene(gap("how's your week going?", 244.44), gap("I like that.", 252.04), [
    Pill("That's nice!", SCX, SY0 + 50, c("That's nice", 246.32), color=AARON, upper=False, size=28),
    Words("The week has three doors", SCX, 220, sp("the week has three doors", 247.5), size=72, colors={3: GOLD, 4: GOLD},
          pulses=[sp("the week has three doors", 249.91)]),
    *[el for k, (x, label) in enumerate(zip(row_x(3, 400), ("MONDAY", "MIDWEEK", "FRIDAY")))
      for el in (Door(x, 455, t3 - 0.3 + 0.2 * k, keys=[(0, 0.0), (t3 + 0.25 * k, 1.0)], w=140, h=220),
                 Text(label, x, 615, t3 + 0.25 * k, size=28, weight="Bold", color=SOFT))],
    Pill("I like that!", SCX, 690, c("I like that", 252.04), color=BELLA, upper=False, size=28),
]))
for k in range(3):
    pop(t3 + 0.25 * k, -19)

simple = [("couch_and_lamp", "QUIET", "It was quiet. I stayed home.", c("It was quiet", 255.88)),
          ("busts_in_silhouette", "BUSY", "It was busy. I visited my parents.", c("it was busy", 259.08)),
          ("sleeping_face", "NOTHING SPECIAL", "Nothing special. I slept a lot.", c("nothing special", 262.68))]
t_slept = c("I slept a lot. That's", 265.43)
add(Scene(gap("I like that.", 252.04), CH[5] - 0.1, [
    Words("The answers can be very simple", SCX, 200, sp("the answers can be very simple", 253.36), size=64),
    *[Card(x, 430, t, w=480, h=300, top=top, emoji_name=icon, emoji_size=100, label=label, label_size=32,
           focus=[(t_slept, CH[5])] if top == "NOTHING SPECIAL" else ())
      for x, (icon, top, label, t) in zip(row_x(3, 520), simple)],
    Pill("“I slept a lot.” That's my answer every Monday!", SCX, 660, t_slept, color=AARON, upper=False, size=28),
]))
for *_, t in simple:
    pop(t)

# ---------- 6 Rule: give one detail ----------

t_say = c("Say, It was good", 276.94)
good = bubble_at("It was good. I walked Max in the park, and he found a very big stick.", 520, 560, t_say,
                 tail="left", size=38, max_w=980)
add(Scene(CH[5] + 0.1, gap("a very big stick.", 281.02), [
    Pill("A small rule", SCX, SY0 + 50, c("here is a small rule", 271.42), color=BELLA, upper=False, size=28),
    Words("Give one detail", SCX, 232, sp("give one detail", 273.51), size=100, colors={2: GOLD}),
    Text("Not:", 420, 395, c("Not, it was good", 275.2), size=40, weight="Bold", color=RED),
    bubble_at("It was good.", 520, 395, c("Not, it was good", 275.2), tail="left", size=38),
    Emoji("cross_mark", 860, 395, c("good.", 276.18) + 0.15, size=64, float_amp=0),
    Text("Say:", 420, 560, t_say, size=40, weight="Bold", color=GREEN),
    good,
    Emoji("check_mark_button", good.x + good.w / 2 + 60, 560, c("very big stick", 281.36), size=70, float_amp=0),
]))
pop(c("Not, it was good", 275.2), -19)
pop(t_say, -19)
sfx("correct", c("very big stick", 281.36), -16)

t_bigger = c("bigger than him", 288.04)
add(Scene(gap("a very big stick.", 281.02), gap("like a king.", 290.24), [
    Emoji("dog_face", 470, 420, c("He did find", 284.68), size=170),
    Emoji("wood", 760, 450, c("big stick", 285.5), size=150, rot0=-30, moves=[(t_bigger, 0.5, 760, 430, 1.45, 1.0)]),
    Emoji("crown", 470, 300, c("like a king", 290.24), size=100),
    Text("Last Sunday…", 1320, 230, c("last Sunday", 286.58), size=40, weight="Medium", color=SOFT),
    Words("It was bigger than him!", 1320, 350, sp("it was bigger than him", 287.75), size=66),
    Text("He carried it home like a king.", 1320, 470, c("He carried it home", 289.4), size=42, color=GOLD),
]))
pop(c("He did find", 284.68), -19)
pop(c("big stick", 285.5), -19)
pop(c("like a king", 290.24), -18)

t_laugh = c("laugh", 296.3)
add(Scene(gap("like a king.", 290.24), END - 4.0, [
    Words("See? That's a story!", SCX, 220, sp("see? that's a story", 293.42), size=88, colors={2: GOLD, 3: GOLD}),
    Text("People will laugh…", SCX - 60, 345, c("People will laugh", 295.76), size=44, weight="Bold"),
    Emoji("face_with_tears_of_joy", SCX + 300, 340, t_laugh, size=90),
    Text("…and then they'll tell you about their", SCX, 445, c("and then they will tell you", 297.27), size=36,
         weight="Medium", color=SOFT),
    *[el for x, (icon, label, t) in zip(row_x(3, 330), (("dog_face", "dog", c("dog", 299.0)),
                                                         ("cat_face", "cat", c("cat", 300.14)),
                                                         ("wood", "stick", c("stick", 301.12))))
      for el in sticker(icon, x, 570, t, size=100, label=label, label_size=30)],
]))
sfx("laugh", t_laugh, -21)

# ---------- end card ----------

add(Scene(END - 4.0, END + 1, [
    Emoji("headphone", SCX, 236, END - 3.9, size=130),
    Words("To be continued…", SCX, 392, END - 3.7, size=96),
    Text("Next: what if your weekend is boring?", SCX, 500, END - 3.2, size=40, weight="Medium", color=SOFT),
    Pill("Enjoy English Talks", SCX, 596, END - 2.9, color=GOLD, size=30, upper=False),
]))
sfx("jingle", END - 3.9, -10)
