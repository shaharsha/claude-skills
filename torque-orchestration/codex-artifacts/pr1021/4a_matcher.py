#!/usr/bin/env python3
"""4A mandatory-class matcher. Stdlib only. Run from the worktree root.

Class (APPROVAL-CRITERIA.md 4A, as amended by 4A.1/4A.2 and corrected by 4A.6):
  engine/**  models/**  risk/**
  api/services/<product>/**  for product in _REAL_PRODUCTS (AST-parsed, lowercased)
  db/schema.py  api/auth/**  api/services/{vault,silver,computation}/**
  api/services/publishing.py      (FILE entry, 4A.6)
  authored_pages/** EXCEPT **/README.md
  api/services/projector/**
"""
import ast
import subprocess
import sys
import posixpath

ROOT = "."


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def real_products():
    """AST-parse _REAL_PRODUCTS from api/routers/companies.py.

    Never grep: a commented-out SMPRT block greps live. The constant holds
    3-tuples, so take e[0], never str(e).
    """
    src = open("api/routers/companies.py", encoding="utf-8").read()
    tree = ast.parse(src)
    assigns = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]
    node = None
    for n in assigns:
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id == "_REAL_PRODUCTS":
                node = n.value
    if node is None:
        sys.exit("FATAL: _REAL_PRODUCTS not found by AST")
    entries = ast.literal_eval(node)
    arity = {len(e) if isinstance(e, tuple) else -1 for e in entries}
    codes = [e[0] if isinstance(e, tuple) else e for e in entries]
    return codes, len(assigns), arity


def build_class(codes):
    sel = []
    for p in ("engine", "models", "risk", "api/auth"):
        sel.append((p + "/**", "dir"))
    for s in ("vault", "silver", "computation", "projector"):
        sel.append(("api/services/%s/**" % s, "dir"))
    for c in sorted(codes):
        sel.append(("api/services/%s/**" % c.lower(), "dir"))
    sel.append(("db/schema.py", "file"))
    sel.append(("api/services/publishing.py", "file"))
    sel.append(("authored_pages/**", "dir_except_readme"))
    return sel


def matches(path, sel):
    """Return the selector that puts `path` in the class, or None."""
    for pat, kind in sel:
        if kind == "file":
            if path == pat:
                return pat
        elif kind == "dir":
            prefix = pat[:-3] + "/"
            if path.startswith(prefix):
                return pat
        elif kind == "dir_except_readme":
            prefix = pat[:-3] + "/"
            if path.startswith(prefix):
                if posixpath.basename(path) == "README.md":
                    continue
                return pat
    return None


def main():
    base, head = sys.argv[1], sys.argv[2]
    codes, n_assign, arity = real_products()
    print("AST positive control   %d Assign nodes in api/routers/companies.py" % n_assign)
    print("entries=%d  arity=%s   %s" % (len(codes), sorted(arity), codes))
    sel = build_class(codes)
    print("product slugs          %s" % sorted(c.lower() for c in codes))
    print("selectors              %d" % len(sel))

    # --- dead-selector check (4A.6): every selector must resolve to >=1 tracked path
    tracked = sh("git", "ls-files").splitlines()
    print("\ntracked paths          %d" % len(tracked))
    dead = []
    for pat, kind in sel:
        hits = sum(1 for t in tracked if matches(t, [(pat, kind)]))
        if hits == 0:
            dead.append(pat)
    print("DEAD SELECTORS         %s" % (dead if dead else "none"))

    # --- corpus two-direction control
    neg = sum(1 for t in tracked if matches(t, [("api/services/definitely_not_a_real_dir/**", "dir")]))
    pos = sum(1 for t in tracked if matches(t, [("api/services/**", "dir")]))
    print("corpus control         neg=%d (must be 0)  pos=%d (must be >0)" % (neg, pos))

    # --- must-hit / must-miss controls
    MUST_HIT = [
        "engine/x.py", "models/x.py", "risk/x.py", "db/schema.py",
        "api/auth/sessions.py", "api/services/vault/raw_read.py",
        "api/services/silver/x.py", "api/services/computation/batch.py",
        "api/services/publishing.py", "api/services/projector/chart_compiler.py",
        "api/services/smp/data.py", "api/services/lr/forecast.py",
        "api/services/tbr/historical_analysis.py",
        "authored_pages/alm_historical/body.html",
    ]
    MUST_MISS = [
        "api/services/control_plane/pages.py", "scripts/torque_admin.py",
        "scripts/build_page.py", "db/pg.py", "tests/test_vault_raw_read.py",
        "authored_pages/alm_historical/README.md",
        "api/routers/publishing.py",
        "api/services/SMP/data.py",            # CASE axis
        "api/services/publishing/x.py",        # FILE-vs-PACKAGE axis (4A.6)
        "frontend/src/App.tsx",
        "api/services/vaultish/x.py",          # prefix-not-dir axis
    ]
    hit_ok = miss_ok = 0
    for p in MUST_HIT:
        m = matches(p, sel)
        print("MUST-HIT   %-52s %s" % (p, m if m else "*** MISSED ***"))
        hit_ok += 1 if m else 0
    for p in MUST_MISS:
        m = matches(p, sel)
        print("MUST-MISS  %-52s %s" % (p, ("*** HIT by %s ***" % m) if m else "ok"))
        miss_ok += 0 if m else 1
    print("CONTROLS   must-hit %d/%d   must-miss %d/%d"
          % (hit_ok, len(MUST_HIT), miss_ok, len(MUST_MISS)))

    # --- the actual delta
    rows = sh("git", "diff", "--name-only", "%s..%s" % (base, head)).splitlines()
    rows = [r for r in rows if r.strip()]
    mand = [(r, matches(r, sel)) for r in rows]
    mand = [(r, m) for r, m in mand if m]
    print("\nDELTA %s..%s" % (base, head))
    print("rows %d   MANDATORY %d" % (len(rows), len(mand)))
    for r, m in sorted(mand):
        print("    %-60s <- %s" % (r, m))

    ok = (not dead) and neg == 0 and pos > 0 and hit_ok == len(MUST_HIT) and miss_ok == len(MUST_MISS)
    print("\nMATCHER SELF-CHECK %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
