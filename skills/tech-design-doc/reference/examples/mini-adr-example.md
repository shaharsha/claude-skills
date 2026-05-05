# ADR-0042: Use sentence-transformers for first-pass embedding

| Field | Value |
|---|---|
| Status | Accepted |
| Author | Shahar Shavit |
| Created | 2026-05-12 |
| Last edited | 2026-05-12 |
| Decision date | 2026-05-12 |
| Approvers | Jordan (Acme), Shahar |

## Context

The example agent's RAG knowledge layer needs an embedding model. We have three real options: (a) Azure AI Foundry's hosted embedding endpoint (`text-embedding-3-large`, ~\$0.13/1M tokens), (b) sentence-transformers running in-process (no per-call cost, ~250ms for ~50 docs), (c) bring up a dedicated embedding service. We've been informally using option (a) in the dev environment for ~1 week.

The cost of option (a) at projected MVP volume is ~\$30/month — small but per-query. Option (b) adds ~150MB to the container image but no per-query cost. Option (c) is overkill for MVP.

The decision affects only the FastAPI service; no other team is impacted. Reversible in <1 day if we change our mind.

## Decision

We will use **sentence-transformers (all-MiniLM-L6-v2)** in-process for the first-pass embedding in MVP. We will revisit if quality measurements during the pilot show a meaningful gap to `text-embedding-3-large`.

## Consequences

**Positive:**
- Zero per-query cost on the embedding path.
- No external dependency — works offline in dev, no network failure to handle.
- ~150MB image size addition is acceptable for our deployment (Container Apps can pull warm-cache).

**Negative:**
- ~768-dim vs 3072-dim — lower theoretical ceiling on retrieval quality.
- Extra warm-up time on cold start (~1.5s to load the model).

**Neutral:**
- Adds `sentence-transformers` as a Python dependency.

## Alternatives considered

- **Azure Foundry `text-embedding-3-large`:** Higher quality ceiling, ~\$30/month MVP cost, network-dependent. Rejected as default but kept as a fallback we can swap to if pilot quality measurements show a gap.
- **Dedicated embedding service:** Overkill for MVP volume. Reconsider at year-1 scale if we have multiple consumers.
- **Use cached embeddings only (no live inference):** Doesn't work — knowledge corpus changes (new policy PDFs added) and we need to re-embed on the fly.

---

## Decision log row

```
| 2026-05-12 | Use sentence-transformers for first-pass embedding | Accepted | Shahar Shavit | drafts/adr-0042-sentence-transformers.md |
```
