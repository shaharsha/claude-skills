# Alternatives Considered: the highest-leverage section

This is the section reviewers learn the most from. It's also the section that fails most often, because writing weak alternatives is easier than writing strong ones — and the temptation to under-do it is constant.

## House rule: ≥3 alternatives, scored on consistent axes

Three is the floor:
1. **Status quo / do-nothing.** What if we don't do this?
2. **Incremental.** The smallest change that might work.
3. **Your proposal.** What you're recommending.

For non-trivial designs, add 1-2 more (a fourth alternative that's plausible but you reject; a fifth that's the "obvious" choice you considered first).

## What "consistent axes" means

Every alternative gets scored on the *same* axes. The axes are derived from your goals (Section 4) — if your goal is "p95 ≤ 300ms," then "expected latency" is an axis. Common axes:

- **Effort** (engineer-weeks)
- **Risk** (irreversibility, blast radius, learning curve)
- **Latency / throughput / cost** (the technical numbers your goals quantified)
- **Time-to-value** (when does this start paying off?)
- **Reversibility** (how hard is it to walk back?)
- **Dependencies** (does this require buy-in from another team?)
- **Operational burden** (on-call complexity, debuggability)

Pick 3-5 axes. Score every alternative on every one. If an axis only matters for one option, it's the wrong axis — drop it.

## The candor rule

> If you can't articulate why an alternative is *appealing*, you haven't taken it seriously.

Weak strawmen are nearly as bad as no alternatives. Reviewers can smell when you've stacked the deck. Each alternative should have at least one row where it *wins* an axis. If your proposal wins every row on every axis, your axes are wrong (or your proposal is so obviously right you don't need a doc).

## Format: scored table + per-alternative rationale

```markdown
### Alternatives matrix

| Axis | Status quo | Incremental (X) | Proposal (Y) | Alternative Z |
|---|---|---|---|---|
| Effort | 0 weeks | 2 weeks | 6 weeks | 10 weeks |
| p95 latency | 800ms (current) | 500ms | 200ms | 150ms |
| Reversibility | trivial | easy | medium | hard |
| Operational burden | low | low | medium | high |
| Time-to-value | n/a | 1 month | 3 months | 6 months |

### A1. Status quo
**What:** Keep the current architecture; don't migrate.
**Why appealing:** Zero effort, zero risk, zero new operational burden.
**Why we reject it:** p95 latency is the user-facing complaint; status quo doesn't move it. Goal G1 unmet.

### A2. Incremental — add a Redis cache layer
**What:** Layer a Redis cache in front of the existing MongoDB.
**Why appealing:** Small effort (~2 weeks), preserves existing schema and ops knowledge.
**Why we reject it:** Halves latency but doesn't hit goal (≤300ms). Cache invalidation adds operational complexity with limited upside.

### A3. Proposal — migrate to Postgres
**What:** [details — see Section 5]
**Why appealing:** Hits all three goals. Reuses team's existing Postgres operational knowledge from service Y.
**Trade-offs:** 6-week effort, irreversibility once data migrates, requires backfill plan.

### A4. Alternative — build a custom in-memory store
**What:** Replace MongoDB with a bespoke in-memory + WAL design.
**Why appealing:** Lowest possible latency (≤150ms), full control of schema and ops.
**Why we reject it:** 10+ weeks of engineering, irreversible, takes us into "we built our own database" territory which the team has explicitly avoided in past decisions [link to ADR-0008].
```

## Common failure modes

| Failure | Looks like | Fix |
|---|---|---|
| **Single-option doc** | Just "Proposal" with no alternatives | Always include status quo + one incremental |
| **Weak strawmen** | "Alternative B: rewrite in Rust 🤡" | Write each alternative as if its advocate is in the room |
| **Inconsistent axes** | Proposal scored on cost; alternative scored on "vibes" | Pick 3-5 axes upfront; score every alt on every axis |
| **No "why appealing"** | Just rejection reasons | One sentence on what makes each alt attractive — even the rejected ones |
| **Hidden criteria** | Reject alt without naming the axis | If you reject on "complexity," "complexity" must be in the matrix |
| **Status quo missing** | Goes straight to alternative designs | Always include "do nothing" — it's the only option that has zero new risk |

## Heuristic: how good are your alternatives?

After writing them, ask:
1. Could a thoughtful reviewer pick a different alternative based on what's written? If no, you've written stalking horses.
2. Is your reasoning falsifiable? "Postgres is faster" is not falsifiable; "Postgres has p95 ~200ms vs MongoDB ~800ms on equivalent benchmarks [link]" is.
3. If your goals shifted slightly, would a different alternative win? If yes, that's the right shape — it shows the choice is contingent on the *goals*, not on bias.

If all three pass, you've written a strong Alternatives Considered section.

## What to do when you genuinely don't have alternatives

Rare, but happens (e.g., regulatory requirement forces a specific approach). State this explicitly:
> "We considered alternatives X, Y, Z and rejected them upfront because of [regulation/contractual obligation/security mandate]. The remaining design space is small and we describe it below."

Then describe the small design space. *Do not* fabricate alternatives just to fill the section — reviewers can tell.
