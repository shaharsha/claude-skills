# Canonical outline: every section, with rationale

The master section list. Templates pick a subset. Each section here has a one-line **purpose** and a one-line **failure mode** so you know why it exists and what it looks like when it's broken.

| # | Section | Mini ADR | Standard RFC | Heavyweight | Partner |
|---|---|---|---|---|---|
| 0 | Status header | ✅ | ✅ | ✅ | ✅ |
| 1 | Summary (BLUF) | ✅ | ✅ | ✅ | ✅ |
| 2 | Context / Background | inline | ✅ | ✅ | ✅ (longer) |
| 3 | Glossary | — | optional | optional | ✅ (mandatory) |
| 4 | Goals & Non-Goals | inline | ✅ | ✅ | ✅ |
| 5 | Proposal / Design | ✅ | ✅ | ✅ | ✅ |
| 6 | Diagrams (C4 + sequence) | optional | ✅ | ✅ | ✅ |
| 7 | Alternatives Considered | inline | ✅ | ✅ | ✅ |
| 8 | Cross-cutting concerns | optional | ✅ | ✅ (PRR) | ✅ |
| 9 | Decision-ownership | — | — | — | ✅ |
| 10 | Open questions | optional | ✅ | ✅ | ✅ |
| 11 | Rollout / Migration plan | — | optional | ✅ | optional |
| 12 | Success metrics & SLAs | — | ✅ | ✅ | ✅ |
| 13 | Next steps | ✅ | ✅ | ✅ | ✅ |
| 14 | Decision log row (auto) | ✅ | ✅ | ✅ | ✅ |

---

## 0. Status header

**Purpose:** Make the doc usable as a durable artifact. Reviewers know if it's actionable.
**Failure mode:** Stale doc lingers as "Draft" forever; nobody trusts it as a source of truth.

Required fields: `Version`, `Author(s)`, `Last edited`, `Status` (Draft / In-Review / Accepted / Rejected / Superseded), `Approvers`, `Decision date` (when status flips).

## 1. Summary (BLUF)

**Purpose:** Reviewer knows in 30 seconds what decision is being requested.
**Failure mode:** Opens with background. Reader scrolls to find "what am I deciding."

The first paragraph names **the decision being requested** (or recorded). Not the problem. Not the background. The decision. Two sentences max for the decision itself; one paragraph total for full BLUF.

**Bad:** "We have a service X that does Y. It's been around for a while. Recently we noticed…"
**Good:** "We're proposing to migrate service X from MongoDB to Postgres by Q3 to reduce p99 latency below 200ms. Decision needed by 2026-05-15."

## 2. Context / Background

**Purpose:** Reviewers without your tribal knowledge can follow.
**Failure mode:** Either too short ("you should know this") or a wall of text covering 5 years of history.

Two paragraphs is the sweet spot. Link to deeper docs (the product plan, prior RFCs, prior incidents) rather than re-stating. For partner-mode, expand to assume zero shared mental model.

## 3. Glossary (partner-mode mandatory)

**Purpose:** Terminology drift kills cross-org docs faster than design errors.
**Failure mode:** "What's MAU?" "What's a containment rate?" derail the meeting.

Define every domain term you use, every acronym, every product name. Inline on first use is fine for short docs; a glossary block is mandatory for partner-mode.

## 4. Goals & Non-Goals

**Purpose:** Goals quantify success criteria; non-goals prevent scope-creep arguments later.
**Failure mode:** Buzzword goals ("scalable, reliable, modern"). No non-goals → every meeting becomes a scope debate.

**Goals must be quantified.** "Scalable" → "Handles 10× current peak with p95 ≤ 300ms." "Fast" → "User-perceived latency ≤ 1s for 95% of requests." See [non-goals.md](non-goals.md) for the quantification rules.

**Non-goals must be load-bearing.** Listing what you're explicitly *not* doing is half the value of the doc. Examples: "Multi-tenant isolation is out of scope (single-tenant only for v1)." "Full i18n is out of scope (Hebrew + English only)."

## 5. Proposal / Design

**Purpose:** The actual proposal. What you're going to build.
**Failure mode:** Implementation manual masquerading as a design doc — schema definitions, full API specs, function signatures. Save those for the code review.

Lead with an overview (1-2 paragraphs), then go into details *only for parts that are relevant to the design and its trade-offs*. If you find yourself copy-pasting interface definitions, stop — link to a separate API spec or to the source code.

For multi-component proposals, structure by component (4.1 Frontend / 4.2 Backend / 4.3 Database / 4.4 Models). Each component sub-section: 1-paragraph overview, key decisions, trade-offs called out explicitly.

## 6. Diagrams (C4 + sequence)

**Purpose:** A picture beats a slab of text for most readers.
**Failure mode:** Happy-path-only boxes-and-arrows. Implies false completeness.

Required minimum for standard+: one **C4 system context** diagram (boxes + arrows + external systems) and one **sequence diagram** for the critical flow (with retries, timeouts, failure paths). Mermaid in the markdown source — survives copy-paste into Google Docs and Notion. See [diagrams.md](diagrams.md).

## 7. Alternatives Considered

**Purpose:** Show you did the work. Reviewers know the road not taken.
**Failure mode:** Single option (you're asking permission, not designing). Weak strawmen (you're cheating).

**≥3 alternatives, scored on consistent axes.** Status quo, incremental, your proposal. Same axes for all three. Same downside-candor for all three. If you can't articulate why an alternative is *appealing*, you haven't taken it seriously. See [alternatives-considered.md](alternatives-considered.md).

## 8. Cross-cutting concerns

**Purpose:** Force a structured pass over the easy-to-forget axes.
**Failure mode:** Silently absent. "Oh, we forgot about observability" surfaces in week 6.

Run the checklist: security, privacy, observability, rollout/rollback, scalability, dependencies, failure modes, on-call. Mark explicit N/A with reason for anything skipped. See [cross-cutting-checklist.md](cross-cutting-checklist.md). Heavyweight upgrades this to the full Production Readiness Review questionnaire (~24 items).

## 9. Decision-ownership (partner-mode only)

**Purpose:** Across an org boundary, every decision needs an owner.
**Failure mode:** "We thought you owned that" surfaces as a blocker mid-build.

For each decision area, name the owner: *We own X / You own Y / Joint Z*. Format as a table. See [partner-mode.md](partner-mode.md).

## 10. Open questions

**Purpose:** Surface what's unresolved. Reviewers can answer them in the meeting.
**Failure mode:** Silent unresolveds → blocked work surfaces 3 weeks later.

Number them. Tag each with an owner ("for Northwind") or N/A if it's a parking-lot question.

## 11. Rollout / Migration plan

**Purpose:** Implementation plan: phases, feature flags, kill switches, dual-writes, backfills.
**Failure mode:** Approval treated as the finish line. No phasing → big-bang deploy → incident.

Required for heavyweight; optional for standard. Phases with success criteria for each. Kill switches and rollback paths. Owner per phase.

## 12. Success metrics & SLAs

**Purpose:** How you'll know it worked.
**Failure mode:** No metrics → no way to declare done; doc becomes folklore.

Quantified. Measurement plan (which dashboard, which logs, who watches). For SLAs: numbers (p95 ≤ Xms, error rate ≤ Y%, availability ≥ Z%) plus the consequence of breach (rollback? rate limit? page on-call?).

## 13. Next steps

**Purpose:** What happens after Accepted.
**Failure mode:** Doc rots in the "Accepted" pile because nobody knows what's next.

Concrete: who does what, by when. Linked follow-up RFCs/ADRs by ID. First milestone with date.

## 14. Decision log row (auto)

**Purpose:** The artifact that gets appended to the project's `DECISIONS.md`.
**Failure mode:** Skipped → no institutional memory → re-litigation in 6 months.

One row, machine-friendly format:
```
| 2026-05-03 | Migrate X to Postgres | Accepted | Shahar | drafts/design-postgres-migration-v2.md |
```

`scripts/append-decision-log.py` builds this for you.
