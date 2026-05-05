---
name: tech-design-doc
description: Use when authoring, scaffolding, or auditing a technical design doc, RFC, ADR, technical spec, or architecture proposal — for any audience including external dev partners. Triggers include "design doc for X", "I need an RFC", "should this be an ADR or a full design doc", "help me prep for the architecture review meeting", "audit this design doc". Skip for product plans / PRDs, single-line decisions that fit in a commit message, post-mortems, or process-only meeting agendas without architectural content.
---

# Technical Design Doc

The only thing a design doc optimizes for is decision quality — *can a reasonable reviewer make the right call from this doc in one meeting*. Most "bad" design docs aren't bad at writing; they're bad at triage. Get the format right and 70% of the work is done.

## Triage first (do this every time)

```
Q1. Recording a decision already made, OR seeking buy-in?
    └─ recording → ADR (~1 page)

Q2. Buy-in: how many stakeholders?
    ├─ 1-3 your team           → standard RFC (4-6 pages, 60-min review)
    ├─ 4-10 cross-team         → standard RFC + formal approvers list
    └─ org-spanning / infra    → heavyweight (10-20 pages, KEP + PRR)

Q3. Audience is an external partner (different company)?
    └─ yes → switch to partner-mode (adds glossary, ownership table, "proposing" tone)

Default if unsure: standard RFC. Need evidence to grow heavyweight or shrink to ADR.
```

Edge cases (PR/FAQ vs design doc, splitting, when ADR should grow into RFC) → [reference/triage.md](reference/triage.md).

## Templates

| Template | Pages | Meeting | When |
|---|---|---|---|
| `mini-adr.md.tmpl` | 1-2 | 30 min or async | Decision already made — recording it. Nygard format. |
| `standard-rfc.md.tmpl` | 4-6 | 60 min | Buy-in for a non-trivial design, one team. Rust-RFC skeleton. |
| `heavyweight-doc.md.tmpl` | 10-20 | multi-week | Org-spanning, infra-sensitive. KEP + Production Readiness Review. |
| `partner-doc.md.tmpl` | flexible | varies | External dev partner. Standard + glossary + ownership table. |

## Workflow

```
1. Triage              → pick template
2. Scaffold            → scripts/new-doc.sh --template <t> --slug <s> --title "..."
3. Outline (BLUF)      → Summary + Goals/Non-Goals first
4. Alternatives        → ≥3 alternatives BEFORE detailing the proposal
5. Design              → proposal + diagrams (C4 context + sequence)
6. Cross-cutting       → fill checklist; mark N/A explicitly with reason
7. Audit               → scripts/audit-doc.py <file>
8. Pre-read            → distribute 24h before meeting (48h for partner-mode)
9. Decide              → meeting (or async) → status flips
10. Log                → scripts/append-decision-log.py → row in DECISIONS.md
11. (optional) Sync    → gdoc-sync to a live Doc
```

## House rules (audit enforces 6 of 10)

1. **BLUF.** First paragraph names the decision being requested, not the background.
2. **Quantify goals** — replace adjectives with numbers. ("scalable" → "10× peak, p95 ≤ 300ms"). See [reference/non-goals.md](reference/non-goals.md).
3. **Alternatives, scored on consistent axes.** Standard RFC and heavyweight: ≥3 alternatives (status quo + incremental + proposal at minimum). Mini-ADR: 2-3 inline brief alternatives are fine — narrower decision, lighter requirement. See [reference/alternatives-considered.md](reference/alternatives-considered.md).
4. **Non-goals are load-bearing** — they prevent 80% of scope-creep arguments.
5. **No happy-path-only diagrams.** Show retries, timeouts, failure paths. See [reference/diagrams.md](reference/diagrams.md).
6. **Cross-cutting checklist every time** — security, privacy, observability, rollout, scalability, dependencies, failure modes, on-call. Silent omission forbidden; N/A with reason is fine. See [reference/cross-cutting-checklist.md](reference/cross-cutting-checklist.md).
7. **Status header mandatory** — Version, Author, Status (Draft/In-Review/Accepted/Rejected/Superseded), Approvers, Decision date.
8. **Be opinionated** — your job is to propose. If genuinely no opinion, say so explicitly and commit to that posture.
9. **Length matches scope** — 2 pages → 30-min, 6 pages → 60-min, >6 pages → split or escalate. Past these breakpoints, comment volume goes nonlinear.
10. **End with Next Steps, not approval** — phases, owners, dates, metrics. Approval is the start.

The why behind each rule + 9 documented anti-patterns: [reference/anti-patterns.md](reference/anti-patterns.md).

## Reference docs (load on demand)

| File | When |
|---|---|
| [reference/triage.md](reference/triage.md) | Edge cases (ADR↔RFC, PR/FAQ, splitting) |
| [reference/canonical-outline.md](reference/canonical-outline.md) | Outlining — every section, with rationale |
| [reference/alternatives-considered.md](reference/alternatives-considered.md) | The highest-leverage section in the doc |
| [reference/non-goals.md](reference/non-goals.md) | Quantification rules for Goals/Non-Goals |
| [reference/cross-cutting-checklist.md](reference/cross-cutting-checklist.md) | The 8-item checklist + heavyweight PRR |
| [reference/diagrams.md](reference/diagrams.md) | C4 + mermaid recipes |
| [reference/partner-mode.md](reference/partner-mode.md) | External-dev-partner specifics |
| [reference/meeting-protocol.md](reference/meeting-protocol.md) | Pre-read window, decision capture |
| [reference/anti-patterns.md](reference/anti-patterns.md) | 9 killers + rewrite examples |
| [reference/examples/](reference/examples/) | Worked mini-ADR + standard-RFC |

## Scripts

| Script | What |
|---|---|
| `scripts/new-doc.sh --template <t> --slug <s> --title "..."` | Scaffold from template into `./drafts/design-<slug>-v1.md` |
| `scripts/audit-doc.py <file>` | Static checks against house rules; non-zero on errors |
| `scripts/append-decision-log.py <file>` | Append one row to `DECISIONS.md` after Accepted |

Output: `./drafts/design-<slug>-v1.md` + `./drafts/DECISIONS.md`. Never overwrite a previous version without asking.

## When NOT to use

- **PRD / product plan** — vision-first, customer-first. Different shape.
- **Brainstorm / sketch** — too early. Free-form notes; escalate when ready for buy-in.
- **Single-line decision** — write a commit message; don't ADR-ify trivial things.
- **Post-mortem / incident review** — separate format (timeline → root cause → corrective actions).

## Cross-skill calls

- **`gdoc-sync`** — push the finished doc to a live Google Doc for stakeholder comments.
- **`presentation-generator`** *(optional)* — derive an exec-summary deck from the doc's Summary + Goals + Alternatives.
- **`prompt-engineer`** *(optional)* — for LLM/agent design docs, reference its prompt-engineering guidance.
