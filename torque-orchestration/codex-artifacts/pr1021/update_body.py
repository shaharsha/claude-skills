#!/usr/bin/env python3
"""Rewrite PR #1021's body for the re-merged head. Exact-match replacements only:
every anchor must appear exactly once, or we abort rather than silently no-op."""
import sys

SUITE_LINE = sys.argv[1]      # e.g. "10712 passed, 50 skipped, 2 xfailed   in 2431.02s"
HEAD = "29c75f56797e07efa01d2db61e13a51c09a303f4"
DEV = "4a63f76861957b73931710a7ef05eaee20b0d9e8"

body = open("/tmp/pr1021_body.md", encoding="utf-8").read()

REPLACEMENTS = []

# ---- 1 · the §4A gates block -------------------------------------------------
REPLACEMENTS.append((
"""§4A matcher      _REAL_PRODUCTS by AST (7 entries, 3-tuples), .lower() applied
                 must-hit 11/11 · must-miss 9/9 — incl. the CASE axis (api/services/SMP/...)
                 and the FILE-vs-package axis (api/services/publishing/... , §4A.6)
§4A.6 assertion  2023 tracked paths · corpus control neg=0 pos=165 · DEAD SELECTORS: none
delta            BEFORE the re-merge  7d21e5ae..77e424f7   47 rows, 25 mandatory (24 develop-side)
                 AFTER                <develop>..<head>     6 rows,  1 mandatory
mandatory row    api/services/vault/raw_read.py  <- api/services/vault/**
ccverify files   CLEAN, exit 0 (it was exit 2 — no FILES: block — at the ruling)""",

"""§4A matcher      _REAL_PRODUCTS by AST (7 entries, 3-tuples, e[0] never str(e)), .lower() applied
                 AST positive control 26 Assign nodes in api/routers/companies.py
                 must-hit 14/14 · must-miss 11/11 — incl. the CASE axis (api/services/SMP/...)
                 and the FILE-vs-package axis (api/services/publishing/... , §4A.6)
§4A.6 assertion  2055 tracked paths · corpus control neg=0 pos=169 · DEAD SELECTORS: none
                 matcher self-check PASS (it exits 3 if any control fails)

§4A.5 delta      measured over the WHOLE baaf5c8b..HEAD, merge-arrived bytes INCLUDED
                 baaf5c8b..29c75f56    140 rows, MANDATORY 18
                 all 18 arrived FROM develop — api/auth/** (8) · api/services/alm/** (5)
                 computation/{batch,broker} (2) · publishing.py · smp/historical_analysis.py
                 · db/schema.py
authored delta   origin/develop 4a63f768...29c75f56   6 rows, 1 mandatory
mandatory row    api/services/vault/raw_read.py  <- api/services/vault/**  (the authored one)
FILES block      6 declared / 6 actual, ZERO undeclared; all 5 NOT TOUCHING verified absent"""))

# ---- 2 · the §4A.4 outcome, stated as measurement ---------------------------
REPLACEMENTS.append((
"""**1 mandatory row, so route A is mandatory and route B cannot discharge it.** Each round ran on the post-merge head, per §4A.5 — a round on `77e424f7` would have been voided by the 24 develop-side mandatory rows the re-merge pulled in.

### Route A artifacts — four rounds, each on a pushed post-merge head""",

"""**1 authored mandatory row, so route A is mandatory and route B cannot discharge it.**

**§4A.4 clause 1, measured at this head rather than pre-declared (§4A.5 forbids pre-declaring the outcome across a re-merge):** round 4's sidecar covers `baaf5c8b`; `git diff --name-only baaf5c8b..29c75f56` is **140 rows of which 18 are mandatory-class**, so **clause 1 does NOT hold and round 4's allowance is VOID**. A fifth route-A round was therefore owed, and ran. This is the conservative direction and it is the one §4A.5 exists to protect.

### Route A artifacts — five rounds, each on a post-merge head"""))

# ---- 3 · add round 5 ---------------------------------------------------------
REPLACEMENTS.append((
"""round 4  .codex-review/20260918-125024-analyst-cli-r2-round4.md   sha=baaf5c8b tree=clean
         SOUND   0 findings
```""",

"""round 4  .codex-review/20260918-125024-analyst-cli-r2-round4.md   sha=baaf5c8b tree=clean
         SOUND   0 findings
round 5  .codex-review/20260918-165108-analyst-cli-r2-round5.md   sha=29c75f56 tree=clean
         SOUND   0 findings (confidence 0.96, gpt-5.6-sol, effort high)
         subject: THE MERGED COMBINATION — the 18 mandatory rows develop brought in,
         read against this PR's read path. Not a re-review of the PR's own bytes.
```"""))

# ---- 4 · durable artifact path + what r5 checked ----------------------------
REPLACEMENTS.append((
"""All four live in `/Users/shaharshavit/Projects/torque/.claude/worktrees/analyst-cli-2-r2/.codex-review/`. **The gate is discharged by round 4, whose sidecar `sha=` equals this head.** Rounds 1-3 are kept because the fix-a-fix pattern they document is the substance of this PR: every round but the last found defects that the previous round's fix had introduced, and all fifteen were green at the moment they shipped.""",

"""**The gate is discharged by round 5, whose sidecar reads `sha=29c75f56797e07efa01d2db61e13a51c09a303f4  tree=clean` — exactly this head.** Read the sidecar, not the markdown header.

**Artifacts copied somewhere durable, because a Codex artifact dies with its worktree (TOR-1322):**

```
round 5 (live)  <worktree>/.codex-review/20260918-165108-analyst-cli-r2-round5.md
round 5 (kept)  ~/.claude/torque-orchestration/codex-artifacts/pr1021/
                  20260918-165108-analyst-cli-r2-round5.{md,json,provenance,prompt.md}
                  artifact_sha256 in the sidecar == sha256 of the kept .md (verified)
rounds 1-4      ~/.claude/torque-orchestration/codex-artifacts/pr1021/prior-rounds-r1-r4/
                  sidecars: e0e2a6f8 · b06c4762 · 4f7e10b1 · baaf5c8b, all tree=clean
4A matcher      ~/.claude/torque-orchestration/codex-artifacts/pr1021/4a_matcher.py
                  + 4a-count-29c75f56.txt (its full output, controls included)
```

**What round 5 was pointed at, and what it returned.** Its four priority questions were the schema/`raw_read` table surface, the auth rework against this CLI's absent auth, `computation/broker.py` against the vault read path, and test-level collisions. It reported **0 findings** with substantive negatives rather than padding — notably that the `CREATE TABLE` blocks for `client_runs`, `upload_sessions` and `upload_objects` are byte-identical across the merge, and that no broker/batch path reads or writes those tables.

⚠️ **That claim was re-verified first-party rather than relayed**, because a zero-finding round is exactly where an instrument should be checked. A first attempt collapsed — one regex returned the *same* hash for two different tables — and was rewritten until it discriminated:

```
probe self-test   4 tables -> 4 DISTINCT hashes   (the broken version gave 2 identical)
client_runs       16cd44fa78ac -> 16cd44fa78ac   IDENTICAL   (343 chars)
upload_sessions   b7bb4a439b03 -> b7bb4a439b03   IDENTICAL   (565 chars)
upload_objects    7ef8cabc9ec5 -> 7ef8cabc9ec5   IDENTICAL   (676 chars)
MUST-FIRE CONTROL auth_session_families  ABSENT at baaf5c8b -> ADDED at head
                  (so the probe CAN see a schema change; db/schema.py itself DIFFERS)
```

⚠️ **What round 5 could NOT do:** its sandbox is read-only, so it could not reach Postgres or create temp files — no database-backed test executed inside the round. That half is covered by the suite below, not by the round.

Rounds 1-4 are kept because the fix-a-fix pattern they document is the substance of this PR: every round but the last found defects that the previous round's fix had introduced, and all fifteen were green at the moment they shipped."""))

# ---- 5 · guard survival across the re-merge ---------------------------------
REPLACEMENTS.append((
"""## Suite

```""",

"""## The re-merge did not delete this PR's own guards — measured, not inferred from an absent conflict

A `merge-tree` rc=0 with green CI has silently removed a PR's own pinned assertion before (#1011, today: develop rewrote a string this PR had pinned in a test, the merge dropped the pin, develop's own pin survived, and nothing reddened). So the survival of this PR's guards is measured in both directions.

```
BLOB IDENTITY            d0b022d7 -> 29c75f56
  tests/test_vault_raw_read.py    1204050d -> 1204050d   IDENTICAL
  tests/test_artifact_fetch.py    935e2a8e -> 935e2a8e   IDENTICAL
  api/services/vault/raw_read.py  252d7aba -> 252d7aba   IDENTICAL
ASSERTION COUNTS (AST, not grep -c, which counts LINES)
  test_vault_raw_read.py   31 test defs / 135 asserts   both sides
  test_artifact_fetch.py    8 test defs /  25 asserts   both sides
MUST-DIFFER CONTROL      the comparator can see a change
  db/schema.py            7454b767 -> c4479a70   DIFFERS
  api/auth/sessions.py    e8a5bf19 -> 704300f5   DIFFERS
  scripts/torque_admin.py 969bc6f2 -> 9e8e02ee   DIFFERS  (this revision's own edit landed)
```

⚠️ **Byte-identity alone would not close this.** A pin can survive intact and still stop matching, if develop rewrote the string it pins somewhere else — the identical-bytes check is blind to that. The completing evidence is that **both files' 39 tests pass on the merged tree** (below), which byte-identity cannot establish and a green develop cannot either.

## Suite

```"""))

# ---- 6 · the suite block ----------------------------------------------------
REPLACEMENTS.append((
"""10670 passed, 50 skipped, 2 xfailed   in 1999.85s (-n 4, heavy machine contention)
head    baaf5c8ba258be56f79dcb12de7a22ef01515d11    tree clean, HEAD unchanged after the run
tree    /Users/shaharshavit/Projects/torque/.claude/worktrees/analyst-cli-2-r2
base    origin/develop 8b7eeacc merged; behind-by 0 at the moment of push""",

"""targeted  39 passed in 80.20s        tests/test_vault_raw_read.py + tests/test_artifact_fetch.py
          -- run FIRST and on the MERGED tree, as the completing half of the guard-survival
             check above: the pins still match what they pin
full      %s
head    29c75f56797e07efa01d2db61e13a51c09a303f4   tree clean, HEAD unchanged after the run
tree    /Users/shaharshavit/Projects/torque/.claude/worktrees/pr1021-remerge
base    origin/develop 4a63f768 merged (two merges: 5337f9cd, then 4a63f768 when #1031 landed)
slot    suite_slot.sh slot3, acquired and released around the run, -n 4 (never -n auto)
db      DATABASE_URL -> torque_dev. pytest creates a disposable DB per process; NO protected
        restore (torque_baseline / torque_qa / railway_production_restore) was read or written""" % SUITE_LINE))

# ---- 7 · the TOR-1330 deferral REASON --------------------------------------
REPLACEMENTS.append((
"""`artifact fetch` still defaults to stdout while `raw fetch` no longer does (a published artifact is already served to authorised readers, which is why the line was drawn there — but it is a judgement call, not a measurement); and the CHECK constraint that would genuinely close the session-state space.""",

"""`artifact fetch` still defaults to stdout while `raw fetch` no longer does — **with a corrected reason, see below**; and the CHECK constraint that would genuinely close the session-state space.

### The `artifact fetch` stdout deferral — its stated REASON was FALSE and is corrected here

The deferral previously read *"a published artifact is already served to authorised readers, which is why the line was drawn there — but it is a judgement call, not a measurement."* **This PR falsifies that thirty lines away.** It renames `served_to_readers` -> `served_by_default` *precisely because the old name was false*, and the field is

```
served_by_default = bool(is_live) and serve_mode == "manifest"
```

so on a `serve_mode='legacy'` slot the **default** path (`--version` omitted, which selects the live version) returns bytes whose own record reads `served_by_default: false` — the page an unqualified request does not return — into a bare `sys.stdout.write(html)`. An explicit `--version N` does the same for any historical version. It also conflated two audiences: *"served to authorised readers"* describes the **app's** gate, and this CLI has none.

**Corrected in `cmd_artifact_fetch`'s docstring in this revision, and on TOR-1330, so the deferral is triaged on a true premise. The BEHAVIOUR is deliberately unchanged** — making `-o`/`--stdout` mutually exclusive and required on `artifact fetch` is a CLI contract change owing its own tests and DONE-WHEN, and the adjudicating seat explicitly did not ask for it here.

## What this PR does NOT close

🔴 **It narrows what an analyst reaches for. It does not narrow who may reach.** `scripts/torque_admin.py:main()` authenticates nobody — it opens a connection and dispatches; there is no principal, no role check, and the read is recorded only to a Python `logger`, never to a durable audit row. Handing an analyst this verb still means handing over a database DSN and an AWS profile. The verb is the right shape for an authorization boundary to be added later, but there is no parameter in it where a principal would go. Nothing in this PR should be read as an access-control change."""))

out = body
for old, new in REPLACEMENTS:
    n = out.count(old)
    if n != 1:
        sys.exit("ABORT: anchor matched %d times (need exactly 1):\n---\n%s\n---" % (n, old[:220]))
    out = out.replace(old, new)

open("/tmp/pr1021_body_new.md", "w", encoding="utf-8").write(out)
print("OK — %d replacements applied, all anchors unique" % len(REPLACEMENTS))
print("old %d lines -> new %d lines" % (body.count("\n") + 1, out.count("\n") + 1))
for probe, want in [("already served to authorised readers, which is why", 0),
                    ("round 5", 1), ("29c75f56", 6),
                    ("does not narrow who may reach", 1)]:
    got = out.count(probe)
    print("  probe %-46s %d (want %s) %s" % (probe[:44], got, want,
          "OK" if (got == want if isinstance(want, int) else True) else "*** MISMATCH ***"))
