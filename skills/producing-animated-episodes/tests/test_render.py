import os, subprocess
import numpy as np
import pytest
from PIL import Image
import render, timeline

DUR = {"01-1": 1.0, "02-1": 1.5, "02-2": 1.2, "02-3": 0.8}


def panels(ep):
    os.makedirs(ep.path("panels_final"), exist_ok=True)
    for pid, c in (("p01", (200, 60, 60)), ("p02", (40, 60, 90))):   # no channel near white: subtitles must stand out
        Image.new("RGB", (1152, 2048), c).save(ep.path("panels_final", f"{pid}.png"))


def raw_frames(path, idx, w=108, h=192):
    sel = "+".join(f"eq(n\\,{i})" for i in idx)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vf", f"select={sel},scale={w}:{h}",
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return [np.frombuffer(out[i * w * h * 3:(i + 1) * w * h * 3], np.uint8).reshape(h, w, 3).astype(int) for i in range(len(idx))]


def nframes(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                               "stream=nb_read_frames", "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def test_cam_helpers():
    assert render.cam_keys({"in": [1.2, .4, .3]}) == [(0, 1.0, .5, .5), (1, 1.2, .4, .3)]
    assert render.cam_keys({"out": [1.15]}) == [(0, 1.15, .5, .5), (1, 1.0, .5, .5)]
    assert render.cam_keys([[0, 1, .5, .5], [1, 2, .5, .5]]) == [(0, 1, .5, .5), (1, 2, .5, .5)]
    assert render.cam_keys(None) is None
    z, cx, cy = render.cam_at([(0, 1.0, .5, .5), (1, 2.0, .5, .5)], 0.5)
    assert z == pytest.approx(1.5)


def test_short_clip_holds_last_frame(tiny, tmp_path):
    panels(tiny)
    os.makedirs(tiny.path("clips"), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=288x512:rate=24",
                    "-frames:v", "12", "-pix_fmt", "yuv420p", tiny.path("clips", "S01.mp4")], check=True)
    shots, _ = timeline.build_timeline(tiny, DUR)
    s1 = dict(shots[0], clip_cam=[[0, 1, .5, .5], [1, 1, .5, .5]])
    render.render_shot((tiny, s1, str(tmp_path), True))
    seg = str(tmp_path / "seg" / "S01.mp4")
    assert nframes(seg) == s1["nframes"]
    a, b, c = raw_frames(seg, [5, 45, s1["nframes"] - 1])
    assert np.abs(b - c).max() <= 3          # held
    assert np.abs(a - b).max() > 30           # the clip did move before it ran out


def test_subtitle_visible_only_during_line(tiny, tmp_path):
    panels(tiny)
    shots, _ = timeline.build_timeline(tiny, DUR)
    s2 = shots[1]
    render.render_shot((tiny, s2, str(tmp_path), True))
    st, en = s2["placed"]["02-2"]
    before, during = raw_frames(str(tmp_path / "seg" / "S02.mp4"), [1, int((st + en) / 2 * 24)])
    band = slice(140, 160)                     # rows 1400-1600 of 1920, at 108x192
    assert during[band].max() > 200 and before[band].max() < 120


def test_render_all_skips_existing_and_concat(tiny, tmp_path):
    panels(tiny)
    shots, _ = timeline.build_timeline(tiny, DUR)
    os.makedirs(tmp_path / "seg")
    (tmp_path / "seg" / "S01.mp4").write_bytes(b"keep")
    done = render.render_all(tiny, shots, str(tmp_path), workers=2)
    assert sorted(done) == ["S02", "S03"] and (tmp_path / "seg" / "S01.mp4").read_bytes() == b"keep"
    render.render_shot((tiny, shots[0], str(tmp_path), True))
    video = render.concat(shots, str(tmp_path))
    assert nframes(video) == sum(s["nframes"] for s in shots)
