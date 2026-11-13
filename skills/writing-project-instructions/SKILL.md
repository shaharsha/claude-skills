---
name: writing-project-instructions
description: Use when authoring, editing, updating, trimming, or adding rules to a CLAUDE.md, AGENTS.md, CLAUDE.local.md, or other project-level instruction file for an AI coding agent — including small one-line changes. Triggers on "write a CLAUDE.md", "audit my CLAUDE.md", "trim my CLAUDE.md", "is my CLAUDE.md too long", "what should go in my CLAUDE.md", "why isn't Claude following my CLAUDE.md", "add this to CLAUDE.md", "edit CLAUDE.md", "update CLAUDE.md", "put a rule in CLAUDE.md", "remember this in CLAUDE.md", or the equivalent for AGENTS.md. Always load this skill before modifying any CLAUDE.md/AGENTS.md, not just when explicitly asked.
---

# Writing project memory

CLAUDE.md (and the cross-agent equivalent AGENTS.md) is the file an AI coding agent reads at the start of every session for project context. It compounds in value but bloats easily, and bloated files get ignored — Claude drops rules when the file is too long.

## The single most important test

Before keeping any line, ask: **"Would removing this cause the agent to make a specific, identifiable mistake?"**

If you can't articulate the specific mistake the line prevents, cut the line.

The evidence backs a short file. In one study, context files did not generally raise coding agents' task success and added over 20% inference cost; the agents followed the instructions in them, but repository overviews didn't help (Gloaguen et al., arXiv:2602.11988, 2026). Another study linked `AGENTS.md` to lower median runtime and fewer output tokens at similar task completion (Lulla et al., arXiv:2601.20404). Measure on your own tasks before you trust a file.

## What to include vs exclude (Anthropic's cardinal rule)

| ✅ Include | ❌ Exclude |
|---|---|
| Bash commands the agent can't guess (`bun test`, custom scripts) | Anything visible from `package.json`, `tsconfig.json`, or `ls` |
| Code style rules that **differ** from language defaults | Standard conventions (`async/await`, `const` over `var`, etc.) |
| Repository etiquette (branch naming, commit format, PR rules) | Self-evident practices ("write clean code", "be helpful") |
| Architectural decisions specific to the project (why X not Y) | Long explanations or tutorials — link to `docs/X.md` instead |
| Required env vars, ports, OS quirks | File-by-file directory listings — the agent can `ls` |
| Common gotchas / non-obvious foot-guns | Stale rules referencing tools you no longer use |
| Where to look up live state (the command, file or dashboard that reports it) | Live state itself: what's switched on or off, which workflows or services exist, who owns what right now |

## Length and structure

- Target: **under 200 lines** per file. Official wording: *"target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."*
- **It's a soft target, not a cliff — don't over-index on it.** A file that loads at launch isn't cut at 200 lines; you get a warning at startup and in `/status` when a file runs long or the files add up past a combined limit, and a file over 4 MiB is skipped. Adherence decays gradually. A 250-line file of real foot-guns beats a 190-line file that cut them to hit a number.
- **Files that load on demand do get cut.** A subdirectory `CLAUDE.md` or `CLAUDE.local.md` (and what it imports), a nested `.claude/rules/` file, or a path-scoped rule over a per-file limit reaches Claude as its start plus a note to read the rest, and the rest stays out of context until Claude chooses to read it. The limit is 40,000 characters on a 200K context window and 150,000 on a 1M window (200,000 on Opus 4.6 / Sonnet 4.6), since v2.1.309. Check with `wc -m`, and keep the rules that matter near the top.
- **Don't confuse it with the auto-memory cap.** The *hard* 200-line/25KB limit applies only to auto memory's `MEMORY.md`, where content past the limit is **silently dropped** at load. Different file, different rule.
- Too long and Claude ignores half of it: important rules get lost in the noise.
- Use markdown headers (`## Build`, `## Style`) and bullets — not dense prose.
- **Run `/doctor`** (v2.1.206+) to get trims proposed against the real criteria: it cuts what Claude can derive from the codebase (directory layouts, dependency lists, architecture overviews) and keeps pitfalls, rationale, and conventions that differ from tool defaults. Prefer it to eyeballing. **`/doctor prompt-audit`** (v2.1.283+) looks for instructions written for older models, references to files or commands that no longer exist, and files that contradict each other, across CLAUDE.md, CLAUDE.local.md, AGENTS.md and the rules, skills, commands, subagents and output styles under `.claude/`; it proposes edits and changes nothing until you ask. For skills, `/skill-doctor` (v2.1.252+) shows what each one costs in context and how often it's used.
- **In a shared repo, give the file an owner and review changes to it like code.** CLAUDE.md grows the way any unowned config file does — every team appends, nobody deletes — and every line then loads for every engineer on every session whether it's relevant or not. In a monorepo, give each team's directory its own subdirectory CLAUDE.md; developers can set `claudeMdExcludes` to skip files from teams whose code they never touch.
- If you cross 200 and can't trim, split conditional content into `.claude/rules/<topic>.md` with `paths:` frontmatter (loads only when matching files are read).
- ⚠️ **`.claude/rules/` is invisible to most other agents.** If the repo keeps instructions in `AGENTS.md` for cross-agent parity (Codex, Cursor and Grok Build read it, Gemini CLI when configured to, and Claude Code directly or through `@AGENTS.md`; see *How other agents load these files*), moving content into `.claude/rules/` hides it from **Codex, Cursor and Gemini CLI** (Grok Build reads it for compatibility). Weigh the context saving against breaking the parity AGENTS.md exists for — usually not worth it for a few lines.
- Splitting into `@path` imports does **not** save context — imported files load in full at launch. Only `paths:`-scoped rules and skills reduce startup context.

## Specificity — every rule must be falsifiable

A reviewer should be able to point at code and say "this rule was violated."

| ❌ Vague | ✅ Concrete |
|---|---|
| "Format code properly." | "2-space indentation, no semicolons, single quotes." |
| "Test your changes." | "Run `bun run typecheck && bun test` before commit." |
| "Be careful with auth." | "JWT validated in `src/middleware.ts` only — never per-route." |

## Locations and loading

| File | Scope | Loaded | Survives compaction? |
|---|---|---|---|
| `./CLAUDE.md` | Team, in git | Every session | Yes — memoized, cache cleared and re-read |
| `./CLAUDE.local.md` | You, gitignored | Every session, after CLAUDE.md | Yes — re-read |
| `~/.claude/CLAUDE.md` | You, all your projects | Every session | Yes — re-read |
| `./sub/dir/CLAUDE.md` | That subtree | When a file under it is read | **No — gone until that subtree is touched again** |
| `./.claude/rules/<topic>.md`, no `paths:` | Always on | Every session | Yes — re-injected |
| `./.claude/rules/<topic>.md` with `paths:` | Per-glob | Only when matching files open | **No — gone until a matching file is touched again** |

The compaction column is the one people get wrong. An **unscoped rule is mechanically identical to putting the content in CLAUDE.md** — always loaded, always costing tokens — so the `paths:` field is the entire reason to reach for a rule. But scoping trades away persistence: a path-scoped rule and a subdirectory CLAUDE.md both vanish after compaction until something re-triggers them. Choose a path-scoped rule over a nested CLAUDE.md when the constraint is cross-cutting — it applies to files in several corners of the repo rather than one directory.

Two neighbours worth knowing for the "where does this belong" call: a **skill**'s body loads only when invoked, and invoked skills are re-injected after compaction only up to a budget *shared across all of them*, oldest dropped first. A **hook** bypasses compaction entirely, because it's code the harness runs rather than text competing for the window. The longer the session, the more a hook beats a rule and a rule beats a paragraph.

**Claude Code reads `AGENTS.md` too (v2.1.277+), but only when no CLAUDE file is in the way.** With no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the working directory or above it, Claude loads every `AGENTS.md` (and `.claude/AGENTS.md`) from there up at launch, and a subdirectory's `AGENTS.md` when it opens a file in that subdirectory with the Read tool - unless that subdirectory has a `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` of its own. `~/.claude/CLAUDE.md`, managed instructions and `.claude/rules/` don't count and keep loading alongside. Once one of those three files exists, it reads the CLAUDE files only, so **adding a personal `CLAUDE.local.md` quietly switches `AGENTS.md` off** for you. The **Project instructions** setting changes the default (`claude-md-or-agents-md`) to `claude-md-and-agents-md` (both, each directory's CLAUDE files first), `claude-md`, or `managed-only`. It never reads `AGENTS.override.md`, `AGENTS.local.md`, or anything under `.agents/`. To share one file and add Claude-only lines, keep a `CLAUDE.md` whose first line is `@AGENTS.md`: it works on every version and in sessions that can't read `AGENTS.md` directly, and Claude never reads the file twice. A symlink (`ln -s AGENTS.md CLAUDE.md`) also works, but Edit and Write refuse to write through it and a Windows clone may check it out as a one-line text file. `/init` folds Cursor and Copilot rules into a new CLAUDE.md, and `AGENTS.md` too only with `CLAUDE_CODE_NEW_INIT=1`; `/import` appends a one-time copy of another agent's files such as `AGENTS.md`.

## How other agents load these files

The same files reach each agent differently, and two limits drop text without an error:

| Agent | Files it reads | Which directories, and when | Size limit |
|---|---|---|---|
| Claude Code | `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/`, and `AGENTS.md` as above | the working directory and every directory above it at launch; subdirectories on demand, when Claude touches a file there | launch files: a warning, not a cut (over 4 MiB skipped); on-demand files: cut to their start past 40,000 / 150,000 (200,000 on Opus / Sonnet 4.6) characters (above) |
| Codex | `~/.codex/AGENTS.override.md` or `AGENTS.md`, then per directory one of `AGENTS.override.md`, `AGENTS.md`, or a name listed in `project_doc_fallback_filenames` | the project root (usually the git root) down to the working directory, once per run; **nothing below the working directory** | stops adding files once the combined size reaches `project_doc_max_bytes`, **32 KiB** by default |
| Gemini CLI | `GEMINI.md`; set `context.fileName` to include `AGENTS.md` | `~/.gemini`, the workspace directories and their parents; just in time when a tool touches a directory (that directory and its ancestors, up to a trusted root) | not documented |
| Cursor | `.cursor/rules/*.mdc` (a plain `.md` there is ignored) and `AGENTS.md` | the root and any subdirectory, combined with the parents; the more specific file wins | not documented |
| Grok Build | `AGENTS.md`, plus `CLAUDE.md`, `.claude/rules/` and `.cursor/rules/` for compatibility | not documented in detail | loaded in full, no cap |

What follows from the table:

- **Per-folder files reach Codex only on the path to where it started.** Claude Code picks up `services/payments/CLAUDE.md` when it opens a file there; Codex started at the repo root never reads `services/payments/AGENTS.md`. Put rules every agent needs in the root file, and a folder's rules in that folder's file only if the agents that need them start there or load on demand.
- **Past 32 KiB combined, Codex drops the rest of the chain.** Files are added root first, so the closest, most specific file is the one lost. Check the byte size of the root-to-folder chain, not only each file's line count.
- **`.claude/rules/` and `@path` imports are Claude features.** Content that lives only in `.claude/rules/` is invisible to Codex, Cursor and Gemini CLI (Grok Build reads it); an `@path` line in a shared `AGENTS.md` is plain text to agents that don't expand imports.

Claude also keeps its own **auto memory** at `~/.claude/projects/<project>/memory/` — loaded automatically every session. Division of labor: **CLAUDE.md = instructions you write** (team-shared, in git); **auto memory = learnings Claude writes** (personal, automatic). Don't hand-maintain session learnings in CLAUDE.md that auto memory already captures. Saying "remember X" lands in private auto memory — if the fact is team-relevant (a gotcha, env quirk, convention), say "add this to CLAUDE.md" instead so it's shared and versioned.

## Authoring workflow

**Scaffold a new file:**

1. Read `package.json`, `tsconfig.json`, README, and 1-2 source files to discover the actual conventions.
2. For each candidate section, ask: *"What does this project do that's NOT inferable from those files?"*
3. Empty sections are deleted, not stubbed with TODO.
4. `wc -l CLAUDE.md` to verify under 200 lines.

**Audit an existing file:**

1. Read the file fully.
2. Score every line against the falsifiability test.
3. Flag: framework name-drops (visible from package.json), file-by-file directory listings, embedded tutorials, vague rules, `IMPORTANT` overuse (>2 per file dilutes emphasis), contradictions across rules.
4. Propose a trimmed version as a unified diff. Don't auto-apply — CLAUDE.md is in git, let the user review.

## Compounding loop

After Claude makes a non-obvious mistake, end the correction with *"update your CLAUDE.md so you don't make that mistake again"* — Claude is good at writing rules for itself (use `/memory` to review what's loaded and edit). Commit to git; audit periodically and cut stale rules until the mistake rate measurably drops. The file compounds in value — each correction prevents the same mistake forever.

Route each learning to the right home: applies-every-session fact → **CLAUDE.md**; sometimes-relevant workflow or domain knowledge → **skill** (rule of thumb: anything you do more than once a day becomes a skill or command); must-always-happen action → **hook**.

## Common mistakes

- **Listing the framework stack.** `package.json` shows it.
- **Reproducing the directory tree.** Agent can `ls`.
- **`IMPORTANT` everywhere.** Reserve for ≤2 truly load-bearing rules (security, data loss).
- **Embedded tutorials.** A 30-line auth explanation goes in `docs/auth.md`. Link, don't inline.
- **Copying live state into the file.** Lines that say what's switched on, which workflows exist, or who owns a service go stale within days, and the agent acts on them as current: in one team's review of a repo's instruction files, 5 of 6 areas described that way were already wrong. Keep the rule and point to the command or file that reports the current state.
- **Using CLAUDE.md for must-happen or must-never-happen behavior.** CLAUDE.md is advisory (delivered as a user message, not the system prompt). Claude follows a prompted rule most of the time, and "most of the time" fails exactly where it matters — deep in a long session, in an ambiguous situation, or when a file read during the task carries a prompt injection. Real guardrails are deterministic, in escalating order: a **hook** (`PreToolUse` can inspect a call and exit 2 to block it) for formatters, lint gates, and dangerous commands; **permissions** for what tools may touch; and **managed settings** when it must hold org-wide — those are admin-deployed and a user's local config cannot override them.
