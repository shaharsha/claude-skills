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


def prepared(ep, shots, sid="S02"):
    """What `lipsync prep` records after cutting a shot's parts."""
    s = {x["id"]: x for x in shots}[sid]
    os.makedirs(ep.path("lipsync", "parts"), exist_ok=True)
    json.dump(lipsync.inputs(ep, s), open(ep.path("lipsync", "parts", f"{sid}_inputs.json"), "w"))


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
    prepared(tiny, shots)
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


def test_stale_synced_parts_are_retired(tiny):
    shots = setup(tiny, faces={"S02|0": [400, 500]})
    s2 = shots[1]
    for name in ("S02_0.mp4", "S02_1.mp4"):
        lavfi(tiny.path("lipsync", "out", name), 10)
    lavfi(tiny.path("lipsync", "final", "S02.mp4"), s2["nframes"])
    json.dump({"old": True}, open(tiny.path("lipsync", "final", "S02.json"), "w"))
    assert lipsync.retire_stale(tiny, s2) is True
    assert not os.path.exists(tiny.path("lipsync", "out", "S02_0.mp4"))
    assert not os.path.exists(tiny.path("lipsync", "final", "S02.mp4"))
    assert os.listdir(tiny.path("lipsync", "out", "_old"))
    json.dump(lipsync.manifest(tiny, s2), open(tiny.path("lipsync", "final", "S02.json"), "w"))
    lavfi(tiny.path("lipsync", "final", "S02.mp4"), s2["nframes"])
    assert lipsync.retire_stale(tiny, s2) is False                     # current: kept


def test_run_skips_a_shot_changed_since_prep(tiny, monkeypatch, capsys):
    shots = setup(tiny, faces={"S02|0": [400, 500]})
    prepared(tiny, shots)
    shots[1]["clip_off"] = 0.5                                          # changed after prep
    calls = []
    monkeypatch.setattr(lipsync.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    lipsync.run(tiny, shots)
    assert not calls and "lipsync prep S02" in capsys.readouterr().out


def test_run_resyncs_a_part_whose_face_point_changed(tiny, monkeypatch, capsys):
    shots = setup(tiny, faces={"S02|0": [400, 500]})
    prepared(tiny, shots)
    lavfi(tiny.path("lipsync", "out", "S02_0.mp4"), 10)                 # synced with the old point
    rec = lipsync.manifest(tiny, shots[1])
    rec["faces"] = {"S02|0": [100, 100]}
    os.makedirs(tiny.path("lipsync", "final"), exist_ok=True)
    json.dump(rec, open(tiny.path("lipsync", "final", "S02.json"), "w"))
    calls = []
    monkeypatch.setattr(lipsync.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    lipsync.run(tiny, shots)
    assert not os.path.exists(tiny.path("lipsync", "out", "S02_0.mp4")) and calls
    assert "about $0.00" not in capsys.readouterr().out                 # the part is priced again
