# Anti-patterns: 9 killers from the literature

These are the patterns that consistently kill design docs in review, distilled from Bhatti's "How Not to Write a Design Document," Slatton's "Writing a good design document," and observations across Google/Amazon/Stripe/Uber. Each anti-pattern below has a one-sentence symptom + a rewrite example.

The audit script flags 6 of these. The other 3 are judgment calls you have to catch yourself.

## 1. Solution-first / "Move to X" framing

**Symptom:** Title or summary names the *answer*, not the *problem*.

**Bad:**
> "Migrate from MongoDB to Postgres"

**Good:**
> "Reduce p99 chat-history query latency below 200ms"

If the title pre-commits to an answer, reviewers can't engage with the alternatives section honestly — they're just rubber-stamping. Frame the doc around the *problem*; the proposal can be "migrate to Postgres" *in the body*.

## 2. Buzzword goals

**Symptom:** Goals like "scalable, flexible, reliable, modern" without numbers.

**Bad:**
> "Goals: Build a scalable, modern, secure architecture for the agent."

**Good:**
> "Goals: (G1) Handle 10× current chat volume with p95 ≤ 300ms. (G2) Pass OWASP Top 10 review with zero criticals. (G3) Each goal measured via [dashboard X / penetration test Y]."

Replace every adjective with a number. "Modern" is never load-bearing. See [non-goals.md](non-goals.md).

*The audit script flags any of these adjectives used without a quantified neighbor: scalable, flexible, reliable, modern, fast, low-cost, secure, robust, simple, elegant.*

## 3. No current-state analysis

**Symptom:** Existing system is treated as "embarrassing" or skipped entirely.

**Bad:**
> "We need to redesign the auth system." [no description of what auth system exists today]

**Good:**
> "Today, auth is handled by [specific scheme] — JWT issued by Acme Node backend, validated client-side. Strengths: low operational burden. Weaknesses: token rotation requires app redeploy. The proposal addresses the rotation weakness while preserving the validation flow…"

Without current-state analysis, reviewers can't judge proportionality. They don't know if your proposal is overkill or underkill.

## 4. Single-option alternatives (or weak strawmen)

**Symptom:** Alternatives section has only your proposal, or has 2 strawmen so weak they barely deserve to be considered.

**Bad:**
> "Alternatives considered:
> A. Do nothing. Rejected: doesn't meet goals.
> B. Use a different DB. Rejected: too much work."

**Good:** ≥3 alternatives, each with a real "why appealing" line, scored on consistent axes. See [alternatives-considered.md](alternatives-considered.md).

If you can't articulate why an alternative is *appealing*, you haven't taken it seriously. Reviewers can smell a stacked deck and they will reject the doc on those grounds even if your proposal is correct.

## 5. Architecture diagrams without behavior

**Symptom:** Boxes connected by arrows; no retries, timeouts, queues, failure paths, observability.

**Bad:**
```
[ App ]  →  [ API ]  →  [ DB ]
```

**Good:** Sequence diagram with retry/timeout annotations, alt blocks for failure paths, labeled arrows with protocol + auth scheme. See [diagrams.md](diagrams.md#sequence-diagrams--the-highest-value-diagram).

A happy-path-only diagram is *worse* than no diagram because it implies false completeness. Reviewers skip the "what if X is down" question.

## 6. Implementation manual masquerading as design doc

**Symptom:** Schemas, full API specs, function signatures, database column types.

> Google's heuristic: *"If a doc basically says 'this is how we are going to implement it'… it would probably have been a better idea to write the actual program right away."*

**Bad:**
> "The new endpoint accepts POST /v1/sessions with body { user_id: string (UUID v4), name: string (max 64 chars), … } returning { session_id: string, created_at: string (ISO 8601), … }"

**Good:**
> "The new endpoint POSTs a session create request and returns a session ID. See [api-spec.md] for the full contract. The design choice that matters is: sessions are server-generated IDs (not client-supplied) so we can trace abuse [reasons]."

Save schema-level detail for the OpenAPI spec or the code review. The design doc's job is to surface the *decisions* (server-generated vs client-supplied IDs) and the *trade-offs* — not to be a substitute for documentation.

## 7. Approval-as-finish-line (no rollout / next steps)

**Symptom:** Doc ends with "Once approved, we'll start." No phases, no milestones, no metrics.

**Bad:**
> "Conclusion: We propose X. Pending approval, we'll begin implementation."

**Good:**
> "Next steps: (1) Sign off on this doc by 2026-05-15. (2) Phase 1 (dual-write) by 2026-06-01. (3) Phase 2 (cutover) by 2026-06-15. (4) Phase 3 (decommission old) by 2026-07-01. Owners: [author] (1-3), Jordan (4). Success measured via dashboard [link] — p95 ≤ 200ms by 2026-07-01."

Approval is the start, not the finish. Every Accepted doc generates concrete follow-ups.

## 8. Spaghetti structure (Slatton)

**Symptom:** Each paragraph weaves multiple ideas; readers untangle prose like spaghetti code.

**Bad:**
> "We considered Postgres but it has connection pooling issues although those are mitigatable with PgBouncer however that adds operational burden which is why we also evaluated MongoDB which has different consistency semantics…"

**Good:**
> "Postgres is the front-runner. **Pros:** [bullet list]. **Cons:** [bullet list, including connection pooling]. **Mitigation:** PgBouncer (operational burden noted in §X)."

Each paragraph should be one compressible idea. Bullet lists, headings, and tables exist for a reason — use them.

## 9. Surprise objections

**Symptom:** A thoughtful reviewer raises an objection the author hadn't considered. Half the meeting derails.

**Fix:** Pre-mortem your own doc before distribution. Read it adversarially. Anything a reviewer might say:
- "What if X is down?" → answer in cross-cutting / failure modes.
- "What about the existing system Y?" → answer in current-state analysis.
- "Did you consider Z?" → answer in alternatives.
- "What's the rollback?" → answer in rollout.
- "How will we know it worked?" → answer in success metrics.

If a reviewer surfaces an objection in the meeting, that's a doc bug. Note it, address it in v2, and re-distribute.

## Quick audit checklist

Before distributing, sanity-check against these 9:

| Anti-pattern | Quick check |
|---|---|
| 1. Solution-first | Is the title a problem or an answer? |
| 2. Buzzword goals | Are all goals quantified? |
| 3. No current-state | Is there a paragraph on "what we have today"? |
| 4. Weak alternatives | ≥3 alternatives, each with "why appealing"? |
| 5. Behavior-less diagrams | Are retries/failures shown? |
| 6. Implementation manual | Are schemas saved for the API spec? |
| 7. Approval-as-finish | Are next steps concrete with dates? |
| 8. Spaghetti prose | Are sections short, with bullets/tables where they help? |
| 9. Surprise objections | Have you read adversarially? |

The audit script (`scripts/audit-doc.py`) automates checks 1, 2, 4, 5, 6, 7. Checks 3, 8, 9 are judgment calls you have to make.

## Sources

- Shahzad Bhatti, "How Not to Write a Design Document" — 24 anti-patterns. ([weblog.plexobject.com/archives/7459](https://weblog.plexobject.com/archives/7459))
- Grant Slatton, "Writing a good design document." ([grantslatton.com/how-to-design-document](https://grantslatton.com/how-to-design-document))
- "Design Docs at Google" — Industrial Empathy. ([industrialempathy.com](https://www.industrialempathy.com/posts/design-docs-at-google/))
