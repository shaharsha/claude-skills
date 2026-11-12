"""Offline tests for transcribe.py: no API calls."""
import argparse, json, os, subprocess, sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "transcribe.py")
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import transcribe as t  # noqa: E402


def w(text, start, end, spk="speaker_0", kind="word"):
    return {"text": text, "start": start, "end": end, "type": kind, "speaker_id": spk}


def sp(at, spk="speaker_0"):
    return w(" ", at, at, spk, "spacing")


def test_paragraphs_split_on_speaker_and_pause():
    data = {"words": [w("שלום", 0, 0.5), sp(0.5), w("לכולם", 0.5, 1.0),
                      w("hi", 1.2, 1.4, "speaker_1"),
                      w("again", 5.0, 5.3, "speaker_1")]}
    paras = t.paragraphs(data)
    assert [(p["spk"], p["text"]) for p in paras] == [
        ("speaker_0", "שלום לכולם"), ("speaker_1", "hi"), ("speaker_1", "again")]


def test_render_hides_label_for_one_speaker():
    data = {"words": [w("one", 0, 1), sp(1), w("voice", 1, 2)]}
    md, n, speakers = t.render(data, "T", "ElevenLabs scribe_v3")
    assert "[00:00] one voice" in md and "speaker_0" not in md and n == 1


def test_gaps_reports_long_silence_and_tail():
    data = {"audio_duration_secs": 200, "words": [w("a", 0, 1), w("b", 100, 101)]}
    assert t.gaps(data) == [(1, 100), (101, 200)]


def srt(*cues):
    return "\n\n".join(f"{i}\n{t._srt_fmt(a)} --> {t._srt_fmt(b)}\n{txt}" for i, (a, b, txt) in enumerate(cues, 1))


def test_tidy_srt_merges_fragment_into_neighbour():
    s = srt((0.0, 2.0, "ומה קורה אם יש"), (2.05, 2.25, "hole"), (3.0, 5.0, "סוף המשפט כאן"))
    out, merged, resplit = t.tidy_srt(s, width=42, max_secs=6)
    assert merged == 1 and resplit == 0
    blocks = out.strip().split("\n\n")
    assert len(blocks) == 2 and "ומה קורה אם יש hole" in blocks[0].replace("\n", " ")
    assert blocks[0].split("\n")[1] == "00:00:00,000 --> 00:00:02,250"
    assert [b.split("\n")[0] for b in blocks] == ["1", "2"]


def test_tidy_srt_keeps_fragment_when_merge_breaks_limits():
    s = srt((0.0, 5.8, "x" * 40), (5.85, 6.1, "tail"))
    out, merged, resplit = t.tidy_srt(s, width=42, max_secs=6)
    assert merged == 0 and resplit == 0 and len(out.strip().split("\n\n")) == 2


def test_wrap_respects_two_lines():
    assert t._wrap("a " * 10, 6) is None
    assert t._wrap("one two three", 8) == ["one two", "three"]


def ns(**kw):
    base = dict(keyterms=None, keyterms_file=None)
    base.update(kw)
    return argparse.Namespace(**base)


def test_read_terms_dedupes_and_validates(tmp_path):
    f = tmp_path / "terms.txt"
    f.write_text("Claude Code  # product\n\nsandbox\n", encoding="utf-8")
    assert t.read_terms(ns(keyterms=["agent, sandbox"], keyterms_file=str(f))) == ["agent", "sandbox", "Claude Code"]
    with pytest.raises(SystemExit):
        t.read_terms(ns(keyterms=["one two three four five six"]))
    with pytest.raises(SystemExit):
        t.read_terms(ns(keyterms=["[bad]"]))


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


def test_cli_rejects_v3_only_options_on_v2(tmp_path):
    r = run("x.mp3", "--out", str(tmp_path), "--model", "scribe_v2", "--numbers", "digits")
    assert r.returncode != 0 and "scribe_v3" in r.stderr


def test_cli_requires_language_with_also(tmp_path):
    r = run("x.mp3", "--out", str(tmp_path), "--also", "en")
    assert r.returncode != 0 and "--language" in r.stderr


def test_from_json_renders_srt_and_counts_latin(tmp_path):
    data = {"language_code": "heb", "language_probability": 1.0, "audio_duration_secs": 3,
            "words": [w("ה-agent", 0, 0.5), sp(0.5), w("רץ", 0.5, 1.0)],
            "additional_formats": [{"requested_format": "srt", "content": srt((0, 1, "ה-agent רץ"))}]}
    src = tmp_path / "talk.scribe.json"
    src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    r = run("--from-json", str(src), "--out", str(tmp_path / "o"))
    assert r.returncode == 0, r.stderr
    assert "Latin-script words: 1 of 2" in r.stdout
    assert (tmp_path / "o" / "talk.srt").exists() and (tmp_path / "o" / "talk.api.srt").exists()
    assert "[00:00] ה-agent רץ" in (tmp_path / "o" / "talk.transcript.md").read_text(encoding="utf-8")


def test_tidy_srt_resplits_unmergeable_fragment_with_word_times():
    words = [w("אנחנו", 5.88, 6.02), w("לא", 6.1, 6.3), w("מסוגלים", 6.3, 6.9), w("להבין", 6.9, 7.1),
             w("את", 7.1, 7.2), w("כולם.", 7.2, 7.36), w("סתם", 7.84, 8.1), w("דוגמאות", 8.1, 8.6),
             w("לפרטים", 8.6, 9.2), w("שצפו", 9.2, 9.6), w("מתוך", 9.6, 10.0), w("ה-evals", 10.0, 10.6),
             w("בתוך", 11.5, 12.0), w("המערכת.", 12.0, 12.64)]
    s = srt((5.88, 6.02, "אנחנו"),
            (6.1, 12.64, "לא מסוגלים להבין את כולם. סתם דוגמאות לפרטים שצפו מתוך ה-evals בתוך המערכת."))
    out, merged, resplit = t.tidy_srt(s, width=42, max_secs=6, words=words)
    blocks = out.strip().split("\n\n")
    assert merged == 0 and resplit == 1 and len(blocks) == 2
    assert blocks[0].split("\n")[1] == "00:00:05,880 --> 00:00:07,360"
    assert blocks[0].split("\n", 2)[2].replace("\n", " ") == "אנחנו לא מסוגלים להבין את כולם."
    assert blocks[1].split("\n")[1].startswith("00:00:07,840")
