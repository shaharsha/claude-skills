---
name: tech-design-doc
description: Author technical design review documents — RFCs, design docs, ADRs, technical specs, architecture proposals — sized correctly for the audience and the decision being made. Triages format first (1-2 page mini ADR for recording vs. 6-page standard RFC for buy-in vs. 10-20 page heavyweight KEP for org-spanning architecture vs. partner-mode for external dev partners), then scaffolds from a research-grounded template, enforces the load-bearing sections (BLUF summary, goals/non-goals with quantified targets, ≥3 alternatives considered, cross-cutting concerns checklist, decision log row), inserts mandatory C4 + sequence diagrams in mermaid, and runs a static audit against best-practice anti-patterns before sync. Calls gdoc-sync to push the finished doc to a live Google Doc when ready. Use whenever the user asks to write, draft, scaffold, or audit a technical design doc, RFC, ADR, design review, technical spec, architecture proposal, or "design doc for X". SKIP when the user wants a product plan or PRD (use freeform or `brand-system`-adjacent), a single-decision micro-record that fits in a commit message, or a process-only meeting agenda with no architectural content.
---

# Technical Design Review

Decision-quality is the only thing a TDR optimizes for. Length, prose-craft, diagram-density — all subordinate to *can a reasonable reviewer make the right call from this doc in one meeting*. Most "bad" design docs aren't bad at writing; they're bad at triage — a 20-page proposal for a one-line ADR-shaped decision, or a 2-page summary for a system-spanning rewrite. Get the format right and 70% of the work is done.

## The triage rule (do this first, every time)

```
Q1: Are you recording an already-made decision OR seeking buy-in?
    ├─ recording      → ADR (Nygard format, ~1 page)
    └─ buy-in / open  → continue to Q2

Q2: How many stakeholders need to read this?
    ├─ 1-3 (your team)         → standard RFC, 4-6 pages, 60-min review
    ├─ 4-10 (cross-team)       → standard RFC + add formal approvers list
    └─ org-spanning / infra    → heavyweight, 10-20 pages, KEP-style + PRR

Q3: Is the primary audience an external partner (different company)?
    └─ yes → switch to partner-mode (any size)
            adds: glossary, decision-ownership column, zero-tribal-knowledge
            context, "proposing + asking" tone

Default if unsure: standard RFC. Require evidence to grow to heavyweight.
Require evidence to shrink to ADR.
```

Read [reference/triage.md](reference/triage.md) for the full decision tree with examples and edge cases (PR/FAQ, when an RFC should split into multiple, when an ADR should grow into an RFC).

## The four templates

| Template | Pages | Meeting | When |
|---|---|---|---|
| `mini-adr.md.tmpl` | 1-2 | 30 min or async | Decision is already made; you're recording it. Nygard: Context / Decision / Consequences. |
| `standard-rfc.md.tmpl` | 4-6 | 60 min | Seeking buy-in for a non-trivial design across one team. Rust-RFC skeleton. |
| `heavyweight-doc.md.tmpl` | 10-20 | multi-week | Org-spanning architecture, infra-sensitive, irreducibly complex. KEP + Production Readiness Review. |
| `partner-doc.md.tmpl` | flexible | varies | Audience is an external dev partner. Standard skeleton + glossary + decision-ownership column + "proposing" tone. |

Pick one, scaffold it via `scripts/new-doc.sh`, fill it.

## Workflow

```
1. Triage          — answer Q1-Q3 above; pick template
2. Scaffold        — scripts/new-doc.sh --template <t> --slug <s> --title "..."
3. Outline         — fill the Summary + Goals/Non-Goals first (BLUF principle)
4. Alternatives    — write ≥3 alternatives BEFORE writing the proposal in detail
5. Design          — write the proposal, then add diagrams (C4 context + sequence)
6. Cross-cutting   — fill the checklist; mark N/A explicitly with reason
7. Audit           — scripts/audit-doc.py <file> — checks structure + anti-patterns
8. Pre-read        — distribute 24h before the meeting
9. Decide          — meeting (or async) → status changes to Accepted/Rejected
10. Log            — scripts/append-decision-log.py — one row in DECISIONS.md
11. (optional) Sync — gdoc-sync to a live Doc for stakeholder comments
```

## House rules

These are imperatives, not suggestions. The audit script enforces most of them.

1. **BLUF every doc.** First paragraph names the decision being requested, not the background. A reader should know in 30 seconds why they're reading.
2. **Quantify every adjective in goals.** "Scalable" is meaningless. "Handles 10× current peak with p95 ≤ 300ms" is a goal.
3. **Always ≥3 alternatives, scored on consistent axes.** Status quo, incremental, your proposal — same axes for all three. Single-option docs get rejected; weak strawmen are nearly as bad as no alternatives.
4. **Non-goals are load-bearing.** Listing what you're *not* doing prevents 80% of scope-creep arguments later. Read [reference/canonical-outline.md](reference/canonical-outline.md#goals--non-goals).
5. **No happy-path-only diagrams.** Every architecture diagram shows retries, timeouts, failure paths, and observability boundaries. A boxes-and-arrows happy path is worse than no diagram — it implies false completeness.
6. **Cross-cutting checklist runs every time.** Security, privacy, observability, rollout/rollback, scalability, dependencies, failure modes, on-call. A skipped item must be explicitly marked N/A with reason — never silently absent. See [reference/cross-cutting-checklist.md](reference/cross-cutting-checklist.md).
7. **Status header is mandatory.** Version, author, last-edited, status (Draft / In-Review / Accepted / Rejected / Superseded), approvers, decision date.
8. **Be opinionated.** Your job as author is to navigate the issue and propose. Ambiguity creates unproductive discussion. If you genuinely don't have an opinion, say "we don't have an opinion; here are the trade-offs and we want the room to decide" — but commit to that posture explicitly.
9. **Length matches scope.** 2-page doc → 30-min decision. 6-page doc → 60-min decision. >6 pages → split into sub-decisions or escalate to heavyweight (multi-week). Past these breakpoints, comment volume goes nonlinear and decisions slip.
10. **End with Next Steps, not approval.** Phases, milestones, follow-up RFCs/ADRs, migration steps, success metrics with measurement plan. Approval is the start, not the finish.

## Reference docs (load when needed)

| File | When to read |
|---|---|
| [reference/triage.md](reference/triage.md) | Before scaffolding, especially for edge cases (ADR vs RFC, PR/FAQ, splitting) |
| [reference/canonical-outline.md](reference/canonical-outline.md) | While outlining; lists every section across all templates with rationale |
| [reference/alternatives-considered.md](reference/alternatives-considered.md) | While writing the Alternatives section — the highest-leverage section in the doc |
| [reference/non-goals.md](reference/non-goals.md) | While writing Goals & Non-Goals — quantification rules |
| [reference/cross-cutting-checklist.md](reference/cross-cutting-checklist.md) | After the proposal is written — fill the checklist |
| [reference/diagrams.md](reference/diagrams.md) | Before adding diagrams — C4 model, mermaid recipes, anti-patterns |
| [reference/partner-mode.md](reference/partner-mode.md) | Whenever the audience is an external dev partner |
| [reference/meeting-protocol.md](reference/meeting-protocol.md) | Before distributing — pre-read window, 2-round-trip rule, questions doc |
| [reference/anti-patterns.md](reference/anti-patterns.md) | Before audit — 9 killers from the literature with rewrite examples |
| [reference/examples/](reference/examples/) | Worked examples: mini-adr-example.md, standard-rfc-example.md |

## Scripts

| Script | What |
|---|---|
| `scripts/new-doc.sh --template <t> --slug <s> --title "..."` | Scaffold from template; fills frontmatter (date, author, status: Draft); writes to `./drafts/design-<slug>-v1.md` (or path passed via `--out`). |
| `scripts/audit-doc.py <file>` | Static checks: required sections present, ≥3 alternatives, no buzzword goals, status header complete, decision-log row drafted, diagrams present (warns; doesn't fail). Returns nonzero on errors. |
| `scripts/append-decision-log.py <tdr-file> [--log DECISIONS.md]` | After a TDR is Accepted/Rejected, appends one row to a project-level decision log. |

## Output convention

```
./drafts/
├── design-<slug>-v1.md       # current draft, versioned (-v2, -v3 on iteration)
└── DECISIONS.md           # auto-appended log; one row per accepted decision
```

Never overwrite a previous version without asking. The audit script will complain if it sees `design-foo-v1.md` and `design-foo-v2.md` with the v1 status still "Draft" — old drafts should be marked `Superseded` before bumping.

## When to use this skill

- "Help me write a design doc for X."
- "I need a TDR / RFC / ADR / technical spec for X."
- "We need to design X — write up the proposal."
- "Audit this design doc."
- "Should X be a design doc or just an ADR?" (triage question)
- Aimed at any audience: internal team, cross-team, external dev partner.

## When NOT to use this skill

- **Product plan / PRD** — different shape (vision-first, customer-first). Write freely or use a PRD template.
- **Architecture sketch / brainstorm** — too early for a TDR. Sketch in markdown notes, then escalate when you're ready to seek buy-in.
- **Single-line decision** — "we'll use Postgres not MongoDB, end of conversation" — write a one-liner in a commit message or a CHANGELOG note. Don't ADR-ify trivial things.
- **Process-only meeting agenda** — no architectural content. Use `presentation-generator` if you need slides, or just a markdown agenda.
- **Post-mortem / incident review** — different format (timeline, root cause, contributing factors, corrective actions). Use a post-mortem template.

## Cross-skill calls

- **`gdoc-sync`** — push the finished TDR to a live Google Doc for stakeholder comments. The included partner-mode example uses exactly this flow.
- **`presentation-generator`** *(optional)* — generate an exec-summary deck off the same TDR for the actual review meeting. Use the TDR's Summary + Goals + Alternatives table as the skeleton.
- **`prompt-engineer`** *(optional)* — when the TDR proposes an LLM agent / prompt-heavy system, the Design section's prompt-engineering choices should reference `prompt-engineer`'s reference docs.

## First-run validation

If you have an existing design doc from before this skill, audit it as a smoke test:

```bash
~/.claude/skills/tech-design-doc/scripts/audit-doc.py path/to/your-existing-doc.md
```

Common gaps the audit surfaces on pre-skill docs: missing explicit Non-Goals section, no Alternatives Considered section, no SLA/success-metric targets in the proposal, no decision-log row drafted. Each becomes an actionable item for the next revision.
