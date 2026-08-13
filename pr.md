---
description: Open a PR and drive CI to green. Does NOT merge — merging is gated elsewhere.
---

Commit the changes, push the branch, and open a PR. Then monitor CI until the checks complete. If a
check fails, read the logs, diagnose the root cause, fix it, and re-push. If you cannot fix it after
two attempts, stop and explain what is failing.

**Then stop. Report the PR number, the pushed head, and the CI result.**

## ⚠️ DO NOT MERGE. This command used to say "once all checks pass, merge the PR" and that was wrong.

Green CI is **not** an approval. It says the tests that exist passed on that head; it says nothing
about whether anyone reviewed the change, whether the plan covered it, or whether the base has moved
since. **Merging on green alone bypasses every gate this machine's sprint work runs on.**

**If this is Torque Sprint work, the flow is `/worker`, and merging is step 8–9 of it:**

```
6  Codex round on the IMPLEMENTATION      a round happened iff its .md exists
7  OPEN THE PR                            <- this command gets you here, and no further
8  the ADJUDICATOR reviews and approves   on the exact head, after you re-merge develop
9  YOU merge, then watch the deploy and QA it live
```

⚠️ **An approval is a pair — a diff AND a base — and it expires when either moves.** So the order is
**re-merge → push → report → approved on THAT head → merge immediately.** Approving first and
re-merging second voids the approval in the act of preparing to use it.

**Never `--no-verify`, never `--admin`, never push to `develop` or `main` directly. Never merge on
silence** — an absent answer is not an approval.

**For non-sprint work in a personal repo**, merging yourself is fine and this command simply stops
early; say so and merge deliberately, rather than having a slash command do it as a side effect.

*Rewritten 2026-08-12. The previous version instructed an unapproved merge on green CI, in the same
command namespace the sprint lanes use.*
