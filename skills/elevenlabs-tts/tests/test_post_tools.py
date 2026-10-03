import io, json, os, subprocess, sys, urllib.error
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
import ab_concat as A
import generate_music_and_sfx as M
import level_clips as L
import trim_to_words as T


class Resp:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body


def tone(path, seconds=1.0, amp_db=-20, freq=220):
    """A sine whose PEAK is amp_db dBFS (lavfi 'sine' is fixed at amplitude 1/8, so use aevalsrc)."""
    amp = 10 ** (amp_db / 20)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"aevalsrc={amp}*sin(2*PI*{freq}*t):s=44100:d={seconds}", str(path)], check=True)


def test_word_window_pads_and_clamps():
    words = [{"text": " ", "start": 0.0, "end": 0.3}, {"text": "hello", "start": 0.52, "end": 1.09}]
    assert T.word_window(words, 1.15) == pytest.approx((0.48, 1.15))


def test_word_window_no_words_raises():
    with pytest.raises(ValueError):
        T.word_window([{"text": " ", "start": 0.0, "end": 1.0}], 1.0)


def test_trim_cut_keeps_window(tmp_path):
    src, dst = tmp_path / "a.mp3", tmp_path / "b.mp3"
    tone(src, 2.0)
    T.cut(str(src), str(dst), 0.5, 1.2)
    assert abs(T.duration(str(dst)) - 0.7) < 0.06
    assert not (tmp_path / "b.mp3.part.mp3").exists()


def test_trim_main_reports_and_continues(tmp_path, monkeypatch):
    raw, out = tmp_path / "raw", tmp_path / "out"; raw.mkdir()
    tone(raw / "a.mp3"); tone(raw / "b.mp3")
    (tmp_path / "s.json").write_text(json.dumps({"a": "[sighs] one", "b": "two"}))
    def fake_align(mp3, text, key, retries=3):
        return {"words": [] if mp3.endswith("a.mp3") else [{"text": "two", "start": 0.2, "end": 0.6}]}
    monkeypatch.setattr(T, "align", fake_align)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(sys, "argv", ["trim_to_words.py", str(tmp_path / "s.json"), str(raw), str(out)])
    with pytest.raises(SystemExit) as e:
        T.main()
    assert "['a']" in str(e.value)                 # the failed clip is named
    assert (out / "b.mp3").exists() and not (out / "a.mp3").exists()
    assert (raw / "a.mp3").exists()                # original untouched


def test_parse_volumedetect():
    err = ("[Parsed_volumedetect_1 @ 0x1] mean_volume: -23.4 dB\n"
           "[Parsed_volumedetect_1 @ 0x1] max_volume: -4.1 dB\n")
    assert L.parse_volumedetect(err) == (-23.4, -4.1)


def test_gain_for_hits_target_unless_peak_limits():
    assert L.gain_for(-24.0, -10.0) == pytest.approx(6.0)
    assert L.gain_for(-30.0, -2.0) == pytest.approx(7.0)   # peak may rise to +5 dB, the limiter catches it


def test_weak_spots_flags_sagging_word_not_pauses():
    rms = [-70, -20, -21, -19, -38, -20, -50, -22, -70]    # index 4: a swallowed word; index 6: a pause
    assert L.weak_spots(rms) == [0.6]


def test_level_brings_clips_to_target(tmp_path):
    src, out = tmp_path / "in", tmp_path / "out"; src.mkdir()
    tone(src / "quiet.mp3", amp_db=-30); tone(src / "loud.mp3", amp_db=-12)
    subprocess.run([sys.executable, os.path.join(SCRIPTS, "level_clips.py"), str(src), str(out)], check=True)
    for f in ("quiet.mp3", "loud.mp3"):
        assert abs(L.voiced_levels(str(out / f))[0] - (-18.0)) < 1.0


def test_level_refuses_to_overwrite_originals(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "level_clips.py"), str(tmp_path), str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "out_dir" in r.stderr


def test_ab_starts_and_labels():
    assert A.starts([1.5, 2.0, 0.7]) == [0.0, 2.5, 5.5]
    assert A.mmss(65.5) == "1:05.50"


def test_music_request_forces_v2_5_and_instrumental():
    url, body = M.request_for("op", {"type": "music", "prompt": "x", "seconds": 52})
    assert url == "https://api.elevenlabs.io/v1/music"
    assert body == {"prompt": "x", "music_length_ms": 52000, "model_id": "music_v2_5", "force_instrumental": True}


def test_sfx_request():
    url, body = M.request_for("w", {"type": "sfx", "prompt": "whoosh", "seconds": 1.0})
    assert url == "https://api.elevenlabs.io/v1/sound-generation"
    assert body == {"text": "whoosh", "duration_seconds": 1.0, "prompt_influence": 0.5}


def test_bad_type_raises():
    with pytest.raises(ValueError):
        M.request_for("x", {"type": "speech", "prompt": "", "seconds": 1})


def test_post_writes_real_mp3_only(tmp_path):
    out = tmp_path / "op.mp3"
    msg = M.post("https://example.test/m", {}, str(out), "k", opener=lambda req, timeout=0: Resp(b"ID3" + b"\0" * 3000))
    assert msg.startswith("OK") and out.read_bytes()[:3] == b"ID3"


def test_http_error_leaves_no_file(tmp_path):
    def opener(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 402, "Payment Required", {},
                                     io.BytesIO(b'{"detail":{"status":"paid_plan_required"}}'))
    out = tmp_path / "op.mp3"
    msg = M.post("https://api.elevenlabs.io/v1/music", {"prompt": "x"}, str(out), "k", opener=opener)
    assert "402" in msg and "paid_plan_required" in msg
    assert list(tmp_path.iterdir()) == []


def test_post_retries_429_then_succeeds(tmp_path):
    calls, slept = [], []
    def opener(req, timeout=0):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "busy", {}, io.BytesIO(b"busy"))
        return Resp(b"ID3" + b"\0" * 3000)
    msg = M.post("https://example.test/m", {}, str(tmp_path / "a.mp3"), "k", opener=opener, sleep=slept.append)
    assert msg.startswith("OK") and slept == [5]


def test_music_skips_existing(tmp_path, monkeypatch, capsys):
    (tmp_path / "op.mp3").write_bytes(b"ID3old")
    spec = tmp_path / "s.json"; spec.write_text(json.dumps({"op": {"type": "music", "prompt": "x", "seconds": 10}}))
    monkeypatch.setattr(M, "post", lambda *a, **k: pytest.fail("must not call the API for an existing file"))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(sys, "argv", ["g", str(spec), str(tmp_path)])
    M.main()
    assert "exists" in capsys.readouterr().out and (tmp_path / "op.mp3").read_bytes() == b"ID3old"


def test_post_network_error_is_retried_then_reported(tmp_path):
    calls = []
    def opener(req, timeout=0):
        calls.append(1)
        raise urllib.error.URLError("no route")
    msg = M.post("https://example.test/m", {}, str(tmp_path / "a.mp3"), "k", opener=opener, sleep=lambda s: None)
    assert "no route" in msg and len(calls) == 5 and list(tmp_path.iterdir()) == []


def test_level_continues_past_a_silent_clip(tmp_path):
    src, out = tmp_path / "in", tmp_path / "out"; src.mkdir()
    tone(src / "a.mp3", amp_db=-20)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", "1", str(src / "b.mp3")], check=True)          # nothing above -45 dB
    tone(src / "c.mp3", amp_db=-25)
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "level_clips.py"), str(src), str(out)], capture_output=True, text=True)
    assert r.returncode != 0 and "b" in r.stderr + r.stdout and "Traceback" not in r.stderr
    assert (out / "a.mp3").exists() and (out / "c.mp3").exists() and not (out / "b.mp3").exists()
