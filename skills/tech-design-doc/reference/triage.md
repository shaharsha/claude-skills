# Triage: pick the right format before you write

Most "bad" design docs aren't bad at writing — they're bad at triage. A 20-page proposal for a one-line ADR-shaped decision wastes everyone's time; a 2-page summary for a system-spanning rewrite gets rejected for thinness. Get the format right and 70% of the work is done.

## Decision tree

```
Q1. Are you recording an already-made decision, or seeking buy-in?
    ├─ recording  → ADR (mini), 1-2 pages
    └─ buy-in     → continue

Q2. How many stakeholders?
    ├─ 1-3 (your team)              → standard RFC, 4-6 pages
    ├─ 4-10 (cross-team / cross-org) → standard + formal approvers list
    └─ org-spanning / infra / shared platform → heavyweight, 10-20 pages, KEP-style

Q3. Is the audience an external partner (different company)?
    └─ yes → switch to partner-mode (any size; usually standard)

Q4. Is this a customer-facing product, not infra?
    └─ yes, and customer experience is the primary uncertainty → consider PR/FAQ instead
       (PR/FAQ is OUT OF SCOPE for this skill — use freeform or PRD)

Default if unsure: standard RFC. Require evidence to grow to heavyweight.
Require evidence to shrink to ADR.
```

## Format reference

| Format | Pages | Meeting | Mode | When |
|---|---|---|---|---|
| **ADR (mini)** | 1-2 | 30 min or async | recording | Decision is made; documenting for durable memory. |
| **Standard RFC** | 4-6 | 60 min | buy-in | Non-trivial design, single team or small cross-team group. |
| **Heavyweight** | 10-20 | multi-week, multiple sessions | buy-in | Org-spanning architecture, infra-sensitive, irreducibly complex. |
| **Partner-mode** | flexible | varies | buy-in across org boundary | Audience is an external dev partner. |

## Rules of thumb

**An RFC should be an ADR when:**
- The decision is binary (X vs Y) and the team is already aligned on tradeoffs.
- The decision affects only your team's code.
- You can write the rationale in 1 page without losing fidelity.

**An ADR should be an RFC when:**
- The decision affects callers, downstream teams, or shared infra.
- You're not yet aligned on tradeoffs and need a meeting to close.
- The blast radius is irreversible (data migration, API contract change, security model).

**A standard RFC should be heavyweight when:**
- ≥4 services or systems are touched.
- Rollout requires phasing, feature flags, kill switches, dual-writes, or backfills.
- The decision needs production-readiness review (PRR) — security, on-call, SLAs.
- Reversal cost is week-of-engineering-time or worse.

**A heavyweight RFC should split when:**
- It exceeds 20 pages.
- Reviewers can't close in 2 sessions.
- Multiple sub-decisions are independently valid (each gets its own RFC).

## Edge cases

**The "I'm not sure if it's worth a doc at all" case.**
Default: write a 1-page ADR. The act of articulating the decision usually surfaces issues that justify the doc. If the ADR fits in 3 sentences, downgrade to a commit message or CHANGELOG line.

**The "we keep relitigating this" case.**
If the same decision keeps coming up, the *previous* doc is missing or unfindable. Write an ADR, link it from the relevant code (`See: docs/adr/0042-database-choice.md`), and announce. The goal of the ADR is to end the relitigation.

**The "early sketch / brainstorm" case.**
Don't use this skill yet. Write rough markdown notes. When you're ready to seek buy-in, scaffold the standard RFC and use the notes as raw material.

**The "post-mortem" case.**
Different format entirely (timeline → root cause → contributing factors → corrective actions). Out of scope for this skill.

**The "PR/FAQ vs design doc" case.**
PR/FAQ shines when *customer experience* is the primary uncertainty (novel product, unclear value prop). Design docs shine when *technical execution* is the primary uncertainty (infra, refactor, internal platform, integration). For LLM agent integrations into existing products, design doc wins — the customer experience is sketched in the product plan, the uncertainty is technical.

## Worked triage examples

| Decision | Format | Why |
|---|---|---|
| "Pick Postgres vs MongoDB for this service" | ADR | Binary, team aligned on axes, 1 page is enough |
| "Design the LLM agent integration with the existing app" | Standard RFC or partner-mode | Cross-team buy-in, integration points need agreement |
| "Migrate the entire payment system to a new vendor" | Heavyweight | Irreducibly complex, multi-week, PRR required |
| "Adopt sentence-transformers for vector search" | ADR or RFC | ADR if just for one service; RFC if other teams will inherit it |
| "New auth scheme across all backends" | Heavyweight | Org-spanning, security-sensitive, blast radius is huge |
| "Rename a single internal API endpoint" | Commit message + CHANGELOG | Not worth a doc |
| "Should we use TypeScript or JavaScript for the new service?" | ADR | Binary, well-understood tradeoffs, write it once |
| "Build a new internal platform for X used by 10 teams" | Heavyweight + partner-mode if external | Multi-team buy-in, PRR, possibly external collaborators |

## When in doubt

Default to **standard RFC**. It's the workhorse format. The audit script will warn you if your doc is so thin an ADR would have been enough, or so thick it should have been heavyweight or split.
