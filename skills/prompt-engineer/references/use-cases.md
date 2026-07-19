# Use-Case Playbooks — task-specific prompting

A **task** reference, not a provider one. The universal Section A and the provider files still apply inside each use case; this file adds the concrete, research-backed levers that differ *by task*. Read the matching playbook when the agent's job is clearly one of these. Evidence is labeled where it matters; most levers generalize across current frontier models.

The cross-cutting rule these playbooks lean on (from SKILL.md): the reliable signal is **external** — tests, execution, retrieval, a verifier, a transcription of what's visible — not the model's own confidence or narration.

## Contents
- Coding agents / SWE
- Deep research / RAG
- Data analysis / SQL / tabular
- Extraction / classification / structured parsing
- Multimodal / vision / document AI

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
6. **Retrieval quality: contextualize chunks, hybrid + rerank.** If the KB is **< ~200K tokens, skip RAG** — put it all in context with prompt caching. Otherwise prepend a **50–100-token doc-situating context to each chunk before embedding**, combine **contextual embeddings + contextual BM25**, then **rerank to ~top-20**: Anthropic reports retrieval-failure cuts of −35% (embeddings) / −49% (+BM25) / −67% (+rerank) (*Introducing Contextual Retrieval*, anthropic.com/news/contextual-retrieval).

## Data analysis / SQL / tabular

For text-to-SQL and table reasoning, the wins come from constraining the problem (schema, decomposition) and grounding answers in execution rather than prose:

1. **Prune the schema to the relevant subset before generating.** The full schema is noise — link the relevant tables/columns first and generate against the pruned set (forward+backward schema linking keeps ~94% recall while cutting input columns ~83% and lifts execution accuracy — RSL-SQL, arXiv:2411.00073).
2. **Decompose complex queries** — classify difficulty, then split into schema-linking → sub-query → assembly rather than one-shot SQL (DIN-SQL, arXiv:2304.11015; a pillar of SOTA CHASE-SQL, arXiv:2410.01943).
3. **Generate several candidates and select by *execution*, not the model's vote** — sample diverse queries and pick with an execution-grounded selector; a single greedy decode leaves accuracy on the table (CHASE-SQL, arXiv:2410.01943).
4. **Repair from the DB error, not blind self-critique** — route the real execution error / empty-result back for a fix. It works because it's an *external* signal (see SKILL.md — intrinsic self-correction doesn't; arXiv:2310.01798).
5. **Pick the table serialization format deliberately** — it shifts accuracy and cost materially (markup like HTML tops structural tasks but costs ~3× the tokens of CSV); choose per model and token budget (Table Meets LLM, arXiv:2305.13062).
6. **Ground numbers in executed code, not prose arithmetic** — emit a program (SQL/Python) and let the engine compute; Program-of-Thoughts averaged ~+12% over CoT on math/financial QA (arXiv:2211.12588).

## Extraction / classification / structured parsing

For pulling fields, labels, and records out of text, the levers are schema shape, when to constrain, and when to refuse:

1. **Reason before the value.** Put a `reasoning`/`evidence_quote` field *ahead* of each extracted value — an answer-first schema forces a commit before the reasoning exists (the universal rule in SKILL.md §A Output Format; "reason in NL, then serialize" recovers the loss — Let Me Speak Freely, arXiv:2408.02442).
2. **Constrain narrowly** — strict JSON/enum helps label selection but taxes free reasoning; keep hard constraints on the value/enum slot and leave the reasoning field unconstrained (arXiv:2408.02442).
3. **Force abstention — emit explicit `null` for missing fields.** When a value isn't in the source, models invent a plausible one; require "return null if not stated" and a real abstain path (conformal abstention gives a tunable hallucination-rate guarantee — arXiv:2405.01563).
4. **Treat the schema as an optimizable prompt surface** — field *descriptions* and *structure* drive reliability more than the extractor prompt; contextual field descriptions + flattened nesting give large gains, and a validation-retry cuts errors sharply (PARSE, arXiv:2510.08623).
5. **Many-shot for rare/hard classes** — scaling to dozens–hundreds of examples improves rare-label coverage and overrides pretraining label priors (arXiv:2404.11018); long context + caching make it cheap. (Not for reasoning models — see SKILL.md.)
6. **Calibrate and threshold confidence** — elicited verbalized confidence beats raw logprobs on RLHF models (~50% lower calibration error); threshold it to defer low-confidence extractions to review (arXiv:2305.14975; and the P(True) note in SKILL.md).

## Multimodal / vision / document AI

Perception, not reasoning, is the dominant VLM failure mode — so make the model commit to what it *sees* before it answers:

1. **Transcribe the visible evidence first, then reason over the transcription.** Most VLM errors are misreads that longer reasoning can't fix (~87% of one strong model's visual-math errors were perception, not logic — arXiv:2605.20177); forcing it to enumerate values/labels/objects/text first lifts accuracy and makes a wrong answer diagnosable.
2. **Put the image *before* the text, and label every image.** Physically placing the image ahead of the question gives small consistent gains (a bare verbal "describe it first" can *hurt* — arXiv:2410.03062); with multiple images tag each in text ("Image 1: …"), since VLMs are order-sensitive and degrade on later-positioned images (arXiv:2410.16983). Task-dependent — test on your model.
3. **Ground spatial questions with marks, not words (Set-of-Mark).** Overlay numbered/boxed marks (or a coarse grid) on candidate regions and have the model answer by *mark ID* — unlocks zero-shot grounding that beat fine-tuned SOTA (arXiv:2310.11441). Prompt-only fallback: ask for bounding boxes / coordinates and name the region to attend to.
4. **Charts/figures/docs: extract to structured text first, then reason on the text.** Plot → linearized table, then reason over the table, beat a fine-tuned SOTA by +24 pts on ChartQA with one-shot prompting (DePlot, arXiv:2212.10505); one-pass "just answer the chart" misreads axes and drops datapoints. For documents, emit OCR text **plus reading order/layout** first.
5. **Cut hallucination: trust the image, keep outputs short and scoped.** Two tiny instructions — attend to the image, and when it conflicts with prior knowledge trust the image — reduce hallucination training-free (arXiv:2410.11701; re-test on the newest models); and object hallucinations cluster in the *later* part of long generations, so scope descriptions to "only what is visible" (LURE, arXiv:2310.00754). CoT can *worsen* VLM hallucination — use it carefully.
6. **Video: sample sparse, stamp frames with timestamps, ask "when."** Most long-video questions are answerable from 1–5 frames — locate them rather than dumping uniform frames (T*, CVPR 2025); overlay each sampled frame's timestamp and ask explicit "when did X happen?" queries so the model can localize temporally.
