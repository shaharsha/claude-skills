#!/usr/bin/env python3
"""
Tests for `ccverify files`. Stdlib only:  python3 torque-orchestration/ccverify_test.py

Every end-to-end case builds a THROWAWAY git repo and runs the real script as a
subprocess, because the thing under test is a verdict a human acts on — an assertion
about `parse_declared` alone would pass while the CLI dropped the result on the floor.

⚠️ THE MUST-FIRE AND MUST-NOT-FIRE CASES ARE ONE PAIR, DELIBERATELY.
`test_a_file_the_plan_only_MENTIONS_is_a_breach` and
`test_the_SAME_file_DECLARED_passes_clean` run the SAME repo and the SAME plan text
with ONE line moved into the FILES: block. That pairing is what makes them a control
rather than two hopeful assertions: a parser that went back to reading prose turns the
first one GREEN, and a parser that refuses correct lists turns the second one RED.
Neither can be satisfied by an inert gate.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CCVERIFY = os.path.join(HERE, "ccverify")
FIXTURES = os.path.join(HERE, "fixtures")


def _load():
    spec = importlib.util.spec_from_loader(
        "ccverify_mod", importlib.machinery.SourceFileLoader("ccverify_mod", CCVERIFY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load()


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    assert p.returncode == 0, f"git {args} failed: {p.stderr}"
    return p.stdout


class Repo:
    """A two-commit git repo: `base` has the tree, HEAD has the change under review."""

    def __init__(self, before, after):
        self.dir = tempfile.mkdtemp(prefix="ccverify-test-")
        git(self.dir, "init", "-q", "-b", "main")
        git(self.dir, "config", "user.email", "t@t")
        git(self.dir, "config", "user.name", "t")
        self._write(before)
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-qm", "base")
        self.base = git(self.dir, "rev-parse", "HEAD").strip()
        self._write(after)
        git(self.dir, "add", "-A")
        git(self.dir, "commit", "-qm", "change")

    def _write(self, files):
        for rel, body in files.items():
            path = os.path.join(self.dir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def run_files(repo, plan_text=None, extra=(), plan_path=None):
    """-> (rc, combined output). --no-untracked keeps the fixtures free of scratch noise."""
    cmd = [sys.executable, CCVERIFY, "files", "--repo", repo.dir,
           "--base", repo.base, "--no-untracked"] + list(extra)
    if plan_path:
        cmd += ["--plan", plan_path]
    elif plan_text is not None:
        cmd += ["--plan", "-"]
    p = subprocess.run(cmd, input=plan_text, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ---------------------------------------------------------------- the pair

# One document. `tests/conftest.py` is DISCUSSED in prose and NOT in the FILES: block —
# the shape measured on 2026-08-24, where two lanes were editing that exact file.
PLAN_MENTION_ONLY = textwrap.dedent("""\
    # TOR-000 — a plan

    The renderer reads its fixtures through `tests/conftest.py`, so the session-scoped
    fixture there is the reason the suite is slow. We are not changing that here.

    FILES:
      - `src/renderer.ts`

    ## Done when
    The suite is green.
    """)

# The SAME document with that one path moved into the block. Nothing else differs.
PLAN_DECLARED = PLAN_MENTION_ONLY.replace(
    "FILES:\n  - `src/renderer.ts`\n",
    "FILES:\n  - `src/renderer.ts`\n  - `tests/conftest.py`\n")

TOUCHED_BOTH = ({"src/renderer.ts": "a\n", "tests/conftest.py": "a\n"},
                {"src/renderer.ts": "b\n", "tests/conftest.py": "b\n"})


class TheControlPair(unittest.TestCase):

    def setUp(self):
        self.repo = Repo(*TOUCHED_BOTH)
        self.addCleanup(self.repo.close)

    def test_the_two_plans_differ_by_exactly_one_line(self):
        """The pair is only a control while its two halves differ in the one way claimed."""
        a, b = PLAN_MENTION_ONLY.splitlines(), PLAN_DECLARED.splitlines()
        added = [ln for ln in b if ln not in a]
        self.assertEqual(added, ["  - `tests/conftest.py`"])

    def test_a_file_the_plan_only_MENTIONS_is_a_breach(self):
        """MUST FIRE. This is the case that PASSED before 2026-08-24."""
        rc, out = run_files(self.repo, PLAN_MENTION_ONLY)
        self.assertEqual(rc, 1, out)
        self.assertIn("UNDECLARED", out)
        self.assertIn("tests/conftest.py", out)
        self.assertIn("a mention is not a declaration", out)

    def test_the_SAME_file_DECLARED_passes_clean(self):
        """MUST NOT FIRE. A gate that fires on correct work gets uninstalled."""
        rc, out = run_files(self.repo, PLAN_DECLARED)
        self.assertEqual(rc, 0, out)
        self.assertIn("CLEAN", out)


# ---------------------------------------------------------------- no block at all

class NoDeclarationBlock(unittest.TestCase):

    def setUp(self):
        self.repo = Repo({"src/a.ts": "a\n"}, {"src/a.ts": "b\n"})
        self.addCleanup(self.repo.close)

    def test_a_plan_with_no_block_is_CANNOT_CHECK(self):
        rc, out = run_files(self.repo, "# a plan\n\nWe will edit `src/a.ts` and be done.\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("CANNOT CHECK", out)
        self.assertIn("no declaration block", out)
        self.assertIn("exit 2 is not a pass", out)

    def test_it_does_NOT_infer_the_list_from_that_prose(self):
        """The inferred list would have covered the diff exactly. Exit 0 is the old defect."""
        rc, out = run_files(self.repo, "# a plan\n\nWe will edit `src/a.ts` and be done.\n")
        self.assertNotEqual(rc, 0, out)
        self.assertNotIn("CLEAN", out)

    def test_a_prohibition_alone_is_not_a_declaration(self):
        rc, out = run_files(self.repo, "NOT TOUCHING:\n  - `src/a.ts`\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("not touch", out.lower())

    def test_a_header_with_no_paths_under_it_is_CANNOT_CHECK(self):
        rc, out = run_files(self.repo, "FILES:\n\n\nSome prose about `src/a.ts`.\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("no paths under it", out)


# ---------------------------------------------------------------- accepted block shapes

class BlockShapes(unittest.TestCase):
    """Every shape a plan author plausibly writes must pass, or the gate gets uninstalled."""

    def setUp(self):
        self.repo = Repo({"src/a.ts": "a\n", "src/b.ts": "a\n"},
                         {"src/a.ts": "b\n", "src/b.ts": "b\n"})
        self.addCleanup(self.repo.close)

    def assertClean(self, plan):
        rc, out = run_files(self.repo, plan)
        self.assertEqual(rc, 0, out)

    def test_inline_on_the_header_line(self):
        self.assertClean("FILES: `src/a.ts` `src/b.ts`\n")

    def test_bulleted_list(self):
        self.assertClean("FILES:\n- `src/a.ts`\n- `src/b.ts`\n")

    def test_numbered_list(self):
        self.assertClean("FILES:\n1. `src/a.ts`\n2. `src/b.ts`\n")

    def test_a_single_blank_line_inside_the_list(self):
        self.assertClean("FILES:\n- `src/a.ts`\n\n- `src/b.ts`\n")

    def test_a_fenced_block_one_path_per_line(self):
        self.assertClean("FILES:\n```\nsrc/a.ts\nsrc/b.ts\n```\n")

    def test_bare_paths_in_a_list_need_no_backticks(self):
        self.assertClean("FILES:\n- src/a.ts\n- src/b.ts\n")

    def test_a_bolded_markdown_header(self):
        self.assertClean("**FILES:**\n- `src/a.ts`\n- `src/b.ts`\n")

    def test_a_list_item_may_carry_a_trailing_comment(self):
        self.assertClean("FILES:\n- `src/a.ts` — the entry point\n- `src/b.ts` — its helper\n")

    def test_two_blocks_are_unioned(self):
        self.assertClean("FILES:\n- `src/a.ts`\n\nPhase 2.\n\nFILES:\n- `src/b.ts`\n")

    def test_a_directory_prefix_still_covers_its_children(self):
        self.assertClean("FILES:\n- `src/`\n")

    def test_a_glob_still_covers_its_matches(self):
        self.assertClean("FILES:\n- `src/*.ts`\n")

    def test_inline_declarations_still_work(self):
        rc, out = run_files(self.repo, plan_text=None,
                            extra=["-d", "src/a.ts", "-d", "src/b.ts"])
        self.assertEqual(rc, 0, out)


# ---------------------------------------------------------------- the block's bound

class BlockEndsAtProse(unittest.TestCase):

    def setUp(self):
        self.repo = Repo({"src/a.ts": "a\n", "src/leak.ts": "a\n"},
                         {"src/a.ts": "b\n", "src/leak.ts": "b\n"})
        self.addCleanup(self.repo.close)

    def test_a_path_in_the_paragraph_below_the_list_is_not_declared(self):
        rc, out = run_files(self.repo, textwrap.dedent("""\
            FILES:
            - `src/a.ts`

            While we are in there we will read `src/leak.ts` for reference.
            """))
        self.assertEqual(rc, 1, out)
        self.assertIn("src/leak.ts", out)

    def test_a_path_under_a_HEADING_below_the_block_is_not_declared(self):
        rc, out = run_files(self.repo, textwrap.dedent("""\
            FILES:
            - `src/a.ts`
            ## Notes
            - `src/leak.ts` is where the bug came from
            """))
        self.assertEqual(rc, 1, out)
        self.assertIn("src/leak.ts", out)

    def test_two_blank_lines_close_the_block(self):
        rc, out = run_files(self.repo, "FILES:\n- `src/a.ts`\n\n\n- `src/leak.ts`\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("src/leak.ts", out)


# ---------------------------------------------------------------- prohibitions

class Prohibitions(unittest.TestCase):

    def setUp(self):
        self.repo = Repo({"src/a.ts": "a\n", "src/held.ts": "a\n"},
                         {"src/a.ts": "b\n", "src/held.ts": "b\n"})
        self.addCleanup(self.repo.close)

    def test_touching_a_prohibited_file_is_the_harder_failure(self):
        rc, out = run_files(self.repo,
                            "FILES:\n- `src/a.ts`\n\nNOT TOUCHING:\n- `src/held.ts`\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("PROHIBITION BREACHED", out)

    def test_a_prohibition_is_never_read_as_a_declaration(self):
        """The PR #526 finding. A prohibited path must not silence the breach."""
        rc, out = run_files(self.repo,
                            "FILES:\n- `src/a.ts`\n\nNOT TOUCHING:\n- `src/held.ts`\n")
        self.assertNotIn("CLEAN — every file touched was declared", out)

    def test_a_clean_prohibition_reports_clean(self):
        repo = Repo({"src/a.ts": "a\n"}, {"src/a.ts": "b\n"})
        self.addCleanup(repo.close)
        rc, out = run_files(repo, "FILES:\n- `src/a.ts`\n\nNOT TOUCHING:\n- `src/held.ts`\n")
        self.assertEqual(rc, 0, out)


# ---------------------------------------------------------------- the real document

class TOR750Regression(unittest.TestCase):
    """
    The document that broke the parser: a real 661-line plan whose prose parsed to
    `declared 131`, including a slash command, a git range, currency and CSS class names.
    Committed here because a fixture nobody can reproduce is not a regression test.
    """

    PLAN = os.path.join(FIXTURES, "tor750-plan.md")

    def setUp(self):
        with open(self.PLAN, encoding="utf-8") as fh:
            self.text = fh.read()

    def test_the_fixture_still_CONTAINS_the_tokens_that_broke_the_parser(self):
        """
        ⚠️ A control must reach the failure. If someone tidies this fixture the case stops
        being covered, and the suite would otherwise stay green while covering nothing.
        """
        mentions = {}
        for i, line in enumerate(self.text.splitlines()):
            for t in cc._mention_tokens(line):
                mentions.setdefault(t, i + 1)
        for junk in ("/adjudicate", "9cf4a350..2ac44d42", "$52.80",
                     ".recharts-line-chart", "frontend/src/{charts,pagekit}", "entry.tsx"):
            self.assertIn(junk, mentions, f"fixture no longer contains {junk!r}")

    def test_it_now_declares_NOTHING_and_names_no_block(self):
        declared, prohibited, blocks, mentions = cc.parse_declared(self.text)
        self.assertEqual(blocks, [])
        self.assertEqual(declared, [])
        self.assertEqual(prohibited, [])
        self.assertGreater(len(mentions), 100)   # the prose is still full of paths

    def test_end_to_end_it_is_CANNOT_CHECK(self):
        repo = Repo({"src/a.ts": "a\n"}, {"src/a.ts": "b\n"})
        self.addCleanup(repo.close)
        rc, out = run_files(repo, plan_path=self.PLAN)
        self.assertEqual(rc, 2, out)
        self.assertIn("no declaration block", out)


# ---------------------------------------------------------------- untouched behaviour

class UntouchedRefusals(unittest.TestCase):
    """These were already right. The fix must not have moved them."""

    def test_an_empty_diff_range_is_still_CANNOT_CHECK(self):
        repo = Repo({"src/a.ts": "a\n"}, {"src/a.ts": "b\n"})
        self.addCleanup(repo.close)
        p = subprocess.run(
            [sys.executable, CCVERIFY, "files", "--repo", repo.dir, "--base", "HEAD",
             "--no-untracked", "--plan", "-"],
            input="FILES:\n- `src/a.ts`\n", capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("is EMPTY", p.stdout + p.stderr)

    def test_a_missing_repo_is_still_CANNOT_CHECK(self):
        p = subprocess.run(
            [sys.executable, CCVERIFY, "files", "--repo", tempfile.mkdtemp(),
             "--plan", "-"], input="FILES:\n- `a.ts`\n", capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
