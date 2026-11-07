# Podcast video edit — "Small Words Open Big Doors"

The voice-over (`../audio/01_master_cleaned.mp3`) edited into a 1920×1080, 30 fps video with images synced to the speech, title cards, sound effects and a music bed that ducks under the voice.

**Download the finished video** from this repo's GitHub Releases page (`podcast_final.mp4`, 31:22, 192 MB). It's too large to commit to git.

## How it's built
| Step | File |
|---|---|
| Word-level transcript (faster-whisper `small.en`) | `transcribe.py` → `transcript.json` |
| Scene plan: cue time, image query / studio shot / title card, SFX | `scenes.tsv` |
| CC0 images from Openverse (WordPress Photo Directory, StockSnap) | `fetch_images.py` → `img/q/`, `img/meta.json` |
| Render: snap cuts to word onsets, cover-fit images to 16:9 with a slow pan, title cards, music + SFX mix | `render.py` → `out/podcast_final.mp4` |

Every image cut is snapped to the start of a spoken word, landing 0.12 s before it. Images are scaled to fill the frame (cover-crop), so there are no black bars. Music changes per section (intro, each of the five ways, practice, wrap-up), crossfades between loops, and is sidechain-ducked under the voice. The final mix is about −17 LUFS.

To change an image, edit its line in `scenes.tsv`, run `fetch_images.py`, then `render.py`.

```sh
python3 -m venv .venv && . .venv/bin/activate && pip install pillow faster-whisper
python fetch_images.py && python render.py   # needs ffmpeg
```

Licenses: see `CREDITS.md` (all third-party media is CC0 / public domain; Poppins font is OFL).
