# Three cards motion graphic (CapCut)

A 7-second motion graphic: three rectangle cards with the text **1** (left), **2** (center) and **3** (right) on a dark blue → blue gradient background. The cards rise in one after another, the numbers pop in, a light sweeps across each card, the cards glow in turn and then fly out.

![Preview](output/preview.png)

| File | What it is |
|---|---|
| `output/three_cards_motion.mp4` | Finished video, 1920×1080, 30 fps, 7 s. Import it into CapCut on a phone, PC or Mac. |
| `output/Three Cards Motion - CapCut project.zip` | Editable CapCut project for CapCut on Windows PC. |

To download a file, open it on GitHub and click **Download raw file**.

## Open the project in CapCut (Windows PC)

1. Close CapCut.
2. Right-click the zip → **Extract All**.
3. Double-click `INSTALL_ON_WINDOWS.bat` and press Enter.
4. Open CapCut and click the project **Three Cards Motion**.

CapCut stores media as full file paths, so the installer copies the project into CapCut's projects folder and writes the paths for your PC. Manual steps are in `HOW_TO_OPEN.txt` inside the zip.

Tracks in the project:

- **Background**: animated gradient video
- **Card 1–3**: card images
- **Number 1–3**: editable text in Poppins Bold

All motion is keyframes, so you can edit it in CapCut. The light sweep and glow are only in the MP4.

## Rebuild

```bash
pip install -r requirements.txt
python render_video.py           # MP4 + project media (needs ffmpeg)
python build_capcut_project.py   # CapCut project zip
```

`motion.py` holds the layout and animation curves. Both scripts use it, so the CapCut keyframes follow the same motion as the video.

Font: Poppins Bold, SIL Open Font License (`fonts/OFL.txt`).
