# Goals & Non-Goals: quantification rules

The Goals & Non-Goals section is the contract for the doc. Every later section refers back to it. Get this wrong and the rest of the doc is litigating fuzzy targets.

## The quantification rule

> Replace every adjective in a goal with a number. If you can't, the goal isn't a goal — it's a vibe.

| Adjective | Vibe | Goal |
|---|---|---|
| "Scalable" | ❌ | "Handles 10× current peak (~50K req/min) with p95 ≤ 300ms" |
| "Fast" | ❌ | "User-perceived latency ≤ 1s for 95% of requests" |
| "Reliable" | ❌ | "Availability ≥ 99.9% measured monthly; ≤ 5 critical incidents/year" |
| "Secure" | ❌ | "Passes OWASP Top 10 review; no PII in logs; auth via Acme JWT" |
| "Modern" | ❌ | (delete this goal — "modern" is never load-bearing) |
| "Low-cost" | ❌ | "Steady-state ≤ \$5K/mo at 10K MAU" |
| "Maintainable" | ❌ | "New engineer can land first PR within 5 working days" |
| "Cross-platform" | ❌ | "Runs on iOS 16+ and Android 13+ with the same RN codebase" |

## Goal shape

Each goal has 4 parts:

1. **What** — the outcome (not the implementation).
2. **Number** — quantified target.
3. **Measurement** — how you'll observe it (which metric, which dashboard, which test).
4. **Source** — why this number (benchmark, prior incident, competitor, business commitment).

**Example:**
> **G3. p95 user-perceived chat latency ≤ 1s.** Measured via the existing OpenTelemetry trace from RN ChatScreen → first-token-rendered. Source: prior dogfood feedback that >1.5s feels broken; industry research on conversational UI thresholds.

A goal without a measurement is unfalsifiable. A goal without a source is arbitrary.

## Non-goal shape

Non-goals prevent 80% of scope-creep arguments. They are *load-bearing*.

Each non-goal has 2 parts:

1. **What we're NOT doing.**
2. **Why** (so reviewers can challenge if they think it should be in scope).

**Examples:**
> **NG1. Multi-tenant isolation.** Out of scope for v1. Justification: Acme is a single-tenant deployment; we explicitly defer multi-tenancy to a future RFC.
>
> **NG2. Real-time collaboration in the agent.** Out of scope. Justification: single-user sessions only for the foreseeable future; multi-user collaboration is a different product.
>
> **NG3. On-device LLM inference.** Out of scope. Justification: GPT-5.5 quality is the locked target; on-device options don't reach it as of 2026-05.

## Common failure modes

| Failure | Looks like | Fix |
|---|---|---|
| **Buzzword goals** | "Scalable, flexible, reliable, modern" | Replace each with a quantified target or delete |
| **Implementation-as-goal** | "Use Postgres" | "p95 ≤ 200ms" — Postgres is the *means*, not the goal |
| **Goal without measurement** | "Latency improves" | "p95 latency ≤ 300ms measured by trace X" |
| **No non-goals** | Section just has goals | Add 3-7 non-goals; they're free scope-protection |
| **Non-goals without why** | "i18n: out of scope" | "i18n: out of scope. Hebrew + English only for v1; full i18n is RFC-XXX-future" |
| **Aspirational goals** | "Handles 1000× current peak" | Be honest: target what you'll actually build for, not what you wish you could build for |
| **Stretch goal in goal list** | "Goal: ≤ 100ms latency. Stretch: ≤ 50ms" | Stretch goals belong in Next Steps, not Goals — reviewers can't evaluate "stretch" |

## How many goals?

3-7 is the sweet spot. Past 7, reviewers can't hold them in working memory and the section becomes a wishlist. If you have more, the doc is probably trying to do two things — split it.

## How many non-goals?

3-10. Often more than goals because non-goals catch the things reviewers might *assume* are in scope. Read your draft as if you've never seen the project — what would you assume is in scope? List those as non-goals if they aren't.

## Quick test

After writing this section, hand it to someone who hasn't read the rest of the doc and ask: *"What is this project doing? What is it not doing? How will we know it succeeded?"* If they can answer all three from this section alone, it's right. If they can't, rewrite.
