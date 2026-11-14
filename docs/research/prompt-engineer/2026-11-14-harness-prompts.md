# Harness prompts research for prompt-engineer (2026-11-14)

This is the working record behind the agent-harness guidance added to the prompt-engineer skill in November 2026: what was read, what was found, which official sources back it, what the reviews corrected, and how the change tested. It is an archive for maintainers. The skill itself does not load it.

Where each rule in the skill came from, rule by rule, is in [`skills/prompt-engineer/SOURCES.md`](../../../skills/prompt-engineer/SOURCES.md).

Contents:
- Part 1: research notes from the collections
- Part 2: what the official sources say
- Part 3: review history
- Part 4: test rounds
- Part 5: a field report

The collections are unofficial copies of products' prompts. The notes below describe what those copies contained on the day they were read. They are not statements by the vendors. Quotation marks around a few words mark a phrase kept as a search anchor; longer passages are paraphrased.

# Part 1: research notes from the collections

Seven research passes read the collections by area, and each pass's key claims were spot-checked against the files. File and line references are to the collections at the commits in SOURCES.md.


Task: study four public collections of extracted harness prompts and learn from them for the prompt-engineer skill, without copying their text.

Collections read (commits and URLs are in `skills/prompt-engineer/SOURCES.md`): system_prompts_leaks (2,127 files), claude-code-system-prompts (1,218 files, changelog to v2.1.325), system-prompts-and-models-of-ai-tools (126 files, to 2026-10-12), CL4R1T4S (82 files, to 2026-11-09).

## Read myself (verified)

### Per-model variants of the same harness prompt (the strongest signal)
Claude Code ships one prompt per model; the files are ~430 KB each and differ by 21-71 lines (diff against claude-code-opus-5.5.md):
- Fable 5.2 (41 lines): a different effort-to-`<reasoning_effort>` mapping (low 8 / high 30 / xhigh 80 vs Opus 5.5's 5 / 15 / 40), `<thinking_mode>auto`, a model-identity paragraph, Anthropic's published *Finishing work* block, a note that Edit no longer needs a prior Read inside the working directory, and a *Memory, notes and feedback* block (save only applicable + durable things; don't overweight soft feedback; question old cautions but keep cautions about risky actions until a human confirms; don't write planning documents unless asked).
- Haiku 5.5 (71 lines): no effort table; a long "finish the task" block (effort changes thinking, not how much of the request to finish; ending the turn stops all work; ask first only when you can't name the most likely reading or the task depends on something only the user has; approval of a choice you could make yourself is not a reason to ask; ordering words like "plan, then build" are not stopping points; list your choices in the final message; finish the unblocked parts and lead with what's stuck); no EndConversation tool.
- ~~Tool routing differs by model~~ Corrected by agent 1: the Opus 5.5 capture was taken in auto mode (it carries a "While auto mode is active" block); Sonnet, Haiku and Fable carry the "avoid cat/head/sed" line. So the Bash-vs-dedicated-tool line follows the permission mode, not the model (one Opus capture, so not fully settled).
- Sonnet 5.5 vs Opus 5.5: 21 lines; Opus 5 vs Opus 5.5: 30 lines.
Lesson: the vendor keeps one shared prompt and adds small per-model deltas; the deltas are about finishing/stopping, memory hygiene, and tool routing - the behaviors that differ by model. The small model gets the most explicit autonomy text.

Codex (OpenAI) ships per-model files too: gpt-6.1-sol vs gpt-6.1-terra and gpt-6-astra differ by 4 lines (two style sentences: contrastive framing "X, not Y", apologies); gpt-6-luna and gpt-6-sol differ by ~190 lines, an older version of the prompt (personality, writing style, commentary channel, compaction rules).
Codex instruction sections: when to ask permission; autonomy and persistence ("can you..." = do it; don't settle for partial); personality and writing style (anti-slop word list, no contrastive framing, no needless apology); working with the user (commentary vs final channels; a new user message mid-task is steering, not a replacement; compaction does not end the task); intermediate commentary (start with a commentary message when tools are needed; no more than 60 s without an update; no questions in commentary); final answer (self-contained); explain why you need confirmation and where the requirement came from (SKILL.md, AGENTS.md, memory, auto-review).

### Antigravity (Gemini 4 Argon), CLI prompt
- Effort is set as prompt text in the system instruction (a line telling the model to think silently, followed by a numeric effort level of 0.20).
- XML-tagged sections (identity, artifacts, guidelines, communication_style, messaging, subagents, skills).
- It tells the model to ask for clarification when unsure of the user's intent instead of assuming - the opposite default from Claude Code and Codex.
- A hard sandbox rule: never defeat or bypass access controls, credentials, network restrictions or sandbox boundaries (incl. writing to the state a check reads, spoofing, probing local services); if sanctioned paths fail, report and stop.
- No-polling rule: the system wakes the agent when a subagent, background task or queued user message arrives.
- Subagent catalog entries say when to delegate and when not to (for quick, targeted lookups, do the research yourself).
- Skills: must read SKILL.md before proceeding, unless delegating to a subagent that will.

## Agent 1 - tool descriptions and subagent briefs (done; spot-checked)
Verified: SKILL.md:204 says "Full models: 3-4 sentences minimum"; SKILL.md:233 says Claude/GPT "Handles well natively" for error recovery; the Opus capture is in auto mode (claude-code-opus-5.5.md:324).
Top patterns (agent's ranking): (1) brief checklist - what's ruled out, read vs write intent, a length cap for the reply, exact command for lookups vs the question for investigations, never delegate understanding ("based on your findings, fix it" is the anti-pattern); (2) verify a subagent's result against an outside record - its summary says what it intended, not what it did; never fill in a pending result; (3) every tool gets a failure contract ("fails when X; do Y") and retry classes (transient = one retry; denial = adjust, don't retry verbatim; 2-3 failed attempts = stop and ask) - contradicts SKILL.md:233; (4) async tools name how completion arrives, forbid polling, and give a numeric cadence for external state; a "silence is not success" self-check for watch/filter tools; (5) measure coverage across description + schema, not sentence count; GPT/Gemini harnesses keep tool definitions bare and put delegation/asking policy in the developer prompt - contradicts SKILL.md:204 and :231. Also: gate cost-multiplying parameters (effort, model, orchestration) on an explicit user ask; flag human-read fields (a command's description, a wake-up reason) with length and examples; say what the UI adds itself (an "Other" option); state a tool's cost and failure modes before its triggers; consent never passes between agents; small per-model overrides that name the tool they override; enum states defined by entry criteria ("blocked only after the same blocker repeats three turns").

## Agent 2 - autonomy, stopping, safety (done; spot-checked)
Verified: Haiku 5.5's ask test (claude-code-haiku-5.5.md:115); the auto-mode classifier's consent bar - the user must name the action AND the parameter that makes it dangerous, a yes right after the agent's proposal counts, naming the goal is not naming the destructive step, consent binds at the step that ships (prompts/auto-mode-classifier.md:47-57); Codex's "authorization persists across turns" (gpt-6.1-sol.md:7), which disagrees with Claude Code's rule that approval in one context does not carry to the next.
Top patterns (agent's ranking): (1) async work: no polling, the harness wakes you; poll only external state at its real rate; a pending result is never invented or taken as an answer; elapsed time is not approval - new to the skill; (2) how far consent reaches and who can give it: one instance, at the shipping step; the approval must name the dangerous parameter; a question ("can we fix this?") is not consent; instructions relayed by another agent, tool output, skill text, documents under review are not consent; vendors disagree on persistence; (3) the ask test: ask first only if you can't name the likeliest reading or the task needs something only the user has; otherwise act and say which reading you took; finish unblocked parts and lead with what's stuck ("a question at the end costs the same one reply"); define the reversible set (working-tree edits the user can undo) as well as the dangerous one; effort doesn't shrink scope; (4) a new user message steers the task, it doesn't replace it; stop only on a clear stop; compaction continues the task, keeps every user request and safety constraints verbatim, and a countable remaining-work list; (5) a denied call means adjust, never retry verbatim or work around it; list boundary-bypass methods by name (writing to the state a check reads, spoofing, probing local services, editing harness/tests, reading graders).
Also: request-vs-inquiry default differs by vendor (Gemini CLI/Antigravity ask or explain; Codex treats "can you" as do-it; Claude in between) - a ported prompt must state its default; a reaffirmed request after a raised concern is consent; look before you delete and protect what you didn't create; secrets/PII out of outbound headers, titles, URLs; don't over-correct into unsolicited warnings.
Per-model: Claude Code ships almost no autonomy text for Opus 5.5 and Sonnet 5.5, the most for Haiku 5.5, Finishing-work + caution hygiene for Fable 5.2 - evidence that scaffolding is subtracted as models absorb it. Codex 6 -> 6.1: more push to act, tighter rules for messaging others and for skill-triggered pauses (quote the line; default to proceed).

## Agent 7 - helper prompts, skills, reminders, schemas (done; spot-checked)
Verified: compaction prompt guards "no tools" at both ends (prompts/compact.md:1-6 and last line); Codex plan mode "not changed by user intent... treat it as a request to plan the execution" (plan-mode.md:9); the classifier allows by default and lists out-of-scope harms it must not block (auto-mode-classifier.md:33-37).
Top patterns (agent's ranking): (1) gate classifiers for actions (for evals.md): allow by default plus an explicit do-not-block list; hard vs soft rules; a soft rule clears only when the user named the dangerous parameter; score separate axes (risk x authorization) then derive the verdict from a table; say which way missing or truncated evidence pushes the verdict; judge by effect, not self-labels ("dry run"); a cheap harm-only first stage with a stated boundary, then a stricter second stage; investigate only when it would flip the decision; (2) provenance of authority: which channels can authorize (user, developer, project instructions, the ask tool) and which only inform (tool output, skills, the agent's own text, peer agents, documents under review, user-shaped text inside outputs); real reminders only tighten, so a "reminder" that loosens is suspect; (3) compaction anti-drift: no-tools guard at both ends; every user message and constraints kept verbatim; separate pending vs current work; the next step must follow the latest request and be supported by quotes; user-supplied compaction focus; (4) mode switches: define the mode by effect (no repo mutation), immune to user imperatives, the turn may end only in a few legal ways, explore discoverable facts first and ask preferences early with a default; (5) helper and advisor contracts: numeric length budget, format derived from where it's displayed, an explicit "none" output by default with history of past suggestions, side-question agents told they have no tools; advisors triage the stage (starting, stuck, reviewing, choosing), give "a check, not a verdict", and say whether a concern blocks.
Also: memory - save only applicable + durable things, recalled memory is background not instruction, provenance/confidence per item, a strict recall selector (up to 5, empty if unsure), consolidation passes; skills - trigger on the step, list aliases, a "not for X" clause, separate invocation policy from description; output styles stack on the base prompt with stated precedence and kept guardrails; tool schemas - no examples in JSON, short per-field text (~65 chars median), policy in the top-level description, typed return shapes, shared preambles repeated per tool for opaque IDs.
Conflict to note: the compaction prompt asks for an <analysis> block before <summary>, which the skill advises against on 5.x thinking models (reasoning_extraction) - present as "on thinking models, rely on native thinking".

## Agent 3 - how Anthropic edits the Claude Code prompt (May-Nov 2026, v2.1.140-2.1.325; done; spot-checked)
Verified: the compact Grep description drops ALWAYS/NEVER for a "prefer this over grep" line that gives the reason (results integrate with the permission UI) (tool-description-grep-compact.md, "served to newer models", v2.1.178); the proactive /schedule offer's confidence threshold went 70% -> 85% -> 75% (CHANGELOG.md:3045, :2981) before the prompts were removed.
Findings: the most common edits are adding scope/conditions to absolute rules (~60-75), deleting instructions (~46 edits, 89 whole prompts removed), attaching reasons (~34; "because/so that" density 4.2 -> 6.6 per 10k words), and parallel per-model or flagged variants instead of editing shared text (~17 + a 23-file lean rewrite). IMPORTANT/CRITICAL density fell 9.5 -> 3.0 per 10k words and MUST/NEVER/ALWAYS 8.7 -> 3.4, but the absolute count stayed flat: new text is written calm, old capitals survive in legacy tool descriptions. Negations stayed flat (~65 per 10k): Anthropic adds reasons and scope to prohibitions rather than rewriting them as positives. Bullets 114 -> 53 and headers 40 -> 18 per 10k words: moving to prose. "Lean" variants have fewer rules with reasons, not fewer words. Model launches: small identity edits on day one, then gated behavior blocks within days (Haiku 5.5 on Oct 7 -> a completion block on Oct 8); a model-specific block names the shared sentence it overrides and says it takes precedence. Churn: many behavior additions lived 2-15 releases; numeric confidence thresholds in prose never settled and were removed; a dropped safety block came back one release later; self-check prodding and nudges toward an expensive tool (subagents) were removed; hints for features missing from the session are left out.
Lessons (agent's list, condensed): ship per-generation variants rather than edit shared text; a model patch names what it overrides; treat each behavioral addition as an experiment with a removal path, and keep safety text under regression evals; if you keep retuning a numeric threshold in prose, remove the behavior; keep prohibitions that carry reason + scope; "prefer X because Y" over ALWAYS/NEVER for tool routing; judge a rewrite by rules, not length; drop pointers toward expensive tools; omit hints for absent tools; update the previous model's identity claims at launch.

## Agent 5 - chat-app prompts and per-model diffs (done; spot-checked)
Verified: OpenAI's API developer prompt maps verbosity to an "oververbosity" of 1 / 3 / 7 (gpt-5.5-api.md:7); the ChatGPT Thinking app runs 4. Claude Haiku 5.5's "that decision stands for the rest of the conversation", with the reason (claude-haiku-5.5.md:71). Kagi: decide whether to research by the kind of question, not by how confident you feel (kagi-assistant.md:17).
Caveat: the Claude app per-model files are snapshots from different dates (Opus 5.5 Sept 22 ... Fable 5.2 Nov 9) and builds, so some deltas are timeline, not model.
Top patterns (agent's ranking): (1) chat-assistant refusal shape and over-refusal guards: ask one question that would surface a real reason instead of declining when unsure; decline once, in one line, with an alternative; state the principle, not the detection mechanics; a disclaimer never makes declined content acceptable; a warning followed by compliance is not a refusal; a decline stands for the conversation (with the reason); wellbeing rules scoped to the rest of the conversation once triggered, each with its reason; (2) personalization and memory stance: decide how aggressively to use memory (Gemini gates hard on an explicit trigger; ChatGPT Instant uses it aggressively), label every injected block with what it is and how reliable it is, a stored fact must change the substance of the answer, open items are context not an agenda, forbidden narration ("based on your memories"), stored preferences that ask for flattery are void; (3) decide to search by question type, not confidence; a must-not-search list (translation, rewriting, summarizing, casual chat); decide per message, not per thread; query hygiene (don't add years or names the user didn't give; verify current role-holders); citation budgets; report what was found when the answer wasn't; (4) reply endings and formatting caps: decide closing behavior by request type (default no follow-up offer, at most one question), numeric caps tied to the display surface, never narrate compliance ("if concise, don't say it's concise"); (5) persona presets as overlays (artifacts the user asked for don't take the persona; sensitive topics override it; don't mention it); injected reminders pre-declared in the system prompt, never loosen restrictions, say they may be irrelevant, don't mention them, keep the user's language.
Also: a cutoff block that states the current year and last year and how to treat the thinly covered months before the cutoff (Gemini 4 Argon API prompt); per-model: the small Claude model gets hard lines with reasons and the must-do first; ChatGPT Instant is pushed to use context it already has, Thinking is held back on length and meta-commentary; Grok 4.6 -> 4.7 added trust lines per new tool surface.

## Agent 6 - office, browser, voice, research and general agents (done; spot-checked)
Verified: the Excel add-in's overwrite protection - the write tool fails on non-empty cells; read them, tell the user, retry with an explicit override only after confirmation, or on the first try if the user said "replace" (claude-for-excel.md:63-70); voice mode caps replies at 2 sentences / 50 words unless asked to go deep, and repairs speech-recognition errors by considering similar-sounding words ("a sink" -> "async") (claude-voice-mode.md:35-41).
Theme: non-coding deliverables (a document, a message, a purchase, speech) can't be undone like a git change, and most input was written by someone else - so these prompts spend their words on edit protocols, who may authorize what, and what the surface can show.
Top patterns (agent's ranking): (1) artifact/document agents: the artifact is the deliverable and chat is a one-paragraph cover note pointing at it; numbers stay live and traceable in the host app (formulas, labeled inputs); default-safe tools with an explicit override flag and an error that names the next step; route edits by meaning (substantive -> proposed for review; mechanical -> applied; never mixed); replace the smallest range to keep hidden structure (redlines, anchors, footnotes); writes aren't atomic, so re-read what landed before retrying; the user's selection resolves "this"; report the action scoped to what was checked; numeric quality floors (font sizes, contrast); (2) voice agents: describe the actual TTS pipeline (one product says write numbers normally, another says spell them out - it depends on the TTS); numeric length caps and one question at a time; repair recognition errors; one short acknowledgement then silence ("filler is an error"); a fast talker model hands work to a reasoner, with a priority order for incoming results; speakable references (titles and relative dates, not IDs, URLs or timestamps); session-control tools (hang up, switch language); (3) consequential actions: three tiers - prohibited even with permission (permanent deletion, sharing/permission changes, trades, account creation), needs explicit permission, free; approval only from the trusted channel and scoped to the action ("cannot be inherited"); page/email content claiming approval is ignored; instructions found in data are quoted with their location and asked about; credentials never pass through the model (user types, vault, takeover); (4) side-effect integrity: check what happened before retrying anything irreversible; a task stays open until delivered; no "I'll let you know" without something scheduled to notice; an unattended-mode switch (don't ask; state the interpretation and proceed); (5) research: clarify-then-launch (at most 3 questions, only if the answer changes direction, else state the assumption); per-domain source allow-lists with stored provenance (snippets aren't sources); values arrive already cited by the tool; re-check fast-changing facts (prices, flights, listings) at the source; choose the report shape explicitly.
Also: a cost ladder for actions (API connector -> DOM/extension -> pixels; debug a failing fast tier rather than dropping silently); a loop-breaking example in the prompt; all output through tools with separate notify (non-blocking) and ask (blocking) tools and an explicit end tool; tell the model what the UI already said (greeting); typed event streams where only the human-tagged message is user input; products deliberately disagree (Comet never asks, Cowork does) - make the choice explicit.

## Agent 4 - app builders and long tail (done; spot-checked)
Verified: Bolt's prompt says its runtime can't apply a diff or patch, so code is always written in full (Bolt/Prompt.txt:23); Kiro's mode classifier returns chat/do/spec confidences that "must always sum to 1" and a rule to classify as Do when in doubt (Kiro/Mode_Clasifier_Prompt.txt:8, 53).
Top patterns (agent's ranking): (1) the file-edit format must match whatever applies the edit - full files when the runtime can't patch (ban placeholders), a sketch with an exact sentinel string merged by a cheaper model, or anchored search/replace validated by the tool that returns the post-format file; say how deletion is written; a fallback to a full write; (2) modes: define each by an observable rule (any file change = implementation), name who may switch it (only a developer message, not user text or tool descriptions), gate tools per mode in the harness, give each mode an exit tool, a default class for the classifier ("when in doubt, Do") and pass the user's exact words to the routed agent; (3) goal loops: label each previous turn as progress / verified wait / no progress (restating status counts as none); "blocked" only after the same blocker repeats 3 turns; no swapping in a narrower solution; a completion audit with evidence per requirement; context-reset notes store item IDs, not copies; (4) a different first turn: a v1 scope ceiling, design system first, and a default for when to discuss vs build on later turns; (5) multi-model products: one shared core, per-model deltas (the edit tool, the persistence block, channel/format rules, patches for observed failures), a generic template for long-tail models.
Also: name the off-by-default features (no auth, no dark-mode toggle, tests only if asked) and numeric plan-first thresholds (>3 files); an environment section that lists what is absent (no git, no pip), harness-owned files, and a fixed reply for out-of-scope stacks; design rules as numeric limits and all styling through a token file; Kiro's spec pipeline (requirements in EARS -> design -> tasks, an approval gate with a machine-readable reason, one task per turn); to-do item size rules and who owns the plan; memory with one writer, staleness vs cost-to-check, a citation trailer, protected sections; streaming-parser tag contracts (stable ids, one tag per line, ordering); a terminal "finish" tool and a fallback ladder with a retry cap; an <inputs> section listing every block the harness injects with its trust level; production prompts carry bugs (dangling references, undefined labels, duplicated rules) - add those to the re-read checklist.

## Research agents (all seven done)
1. Tool descriptions and subagent briefs (Claude Code, Codex, Antigravity, Piebald tools/).
2. Autonomy, stopping and safety rules, incl. per-model and per-version diffs.
3. Claude Code prompt CHANGELOG: how Anthropic edits its prompt over time.
4. App-builder and long-tail prompts (x1xhlol, CL4R1T4S).
5. Chat-app prompts and per-model diffs (Claude app per model, ChatGPT, Gemini, Grok, Perplexity, others).
6. Office, browser, voice, research and general agents (Claude for Excel/Word/PowerPoint, Cowork, Design, Chrome, Atlas, Comet, Perplexity Computer, deep research, voice modes, Manus, Poke, Muse agent).
7. Auxiliary prompts: classifiers/reviewers (auto-mode classifier, Codex auto-review), compaction and helper prompts, reminders, plan mode, advisor, memory, output styles, vendor skills, raw tool schemas.

# Part 2: what the official sources say

After the collection study, each pattern was checked for an official version. Labels S1 to S9 are this document's; SOURCES.md uses O1 to O9 for the same material plus the advisor-tool page.

S1. Anthropic, *How we built Claude Code auto mode* (anthropic.com/engineering/claude-code-auto-mode):
  - The action classifier sees only user messages and bare tool-call payloads. Assistant prose is stripped "so the agent can't talk the classifier into making a bad call", and tool results are stripped as the injection defense. Anthropic tested including them and performance dropped. A tool-calls-only variant lost the user-intent anchor.
  - Two stages. Stage 1 is a single-token filter that errs toward blocking (8.5% false-positive rate, FPR). Stage 2 uses the same prompt with only the final instruction changed, asking for reasoning (0.4% FPR), so it mostly reads from the cache.
  - The classifier judges real-world effect, not surface text: a payload written to a file and then run, commands chained with `&&`, a command assembled by a script.
  - Authorization means the user authorized this action, not just something related to their goal. "can we fix this?" is a question. "Clean up the PR" doesn't name a force-push. One approval isn't a pattern.
  - 17% false-negative rate on real overeager actions. Most misses saw the danger but misjudged whether consent covered the blast radius. "We've tried prompt-engineering around this and haven't found a fix that doesn't cost more than it gains."
  - Customizable slots: environment (the trust boundary), block rules, allow exceptions. Process: block rules, then exceptions, then user intent, then the decision.
  - Deny-and-continue: a denial returns as a tool result telling the agent to find a safer path and not route around the block. After 3 consecutive or 20 total denials, a human takes over (headless runs terminate).
  - Checks run at subagent delegation (can deny) and at return (warns only). An input-layer probe warns on injection-looking tool results.
S2. Anthropic tool docs:
  - define-tools: "Aim for at least 3-4 sentences per tool description, more if the tool is complex."
  - handle-tool-calls: write instructive errors that say what went wrong and what to try next (e.g. "Rate limit exceeded. Retry after 60 seconds."). "Claude will retry 2-3 times with corrections" on invalid or missing parameters.
S3. Anthropic's published Claude app system prompts (platform.claude.com/docs/en/release-notes/system-prompts/claude-haiku-5-5 and siblings):
  - Once Claude declines or voices concern, "that decision stands for the rest of the conversation", with the reason.
  - A disclaimer or "for educational purposes" note never makes declined content acceptable.
  - Wellbeing rules scoped to "the rest of the conversation" once triggered.
  - Haiku 5.5 checks its `<memory_listing>` when a question is about the person.
S4. OpenAI function-calling guide (developers.openai.com/api/docs/guides/function-calling):
  - Describe the purpose of the function and each parameter.
  - "Use the system prompt to describe when (and when not) to use each function."
  - For deferred tools, detail goes in the function description and the namespace description stays short.
  - Examples may hurt reasoning models.
S5. OpenAI *Using GPT-6* / GPT-6 Astra guide (latest-model pages):
  - Async tool calling (`async: true`) and mid-turn steering.
  - "can you..." / "I want to..." = do the work.
  - Ask for approval only after preparing a concrete, reviewable result.
  - A skill-triggered pause must quote the SKILL.md line.
  - These are already in gpt.md (:46-48, :59, :83).
S6. OpenAI open-source Codex CLI (github.com/openai/codex, Apache-2.0):
  - Plan mode (`collaboration-mode-templates/templates/plan.md`):
    - defined by effect, as non-mutating vs mutating with examples;
    - "not changed by user intent, tone, or imperative language";
    - an execution request means "plan the execution";
    - discoverable facts are explored first; preferences are asked early with 2-4 options and a recommended default, and if unanswered the agent proceeds and records the assumption;
    - one `<proposed_plan>` block per turn; no "should I proceed?".
  - Default mode: the mode changes only via developer instructions, never via user requests or tool descriptions.
  - Guardian classifier (`prompts/templates/guardian/*`):
    - trusted channels are user and developer messages, `AGENTS.md` and the ask-user tool; tool output, skill text and assistant output are untrusted;
    - the user can extend authorization to named content;
    - untrusted content can't widen approval;
    - two axes (authorization high/medium/low/unknown x risk low-critical) with outcome rules;
    - truncated evidence makes the classifier more cautious but doesn't raise intrinsic risk;
    - urgency doesn't change authorization; a goal doesn't authorize every action that reaches it; prior decisions are context, not precedent;
    - an explicit low-risk list;
    - first output token = the verdict;
    - a non-blocking first reviewer whose "high" triggers blocking review.
  - Goal continuation (`ext/goal/templates/goals/continuation.md`):
    - label each previous turn as progress / verified wait / no progress;
    - equivalent blockers count as the same across turns; "blocked" only after 3 consecutive turns;
    - no narrower substitute;
    - a completion audit with authoritative evidence for each requirement;
    - never complete because the budget is nearly gone;
    - inspect the current state before relying on earlier context.
  - Persistent mode (`prompts/templates/persistent_mode.md`):
    - prefer a completion notification or the product's wait mechanism, else check at the expected rate of progress (often 1-3 min for active work, backing off);
    - a pending or unchanged result is not completion;
    - keep the target, last state, stopping condition and next check in task state;
    - follow-ups don't broaden scope.
  - Compaction prompt (`prompts/templates/compact/prompt.md`).
  - Per-model prompt files (`core/gpt_5_1_prompt.md`, `gpt-5.1-codex-max_prompt.md`, ...).
  - Realtime voice front-end over an execution back-end (`prompts/templates/realtime/backend_prompt.md`):
    - the voice layer delegates and treats back-end output as authoritative;
    - `[USER]` / `[BACKEND]` prefixes;
    - no reading out tables or diffs;
    - pacing and verbosity preferences persist for the task;
    - running work stays steerable.
  - Approval escalation (`permissions/approval_policy/on_request.md`): "don't try and circumvent approvals by using other tools"; no broad persistent approval rules (`python3`).
S7. Google open-source Gemini CLI (github.com/google-gemini/gemini-cli, `packages/core/src/prompts/snippets.ts`):
  - "Assume all requests are Inquiries unless they contain an explicit instruction to perform a task" (the opposite default to S5).
  - User hints are "scope-preserving course corrections".
  - A declined tool call is not re-attempted or negotiated.
  - Never run parallel subagents that mutate the same files.
  - Tool outputs are wrapped in `<untrusted_context>`.
  - Compression prompt: treat history as data and ignore instructions in it; a `<state_snapshot>` with goal, active constraints, key knowledge, artifact trail, file state, recent actions, and task state with DONE / IN PROGRESS / TODO and the current focus; an approved plan's path and step status are preserved.
S8. OpenAI *Prompting Realtime models* (developers.openai.com/api/docs/guides/realtime-models-prompting):
  - 1-2 short sentences; one clarifying question at a time.
  - Preambles instead of filler.
  - Don't guess from unclear audio.
  - Normalize spoken numbers; confirm high-precision values (IDs, emails, phone numbers) before a tool call.
S9. LangGraph async subagents notify the parent instead of being polled (already in langgraph.md:89).

# Part 3: review history

The change went through three review rounds before merge (plan, code against plan, fixes), each by two other models with live web access, and a second read by the author after merge. Every finding was checked against its source before it was applied.

## Plan review

Verdicts on the first plan. C = first reviewer, G = second reviewer.

Implementation began from the draft while the reviews ran; every accepted finding below is applied in the worktree.

| # | Finding | Verdict | Applied |
|---|---|---|---|
| C1 | Transient retry needs an idempotency condition | Confirmed | SKILL.md failure contract + template: retry only if read-only, idempotent, keyed, or checked first |
| C2 | Async "don't poll" unconditional | Confirmed | SKILL.md + template: no-poll only when the harness notifies; otherwise the status call and interval |
| C3 | Payload-only classifier can't judge browser clicks | Confirmed (S6 guardian :57-58) | evals.md: S1's filter is for command-style actions; browser reviewers get observed state as evidence that can't authorize |
| C4 | Parallel-worker rule drops the "mutate" qualifier | Confirmed (S7 :294) | agent-harness: read-only work may run in parallel |
| C5 / G1 | Voice "repair" contradicts S8 | Confirmed | use-cases voice item 3 split: native audio models ask (S8); a text model behind a recognizer may consider a similar-sounding domain term, then confirm |
| C6 / G2 | GPT placement leaves conflicting rules; S4's field definition puts when/how in the description | Confirmed | SKILL.md :204, element 2, GPT cell, template checklist: state once; GPT description covers when/how, routing between tools may sit in the system prompt; gpt.md :153 apply_patch sentence kept |
| C7 / G6 | Verbatim-everything compaction is unsupported and can't fit | Confirmed | agent-harness: active requests faithfully, exact words where wording matters, pointers for long specs, drop done ones; no S7 attribution |
| C8 | Duplicates SKILL.md :88/:92 and :184 | Partly | Routing reason folded into the existing decision-tree bullet; Process bullet removed; approval-of-result is a pointer |
| G3 | First-token verdict conflicts with reasoning-before-answer | Confirmed | evals.md: only for a first-stage filter that escalates, or a thinking model |
| G4 | 0d bullet drops Step 0b; SKILL.md:30 stale | Confirmed | 0d bullet now says the provider read still applies; :30 lists harnesses |
| G5 | "Report blocked only after 3" misstates S6 | Confirmed (S6 :23, :47-48) | Report the blocker at once, keep the goal open; the terminal status after 3 consecutive turns |
| G7 | "Smallest model gets the most text" contradicts claude-fable/claude-opus | Confirmed | Each model gets its own finishing block (Fable 5.2, Opus 5.5, Haiku/Sonnet); small and low effort need the most explicit; langgraph harness profiles pointer |
| G8 | Claude retry cell: `strict: true` | Accepted | "Without `strict: true`, retries invalid or missing parameters 2-3 times" |
| G9 | reasoning_extraction qualifier | Accepted | "Claude Opus / Sonnet / Fable 5.x" |
| G10 | orchestrator.md missing from S6 list; root README unstaged | Bookkeeping | S6 also includes `core/templates/agents/orchestrator.md`; root README verified in the worktree |

## Code review

| # | Finding | Verdict | Applied |
|---|---|---|---|
| C1 | Voice readback must wait for confirmation (S8 :730) | Confirmed | use-cases voice: read back and wait for the user to confirm before the tool call |
| C2 / G5a | gpt.md :153 still moves when-to-use out of the description | Confirmed | gpt.md: description keeps when/how (OpenAI's field definition); routing between tools may sit in the system prompt; stated once |
| C3 | Browser rule forbids following content the user named | Confirmed | use-cases browser 2: named content may be followed in scope; otherwise quote and ask |
| C4 | Wellbeing trigger broader than S3 | Confirmed (S3 :284, :290) | Trigger on the user saying they are thinking about self-harm or describing restricting/purging |
| C5 | Goal loops inherit SKILL.md's 2-3 continuation cap | Confirmed (scoping) | The cap is for nudging early stops; goal loops with verified progress continue, the cap applies to no-progress turns |
| C6 | "none" default would cover required summaries | Confirmed | Scoped to optional helpers; a carry-forward summarizer always produces |
| C7 | Override rule stated twice | Confirmed | Bullet removed; merged into the Process pointer |
| G1 | Withholding tools on a mode switch edits `tools` (cache restart; Claude 5.5 thinking invalidation) | Confirmed (SKILL.md :125) | Keep the tool list stable; forbidden tools error in the wrong mode; withhold only when the mode is fixed for the conversation |
| G2 | Exceptions list merges Anthropic and Codex; `rm -rf` exception needs check results; Codex first pass is non-blocking | Confirmed | evals.md: attribution split, the `rm -rf` caveat, the first-token bullet describes the non-blocking first pass |
| G3 | Subagent checks: subagent calls also gated; return check exists for mid-run compromise | Confirmed (S1) | Both files |
| G4 | Action-classifier tasks don't route to evals.md | Confirmed | Step 0c names action classifiers; SKILL.md evals.md summary lists gate classifiers |
| G5b | Template `<tools>` duplicates tool descriptions (pre-existing) | Confirmed | `<tools>` holds policy between tools; per-tool guidance in definitions; GPT routing note |
| G6 | `<inputs>` says only user and prompt can grant permission | Confirmed | Placeholder names the agent's authorizing channels and the ones that can't authorize |
| G7 | Italic references name bullets, not headings | Mostly refuted | The skill already cites bullets in italics (SKILL.md :126 cites *Keep caution from piling up*); "Finishing work" now says "block" |
| G8 | "a few questions" departs from the plan's 3; template duplicates chat rules | Confirmed | "at most 3"; template line points to use-cases *Chat assistants* |

## Check of the fixes

- Codex: 2 findings, both confirmed and applied - the template's `<inputs>` placeholder now counts project instruction files and the user's answer through the ask-the-user tool as authorizing; the wellbeing trigger lists bingeing and compensating for eating too (S3 :290).
- Gemini: no findings; all r10 rows resolved; agrees G7 is mostly refuted.

## Second read after merge

### Wrong or contradicts the skill's own files

R1. **agent-harness-patterns.md:143, "restarts the prompt cache on every provider".** The skill's provider files say otherwise:
  - gpt.md:49 and :155: GPT-6 can enable and disable tools without breaking the cache;
  - claude.md:170: use mid-conversation tool changes / inline tool definitions;
  - kimi.md:85: K3.x loads tools mid-conversation through a content-less `system` message.

  Fix: editing the request's tool list restarts the cache (and on Claude 5.5-generation models invalidates thinking), so change tools the provider's append-style way where one exists, or keep the list fixed and return errors.

R2. **SKILL.md:82, *Maintaining a prompt in production* lost its scope.** My trim commit (f3cdaf0, reviewed by nobody) dropped the lead that limited it to prompts serving several models. It now tells every reader to put new-model behavior in a variant "not an edit to shared text", which contradicts the Process paragraph above it (on a model upgrade, trim the instructions the new model no longer needs). Fix: open with "When one prompt serves several models".

R3. **SKILL.md:207, "lean production tools often meet all six with a 1-3 sentence description".** Unscoped. The underlying observation was about GPT- and Gemini-based harnesses, which keep tool definitions short and put routing in the developer prompt. On Claude, Anthropic calls detailed descriptions "by far the most important factor". As written it can lead a Claude user to under-describe tools. Fix: scope the sentence to GPT- and Gemini-style harnesses.

R4. **use-cases.md, Chat assistants item 1: wrong attribution.** "The decision holds for the rest of the conversation" and "anyone can delete the note" are credited to "Anthropic's published Claude prompts". Only the published Haiku 5.5 prompt has them (checked: the Opus 5.5, Sonnet 5.5 and Fable 5.2 prompts don't). Fable 5.2 carries narrower versions (reworded lyric requests; the eating-disorder limits). So this is a small-model scaffold, and the playbook presents it as a rule for every chat assistant. Fix: attribute to the Haiku 5.5 prompt, and say Anthropic's larger models scope it to specific categories.

R5. **Two files give opposite examples for the same actions.**
  - agent-harness-patterns.md:48 lists purchases, account creation and permission changes as examples of the "never, even when asked" tier (from one extracted browser-agent prompt).
  - use-cases.md, browser item 3 says the same actions need explicit approval, which is what Codex's reviewer prompt says.

  A browser-agent task reads both. Fix: keep the three tiers, say the never tier is a product decision, and use examples that don't conflict.

R6. **agent-harness-patterns.md:165, "Wait for running workers before ending the turn"** is stated as a general rule. It is right for a harness that doesn't wake the agent (Codex). In a harness that notifies, the *Async work* section says the opposite: don't block, the result arrives on its own. Fix: make it conditional on whether the harness notifies.

R7. **agent-harness-patterns.md:30, "Ask first only when one of two things holds".** The "only" leaves out the third case the next section is about: an action that needs approval. A model that follows this literally has a reason to skip an approval. Fix: one clause saying approvals for risky actions are separate.

### Gaps (official material I missed)

R8. **evals.md gate section omits the tiers in front of the classifier.** Anthropic's post: a safe-tool allowlist, then in-project file edits, and only then the classifier; "most actions are allowed prior to that step". It also drops broad allow rules (blanket shell access, wildcarded interpreters) on entering auto mode, and runs an input-side probe that warns on injection-looking tool results. Both round-2 test answers had to invent the code-rule layer themselves. Fix: one bullet for the tiers, one for the probe.

R9. **evals.md, two-stage bullet vs the skill's own `reasoning_extraction` rule.** Anthropic's second stage asks for written reasoning (the post describes Sonnet 4.6). On Claude Opus / Sonnet / Fable 5.x that instruction can be refused. Fix: say to get second-stage reasoning from native thinking on those models, and that a no-reasoning first stage means Haiku 5.5 with thinking disabled or Sonnet 5.5 at `between_tools`.

R10. **Advisor bullet (agent-harness-patterns.md:212) is leak-only and misses Anthropic's advisor-tool guidance.** The advisor tool doc (platform.claude.com, agents-and-tools/tool-use/advisor-tool) says:
  - call the advisor before substantive work, when done (after saving the deliverable), when stuck, and when changing approach;
  - give the advice serious weight, adapt on primary-source evidence, and reconcile a conflict with one more call;
  - cap its length by addressing it in the user message ("Advisor: please keep your guidance under 80 words").

  With Anthropic's tool the advisor runs under Anthropic's own system prompt, so my "the advisor should..." bullet only applies to a self-built advisor. Fix: lead with the executor-side guidance and cite it; keep my bullet as the self-built case.

R11. **Voice playbook misses the official no-op wait tool.** OpenAI's Realtime guide gives the model a `wait_for_user` tool for silence, background noise and side conversations, so it has a valid way to stay quiet. My leak-derived "one acknowledgement then silence" is weaker. The guide also backs "leave out tools the session doesn't have" (a model may invent the tool or pretend it ran), which SKILL.md:82 states without a source. Fix: add the wait tool; cite the guide for the missing-tool rule.

### Smaller

R12. agent-harness-patterns.md:119, "say 'no tools' at both ends": missing the reason. Normally you just give the summarizer no tools; the prompt guard is for a summary call that keeps the agent's tool list to reuse its cache.
R13. agent-harness-patterns.md:37-38: "Vendors' own harnesses take opposite defaults" then cites OpenAI's GPT-6 *guidance*, which is a suggested prompt, not a harness.
R14. agent-harness-patterns.md:88: the heading says the harness prevents a behavior, then cites a harness classifier that misses 17%. Say plainly: prompt, then classifier, then hard rules in code.
R15. agent-harness-patterns.md:125: "Gemini CLI's snapshot has these parts" lists 5 of 7; say "includes".
R16. agent-harness-patterns.md:148: "Ask about preferences it can't find out early" reads wrong; should be "ask early about preferences it can't find out".
R17. use-cases.md, voice item 1: the digits-or-words rule applies only when a separate text-to-speech engine reads the output.

Checked and found correct in that read: the denial caps (3 / 20), the 17%, 8.5% and 0.4% figures, the exceptions lists and their attribution, the Codex plan-mode, goal-loop and persistent-mode statements, the Gemini CLI inquiry default and concurrency rule, the Haiku 5.5 memory rule, the wellbeing triggers, and the Realtime guide's ask-don't-guess and read-back rules all match their sources.

## Check of the second read

Another model checked the 17 findings above before they were fixed. It confirmed R1, R2, R3, R4, R7, R8, R11, R12, R13 and R17, called R15 and R16 harmless, and judged R14 not a separate defect. It corrected four proposed fixes:
- R5: account creation is not in the browser playbook's list, so the overlap is permission changes only.
- R6: a notification is not enough to end a turn on. The condition is that a worker's completion starts a new turn for the agent.
- R9: Anthropic's post says the second stage asks for careful reasoning, not written reasoning.
- R10: the advisor timing blocks are for coding workloads, and the length request is a soft limit.

It also found three defects the second read had missed:
- Project instruction files were listed as a channel that can always authorize. Codex's reviewer trusts `AGENTS.md`; Moonshot's own agent prompt treats it as reference data.
- "Never repeat a denied call" would also forbid the call after the user gives a fresh, explicit approval.
- A compaction summary that keeps only a pointer to a long specification fails when the resumed agent can't open the original.

All of these are applied.

## Final review of the fixes and the source map

Two other models reviewed the fixes, the field rules and `SOURCES.md`, with the cited collection files in front of them.

The first found two defects:
- "A new approval lifts a denial" also lifted product prohibitions. It now applies only to a denial for missing authorization.
- One source-map row cited a line that backed one of its three rules. Each rule now has its own line.

The second found four:
- The advisor bullet applied Anthropic's "not as a default" caveat to the coding timing blocks. The caveat covers only the stricter checkpoint for Opus executors; the timing blocks are recommended for coding workloads.
- Some field rules were unlabelled, and the split of blockers read as part of Codex's goal prompt. Every field rule is now marked, and the text says Codex has one 3-turn rule for all blockers.
- The corrected refusal text (R4) was itself wrong in a detail. The Opus 5.5 prompt also keeps declining reworded song-lyric requests, all three larger models' prompts hold child-safety declines, and the Fable 5.2 prompt carries the same wellbeing limits as Haiku 5.5. The author's check had searched for "rest of the conversation" and missed "rest of that conversation".
- One line reference in the source map was off by four lines.

Lessons from the reviews:
- About half the corrections were to rules taken from a collection that an official page contradicted or narrowed. Check a pattern against an official page before writing it.
- A rule that is right for one harness is often stated as general. Ask whether it depends on how the harness works (does it notify, can it change tools mid-conversation, does the model hear audio).
- A search that finds nothing is weak evidence. Before writing "only X says this", search for the idea in more than one wording.
- Last-minute trims need a review too. One unreviewed trim removed the words that scoped a paragraph and made it contradict the text above it.

# Part 4: test rounds

Each task was run twice by a Sonnet 5.5 subagent: once with the new skill, once with the version before the change. One run per cell, graded by the author against assertions written before reading the answers.

Round 1 (plan-mode tool swap on Sonnet 5.5; a refund job that times out and gets retried; a pharmacy voice line): the new routing worked in all three runs, and the content tied. The older skill plus the model's own knowledge already produced the key points.

Round 2 (how far an approval reaches; a two-stage action classifier; a goal loop that blocks early or fakes progress): the new version passed 17 of 18 content checks and the old one 15. Both gains were things only the new files carry: which inputs can never grant approval, and handing over to a human after repeated denials. The goal-loop task tied.

Round 3, after the second read (two tasks aimed at what the fixes changed, fixed version against the merged one): a GPT-6.1 Sol mode switch with workers lost in a redeploy, and an Opus 5.5 assistant told that a decline stands for the whole chat. The fixed version passed 12 of 12 checks and the merged one 9 of 12. On the refusal task the merged version repeated the wrong attribution of the blanket rule to Anthropic's prompts in general; on the mode-switch task its prompt told the agent never to end a turn while a worker runs, whatever the harness does. Both versions' answers noted that the GPT file named no mechanism for changing tools without breaking the cache, which led to adding `allowed_tools`.

Cost: about 6% more tokens and about 20 seconds more per task, from one more file to read.

Limits: eight tasks across the three rounds, one run each, one model, graded by the author. Treat the result as "no regression, a modest gain on approvals and classifiers", not as proof.

# Part 5: a field report

After the second read, the maintainer asked one team for its experience with the rules that rested only on vendors' prompts. The team had run 8-10 coding agents in parallel for about two weeks. Its answers, restated in general terms:

**When to stop on a blocker.** One "3 turns" rule was too coarse.
- A transient blocker (an outage, a service answering "unknown") was worth retrying. A queue call that failed that way succeeded on its third try.
- A blocker that needed a person's decision (a change touching a frozen file, an action needing a go-ahead) was right to stop on at the first turn, and stopping there never cost anything.
- The costly failures were workers improvising past a blocker instead of stopping.

**Ending a turn while workers run.** A long-running worker died when its host application restarted. Its wake-up never came, and the agent driving it sat stopped for about seven hours. The team now lists its workers and checks each is alive after any restart or resume. The opposite problem also appeared: workers' own wait loops sent repeated "still waiting" messages.

**Worker reports that misled, most common first.**
1. "The same tests fail on the base", when the base had never been run.
2. A speed or compatibility claim measured in a development environment that didn't hold in the real one (a query that took 1.8 s locally and timed out in production; a library feature present locally and missing in the deployed image).
3. A confident root cause that was later refuted.
4. "Pushed", now rarely wrong because the team asks for the remote commit id.

The checks the team now always runs: the change's state and merge commit from the hosting service, the remote branch's commit id, the net diff of the merge result against the base (it must equal the reviewed diff), and a re-run of any named failing tests on the base.

**What briefs were missing.** Each of these cost work before it was added:
- the exact files other work depends on and that must not change;
- shared environments, with when to announce use and when to release;
- proof on the real path, not an idealised fixture;
- the exact checks to run, by path (workers guessed three different sets);
- banned commands written out;
- who allocates shared sequence numbers (three parallel changes took the same one).

A length cap for the reply mattered less than expected; the format mattered more. Read-only versus write mattered a lot.

**Rules the file lacked.** Claim work before starting it (two sessions twice started the same fix). Measure where it runs. "Done" for deployed work means checked in the deployed environment, not merged. The rule that authorization doesn't pass by delegation was needed: workers had relayed approvals.

These went into `agent-harness-patterns.md` marked *field*. Banned commands were not added as a brief item: the skill already says to enforce those in the harness.

## Follow-up from the team's log

The same team then went through its running log: about 17 days, about 2,850 entries, 49 of them marked as corrections. The patterns that recurred:

1. **The orchestrator's own claims about state, made from memory.** It told a worker a change had merged when it was conflicting, its log timestamps ran about two hours off, and twice it called something not done that had been done days earlier. Rule: a claim about state (merged, done, a time, a count) comes from the system of record or the clock at the moment it is made. That covers the orchestrator's claims as well as workers'.
2. **A worker paraphrasing someone else's document wrongly.** The orchestrator then asked a person an unneeded question built on the paraphrase. Rule: when a worker relays what a document, a change or a message says, it quotes the line with its location.
3. **Counts off by one or two in prose summaries** (10 of 18 reported as 9 of 18). Rule: numbers in a report come from pasted tool output.
4. **A hold message missed after a context reset.** Another agent had asked for a pause; the orchestrator re-planned from its summary and didn't see the request. A final check caught it. Rule: after compaction or a resume, re-read inbound messages for holds and stops before any action on shared state.
5. **Sampled monitoring missed a peak.** A check every 45 seconds missed a memory peak that came within a few percent of the limit. Rule: when the question is whether a value ever exceeded a limit, read the system's own high-water mark or counter, not samples.
6. **Destructive effects hidden in a routine command.** A tear-down command deleted stored data, not only processes. A worker caught it before running it. Rule: the brief names the commands with irreversible effects in this environment, not only the obviously dangerous ones.
7. **First diagnoses were often wrong**, about a third of the corrections: a "size cap" that was a parsing bug, a "validator defect" that was a deliberate rule, "judge misses" where the judge had never seen the evidence. Rule: a diagnosis is a hypothesis until a measurement or a trace step confirms it. Asking a second model on the same evidence caught several.
8. **Limits that are immutable by design.** A worker was right to refuse to hand-edit a cap that was meant to be fixed; the right move was a new object. Rule: when a guard refuses, find out whether the refusal is the design before looking for a way around it.

Two smaller ones: workers reporting "the same failures as the base" without running the base, and banned commands that slipped once each despite the brief. Both slips were self-reported. Self-reporting worked; prevention needs the harness.

Items 1 to 8 went into `agent-harness-patterns.md` marked *field*.
