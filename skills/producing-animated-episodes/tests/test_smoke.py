import json, os, subprocess, sys
import audio

EP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "episode.py")


def run(*args):
    return subprocess.run([sys.executable, EP, *map(str, args)], capture_output=True, text=True)


def test_demo_builds_end_to_end(tmp_path):
    r = run(tmp_path, "demo"); assert r.returncode == 0, r.stderr
    proj = tmp_path / "demo-episode"
    r = run(proj, "check"); assert r.returncode == 0, r.stdout + r.stderr
    r = run(proj, "build", "--workers", "2"); assert r.returncode == 0, r.stdout + r.stderr
    total = sum(s["dur"] for s in json.load(open(proj / "build" / "timeline.json")))
    v, a = audio.check_durations(str(proj / "build" / "demo.mp4"), total, 24)
    assert abs(v - total) < 0.07
    assert run(proj, "deliver").returncode == 0 and (proj / "build" / "demo_whatsapp.mp4").exists()
    assert run(proj, "sheet").returncode == 0 and (proj / "build" / "review" / "shots_0.jpg").exists()
    dump = json.loads(run(proj, "prompts").stdout)
    assert set(dump["panel_draft"]) == {"p01", "p02s"} and dump["lines"][0][0] == "01-1"


def test_rebuild_reuses_segments(tmp_path):
    run(tmp_path, "demo")
    proj = tmp_path / "demo-episode"
    assert run(proj, "build", "--workers", "2").returncode == 0
    r = run(proj, "build", "--workers", "2")
    assert r.returncode == 0 and "rendered" not in r.stdout          # cached segments, only concat + mix + mux
    r = run(proj, "build", "--only", "S01", "--workers", "1")
    assert r.returncode == 0 and "rendered S01" in r.stdout


def test_check_reports_missing_assets(tmp_path):
    run(tmp_path, "demo")
    proj = tmp_path / "demo-episode"
    os.remove(proj / "audio" / "lines" / "03-1.mp3")
    r = run(proj, "check")
    assert r.returncode == 1 and "03-1.mp3" in r.stdout and "1 blocker(s)" in r.stdout


def test_config_error_is_reported_before_work(tmp_path):
    run(tmp_path, "demo")
    proj = tmp_path / "demo-episode"
    cfg = json.load(open(proj / "episode.json"))
    cfg["shots"][0]["lines"] = ["99-9"]
    json.dump(cfg, open(proj / "episode.json", "w"), ensure_ascii=False)
    r = run(proj, "build")
    assert r.returncode == 1 and "unknown line 99-9" in r.stdout and not (proj / "build" / "seg").exists()


def test_check_warns_when_overlay_text_is_wider_than_the_frame(tmp_path):
    run(tmp_path, "demo")
    proj = tmp_path / "demo-episode"
    cfg = json.load(open(proj / "episode.json"))
    cfg["styles"]["title"]["size"] = 300
    json.dump(cfg, open(proj / "episode.json", "w"), ensure_ascii=False)
    r = run(proj, "check")
    assert "S01" in r.stdout and "wider than the frame" in r.stdout
    assert r.returncode == 0                       # a warning, not a blocker


def test_check_blocks_on_a_missing_subtitle_font(tmp_path):
    run(tmp_path, "demo")
    proj = tmp_path / "demo-episode"
    cfg = json.load(open(proj / "episode.json"))
    cfg["subtitle"] = {"font": "nosuchkey"}
    json.dump(cfg, open(proj / "episode.json", "w"), ensure_ascii=False)
    r = run(proj, "check")
    assert r.returncode == 1 and "nosuchkey" in r.stdout


def test_sheet_page_fits_its_shots(tmp_path):
    from PIL import Image
    run(tmp_path, "demo")
    proj = tmp_path / "demo-episode"
    assert run(proj, "build", "--workers", "2").returncode == 0
    assert run(proj, "sheet").returncode == 0
    im = Image.open(proj / "build" / "review" / "shots_0.jpg")
    assert im.height == 5 * (384 + 6)                              # the demo has 5 shots, not 6 rows
