import json, os, subprocess, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)
import check_tags_spoken as C
import el_common as E
import generate_tts as G
import join_clips as J


def tone(path, seconds, rate=44100, channels=1, freq=220):
    subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=f={freq}:d={seconds}", "-ar", str(rate), "-ac", str(channels), str(path)],
                   check=True)


# --- key -----------------------------------------------------------------------------------------

def test_key_from_env_wins(monkeypatch, tmp_path):
    f = tmp_path / "api_key"; f.write_text("sk_file\n")
    monkeypatch.setattr(E, "KEY_FILE", str(f))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_env")
    assert E.api_key() == "sk_env"


def test_key_falls_back_to_config_file(monkeypatch, tmp_path):
    f = tmp_path / "api_key"; f.write_text("  sk_file  \nignored\n")
    monkeypatch.setattr(E, "KEY_FILE", str(f))
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert E.api_key() == "sk_file"


def test_missing_key_exits_without_printing_a_key(monkeypatch, tmp_path):
    monkeypatch.setattr(E, "KEY_FILE", str(tmp_path / "nope"))
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(SystemExit) as e:
        E.api_key()
    assert "ELEVENLABS_API_KEY" in str(e.value) and str(tmp_path / "nope") in str(e.value)


# --- clip paths and text -------------------------------------------------------------------------

def test_clip_path_prefers_explicit_prefix_then_manifest_then_slide(tmp_path):
    (tmp_path / "_manifest.json").write_text(json.dumps({"01": {"file": "rollout-plan-01.mp3"}}))
    assert E.clip_path(str(tmp_path), "01", "part") == str(tmp_path / "part01.mp3")
    assert E.clip_path(str(tmp_path), "01") == str(tmp_path / "rollout-plan-01.mp3")
    assert E.clip_path(str(tmp_path), "02") == str(tmp_path / "slide02.mp3")
    assert E.clip_path(str(tmp_path), "01", "") == str(tmp_path / "01.mp3")


def test_spoken_chars_ignores_free_form_v4_tags():
    assert E.spoken_chars("[Warm, conversational tone] Hello. [Pause, dry amusement] Bye.") == len("Hello. Bye.")


def test_mmss():
    assert E.mmss(0) == "0:00" and E.mmss(89.6) == "1:30" and E.mmss(3725) == "62:05"


# --- join_clips ----------------------------------------------------------------------------------

def test_join_cmd_pads_all_but_last_and_closes_stdin():
    cmd = J.build_cmd(["a.mp3", "b.mp3", "c.mp3"], "out.mp3", 0.8)
    assert cmd[:2] == ["ffmpeg", "-nostdin"]
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count("apad=pad_dur=0.8") == 2 and "concat=n=3:v=0:a=1" in graph


def test_chapters_accumulate_lengths_and_gaps():
    rows = J.chapters(["a", "b", "c"], [10.0, 20.0, 5.0], 1.0)
    assert rows == [(0.0, "a"), (11.0, "b"), (32.0, "c")]


def test_join_mixed_rates_and_layouts(tmp_path, monkeypatch, capsys):
    a, b = tmp_path / "part01.mp3", tmp_path / "part02.mp3"
    tone(a, 2.0); tone(b, 1.5, rate=22050, channels=2, freq=330)
    out, ch = tmp_path / "brief.mp3", tmp_path / "ch.txt"
    monkeypatch.setattr(sys, "argv", ["join_clips.py", str(out), str(a), str(b), "--gap", "1.0",
                                      "--chapters", str(ch)])
    J.main()
    printed = capsys.readouterr().out
    assert "0:00  part01" in printed and "0:03  part02" in printed
    assert E.duration(str(out)) == pytest.approx(4.5, abs=0.3)
    assert "total 0:0" in ch.read_text()
    assert not (tmp_path / "brief.mp3.part.mp3").exists()


def test_join_refuses_to_overwrite_an_input(tmp_path, monkeypatch):
    a = tmp_path / "a.mp3"; tone(a, 1.0)
    monkeypatch.setattr(sys, "argv", ["join_clips.py", str(a), str(a)])
    with pytest.raises(SystemExit):
        J.main()


# --- generate_tts --------------------------------------------------------------------------------

def test_pace_outliers_flags_only_the_odd_clip():
    entries = {k: {"chars": c, "seconds": 10.0} for k, c in [("01", 140), ("02", 150), ("03", 145), ("04", 70)]}
    assert G.pace_outliers(entries) == ["04"]


def test_pace_outliers_needs_three_clips():
    assert G.pace_outliers({"01": {"chars": 10, "seconds": 10.0}, "02": {"chars": 90, "seconds": 10.0}}) == []


class FakeResp:
    def __init__(self, body): self.body = body; self.headers = {"request-id": "rid-1"}
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return self.body


def test_generate_writes_named_file_and_manifest(tmp_path, monkeypatch, capsys):
    scripts = tmp_path / "s.json"
    scripts.write_text(json.dumps({"rollout-plan-he": "[Warm, conversational tone] שלום לכולם."}))
    fake_mp3 = b"ID3" + b"\x00" * 31_997  # 32,000 bytes = 2.0 s at 128 kbit/s
    monkeypatch.setattr(G.urllib.request, "urlopen", lambda req, timeout=0: FakeResp(fake_mp3))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    out = tmp_path / "audio"
    monkeypatch.setattr(sys, "argv", ["generate_tts.py", str(scripts), "VOICE", str(out), "--prefix", "",
                                      "--language-code", "he"])
    G.main()
    printed = capsys.readouterr().out
    assert (out / "rollout-plan-he.mp3").exists()
    assert "0:02" in printed and "chars/s" in printed and "sk_test" not in printed
    m = json.load(open(out / "_manifest.json"))["rollout-plan-he"]
    assert m["file"] == "rollout-plan-he.mp3" and m["seconds"] == 2.0 and m["language_code"] == "he"
    assert m["chars"] == len("שלום לכולם.")
    # a later check/align run without --prefix finds the same file
    assert E.clip_path(str(out), "rollout-plan-he") == str(out / "rollout-plan-he.mp3")


# --- check_tags_spoken ---------------------------------------------------------------------------

def test_check_flags_leak():
    leaks, _, status, _ = C.check("[Warm, conversational tone] hello there", "conversational hello there", 1.15)
    assert status == "LEAK" and leaks == ["conversational"]


def test_check_flags_short_when_no_digits_explain_it():
    script = "one two three four five six seven eight nine ten"
    assert C.check(script, "one two three four five", 1.15)[2] == "SHORT"


def test_one_digit_does_not_hide_a_dropped_half():
    script = " ".join(f"word{chr(97 + i % 26)}" for i in range(40)).replace("word", "w")
    transcript = " ".join(script.split()[:15]) + " 2026"
    assert C.check(script, transcript, 1.15)[2] == "SHORT"


def test_check_digit_heavy_transcript_is_ok_with_a_note():
    script = "it cost eight hundred and eighty thousand shekels this month in total"
    _, ratio, status, note = C.check(script, "it cost 880,000 shekels this month in total", 1.15)
    assert status == "ok" and ratio < 0.9 and "digits" in note  # 880,000 counts as one word


def test_check_extra():
    assert C.check("hello there", "hello there friend of mine today", 1.15)[2] == "EXTRA"


def test_generate_only_regenerates_named_keys_and_keeps_the_manifest(tmp_path, monkeypatch):
    scripts = tmp_path / "s.json"
    scripts.write_text(json.dumps({"01": "one", "02": "two", "03": "three"}))
    out = tmp_path / "audio"; out.mkdir()
    (out / "_manifest.json").write_text(json.dumps({"01": {"file": "slide01.mp3", "model": "eleven_v4",
                                                           "stability": 0.5, "voice": "VOICE", "chars": 3,
                                                           "seconds": 1.0}}))
    sent = []
    def fake(req, timeout=0):
        sent.append(json.loads(req.data)["text"]); return FakeResp(b"ID3" + b"\x00" * 16_000)
    monkeypatch.setattr(G.urllib.request, "urlopen", fake)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    monkeypatch.setattr(sys, "argv", ["generate_tts.py", str(scripts), "VOICE", str(out), "--only", "03"])
    G.main()
    assert sent == ["three"]
    m = json.load(open(out / "_manifest.json"))
    assert set(m) == {"01", "03"} and m["03"]["file"] == "slide03.mp3"


def test_generate_only_rejects_unknown_keys(tmp_path, monkeypatch):
    scripts = tmp_path / "s.json"; scripts.write_text(json.dumps({"01": "one"}))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test")
    monkeypatch.setattr(sys, "argv", ["generate_tts.py", str(scripts), "V", str(tmp_path / "a"), "--only", "09"])
    with pytest.raises(SystemExit):
        G.main()
