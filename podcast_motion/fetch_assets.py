"""Download the Fluent Emoji 3D icons (MIT) and CC0 sound effects / music used by render.py."""
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
EMOJI_DIR = HERE / "assets" / "emoji"
AUDIO_DIR = HERE / "assets" / "audio"
FLUENT = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/"

# Fluent Emoji folder names (https://github.com/microsoft/fluentui-emoji/tree/main/assets)
EMOJI = """Headphone, Studio microphone, Sunrise, Potted plant, Teacup without handle, Alarm clock, Waving hand,
Elevator, Office building, Office worker, Pizza, Brain, Face without mouth, Grimacing face, Input numbers,
Running shoe, Zipper-mouth face, Grinning face with sweat, Busts in silhouette, Woman dancing, Calendar,
Counterclockwise arrows button, Check mark button, Memo, Sparkles, Guitar, Weary face, Speech balloon,
Shopping cart, Briefcase, Thumbs up, Bell, Outbox tray, Red heart, Red question mark, Sun behind cloud,
Spaghetti, Eyes, Glowing star, Smiling face with smiling eyes, Door, Couch and lamp, Brick, Key, Light bulb,
Face with peeking eye, Hand with fingers splayed, Cloud with rain, Megaphone, Hourglass not done, Cricket,
Thinking face, Books, Repeat button, Man dancing, Musical notes, Globe showing europe-africa, Anxious face with sweat,
Cross mark, Bullseye, Party popper, Face with tears of joy, Hundred points, Wrapped gift, House,
Closed umbrella, Snowflake, Sun, Hot face, Hot beverage, Wilted flower, Woman farmer, House with garden, Postbox,
Bread, Tomato, Sunflower, Dog face, Beach with umbrella, Houses, Crown, Seedling, Handshake, Magic wand, Window,
Mirror, Stopwatch, Cat face, Wood, Sleeping face, Grinning squinting face, Calendar, Spiral calendar, Partying face,
Thumbs up, Speaking head, Ear, Family, Person raising hand""".replace("\n", " ")

# (file, url, title, author) - all CC0, from freesound.org
AUDIO = [
    ("whoosh.mp3", "https://cdn.freesound.org/previews/60/60007_71257-hq.mp3", "Swipe Whoosh", "freesound #60007"),
    ("whoosh_soft.mp3", "https://cdn.freesound.org/previews/71/71852_1062668-hq.mp3", "digital_whoosh_soft", "ludvique, freesound #71852"),
    ("pop.mp3", "https://cdn.freesound.org/previews/669/669918_9129912-hq.mp3", "Bubble Pop for UI", "el_boss, freesound #669918"),
    ("ding_elevator.mp3", "https://cdn.freesound.org/previews/119/119448_1990688-hq.mp3", "Elevator Ding", "lmbubec, freesound #119448"),
    ("crickets.mp3", "https://cdn.freesound.org/previews/129/129678_2362707-hq.mp3", "crickets", "FreethinkerAnon, freesound #129678"),
    ("chime.mp3", "https://cdn.freesound.org/previews/380/380482_6512973-hq.mp3", "Chime Notification", "Jofae, freesound #380482"),
    ("correct.mp3", "https://cdn.freesound.org/previews/644/644951_8358230-hq.mp3", "Quiz Correct Ping 04", "craigscottuk, freesound #644951"),
    ("click.mp3", "https://cdn.freesound.org/previews/534/534104_11830391-hq.mp3", "mouse-click-double", "pbimal, freesound #534104"),
    ("scratch.mp3", "https://cdn.freesound.org/previews/431/431777_817038-hq.mp3", "Record Scratch #4", "musicvision31, freesound #431777"),
    ("jingle.mp3", "https://cdn.freesound.org/previews/255/255100_2127539-hq.mp3", "jingle1", "soneproject, freesound #255100"),
    ("laugh.mp3", "https://cdn.freesound.org/previews/138/138112_1572282-hq.mp3", "Small Crowd Laughing", "snakebarney, freesound #138112"),
    ("music_chill_melody.mp3", "https://cdn.freesound.org/previews/629/629147_12574855-hq.mp3", "Chill Lofi Melody Loop 95 BPM", "holizna, freesound #629147"),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        return r.read()


def slug(name):
    return name.lower().replace(" ", "_")


def fetch_emoji(name):
    out = EMOJI_DIR / f"{slug(name)}.png"
    if out.exists():
        return
    base = FLUENT + urllib.parse.quote(name)
    for path in (f"/3D/{slug(name)}_3d.png", f"/Default/3D/{slug(name)}_3d_default.png"):
        try:
            out.write_bytes(get(base + path))
            return
        except urllib.error.HTTPError:
            pass
    raise SystemExit(f"emoji not found: {name}")


def main():
    EMOJI_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for name in (n.strip() for n in EMOJI.split(",")):
        fetch_emoji(name)
    license_file = EMOJI_DIR / "LICENSE"
    if not license_file.exists():
        license_file.write_bytes(get("https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/LICENSE"))
    for file, url, _, _ in AUDIO:
        if not (AUDIO_DIR / file).exists():
            (AUDIO_DIR / file).write_bytes(get(url))
    print(len(list(EMOJI_DIR.glob("*.png"))), "emoji,", len(list(AUDIO_DIR.glob("*.mp3"))), "audio files")


if __name__ == "__main__":
    main()
