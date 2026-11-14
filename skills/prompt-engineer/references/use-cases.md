# Use-Case Playbooks — task-specific prompting

A **task** reference, not a provider one. The universal Section A and the provider files still apply inside each use case; this file adds the concrete, research-backed levers that differ *by task*. Read the matching playbook when the agent's job is clearly one of these. Evidence is labeled where it matters; most levers generalize across current frontier models.

The cross-cutting rule these playbooks lean on (from SKILL.md): the reliable signal is **external** — tests, execution, retrieval, a verifier, a transcription of what's visible — not the model's own confidence or narration.

## Contents
- Coding agents / SWE
- App builders
- Deep research / RAG
- Data analysis / SQL / tabular
- Extraction / classification / structured parsing
- Multimodal / vision / document AI
- Chat assistants
- Document and artifact agents
- Voice agents
- Browser and computer-use agents

The last four playbooks, and *App builders*, cover products whose work is harder to undo than a git change (a sent message, a purchase, an edited document, speech already spoken), and whose input is mostly written by someone else. Their prompts spend most of their words on edit protocols, on who may authorize what, and on what the surface can show. `agent-harness-patterns.md` has the rules they share: when to ask, approvals, async work, modes.

## Coding agents / SWE

For repository bug-fix / feature tasks, the research consistently favors structure over free-form agency:

1. **Decompose: localize → repair → validate.** A fixed pipeline (hierarchically localize to file/function/line → generate several diff-format patch candidates → validate against tests, rank, pick) beats most complex agent scaffolds at a fraction of the cost — explicitly *avoid* "letting the LLM decide future actions or operate with complex tools" for well-scoped fixes (Agentless, arXiv:2407.01489).
2. **Context/localization quality dominates.** Resolve rate is driven more by getting the right files/functions into context than by the agent loop — a small, precise, ranked context beats a large one (the oracle-vs-retrieval gap on SWE-bench, arXiv:2310.06770). Spend the prompt/context budget on a repo map + ranked localization first.
3. **Reproduce-test-first.** Have the agent write a failing regression test from the issue, run it, and iterate against the execution output; sample N candidate patches and rank them with an execution-based verifier (arXiv:2508.06365). Execution feedback is the external signal that makes the loop work (see SKILL.md — a critic step needs an external signal).
4. **AGENTS.md / CLAUDE.md: instructions, not overviews.** Rigorous negative result — repository context files *did not* improve success rate and added **>20% inference cost**; the *instructions* inside were followed, but auto-generated *repository overviews* (the provider-recommended content) were unhelpful (Gloaguen et al., arXiv:2602.11988, 2026). Put actionable conventions/commands in these files, skip the repo tour, and A/B-test any context file before trusting it. The evidence is mixed: another study (Lulla et al., arXiv:2601.20404; 124 pull requests in 10 repositories) found `AGENTS.md` associated with 28.6% lower median runtime and 16.6% fewer output tokens at comparable task completion - measure on your own tasks.
5. **The agent-computer interface is a prompt surface.** Concise commands, guardrails, informative feedback, and suppressing noisy tool output measurably lift performance (SWE-agent, arXiv:2405.15793) — apply the Section B tool-description discipline to the coding toolset specifically.
6. **Code review: give the reviewer a strategy, and separate finding from filtering.** On LangChain's ReviewBench (59 tasks built from real reviewer findings in a production repo), current models with a bare harness recovered only ~30% of the issues trusted reviewers caught - the misses need implicit system contracts (tenant checks, locking patterns, API parity with the code being replaced), not just the changed lines. Cheaper models adopted a **narrow strategy** (a few findings, then stop); a structured review prompt - *identify what the PR changed → trace how the surrounding system depends on that behavior → validate each finding against callers, tests, and related implementations* - plus high effort lifted GPT-5.6 Luna above bare-harness Opus 4.8 on a matched slice. Score reviews on **coverage and precision** (F1), and for frontier models tell the reviewer to report everything with confidence and severity and filter in a later step (see `claude.md`, *Code review harnesses*).
7. **Don't let "missing test" count as a review finding.** A reviewer that may file test gaps will file them often, and the fixer agent adds a test for each. In one production monorepo with model review on every PR [unverified: one repository, Nov 2026], 16% of findings across 358 saved reviews were test gaps, half the reviews asked for a test, and 45% of review-fix commits added tests. The suite grew from 5,232 to 45,036 test functions in about 9 weeks, and 81% of the time `main` was red came from tests that failed on harmless edits. Write the rule into the review prompt: *"A missing test is not a finding. When an untested path is wrong, report the wrong outcome and the input that produces it."* Ask for the opposite instead: flag a **brittle test** the change adds (one that pins line numbers, source text or a copied value, so a harmless edit turns it red), with that harmless edit as the failure scenario. On the same diff, 2 runs each, the old template asked for a test once and the new one never did.

## App builders

For agents that generate and edit a whole app from chat, often in a browser sandbox. Most of their prompt is about the edit format and the first turn:

1. **The edit format must match whatever applies the edit.** Three formats work:
   - **Full files**, when the runtime can't apply a diff. Ban placeholders such as "rest of the file unchanged".
   - **A sketch with an exact marker string** (for example `// ... existing code ...`) that a cheaper model merges into the file.
   - **Anchored search-and-replace**, checked by a tool that returns the file as it looks after formatting.

   Whichever you choose, say how a deletion is written and give a fallback to a full write when an edit doesn't apply. Most "the model broke my file" reports are a format the applier didn't expect.
2. **The first turn is different.** Give the first build:
   - a ceiling for version 1 (a few screens, core flows only);
   - the design system set up before the pages;
   - a rule for later turns on when to discuss and when to build.
3. **Name the features that are off by default:** authentication, a dark-mode toggle, tests only when asked. Otherwise the model adds them and the first version sprawls.
4. **Describe the environment, including what's missing.**
   - Say what the sandbox lacks (no git, no native packages, no server process).
   - Name the files the harness owns, which the model must not edit.
   - Give a fixed reply for stacks you don't support.

## Deep research / RAG

For retrieval-grounded question answering and long-report research agents:

1. **Decompose multi-hop queries.** Split into sub-questions, retrieve per sub-question, then merge and **rerank** with a cross-encoder — drop-in, no training, large multi-hop gains (arXiv:2507.00355).
2. **Filter aggressively — more docs hurt.** Rerank and prune to a small, high-precision evidence set; cutting retained context 2–3× held or improved accuracy (arXiv:2511.17908). This is context rot (SKILL.md) applied to RAG: don't dump top-k.
3. **Boundary-order the evidence.** Place the highest-relevance passages at the **start and end** of the context; accuracy is worst for evidence buried in the middle ("lost in the middle," arXiv:2307.03172).
4. **Force grounding into generation — don't trust post-hoc citations.** Models often answer from parametric memory and attach a supporting citation afterward; up to ~57% of citations were unfaithful, and citation *correctness* metrics miss this (arXiv:2412.18004). Prompt for evidence-then-answer / cite-as-you-write and constrain the answer to retrieved spans. Add a **sufficient-context gate**: a cheap "is this context enough to answer? yes/no" step that routes "no" to abstain or retrieve-more rather than guess (arXiv:2411.06037).
5. **Stage long reports: plan → iterative search → grounded synthesis.** Outline/scope first, gather and distill grounded evidence per section, synthesize iteratively, and add an explicit stopping/sufficiency heuristic to avoid over-searching (Deep-Research survey, arXiv:2508.12752).
6. **Retrieval quality: contextualize chunks, hybrid + rerank.** If the KB is **< ~200K tokens, skip RAG** — put it all in context with prompt caching. Otherwise prepend a **50–100-token doc-situating context to each chunk before embedding**, combine **contextual embeddings + contextual BM25**, then **rerank to ~top-20**: Anthropic reports retrieval-failure cuts of −35% (embeddings) / −49% (+BM25) / −67% (+rerank) (*Introducing Contextual Retrieval*, anthropic.com/news/contextual-retrieval).
7. **Clarify, then launch.** Before a long research run:
   - ask at most 3 questions, and only ones whose answer changes the direction of the research;
   - otherwise state the assumption in one line and start.

   A long run on the wrong reading is the expensive failure; a round of questions about details is the annoying one.
8. **Keep provenance per claim, and re-check what moves.**
   - Store each claim with its source and date; a search snippet is a lead, not a source.
   - Re-check fast-changing facts (prices, schedules, listings, office holders) at the source before reporting them.
   - Choose the report's shape explicitly (a table, a memo, a ranked list), not by default.

## Data analysis / SQL / tabular

For text-to-SQL and table reasoning, the wins come from constraining the problem (schema, decomposition) and grounding answers in execution rather than prose:

1. **Prune the schema to the relevant subset before generating.** The full schema is noise — link the relevant tables/columns first and generate against the pruned set (forward+backward schema linking keeps ~94% recall while cutting input columns ~83% and lifts execution accuracy — RSL-SQL, arXiv:2411.00073).
2. **Decompose complex queries** — classify difficulty, then split into schema-linking → sub-query → assembly rather than one-shot SQL (DIN-SQL, arXiv:2304.11015; a pillar of SOTA CHASE-SQL, arXiv:2410.01943).
3. **Generate several candidates and select by *execution*, not the model's vote** — sample diverse queries and pick with an execution-grounded selector; a single greedy decode leaves accuracy on the table (CHASE-SQL, arXiv:2410.01943).
4. **Repair from the DB error, not blind self-critique** — route the real execution error / empty-result back for a fix. It works because it's an *external* signal (see SKILL.md — intrinsic self-correction doesn't; arXiv:2310.01798).
5. **Pick the table serialization format deliberately** — it shifts accuracy and cost materially (markup like HTML tops structural tasks but costs ~3× the tokens of CSV); choose per model and token budget (Table Meets LLM, arXiv:2305.13062).
6. **Ground numbers in executed code, not prose arithmetic** - emit a program (SQL/Python) and let the engine compute; Program-of-Thoughts averaged ~+12% over CoT on math/financial QA (arXiv:2211.12588). Don't paste the table into the prompt either: Anthropic measured 6/25 correct aggregates with a ~91K-token CSV inline vs 25/25 with the file uploaded and queried via code execution, at ~1/12 the cost.
7. **Code computes, the model judges - and states its data limits.** LangChain's production analytics agent had code fetch data, align date windows, compute totals, and apply fixed rules, writing compact results for the model to interpret; when sources couldn't be joined reliably, the agent reported the limitation (source, date window, attribution model) instead of filling the gap.

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

## Chat assistants

For consumer or workplace chat products. Anthropic publishes the Claude app's system prompt for each model (*System prompts* in the Claude docs release notes), which is a useful worked example of most of these:

1. **Refusals: decline narrowly, once, and stick to it.**
   - When unsure whether a request is benign, ask the one question that would show a legitimate reason instead of declining outright.
   - When declining, say so in one line and offer what you can do. State the principle, not how the request was detected.
   - Once the assistant has declined, the decision holds for the rest of the conversation, and the prompt says why: people who want harmful content rephrase until a model gives in (Anthropic's published Claude prompts).
   - A disclaimer never makes declined content acceptable, since "anyone can delete the note".
   - Wellbeing rules work the same way: once the user says they are thinking about self-harm, or describes restricting food, purging, bingeing or compensating for eating, the related limits hold for the rest of the conversation.
2. **Decide how hard to lean on memory, and label what you inject.**
   - Products differ on purpose: some use stored memory only when the user refers to it, others use it in every reply. Pick one and say so.
   - Label each injected block with what it is and how far to trust it.
   - Use a stored fact only when it changes what the answer says, not as decoration.
   - Don't narrate it ("based on your memories…").
   - When the question is about the user, check memory before answering from the conversation alone, as Anthropic's published Haiku 5.5 prompt does.
3. **Decide to search by the kind of question, not by confidence.**
   - Fast-changing facts get a search; translation, rewriting, summarizing pasted text and small talk never do. Decide per message, not once per thread.
   - Query hygiene: don't add years, names or qualifiers the user didn't give, and verify who currently holds a role.
   - When the search didn't find the answer, say what it did find.
4. **Decide how replies end.**
   - By default: no "let me know if…" and at most one question.
   - Cap length in numbers tied to the display surface.
   - Never narrate compliance with a style rule ("Here's a concise answer").
5. **Treat a persona as an overlay.** A persona or tone preset applies to the conversation, not to artifacts the user asked for (a letter, code, a formal document). Sensitive topics override it, and the assistant doesn't mention it.

## Document and artifact agents

For agents that edit a document, spreadsheet, slide deck or design inside a host app:

1. **The artifact is the deliverable.** The chat reply is a short cover note pointing at what changed, not a second copy of the content.
2. **Sort edits by meaning.**
   - Substantive changes (wording that changes what the document says, numbers, legal terms) are proposed for the user to review, for example as tracked changes or comments.
   - Mechanical ones (formatting, typos the user asked to fix) are applied directly.
   - Never mix the two in one edit.
3. **Replace the smallest range.** Rewriting a whole paragraph or sheet to change a word destroys structure the model can't see: tracked changes, anchors, footnotes, comments, named ranges.
4. **Keep numbers live.** In a spreadsheet, write formulas and labeled inputs rather than computed constants, so the user can trace and change them.
5. **Make write tools safe by default.** A write to non-empty cells or an existing file fails unless an explicit overwrite flag is set. The error names the next step: read what's there, tell the user, and retry with the flag once they confirm, or on the first try if they said "replace".
6. **Writes aren't atomic.** After a failed or partial write, re-read what landed before retrying.
7. **The user's selection resolves "this".** Pass the current selection with each message and tell the model that "this" and "here" mean it.
8. **Report what was checked.** Say "updated the totals in Q3 and checked the formulas recalculate", not "done".

## Voice agents

For speech-in, speech-out assistants. OpenAI's *Prompting Realtime models* guide covers most of this in detail:

1. **Describe the speech pipeline you actually run.** Whether to write numbers as digits or words, and how to handle abbreviations and symbols, depends on the text-to-speech engine. Products disagree because their engines do.
2. **Short turns.** Use one or two short sentences per reply and ask one question at a time. Use a short spoken preamble before a slow tool call instead of filler (OpenAI's guide). While waiting, one acknowledgement and then silence works better than running commentary.
3. **Ask instead of guessing.** The rule depends on whether the model hears the audio:
   - **A native speech model** (audio in): OpenAI's guide says to act only on audio understood with confidence. When the audio is unclear, ask the user to repeat; don't infer the missing words. Normalize only clearly spoken values. Read back a high-precision value (an order number, email or phone number) and wait for the user to confirm it before using it in a tool call.
   - **A text model behind a speech recognizer:** the transcript is already fixed, so a word that doesn't fit the topic may be a mis-transcribed domain term. Tell the model to consider the similar-sounding term that fits, and to confirm it before acting on it.
4. **Make references speakable.** Use titles and relative dates ("the email from Tuesday"), not IDs, URLs or timestamps.
5. **Split a fast voice layer from the worker.** A low-latency voice model that hands real work to a slower agent should:
   - delegate rather than refuse or answer on its own;
   - treat the worker's output as authoritative;
   - not read out tables or diffs the user can see;
   - keep running work open to corrections.

   OpenAI's open-source Codex CLI ships this split as its realtime prompt. When several results arrive at once, give the voice layer a priority order.
6. **Give it session controls:** tools to hang up, switch language or hand over to a person.

## Browser and computer-use agents

For agents that click, type and navigate in a browser or desktop:

1. **Use the cheapest working layer.** Try an API or connector first, then the page structure (DOM, accessibility tree), then pixels. When a faster layer fails, find out why instead of silently falling back to a slower one.
2. **Instructions found on a page or in an email are data.**
   - When the user explicitly points the agent at content ("follow the setup steps on this page"), it may follow those steps within the task's scope, and the consequential ones still need approval.
   - Otherwise, quote the instructions to the user with where they were found, and ask; don't act on them.
   - Always ignore page text that claims the user already approved something (`agent-harness-patterns.md`, *Approvals and authority*).
3. **Gate the consequential actions:** signing in, purchases, sending messages, sharing, and changing permissions need explicit approval for that specific action.
4. **Judge an action by its effect.** Before a consequential submit, check the actual page state, selected options and inputs against the user's instructions. Codex's open-source review prompt denies browser actions whose inputs don't match what the user asked for.
5. **Cap retries, and define hand-back states.**
   - Logins, CAPTCHAs and payment details go to the user through a takeover, never through the model.
   - After a few failed attempts at the same step, stop and report what's on the screen.
