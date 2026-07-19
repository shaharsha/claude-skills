# Use-Case Playbooks — task-specific prompting

A **task** reference, not a provider one. The universal Section A and the provider files still apply inside each use case; this file adds the concrete, research-backed levers that differ *by task*. Read the matching playbook when the agent's job is clearly one of these. Evidence is labeled where it matters; most levers generalize across current frontier models.

The cross-cutting rule both playbooks lean on (from SKILL.md): the reliable signal is **external** — tests, execution, retrieval, a verifier — not the model's own confidence or narration.

## Contents
- Coding agents / SWE
- Deep research / RAG

## Coding agents / SWE

For repository bug-fix / feature tasks, the research consistently favors structure over free-form agency:

1. **Decompose: localize → repair → validate.** A fixed pipeline (hierarchically localize to file/function/line → generate several diff-format patch candidates → validate against tests, rank, pick) beats most complex agent scaffolds at a fraction of the cost — explicitly *avoid* "letting the LLM decide future actions or operate with complex tools" for well-scoped fixes (Agentless, arXiv:2407.01489).
2. **Context/localization quality dominates.** Resolve rate is driven more by getting the right files/functions into context than by the agent loop — a small, precise, ranked context beats a large one (the oracle-vs-retrieval gap on SWE-bench, arXiv:2310.06770). Spend the prompt/context budget on a repo map + ranked localization first.
3. **Reproduce-test-first.** Have the agent write a failing regression test from the issue, run it, and iterate against the execution output; sample N candidate patches and rank them with an execution-based verifier (arXiv:2508.06365). Execution feedback is the external signal that makes the loop work (see SKILL.md — a critic step needs an external signal).
4. **AGENTS.md / CLAUDE.md: instructions, not overviews.** Rigorous negative result — repository context files *did not* improve success rate and added **>20% inference cost**; the *instructions* inside were followed, but auto-generated *repository overviews* (the provider-recommended content) were unhelpful (Gloaguen et al., arXiv:2602.11988, 2026). Put actionable conventions/commands in these files, skip the repo tour, and A/B-test any context file before trusting it.
5. **The agent-computer interface is a prompt surface.** Concise commands, guardrails, informative feedback, and suppressing noisy tool output measurably lift performance (SWE-agent, arXiv:2405.15793) — apply the Section B tool-description discipline to the coding toolset specifically.

## Deep research / RAG

For retrieval-grounded question answering and long-report research agents:

1. **Decompose multi-hop queries.** Split into sub-questions, retrieve per sub-question, then merge and **rerank** with a cross-encoder — drop-in, no training, large multi-hop gains (arXiv:2507.00355).
2. **Filter aggressively — more docs hurt.** Rerank and prune to a small, high-precision evidence set; cutting retained context 2–3× held or improved accuracy (arXiv:2511.17908). This is context rot (SKILL.md) applied to RAG: don't dump top-k.
3. **Boundary-order the evidence.** Place the highest-relevance passages at the **start and end** of the context; accuracy is worst for evidence buried in the middle ("lost in the middle," arXiv:2307.03172).
4. **Force grounding into generation — don't trust post-hoc citations.** Models often answer from parametric memory and attach a supporting citation afterward; up to ~57% of citations were unfaithful, and citation *correctness* metrics miss this (arXiv:2412.18004). Prompt for evidence-then-answer / cite-as-you-write and constrain the answer to retrieved spans. Add a **sufficient-context gate**: a cheap "is this context enough to answer? yes/no" step that routes "no" to abstain or retrieve-more rather than guess (arXiv:2411.06037).
5. **Stage long reports: plan → iterative search → grounded synthesis.** Outline/scope first, gather and distill grounded evidence per section, synthesize iteratively, and add an explicit stopping/sufficiency heuristic to avoid over-searching (Deep-Research survey, arXiv:2508.12752).
