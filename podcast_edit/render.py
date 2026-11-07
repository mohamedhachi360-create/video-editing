"""Render the podcast video: CC0 images synced to the voice-over, title cards, SFX and a ducked music bed."""
import csv, json, os, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

W, H, FPS = 1920, 1080, 30
PAN = 1.08  # images are rendered 8% oversize so they can drift without exposing edges
VO = "../audio/01_master_cleaned.mp3"
TAIL = 3.0  # seconds of end card after the voice-over ends
OUT = "out"; os.makedirs(f"{OUT}/frames", exist_ok=True); os.makedirs(f"{OUT}/clips", exist_ok=True)
FONT_B, FONT_M = "fonts/Poppins-Bold.ttf", "fonts/Poppins-Medium.ttf"

def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
def dur(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))

vo_len = dur(VO)
total = vo_len + TAIL
words = [w for s in json.load(open("transcript.json")) for w in s["words"]]
meta = json.load(open("img/meta.json"))

# --- scenes: snap each cue to the nearest word onset so cuts land on speech ---
cues = []
for r in csv.reader(open("scenes.tsv"), delimiter="\t"):
    if not r or r[0].startswith("#"): continue
    t = float(r[0])
    if t > 0:
        near = min(words, key=lambda w: abs(w["s"] - t))
        if abs(near["s"] - t) < 3: t = max(0, near["s"] - 0.12)
    cues.append(dict(t=t, img=r[1], sfx=(r[2] if len(r) > 2 else "").strip()))
cues.sort(key=lambda c: c["t"])
frames = [round(c["t"] * FPS) for c in cues] + [round(total * FPS)]
for i, c in enumerate(cues): c["n"] = frames[i + 1] - frames[i]; c["f0"] = frames[i]
assert all(c["n"] >= FPS for c in cues), [(c["t"], c["img"]) for c in cues if c["n"] < FPS]

# --- stills ---
studio = Image.open("img/studio.png").convert("RGB")
bg_card = ImageEnhance.Brightness(ImageOps.fit(studio, (W, H)).filter(ImageFilter.GaussianBlur(28))).enhance(0.45)

def balanced(text, n):
    words = text.split(); lines = []
    for k in range(n):
        rest = words[sum(len(l.split()) for l in lines):]
        if k == n - 1: lines.append(" ".join(rest)); break
        target = len(" ".join(rest)) / (n - k); line = []
        for w in rest:
            if line and len(" ".join(line + [w])) > target + 4: break
            line.append(w)
        lines.append(" ".join(line))
    return [l for l in lines if l]

def fit_text(draw, text, font_path, max_w, size, min_size, max_lines=3):
    for sz in range(size, min_size - 1, -4):
        f = ImageFont.truetype(font_path, sz)
        for n in range(1, max_lines + 1):
            lines = balanced(text, n)
            if max(draw.textlength(l, font=f) for l in lines) <= max_w: return f, lines
    f = ImageFont.truetype(font_path, min_size); return f, balanced(text, max_lines)

def card(title, sub):
    im = bg_card.copy(); d = ImageDraw.Draw(im, "RGBA")
    tf, tl = fit_text(d, title, FONT_B, W - 480, 112, 60)
    sf, sl = fit_text(d, sub, FONT_M, W - 520, 50, 34, 2)
    tlh, slh = round(tf.size * 1.22), round(sf.size * 1.3)
    block = tlh * len(tl) + 34 + slh * len(sl)
    top = (H - block) / 2
    d.rounded_rectangle((180, top - 90, W - 180, top + block + 90), 48, fill=(20, 16, 12, 175), outline=(255, 196, 120, 210), width=4)
    y = top
    for l in tl: d.text((W / 2, y), l, font=tf, fill="white", anchor="ma"); y += tlh
    y += 34
    for l in sl: d.text((W / 2, y), l, font=sf, fill=(255, 205, 140), anchor="ma"); y += slh
    return im

def oversize(im, focus=(0.5, 0.5), zoom=1.0):
    big = ImageOps.fit(im, (round(W * PAN), round(H * PAN)), Image.LANCZOS, centering=focus)
    if zoom > 1:  # tighter framing of the same picture
        cw, ch = big.width / zoom, big.height / zoom
        cx, cy = focus[0] * big.width, focus[1] * big.height
        x0 = min(max(cx - cw / 2, 0), big.width - cw); y0 = min(max(cy - ch / 2, 0), big.height - ch)
        big = big.crop((x0, y0, x0 + cw, y0 + ch)).resize((round(W * PAN), round(H * PAN)), Image.LANCZOS)
    return big

studio_frames = [((0.5, 0.5), 1.0), ((0.27, 0.45), 1.7), ((0.75, 0.42), 1.7), ((0.5, 0.55), 1.3)]
si = 0
for i, c in enumerate(cues):
    p = f"{OUT}/frames/{i:03d}.jpg"; c["still"] = p
    if c["img"].startswith("@card:"):
        t, _, s = c["img"][6:].partition("|"); card(t, s).save(p, quality=94); c["pan"] = False
    else:
        if c["img"].startswith("@studio"):
            focus, z = studio_frames[si % len(studio_frames)]; si += 1
            oversize(studio, focus, z).save(p, quality=94)
        else:
            oversize(Image.open(meta[c["img"]]["path"]).convert("RGB")).save(p, quality=94)
        c["pan"] = True

# --- per-scene clips (slow drift; direction alternates) ---
dx, dy = round(W * PAN) - W, round(H * PAN) - H
dirs = [(0, 0, 1, 1), (1, 1, 0, 0), (1, 0, 0, 1), (0, 1, 1, 0), (0, 0.5, 1, 0.5), (1, 0.5, 0, 0.5)]
def clip(i):
    c = cues[i]; o = f"{OUT}/clips/{i:03d}.mp4"
    if os.path.exists(o) and os.environ.get("REUSE"): return o
    if c["pan"]:
        x0, y0, x1, y1 = dirs[i % len(dirs)]; n = c["n"]
        vf = f"crop={W}:{H}:x='{dx}*({x0}+({x1}-{x0})*n/{n})':y='{dy}*({y0}+({y1}-{y0})*n/{n})'"
    else:
        vf = "null"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", c["still"], "-vf", vf + ",format=yuv420p",
         "-frames:v", str(c["n"]), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), "-g", str(FPS * 4), o])
    return o
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(4) as ex: clips = list(ex.map(clip, range(len(cues))))
open(f"{OUT}/concat.txt", "w").write("".join(f"file 'clips/{i:03d}.mp4'\n" for i in range(len(cues))))
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/concat.txt", "-c", "copy", f"{OUT}/video.mp4"])

# --- music bed: one CC0 loop per section, crossfaded, then ducked under the voice ---
sections = [(0, "m5_ukulele"), (170, "m3_chill_melody"), (292, "m1_fat_lofi"), (511, "m2_lofi_scoop"),
            (779, "m4_jazz_organ"), (1001, "m6_epiano"), (1248, "m3_chill_melody"), (1506, "m1_fat_lofi"), (1678, "m5_ukulele")]
XF = 3.0
parts = []
for k, (s, name) in enumerate(sections):
    e = sections[k + 1][0] if k + 1 < len(sections) else total
    d = e - s + (XF if k + 1 < len(sections) else 0)
    o = f"{OUT}/music_{k}.wav"
    run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", f"music/{name}.mp3", "-t", f"{d:.3f}",
         "-af", "loudnorm=I=-16:TP=-2:LRA=11,aresample=44100", "-ac", "2", o])
    parts.append(o)
inp = sum((["-i", p] for p in parts), [])
chain, last = [], "[0:a]"
for k in range(1, len(parts)):
    chain.append(f"{last}[{k}:a]acrossfade=d={XF}:c1=tri:c2=tri[x{k}]"); last = f"[x{k}]"
chain.append(f"{last}afade=t=out:st={total - 4:.3f}:d=4[m]")
run(["ffmpeg", "-y", *inp, "-filter_complex", ";".join(chain), "-map", "[m]", f"{OUT}/music_bed.wav"])

# --- SFX ---
SFX_GAIN = {"crickets": -20, "laugh": -14, "ding_elevator": -10, "jingle": -8, "scratch": -12}
sfx_events = [(max(0, c["t"] - (0.25 if c["sfx"].startswith("whoosh") else 0)), c["sfx"]) for c in cues if c["sfx"]]
sfx_events.append((vo_len + 0.3, "jingle"))
peaks = {}
for _, n in sfx_events:
    if n in peaks: continue
    out = subprocess.run(["ffmpeg", "-i", f"sfx/{n}.mp3", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    peaks[n] = float(out.split("max_volume:")[1].split("dB")[0])

inputs = ["-i", VO, "-i", f"{OUT}/music_bed.wav"]
fc = ["[0:a]aresample=44100,aformat=channel_layouts=stereo,asplit=2[vo][key]",
      "[1:a]volume=-15dB[mus]",
      "[mus][key]sidechaincompress=threshold=0.02:ratio=4:attack=80:release=600:makeup=1[duck]"]
mix = ["[vo]", "[duck]"]
for j, (t, n) in enumerate(sfx_events):
    inputs += ["-i", f"sfx/{n}.mp3"]
    g = SFX_GAIN.get(n, -9) - peaks[n]
    trim = ",atrim=0:4,afade=t=out:st=3:d=1" if n == "crickets" else ""
    fc.append(f"[{j + 2}:a]aresample=44100,aformat=channel_layouts=stereo{trim},volume={g:.1f}dB,adelay={int(t * 1000)}:all=1[s{j}]")
    mix.append(f"[s{j}]")
fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,apad=whole_dur={total:.3f},alimiter=limit=0.89:level=false[a]")
open(f"{OUT}/audio_graph.txt", "w").write(";".join(fc))
run(["ffmpeg", "-y", *inputs, "-filter_complex_script", f"{OUT}/audio_graph.txt", "-map", "[a]", "-t", f"{total:.3f}",
     "-c:a", "pcm_s16le", f"{OUT}/mix.wav"])

run(["ffmpeg", "-y", "-i", f"{OUT}/video.mp4", "-i", f"{OUT}/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", f"{OUT}/podcast_final.mp4"])

json.dump([dict(t=round(c["t"], 2), frames=c["n"], img=c["img"], sfx=c["sfx"]) for c in cues], open(f"{OUT}/timeline.json", "w"), indent=1)
print("scenes", len(cues), "sfx", len(sfx_events), "duration", total)
