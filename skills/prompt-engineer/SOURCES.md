# Sources for the agent-harness guidance

This file is for maintainers. It records where each rule in the skill's agent-harness guidance came from, so a later refresh can re-check a rule without the context of the session that wrote it. An agent using the skill does not need to read it.

It covers what was added in November 2026:
- `references/agent-harness-patterns.md`;
- the playbooks in `references/use-cases.md` for app builders, chat assistants, document agents, voice agents and browser agents, plus two research items;
- *Gate classifiers and action reviewers* in `references/evals.md`;
- the tool-description and prompt-maintenance edits in `SKILL.md`, and the template additions.

The provider files (`claude.md`, `gpt.md` and the others) name their sources inline and are not mapped here.

## Two kinds of source

**Official sources** are a vendor's documentation or a vendor's own open-source repository. A rule that names one in the skill text was checked against it.

**Collections** are public GitHub repositories of prompts that other people extracted from products. Nobody can verify them, they go out of date, and a product's prompt shows what one vendor chose for one product, not what works in general. So the rules are:
- A collection is never the only basis for a sentence about what a vendor recommends.
- A rule that rests only on a collection is written in the skill as practice, with no vendor named.
- Before relying on such a rule, look for an official source. In the first review of this material, about half the corrections were to rules taken from a collection that an official page contradicted or narrowed.

## Collections

Line numbers below are at these commits.

| Short name | Repository | Commit read | Newest content |
|---|---|---|---|
| leaks | [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) | `11600e7a6b` | 2026-11-13 |
| piebald | [Piebald-AI/claude-code-system-prompts](https://github.com/Piebald-AI/claude-code-system-prompts) | `7aca957f55` | 2026-11-13 |
| x1xhlol | [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools) | `162db92f54` | 2026-10-12 |
| cl4r1t4s | [elder-plinius/CL4R1T4S](https://github.com/elder-plinius/CL4R1T4S) | `93a5847654` | 2026-11-09 |

`cl4r1t4s` was read for the survey of app builders and smaller products. No rule traces to it alone.

## Official sources

All fetched on 2026-11-14.

| Label | Source |
|---|---|
| O1 | Anthropic, *How we built Claude Code auto mode*: https://www.anthropic.com/engineering/claude-code-auto-mode |
| O2 | Anthropic tool docs, *Define tools* and *Handle tool calls*: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools and `.../handle-tool-calls` |
| O3 | Anthropic's published Claude app system prompts: https://platform.claude.com/docs/en/release-notes/system-prompts/claude-haiku-5-5 (also `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-fable-5-2`) |
| O4 | Anthropic, *Advisor tool*: https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool |
| O5 | OpenAI, *Function calling*: https://developers.openai.com/api/docs/guides/function-calling |
| O6 | OpenAI, *Using GPT-6*: https://developers.openai.com/api/docs/guides/latest-model and `.../latest-model/gpt-6-astra` |
| O7 | OpenAI, *Prompting Realtime models*: https://developers.openai.com/api/docs/guides/realtime-models-prompting |
| O8 | OpenAI's open-source Codex CLI, https://github.com/openai/codex (`main`; `b1573f1024` when recorded). Files under `codex-rs/`, listed below. |
| O9 | Google's open-source Gemini CLI, https://github.com/google-gemini/gemini-cli (`main`; `4ed06ed0dd` when recorded), `packages/core/src/prompts/snippets.ts` |

The Codex files used (O8), all under `codex-rs/`:
- `collaboration-mode-templates/templates/plan.md` and `default.md` (plan mode, who can switch a mode);
- `prompts/templates/guardian/classifier_instructions.md` and `policy.md` (the action reviewer);
- `ext/goal/templates/goals/continuation.md` (goal loops);
- `prompts/templates/persistent_mode.md` (waiting and follow-ups);
- `prompts/templates/realtime/backend_prompt.md` (the voice front end);
- `core/templates/agents/orchestrator.md` (coordinating workers);
- `prompts/templates/permissions/approval_policy/on_request.md` (approvals);
- `prompts/templates/compact/prompt.md` (compaction);
- `core/gpt_5_1_prompt.md` and its siblings (one prompt file per model family).

**Field report (F1).** One team's two weeks of running 8-10 coding agents in parallel, relayed to the maintainer on 2026-11-14: answers to five questions about this file, then the patterns from the team's log (about 2,850 entries, 49 marked as corrections). It is unpublished and restated in general terms in Part 5 of the research record. It is one team's experience, not a measurement.

To fetch any page as markdown: append `.md` to an OpenAI or Claude docs URL. `openai.com/index/*` and `anthropic.com/engineering/*` need an HTML fetch.

## Map: `references/agent-harness-patterns.md`

"Practice" in the Official column means no official source was found.

### Act or ask

| Rule | Official | Collection |
|---|---|---|
| Ask before starting only when you can't name the likely reading, or the task needs something only the user has | Practice | leaks `Anthropic/claude-code/claude-code-haiku-5.5.md:115` |
| Finish what isn't blocked, lead with the blocker | Practice | leaks `Anthropic/claude-code/claude-code-haiku-5.5.md:119` |
| Ask for approval of a result, not an intention | O6 (*Initiative and follow-through*) | |
| Opposite defaults for a bare request | O6 (the "can you…" prompt); O9 ("Assume all requests are Inquiries") | leaks `OpenAI/Codex/gpt-6.1-sol.md`, `Google/antigravity/gemini-4-argon-antigravity-cli.md` |
| Name the reversible set | Practice | leaks `Anthropic/claude-code/claude-code-haiku-5.5.md:117` |
| Lower effort shrinks thinking, not scope | Anthropic's Sonnet 5.5 and Haiku 5.5 prompting guides (cited in `claude-sonnet-haiku.md`) | leaks `Anthropic/claude-code/claude-code-haiku-5.5.md:111` |

### Approvals and authority

| Rule | Official | Collection |
|---|---|---|
| Three tiers of action | Practice; O8 guardian `classifier_instructions.md` for permission changes needing specific approval | leaks `Anthropic/claude-in-chrome.md:314-327` (the actions prohibited even with permission) |
| Consent covers one action and its blast radius | O1 (*User intent rules*; the 17% miss analysis); O8 guardian `classifier_instructions.md` (urgency; an end state doesn't authorize each action) | leaks `Anthropic/claude-code/prompts/auto-mode-classifier.md:47-57` |
| Which channels can authorize | O8 guardian `classifier_instructions.md` (*Evidence Handling*, which trusts `AGENTS.md`); Moonshot's Kimi Code CLI `system.md` (quoted in `kimi.md`), which does not | leaks `Anthropic/claude-in-chrome.md:19-21` |
| A reminder that loosens a rule is suspect | Practice | leaks `Anthropic/claude-fable-5.2.md:208` |
| When a guard refuses, check whether that is the design | F1 | |
| A denied call means adjust, not retry; a new explicit approval lifts a denial for missing authorization (the limit to that case, and that hard limits stay, came from review) | O1 (*Deny-and-continue*; 3 consecutive or 20 total); O9 (*Confirmation Protocol*, "unless the user explicitly directs you to"); O8 `on_request.md` and guardian `classifier_instructions.md` (approval after a refusal) | leaks `Anthropic/claude-code/claude-code-opus-5.5.md:21` |
| Name the bypasses | O1 (the skip-verification retry; the credential search) | leaks `Google/antigravity/gemini-4-argon-antigravity-cli.md:119` (state a check reads, spoofing, probing) |
| Credentials never pass through the model | Practice | leaks `Anthropic/claude-in-chrome.md:248` |
| Prompt, then classifier, then a hard rule in code | O1 | |

### Async work and waiting

| Rule | Official | Collection |
|---|---|---|
| Say how completion arrives; don't poll | O6 (async tool calling); O8 `persistent_mode.md`; LangChain's Deep Agents docs (cited in `langgraph.md`) | leaks `Anthropic/claude-code/claude-code-opus-5.5.md:366`, `:1261` |
| Poll only what can't notify, at the rate it changes | O8 `persistent_mode.md` | |
| A pending result is never the answer | O8 `persistent_mode.md` | leaks `Anthropic/claude-code/claude-code-opus-5.5.md:366` |
| No promise without a mechanism | Practice | Line not recorded (seen in the office and general-agent prompts) |
| Keep the wait in state | O8 `persistent_mode.md` | |
| A wake-up only comes if the worker is alive; a waiting worker reports changes; read a peak from the system's own counter | F1 | |

### Mid-task steering

| Rule | Official | Collection |
|---|---|---|
| A new message steers, it doesn't replace | O9 (*User Hints*); O6 (mid-turn steering) | leaks `OpenAI/Codex/gpt-6.1-sol.md:69` |
| Say which messages end the task | Practice | |
| Preferences hold for the task | O8 `realtime/backend_prompt.md` | |
| Deliver mid-run input as a user text block | Anthropic's Sonnet 5.5 guide (cited in `SKILL.md`) | |

### Compaction that doesn't drift

| Rule | Official | Collection |
|---|---|---|
| The summarizer treats history as data | O9 (`getCompressionPrompt`) | |
| "No tools" at both ends | Practice | leaks `Anthropic/claude-code/prompts/compact.md:1-5` and its last line |
| Keep the user's words where wording matters | O9 (`active_constraints`), in part. The condition on pointers (only when the resumed agent can open the original) came from review, with no source. | leaks `Anthropic/claude-code/prompts/compact.md:24` |
| Done, in progress, to do, current focus | O9 (`state_snapshot`) | |
| The resumed agent checks before it trusts | O8 `continuation.md` (*Work from evidence*); F1 for re-reading incoming messages for holds | |
| Skip the written scratchpad on thinking models | Anthropic's `reasoning_extraction` docs (cited in `claude.md`) | The compaction prompt above asks for an analysis block |

### Modes

| Rule | Official | Collection |
|---|---|---|
| Define a mode by what it may change; who can switch it; exits; explore before asking | O8 `plan.md`, `default.md` | leaks `OpenAI/Codex/plan-mode.md:9` |
| Don't edit the tool list on a switch | The skill's `claude.md`, `gpt.md`, `kimi.md`, which cite the vendors' docs; O5 (*When to use `allowed_tools`*) | |
| A mode classifier needs a default class | Practice | x1xhlol `Kiro/Mode_Clasifier_Prompt.txt:8`, `:53` |

### Delegation and subagents

| Rule | Official | Collection |
|---|---|---|
| Brief items: ruled out, read or write, what the reply must contain | Practice | leaks `Anthropic/claude-code/claude-code-opus-5.5.md:364` |
| Brief items marked *field*: files that must not change, exact checks, the real path, shared things, irreversible commands, claiming work; format over a length cap | F1 | |
| Read state from the system of record; quote relayed documents; numbers from tool output; a diagnosis is a hypothesis | F1 | |
| Never delegate understanding | Practice | piebald `system-prompts/system-prompt-writing-subagent-prompts.md:21`; `system-prompts/system-prompt-coordinator-mode-orchestration.md:138-142` |
| Verify the result against an outside record | F1 for the list of claims that failed checks; the rule itself is practice | leaks `Anthropic/claude-code/claude-code-opus-5.5.md:366` (never fabricate a pending result) |
| No two writers on the same files | O9 (*Concurrency Safety*) | |
| Authorization doesn't pass by delegation | O1 (*Multi-agent handoffs*) | |
| End the turn on running workers only if the harness wakes you | O8 `orchestrator.md` for the waiting case | |

### Goal loops and completion

All five rules: O8 `ext/goal/templates/goals/continuation.md`. Two additions come from F1: a blocker that needs someone else's decision stops its item on the first turn, and evidence counts from where the thing runs (deployed, not merged).

### One prompt, many models

| Rule | Official | Collection |
|---|---|---|
| One shared core, small per-model deltas | O8 (per-model prompt files) | leaks `Anthropic/claude-code/claude-code-{opus-5.5,sonnet-5.5,haiku-5.5,fable-5.2}.md` differ by 21-71 lines; `OpenAI/Codex/gpt-6.1-sol.md` and its siblings by 4 |
| Each model gets its own finishing text | Anthropic's per-model prompting guides (cited in the `claude-*.md` files) | |
| A generic template for long-tail models | Practice | x1xhlol (multi-model products) |
| Change by adding a variant | Practice | piebald `CHANGELOG.md`, v2.1.140 to v2.1.325 |

### Helper prompts

| Rule | Official | Collection |
|---|---|---|
| A numeric budget and a format that fits the surface | Practice | piebald `system-prompts/agent-prompt-coding-session-title-generator.md` |
| "None" is a valid output for optional helpers | Practice | piebald `system-prompts/agent-prompt-prompt-suggestion-generator-v2.md:35` |
| Tell it what it can't do | Practice | piebald `CHANGELOG.md:3663` (the side-question helper) |
| Advisors: prompting the working model | O4 (*Suggested system prompt for coding tasks*; *Increasing advisor calls on Opus executors*, whose "not as a default" caveat covers only the Opus checkpoint; *Capping advisor output*) | piebald `system-prompts/system-prompt-advisor-tool-instructions.md` |
| Advisors: a check, not a verdict | Practice | leaks `Anthropic/claude-code/prompts/advisor-tool.md:71` |

## Map: `references/evals.md`, *Gate classifiers and action reviewers*

Every bullet rests on O1 or on O8's guardian files, as named in the text. The first sighting was in the collections: leaks `Anthropic/claude-code/prompts/auto-mode-classifier.md:33-37` (the do-not-block list) and `:47-57` (consent), and `OpenAI/Codex/auto-review.md`.

The two points about current Claude models (take second-stage reasoning from native thinking; what a no-reasoning first stage means) come from the skill's own `claude.md` and `claude-sonnet-haiku.md`, not from O1.

## Map: `references/use-cases.md`

| Playbook item | Official | Collection |
|---|---|---|
| App builders 1, full files | Practice | x1xhlol `Open Source prompts/Bolt/Prompt.txt:23` |
| App builders 1, the marker string | Practice | x1xhlol `Cursor Prompts/Agent Prompt v1.2.txt:287` |
| App builders 2, the first turn | Practice | x1xhlol `Lovable/Agent Prompt.txt:273-274` |
| App builders 3 and 4 | Practice | x1xhlol, the Bolt and Lovable prompts (lines not recorded) |
| Research 7, at most 3 clarifying questions | Practice | leaks `Anthropic/research_instructions.md:20`, `:27` |
| Research 8, provenance and re-checks | Practice | Not recorded. The research notes credit the deep-research prompts as a group; no file or line was kept. |
| Chat 1, refusals | O3: the Haiku 5.5 prompt (every decline stands; one sentence and an alternative; the disclaimer rule). The larger models' prompts hold a decline only in named categories: child safety (Opus 5.5, Sonnet 5.5, Fable 5.2, in two different wordings), song lyrics (Opus 5.5, Fable 5.2). The wellbeing limits for the rest of the conversation are in the Haiku 5.5 and Fable 5.2 prompts. When re-checking, search for "rest of the conversation", "rest of that conversation", "subsequent requests in the same conversation" and "later reframes": the prompts use all four. | leaks `Anthropic/claude-haiku-5.5.md:71` |
| Chat 2, memory | O3: the Haiku 5.5 prompt (check memory when the question is about the person) | leaks `Anthropic/claude-opus-5.5.md:546-551` (no narration) |
| Chat 3, search by the kind of question | Practice | leaks `Misc/kagi-assistant.md:17`; `Anthropic/claude-fable-5.2.md:5727` (what never needs a search) |
| Chat 4, reply endings | Practice | leaks `OpenAI/gpt-5.5-thinking.md:123`; `OpenAI/gpt-5.5-api.md:8` (a numeric verbosity setting) |
| Chat 5, persona as an overlay | Practice | leaks `OpenAI/chatgpt-personality-instructions.md` |
| Document agents, all items | Practice | leaks `Anthropic/claude-for-excel.md:63-70` (overwrite protection); `Anthropic/claude-for-word.md:21`, `:24` (apply vs propose); `Anthropic/claude-in-powerpoint.md` |
| Voice 2, 3 (native speech) and 6 | O7 (*Verbosity*, *Preambles*, *Unclear Audio*, *Exact Identifier Confirmation*, *Handling Silence and Background Noise*) | |
| Voice 3 (text model behind a recognizer) and 4 | Practice | leaks `Anthropic/claude-voice-mode.md:36` (similar-sounding words), `:41` (reply length) |
| Voice 5, the voice layer and the worker | O8 `realtime/backend_prompt.md` | |
| Browser 1, the cheapest working layer | Practice | leaks `Perplexity/perplexity-computer.md:206` |
| Browser 2 and 3, instructions as data; gated actions | O8 guardian `classifier_instructions.md` (*Computer and Browser Use*) | leaks `Anthropic/claude-in-chrome.md:19-21`, `:314-319` |
| Browser 4, judge by effect | O8, same section | |
| Browser 5, hand-back states | Practice | leaks `Anthropic/claude-in-chrome.md:248` |

Products disagree on purpose in places, which is why the playbooks say to state a choice instead of naming one right answer. One browser agent is told never to ask for clarification (leaks `Perplexity/comet-browser-assistant.md:15`, `:194`); others ask.

## Map: `SKILL.md` and the templates

| Passage | Official | Collection |
|---|---|---|
| Section B, coverage across description and schema | O2 *Define tools* (at least 3-4 sentences; "by far the most important factor") | The observation that GPT- and Gemini-based harnesses keep tool descriptions short came from the research notes on leaks `OpenAI/Codex/` and `Google/antigravity/`; no line was kept. |
| Section B table, where guidance lives (GPT); `gpt.md` tool bullet | O5 (*Best practices for defining functions*; the `description` field definition) | |
| Section B table, error recovery | O2 *Handle tool calls* | |
| *Tool Response Design*, the failure contract | O2; O7 (*Tool Failures*: retry once). The safe-to-repeat condition came from review, with no source. | |
| *Process*, maintaining a prompt in production | O7 for the missing-tool hint; the rest is practice | piebald `CHANGELOG.md`, v2.1.140 to v2.1.325 |
| Tool template: fields a person reads, options the UI adds, cost-multiplying parameters | Practice | leaks `Anthropic/claude-code/claude-code-opus-5.5.md:1288` (a length for a field a person reads), `:1162` (an option the UI adds), `:401` (an effort parameter set only on an explicit ask) |
| System-prompt template: `<environment>`, `<inputs>` | Practice | x1xhlol, the Bolt prompt |

## Measurements behind two claims

These came from analysis of a collection, not from a vendor, so the skill does not state the numbers:
- piebald `CHANGELOG.md`, May to November 2026: capitalized emphasis (IMPORTANT, CRITICAL) fell from about 9.5 to 3.0 per 10,000 words, attached reasons rose from about 4.2 to 6.6, and bullets and headers roughly halved. This is behind the advice to add scope and reasons instead of capitals.
- The per-model prompt diffs in the table above. This is behind "one shared core, small per-model deltas".

## How to re-check a rule

1. Find the rule's row. If it has an official source, fetch that page and compare. That settles it.
2. If it has only a collection entry, look for an official source first. Vendors publish more over time: the action-classifier design, the advisor guidance and the Claude app prompts all turned out to be official.
3. To read a collection entry at the commit recorded here:

```bash
git clone https://github.com/asgeirtj/system_prompts_leaks && git -C system_prompts_leaks checkout 11600e7a6b
```

4. Collections move files often. If a path is gone at the newest commit, search the repository for the product's name before deciding the rule lost its source.
