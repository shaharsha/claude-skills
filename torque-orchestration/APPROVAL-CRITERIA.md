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
□  A Codex round artifact EXISTS for THIS artifact
   a round happened iff its .md exists — never because a command exited 0, and a round your
   predecessor ran covers THEIR artifact, not yours

□  The plan names the files it will touch
   no file list -> there is nothing to check the diff against, and no DONE that can be falsified

□  The ticket has a checkable DONE-WHEN
   a goal is not a DONE-WHEN. "improve X" cannot be failed.

□  The plan states what it deliberately does NOT do
   scope without a boundary is not scope

□  The change would actually change something
   TOR-220 was ruled "the fix is the mature-cohort filter" when that filter was already applied
```

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
