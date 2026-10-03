import io, json, os, subprocess, sys, urllib.error
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import lipsync_fal as LF
import lipsync_parts as LP
import omni_generate as OG
import take_sheet as TS


class Resp:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body


def lavfi_clip(path, frames, size="72x128", fps=24):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size={size}:rate={fps}", "-frames:v", str(frames), "-pix_fmt", "yuv420p", str(path)],
                   check=True)


def nframes(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                               "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                              capture_output=True, text=True).stdout)


# ---- omni_generate
def test_omni_body_shape():
    b = OG.build_body(b"jpg", "move", "9:16", "720p")
    assert b["model"] == "gemini-omni-1.1-flash"
    assert b["response_format"] == {"type": "video", "aspect_ratio": "9:16", "resolution": "720p"}
    assert b["input"][0]["mime_type"] == "image/jpeg" and b["input"][1] == {"type": "text", "text": "move"}
    assert b["store"] is False and b["background"] is False


def test_omni_extract_video():
    import base64
    js = {"steps": [{"type": "thought"}, {"type": "model_output", "content": [
        {"mime_type": "video/mp4", "data": base64.b64encode(b"MP4").decode()}]}]}
    assert OG.extract_video(js) == b"MP4" and OG.extract_video({"steps": []}) is None


def test_omni_generate_writes_clip_and_retries_429(tmp_path):
    import base64
    js = {"steps": [{"type": "model_output", "content": [{"mime_type": "video/mp4", "data": base64.b64encode(b"MP4").decode()}]}]}
    calls, slept = [], []
    def opener(req, timeout=0):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "busy", {}, io.BytesIO(b"rate"))
        return Resp(json.dumps(js).encode())
    out = tmp_path / "S1.mp4"
    msg = OG.generate({"x": 1}, "k", str(out), opener=opener, sleep=slept.append)
    assert msg.startswith("OK") and out.read_bytes() == b"MP4" and slept == [20]


def test_omni_http_error_leaves_no_file(tmp_path):
    def opener(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b'{"error":{"message":"API key not valid"}}'))
    msg = OG.generate({}, "k", str(tmp_path / "S1.mp4"), opener=opener)
    assert msg.startswith("HTTP 400") and "API key not valid" in msg and list(tmp_path.iterdir()) == []


def test_omni_main_skips_existing_takes(tmp_path, monkeypatch, capsys):
    (tmp_path / "p.png").write_bytes(b"x")
    (tmp_path / "S1_t1.mp4").write_bytes(b"old")
    (tmp_path / "jobs.json").write_text(json.dumps({"base": "B ", "jobs": {"S1": {"image": "p.png", "prompt": "P"}}}))
    made = []
    monkeypatch.setattr(OG, "to_jpeg", lambda p: b"jpg")
    monkeypatch.setattr(OG, "generate", lambda body, key, out, **k: (made.append((body["input"][1]["text"], out)), "OK 1s")[1])
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(sys, "argv", ["o", str(tmp_path / "jobs.json"), str(tmp_path), "--takes", "2"])
    OG.main()
    assert made == [("B P", str(tmp_path / "S1_t2.mp4"))]
    assert (tmp_path / "S1_t1.mp4").read_bytes() == b"old"


# ---- lipsync_fal
def test_parse_face_and_args():
    assert LF.parse_face("400,520@36") == ([400, 520], 36)
    a = LF.build_args("v", "a", ([400, 520], 36))
    assert a == {"video_url": "v", "audio_url": "a", "sync_mode": "cut_off", "options": {"active_speaker_detection":
                 {"auto_detect": False, "frame_number": 36, "coordinates": [400, 520]}}}
    assert "options" not in LF.build_args("v", "a")


def fal_opener(statuses, fail_on=None):
    seen = []
    def opener(req, timeout=0):
        url = req.full_url
        seen.append((req.get_method(), url))
        if fail_on and fail_on in url:
            raise urllib.error.HTTPError(url, 401, "no", {}, io.BytesIO(b'{"detail":"Invalid key"}'))
        if "/storage/auth/token?storage_type=fal-cdn-v3" in url:
            assert req.get_header("Authorization") == "Key k"
            return Resp(json.dumps({"token": "t", "token_type": "Bearer", "base_url": "https://v3.fal.media"}).encode())
        if url == "https://v3.fal.media/files/upload":
            assert req.get_method() == "POST" and req.get_header("Authorization") == "Bearer t"
            n = sum(u == url for _, u in seen)
            return Resp(json.dumps({"access_url": f"https://cdn/{n}"}).encode())
        if url == "https://queue.fal.run/fal-ai/sync-lipsync/v3":
            body = json.loads(req.data)
            assert body["video_url"] == "https://cdn/1" and body["audio_url"] == "https://cdn/2"
            return Resp(json.dumps({"request_id": "r1", "status_url": "https://q/status",
                                    "response_url": "https://q/resp"}).encode())
        if url == "https://q/status":
            return Resp(json.dumps({"status": statuses.pop(0)}).encode())
        if url == "https://q/resp":
            return Resp(json.dumps({"video": {"url": "https://cdn/out.mp4"}}).encode())
        if url == "https://cdn/out.mp4":
            return Resp(b"SYNCED")
        raise AssertionError(url)
    return opener, seen


def test_lipsync_run_uploads_submits_polls_downloads(tmp_path):
    v, a = tmp_path / "v.mp4", tmp_path / "a.wav"; v.write_bytes(b"v"); a.write_bytes(b"a")
    opener, seen = fal_opener(["IN_QUEUE", "IN_PROGRESS", "COMPLETED"])
    slept, out = [], tmp_path / "o.mp4"
    msg = LF.run(str(v), str(a), str(out), "k", face=([400, 520], 36), opener=opener, sleep=slept.append)
    assert msg == "OK" and out.read_bytes() == b"SYNCED" and len(slept) == 2


def test_lipsync_http_error_leaves_no_file(tmp_path):
    v, a = tmp_path / "v.mp4", tmp_path / "a.wav"; v.write_bytes(b"v"); a.write_bytes(b"a")
    opener, _ = fal_opener([], fail_on="auth/token")
    msg = LF.run(str(v), str(a), str(tmp_path / "o.mp4"), "k", opener=opener)
    assert msg.startswith("HTTP 401") and not (tmp_path / "o.mp4").exists()


def test_lipsync_failed_request_reports_error(tmp_path):
    v, a = tmp_path / "v.mp4", tmp_path / "a.wav"; v.write_bytes(b"v"); a.write_bytes(b"a")
    opener, _ = fal_opener([])
    base = opener
    def failing(req, timeout=0):
        if req.full_url == "https://q/status":
            return Resp(json.dumps({"status": "COMPLETED", "error": "no face found"}).encode())
        return base(req, timeout)
    msg = LF.run(str(v), str(a), str(tmp_path / "o.mp4"), "k", opener=failing)
    assert "no face found" in msg and not (tmp_path / "o.mp4").exists()


# ---- lipsync_parts
def L(i, s, e, **k):
    return {"id": i, "audio": f"{i}.mp3", "start": s, "end": e, **k}


def test_cuts_mid_gap():
    parts = LP.cuts([L("b", 2.4, 4.0), L("a", 0.5, 2.0)], 120, 24)
    assert [(l["id"], f0, f1) for l, f0, f1 in parts] == [("a", 0, 53), ("b", 53, 120)]


def test_cuts_overlap():
    parts = LP.cuts([L("a", 0.5, 2.5), L("b", 2.0, 4.0)], 120, 24)
    assert [(f0, f1) for _, f0, f1 in parts] == [(0, 48), (48, 120)]


def test_cuts_cover_every_frame():
    parts = LP.cuts([L("a", .3, 1.1), L("b", 1.0, 2.0), L("c", 2.6, 3.3)], 90, 24)
    assert parts[0][1] == 0 and parts[-1][2] == 90
    assert all(p[2] == q[1] for p, q in zip(parts, parts[1:]))


def test_split_writes_parts_and_plan(tmp_path):
    lavfi_clip(tmp_path / "shot.mp4", 72)
    for i in ("a", "b"):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=300:duration=0.8", str(tmp_path / f"{i}.mp3")], check=True)
    shot = {"id": "S1", "video": "shot.mp4", "fps": 24, "frames": 72, "size": "72x128",
            "lines": [L("a", 0.2, 1.0, speaker="maya"), L("b", 1.5, 2.3, speaker="ido", skip=True)]}
    plan = json.load(open(LP.split(shot, str(tmp_path / "parts"), str(tmp_path))))
    assert [(p["f0"], p["f1"], p["skip"]) for p in plan["parts"]] == [(0, 30, False), (30, 72, True)]
    assert nframes(plan["parts"][0]["video"]) == 30


def test_join_forces_exact_frame_counts(tmp_path):
    parts, synced = tmp_path / "parts", tmp_path / "synced"; parts.mkdir(); synced.mkdir()
    lavfi_clip(parts / "S1_0.mp4", 20); lavfi_clip(parts / "S1_1.mp4", 30)
    lavfi_clip(synced / "S1_1.mp4", 12)            # the model returned fewer frames than the part had
    plan = {"id": "S1", "fps": 24, "size": "72x128", "parts": [
        {"k": 0, "line": "a", "speaker": "maya", "f0": 0, "f1": 20, "mid": 10, "skip": False,
         "video": str(parts / "S1_0.mp4"), "audio": ""},
        {"k": 1, "line": "b", "speaker": "ido", "f0": 20, "f1": 50, "mid": 15, "skip": False,
         "video": str(parts / "S1_1.mp4"), "audio": ""}]}
    (parts / "S1_plan.json").write_text(json.dumps(plan))
    out = tmp_path / "S1.mp4"
    LP.join(str(parts / "S1_plan.json"), str(synced), str(out))
    assert nframes(out) == 50


def test_normalize_exact_frames_with_offset_and_hold(tmp_path):
    lavfi_clip(tmp_path / "clip.mp4", 48, size="144x256")
    LP.normalize(str(tmp_path / "clip.mp4"), str(tmp_path / "n.mp4"), 60, off=1.0, speed=1.0, size="72x128")
    assert nframes(tmp_path / "n.mp4") == 60      # only 24 source frames remain after the offset: the rest hold


# ---- take_sheet
def test_grid_times_and_box():
    assert TS.grid_times(6.0, 3) == [1.0, 3.0, 5.0]
    assert TS.box_for(10, 10, 140, 720, 1280) == (0, 0)
    assert TS.box_for(715, 1275, 140, 720, 1280) == (580, 1140)


def test_sheet_grid_size(tmp_path):
    lavfi_clip(tmp_path / "a.mp4", 24); lavfi_clip(tmp_path / "b.mp4", 24)
    TS.sheet(str(tmp_path / "s.jpg"), [str(tmp_path / "a.mp4"), str(tmp_path / "b.mp4")], [0.2, 0.6], width=72, pad=4)
    wh = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x",
                         str(tmp_path / "s.jpg")], capture_output=True, text=True).stdout.strip()
    assert wh == "148x260"


def test_sheet_past_end_gets_black_tile(tmp_path):
    lavfi_clip(tmp_path / "a.mp4", 12)              # 0.5 s long
    TS.sheet(str(tmp_path / "s.jpg"), [str(tmp_path / "a.mp4")], [0.1, 3.0], width=72, pad=4)
    assert (tmp_path / "s.jpg").exists()


def test_point_draws_frame(tmp_path):
    lavfi_clip(tmp_path / "a.mp4", 24, size="144x256")
    TS.point(str(tmp_path / "a.mp4"), str(tmp_path / "p.jpg"), 10, 70, 120, box=40)
    assert (tmp_path / "p.jpg").exists()


# ---- hand-off fixes (final review)
def two_part_plan(tmp_path, n0=20, n1=240, synced=(), synced_frames=24, skip1=False):
    parts, sync = tmp_path / "parts", tmp_path / "synced"; parts.mkdir(); sync.mkdir()
    lavfi_clip(parts / "S1_0.mp4", n0); lavfi_clip(parts / "S1_1.mp4", n1)
    for k in synced:
        lavfi_clip(sync / f"S1_{k}.mp4", synced_frames)
    plan = {"id": "S1", "fps": 24, "size": "72x128", "parts": [
        {"k": 0, "line": "a", "speaker": "maya", "f0": 0, "f1": n0, "mid": n0 // 2, "skip": False,
         "video": str(parts / "S1_0.mp4"), "audio": ""},
        {"k": 1, "line": "b", "speaker": "ido", "f0": n0, "f1": n0 + n1, "mid": n1 // 2, "skip": skip1,
         "video": str(parts / "S1_1.mp4"), "audio": ""}]}
    (parts / "S1_plan.json").write_text(json.dumps(plan))
    return str(parts / "S1_plan.json"), str(sync)


def test_join_holds_any_shortfall(tmp_path):
    plan, sync = two_part_plan(tmp_path, synced=(1,), synced_frames=24)   # 216 frames short: more than 5 s
    out = tmp_path / "S1.mp4"
    LP.join(plan, sync, str(out))
    assert nframes(out) == 260


def test_join_warns_for_each_unsynced_part(tmp_path, capsys):
    plan, sync = two_part_plan(tmp_path, n1=30, synced=(1,), synced_frames=30)
    LP.join(plan, sync, str(tmp_path / "S1.mp4"))
    err = capsys.readouterr().err
    assert "S1_0" in err and "maya" in err and "S1_1" not in err


def test_join_strict_refuses_unsynced(tmp_path):
    plan, sync = two_part_plan(tmp_path, n1=30, synced=(1,), synced_frames=30)
    with pytest.raises(RuntimeError, match="S1_0"):
        LP.join(plan, sync, str(tmp_path / "S1.mp4"), strict=True)


def test_skipped_part_is_not_reported_unsynced(tmp_path, capsys):
    plan, sync = two_part_plan(tmp_path, n1=30, synced=(0,), synced_frames=20, skip1=True)
    LP.join(plan, sync, str(tmp_path / "S1.mp4"), strict=True)
    assert "S1_1" not in capsys.readouterr().err


def test_split_writes_ready_jobs_file(tmp_path):
    lavfi_clip(tmp_path / "shot.mp4", 72)
    for i in ("a", "b"):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=300:duration=0.8", str(tmp_path / f"{i}.mp3")], check=True)
    shot = {"id": "S1", "video": "shot.mp4", "fps": 24, "frames": 72, "size": "72x128",
            "lines": [L("a", 0.2, 1.0, speaker="maya"), L("b", 1.5, 2.3, speaker="ido", skip=True)]}
    LP.split(shot, str(tmp_path / "parts"), str(tmp_path))
    jobs = json.load(open(tmp_path / "parts" / "S1_lipsync_jobs.json"))
    assert len(jobs) == 1                                    # the skipped part is not paid for
    j = jobs[0]
    assert j["out"] == str(tmp_path / "synced" / "S1_0.mp4") and j["face"] is None and j["mid"] == 15
    assert os.path.isabs(j["video"]) and j["speaker"] == "maya"


def test_lipsync_force_reruns_existing(tmp_path, monkeypatch):
    (tmp_path / "o.mp4").write_bytes(b"old")
    ran = []
    monkeypatch.setattr(LF, "run", lambda *a, **k: (ran.append(a[2]), "OK")[1])
    monkeypatch.setenv("FAL_KEY", "k")
    monkeypatch.setattr(sys, "argv", ["l", "v.mp4", "a.wav", str(tmp_path / "o.mp4"), "--force"])
    LF.main()
    assert ran == [str(tmp_path / "o.mp4")]


# ---- network resilience (final review)
def flaky(opener, url_part, errors):
    """Wrap a fake opener so requests whose URL contains url_part raise the given errors first."""
    errs = list(errors)
    def wrapped(req, timeout=0):
        if url_part in req.full_url and errs:
            raise errs.pop(0)
        return opener(req, timeout)
    return wrapped


def http_err(code):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b"busy"))


def setup_files(tmp_path):
    v, a = tmp_path / "v.mp4", tmp_path / "a.wav"; v.write_bytes(b"v"); a.write_bytes(b"a")
    return str(v), str(a)


def test_lipsync_poll_survives_transient_errors(tmp_path):
    v, a = setup_files(tmp_path)
    base, _ = fal_opener(["IN_PROGRESS", "COMPLETED"])
    opener = flaky(base, "https://q/status", [http_err(503), urllib.error.URLError("reset")])
    slept = []
    msg = LF.run(v, a, str(tmp_path / "o.mp4"), "k", opener=opener, sleep=slept.append)
    assert msg == "OK" and (tmp_path / "o.mp4").read_bytes() == b"SYNCED"


def test_lipsync_failure_after_submit_keeps_request_id(tmp_path):
    v, a = setup_files(tmp_path)
    base, _ = fal_opener(["COMPLETED"])
    opener = flaky(base, "https://q/resp", [http_err(502)] * 10)
    msg = LF.run(v, a, str(tmp_path / "o.mp4"), "k", opener=opener, sleep=lambda s: None)
    assert "r1" in msg and "https://q/resp" in msg and not (tmp_path / "o.mp4").exists()


def test_lipsync_network_error_is_a_status_line(tmp_path):
    v, a = setup_files(tmp_path)
    base, _ = fal_opener([])
    opener = flaky(base, "auth/token", [urllib.error.URLError("no route")] * 10)
    msg = LF.run(v, a, str(tmp_path / "o.mp4"), "k", opener=opener, sleep=lambda s: None)
    assert "no route" in msg and not (tmp_path / "o.mp4").exists()


def test_lipsync_main_reports_unexpected_errors(tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise KeyError("video")
    monkeypatch.setattr(LF, "run", boom)
    monkeypatch.setenv("FAL_KEY", "k")
    monkeypatch.setattr(sys, "argv", ["l", "v.mp4", "a.wav", str(tmp_path / "o.mp4")])
    with pytest.raises(SystemExit) as e:
        LF.main()
    assert "o.mp4" in str(e.value) and "KeyError" in capsys.readouterr().out


def test_omni_retries_network_errors(tmp_path):
    import base64
    js = {"steps": [{"type": "model_output", "content": [{"mime_type": "video/mp4", "data": base64.b64encode(b"MP4").decode()}]}]}
    calls = []
    def opener(req, timeout=0):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.URLError("connection reset")
        return Resp(json.dumps(js).encode())
    msg = OG.generate({}, "k", str(tmp_path / "S1.mp4"), opener=opener, sleep=lambda s: None)
    assert msg.startswith("OK") and len(calls) == 2


def test_omni_persistent_network_error_is_a_status_line(tmp_path):
    def opener(req, timeout=0):
        raise urllib.error.URLError("no route")
    msg = OG.generate({}, "k", str(tmp_path / "S1.mp4"), opener=opener, sleep=lambda s: None)
    assert "no route" in msg and list(tmp_path.iterdir()) == []


def test_normalize_crops_instead_of_stretching(tmp_path):
    # 16:9 source: black, with a centered white square. Squashed into 72x128 the square becomes a narrow tall bar
    # and the left edge stays black; cover-and-crop fills the whole width with the square instead.
    src = tmp_path / "wide.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=black:s=160x90:r=24",
                    "-vf", "drawbox=x=35:y=0:w=90:h=90:color=white:t=fill", "-frames:v", "24", "-pix_fmt", "yuv420p", str(src)],
                   check=True)
    LP.normalize(str(src), str(tmp_path / "n.mp4"), 24, size="72x128")
    px = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(tmp_path / "n.mp4"), "-vf",
                         "select=eq(n\\,0),crop=2:2:2:64", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                        capture_output=True).stdout
    assert px[0] > 200, px[0]
