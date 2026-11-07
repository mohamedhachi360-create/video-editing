"""Build an editable CapCut project (draft) for the three-card motion graphic.

Run render_video.py first. Writes "output/Three Cards Motion - CapCut project.zip" with the draft
folder, its media and a Windows installer. CapCut only accepts absolute media paths, so the draft
stores PATH_TOKEN and the installer swaps in the real folder on the user's PC.
"""
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path

import pycapcut as cc
from pycapcut import ClipSettings, FontType, KeyframeProperty as KP, TextStyle, Timerange

import motion as m

HERE = Path(__file__).resolve().parent
MEDIA = HERE / "build" / "capcut_media"
DRAFTS = HERE / "build" / "drafts"
INSTALLER = HERE / "installer"
PROJECT = "Three Cards Motion"
ZIP_PATH = HERE / "output" / f"{PROJECT} - CapCut project.zip"
PATH_TOKEN = "__PROJECT_DIR__"
REST_T = 4.95  # a moment where every card is on screen; used for the non-keyframed clip settings
# Approximate mapping between CapCut text size and font pixel size on the canvas.
TEXT_SIZE = round(m.NUMBER_EM_PX * 160 / m.H, 1)
# Maximum interpolation error allowed when thinning keyframes (CapCut units).
TOLERANCE = {KP.position_x: 0.6 / (m.W / 2), KP.position_y: 0.6 / (m.H / 2), KP.rotation: 0.15,
             KP.uniform_scale: 0.003, KP.alpha: 0.01}


def us(seconds):
    return round(seconds * 1_000_000)


def to_capcut(tr):
    """Pixel transform -> CapCut values (half-canvas units, y up, clockwise degrees)."""
    return {
        KP.position_x: (tr.x - m.W / 2) / (m.W / 2),
        KP.position_y: -(tr.y - m.H / 2) / (m.H / 2),
        KP.rotation: tr.rotation,
        KP.uniform_scale: max(tr.scale, 0.01),
        KP.alpha: tr.alpha,
    }


def clip(values):
    s = values[KP.uniform_scale]
    return ClipSettings(transform_x=values[KP.position_x], transform_y=values[KP.position_y],
                        rotation=values[KP.rotation], scale_x=s, scale_y=s, alpha=values[KP.alpha])


def simplify(ts, vs, tol):
    """Indices of samples to keep so linear interpolation stays within tol (Douglas-Peucker)."""
    keep, stack = {0, len(ts) - 1}, [(0, len(ts) - 1)]
    while stack:
        a, b = stack.pop()
        worst, idx = tol, None
        for k in range(a + 1, b):
            err = abs(vs[k] - (vs[a] + (vs[b] - vs[a]) * (ts[k] - ts[a]) / (ts[b] - ts[a])))
            if err > worst:
                worst, idx = err, k
        if idx is not None:
            keep.add(idx)
            stack += [(a, idx), (idx, b)]
    return sorted(keep)


def animate(segment, span, transform, props):
    start, end = span
    n = round((end - start) * m.FPS)
    ts = [start + k / m.FPS for k in range(n)] + [end]
    samples = [to_capcut(transform(t)) for t in ts]
    count = 0
    for prop in props:
        vs = [s[prop] for s in samples]
        if max(vs) - min(vs) <= TOLERANCE[prop]:
            continue
        for k in simplify(ts, vs, TOLERANCE[prop]):
            segment.add_keyframe(prop, us(ts[k] - start), vs[k])
            count += 1
    return count


def build_draft():
    if DRAFTS.exists():
        shutil.rmtree(DRAFTS)
    DRAFTS.mkdir(parents=True)
    script = cc.DraftFolder(str(DRAFTS)).create_draft(PROJECT, m.W, m.H, fps=m.FPS)
    draft_dir = DRAFTS / PROJECT
    media = draft_dir / "media"
    media.mkdir()
    for name in ("background.mp4", "card_1.png", "card_2.png", "card_3.png"):
        shutil.copy(MEDIA / name, media / name)
    shutil.copy(MEDIA / "cover.jpg", draft_dir / "draft_cover.jpg")

    script.add_track(cc.TrackType.video, "Background")
    for i in range(3):
        script.add_track(cc.TrackType.video, f"Card {i + 1}", relative_index=i + 1)
    for i in range(3):
        script.add_track(cc.TrackType.text, f"Number {i + 1}", relative_index=i + 1)

    bg = cc.VideoMaterial(str(media / "background.mp4"), material_name="Background")
    script.add_segment(cc.VideoSegment(bg, Timerange(0, min(bg.duration, us(m.DURATION)))), "Background")

    keyframes = 0
    for i in range(3):
        span = m.card_span(i)
        material = cc.VideoMaterial(str(media / f"card_{i + 1}.png"), material_name=f"Card {i + 1}")
        card = cc.VideoSegment(material, Timerange(us(span[0]), us(span[1] - span[0])),
                               clip_settings=clip(to_capcut(m.card_transform(i, REST_T))))
        keyframes += animate(card, span, lambda t, i=i: m.card_transform(i, t),
                             (KP.position_x, KP.position_y, KP.rotation, KP.uniform_scale, KP.alpha))
        script.add_segment(card, f"Card {i + 1}")

        # CapCut has no opacity keyframes for text, so numbers appear and leave by scale only.
        span = m.number_span(i)
        text = cc.TextSegment(m.LABELS[i], Timerange(us(span[0]), us(span[1] - span[0])),
                              font=FontType.Poppins_Bold,
                              style=TextStyle(size=TEXT_SIZE, color=(1.0, 1.0, 1.0), align=1),
                              clip_settings=clip(to_capcut(m.number_transform(i, REST_T))))
        keyframes += animate(text, span, lambda t, i=i: m.number_transform(i, t),
                             (KP.position_x, KP.position_y, KP.rotation, KP.uniform_scale))
        script.add_segment(text, f"Number {i + 1}")

    script.save()
    print(f"draft: {len(script.tracks)} tracks, {keyframes} keyframes, {script.duration / 1e6:.2f} s")
    return draft_dir, script.duration


def relocate_media(draft_dir):
    path = draft_dir / "draft_content.json"
    content = json.loads(path.read_text("utf-8"))
    local = os.path.abspath(draft_dir)
    for video in content["materials"]["videos"]:
        if not video["path"].startswith(local):
            raise SystemExit(f"unexpected material path {video['path']}")
        video["path"] = PATH_TOKEN + video["path"][len(local):].replace("\\", "/")
    text = json.dumps(content, ensure_ascii=False, indent=4)
    if local in text:
        raise SystemExit("draft still contains a build-machine path")
    path.write_text(text, "utf-8")


def write_meta(draft_dir, duration):
    path = draft_dir / "draft_meta_info.json"
    meta = json.loads(path.read_text("utf-8"))
    meta.update(draft_id=str(uuid.uuid4()).upper(), draft_name=PROJECT,
                draft_cover="draft_cover.jpg", tm_duration=duration)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=4), "utf-8")


def package(draft_dir):
    ZIP_PATH.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(INSTALLER.iterdir()):
            # Windows tools expect CRLF line endings.
            zf.writestr(f.name, f.read_text("utf-8").replace("\r\n", "\n").replace("\n", "\r\n"))
        for f in sorted(draft_dir.rglob("*")):
            if f.is_file():
                zf.write(f, f"{PROJECT}/{f.relative_to(draft_dir).as_posix()}")
    print(f"wrote {ZIP_PATH.relative_to(HERE)} ({ZIP_PATH.stat().st_size / 1e6:.1f} MB)")


def main():
    draft_dir, duration = build_draft()
    relocate_media(draft_dir)
    write_meta(draft_dir, duration)
    package(draft_dir)


if __name__ == "__main__":
    main()
