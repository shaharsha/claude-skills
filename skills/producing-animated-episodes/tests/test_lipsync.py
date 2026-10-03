import json, os, subprocess
import lipsync, timeline

DUR = {"01-1": 1.0, "02-1": 1.5, "02-2": 1.2, "02-3": 0.8}


def lavfi(path, frames, size="72x128"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=24",
                    "-frames:v", str(frames), "-pix_fmt", "yuv420p", path], check=True)


def nframes(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                               "stream=nb_read_frames", "-of", "csv=p=0", path], capture_output=True, text=True).stdout)


def setup(ep, faces=None):
    ep.data["lipsync"] = {"shots": ["S02"], "skip": [["S02", "02-3"]], "faces": faces or {}}
    return timeline.build_timeline(ep, DUR)[0]


def test_plan_parts_cover_shot_and_mark_skips(tiny):
    shots = setup(tiny)
    parts = lipsync.plan_parts(tiny, shots)
    s2 = shots[1]
    assert [(p["line"], p["who"], p["skip"]) for p in parts] == [("02-1", "maya", False), ("02-2", "ido", False), ("02-3", "ALL", True)]
    assert parts[0]["f0"] == 0 and parts[-1]["f1"] == s2["nframes"]
    assert all(a["f1"] == b["f0"] for a, b in zip(parts, parts[1:]))
    assert parts[2]["f0"] == round(s2["placed"]["02-3"][0] * 24)   # overlapping line: cut at its start


def test_run_builds_jobs_only_for_faced_parts(tiny, monkeypatch, capsys):
    shots = setup(tiny, faces={"S02|0": [400, 500]})
    calls = []
    monkeypatch.setattr(lipsync.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    lipsync.run(tiny, shots)
    jobs = json.load(open(calls[0][calls[0].index("--jobs") + 1]))
    mid = lipsync.plan_parts(tiny, shots)[0]["mid"]
    assert [j["face"] for j in jobs] == [f"400,500@{mid}"]
    assert jobs[0]["out"].endswith("video/lipsync/out/S02_0.mp4")
    out = capsys.readouterr().out
    assert "S02|1" in out                                         # a speaking part without a face point is reported
    assert "about $" in out                                       # the cost is shown before anything is submitted


def test_join_one_is_frame_exact(tiny, tmp_path):
    shots = setup(tiny)
    s2 = shots[1]
    for p in lipsync.plan_parts(tiny, shots):
        lavfi(tiny.path("lipsync", "parts", f"S02_{p['k']}.mp4"), p["f1"] - p["f0"])
    lavfi(tiny.path("lipsync", "out", "S02_1.mp4"), 5)              # synced part came back too short
    out = str(tmp_path / "S02.mp4")
    tiny.video["clip_size"] = [72, 128]
    lipsync.join_one(tiny, shots, "S02", out)
    assert nframes(out) == s2["nframes"]
