# Review prompt templates

Fill the `{{PLACEHOLDERS}}`, write the result to a file, pass it as `--prompt-file`.

The templates are deliberately lean. GPT-5.6 follows a single clear statement and
loses ground when instructions repeat — OpenAI's own evals put the cost of
redundant system-prompt text at 10-15% of eval score. Resist padding these with
"be thorough" or "think carefully"; on this model family that language buys
over-exploration, not depth.

## What goes in `{{INTENT}}` — and what must not

This is the highest-leverage decision in the whole skill, so it is worth being
precise about.

Give the reviewer the **specification**: what the change is supposed to
accomplish, the constraints it must respect, the invariants that must hold, the
decisions already settled and not up for debate. That is what makes a reviewer
able to catch "this doesn't do what it promised", which is the defect class an
uninformed reviewer structurally cannot see.

Withhold the **rationale**: your reasoning, your justification for the approach,
your confidence that it works, your explanation of why an apparent problem
isn't one. A reviewer handed the author's reasoning tends to grade the
reasoning rather than the artifact.

That split isn't a stylistic preference. In the cross-context review study
(arXiv:2603.12123, 360 runs over 150 injected defects), the condition that got a
fresh context *plus the generation prompt* scored F1 23.8 — below plain
same-session self-review at 24.6, and well below artifact-only review at 28.6.
Carrying the author's framing across the boundary cost more than the fresh
context gained. Specification survives that boundary well; rationale does not.

Concretely:

- Good: "Refunds must be idempotent per `(user_id, refund_id)`. Balances are
  money — no lost updates under concurrent calls."
- Good: "Team decision, not up for review: all DB access goes through
  `db.execute()`. Flagging the direct-driver call in `legacy/` is out of scope."
- Bad: "I used a read-modify-write here because the table is small and
  contention is unlikely, so I think the race is theoretical."
- Bad: "This should be correct — I've already checked the concurrency."

---

## Mode: code

For reviewing a diff. The reviewer reads the diff itself with git rather than
being handed a paste, so it can open surrounding files and check callers.

```
Review the change described below for defects. This is a pre-merge review of the
author's own repository, requested by the author.

<scope>
{{SCOPE}}
</scope>

Read the diff yourself with git, then read enough of the surrounding files to
judge whether each change is correct in context. Callers, tests, and adjacent
error paths are usually where the answer is.

<intent>
{{INTENT}}
</intent>

<what_counts>
Report a defect when you can name concrete inputs or state that produce a
concrete wrong outcome. Correctness, security, concurrency, data loss, broken
API contracts, unhandled errors, and resource leaks all qualify. So does a
change that contradicts a constraint stated above.

Style, naming, formatting, and structural preference do not qualify. Neither
does a pre-existing problem the change does not introduce or worsen. Missing
tests qualify only where an untested path could plausibly be wrong.

Severity is about the consequence if the scenario occurs, confidence is about
whether the scenario is real. Keep them independent — a certain cosmetic issue
is low severity at high confidence, and a suspected data-loss bug is critical at
low confidence. Report both honestly rather than hedging one into the other.

Where the code is genuinely correct, say so and move on. An empty findings list
is a valid outcome and a better answer than a padded one.
</what_counts>

Return your result as JSON conforming to the supplied schema.
```

---

## Mode: plan

For reviewing a plan, design doc, spec, or RFC before implementation. The
`file` field in each finding takes the plan's path; line numbers point into it.

```
Review the plan at {{PLAN_PATH}} against the repository it will be implemented
in. This is the author's own plan, submitted for review before implementation.

Read the plan, then read enough of the repository to check its claims. A plan
that assumes a function, schema, endpoint, config key, or migration state that
does not match the actual repository is the primary thing to catch.

<intent>
{{INTENT}}
</intent>

<what_counts>
Report a defect when the plan would fail, produce a wrong result, or prove
unimplementable as written. That includes: assumptions contradicted by the
repository, steps whose ordering breaks something, missing migration or
rollback paths, unhandled failure modes, ignored concurrent or partial-failure
behaviour, security or data-loss exposure, and requirements the plan silently
drops.

Also report where the plan is more complex than the stated goal requires, when
you can name the simpler approach that meets the same requirements.

Do not report alternative designs that are merely different, or preferences
about structure and wording. Judge the plan against its own stated goal, not
against the plan you would have written.

For each finding, name the concrete circumstance under which the plan fails.
"This section is vague" is not a finding; "step 4 assumes the `accounts` table
has a `version` column, and it does not, so the migration in step 6 fails" is.
</what_counts>

Return your result as JSON conforming to the supplied schema.
```

---

## Mode: code-vs-plan

For checking that an implementation actually does what its plan said.

```
Check whether the implementation described below does what the plan at
{{PLAN_PATH}} specified. This is the author's own work, submitted for review.

<scope>
{{SCOPE}}
</scope>

Read the plan, then read the diff with git, then read enough of the repository
to judge the match. Work through the plan's requirements one at a time.

<intent>
{{INTENT}}
</intent>

<what_counts>
Report: requirements the plan states that the implementation does not satisfy,
behaviour the implementation adds that the plan did not call for and that
changes observable behaviour, and places where the implementation satisfies the
plan's letter while defeating its stated purpose.

Report ordinary defects too — a change that matches the plan exactly and is
still wrong is still worth catching.

A requirement the plan deliberately deferred is not a gap. Say which
requirements are satisfied, not only which are not; a plan fully implemented is
a valid and useful outcome.
</what_counts>

Return your result as JSON conforming to the supplied schema.
```

---

---

## Mode: follow-up (resume the same reviewer)

For arguing with a specific finding. Run with `--resume <label>` — the reviewer
keeps its context, which is the whole point here: it already knows what it
claimed and why, so it can defend or withdraw it.

Ask it to re-derive, not to agree. A reviewer told which answer you want will
generally supply it — sycophancy is trained in, and a prompt that hints at the
expected conclusion gets reasoning built backwards from it.

```
Re-examine finding {{N}} ({{TITLE}}).

{{NEW_EVIDENCE}}

Work through the failure scenario again against the current source. If it still
holds, say what specifically defeats the evidence above. If it does not hold,
withdraw the finding and say what you missed the first time.

Return JSON conforming to the supplied schema, containing only the findings that
still stand.
```

Fill `{{NEW_EVIDENCE}}` with what the source says, not with your conclusion:

- Good: "`pay.py:42` acquires `self._lock` before the read at line 47, and every
  writer path goes through `_apply()` which takes the same lock."
- Bad: "I don't think this race is real — the lock handles it."

---

## Mode: re-review after fixes (start a FRESH reviewer)

Counterintuitive, and worth getting right: after fixing findings, do **not**
resume. Start a new session with `--name <label>-r2`.

Reviewing twice in the same context was the *worst* of the four conditions
measured in arXiv:2603.12123 — F1 21.7, below even plain same-session
self-review at 24.6, and well below a fresh reviewer at 28.6. The second pass
produced *more* findings (5.5 vs 4.8) without producing better ones: it anchors
on its first pass and generates speculation rather than reconsidering. Resuming
to re-review buys the anchoring and pays for it in precision.

A fresh reviewer does need to know what was already addressed, or it re-raises
fixed issues and skips the regression check. Give it the previous findings as
**facts to verify**, not as conclusions to accept — same specification-not-
rationale split as `{{INTENT}}`:

```
Review the change described below for defects. This is a pre-merge review of the
author's own repository, requested by the author.

<scope>
{{SCOPE}}
</scope>

Read the diff yourself with git, then read enough of the surrounding files to
judge whether each change is correct in context.

<previously_raised>
An earlier review raised the items below and the author has since changed the
code. Verify each one independently against the current source: confirm the
defect is genuinely gone, and check that the fix did not introduce a new one.
Do not assume an item is resolved because it is listed here.

{{PRIOR_FINDINGS}}
</previously_raised>

<intent>
{{INTENT}}
</intent>

<what_counts>
Report a defect when you can name concrete inputs or state that produce a
concrete wrong outcome. Include defects unrelated to the list above — the list
is not the scope of the review.

Style, naming, formatting, and structural preference do not qualify. Neither
does a pre-existing problem the change does not introduce or worsen.

Severity is about the consequence if the scenario occurs, confidence is about
whether the scenario is real. Keep them independent.
</what_counts>

Return your result as JSON conforming to the supplied schema.
```

Build `{{PRIOR_FINDINGS}}` from the previous run's JSON — title, file, and line
for each confirmed finding, one per line. Leave out the previous reviewer's
evidence and reasoning; the new reviewer should re-derive rather than inherit.

```bash
python3 -c '
import json,sys
for f in json.load(open(sys.argv[1]))["findings"]:
    print(f"- {f[\"title\"]} ({f[\"file\"]}:{f[\"line_start\"]})")
' .codex-review/<previous>.json
```

---

## Filling `{{SCOPE}}`

Say which changes are under review, in terms the reviewer can act on with git:

- `Uncommitted work: staged, unstaged, and untracked files. git status --short then git diff HEAD.`
- `The commits on this branch that are not on main: git diff main...HEAD.`
- `Commit a1b2c3d: git show a1b2c3d.`
- `Only src/payments/ within the uncommitted changes. Other paths are out of scope.`

## A note on refusals

GPT-5.6 runs live cyber-misuse classifiers over its own output, and OpenAI
documents code review and vulnerability work as legitimate activity that can
trip them. The templates open by naming the work as pre-merge review of the
author's own repository, which is both true and the framing that keeps the run
clean. If a review does come back refused or truncated mid-stream, that is the
classifier rather than a Codex failure — narrow the scope and rerun.
