import json
import pytest
import config, timeline
from conftest import tiny_cfg

DUR = {"01-1": 1.0, "02-1": 1.5, "02-2": 1.2, "02-3": 0.8}


def write(tmp_path, cfg):
    (tmp_path / "episode.json").write_text(json.dumps(cfg, ensure_ascii=False))
    return str(tmp_path)


def test_defaults_and_paths(tiny):
    assert tiny.fps == 24 and (tiny.W, tiny.H) == (1080, 1920)
    assert tiny.text_dir == "rtl" and tiny.text_lang == "he"
    assert tiny.line_audio("01-1") == f"{tiny.root}/audio/lines/01-1.mp3"
    assert tiny.speakers["maya"] == {"display": "מאיה", "color": "#F28C28"}
    assert tiny.speakers["ALL"]["display"] == "כולם"
    assert tiny.prompts["person_one"] == "person"            # neutral default


def test_ltr_default_for_english(tmp_path):
    cfg = tiny_cfg(); cfg["text"] = {"language": "en"}
    assert config.load(write(tmp_path, cfg)).text_dir == "ltr"


def test_validation_lists_every_error(tmp_path):
    cfg = tiny_cfg()
    cfg["shots"].append({"id": "S01", "img": "p9", "lines": ["99-9"], "overlays": [{"style": "nope", "text": "x"}]})
    cfg["shots"][0]["who"] = {"01-1": "ghost"}
    cfg["music_cues"].append(["x", "S01", "S77", 0.3, 0])
    with pytest.raises(config.ConfigError) as e:
        config.load(write(tmp_path, cfg))
    msg = str(e.value)
    for needle in ("duplicate shot ids", "unknown line 99-9", "unknown style 'nope'", "'ghost'", "S77"):
        assert needle in msg, needle


def test_shot_needs_lines_or_dur(tmp_path):
    cfg = tiny_cfg(); cfg["shots"].append({"id": "S09", "img": "black"})
    with pytest.raises(config.ConfigError, match="S09: needs lines or dur"):
        config.load(write(tmp_path, cfg))


def test_resolve_time():
    placed = {"02-1": (0.3, 1.8)}
    assert timeline.resolve_time(0.5, placed) == 0.5
    assert timeline.resolve_time(None, placed) is None
    assert timeline.resolve_time("E02-1+0.5", placed) == pytest.approx(2.3)
    assert timeline.resolve_time("S02-1-0.1", placed) == pytest.approx(0.2)
    with pytest.raises(ValueError):
        timeline.resolve_time("X02-1", placed)


def test_timeline_frames_and_overlap(tiny):
    shots, total = timeline.build_timeline(tiny, DUR)
    s1, s2, s3 = shots
    assert s1["placed"]["01-1"] == pytest.approx((0.5, 1.5)) and s1["nframes"] == round((1.5 + 0.7) * 24)
    assert s2["start"] == pytest.approx(s1["nframes"] / 24)
    a, b, c = (s2["placed"][k] for k in ("02-1", "02-2", "02-3"))
    assert b[0] == pytest.approx(a[1] + 0.12)                 # default gap
    assert c[0] == pytest.approx(b[1] - 0.4)                  # "@-0.4": overlaps the previous line
    assert s3["nframes"] == 48 and total == pytest.approx(sum(s["nframes"] for s in shots) / 24)
    assert all(isinstance(s["nframes"], int) for s in shots)


def test_pad_and_silent_scales(tmp_path):
    cfg = tiny_cfg(); cfg["timing"] = {"pad_scale": 0.5, "silent_scale": 0.5}
    shots, _ = timeline.build_timeline(config.load(write(tmp_path, cfg)), DUR)
    assert shots[0]["placed"]["01-1"][0] == pytest.approx(0.25) and shots[2]["nframes"] == 24


def test_write_timeline(tiny, tmp_path):
    shots, _ = timeline.build_timeline(tiny, DUR)
    timeline.write_timeline(shots, str(tmp_path / "t.json"))
    t = json.load(open(tmp_path / "t.json"))
    assert set(t[0]) == {"id", "start", "dur", "placed"} and t[1]["placed"]["02-2"] == list(shots[1]["placed"]["02-2"])
