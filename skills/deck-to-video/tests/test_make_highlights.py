import json, os, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import make_highlights as H


def alignment(text, cps=10.0):
    """A fake forced alignment: every character lasts 1/cps seconds."""
    return {"stripped": text,
            "characters": [{"text": c, "start": i / cps, "end": (i + 1) / cps} for i, c in enumerate(text)]}


TEXT = ("Here is the problem we keep hitting every week. The fix is a queue per file with retries. "
        "The fix also needs an owner on call. Now, to the costs.")


def test_windows_run_marker_to_marker_and_end_closes_early():
    marks = [["problem", "Here is the problem"], ["fix", "The fix is"], ["_end", "Now, to the costs"]]
    w = H.windows(marks, alignment(TEXT))
    assert [r for r, _, _ in w] == ["problem", "fix"]
    fix_at, end_at = TEXT.index("The fix is") / 10, TEXT.index("Now, to") / 10
    assert w[1][1] == pytest.approx(fix_at - 0.12, abs=0.01) and w[1][2] == pytest.approx(end_at - 0.12, abs=0.01)


def test_search_moves_forward_so_a_repeated_phrase_cannot_jump_back():
    marks = [["a", "The fix"], ["b", "The fix"]]   # second "The fix" must be the later one
    w = H.windows(marks, alignment(TEXT))
    assert w[1][1] > w[0][1] + 3


def test_last_window_runs_to_end_of_speech_plus_tail():
    w = H.windows([["only", "Now, to"]], alignment(TEXT))
    assert w[0][2] == pytest.approx(len(TEXT) / 10 + 0.25, abs=0.01)


def test_marker_matches_across_a_line_break_and_case():
    w = H.windows([["x", "the PROBLEM we keep"]], alignment(TEXT.replace("problem we", "problem\nwe")))
    assert w and w[0][0] == "x"


def test_missing_phrase_and_length_mismatch_raise():
    with pytest.raises(ValueError, match="not found"):
        H.windows([["x", "nowhere in the script"]], alignment(TEXT))
    bad = alignment(TEXT); bad["characters"] = bad["characters"][:-3]
    with pytest.raises(ValueError, match="characters"):
        H.windows([["x", "Here"]], bad)


def test_check_box_frame_and_glow_margin():
    assert H.check_box([100, 100, 400, 300], (1920, 1080)) == ""
    assert H.check_box([5, 100, 400, 300], (1920, 1080)).startswith("warning")
    assert H.check_box([1700, 100, 400, 300], (1920, 1080)).startswith("error")


def write_case(tmp_path, markers, boxes, text=TEXT):
    al = tmp_path / "alignment"; al.mkdir(exist_ok=True)
    (al / "slide03.json").write_text(json.dumps(alignment(text)))
    (tmp_path / "markers.json").write_text(json.dumps(markers))
    (tmp_path / "boxes.json").write_text(json.dumps(boxes))
    return [str(tmp_path / "markers.json"), str(tmp_path / "boxes.json"), str(al), str(tmp_path / "out.json")]


def test_end_to_end_styles_inches_and_short_windows(tmp_path, capsys):
    markers = {"03": {"marks": [["problem", "Here is"], ["fix", "The fix is"], ["owner", "also needs"],
                                ["_end", "an owner"]],
                      "dim": "black", "colour": "#2A9D8F", "colours": {"fix": "#E76F51"}}}
    boxes = {"03": {"problem": [1, 1, 4, 2], "fix": [6, 1, 4, 2], "owner": [1, 3.5, 4, 2]}}  # inches
    H.main(write_case(tmp_path, markers, boxes) + ["--inches", "13.333", "--size", "1920x1080"])
    out = json.load(open(tmp_path / "out.json"))["03"]
    assert [w["card"] for w in out] == ["problem", "fix"]          # "owner" lasts 0.9 s: skipped
    assert out[0]["box"] == [144, 144, 576, 288]                    # inches x 144 px/in
    assert out[0]["colour"] == "#2A9D8F" and out[1]["colour"] == "#E76F51" and out[0]["dim"] == "black"
    assert "too short" in capsys.readouterr().out


def test_errors_stop_before_writing(tmp_path):
    markers = {"03": [["problem", "Here is"], ["ghost", "The fix is"]]}
    boxes = {"03": {"problem": [100, 100, 400, 300]}}
    with pytest.raises(SystemExit) as e:
        H.main(write_case(tmp_path, markers, boxes))
    assert "no box for region 'ghost'" in str(e.value)
    assert not (tmp_path / "out.json").exists()
