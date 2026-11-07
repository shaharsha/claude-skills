import os, sys, types
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import office_render as O


def fake_osa(reply, log, rc=0):
    def osa(script):
        log.append(script)
        if "name of every" in script:
            return types.SimpleNamespace(stdout=reply, stderr="", returncode=rc)
        return types.SimpleNamespace(stdout="", stderr="", returncode=0)
    return osa


@pytest.mark.parametrize("reply,rc", [("ok\nQ3 board deck.pptx\nbudget.pptx\n", 0), ("", 1)])
def test_refuses_to_quit_with_open_or_uncountable_documents(monkeypatch, reply, rc):
    log = []
    monkeypatch.setattr(O, "osa", fake_osa(reply, log, rc))
    with pytest.raises(SystemExit) as e:
        O.quit_app("Microsoft PowerPoint")
    assert "without saving" in str(e.value) and not any("quit saving no" in s for s in log)


def test_quits_when_nothing_is_open(monkeypatch):
    log = []
    monkeypatch.setattr(O, "osa", fake_osa("ok\n", log))
    O.quit_app("Microsoft PowerPoint")
    assert any("quit saving no" in s for s in log)


def test_ignores_its_own_staged_copy_and_excel_personal_workbook(monkeypatch, tmp_path):
    monkeypatch.setattr(O.Path, "home", staticmethod(lambda: tmp_path))
    stage = tmp_path / "Downloads" / ".office-render"; stage.mkdir(parents=True)
    (stage / "deck.pptx").write_text("x")
    log = []
    monkeypatch.setattr(O, "osa", fake_osa("ok\ndeck.pptx\nPERSONAL.XLSB\n", log))
    assert O.open_documents("Microsoft Excel") == 0
    O.quit_app("Microsoft Excel")
    assert any("quit saving no" in s for s in log)


def test_force_quit_overrides(monkeypatch):
    log = []
    monkeypatch.setattr(O, "osa", fake_osa("ok\nmine.xlsx\n", log))
    O.quit_app("Microsoft Excel", force=True)
    assert any("quit saving no" in s for s in log)


def test_count_check_does_not_launch_the_app():
    seen = []
    orig = O.osa
    try:
        O.osa = lambda s: (seen.append(s), types.SimpleNamespace(stdout="ok", stderr="", returncode=0))[1]
        O.open_documents("Microsoft Word")
    finally:
        O.osa = orig
    assert 'is running' in seen[0] and "name of every document" in seen[0]
