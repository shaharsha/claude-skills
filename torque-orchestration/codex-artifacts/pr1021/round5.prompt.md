# Adversarial review — PR #1021 `torque-admin` analyst read verbs, ROUND 5: THE MERGED COMBINATION

You are reviewing bytes you did not write. Be adversarial and concrete. A finding must name a
file and a mechanism, with the concrete input or row state that triggers it. Do not report style
preferences, and do not restate the PR's own claims back to me as findings. If a category is
clean, say so explicitly rather than padding.

## Why this round exists — it is NOT a re-review of the PR

Four rounds already ran on this PR's own bytes; round 4 returned SOUND with 0 findings at
`baaf5c8b`. The branch has since been merged with `origin/develop` twice. That merge brought **18
mandatory-class rows** in from other people's merged work.

**The question this round exists to answer is the one no previous round could:**

> Each side's round read bytes that were fine. **Nobody has read the combination.**

Both merges reported no conflict and the tree is clean. That is not evidence the combination is
correct — git reports no conflict for a semantic one. **Your subject is the interaction**, not the
PR's own diff in isolation and not develop's changes in isolation.

## The two sides

**Side A — what this PR adds** (already reviewed four times; re-report a defect here only if the
merge is what makes it wrong):

- `api/services/vault/raw_read.py` — NEW module. Two read-only service functions, `resolve` and
  `fetch`, over the raw client vault.
- `api/services/control_plane/artifacts.py` — NEW function `fetch_artifact`.
- `scripts/torque_admin.py` — CLI wrappers `cmd_raw_runs`, `cmd_raw_list`, `cmd_raw_fetch`,
  `cmd_artifact_fetch`, and their argparse parsers.
- `tests/test_vault_raw_read.py`, `tests/test_artifact_fetch.py`.

**Side B — what arrived from develop in the merge.** Review `git diff baaf5c8b..HEAD` restricted
to these, and read them as *the environment side A now runs in*:

```
api/auth/{__init__,config,deps,grants,roles,session_format,sessions,tokens}.py   (+~620 lines;
      sessions.py alone is +368 — an auth-token/live-session binding rework)
api/services/computation/{batch,broker}.py                                       (+277)
api/services/alm/{dealops,dealops_context,live_risk_analysis,monitoring,
                  monitoring_management}.py                                      (a page split)
api/services/publishing.py · api/services/smp/historical_analysis.py             (small)
db/schema.py                                                                     (+132)
```

## Where I most want an independent read — in priority order

1. **`db/schema.py` against `raw_read.py`'s three tables.** `raw_read` reads `client_runs`,
   `upload_sessions` and `upload_objects` (see its two SQL statements, and the
   `state`/`version_id` columns it filters on). I measured that db/schema.py's delta contains
   **zero changed lines mentioning any of those three table names** — command:
   `git diff baaf5c8b..HEAD -- db/schema.py | grep -c <table>`. **Try to falsify that**: a
   constraint, trigger, index, enum, default, or a renamed shared column could reach those tables
   without naming them on a changed line, and a grep over changed lines cannot see a table reached
   indirectly. If it holds, say so.

2. **The auth rework against this CLI's complete absence of auth.** `scripts/torque_admin.py`'s
   `main()` authenticates nobody: it opens a connection and dispatches. The incoming
   `api/auth/**` change binds auth tokens to live sessions. Does anything in that rework create a
   surface this CLI now bypasses *differently* than before — a grant, role or session row that
   other code now assumes exists, or an invariant that the CLI's unauthenticated read violates now
   but did not at `baaf5c8b`? I am not asking you to relitigate that the CLI is unauthenticated;
   that is known and recorded. I am asking whether the MERGE changed what that costs.

3. **`computation/broker.py` and `batch.py` against the vault read path.** The broker grew 256
   lines. Does it now write, move, or reinterpret any `upload_sessions.state`,
   `client_runs` row, or vault object that `resolve`'s admission predicate reads? `resolve`
   refuses a newest run that is not `sealed`, and admits a deliberate `--run` read of one that is
   not. If the broker can now produce a session state combination that predicate did not
   anticipate, that is the finding I most expect to exist.

4. **Test-level collisions the merge could have created silently.** Both new test files are
   byte-identical across the merge (I verified blob ids, with a must-differ control). But a test
   can keep its bytes and lose its meaning: a fixture, conftest, factory or shared helper that
   develop changed underneath it, a table or column the test seeds that schema no longer defines,
   or a pinned string that develop rewrote elsewhere. **Name any assertion in
   `tests/test_vault_raw_read.py` or `tests/test_artifact_fetch.py` that no longer constrains what
   its name says it constrains, given side B.**

5. **`api/services/publishing.py` and `fetch_artifact`.** `fetch_artifact` resolves a version via
   `list_artifact_versions` and computes
   `served_by_default = is_live and serve_mode == "manifest"`. `publishing.py` is the sole writer
   of `page_pointers` / `page_versions` and owns `set_serve_mode`. Its delta is small — check
   whether it changed anything `served_by_default` depends on, or any state in which that
   expression now asserts something false.

## Settled decisions — context, so you do not report them as findings

- **`artifact fetch` still defaults to stdout while `raw fetch` requires `-o`/`--stdout`.** This is
  a deliberate, recorded deferral (TOR-1330). Its originally-stated reason ("a published artifact
  is already served to authorised readers") was found FALSE and has been corrected in this very
  head — see `cmd_artifact_fetch`'s docstring. **The behaviour is knowingly unchanged.** Report a
  defect here only if you find something neither the docstring nor TOR-1330 already states.
- The CLI takes a DSN and an AWS profile and has no principal, no role check and no audit row. Known
  and recorded; not a finding.
- `resolve`'s `other_runs` carries bare run ids without states. Known, deferred, recorded.
- Three hypotheses were tested in earlier rounds and FAILED — do not redo them: the `.get()`-vs-`[]`
  access on `is_live`/`serve_mode`; duplicate candidates from the `upload_sessions` join; a
  `DEFAULT_MAX_BYTES` bypass when size is 0.

## The domain invariant that matters most

Raw client files are immutable evidence in an S3 vault. Every read must address the **recorded
`VersionId`** captured at seal time, never a bare key — a presigned PUT can land after a seal, so a
bare-key read can return bytes nothing verified. `upload_sessions.state` (`open|sealing|sealed|
failed`) is the schema's declared source of truth for "may this run be analysed".

## Runtime context

Single-process CLI, run by a human operator against a live Postgres and a real S3 vault. Inputs are
operator-supplied (slug, path, run id) and therefore trusted-ish, but the DATA read is real client
evidence. The API side (`api/**`) runs concurrently under a web server; the CLI does not.
