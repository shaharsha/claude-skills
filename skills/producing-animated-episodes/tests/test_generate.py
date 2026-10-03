import pytest
import generate as G


def setup(ep):
    ep.data["pronounce"] = [["האבסולוט", "ה-Absolut"], ["אבסולוט", "Absolut"]]
    ep.characters["maya"]["refs"] = ["maya-1", "maya-2"]
    ep.data["panels"] = {"p02": {"chars": ["maya", "ido"], "scene": "SCENE: Maya hands Ido a phone. Maya smiles.", "hq": True},
                         "p03": {"chars": [], "scene": "SCENE: a shop sign.", "text_exception": 'the word "SALE" once'}}
    ep.data["music"] = {"theme": {"prompt": "x", "seconds": 20}}
    ep.data["sfx"] = {"ding": {"prompt": "ding", "seconds": 0.5}}
    ep.data["animate"] = {"base": "BASE ", "shots": {"S02": {"panel": "p02", "motion": "[0-3s] the woman talks."}}}
    return ep


def test_pron_order(tiny):
    assert G.pron(setup(tiny), "האבסולוט ואבסולוט") == "ה-Absolut וAbsolut"


def test_char_face_args_refs_and_text_only(tiny):
    setup(tiny)
    a = G.char_face_args(tiny, "maya")
    assert a[:5] == ["--size", "1024x1536", "--n", "2", "--draft"] and a[a.index("--output") + 1] == "characters/maya-face.png"
    assert a[-4:] == ["--ref", "faces/maya-1.png", "--ref", "faces/maya-2.png"]
    assert "every image is a close-up of the same person's face" in a[a.index("--prompt") + 1]
    b = G.char_face_args(tiny, "ido")
    assert "--ref" not in b and "CHARACTER: curly hair." in b[b.index("--prompt") + 1]


def test_card_keep_adjusted(tiny):
    tiny.characters["ido"]["face_adjust"] = "a little fuller face"
    a = G.char_card_args(tiny, "ido", "ido-face.png")
    p = a[a.index("--prompt") + 1]
    assert "but a little fuller face." in p and "BUILD: tall and thin." in p and a[a.index("--ref") + 1] == "characters/ido-face.png"
    assert G.char_final_args(tiny, "maya")[3] == "characters/final/maya.png"


def test_panel_prompt_binds_first_mention_only(tiny):
    p = G.panel_prompt(setup(tiny), "p02")
    assert "Maya (the person from Image 1) hands Ido (the person from Image 2) a phone. Maya smiles." in p
    assert "these 2 named people" in p and p.startswith("Image 1: Maya's character card")


def test_panel_args_quality_and_refs(tiny):
    setup(tiny)
    hq, flare = G.panel_draft_args(tiny, "p02", True), G.panel_draft_args(tiny, "p02", False)
    assert hq[2:4] == ["--quality", "high"] and flare[2] == "--draft"
    assert hq[-4:] == ["--ref", "characters/final/maya.png", "--ref", "characters/final/ido.png"]


def test_panel_text_exception(tiny):
    setup(tiny)
    assert 'except the word "SALE" once' in G.panel_prompt(tiny, "p03")
    f = G.panel_final_args(tiny, "p03")
    assert f[-1].endswith('Leave the word "SALE" once untouched and add no other text.')
    assert G.panel_final_args(tiny, "p02")[-1].endswith("No writing anywhere.")


def test_line_jobs_groups(tiny):
    jobs = G.line_jobs(setup(tiny))
    assert jobs[1] == ["02-1", "V1", "איפה ה-Absolut?"]
    assert jobs[-2:] == [["02-3__maya", "V1", "לחיים!"], ["02-3__ido", "V2", "לחיים!"]]
    assert [j[0] for j in G.line_jobs(tiny, only={"01-1"})] == ["01-1"]


def test_sound_and_animate(tiny):
    setup(tiny)
    s = G.sound_requests(tiny)
    assert s["theme"][0].endswith("/v1/music") and s["theme"][1]["model_id"] == "music_v2_5"
    assert s["ding"][0].endswith("/v1/sound-generation")
    assert G.animate_jobs(tiny) == {"S02": ["p02", "BASE [0-3s] the woman talks."]}
    d = G.prompts_dump(tiny)
    assert set(d) == {"char_face", "char_card", "char_final", "panel_draft", "panel_drafthq", "panel_final", "lines", "sound", "animate"}


def test_tool_missing_sibling():
    with pytest.raises(SystemExit):
        G.tool("no-such-skill", "x.py")


def test_tts_command_carries_voice_settings():
    V = {"model": "eleven_v4", "stability": 0.45, "similarity": 0.8, "language_code": "he"}
    cmd = G.tts_cmd(V, "gen.py", "line.json", "VOICE", "work")
    assert cmd[cmd.index("--stability") + 1] == "0.45" and cmd[cmd.index("--similarity") + 1] == "0.8"
    assert cmd[cmd.index("--language-code") + 1] == "he"
    assert "--similarity" not in G.tts_cmd({"model": "eleven_v4", "stability": 0.5}, "g", "j", "V", "w")


def test_processing_lines_in_place_is_refused(tiny):
    tiny.paths["lines_raw"] = tiny.paths["lines"]
    tiny.data["voice"] = {"tempo": 1.1}
    with pytest.raises(SystemExit, match="lines_raw"):
        G.check_line_paths(tiny)
