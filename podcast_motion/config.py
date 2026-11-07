"""Which part of the episode to build, and per-part settings. Choose the part with PART=1..7 (default 1)."""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PART = int(os.environ.get("PART", "1"))
MASTER = HERE.parent / "audio" / "01_master_cleaned.mp3"


def audio_file(part):
    return HERE.parent / "audio" / "qaybo_5min" / f"qayb_{part - 1:02d}.mp3"


def data_dir(part):
    return HERE / "data" / f"part{part}"


AUDIO = audio_file(PART)
DATA = data_dir(PART)
BUILD = HERE / "build" / f"part{PART}"
OUT_FILE = HERE / "output" / f"enjoy_english_talks_part{PART}.mp4"
PREVIEW = HERE / "output" / f"part{PART}_preview.jpg"
TITLE = "Enjoy English Talks" + (f" · Part {PART}" if PART > 1 else "")

# Seconds of title card before any voice.
INTRO = {2: 2.0}.get(PART, 0.0)
# The previous part's last line, replayed so the conversation makes sense: (start, end) in that part's audio.
RECAP = {2: (296.62, 299.5)}.get(PART)
RECAP_GAP = 0.45
# Where this part's voice ends, in seconds of its own audio. Past the end of the file means the last
# sentence was cut by the 5-minute split and is finished from the full episode. None = end of file.
AUDIO_END = {}.get(PART)

VOICE_START = INTRO + ((RECAP[1] - RECAP[0] + RECAP_GAP) if RECAP else 0.0)
