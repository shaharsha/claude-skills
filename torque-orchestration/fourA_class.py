#!/usr/bin/env python3
"""§4A mandatory-class matcher for Torque PRs.

Written 2026-09-20 by the PR #1060 merge-adjudicator seat, at a SHARED path
rather than as a fifth private copy. §4A.3's second "smaller one" ("class
membership is eyeballed, not computed"), §4A.6's "until it exists, this
correction is checked by nobody, ever again" and TOR-1160's third done-when all
ask for exactly this.  Until it is committed INTO the repo it is still
orchestration-local; that is TOR-1160's remaining ask, not this file's claim.

Class entries are transcribed from APPROVAL-CRITERIA.md §4A as amended by
§4A.1 (authored_pages, README carve-out), §4A.2 (projector), §4A.8 (slots.py),
§4A.9 (provenance_gate.py, chart_width.py), §4A.10 (the text-presence check and
its publish wiring) and corrected by §4A.6 (publishing is a FILE, not a package).

Usage:
    fourA_class.py --repo <path> --range <base>..<head>
    fourA_class.py --repo <path> --self-test
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- class spec

# Static entries.  A trailing "/**" means prefix-match on the directory;
# an entry with no glob is an exact FILE path.
STATIC_PREFIX_ENTRIES = [
    "engine/",
    "models/",
    "risk/",
    "api/auth/",
    "api/services/vault/",
    "api/services/silver/",
    "api/services/computation/",
    "api/services/projector/",
]
STATIC_FILE_ENTRIES = [
    "db/schema.py",
    # §4A.6: a MODULE, not a package.  `api/services/publishing/**` matched zero
    # paths from 2026-08-28 until the 2026-09-18 correction.
    "api/services/publishing.py",
    # §4A.8 (2026-09-24, Shahar): `_PUBLISHED_SHAPE` decides both the reader's
    # Recompute and the drift detector's comparison for a published page.
    "api/services/slots.py",
    # §4A.9 (2026-09-26, Shahar, TOR-1995): once torque #1239 lifts the interim
    # refusal, these two are the only guard between a wrong number and an
    # immutable published page.  FILE entries: the rest of control_plane/**
    # stays unruled (§4A.6) and outside the class.
    "api/services/control_plane/provenance_gate.py",
    # ⚠️ Created by torque #1239; until that merges, entry liveness reports it
    # DEAD on any ref that lacks it.  That is the truthful reading, not a bug.
    "api/services/chart_width.py",
    # §4A.10 (2026-09-29, Shahar): the rendered text-presence check.  The three
    # modules whose code decides the verdict (TOR-1724 Part 1 spec §5.5 lists them
    # with provenance_gate.py and chart_width.py, already above), its register, its
    # CI workflow, and the one publish door that calls it.  ALL FILE entries:
    # publishing.py's control_plane neighbours stay unruled.
    "api/services/rendered_text.py",
    "api/services/as_of_edge.py",
    "api/services/drawn_text.py",
    "scripts/rendered_text_expected_differences.yml",
    ".github/workflows/text-presence.yml",
    "api/services/control_plane/artifacts.py",
]
# §4A.10: scripts/rendered_text_*.py, directly under scripts/ (no subdirectory).
# (directory prefix, name prefix, suffix) -- a name-stem entry, not a directory.
STEM_ENTRIES = [
    ("scripts/", "rendered_text_", ".py"),
]
# §4A.1: authored_pages/** is in the class EXCEPT **/README.md
AUTHORED_PREFIX = "authored_pages/"


def product_codes(repo: Path) -> list[str]:
    """Read the client product list from tests/fixtures/company_rows.py.

    §4A: `_REAL_PRODUCTS` was DELETED by PR #1040 (develop abbb8e4f).  Every
    matcher that still AST-parses that constant resolves nothing and returns a
    silent zero for the product branch.  The replacement source is COMPANY_ROW.

    ⚠️ The parse shape is ASSERTED: COMPANY_ROW is an ast.AnnAssign (an
    annotated assignment).  If it is ever respelled as a plain ast.Assign this
    raises rather than returning an empty list, because an empty product set and
    a non-resolving source are indistinguishable from the count alone.
    """
    src = (repo / "tests/fixtures/company_rows.py").read_text()
    tree = ast.parse(src)

    ann_nodes = [
        n for n in tree.body
        if isinstance(n, ast.AnnAssign)
        and isinstance(n.target, ast.Name)
        and n.target.id == "COMPANY_ROW"
    ]
    plain_nodes = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "COMPANY_ROW" for t in n.targets)
    ]
    if plain_nodes and not ann_nodes:
        raise SystemExit(
            "PARSE-SHAPE ASSERTION FAILED: COMPANY_ROW is a plain ast.Assign, not "
            "an ast.AnnAssign. The matcher's shape assumption has rotted — fix the "
            "matcher rather than accepting its zero."
        )
    if len(ann_nodes) != 1:
        raise SystemExit(
            f"PARSE-SHAPE ASSERTION FAILED: expected exactly 1 AnnAssign named "
            f"COMPANY_ROW, found {len(ann_nodes)} (plain Assign: {len(plain_nodes)})."
        )
    node = ann_nodes[0]
    if not isinstance(node.value, ast.Dict):
        raise SystemExit(
            "PARSE-SHAPE ASSERTION FAILED: COMPANY_ROW's value is not a dict literal."
        )
    codes = []
    for k in node.value.keys:
        if not isinstance(k, ast.Constant) or not isinstance(k.value, str):
            raise SystemExit("PARSE-SHAPE ASSERTION FAILED: non-string key in COMPANY_ROW.")
        codes.append(k.value)
    if not codes:
        raise SystemExit("PARSE-SHAPE ASSERTION FAILED: COMPANY_ROW is empty.")
    return codes


def build_entries(repo: Path) -> list[tuple[str, str, str]]:
    """Return (kind, pattern, label) for every live class entry."""
    entries: list[tuple[str, str, str]] = []
    for p in STATIC_PREFIX_ENTRIES:
        entries.append(("prefix", p, f"{p}**"))
    for f in STATIC_FILE_ENTRIES:
        entries.append(("file", f, f))
    for d, stem, suf in STEM_ENTRIES:
        entries.append(("stem", (d, stem, suf), f"{d}{stem}*{suf}"))
    entries.append(("authored", AUTHORED_PREFIX, "authored_pages/** (except **/README.md)"))
    # ⚠️ all seven codes are UPPERCASE against lowercase directories:
    # case-normalisation is load-bearing.
    for code in product_codes(repo):
        d = f"api/services/{code.lower()}/"
        entries.append(("prefix", d, f"{d}** [product {code}]"))
    return entries


def _stem_match(path: str, pat: tuple[str, str, str]) -> bool:
    """`<dir><stem>*<suffix>`, with nothing after `<dir>` but the file name."""
    d, stem, suf = pat
    if not path.startswith(d):
        return False
    name = path[len(d):]
    return "/" not in name and name.startswith(stem) and name.endswith(suf)


def classify(path: str, entries) -> str | None:
    """Return the label of the first class entry `path` matches, else None."""
    for kind, pat, label in entries:
        if kind == "prefix" and path.startswith(pat):
            return label
        if kind == "file" and path == pat:
            return label
        if kind == "stem" and _stem_match(path, pat):
            return label
        if kind == "authored" and path.startswith(pat):
            # §4A.1 carve-out: README.md at any depth is NOT a trigger.
            if Path(path).name == "README.md":
                continue
            return label
    return None


# ---------------------------------------------------------------- git helpers

def git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed rc={r.returncode}: {r.stderr.strip()}")
    return r.stdout


def tracked_at(repo: Path, ref: str) -> list[str]:
    return [l for l in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines() if l]


def changed(repo: Path, rng: str) -> list[str]:
    base, _, head = rng.partition("..")
    return [l for l in git(repo, "diff", "--name-only", base, head).splitlines() if l]


# ---------------------------------------------------------------- controls

MUST_HIT = [
    ("engine/torque_engine/x.py", "engine"),
    ("models/vyb_loan_model.py", "models"),
    ("risk/scorer.py", "risk"),
    ("api/auth/deps.py", "api/auth"),
    ("api/services/vault/raw_scan.py", "vault"),
    ("api/services/silver/catalogue.py", "silver"),
    ("api/services/computation/packages.py", "computation"),
    ("api/services/projector/payload.py", "projector"),
    ("db/schema.py", "db/schema.py"),
    ("api/services/publishing.py", "publishing.py (§4A.6)"),
    ("api/services/slots.py", "slots.py (§4A.8)"),
    ("api/services/control_plane/provenance_gate.py", "provenance_gate.py (§4A.9)"),
    ("api/services/chart_width.py", "chart_width.py (§4A.9)"),
    ("api/services/rendered_text.py", "rendered_text.py (§4A.10)"),
    ("api/services/as_of_edge.py", "as_of_edge.py (§4A.10)"),
    ("api/services/drawn_text.py", "drawn_text.py (§4A.10)"),
    ("scripts/rendered_text_differential.py", "scripts/rendered_text_*.py (§4A.10)"),
    ("scripts/rendered_text_canaries.py", "scripts/rendered_text_*.py (§4A.10)"),
    ("scripts/rendered_text_.py", "the stem's `*` may match nothing (§4A.10)"),
    ("scripts/rendered_text_corpus.py", "scripts/rendered_text_*.py (§4A.10)"),
    ("scripts/rendered_text_real_pages.py", "scripts/rendered_text_*.py (§4A.10)"),
    ("scripts/rendered_text_a_script_not_written_yet.py", "the stem covers scripts added later (§4A.10)"),
    ("scripts/rendered_text_expected_differences.yml", "the register (§4A.10)"),
    (".github/workflows/text-presence.yml", "text-presence.yml (§4A.10)"),
    ("api/services/control_plane/artifacts.py", "artifacts.py, the publish wiring (§4A.10)"),
    ("authored_pages/lr_historical/body.html", "authored_pages non-README"),
    ("api/services/lr/forecast.py", "PRODUCT branch (§4A product control)"),
]

MUST_MISS = [
    # the brief's named traps
    ("api/services/control_plane/silver.py", "control_plane/silver.py is NOT silver/**"),
    ("api/services/control_plane/pages.py", "control_plane is not in the class"),
    ("api/services/control_plane/pins.py", "control_plane is not in the class"),
    ("api/services/control_plane/descriptors.py", "control_plane is not in the class"),
    ("api/services/control_plane/publishing_helpers.py",
     "§4A.10 added artifacts.py as a FILE, not control_plane/**"),
    ("api/services/control_plane/artifacts_helpers.py",
     "§4A.10 is an exact FILE entry, not a prefix"),
    ("api/services/control_plane/provenance_gate_helpers.py",
     "§4A.9 is an exact FILE entry, not a prefix"),
    ("api/services/chart_width_legacy.py", "§4A.9 is an exact FILE entry, not a prefix"),
    ("api/services/control_plane/provenance_gate.py.bak", "§4A.9 exact FILE entry: a prefix entry would admit this"),
    ("api/services/chart_width.py.bak", "§4A.9 exact FILE entry: a prefix entry would admit this"),
    ("api/services/rendered_text_helpers.py", "§4A.10 is an exact FILE entry, not a prefix"),
    ("api/services/as_of_edge_legacy.py", "§4A.10 is an exact FILE entry, not a prefix"),
    ("api/services/drawn_text_utils.py", "§4A.10 is an exact FILE entry, not a prefix"),
    ("api/services/rendered_text.py.bak", "§4A.10 exact FILE entry: a prefix entry would admit this"),
    ("api/services/as_of_edge.py.bak", "§4A.10 exact FILE entry: a prefix entry would admit this"),
    ("api/services/drawn_text.py.bak", "§4A.10 exact FILE entry: a prefix entry would admit this"),
    ("api/services/control_plane/artifacts.py.bak",
     "§4A.10 exact FILE entry: a prefix entry would admit this"),
    ("scripts/rendered_text_expected_differences.yml.bak",
     "§4A.10 exact FILE entry: a prefix entry would admit this"),
    (".github/workflows/text-presence.yml.bak",
     "§4A.10 exact FILE entry: a prefix entry would admit this"),
    ("scripts/rendered_text_x.py.bak", "§4A.10 stem entry needs the .py suffix at the end"),
    ("scripts/rendered_text_readme.md", "§4A.10 stem entry needs the .py suffix"),
    ("scripts/rendered_text.py", "§4A.10 stem is `rendered_text_`, with the underscore"),
    ("scripts/rendered_textual.py", "§4A.10 stem is `rendered_text_`, not `rendered_text`"),
    ("scripts/sub/rendered_text_x.py", "§4A.10 stem entry matches directly under scripts/ only"),
    ("helpers/rendered_text_x.py", "§4A.10 stem is under scripts/ only, not any directory"),
    ("helpers/scripts/rendered_text_x.py", "§4A.10 stem is the top-level scripts/, not any scripts/ directory"),
    ("scripts/rendered_text_sub/x.py", "§4A.10 stem matches a file name, not a directory named like one"),
    ("scripts/rendered_text_expected_differences.yaml", "§4A.10 register is the exact .yml path"),
    (".github/workflows/text-presence-notes.yml", "§4A.10 workflow is an exact FILE entry"),
    (".github/workflows/browser-sweep.yml", "a neighbouring workflow is not in the class"),
    ("api/routers/publishing.py", "routers/publishing.py is NOT in any entry"),
    ("api/services/manifest_controls.py", "TOR-1123's instance, still uncovered"),
    ("api/schemas/version_descriptor.py", "schemas are not in the class"),
    ("api/services/slot_registry.py", "slot_registry.py is NOT slots.py (§4A.8 is a FILE entry)"),
    ("authored_pages/lr_historical/README.md", "§4A.1 README carve-out"),
    ("api/services/publishing/anything.py", "the DEAD selector §4A.6 corrected"),
    ("scripts/build_page.py", "page-kit carve-out"),
    ("frontend/src/pagekit/theme.ts", "renderer carve-out"),
    ("docs/agents/publishing-and-compute.md", "docs are not in the class"),
]


def run_controls(entries) -> bool:
    ok = True
    print("  MUST-HIT controls:")
    hits = 0
    for p, why in MUST_HIT:
        lab = classify(p, entries)
        mark = "HIT " if lab else "MISS"
        if lab:
            hits += 1
        else:
            ok = False
        print(f"    {mark}  {p:<48} [{why}]")
    print(f"    -> MUST-HIT {hits}/{len(MUST_HIT)}")

    print("  MUST-MISS controls:")
    misses = 0
    for p, why in MUST_MISS:
        lab = classify(p, entries)
        if lab is None:
            misses += 1
            print(f"    MISS  {p:<48} [{why}]")
        else:
            ok = False
            print(f"    🔴 HIT (SHOULD MISS) {p} -> {lab}   [{why}]")
    print(f"    -> MUST-MISS {misses}/{len(MUST_MISS)}")
    return ok


def _resolved(tracked, kind: str, pat) -> int:
    """How many tracked paths one class entry resolves to."""
    if kind == "file":
        return sum(1 for t in tracked if t == pat)
    if kind == "stem":
        return sum(1 for t in tracked if _stem_match(t, pat))
    if kind == "authored":
        return sum(1 for t in tracked if t.startswith(pat) and Path(t).name != "README.md")
    return sum(1 for t in tracked if t.startswith(pat))


def entry_liveness(repo, ref: str, entries, *, tracked=None, quiet: bool = False) -> bool:
    """§4A.6's owed structural half: every class entry must resolve to >=1 tracked path.

    `tracked` replaces the git listing (used by `liveness_control`, which exercises THIS verdict)."""
    if tracked is None:
        tracked = tracked_at(repo, ref)
    ok = True
    live = 0
    for kind, pat, label in entries:
        n = _resolved(tracked, kind, pat)
        if n == 0:
            ok = False
            if not quiet:
                print(f"    🔴 DEAD ENTRY (0 tracked paths): {label}")
        else:
            live += 1
    if not quiet:
        print(f"    -> ENTRY LIVENESS {live}/{len(entries)}  (ref {ref[:8]})")
    return ok


def liveness_control(entries) -> bool:
    """Negative and positive control for entry liveness (§4A.10), run through `entry_liveness` itself and
    DERIVED from the classification controls so the two cannot drift apart, for EVERY kind of entry: a tree
    holding every MUST_MISS path must leave each entry dead, and a tree holding any ONE must-hit path that
    the entry classifies must leave that entry live."""
    misses = [p for p, _ in MUST_MISS]
    ok = bool(entries)
    for e in entries:
        if entry_liveness(None, "", [e], tracked=misses, quiet=True):
            print(f"    🔴 liveness: {e[2]} is LIVE on a tree of only must-miss paths")
            ok = False
        for h in (p for p, _ in MUST_HIT if classify(p, [e])):
            if not entry_liveness(None, "", [e], tracked=[h], quiet=True):
                print(f"    🔴 liveness: {e[2]} is DEAD on a tree holding its own must-hit {h}")
                ok = False
    print(f"  LIVENESS control (each entry dead on every must-miss path, live on each of its must-hits alone): "
          f"{'ok' if ok else '🔴 FAILED'}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--range", action="append", default=[])
    ap.add_argument("--ref", default="HEAD", help="ref for entry-liveness")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo)

    entries = build_entries(repo)
    codes = product_codes(repo)
    print(f"CLASS ENTRIES: {len(entries)}   products from COMPANY_ROW: {codes}")
    print("CONTROLS")
    controls_ok = run_controls(entries)
    # The liveness control tests the matcher itself (not the ref), so its failure blocks range mode too.
    controls_ok = liveness_control(entries) and controls_ok
    print("ENTRY LIVENESS")
    live_ok = entry_liveness(repo, a.ref, entries)
    if a.self_test:
        print(f"\nSELF-TEST {'PASS' if controls_ok and live_ok else 'FAIL'}")
        return 0 if (controls_ok and live_ok) else 1
    if not controls_ok:
        print("\n🔴 CONTROLS FAILED — do not believe any count below.")
        return 1

    for rng in a.range:
        rows = changed(repo, rng)
        mandatory = [(p, classify(p, entries)) for p in rows]
        mand = [(p, l) for p, l in mandatory if l]
        print(f"\nDELTA {rng}")
        print(f"  total rows : {len(rows)}")
        print(f"  MANDATORY  : {len(mand)}")
        for p, l in mand:
            print(f"    {p}   <- {l}")
        if not mand:
            print("    (none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
