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
    assert "with 2 named people" in p and p.startswith("Image 1: Maya's character card")


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


def test_one_character_panel_reads_naturally(tiny):
    tiny.data["panels"] = {"p9": {"chars": ["maya"], "scene": "SCENE: Maya waves."}}
    assert "with 1 named person" in G.panel_prompt(tiny, "p9")


def test_line_scripts_for_the_leak_check(tiny):
    setup(tiny)
    s = G.line_scripts(tiny)
    assert s["02-1"] == "איפה ה-Absolut?" and s["02-3__ido"] == "לחיים!"


# ---- final review fixes: partial failures, --force, leak-check scripts
import json, os, subprocess, sys, types
import episode, timeline

FAKE_TTS = r'''
import json, os, subprocess, sys
js, voice, out = sys.argv[1:4]
for clip in json.load(open(js)):
    if clip in os.environ.get("FAKE_FAIL", "").split(","):
        print(clip + ": HTTP 400"); sys.exit(1)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=0.5",
                    os.path.join(out, clip + ".mp3")], check=True)
'''


def tone(path, secs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"sine=f=220:d={secs}", path],
                   check=True)


def fake_tts(monkeypatch, tmp_path, fail):
    fake = tmp_path / "fake_tts.py"
    fake.write_text(FAKE_TTS)
    real = G.tool
    monkeypatch.setattr(G, "tool", lambda skill, *rel: str(fake) if rel[-1] == "generate_tts.py" else real(skill, *rel))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    monkeypatch.setenv("FAKE_FAIL", fail)


def test_failed_take_is_not_processed_and_is_reported(tiny, tmp_path, monkeypatch, capsys):
    fake_tts(monkeypatch, tmp_path, "02-2")
    for lid in ("01-1", "02-2"):
        tone(tiny.path("lines_raw", f"{lid}.mp3"), 3.0)          # last round's takes
        tone(tiny.path("lines", f"{lid}.mp3"), 3.0)
    failed = G.run_lines(tiny)
    assert failed == ["02-2"]
    assert timeline.adur(tiny.path("lines", "01-1.mp3")) < 1.0                 # the new take went through
    assert timeline.adur(tiny.path("lines", "02-3.mp3")) < 1.0                 # the crowd line was mixed and copied
    assert timeline.adur(tiny.path("lines", "02-2.mp3")) > 2.5                 # the old take was not passed off as new
    out = capsys.readouterr().out
    assert "1 line(s) failed" in out and "lines 02-2" in out


def test_failed_crowd_part_fails_its_line(tiny, tmp_path, monkeypatch):
    fake_tts(monkeypatch, tmp_path, "02-3__ido")
    assert G.run_lines(tiny) == ["02-3"]
    assert not os.path.exists(tiny.path("lines", "02-3.mp3"))


def test_leak_check_scripts_match_their_folders(tiny, tmp_path, monkeypatch):
    fake_tts(monkeypatch, tmp_path, "")
    G.run_lines(tiny)
    main = json.load(open(tiny.path("lines_raw", "_scripts.json")))
    parts = json.load(open(tiny.path("lines_raw", "parts", "_scripts.json")))
    assert "01-1" in main and not any("__" in k for k in main)
    assert set(parts) == {"02-3__maya", "02-3__ido"}


def test_cli_lines_exits_nonzero_on_a_failed_take(tiny, tmp_path, monkeypatch):
    fake_tts(monkeypatch, tmp_path, "01-1")
    assert episode.main([tiny.root, "lines"]) == 1


def capture(monkeypatch):
    calls = []
    monkeypatch.setattr(G.subprocess, "run", lambda cmd, **k: calls.append(cmd) or types.SimpleNamespace(stdout="", returncode=0))
    return calls


def save(ep):
    json.dump(ep.data, open(ep.file, "w"), ensure_ascii=False)


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(b"x")


def test_sound_force_regenerates_existing_cues(tiny, monkeypatch, capsys):
    save(setup(tiny))
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test")
    touch(tiny.path("music", "theme.mp3"))
    calls = capture(monkeypatch)
    assert episode.main([tiny.root, "sound", "theme"]) == 0
    out = capsys.readouterr().out
    assert not calls and "theme: exists" in out and "--force" in out      # nothing requested, nothing priced
    assert episode.main([tiny.root, "sound", "theme", "--force"]) == 0
    assert calls and "--force" in calls[-1]
    assert "20 s requested" in capsys.readouterr().out


def test_animate_force_and_retakes_replace_existing_clips(tiny, monkeypatch):
    save(setup(tiny))
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    touch(tiny.path("panels_final", "p02.png"))
    touch(tiny.path("clips", "S02.mp4"))
    calls = capture(monkeypatch)
    episode.main([tiny.root, "animate", "S02"])
    assert not calls and os.path.exists(tiny.path("clips", "S02.mp4"))     # exists: nothing requested without --force
    episode.main([tiny.root, "animate", "S02", "--force"])
    assert calls and not os.path.exists(tiny.path("clips", "S02.mp4")) and os.listdir(tiny.path("clips", "_old"))
    calls.clear()
    for t in (1, 2):
        touch(tiny.path("clips", f"S02_t{t}.mp4"))
    episode.main([tiny.root, "animate", "S02", "--takes", "2"])
    assert not calls                                                     # both takes exist: nothing to do
    episode.main([tiny.root, "animate", "S02", "--takes", "2", "--force"])
    assert calls and not os.path.exists(tiny.path("clips", "S02_t1.mp4"))  # earlier takes moved aside: 2 new takes


# ---- narration: a narrator is a speaker with a voice, never drawn
def test_narrator_speaker_voices_its_lines(tiny):
    tiny.speakers["narrator"] = {"display": None, "voice": "VN"}
    tiny.data["lines"].append({"id": "09-1", "who": "narrator", "text": "Once upon a time."})
    assert ["09-1", "VN", "Once upon a time."] in G.line_jobs(tiny)
    assert "narrator" not in G.prompts_dump(tiny)["char_face"]


def test_a_line_without_a_voice_is_named(tiny):
    tiny.data["groups"] = {}                                   # 02-3 by ALL is no longer a crowd line
    with pytest.raises(SystemExit) as e:
        G.line_jobs(tiny)
    assert "02-3" in str(e.value) and "voice" in str(e.value)
