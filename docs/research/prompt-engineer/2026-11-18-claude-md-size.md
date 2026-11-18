# claude.md back under the single-read limit (2026-11-18)

Record for moving two sections out of `skills/prompt-engineer/references/claude.md`. No guidance was added, removed or reworded; the change is where the text lives and the pointers to it.

## Why

The skill tells the reader to read each reference file in full. The reading tool the skill is used with returns at most 25,000 tokens per call, by its own count. On 2026-11-18, test runs for the GPT-6.2 update recorded how each file was read: a single call on `claude.md` returned lines 1-216 of 268 and reported 26,363 tokens. The file was 69,213 characters, so the tool counts about 2.6 characters per token for it. `gpt.md` was split the same day for the same reason (`2026-11-18-gpt-6-2-astra-sol.md`).

## What moved

| Text | Size | From | To |
|---|---|---|---|
| *Migration checklists*, 11 paragraphs | 6.5 KB | `claude.md` | The file of the model each checklist moves **to**: 5 to `claude-opus.md`, 3 to `claude-fable.md`, 3 to `claude-sonnet-haiku.md`, each as a closing *Migration checklists* section |
| *Cost and intelligence: Anthropic's measured playbook*, 8 numbered steps | 4.8 KB | `claude.md` | New `claude-cost.md` |

`claude.md` keeps both headings, each with a short pointer. It is now 58,812 characters.

**Why these two.** The per-model files are already read for every Claude model in scope, including the one being migrated from (Step 0b), so a checklist placed in its target model's file is read exactly when it is needed and needs no new routing. The cost playbook is one self-contained list from one source and is needed for one kind of task, so it reads well as its own file with a routing clause.

## Pointers changed

- `SKILL.md` (three in-place edits, still 495 lines): the Step 0b line for Claude now says each per-model file holds its model's migration checklists and adds `claude-cost.md` for tasks about cost, effort level, budgets or combining models; the effort bullet and the file list at the end name the new file.
- `claude.md`: its Contents list, the per-model table (a *Migration checklists* entry per file) and the two pointer sections.
- `claude-opus.md`, `claude-fable.md`, `claude-sonnet-haiku.md`: the opening sentence no longer says the migration checklists are in `claude.md`; Contents lists the new section.
- `claude-cost.md`: "(see *Caching*)" became "(`claude.md`, *Caching*)".
- `agent-harness-patterns.md` and the skill's `README.md`: one pointer each.

## Checks

- **Nothing lost.** A script compared the old `claude.md` with the five files that now hold its text: every non-empty line is present verbatim except six intended edits (two Contents entries, three rows of the per-model table, and the "(see *Caching*)" pointer). Each of the 11 migration paragraphs is in exactly one per-model file.
- **Single read.** A subagent called the reading tool once per file with no offset or limit: `claude.md` (238 lines), `claude-cost.md`, `claude-opus.md`, `claude-fable.md` and `claude-sonnet-haiku.md` each came back whole. `gemini.md` (64.8 KB, the next largest reference file) was checked the same way and also came back whole.
- **Review.** Codex (gpt-6.1-sol, high effort, 103 s) read the old files, the new files and a diff of the old `claude.md` against the new files put back together: no findings. It confirmed the 11 paragraphs verbatim in the right files (5, 3, 3), the eight-step playbook, the references inside the moved text, and the Step 0b routing.
- **Test.** One question that needs both moved sections (a checklist for moving a workload from Opus 5.5 to Fable 5.2, and the order of cost reductions with their measured results), answered by a subagent (Claude Sonnet 5.5, high effort) with the skill after and before the move. Both answers passed all 9 written checks. With the moved files the subagent read `claude.md` in one call and followed the routing to `claude-fable.md` and `claude-cost.md`; before the move it needed two calls for `claude.md`. Tokens per run: 148,914 after, 146,281 before.

## Not done

`SKILL.md` itself is about 36,000 tokens by the same count. It is normally loaded by the skill mechanism, not by a file read, and it was left alone.
