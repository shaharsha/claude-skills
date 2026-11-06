import json, os, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import renumber_slides as R


def deck(tmp_path, n=4):
    audio = tmp_path / "audio"; audio.mkdir()
    al = tmp_path / "alignment"; al.mkdir()
    scripts = {f"{i:02d}": f"script {i}" for i in range(1, n + 1)}
    manifest = {f"{i:02d}": {"file": f"slide{i:02d}.mp3", "voice": "V", "stability": 0.5} for i in range(1, n + 1)}
    for i in range(1, n + 1):
        (audio / f"slide{i:02d}.mp3").write_text(f"audio {i}")
        (al / f"slide{i:02d}.json").write_text(f"align {i}")
    (tmp_path / "scripts.json").write_text(json.dumps(scripts))
    (audio / "_manifest.json").write_text(json.dumps(manifest))
    return tmp_path


def run(monkeypatch, root, *args):
    monkeypatch.setattr(sys, "argv", ["renumber_slides.py", str(root / "scripts.json"), str(root / "audio"),
                                      "--alignment", str(root / "alignment"), *args])
    R.main()


def test_plan_insert_and_delete():
    keys = {"01", "02", "03", "04"}
    assert R.plan(keys, "insert", 3) == {"03": "04", "04": "05"}
    assert R.plan(keys, "delete", 2) == {"02": None, "03": "02", "04": "03"}


def test_insert_frees_the_slot_and_keeps_audio_with_its_script(tmp_path, monkeypatch):
    root = deck(tmp_path)
    run(monkeypatch, root, "--insert", "3")
    s = json.load(open(root / "scripts.json"))
    m = json.load(open(root / "audio" / "_manifest.json"))
    assert sorted(s) == ["01", "02", "04", "05"] and s["04"] == "script 3" and s["05"] == "script 4"
    assert (root / "audio" / "slide04.mp3").read_text() == "audio 3"
    assert (root / "audio" / "slide05.mp3").read_text() == "audio 4"
    assert not (root / "audio" / "slide03.mp3").exists()
    assert m["04"]["file"] == "slide04.mp3" and "03" not in m
    assert (root / "alignment" / "slide05.json").read_text() == "align 4"


def test_delete_moves_the_clip_aside_and_closes_the_gap(tmp_path, monkeypatch):
    root = deck(tmp_path)
    run(monkeypatch, root, "--delete", "2")
    s = json.load(open(root / "scripts.json"))
    assert sorted(s) == ["01", "02", "03"] and s["02"] == "script 3"
    assert (root / "audio" / "removed" / "slide02.mp3").read_text() == "audio 2"
    assert (root / "audio" / "removed" / "slide02.manifest.json").exists()
    assert (root / "audio" / "slide02.mp3").read_text() == "audio 3"
    assert not (root / "audio" / "slide04.mp3").exists()


def test_dry_run_changes_nothing(tmp_path, monkeypatch):
    root = deck(tmp_path)
    before = sorted(os.listdir(root / "audio"))
    run(monkeypatch, root, "--insert", "1", "--dry-run")
    assert sorted(os.listdir(root / "audio")) == before
    assert sorted(json.load(open(root / "scripts.json"))) == ["01", "02", "03", "04"]


def test_plan_keeps_each_keys_own_padding():
    keys = {str(i) for i in range(1, 13)}
    assert R.plan(keys, "insert", 5) == {str(i): str(i + 1) for i in range(5, 13)}
    keys3 = {f"{i:02d}" for i in range(1, 100)} | {"100"}
    m = R.plan(keys3, "insert", 98)
    assert m == {"98": "99", "99": "100", "100": "101"}


def test_unpadded_keys_insert_end_to_end(tmp_path, monkeypatch):
    audio = tmp_path / "audio"; audio.mkdir()
    scripts = {str(i): f"script {i}" for i in range(1, 13)}
    for i in range(1, 13):
        (audio / f"slide{i}.mp3").write_text(f"audio {i}")
    (tmp_path / "scripts.json").write_text(json.dumps(scripts))
    monkeypatch.setattr(sys, "argv", ["r", str(tmp_path / "scripts.json"), str(audio), "--insert", "5"])
    R.main()
    s = json.load(open(tmp_path / "scripts.json"))
    assert "5" not in s and s["6"] == "script 5" and s["13"] == "script 12"
    assert (audio / "slide13.mp3").read_text() == "audio 12" and not (audio / "slide5.mp3").exists()


def test_manifest_file_names_are_followed_not_the_prefix(tmp_path, monkeypatch):
    audio = tmp_path / "audio"; audio.mkdir()
    (tmp_path / "scripts.json").write_text(json.dumps({"01": "a", "02": "b"}))
    (audio / "_manifest.json").write_text(json.dumps({"01": {"file": "narr01.mp3"}, "02": {"file": "narr02.mp3"}}))
    (audio / "narr01.mp3").write_text("A"); (audio / "narr02.mp3").write_text("B")
    monkeypatch.setattr(sys, "argv", ["r", str(tmp_path / "scripts.json"), str(audio), "--insert", "2"])
    R.main()
    m = json.load(open(audio / "_manifest.json"))
    assert m["03"]["file"] == "narr03.mp3" and (audio / "narr03.mp3").read_text() == "B"
    assert not (audio / "narr02.mp3").exists()


def test_missing_manifest_clip_aborts_before_changing_anything(tmp_path, monkeypatch):
    audio = tmp_path / "audio"; audio.mkdir()
    (tmp_path / "scripts.json").write_text(json.dumps({"01": "a", "02": "b"}))
    (audio / "_manifest.json").write_text(json.dumps({"02": {"file": "slide02.mp3"}}))
    monkeypatch.setattr(sys, "argv", ["r", str(tmp_path / "scripts.json"), str(audio), "--insert", "2"])
    with pytest.raises(SystemExit):
        R.main()
    assert sorted(json.load(open(tmp_path / "scripts.json"))) == ["01", "02"]


def test_two_deletes_keep_both_removed_clips(tmp_path, monkeypatch):
    root = deck(tmp_path)
    run(monkeypatch, root, "--delete", "2")
    run(monkeypatch, root, "--delete", "2")
    removed = sorted(os.listdir(root / "audio" / "removed"))
    texts = sorted((root / "audio" / "removed" / f).read_text() for f in removed if f.endswith(".mp3"))
    assert texts == ["audio 2", "audio 3"]
