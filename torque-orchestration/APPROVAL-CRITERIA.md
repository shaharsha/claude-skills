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

### 🔴 ROUTE A IS MANDATORY — route B cannot discharge it — for this change class

```
engine/**          models/**          risk/**
api/services/<product>/**   for any product in `_REAL_PRODUCTS` (api/routers/companies.py)
db/schema.py · api/auth/** · api/services/{publishing,vault,silver,computation}/**
authored_pages/** EXCEPT **/README.md   ADDED 2026-09-15 — see the amendment directly below
```

**Read the product membership THERE, never from a list written here** — that is this repo's own rule
and this file has already watched two transcribed counts rot. The class is defined by *what a wrong
number reaches*: a real client's decision page, or an immutable published version. Everywhere else,
route B is sufficient.

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

⚠️ **`authored_pages/**/README.md` IS EXCLUDED, and the exclusion follows from the trigger rather than from convenience.** The trigger is *content that becomes immutable*. A page README is the opposite: CLAUDE.md designates it as **mutable and travelling with the page** — it is where the platform-state prose that may NOT go on the page is required to live instead. It is rendered to no client and published nowhere. Corrected the same night the amendment landed, after the glob as first written would have required a round on a three-README docs PR (`#943`).

⚠️ **This does NOT widen the class to every page-kit file.** `scripts/{build_page,lint_page,gen_page_kit_css}.py`
and `.claude/skills/torque-page-kit/**` stay route B — **but NOT for the reason first written here.**

🔴 **The original justification was *"a defect there surfaces on the next build rather than being frozen into
a published artifact"*, and that is FALSE for one file in the exempted set.** `assets/vendor/torque-charts.js`
is inlined **VERBATIM** by `build_page.py:61` into a page that is immutable once published, and CLAUDE.md's
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
