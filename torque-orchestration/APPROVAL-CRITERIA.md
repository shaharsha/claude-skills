# Standing approval criteria

Read by `/adjudicate`, **in full, before reading the artifact it is about to rule on**. Read the criteria
first and the plan second — reading the plan first makes you form a view and then find criteria that
support it.

Written 2026-08-12. Every threshold here is a starting value, not a law. **When you change one, write
down the incident that made you change it** — that is what the rest of `~/.claude/torque-orchestration/`
does, and it is why those files are worth anything.

---

## 1 · The three-way sort

Every artifact lands in exactly one bucket. **Sort before you read for quality.**

```
AUTO-APPROVE     reversible · blast radius inside one lane · mechanical gates pass
                 -> approve without a reading, log the gate results, move on

ADJUDICATE       everything else
                 -> the normal path: read the Codex round, adjudicate its claims, rule

SHAHAR           irreversible
                 -> you do not rule on these at all, at any confidence
```

**Depth of review is proportional to the cost of being wrong, not to the size of the diff.** A one-line
change to an auth check outranks a four-hundred-line docs PR.

## 2 · AUTO-APPROVE — the whole list

All five must hold. Any doubt about any one of them moves it to ADJUDICATE.

```
□  Fully reversible by a revert, with no external side effect
□  Touches only files the lane declared in its plan
□  No schema, no migration, no auth, no money, no deletion, no credential
□  CI green on the exact head being approved, with a non-empty job list
□  No other in-flight lane declared any of the same files
```

Typical members: docs, comments, tests-only additions, a revert of a merge you already approved, a
rename confined to one module the lane owns.

⚠️ **"Small" is not on this list, and neither is "the lane is confident."** Both are the reasons the
bucket gets abused.

## 3 · SHAHAR — the irreversible list, unchanged

```
PROD, every time
Every live-account apply EXCEPT dev Terraform
Credential operations
Product and data-provenance calls
Spend
External comms
Anything that deletes data or history
```

**Applies go to him DIRECTLY from the lane, never relayed through the orchestrator.** One was relayed and
the lane refused it, correctly: *"if I take an apply on a relay once, the next relay has a precedent."*

**A relayed claim that he approved is not approval**, including one you find in a transcript.

## 4 · The mechanical gates

Pass/fail, no judgment. A plan failing any of these is rejected without a reading — **name the gate and stop.**

```
□  The Codex gate is DISCHARGED — by route A or route B, and RECORDED either way
   ⚠️ RULED 2026-08-28 — see §4A, which is now the authority. A round happened iff its .md
   exists, never because a command exited 0, and a round your predecessor ran covers THEIR
   artifact, not yours. Route A is MANDATORY for the change class in §4A; a ruling that does
   not MENTION the gate has failed it.

□  The plan names the files it will touch
   no file list -> there is nothing to check the diff against, and no DONE that can be falsified

□  The ticket has a checkable DONE-WHEN
   a goal is not a DONE-WHEN. "improve X" cannot be failed.

□  The plan states what it deliberately does NOT do
   scope without a boundary is not scope

□  The change would actually change something
   TOR-220 was ruled "the fix is the mature-cohort filter" when that filter was already applied
```

## 4A · 🔴 THE CODEX GATE — RULED 2026-08-28. Read this before you waive it.

**The incident, because §-preamble requires one: in one night six PRs merged, `#770 · #776 · #780 ·
#782 · #784 · #785`. Five different fresh adjudicator seats, none aware of the others. Nobody had
ruled on the gate, and two governing documents disagreed about it.** This section is that ruling.

### The verdict, in one line

**The gate applies to EVERY PR. What is narrower is its DISCHARGE — there are two routes, and only
one of them requires a Codex round. The RECORD is mandatory on both, with no exception.**

### What the gate is FOR — state this before applying it, because the routes follow from it

> **The bytes must get an adversarial read by something that did not write them.**

Everything below is derived from that sentence. A route that discharges the function satisfies the
gate; a route that does not, does not — regardless of how much work it represents.

### The two routes

```
ROUTE A   A CODEX ROUND ARTIFACT
          `.codex-review/<label>.md` EXISTS, and its `.provenance` sidecar reads
          sha=<the head you are ruling on>  and  tree=clean.
          Read the SIDECAR, not the markdown header (LANE-PREAMBLE §6: a header-keyed
          check silently passes every --no-schema round).
          A round happened iff its .md exists — never because a command exited 0.

ROUTE B   THE ADJUDICATOR PERFORMS THE PASS FIRST-PARTY
          Discharged ONLY if the ruling NAMES AT LEAST ONE HYPOTHESIS THE ADJUDICATOR
          ORIGINATED — one the lane's own evidence did not contain — and states its
          outcome, held or failed.

          ⚠️ RE-RUNNING THE LANE'S EVIDENCE IS NOT ROUTE B. Re-running a mutation table
          verifies an existing hypothesis. Route B requires a NEW one. If every number in
          your ruling has a counterpart in the PR body, you re-measured; you did not
          adjudicate the bytes, and the gate is UNDISCHARGED.
```

⚠️ **ROUTE A ALSO REQUIRES A PROMPT VERDICT — `VERIFIED` / `BROKEN` / `CANNOT-TELL`, ADDED
2026-09-19, §4A.7.** The two conditions in the fence above are about the *answer*; a sidecar can
satisfy both while the *question* it names is unreadable or has been replaced. Measured: 242 of 498
sidecars record a `prompt=` that no longer resolves, and 3 resolve to bytes that disagree with the
hash recorded beside them. **Read §4A.7 before ruling route A discharged** — a dangling prompt is
CANNOT-TELL, which is neither a pass nor a refusal and must be STATED.

### 🔴 ROUTE A IS MANDATORY — route B cannot discharge it — for this change class

```
engine/**          models/**          risk/**
api/services/<product>/**   for any product in COMPANY_ROW (tests/fixtures/company_rows.py)
db/schema.py · api/auth/** · api/services/{vault,silver,computation}/**
api/services/publishing.py              CORRECTED 2026-09-18 — see §4A.6
authored_pages/** EXCEPT **/README.md   ADDED 2026-09-15 — see the amendment directly below
api/services/projector/**               ADDED 2026-09-16 — see §4A.2
```

🔴 **PRODUCT-LIST SOURCE CHANGED 2026-09-18 — `_REAL_PRODUCTS` NO LONGER EXISTS.** PR #1040 deleted it
(develop `abbb8e4f`): a client is now a row in `clients`, not a literal in `api/routers/companies.py`.
**Every matcher that AST-parses that constant now resolves NOTHING and returns a silent zero for the
product branch** — a clean-looking §4A count that measured nothing, on the gate every PR passes
through. **This is §4A.6's failure mode repeating: a selector matching zero paths, reported as zero
rows.**

**Read the product list from `tests/fixtures/company_rows.py` — `COMPANY_ROW` (code → company name),
with `TENANTS` beside it.** 🔑 **Why a fixture and not the registry: the registry is per-DATABASE, so
no checkout can read the live set, and a glob needs something a checkout can compute.** A matcher must
resolve from tracked bytes or it cannot run in CI, in a worktree, or on a detached head.

⚠️ **Run a MUST-HIT control on the product branch specifically** — e.g. `api/services/lr/x.py` → hit —
before believing any count. A non-resolving source and an empty product set are indistinguishable from
the count alone, and **all seven codes are UPPERCASE against seven lowercase directories, so
case-normalisation stays load-bearing.**

⚠️ **Historical case records below (§4A.5, §4A.6 and the ruling log) still name `_REAL_PRODUCTS` and
are LEFT AS WRITTEN** — they are the record of what was measured at the time, not live instructions.

⚠️ **`api/services/publishing.py` is a FILE entry on purpose — it is a module, not a package.** It sat
inside the brace group as `publishing/**` until 2026-09-18, a selector matching **zero paths**; §4A.6
holds the measurement. **Keep this fence machine-parseable — put reasons outside it, never inside**, or a
matcher reads the explanation as a class entry (which happened to the very check that produced §4A.6).

⚠️ **A sidecar naming an EARLIER sha can still discharge route A — §4A.4, bounded. And the SCOPE of a
round on `authored_pages/<page>/` is that whole directory, its README included — §4A.1.**

**Read the product membership THERE, never from a list written here** — that is this repo's own rule
and this file has already watched two transcribed counts rot. Everywhere else, route B is sufficient.

🔑 **THE PRINCIPLE THE CLASS EXPRESSES — one sentence, and it REPLACES *"content that becomes
immutable"* (ruled 2026-09-16 — §4A.1, §4A.2, §4A.4):**

> **Route A is mandatory where a wrong claim can reach a real client's decision, AND no EXECUTING
> gate would go red first.**

Both clauses do work, and the old sentence had neither. **"Reach a real client's decision"** is wider
than *content that becomes immutable*: it covers the artifact, **the machine that produces it**, and
**the record a publish decision rests on** — the two things the old wording is silent about, and the
two places §4A was measured wrong inside 24 hours. **"No executing gate would go red first"** is the
axis this section had already used twice without naming: the 2026-09-15 amendment turned on *no gate
renders anything*, and the `assets/vendor/**` carve-out was rescued by naming `bundle_currency.test.ts`
as a guard that RUNS. Naming it makes membership **derivable** instead of enumerated, and makes every
carve-out contingent on a **named, runnable** check rather than on a claim about blast radius.

### ⚠️ AMENDMENT 2026-09-15 — `authored_pages/**` JOINS THE MANDATORY CLASS (approved by Shahar)

**The list above excluded the thing its own defining sentence describes.** The class is *what a wrong
number reaches: a real client's decision page, or an immutable published version.* An authored page is
BOTH — it is a real client's DECISION slot, and publishing it is immutable. It was nevertheless absent,
so two authored DECISION pages for real clients (`#938` FRTC/simulator, and `#935` LR/forecast pending)
discharged route B tonight, correctly by the letter.

**What makes this different from an ordinary omission is that the automated gate is MEASURED BLIND here.**
For manifests the four page gates plus the acceptance equalities carry real weight. For an authored page
they do not:

```
A page reverted to a known-broken charts.js passed ALL FOUR gates at RC=0
while a series drew in 12 disconnected pieces against the builder's 1.
```

Measured by execution 2026-09-15. The reason is structural — **no gate renders anything**: two are stdlib
`HTMLParser`, one runs in a node `vm` with a stubbed `document`, and `parity.py` half (c) calls a function
whose own comment reads `undefined; // deliberately NOT rendered`. Four lanes hit gate-invisible render
defects the same night (an un-clamped control echo · four browser-clamped sliders **jsdom could not
reproduce** · a dropped `error_x` interval on a horizontal dot plot · a recompute throw that silently
abandoned a page's KPIs, a 5x7 grid and both loan bases).

🔑 **So the human adversary is not a second opinion here — it is the ONLY opinion.** That is precisely the
condition the mandate exists for, and it was the one place the list had exempted.

⚠️ **`authored_pages/**/README.md` IS EXCLUDED FROM THE **TRIGGER** — and NOT from a round's SCOPE. Read §4A.1 before citing this sentence: a README-only PR needs no round, but once a round IS triggered the README is INSIDE it. Both clauses are live and they govern different questions; a lane reading this line alone on 2026-09-16 concluded the opposite and reported a correct brief as wrong.** The exclusion follows from the trigger rather than from convenience.** The trigger is *content that becomes immutable*. A page README is the opposite: CLAUDE.md designates it as **mutable and travelling with the page** — it is where the platform-state prose that may NOT go on the page is required to live instead. It is rendered to no client and published nowhere. Corrected the same night the amendment landed, after the glob as first written would have required a round on a three-README docs PR (`#943`).

🔵 **SUPERSEDED IN PART, 2026-09-16 — §4A.1.** The *trigger* this paragraph defends survives and is
kept. Its stated GROUND does not: ~~*"the trigger is content that becomes immutable"*~~ is struck as
the class's principle (see the principle block in §4A above), and *"rendered to no client and published
nowhere"* is true of the file and **false of its effect** — CLAUDE.md/TOR-782 make a page README the
artifact a publish decision is read from, and TOR-1059 is a README that told a reader there was nothing
published to republish. Struck rather than rewritten, per this file's own rule: a replaced sentence is
indistinguishable from a checked one.

⚠️ **This does NOT widen the class to every page-kit file.** `scripts/{build_page,lint_page,gen_page_kit_css}.py`
and `.claude/skills/torque-page-kit/**` stay route B — **but NOT for the reason first written here.**

🔴 **The original justification was *"a defect there surfaces on the next build rather than being frozen into
a published artifact"*, and that is FALSE for one file in the exempted set.** `assets/vendor/torque-charts.js`
is inlined **VERBATIM** by `build_page.py:190` into a page that is immutable once published, and CLAUDE.md's
own TOR-785 entry records a stale bundle freezing **7 wrong numbers onto `LR/historical` v1**. The repo had
already falsified that sentence before it was written here.

**The exemption still stands, on the ground that actually holds: an EXECUTING guard covers it.**
`frontend/src/pagekit/bundle_currency.test.ts` re-runs `build:page-kit` into a scratch directory and
byte-compares the result against the committed bundle, inside `test-frontend` — so a stale bundle reddens CI
rather than reaching a page. That is a check anyone can run, not a claim about blast radius.

⚠️ **So the carve-out is contingent on that guard continuing to execute.** If `bundle_currency.test.ts` is
ever weakened to a presence check, or the bundle stops being byte-compared, `assets/vendor/**` belongs in the
mandatory class immediately. Corrected 2026-09-15, same night, after an adjudicator measured the original
reason against TOR-785.

**Cost:** unchanged from the measurement above — a round's median is 280s against a ~12 minute CI window it
runs concurrently with. The section's own tripwire applies here too: if over the next two weeks route-A
rounds on authored pages return only restatements, this amendment is too wide; narrow it.

**Cost, MEASURED rather than asserted** — the objection this mandate has to survive is *"rounds are
expensive"*, and it is false at this scale. The seven rounds on PR #770, timed from each round's
`.prompt.md` to its `.json`:

```
457s · 166s · 233s · 248s · 373s · 280s · 304s      median 280s (4m40s)
```

Backend CI on this repo is ~12 minutes (§5). **A round fits inside the CI window you are already
waiting on, and can run concurrently with it.** For the narrow class above the marginal wall-clock
cost is approximately zero. That is why the mandate is affordable, and it is also why the class is
kept narrow rather than universal.

### ⚠️ AMENDMENT 2026-09-16 · §4A.1 — the README carve-out is KEPT as a TRIGGER and OVERRULED as a SCOPE

**Two defects in the 2026-09-15 amendment were measured within 24 hours of it landing, in opposite
directions. This section and §4A.2 are one ruling, because they are one question.**

**The framing this was commissioned on is FALSIFIED, and that changes the fix.** The commissioning
account treats the README exclusion as the cause and proposes widening the trigger. Measured
2026-09-16:

```
PR #942  files = authored_pages/alm_historical/body.html   — ONE file, NO README
         merged 2026-09-15T20:33:13Z, i.e. 54 min AFTER the amendment (67adbbe, 19:39:19Z)
         -> already IN the mandatory class
         -> PR body carries "### Codex gate — ROUTE A, DISCHARGED", artifact
            .../wt-almhist/.codex-review/20260915-225722-alm-yoy-stale-pr942.md
         -> TOR-1153 happened ANYWAY
```

🔑 **So the class was applied, a route-A round ran, and the README still went stale.** No file-glob
trigger could have helped: **the round's scope was the diff, and the README was not in the diff.** The
PR's own body even *quotes* that README's four-clean-gates claim as evidence of the defect (`#942`
body, the `scratch_almhist_build` paragraph) — the author read it and still did not update it. **This
is not an attention failure and it is not a trigger failure. Nothing asked the question.**

**Classify the four cited instances by whether a trigger can reach them at all** — the brief presents
them as one class and they are three:

| instance | README in the PR's files? | reachable by a TRIGGER? |
| -- | -- | -- |
| **#941** (the defect-1 instance) | **yes** | yes |
| **TOR-1153 / #942** (called the sharpest) | **no** — `body.html` only | **no** |
| **TOR-1059** (`frtc_historical` "NOT PUBLISHED") | **no PR exists** — a `page_pointers` write falsified it | **no, by anything in §4A** |

**RULING — trigger unchanged, scope widened:**

1. **The trigger stays exactly as `cb118ec` wrote it.** `authored_pages/**` EXCEPT `**/README.md`; a PR
   touching **only** READMEs stays route B. The counter-argument is real and it holds: a gate that
   fires on correct work gets deleted.
2. **NEW — when route A fires because a PR touches `authored_pages/<page>/`, the round's SCOPE is that
   whole `<page>/` directory, its README included**, and the ruling must state, in one line, whether
   the change falsifies anything that README asserts. The codex-review skill already makes scope a
   property of what you hand the reviewer (*"Hand it the outputs as well as the source"*), so this
   needs no new machinery.

**Cost, measured rather than asserted — 381 PR merges into `origin/develop`, 2026-08-17 → 2026-09-16,
must-fire control passing:**

```
README-ONLY PRs (what the carve-out protects)        8    -> unchanged, still route B
README + page bytes  (#941's shape)                 22    -> ALREADY route A; scope now covers it
page bytes only, no README  (#942 / TOR-1153)       15    -> ALREADY route A; scope now covers it

MARGINAL MANDATORY ROUNDS ADDED BY THIS RULING:      0
```

**Zero, because every PR it applies to is already in the class.** It buys #941's shape and reaches
TOR-1153's — which widening the trigger does not, at any glob.

⚠️ **THE COST I AM ACCEPTING, stated so it can be held against me:** a README-only PR gets no mandatory
round. That leaves **`#943`'s own class uncovered** — and `#943` is not a neutral example, it is
*"three READMEs claimed 3 of 4 parity halves do real work — only ONE does"*, i.e. **the PR cited to
justify the exemption was itself a fix for false README claims.** Route B still applies there and
still requires an originated hypothesis. If a README-only PR ships a false claim that reaches a
publish decision, this ruling is wrong and the trigger must widen — record it with the PR number.

⚠️ **NOT CLAIMED: this does not reach TOR-1059.** That README was falsified by an `artifact publish` —
an act with no PR, no diff and no §4A route. See §4A.3, which is the larger problem.

### ⚠️ AMENDMENT 2026-09-16 · §4A.2 — `api/services/projector/**` JOINS THE MANDATORY CLASS

Raised by PR #947's adjudicator after merge. **Verified first-party**: `#947` touched
`api/services/projector/{chart_compiler,chart_field_honouring}.py`; `projector` is in neither
`_REAL_PRODUCTS` nor `{publishing,vault,silver,computation}`, so the omission is real and route B was
correct by the letter.

🔑 **AND IT WAS ALREADY FILED — TOR-1123, 2026-09-14, the day BEFORE the amendment**, found by
searching Linear rather than by filing blind. It names the *general* defect exactly: the class is
**defined by blast radius and SELECTED by path globs**, the two sets are not the same, *"and where they
disagree the selector silently wins, because nothing compares them."* Its instance is PR #918 —
`manifest_controls.py` and `control_plane/pages.py`, both publish boundaries, both matching no glob —
where the gate fired only because an adjudicator read the definition and overrode the list by hand.
**So the amendment landed one day after this exact failure mode was written down, and reproduced it.**
That is the argument for the PRINCIPLE above carrying more weight than any list, and it is why
TOR-1123's option 2 is named as Shahar's in §4A.4 rather than quietly adopted here.

**Why it is in, on the principle above rather than on "more review is safer":**

The projector is the only code path that turns a builder's page into an immutable `page_versions` row.
Clause 1 of the principle is satisfied by its defining sentence. **Clause 2 is the measured half** —
`git grep -n "diff_baseline" -- .github/` and the same for `project_manifests` **both return no
matches**: the end-to-end equivalence gate runs in **zero** workflows.

⚠️ **State that precisely, because the overclaim is available and I nearly made it.** The projector is
NOT uncovered: **53 test files / ~961 test definitions import `api.services.projector`, and the bare
`pytest -n 8 -q` at `ci.yml:105` collects every one of them** against a live Postgres. What is absent
is the *semantic* comparison. `tests/baseline/test_acceptance_targets_are_gradable.py:27` says so in
its own words — *"only `--acceptance-db --through-router`, which no workflow invokes, goes red."* The
truth checks degrade to **shape checks over synthetic fixtures** in CI because the frozen extracts are
gitignored. That is clause 2, and it is the same condition — *the thing that would catch this is not
run* — that justified the `authored_pages` amendment one day earlier.

🔴 **DIRECTION-SENSITIVITY IS REJECTED, and the second reason matters more than the first.** The
proposal was to mandate route A only for a projector change that *admits* more.

1. **A trigger must be decidable from the file list**, because the reviewer must know the route
   *before* doing the work. "Does this admit more?" is answerable only by performing the review.
2. **"Refuses more is safe" is FALSE as a general claim.** A wrong refusal freezes no number — it
   silently removes a slot from the migration, and CLAUDE.md records both halves: TOR-939
   (*"a projecting count is not a migratable count — never size the remaining migration off one"*) and
   TOR-639, where a new refusal firing **earlier** than the declared one left `FRTC/financial`
   mis-declared for a day. The asymmetry is real for *immutability* and does not hold for *roadmap
   inputs*, so it cannot carry a review trigger.

**Cost, MEASURED — same window and control as §4A.1:**

```
PRs touching api/services/projector/**            41 / 381
mandatory class TODAY (union of every member)    138 / 381   (36.2%)
mandatory class WITH the projector               171 / 381   (44.9%)
MARGINAL — pulled in by the projector alone       33         (+24% on the class)
```

⚠️ **An earlier pass of this measurement read `37 → 73, "the class nearly doubles"`. That was a DEAD
PROBE** — zsh does not word-split an unquoted parameter, so a `$CLASS` pathspec matched nothing and
only the `authored_pages` branch was counting. Struck rather than overwritten, and stated because
**the correction moved the number in the direction that flatters the widening I was already leaning
toward** (+24%, not +97%) — the direction nobody re-checks. The corrected run carries a must-fire
control. **Re-run it rather than citing these digits.**

**This is the largest single addition the class has had — larger than `models/**` (23) or `engine/**`
(21), second only to `authored_pages/**`.** It is affordable on §4A's own arithmetic (median round
280s, concurrent with a ~12 min CI window) and it is **consistent with, not an escalation beyond, the
amendment approved the previous night**, which admitted a *larger* member (45) on the identical
clause-2 reasoning.

**Falsifier:** if over the next two weeks route-A rounds on projector PRs return only restatements,
this is too wide — narrow it to `{payload,publish,chart_compiler}.py` and record the PR number.

### 🔴 §4A.3 — THE BIGGEST PROBLEM WITH §4A, WHICH NEITHER NAMED DEFECT TOUCHES

**Asked for deliberately, and it is not a third item on the list — it is the reason the first two
exist. §4A protects immutability, and §4A has NO JURISDICTION AT THE MOMENT IMMUTABILITY IS CREATED.**  
**Filed as TOR-1163.**

⚠️ **This is NOT the section further down also headed *"the biggest problem"* — do not merge them.**
That one is about the gate's **compliance signal** (a recorded line is anti-correlated with the quality
it measures, and route B fuses adversary and approver). This one is about its **jurisdiction**. Both
stand; they have different subjects and different fixes.

Every route, every gate, every carve-out in this section is keyed on **a PR merging into `develop`**.
The thing the whole section says it protects — *an immutable published version* — is not created by a
merge. It is created by `torque-admin artifact publish` / `POST /api/publishing/*`, run by an operator
against a live database. **That act has no diff, no head sha, no CI run, no route A and no route B.
§4A does not mention it.**

It is not hypothetical, and both named defects are downstream of it:

```
TOR-1138  (High)  a RED publish gate cannot block a publish. text_parity.py returned rc=1
                  naming the exact defect; build.sh's `set -euo pipefail` then DELETED parity.py;
                  republish.sh never reads the build's exit status and its grep whitelist matches
                  no failure vocabulary. Three wrong figures shipped into an IMMUTABLE page.
                  -> "a red gate was indistinguishable from a green one"
                  -> republish.sh lives OUTSIDE the repo (~/torque-page-review/): unversioned
                     machine state, so no commit and no PR review can reach it at all.

TOR-1059          a tracked README says "NOT PUBLISHED. No artifact publish, no serve_mode change,
                  no page_pointers write." Measured: fortect|historical|legacy|v2|html.
                  -> falsified by an act that produced NO COMMIT. §4A.1's scope rule cannot see it,
                     because there is no PR to scope.
```

🔑 **So §4A reviews the RECIPE and never the SERVING.** A merge is the point at which a change becomes
*available*; a publish is the point at which it becomes *irreversible*. This file spends all of its
precision on the first and none on the second, and the gap is where a wrong number actually becomes
permanent. **It cannot be closed by editing the class list — which is why it belongs here and not in
§4A.1 or §4A.2.**

⚠️ **And note where a publish sits in §3: `Anything that deletes data or history` and `Product and
data-provenance calls` are SHAHAR's. An immutable publish is arguably both and is named as neither.**
That is a gap in the three-way sort, not only in the Codex gate.

**Not ruled here** — it needs its own adjudication and probably Shahar, because the fix is a gate on an
operator action against a live environment rather than a rule for this seat. What this section records
is that **the question exists and §4A currently answers it by silence.** The two candidate shapes, so
whoever takes it does not start cold: (a) a publish-time route — the operator records a gate verdict
the way a lane records a round, three-state per `silver_doctor.py` (pass / fail / **could not run**),
never collapsing the third into a pass; (b) TOR-1138's own done-when — make the harness refuse, and
move the refusal somewhere a commit can hold it.

**Two smaller ones, recorded rather than ruled:**

- **No carve-out in this section has an expiry check.** `776e1d2` made the `assets/vendor/**` exemption
  *"contingent on `bundle_currency.test.ts` continuing to execute"* — and **nothing checks that it
  does.** Weaken that test and §4A becomes silently wrong, with no red anywhere. Same class as this
  repo's own *"red-by-design expires silently"* and *"a fix can drain its own control."* The principle
  in §4A now at least makes the dependency **explicit** for every future carve-out; it does not make
  it **checked**.
- **Class membership is eyeballed, not computed.** Nothing derives the class from a PR's file list,
  though `gh pr view N --json files` ∩ the globs is a few lines. Writing the cost measurements above I
  hit the **same zsh word-splitting dead probe twice**, each time returning a confident wrong number
  in the reassuring direction. **If it can silently mis-answer for me writing the rule, it can for an
  adjudicator applying it at 2am.** A committed script with a must-fire control would make the trigger
  mechanical, which is the one property a gate keyed on globs ought to have. **TOR-1160's third
  done-when asks for exactly this script, and §4A.4 gives it a second job — the byte-identity
  measurement is the same computation.** One tool answers both.

### ⚠️ AMENDMENT 2026-09-16 · §4A.4 — WHEN THE HEAD MOVES ONLY OUTSIDE THE MANDATORY CLASS (TOR-1160)

**The third defect, filed by PR #935's adjudicator. Route A requires the sidecar to read
`sha=<the head>`; the class is scoped by PATH. Those two clauses do not compose when the head moves
after the round but only in files outside the class. §4A did not say which reading governs, and
`#935` and `#939` were decided differently on the same structural situation in one night.**

**Verified first-party, 2026-09-16 (`git diff --name-only <sidecar sha> <head>`), not taken on the relay:**

```
#935  8ce6ad72 -> bf5fe56b   1 file: frontend/src/pagekit/authored_recompute_echo.test.ts
                             mandatory rows 0                                    MERGED
#939  580ba96b -> fbb28b85  21 files                                             HELD
                             mandatory rows 0 — but see below, that zero is MANUFACTURED
#941  (sidecar) -> ed306af6  1 file: api/services/tbr/forecast.py
                             mandatory rows 1 (TBR ∈ _REAL_PRODUCTS)              HELD, correct either way
```

🔴 **`#939`'s zero is produced ENTIRELY by the two carve-outs stacking, and that is the finding —
measured, not argued.** Its 21-file delta contains **5 `authored_pages/**` rows, every one a README**
(0 non-README page bytes) and **6 renderer rows** including `torque-charts.js`, `ChartView.tsx`,
`theme.ts`. The READMEs are excluded only by `cb118ec`; the renderer only by the page-kit carve-out.
**Narrow either and the delta is non-empty and the allowance correctly refuses.** So tonight's three
defects are not independent — **§4A.1 is a PRECONDITION for §4A.4 being safe**, not a separate item.

**RULING — reading (ii) governs, bounded. Route A is discharged by a sidecar naming an EARLIER sha iff
all three hold, and the ruling STATES the measurement:**

1. **Every path in the mandatory class is byte-identical** between the covered sha and the head —
   measured **blob-by-blob with a must-differ control**, counts stated. `#935`'s adjudicator did
   exactly this (15 SAME / 1 DIFFERS) and that is the model.
2. **The uncovered delta contains nothing EMBEDDED VERBATIM into a mandatory-class artifact.** This is
   the `#935` ÷ `#939` discriminator TOR-1160 says nothing currently decides. `scripts/build_page.py:190`
   —`_replace_block(html, BUNDLE_MARK, BUNDLE.read_text() …)` — inlines the page-kit bundle into a page
   that is **immutable once published**, so a renderer change is INSIDE this bound even though it is
   route B standing alone. **Not a contradiction of the page-kit carve-out:** a standalone renderer PR
   makes no claim about any page, whereas a round here CLAIMED to have read a page whose rendering has
   since moved. The round's claim is about the artifact *as it will be published*.
3. **The class is the one as amended by §4A.1 and §4A.2** — otherwise this allowance inherits exactly
   the two gaps ruled on above.

⚠️ **NO SIZE TERM, deliberately.** TOR-1160 warns that keying the allowance on diff size re-introduces
*"small"*, which §2 excludes from AUTO-APPROVE by name. The park-and-pile abuse it fears is answered by
clause 1 — **any** mandatory-class byte moving voids the allowance, however small — never by a count.

⚠️ **Reading (i) — *route A must name the head, full stop* — is REJECTED with a reason, not on
convenience.** §5 of this file already records that the approval pair has **no fixed point on a busy
develop**; at 381 PR merges in 30 days a re-merge is routine, so (i) costs a fresh round per re-merge
and produces the livelock §5 describes. §4A's own lesson applies: *a rule whose first act is to condemn
five correct rulings is a rule that gets deleted.*

**Both prior rulings stand under this: `#935`'s release was correct, and `#939`'s hold was correct** —
and now for a stated reason rather than by two seats' differing instincts.

### 🔴 TESTED, NOT ASSUMED — does §4A.4 SUBSUME §4A.1 and §4A.2? NO, AND ONE ANSWER IS INVERTED

The natural generalisation — *the rule keys on a sha when the property it wants is "did these bytes get
an adversarial read"; define the class by a property and the rest follows* — was put to this seat
explicitly, with an instruction to test rather than assume it. **It does not hold, and it fails in two
different ways:**

```
§4A.4 subsume §4A.1 (README)?   NO — AND A NAIVE BYTE RULE MAKES IT WORSE.
   TOR-1153's README never moved. Its claims were falsified by the PAGE moving around it.
   A byte-identity rule inspects the diff and would positively CERTIFY that unchanged README
   as covered. No selector over a diff can see a file that is not in the diff.
   The fix for §4A.1 is SCOPE — what the round is pointed at — which is a different axis entirely.

§4A.4 subsume §4A.2 (projector)?  ONLY IN A FORM NOBODY FILED.
   As filed, TOR-1160 is about a MOVING HEAD; it says nothing about which paths are in the class.
   Generalised to TOR-1123's option 2 — "a change is in the class if it touches a WRITER of an
   immutable artifact" — it would subsume §4A.2 and the renderer half of §4A.4's own clause 2.
   That is a real and better design. It is ALSO a structural redesign of the selector, it is
   already filed, and it is not needed to close tonight's three.
```

🔑 **The durable half: a property-defined class would subsume the two defects that are about WHICH
BYTES, and neither form touches the one that is about WHICH QUESTION.** §4A.1 is not a selector
problem wearing a disguise.

⚖️ **WHAT IS NOT RULED HERE, AND WHY — TOR-1123 / TOR-1160 are marked *Shahar's call*.**

Applying the standing test — *amending a review rule is this seat's; changing what the fleet owes a
real client's immutable page is his*:

```
MINE, and ruled above    which reading governs a moved head · the bound that stops it being gamed
                         the #935 ÷ #939 discriminator (it only ever TIGHTENS — it adds no permission
                         that did not already follow from the gate's stated function)
                         the class's principle · the README scope · the projector

SHAHAR'S, left UNRULED   replacing the PATH-GLOB selector with a PROPERTY-DEFINED one
                         (TOR-1123 option 2). It is a redesign of his 2026-09-15 amendment, it has
                         a real cost this seat has not measured — a lane must be able to evaluate
                         the class BEFORE starting work, and a property is harder to apply at a
                         glance than a glob — and tonight's three defects close without it.
                         ⚠️ Recorded rather than decided to be tidy.
```

### ⚠️ AMENDMENT 2026-09-17 · §4A.5 — A CONDITIONAL APPROVAL MAY NOT PRE-DECLARE §4A.4's OUTCOME

**The incident, per this file's own rule. PR #970's ruling of 2026-09-17 15:20Z approved conditionally
on a re-merge and offered remedy (a) with the words:** *"A README is outside §4A's trigger, so **r10
still carries under §4A.4** and no fresh round is owed."* **Two paragraphs earlier the same ruling had
found the re-merge was NOT mechanical and that it therefore *"may not pre-authorise a future head."*
Those two sentences cannot both be safe.** Measured after the lane re-merged (`bb85f408..bba92fb0`,
50 rows): **2 mandatory-class rows** (`api/services/smp/{data,loan_simulator}.py`, SMP ∈
`_REAL_PRODUCTS`) and **9 `authored_pages/**` non-README rows** arrived FROM DEVELOP — another lane's
merged work. The allowance was voided and a fresh round was owed. The lane measured this itself,
ran round 11 against its own ruling's estimate, and r11 returned a real finding.

**RULING — clause 1 is measured over the WHOLE `covered-sha..head` delta, INCLUDING bytes that arrived
via a merge.** Three reasons, and the section decides itself:

1. **§4A.4's own HEADING is `WHEN THE HEAD MOVES ONLY OUTSIDE THE MANDATORY CLASS`.** A re-merge that
   pulls mandatory-class bytes in is, by the title, not the case it governs.
2. **Clause 1's subject is the PATH SET, not the PR's authored diff** — *"Every path in the mandatory
   class is byte-identical between the covered sha and the head"* — and §4A.4's own worked measurement
   is `git diff --name-only <sidecar sha> <head>`, which a merge commit populates.
3. **"NO SIZE TERM, deliberately… any mandatory-class byte moving voids the allowance, however small."**
   There is no authored-vs-arrived carve-out, and inventing one is the size term by another name.

**And the FUNCTION settles it**: clause 2 already says the round's claim *"is about the artifact as it
will be published."* A merge changes that artifact. PR #970 is its own proof — develop's generator
change moved two reader-visible lines at `merge-tree` **rc=0** with every test green. Each side's round
read bytes that were fine; **nobody had read the combination.**

🔑 **So a conditional approval may STATE the §4A.4 test and may NOT pre-declare its OUTCOME.** The
correct form:

> *"the standing round carries **iff** `git diff --name-only <covered-sha>..<new head>` contains zero
> mandatory-class rows — measure it and state the count; otherwise a fresh route-A round is owed."*

This is §5's pre-authorisation rule applied to the Codex gate, and it inherits §5's hole verbatim: **git
reports no conflict for a semantic one.** ⚠️ **Note the cost is asymmetric and it is why this is not
softened**: pre-declaring "it carries" is the reassuring direction, it is the direction a lane will not
push back on, and it retires the gate silently. A lane that measures and finds zero has lost nothing.

⚠️ **This constrains the RULING's wording, not the allowance.** §4A.4 is unchanged; both of its prior
rulings (`#935` release, `#939` hold) still stand.

### ⚠️ CORRECTION 2026-09-18 · §4A.6 — `api/services/publishing/**` MATCHED ZERO PATHS. A DEAD SELECTOR, NOT A WIDENING

**Found by the `record-rulings-0918` lane when its §4A matcher's MUST-HIT CONTROL FAILED** — not by
anyone reading line 134. That is the instrument discipline working, and it is the only reason this
surfaced at all.

**Measured first-party at `origin/develop` = `dd45836e`, with two-direction controls
(neg `api/services/definitely_not_a_real_dir/**` → 0; pos `api/services/**` → 164):**

```
api/services/publishing/**    ->    0 paths   DEAD ENTRY
api/services/vault/**         ->    5         api/services/silver/**       -> 5
api/services/computation/**   ->    7         api/services/projector/**    -> 10
api/auth/**  -> 8   ·  db/schema.py -> 1  ·  engine/** -> 24  ·  models/** -> 28  ·  risk/** -> 4
```

`publishing` is the ONLY module in the brace group; the other three are packages. `api/services/publishing.py`
is a 677-line module and **`api/services/publishing/` has never existed** — verified across all reachable
commits, no rename in its 15-commit history.

🔴 **Why this entry, of all of them, is the worst to have void:** `api/services/publishing.py` is the
**sole writer in all production code** of `page_pointers`, `page_versions` and `publish_log` — 9 write
statements, and nothing else under `api/` writes those tables at all. It defines `set_serve_mode`
(the live/off-air flip), `publish_page`, `next_version`, `cas_predicate`, `_lock_pointer` and the four
publish exceptions. Everything else reaches the immutable record *through* it.

**THIS IS A CORRECTION, NOT AN AMENDMENT, and the distinction is load-bearing.** Two things in this
file already read the entry the way the correction now writes it:

1. **The principle block above** states that naming clause 2 makes membership **derivable instead of
   enumerated**. Clause 1 is satisfied by the sole-writer fact.
2. **§4A.2's own applied usage** — *"`projector` is in neither `_REAL_PRODUCTS` nor
   `{publishing,vault,silver,computation}`"* — drops the prefix and the `/**` and reads the brace group
   as a bare NAME set, under which `publishing` was always a member.

🔑 **So the defect's subject was the MECHANICAL path, never the reading path.** A human at line 134
routes A; a matcher does not. `db/schema.py` was already a bare-file entry in the same list, so naming
a file is a format this class supports — the `/**` was an error, not a limitation.

**IT HAS NOT BITTEN, and it structurally could not have.** 11 merged PRs have touched
`api/services/publishing.py`; the last is `1e967b32` (2026-08-24), and the earliest PR body citing this
file at all is `#788` (2026-08-28). **No route-era PR has ever had `publishing.py` in its delta**, and
zero of the 11 declare either route. **No retrospective review is owed** — re-reviewing them applies a
rule that did not exist, and this section's own lesson is that *a rule whose first act is to condemn
correct rulings is a rule that gets deleted.*

**Cost, MEASURED with a must-fire control** (`db/schema.py`, a known member, → 42; a dead probe would
have returned 0): over 918 merge commits on `origin/develop` in 30 days,
**`api/services/publishing.py` is touched by 9** — ~1%, **smaller than every existing member** and far
below the projector's 33. The merge-treadmill objection does not reach a correction this size.

⚠️ **THE CLASS IS NOT WIDENED BY THIS, deliberately.** Measured while ruling, and **recorded rather than
ruled** — each is a class *expansion* and belongs to Shahar or its own ruling, per §4A.2's handling of
TOR-1123's option 2. **All three are the same mechanism as this correction and as TOR-1123: a publish
boundary matching no glob.**

```
api/routers/publishing.py    NOT IN ANY ENTRY, and `api/routers/**` appears nowhere in this file
                             except as the citation for _REAL_PRODUCTS. It owns ALL FIVE publish
                             endpoints — POST /publish · /revert · /restore · /artifact · /serve-mode
                             (:359) — and is the SOLE CALLER of set_serve_mode (:369). The known
                             hard-coded `"kind": "human"` actor defect is at :131, i.e. INSIDE the
                             file route A never mandates.        7 / 918 merge commits
                             ⚠️ §4A.3 says §4A has no jurisdiction where immutability is CREATED
                             because that act "has no diff". The CODE serving POST /api/publishing/*
                             does have a diff — §4A.3 did not notice it is also unclassed.

api/services/manifest_controls.py   TOR-1123's OWN first named instance, still uncovered 4 days on.
                             `assert_publishable_generically` — the generic publish writer.  6 / 918

api/services/control_plane/**       TOR-1123's OWN second named instance (`pages.py`:
                             publish_manifest · validate_manifest · serve_mode_of ·
                             refuse_unapplied_serve_mode), plus pins.py and silver.py.
                             ⚠️ 44 / 918 — this would be the LARGEST single addition the class has
                             ever had, bigger than the projector's 33. Do not bundle it in on alarm;
                             it needs its own cost ruling.
```

⚠️ **Clause 2 of the principle argues AGAINST route A for `publishing.py`, and that is stated because it
is the unflattering direction.** 19 test files exercise `api.services.publishing` against live Postgres
under the bare `pytest -n 8 -q` at `ci.yml:105` — `set_serve_mode` in 9 files, `cas_predicate` /
`PublishConflict` / `VersionOutOfSequence` in 5. **That is materially stronger than either prior
amendment's clause-2 case**, where §4A.2 measured the semantic gate running in *zero* workflows. So this
entry is corrected for **mechanical soundness and consistency with how the file already reads itself** —
NOT on a claim that a wrong number is about to reach a client through it. Whether clause 2 is *satisfied*
here (do those tests discriminate the failure class route A catches?) is a mutation question this ruling
did not measure and does not assert.

🔴 **THE REMEDY THIS SECTION CANNOT BE: the structural half is owed and is NOT a prose fix.** A class
expressed as globs over a tree that mixes modules and packages will drift again the moment a package is
split or a module promoted — **17 top-level modules under `api/services/` and 4 class packages are each
a future instance of this.** What is owed is a committed **must-hit assertion that every §4A class entry
resolves to ≥1 tracked path**, with a two-direction control. It was written and run to produce the table
above; it fires on exactly this entry and passes the other ten. **§4A.3's second "smaller one" already
asked for this** (*"Class membership is eyeballed, not computed"*) and **TOR-1160's third done-when asks
for the same script** — one tool answers all three. Until it exists, this correction is checked by
nobody, ever again, which is the property this file distrusts everywhere else.

⚠️ **The identical defective string is duplicated at `LANE-PREAMBLE.md:566`** and is corrected there in
the same act. A rule held in two transcribed copies has two places to rot.

### ⚠️ AMENDMENT 2026-09-19 · §4A.7 — ROUTE A MUST CHECK THE **PROMPT**, AND THE VERDICT IS THREE-STATE

**The incident, per this file's own rule. Route A is stated as two conditions — the `.md` exists and
its sidecar reads `sha=<the head>` and `tree=clean`. Neither touches the PROMPT, and the producer's
own comment says why that is a hole:** *"for a PLAN round the repo sha is nearly meaningless and the
prompt hash is the whole claim. Cite them, or the citation is about a revision nobody has."* **A
round whose prompt cannot be read has recorded a verdict about a question nobody can see, and route A
passes it today on the strength of a sha.**

**Measured first-party 2026-09-19, sweeping every `.provenance` on this machine — 498 sidecars, with
both controls stated (MUST-HIT: a resolving `prompt=` exists; MUST-MISS: a synthetic absent path
reports unresolved):**

```
prompt= no longer resolves                242 / 498   48.6%
   of those, claiming prompt_durable=yes    55        <- the claim a checker would have believed
   of those 55, the bytes ARE beside the sidecar      52   and all 52 hash to prompt_sha256
   of those 55, the bytes are really gone              3
prompt= resolves, bytes DISAGREE with prompt_sha256    3   <- the worst shape in the corpus
predate the durable-copy mechanism entirely          187   <- permanently uncheckable
```

🔑 **THE FINDING THAT CHANGES THE FIX: the retention was never broken. The CITATION FORM was.**
`codex_review.sh` has copied each prompt next to its artifact since 2026-08-07 and records
`prompt=` as an **absolute path to a file that is always a sibling.** Absolute-plus-sibling is a
citation that breaks on exactly the act preserving evidence requires — lifting the set out of a
worktree about to be removed. 52 of the 55 "durable" dangling citations are bytes that never went
anywhere, mis-addressed. **A clause that read `prompt_durable=yes` and stopped would have been
reassured by the field in every one of those cases**, which is the shape this file distrusts.

🔴 **AND A TWO-STATE CLAUSE WOULD HAVE PASSED THE THREE WORST ARTIFACTS IN THE CORPUS.** A drafted
version of this clause enumerated only PASS and REFUSE, keyed on whether the path resolves.
`tor428-plan-r1/r2/r3` (2026-08-06) each cite the **same** plan file at a **different** recorded
hash; the file resolves today and holds a **fourth** set of bytes matching none of them. Three rounds
whose verdicts are about three revisions nobody has — and a resolve-check calls all three PASS.
**Resolution is not the predicate. The HASH is.**

**RULING — route A additionally requires a prompt verdict, and it has three states:**

```
VERIFIED     (0)  a citation resolved and its bytes hash to prompt_sha256
BROKEN       (1)  a citation resolved and its bytes DIFFER from prompt_sha256
CANNOT-TELL  (2)  nothing resolved, or there was nothing to check against
```

1. **VERIFIED discharges the prompt half of route A. BROKEN does not, and neither does CANNOT-TELL.**
2. **A dangling citation is CANNOT-TELL, never BROKEN and never VERIFIED.** As VERIFIED it certifies a
   round nobody examined; as BROKEN it accuses one nobody examined. This is `verify_artifact.sh`'s
   rule for its own third state, applied to the same sidecar.
3. **CANNOT-TELL is not a refusal of the PR.** 187 sidecars predate the mechanism and are in this
   class permanently — that is a fact about the evidence, not a defect in the round. It obliges the
   ruling to **say so in the line §4A already makes mandatory**, so an unreadable prompt is a stated
   gap rather than a silent pass. A lane may close it by re-running the round.
4. **Resolution order is `prompt_relative` → the basename of `prompt=` beside the sidecar → the
   recorded absolute path.** A bare-name citation the sidecar's own directory vouches for beats an
   absolute path into a home directory that may today hold a **different file of the same name**.

⚠️ **THE NAME. The adjudicator who ruled this called the third state `COULD NOT RUN`, after
`silver_doctor.py` as §4A.3 cites it. It is renamed `CANNOT-TELL` here and the reason is this file's
own §4A.6 lesson — a rule held in two transcribed copies has two places to rot.** The checker for
this clause is the sibling of `verify_artifact.sh`, in the same directory, reading the same sidecar,
and that script has named its third state `CANNOT-TELL` at exit 2 since it was written. Three names
for one state across one directory is how a matcher ends up testing for a word nothing emits.
`ccdoccheck`'s *"exit 2 could not check <- NOT a pass"* and this section's own *"exit-2 UNKNOWN,
never a fail and never a pass"* are the same state under two more names; **the exit CODE is the
durable part and it is 2 in all of them.**

**BOTH HALVES SHIP TOGETHER, because the clause alone is not a working gate.** A three-state rule on
top of the old producer converts a silent pass into a loud CANNOT-TELL on half the corpus — honest,
and useless. The producer change is the load-bearing half:

- `prompt_relative=<basename>` is emitted, and a checker resolves **that** first.
- **`prompt_durable=yes` is now EARNED, not asserted.** It used to mean *"`cp` exited 0"* — a claim
  about a command, not about bytes a later reader will find. The copy is now re-hashed against
  `prompt_sha256` at generation, and a copy that does not match records `no`. The sidecar comment
  already argued the copy is identical *"BY CONSTRUCTION"*; re-hashing is what makes that argument
  checkable by the one process that can still see both files.
- `prompt_sha256` gets the guard `artifact_sha256` already had. Written bare under `set -euo
  pipefail` the old form **aborted the round** when the hasher failed, so the `unknown` sentinel the
  script believes it has was unreachable. Both are now exercised.

**The checker is `skills/codex-review/scripts/verify_prompt.sh`, with `--self-test` and `--dir`.**
🔑 **It is committed rather than described, and that is deliberate** — §4A.3's second "smaller one"
(*"class membership is eyeballed, not computed"*) and §4A.6's *"until it exists, this correction is
checked by nobody, ever again"* both ask for exactly this property, and a prose clause about hashes
would have neither.

**Cost, MEASURED rather than asserted — the shipped checker over all 498 sidecars, single-file and
`--dir` modes agreeing, and independently reproduced by a second implementation:**

```
VERIFIED     305      BROKEN  3      CANNOT-TELL  190        sum 498, nothing left the denominator
```

**So the gate is green on 61% of the corpus on day one, and the 190 are 187 pre-mechanism rounds
plus 3 genuinely lost.**

🔴 **DO NOT CITE THOSE DIGITS BACK — RE-RUN THEM, AND THE REASON IS MEASURED.** Two sweeps twenty
minutes apart returned `305/3/190` and `309/3/186` **over an identical 498-file population, with no
new round run.** Four prompt files appeared and vanished again: a lane on this machine created and
removed a worktree between the reads. **This corpus is a MOVING PANEL, not a fixed one** — a sidecar
citing a live worktree VERIFIES while that worktree exists and is CANNOT-TELL the moment it is
removed, which is TOR-255 showing up inside the measurement of it. Both readings were true of their
instant; the figures above are the single-instant reading where two independent implementations were
run against the same filesystem state and agreed on all 498. ⚠️ **What does NOT move is the shape:**
242 dangling, 55 of them claiming durable, 52 of those recoverable beside their sidecar, 3 BROKEN —
stable across every sweep.

⚠️ **A third instrument — an ad-hoc shell aggregator written to summarise this — was the one that
first showed the drift, and it is recorded because the discipline is the only reason any of it was
caught:** when two implementations agree and a summariser does not, the summariser is the suspect,
and when the same implementation disagrees with ITSELF the subject is moving. Neither would have
been visible from a single run of a single tool, which is what a cost line normally is.

⚠️ **NOT CLAIMED.** This does not reach TOR-255's location problem — a prompt that VERIFIES in a
worktree still dies with it. It does not reach §4A.3: a publish still has no prompt, no sha and no
route. And it says nothing about whether a prompt asked the *right* question; it compares bytes, and
bytes cannot tell a legitimate revision from a substitution — the three BROKEN instances are almost
certainly honest edits between rounds.

**Falsifier, so this is held to the same standard as §4A.1 and §4A.2:** if over the next two weeks no
route-A round returns BROKEN or CANNOT-TELL on a prompt a lane actually needed, the prompt half is
ceremony and should be folded back into `verify_artifact.sh` as one more CANNOT-TELL cause. Record it
with the PR number.

### ⚠️ ROUTE A HAS A LOCATION PROBLEM — the LANE must cite the path, not the adjudicator hunt for it

**Open, and it is a live hazard for this mandate: TOR-255** (*"Codex round artifacts land in two
different places — half of tonight's gate evidence dies with its session"*, Backlog since
2026-08-04) and **TOR-322** (*"the Codex review round is a mandatory merge gate that does not exist
in this repository"*, Backlog since 2026-08-05).

Measured writing this ruling: TOR-927's seven artifacts are **not** in the main checkout's
`.codex-review/` (1,004 entries, zero of them TOR-927). They are in the lane's own worktree, and I
found them only by sweeping every `.codex-review/` directory on the machine. **A gate whose evidence
must be located by a filesystem sweep is a gate the next adjudicator will skip on a busy night** —
and worktrees are removed, which is how the evidence dies.

```
LANE      cite the artifact in the PR BODY: the full path, the .provenance sha=, and tree=
ADJUDICATOR  read the sidecar at that path. If it is not cited, ASK — do not sweep, and do not
             infer absence from a failed search. An artifact you could not find is exit-2
             UNKNOWN, never a fail and never a pass.
```

PR #770 did this correctly and is the model: its body names both round labels with `sha=` and
prompt hashes, which is why its gate was checkable in seconds.

### ⚖️ THE RECORD IS MANDATORY ON BOTH ROUTES. A ruling that does not mention the gate has FAILED it.

One line in the ruling. Route A: name the provenance sha. Route B: name the hypothesis you
originated and what it returned. **This is checkable by the next reader and by `census.sh`; "I did
think about it" is not.** A seat that performed a flawless adversarial pass and wrote no line has
failed this gate, and it is not a technicality — see the retrospective below, where exactly that
happened on the highest-blast-radius change of the night.

### The crux: "the evidence is re-runnable by a reader" is NOT a valid waiver, and the reason is not that it is too permissive

It was argued four times on 2026-08-28 and self-falsified by the seat that used it last. The
objection normally raised — *that argument waives every PR* — is true but is the weaker half.

**The decisive point is that re-runnability is ORTHOGONAL to what the round catches.**

```
RE-RUNNING THE EVIDENCE ANSWERS      does the claimed check pass?
IT CANNOT ANSWER                     is the check the RIGHT check?
                                     does it discriminate?
                                     did the fix drain its own control?
                                     is the guard reachable at all?
```

This repo's dominant recorded defect class lives entirely in the second column — *"a guard whose two
sides move together is not a guard"*, *"a control that comes back GREEN is a finding"*, *"validated
component never wired"*, *"a fix can drain its own control"*. **A guard that cannot fail passes
re-running with flying colours; that IS the failure mode.** So the carve-out selects on the
checkability of the CLAIM when the risk lives in the soundness of the CHECK.

**Measured, on PR #784.** The lane's four committed mutations were re-run first-party and all four
reproduced exactly — a clean green. The adjudicator then originated a fifth:

```
M5  delete the `axis_tick_membership.sweep(...)` call from scripts/baseline/diff.py
    -> the key is still written (empty list), has_violation([]) is False, the run passes
    -> tests/baseline + tests/structure:  3219 passed, 13 skipped, 1 xfailed
    NOTHING GOES RED. The comparator was dead code behind a string grep.
```

**Re-running the evidence returned green and told you nothing.** The defect required a hypothesis
the lane did not have. That is the whole argument, and it is why route B is defined by *originating
a hypothesis* rather than by *re-measuring diligently*.

### ⚠️ THE 2026-08-18 SCOPING IN `LANE-PREAMBLE.md` §6 IS SUPERSEDED FOR THIS SEAT

That scoping keyed the gate on *"the artifact's core evidence CANNOT BE EXECUTED BY A READER"*. It is
the same wrong axis, and it lived in the LANE's document — where an adjudicator does not read it.
Measured: PR #782's seat was cited that clause by its lane and answered *"which is not an artifact I
can read, so I am not accepting it as licence."* **That seat was right.** §8's escalation trigger
fired here — two documents disagreed and one was stale; this section is the reconciliation, and
`LANE-PREAMBLE.md` §6 now points at it. Do not let a third statement of this rule accumulate.

### The retrospective — what actually happened, measured first-party, and the received account is wrong in two places

Every cell below was read from the artifact (`gh pr view`, and a filesystem sweep for
`.codex-review/*` across every worktree on the machine), not from any seat's report.

| PR | change class | Codex gate — MEASURED |
| -- | -- | -- |
| #770 | `models/vyb_loan_model.py`, `api/services/vyb/`, `db/pg.py` | ✅ **PASSED — route A.** 7 rounds present with provenance; `…-r7.provenance` reads `sha=29f0d3ef…`, `tree=clean`, exactly the head ruled on. Findings converged `3·5·4·4·3·1·0`. |
| #776 | `scripts/baseline/**`, tests, docs | ✅ route B, **recorded** (*"UNRUN … reported as exit-2, not as a pass"*) |
| #780 | `scripts/baseline/**`, `scripts/`, tests, docs | ✅ route B, **recorded twice** |
| #782 | `scripts/baseline/supersession.py`, tests | ✅ route B, **recorded**; refused the lane's citation as licence |
| #784 | `scripts/baseline/**`, `scripts/`, tests, plans | ✅ route B, **recorded at length**; 2 blocking findings from the substituted pass |
| #785 | 🔴 **`engine/torque_engine/vyb_loan_model.py`, `models/vyb_loan_model.py`** | ❌ **NOT MENTIONED ANYWHERE.** No pass, no waiver, no record, in body or any comment. |

**Two corrections to the account this ruling was commissioned on, and both matter:**

1. **It was not five waivers. It was one PASS, four RECORDED waivers, and one SILENT skip.** #770
   satisfied the gate outright — the positive control for the sweep that found nothing for the other
   five is that the same command returned 35 files for TOR-927 and zero for TOR-933/934/939/940, so
   those zeros are real and not a dead probe.

2. **The seats did not skip the WORK — every one of them performed the adversarial pass.** #785's
   seat produced the strongest pass of the night: it executed `n_tranches=1` and found a
   **−$4,447.38 dip** — a descending displayed cumulative curve, the one thing `CLAUDE.md` forbids
   outright — sitting behind a slider minimum in another file that no test reads; it ran its own
   336-cell sweep; it caught an over-claimed `# Source:` denominator, a corrupted measurement table
   and a present-tense docstring the PR had refuted. **What decayed was the RECORD, not the rigour.**

🔑 **And the decay was DIRECTIONAL: the record vanished on the last PR of the night and on the
highest-blast-radius change of the night** — a shared-`engine/` underwriting-wheel edit to a real
client's DECISION slot, four hours after another merge moved the same KPIs, adjudicated with Linear
unreachable so the ticket was never read. #770 and #785 touch **the same file**. One got seven
rounds; the other got none and no record. **That is why route A is mandatory for that class and why
the record is mandatory everywhere: a norm sustained only by each seat's diligence decayed inside a
single night, and it decayed on the artifact that could least afford it.**

### The six already merged: PROSPECTIVE, with ONE recorded exception

**Nothing is reverted and nothing is re-adjudicated.** #770 passed. #776, #780, #782 and #784 each
discharged the function by route B and recorded it — under this ruling they are **compliant, not
excused**, and that is deliberate: a rule whose first act is to condemn five correct rulings is a
rule that gets deleted (§5's own lesson — *the gate's wrongness lands on the careful participant*).

**#785 carries a recorded exception and one owed action: run a Codex round against
`06adfed9` now, route A, and triage its findings as tickets.** Not a revert — the change is
believed correct and the direction is conservative (`sum(max(0,d)) >= sum(d)`, so it can only lower
recoup). It is owed because it is in the mandatory class, because the ~5 minutes are cheap against a
real client's facility maths, and because its own ruling left **five follow-ups that exist nowhere
but a PR comment** (Linear was down): the `n_tranches` cross-file precondition, the over-claimed
sweep scope, the engine wheel version discipline, and two prose defects. **Those must be filed.**

### 🔴 The biggest problem with this rule, which nobody named — stated here rather than discovered later

**The compliance signal is ANTI-CORRELATED with the quality it is trying to measure, in the only
sample that exists.**

The seat that did the best adversarial pass of the night wrote no record. A seat that did *no*
adversarial pass would find `☑ route B — adversarial pass performed` the single easiest line in a
ruling to type. **This gate therefore selects for the behaviour of writing a line, and the one
observed failure was a false negative on an excellent seat while the failure mode it exists to stop
— a seat that looked and saw nothing because it wanted to finish — would sail through.** §9 already
says this file *"catches only carelessness"*; this section is in that class and must not be read as
a control.

**Partial mitigation, and it is partial:** route B's recorded thing is CONTENT, not a checkbox — a
named hypothesis with its outcome. A hypothesis is falsifiable by the next reader; a checkbox is
not. That is the difference between *"M5: delete `sweep()` → 3,219 pass"* and *"I reviewed it
adversarially."* A seat can still name a trivial hypothesis, and nothing here stops it.

**The second problem, which is structural and which the mitigation does NOT touch:** route B fuses
the adversary and the approver into one seat. That is the exact conflict `/adjudicate` exists to
prevent one level up — *"a grader who is also the assigner has no independent check on its own
feedback"* — rebuilt one layer down. And the incentives are asymmetric: on a busy `develop` with **no
fixed point for the approval pair** (§5), a finding costs the adjudicator a round-trip, a re-merge
and an expiring approval, while finding nothing costs it nothing. **Route A is the only route whose
adversary has no merge authority and no stake in the outcome.** That is the whole reason it stays
mandatory where being wrong is most expensive, and it is the reason this ruling does not simply
bless route B everywhere and call the gate satisfied.

**Falsifier, so this ruling can be overturned by evidence rather than by preference:** if over the
next two weeks route-A rounds in the mandatory class return only restatements while route-B passes
keep producing the blocking findings, the class is too wide — narrow it. If a route-B ruling in the
non-mandatory class ships a defect that a round would have caught, it is too narrow — widen it.
**Record which, with the PR number.**

## 5 · The rule that makes DONE mechanically checkable

**Files touched outside the declared list ⇒ the PLAN failed, not the diff.**

Do not patch the diff. Send it back to planning and say the file list was wrong. If a lane cannot say up
front which files it will touch, the plan was not specific enough to implement, and no amount of
reviewing the output will recover that.

⚠️ **AN AMENDED LIST IS A KEPT LIST, NOT A BROKEN ONE.** A lane that stopped, said *"I need X too,
because Y turned out to be Z"*, and updated its list has done exactly what `/worker` §4 requires.
**Check the diff against its FINAL list and do not bounce it** — bouncing an announced amendment
teaches lanes to over-declare up front, and a list that covers everything predicts nothing.

**What fails this gate is the SILENT widening.** The distinction is whether you were told, not whether
the list changed. A list amended three times is a signal worth reading — the change was less understood
than anyone thought going in — and that signal only exists if amending is safe.

This is the one criterion here that cannot be satisfied by a persuasive lane, because it is checked
against a list written before the work started. **Do not check it by reading — run it:**

```bash
ccverify files --plan <plan.md>          # or: pbpaste | ccverify files --plan -
ccverify pr <N>                          # "it landed" -> gh. exit 1 means it did not
```

`exit 1` is the gate; **`exit 2` means it could not check and is NOT a pass.** It prints the file list
it parsed — read that, because a wrong parse fails the same way a clean diff passes.

⚠️ **A plan with no `FILES:` / `NOT TOUCHING:` block is exit 2, and that is the correct outcome.**
Only those blocks declare; a path the plan mentions in prose is not declared. Until 2026-08-24 the
parser read the whole document, which failed PERMISSIVE — this gate's product is the UNDECLARED list,
so an over-broad DECLARED set shrinks it by construction. Measured on a real 661-line plan:
`declared 131`, including a slash command, a git range, `$52.80` from a rounding example and five CSS
class names. **Every plan written before that date lands on exit 2. Send it back for a file list; do
not read the old PASS as evidence** — it was read off prose.

⚠️ **Point `--repo` at the lane's WORKTREE, at the head under review.** Run bare in the main checkout,
`origin/develop...HEAD` is empty and the tool reports that checkout's untracked scratch as the PR's
diff. It now refuses this with exit 2 rather than ruling — but the habit of pointing it correctly is
what you actually need.

### `NOT TOUCHING:` is checked in the OPPOSITE direction

A plan declares two lists. **Touching a prohibited file is the harder failure**, because the lane named
it out of bounds itself and the usual reason is that another lane holds it.

⚠️ **Measured 2026-08-12: the parser read backticked prohibitions as DECLARATIONS**, so a lane obeying
its ticket's stay-out-of clause was counted as having failed to touch those files. Three of four lanes'
plans would have been marked failing **for doing exactly what they were told.** Caught only because an
adjudicator got `THE PLAN FAILED` on a compliant PR and read what the tool had parsed instead of acting
on the verdict. Fixed — **and the lesson outlives the bug: the gate's wrongness lands on the careful
participant and looks like the gate working.**

### 🔴 THE APPROVAL PAIR HAS NO FIXED POINT ON A BUSY DEVELOP. READ THIS BEFORE YOU LIVELOCK.

*"Approval is a pair — a diff and a base — and it expires when either moves"* assumes **CI is fast
relative to the merge rate.** Measured 2026-08-12, twice in a row on one PR:

```
#526 behind 5  ->  lane re-merges, pushes, behind 0
                   backend CI takes 12m7s
                   develop moves (another PR merges)  ->  behind 5 again
```

Backend CI is ~12 minutes and three lanes were merging. **Under those numbers the pair can never be
current at the moment of approval, and the process as written has no fixed point.** There is no
merge-window reservation anywhere in the architecture — nothing lets an approved head hold its place
while CI runs, and "the dispatcher owns timing" is a convention between sessions, not a mechanism.

**What worked, invented mid-ruling and written here so the next seat does not re-derive it:**

```
1  ask whether the required re-merge is MECHANICAL — does develop's advance intersect
   this PR's subsystem at all?
2  if it does not, PRE-AUTHORISE the next head, conditional on green CI
3  say both halves out loud in the approval, so the lane can refuse if either fails
```

⚠️ **And name its hole yourself, because it is real: git reports no conflict for a SEMANTIC one.** The
same evening, a PR merged with **zero file overlap** and falsified a factual claim inside another PR's
docstring — *"ChartView never draws it"*, measured 0, then present. **No gate sees that class.** Not CI,
not the file list, not the diff. It was findable only by reading what develop had gained and
recognising the subject. **If you pre-authorise, you are the only thing standing in front of it.**

## 6 · Judgment criteria, for the ADJUDICATE bucket

Applied to the plan, not to the code. **A bad line of a plan becomes hundreds of bad lines of code**, and
a plan is an order of magnitude cheaper to read than the diff it produces.

**Reject a plan that:**
- changes a schema, a public contract, or a cross-lane interface without naming who else is affected
- has no way to tell whether it worked other than the agent saying so
- widens its own scope relative to the ticket
- deletes or weakens a test in order to pass
- depends on an artifact nobody has read — a harness, a script, a measurement that "was run"

**Approve a plan that:** names its files, names its non-goals, states how it will be verified by
something other than its own report, and would fail visibly if it were wrong.

**Blind yourself to authorship where you can.** It is the easiest bias to remove and the hardest to
notice. A cross-model comparison in which the adjudicator did not know whose plan it was picked the
better plan against its own house model.

## 7 · Bounding the review itself

**One adjudication pass for code. Iterate only on plans.**

Two independent reports exist of iterated review→fix→review loops on code producing worse output, not
better. The person who advocated adversarial review scoped his own claim afterwards: a linear one-shot
process, and mainly for artifacts that are not code.

**Codex rounds: two, then a named question.** Measured 2026-08-06: 130 round artifacts in one night, with
four tickets accounting for 38 of them. **The stop signal is the KIND of finding, not the count** — when
a round starts returning restatements rather than defects, it is done.

## 8 · Escalation triggers that are not about approval

Route these to Shahar even when no approval is pending:

```
A lane has failed the same thing 3+ times          each round adds damage; the answer is a
                                                    stronger model re-planning, not another nudge
Two lanes declared the same file                    a collision, and it is cheaper before the merge
A ruling would contradict a previous ruling         say so out loud; one of them is stale
Spend on one ticket exceeds its expected value      the only cost gate that exists right now
```

## 9 · What this file does not cover

**It does not make a lane honest.** DONE-WHEN, the file list, and CI are the only three things here that
a lane cannot talk its way past. Everything else assumes good faith and catches only carelessness.

**It does not fix the reviewer.** A code-reviewer that quietly degrades will keep passing these criteria.
Nobody in the field has solved that; the only proposed test is to run the same adjudication ten times and
expect it to agree with itself eight.

---

## §4B · `reviewDecision` CANNOT tell you whether a PR was adjudicated — 2026-08-28

**Measured by the PR #759 adjudicator.** `gh pr review --request-changes` is **refused for every PR in
this fleet**: there is one shared GitHub actor, so GitHub answers *"cannot request changes on your own
pull request"*. Every ruling is therefore posted as a **comment**, and `reviewDecision` stays **empty
whether or not the PR was ruled on**.

```
reviewDecision: ""   ==  never adjudicated
reviewDecision: ""   ==  adjudicated, CHANGES-REQUESTED, ruling posted   <- indistinguishable
```

🔑 **So the check for a standing ruling is READING THE COMMENTS. There is no field.** The dispatcher
spawned #759's adjudicator citing an empty `reviewDecision` as one of two reasons for "no standing
ruling". The other reason — all four comments were the PR's own lane's — was sound and is what actually
established it. **The conclusion was right and one of its two stated reasons could never have supported
it**, which is the fleet's *conclusions outrun reasons* pattern: a confident wrong reason prevents
verification, and a lane deriving from it reaches somewhere the conclusion never went.

⚠️ This is the same shape as `probe-with-a-default-cannot-report-absent`: an instrument whose two
outcomes produce identical bytes cannot answer an existence question, whatever it happens to return.

**And the cost of the absence is real, not cosmetic:** a ruling that leaves no machine-readable trace
means a future reader cannot infer from the PR's metadata that it was adjudicated at all. Say so in the
ruling comment itself.

---

## §4C · A CODEX FINDING'S SEVERITY IS NOT EVIDENCE, AND ITS NUMBERS CAN BE FABRICATED — 2026-08-28

**Measured on TOR-941 by an adjudicator seat, by executing the reviewer's own stated scenario.**

Round 3 returned a HIGH at severity **0.99** whose argument turned on a specific digest,
`98cf77e4…`. The lane reproduced the scenario independently and got **`2cd17f14…`**. It reported the
discrepancy rather than adopting the reviewer's digit — *"the property reproduced; their exact value
did not"* — and the adjudicator then settled it: **Codex's value is fabricated. Its own notes admit it
had no interpreter.**

🔑 **The inference that matters is not "one digit was wrong": the finding's SEVERITY inherits the
fabrication.** A 0.99 computed over an invented intermediate is not a strong finding with a typo in
it; it is a number with no measurement under it. **Read a severity as the reviewer's confidence in its
own reasoning, never as evidence about the code.**

⚠️ **The reviewer cannot execute anything** — read-only blocks the temp directory pytest needs — so
**every claim it makes about runtime behaviour is inference from reading.** That is usually valuable
and it has no way to check itself. A concrete-looking artifact (a hash, a byte count, a line of
output) is exactly where that shows, because it *looks* like it was run.

**So the rule is: any specific VALUE in a Codex finding — a digest, a count, a rendered string — is a
CLAIM TO REPRODUCE before it is acted on.** The lane's behaviour here is the model: reproduce, and when
the value differs, **report the discrepancy rather than adopting the reviewer's or quietly dropping
your own.** Had it adopted `98cf77e4…`, nothing downstream would ever have questioned it.

⚠️ **And this does NOT license discounting rounds.** The same three rounds surfaced real defects —
including one the reviewer found in the lane's own fix, twice. What is unreliable is the *arithmetic
inside* a finding, not the finding's existence. Adjudicate each on the source, as always.

---

## §4D · A QUOTA-KILLED JOB AND A FAILING TEST BOTH READ `conclusion=failure` — 2026-08-28

Measured on `Torque-Capital/torque` run `33194621541` (PR #788) at the moment the account hit 100% of
its GitHub Actions budget:

```
test-frontend  status=completed  conclusion=failure
               started 17:25:39  completed 17:25:44     <- FIVE SECONDS
               steps: 0          first_step: NONE       <- THE DISCRIMINATOR
test-backend   status=queued     conclusion=null        <- never started at all
```

**A job that never ran and a job whose tests failed are the SAME `conclusion` value.** Nothing in the
check rollup, in `gh pr view`, or in `mergeStateStatus` separates them — all three say the PR is red.

🔑 **The discriminator is `steps` (and duration).** A real failure executes steps and takes minutes; a
billing kill has **zero steps** and completes in seconds.

```bash
gh api repos/<owner>/<repo>/actions/runs/<id>/jobs \
  --jq '.jobs[] | {name, conclusion, steps: (.steps|length), started_at, completed_at}'
```

⚠️ **And the logs cannot tell you** — `gh run view <id> --log-failed` answers *"run is still in progress;
logs will be available when it is complete"* while a sibling job sits queued, and the per-job log
endpoint returns **404**. So the instrument a reader reaches for first is unavailable in exactly this
case, which is what pushes them toward guessing.

### The failure this actually caused, recorded because it was the dispatcher's

Two backend-only PRs (#787, #788) went red on `test-frontend` while a prose-only PR (#786) passed it.
The dispatcher read that pattern as a **shared vitest flake** (TOR-810) and sent **both lanes** to hunt
a failing test. **There was no failing test.** It was a real symptom with a plausible mechanism attached
and *no evidence connecting them* — the `measured-symptom, invented-cause` failure, committed by the
seat that relays that rule to others.

**What kept it cheap** was hedging it explicitly as a hypothesis and requiring each lane to *name the
failing test and its duration* before believing the flake. **What it still cost** is that the search
direction was the dispatcher's and it was wrong. 🔑 **Check `steps` BEFORE proposing a cause** — it is
one API call, and it separates the two worlds outright.

### Re-triggering once quota is restored

`gh run rerun <id> --failed` first. If that is refused, `ci.yml` is `on: pull_request` with **no
`workflow_dispatch`**, and close/reopen has been observed **not** to fire — the working fallback is
`git commit --allow-empty`, which fires `synchronize`. ⚠️ It mints a new head but **not a new tree**, so
prior verification still describes the bytes under review: **name both shas in the PR body.**

### ⚠️ Addendum — THE MIRROR RULE: a suspect zero can be TRUE SIGNAL, and discounting it has a cost

The lane on PR #788 reached the quota diagnosis **independently**, and named what got it there:

> *"The jobs API returned `steps=0` for the completed, failed frontend job. I flagged that as a blind
> probe — **correctly at the time**, because a broken query returns the same zero — but it was true
> signal: the job had zero steps **because it never ran**. This session's other three instrument
> failures all pointed at the comfortable answer; **this one pointed at the truth and I under-trusted
> it.**"*

🔑 **This is the counterweight to *a zero is a claim about your predicate*, and both rules are right.**
That rule exists because a wrong predicate returns a truthful zero about the wrong question. But its
reflex — *distrust the zero* — is not free: applied to a zero that IS the finding, it discards the
answer. **The discipline is not "distrust zeros"; it is "establish what PRODUCED the zero"** — which
resolves it in either direction, and which a bare reflex does not.

**What settled it was refusing to reason from the symptom at all.** The lane ran all four
`test-frontend` commands first-party on the exact tree — `npm ci`, `npm run build`, `npm run test`
(**1006 passed | 3 skipped**), `npm run gen:api:check` — and **reported them as positive counts**.
⚠️ That mattered more than it looks: `frontend/node_modules` was **absent** in that worktree, so a
grep-for-failures would have returned a **clean-looking empty result from two `command not found`s**.
A must-hit positive count is what separates *the suite passed* from *the suite never ran* — the same
distinction as `steps: 0`, one layer up.

**Re-trigger mechanics, verified rather than assumed:** the empty commit `e6c56db5` has a **byte-identical
tree** to the reviewed head `4b50c366` (`git rev-parse <sha>^{tree}` → `45e62d49…` for both), and
`push_gate_cache.check` still read `FULL: HIT` over those exact bytes. `frontend/node_modules` and
`frontend/dist` are both gitignored, so `npm ci` could not cost the token the way §TOR-960 describes —
**checked before installing, and the tree oid confirmed unchanged afterwards.**

---

## §4E · THE CORRECTIVE THAT DISAGREES WITH THREE WRONG INSTRUMENTS CAN STILL ANSWER THE WRONG QUESTION — 2026-08-28

**Measured on PR #787 (TOR-955), round 4.** The sharpest instrument failure of the night, and the one
no existing rule covers.

A lane's refusal message asserted something the code could not support. Three of its own arms had
returned **reassuring false zeros** — a fixture whose ratios were equal *by construction*, a sweep
where `tranche_size` scaled inversely so ratios were invariant, and a source probe with the wrong
string. **All three said "nothing is affected"** — the answer that would let the false sentence stand.

The lane applied the right corrective: **stop reasoning from fixtures, read the dependency from the
engine's source.** It did that, correctly, and wrote a new sentence — **which was also false, and false
in BOTH directions at once.**

```
what "read it from the CODE" answers     DERIVATION   — which functions take `sched`
what the SENTENCE claimed                PROPAGATION  — whether displayed values change
```

🔑 **The fourth instrument did not agree with the three wrong ones. It DISAGREED — which is exactly
what made it feel like the fix — while measuring a different question and feeling authoritative for
being structural.**

⚠️ **This defeats the fleet's standing remedy.** *"Two instruments disagreeing is the finding"* is how
five other false zeros were caught tonight, and here disagreement was the thing that certified the
wrong answer. A structural derivation genuinely IS stronger evidence than a fixture — about
derivation. It says nothing about propagation, and nothing in *"measure the code, not the fixture"*
tells you which claim your sentence is making.

**How to apply:** before accepting a corrective instrument, **state the question the SENTENCE asks and
the question the INSTRUMENT answers, separately, and check they are the same one.** A structural
result that contradicts a fixture result is not automatically the better answer to *your* question —
it may be the right answer to its neighbour.

**Recorded remedy in that instance: a DELETION, not a fifth patch.** The lane had pre-committed that a
fourth same-class defect in one paragraph meant the message should stop asserting anything beyond the
observable — and that pre-commitment, written before the verdict, is what made the deletion available
instead of another attempt. ⚠️ **Do not let a lane replace the deleted claim with a corrected one:**
silence about an unmeasured property is honest; a fourth statement of it is not.

---

## §6A · REVIEW TIERING AND A NARROW DISPATCHER SELF-MERGE — Shahar, 2026-09-18

**Authorising words:** *"i approve your recommendations. also for 5a as you recommend."* The
dispatcher seat proposed both halves below and stated the argument against the second; Shahar
delegated the call and the seat adopted it. **Either half is revocable by one sentence from him.**

### Why this exists — the measurement, not a preference

Six adjudications ran on 2026-09-18. Two returned defects that would otherwise have shipped: a guard
documented fail-CLOSED that was **fail-OPEN through the first entry of its own read-allowlist**,
against a real-client restore; and a **terminal HOLD sitting on a PR's exact head** that the seat's
brief had declared absent. **Three of the six spent part of their round correcting the DISPATCHER'S
BRIEF rather than reviewing the PR.**

Separately, PR-cycle profiling records a median of ~18–21 minutes with **every** long outlier
(158 / 121 / 90 / 80 / 68 min) being a multi-round adjudication. **Round count is the largest single
lever on wall clock in this programme — larger than test time.**

So the cost is real AND the catches are real. The defect was applying one apparatus flatly: a skill
DESCRIPTION REWRITE was receiving the same treatment as a write-guard on real client data.

### Part 1 · TIERING — by blast radius, not by diff size

**FULL TIER — a fresh `/adjudicate` seat, always.** A PR whose delta touches any of:
- `authored_pages/**` (except `**/README.md`), or any published-bytes or artifact path
- the §4A route-A mandatory class, at a count **greater than zero**
- `api/services/**`, `db/**`, `contracts/**`, `scripts/baseline/**`, `.github/**`
- **any guard, gate, refusal, allowlist, denylist or classifier** — see Part 3
- anything reading or writing `torque_baseline`, `torque_qa`, `railway_production_restore`
- a serve-mode, pin, descriptor, publish or restore operation

**MEASURED-PASS TIER — one pass, no round.** Everything else: docs, skills, decision records. The
pass is not a skim and its four steps are mandatory:
1. §4A mandatory-class count **with must-hit AND must-miss controls on the matcher**
2. freshness measured with `scripts/pr_freshness.sh` — never a green rollup or a three-dot diff
3. CI green on the **exact head**, read from `commits/<sha>/check-runs`
4. **"What is the biggest problem with this PR that I did NOT name?"** — this line has returned the
   review's most important finding thirteen times out of thirteen, every one outside every flag the
   brief wrote. It is not optional in either tier.

### Part 2 · THE SELF-MERGE GRANT — every condition, conjunctively

The dispatcher may merge **without a second seat** only when ALL of these hold, each measured at the
moment of merging:

```
1  §4A mandatory-class rows == 0, measured with must-hit AND must-miss controls
2  MERGEABLE/CLEAN and freshness CURRENT via scripts/pr_freshness.sh
3  CI green on the EXACT head (commits/<sha>/check-runs, total_count > 0 AND all complete)
4  NO comment requesting changes — read `gh pr view N --json comments`, NEVER `reviewDecision`
5  the delta touches none of the FULL-TIER paths in Part 1
6  it is not a guard, gate, refusal, allowlist, denylist or classifier change
7  no publish is in flight on the current develop  (see the ordering rule below)
```

⚠️ **Condition 4 is load-bearing and the field that looks like it is useless.** §4B: `reviewDecision`
is **ALWAYS EMPTY** in this fleet — one shared GitHub actor, so every ruling is a comment, and that
field structurally cannot distinguish *never adjudicated* from *changes requested*. A seat that
checks it will merge under a live hold and believe it checked.

⚠️ **Condition 7 exists because `build.sh` bakes `BUILD_BASE="$(git rev-parse origin/develop)"` into
the IMMUTABLE descriptor.** If develop moves between a rebuild and its publish, the descriptor and
the tree disagree permanently and no gate sees it. The fleet ordering is
**merge → rebuild ON THE MERGE COMMIT → read `page_pointers` → publish PINNED.**

**Audit obligation:** every self-merge records, in the PR, the seven conditions with the measurement
that discharged each. A merge without that record is a gate bypass wearing a green tick.

### Part 3 · WHY GUARDS ARE CARVED OUT — the finding that set the boundary

An allowlist fails through **what it ADMITS**, never through whether its enforcement path fires.
Measured 2026-09-18 on the protected-DSN guard, first-party with a must-fire control:

```
SELECT * INTO new_tbl FROM …   is_write -> False, AND IS SENT   <- PostgreSQL CREATES A TABLE
SELECT setval(…) / nextval(…)  is_write -> False, AND IS SENT
```

Five red mutations, three-route coverage and a real-database verification were all green. The
adjudicator's diagnosis:

> **"Every control varies the PLUMBING; none varies the MEMBERSHIP of `_READ_VERBS` — and membership
> is where an allowlist fails."**

⚠️ **And the obvious fix does not work:** escalating `SELECT` into the scanned-verb set leaves it
open, because `SELECT … INTO` contains no DML token. **The test owed is one violating case per
ADMITTED member**, not another route test.

🔑 **This is why a guard can never take the measured-pass tier.** The artifact a guard produces —
a green mutation table on its enforcement path — is the most convincing evidence available and is
structurally silent about the guard's actual decision. Maximally reassuring, maximally blind.

### What this section does NOT grant

- **No merge of anything in the FULL tier**, at any confidence, on any freshness.
- **No ruling.** The dispatcher still rules on nothing: not design, not plans, not code.
- **No Terraform apply of any kind.** Dev applies are `/adjudicate`'s; **PROD is Shahar's every time.**
- **No serve-mode flip.** A page goes live on Shahar's quoted sentence, per page, with the flip record
  quoting it. Publishing PINNED is sanctioned; flipping is not.
- **No self-granted widening.** A seat that finds these conditions inconvenient escalates; it does not
  reinterpret them. ⚠️ Taking authority feels efficient the way standing down feels costless — both
  get less scrutiny than they deserve, and both are decisions.

### ⚠️ AMENDMENT 2026-09-18 · §6A Part 1 — DECISION RECORDS ARE FULL TIER, and the reason is not blast radius

`docs/decisions/**` and `docs/v2-architecture/**` join the FULL TIER. **Not because of what they
can break — they ship no bytes — but because they are the one document class whose citations
nothing checks.** Proved two ways on 2026-09-18, one by execution:

```
doc_citations.py:77-78   puts docs/decisions/ DELIBERATELY out of scope ("records of a past world")
EXECUTED                 is_compass_doc('docs/decisions/sandbox_packages_and_upload.md') -> False
test_cited_tests_exist   SCANNED = ("api", "contracts/torque_contracts", "scripts")  — no docs/
                         and it resolves only test IDENTIFIERS, never arbitrary paths
CONTROL                  tests/structure/ runs 2300 passed on the merged tree
                         WITH ALL NINE CITATION DEFECTS INSIDE THAT GREEN
```

**Nine citation defects reached review in one memo**, including two blocking: a claim that
`models/` + `risk/` ship as a versioned wheel (false — `packages = ["torque_engine"]`, and
`tests/structure/test_engine_wheel.py:34` puts both in the forbidden-import `PLATFORM` set, so a
running CI guard *prevents* it), and a claim that a guard's named tripwire is "the whole of" it, so
adding a third identity column "stays green".

🔴 **The second one is why this tier exists.** Measured on a disposable scratch DB: baseline
**48 passed**; add a third identity column to `_RAN_IDENTITY_COLUMNS["vault_script"]` →
**6 FAILED / 42 passed**, while the *named* tripwire isolated still **passes**. `pins.py` does
`entry[c]` per required column, so the column produces a `KeyError` gap. **As written the memo tells
an implementer that six real guards are not guards — which licenses deleting them.** A document
that can cause a guard to be removed has blast radius; it just does not have a diff.

⚠️ **And a FULL-TIER seat got this wrong first, which is the load-bearing part.** Its initial
verdict endorsed the memo's claim on the strength of `git grep -n "_RAN_IDENTITY_COLUMNS"` returning
4 references. **The three real tripwires never name that identifier** — they reach the tuple through
`_computed_view`. Its own account:

> *"My probe was built from the vocabulary of the answer I expected, so it could not return the thing
> that refutes it. Because the result AGREED with the lane, nothing re-checked it — I called a grep
> 'independent verification' and it wore the authority of an execution."*

**So the rule for this tier is not "read more carefully". It is: a claim that a guard does NOT cover
something must be discharged by EXECUTING a mutation, never by a grep.** An absence measured with
the vocabulary of the thing you expect to find is not a measurement. Pair it with a baseline and
revert the mutation; use a `scratch_<ticket>_<purpose>` database and never a protected restore.

⚠️ **One further trap specific to this class: correcting a document makes you inherit its
neighbours.** The same memo caught one genuinely stale claim and absorbed the false one sitting
beside it in the same section, unmeasured — and the absorbed claim pointed the way its own
conclusion needed. **Enumerate every factual claim in each section you touch and mark it measured /
unmeasured / out-of-scope**, and say in the PR which neighbours you did not check.

### ⚠️ AMENDMENT 2026-09-18 · §6A Part 4 — AN INSTRUMENT THAT CANNOT RETURN THE OPPOSITE VALUE

**Before believing any probe, answer one question: what would this say if the opposite were true?**
If there is no input on which it returns the other value, it is not a measurement — it is a
constant wearing the shape of one.

**Three instances in one afternoon, found by two independent seats**, all verifying whether an
authored page had picked up a changed page-kit bundle — i.e. all guarding bytes that become
**immutable on publish**:

| instrument | what it could never return |
|---|---|
| `grep -c hairline` on the bundle | **any change at all** — `1` before, `1` after. `grep -c` counts LINES and the bundle is minified, so every match shares one. The blob gained 5 occurrences and a new mark role. |
| extract-the-inlined-region-and-hash | **a boundary slip distinguished from a stale bundle.** `build_page.py` *consumes* the marker it splices at, so the region has no delimiter; an off-by-one is indistinguishable from the defect. |
| `grep TORQUE_PAGEKIT_BUNDLE` | **`True`.** The string was invented and exists in no input. The real marker is `/* PASTE assets/vendor/torque-charts.js HERE` (`build_page.py:44`). |

🔴 **Each returned a clean answer, each pointed the way its author already believed, and none was
capable of the other verdict.** Two of the three were the lane's; the third *agreed with the
adjudicator's own published claim* — and surfaced only because that seat checked a probe that was
flattering it instead of banking it. **A probe that confirms you is the one that stops being
examined.**

**Cost if unexamined:** *"bundle unchanged"* written into a README about a materially different
artifact, on a page that cannot be corrected after publish. CLAUDE.md records TOR-785 because a
stale bundle once shipped 7 wrong numbers to a real client.

**The rule.** Every probe whose **absence or constancy** you intend to act on ships with a control
that **fires** — on a subject where the answer is known to differ:

```
CONTROL  marker in template.html : True     <- proves the probe CAN find it
         marker in out.html      : False    <- the finding
```

And prefer a comparator that is **exact by construction** over one that needs alignment. For
"did this file change?" use the **blob sha** (`git rev-parse <ref>:<path>`). For "was this content
spliced into that artifact?" use **substring containment in both directions** — new text present,
old text absent, plus `old != new` to prove the pair is non-vacuous — because the splice is
byte-exact and there is nothing to align.

⚠️ **This is §6A Part 3 one level down.** There, an allowlist failed through what it ADMITTED
while every enforcement-path control stayed green. Here, a probe fails through what it CANNOT
RETURN while every reading stays clean. **Both are answered by varying the axis the controls do
not vary**, and in all four cases it took a second seat asking.

### 🔴 CORRECTION 2026-09-18 · §6A Part 3 IS ONE-DIRECTIONAL AND THAT IS NOT ENOUGH

Part 3 says: *one violating case per **admitted** member.* **That covers only half the boundary, and
the dispatcher's claim that a second PR "doubly evidenced" it does not survive checking** — measured
by #1020's second adjudicator:

```
#1020  the ADMITTED set contains members that should not be   -> violating case from INSIDE
#1021  states OUTSIDE the admitted set are REACHABLE and treated as inside -> the opposite direction
```

**They are two different failures of one boundary, not two instances of one failure.** The rule must
be **two-directional**:

1. For each **admitted** member, a case that begins with it and nonetheless violates.
2. For each **reachable non-member**, proof it is actually excluded — enumerate what the producing
   code can write, not what the consuming code expects to read.

### 🔴 AND THE THIRD ROUND ON THAT SAME GUARD IS THE REASON THIS MATTERS

Round 1: `SELECT … INTO` / `setval` / `nextval` admitted by `_READ_VERBS`, sent, wrote.
**The fix was correct** — enforcement moved to the only complete oracle, a PostgreSQL session that is
`READ ONLY` at open, with the name-classifier demoted to a pre-send filter and **documented as not
complete**. Round 2 then measured, on a scratch DB with a must-fire control on the same connection:

```
RESET ALL · DISCARD ALL · SET SESSION CHARACTERISTICS … READ WRITE
    all in _READ_VERBS · all is_write=False · all flip transaction_read_only on -> off
then SELECT innocuous_looking_report()   -> LANDED A ROW   (control refused it while armed)
```

`db/protected.py:51` asserts the server layer is *"THE VERDICT. Complete by construction."* It is not.

🔑 **The mechanism, and it generalises past SQL:** the classifier's predicate is *"can this verb
write?"*, and for those three the honest answer is **no**. `_CANNOT_WRITE`'s recorded reasons are
**true about writing — and they are the bypass.** A verb that does not write but **disarms what stops
writes** is invisible to a predicate about writing.

> **Enforcement moved layers; the membership question did not move with it.**

**So when a guard is relocated to a stronger layer, re-ask the membership question AT THE NEW LAYER.**
A correct relocation does not inherit the old layer's boundary, and the old boundary is usually still
sitting there deciding what reaches the new one. ⚠️ **Treat "complete by construction" in any
docstring as a claim to execute, never to read** — it is the sentence most likely to stop the next
reader looking.

*(Mitigating and stated by that seat: nothing in-repo issues any of the three — `RESET ALL` 0 hits,
`DISCARD ALL` 1, which is the PR's own test asserting it safe. Filed as TOR-1337.)*

### 🔴 CORRECTION 2026-09-18 · THE SLOT RECIPE I PUT IN ~15 BRIEFS RELEASES NOTHING, SILENTLY

**Broken — do not use.** Reported by a lane, then reproduced live:

```bash
SLOT=$(… acquire 4 $$) || exit 64
trap '… release "${SLOT#SLOT=}" $$' EXIT INT TERM      # <- WRONG
```

`acquire` prints **three** fields, not one:

```
SLOT=/Users/…/slots/slot2 BACKENDS=11 OWNER=43761
${SLOT#SLOT=}  ->  /Users/…/slots/slot2 BACKENDS=11 OWNER=43761      <- path PLUS two junk fields
correct        ->  /Users/…/slots/slot2
```

🔴 **And it fails toward success.** `release` does `[ -d "$SLOT" ] || { echo "GONE=$SLOT (already
released or reaped)"; exit 0; }`. The junk path is not a directory, so it prints *"already released
or reaped"* and **exits 0**. The trap looks clean, the lane sees a success line, **and the slot stays
held** until the dead-owner reaper collects it. A live sighting: the shared registry's `slot1` held
by a dead owner earlier today.

**Current supported form — use the owned runner.** After the coordinated installation in
[SUITE-RUNNER.md](SUITE-RUNNER.md), the private entry point delegates to Torque's pinned
process-group-aware runner. Configure the intended worktree's interpreter/PYTHONPATH in the same
invocation, then run:

```bash
~/.claude/torque-orchestration/suite_slot.sh run --wait-seconds 60 4 -- <foreground suite command>
```

Options precede the slot count; these values are operational examples, not measured capacity.
The adapter refuses the old `acquire` recipe so a copied brief cannot reserve with a short-lived
shell and launch later. `claim` is only for explicitly registering already-running work. The
historical failure below explains why; it does not authorize an old reaper during the cutover.

⚠️ **This is §6A Part 4 in the dispatcher's own hand.** A release that reports success while releasing
nothing is an instrument that cannot return the opposite value — and it was pasted into roughly
fifteen briefs today **after** the `$$` defect it was written to fix. **The remedy for a broken
recipe is to run it once and read what it produced**, not to reason about what it should produce.
