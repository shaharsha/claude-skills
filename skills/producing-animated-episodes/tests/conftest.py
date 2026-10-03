import json, os, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine"))

FONT_CANDIDATES = ["~/Library/Fonts/Heebo-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
                   "/Library/Fonts/Arial Unicode.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def hebrew_font():
    for f in FONT_CANDIDATES:
        p = os.path.expanduser(f)
        if os.path.exists(p):
            return p
    pytest.skip("no Hebrew-capable font on this machine")


def tiny_cfg():
    f = hebrew_font()
    return {
        "version": 1, "output": "tiny", "text": {"language": "he"},
        "fonts": {"bold": f, "black": f, "hblack": f, "hand": f},
        "characters": {"maya": {"display": "מאיה", "background": "warm orange #F28C28", "voice": "V1", "panel_name": "Maya",
                                "likeness": "short black hair", "body": "average build", "pose": "waving", "outfit": "red jacket"},
                       "ido": {"display": "עידו", "color": "#2450D8", "voice": "V2", "panel_name": "Ido",
                               "likeness": "curly hair", "body": "tall and thin", "pose": "arms crossed", "outfit": "green hoodie"}},
        "speakers": {"ALL": {"display": "כולם", "color": "#FFFFFF"}},
        "lines": [{"id": "01-1", "who": "maya", "text": "[excited] שלום!"},
                  {"id": "02-1", "who": "maya", "text": "איפה ה-Absolut?"},
                  {"id": "02-2", "who": "ido", "text": "[shrugs] לא יודע."},
                  {"id": "02-3", "who": "ALL", "text": "לחיים!"}],
        "groups": {"02-3": ["maya", "ido"]},
        "styles": {"cap": {"font": "bold", "size": 40, "fill": "#FFFFFF", "pill": "#000000AF", "wrap": 900, "y_top": 150, "anim": "fade"}},
        "music_cues": [["theme", "S01", "S02", 0.4, 0]],
        "shots": [{"id": "S01", "img": "p01", "lines": ["01-1"], "pre": 0.5, "post": 0.7},
                  {"id": "S02", "img": "p02", "lines": ["02-1", "02-2", "02-3@-0.4"], "pre": 0.3,
                   "overlays": [{"style": "cap", "text": "שעה קודם.", "t0": 0, "t1": "E02-1"}]},
                  {"id": "S03", "img": "black", "dur": 2.0}],
    }


@pytest.fixture
def tiny(tmp_path):
    import config
    (tmp_path / "episode.json").write_text(json.dumps(tiny_cfg(), ensure_ascii=False))
    return config.load(str(tmp_path))
