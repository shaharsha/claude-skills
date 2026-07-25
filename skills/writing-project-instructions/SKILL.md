---
name: writing-project-instructions
description: Use when authoring, editing, updating, trimming, or adding rules to a CLAUDE.md, AGENTS.md, CLAUDE.local.md, or other project-level instruction file for an AI coding agent — including small one-line changes. Triggers on "write a CLAUDE.md", "audit my CLAUDE.md", "trim my CLAUDE.md", "is my CLAUDE.md too long", "what should go in my CLAUDE.md", "why isn't Claude following my CLAUDE.md", "add this to CLAUDE.md", "edit CLAUDE.md", "update CLAUDE.md", "put a rule in CLAUDE.md", "remember this in CLAUDE.md", or the equivalent for AGENTS.md. Always load this skill before modifying any CLAUDE.md/AGENTS.md, not just when explicitly asked.
---

# Writing project memory

CLAUDE.md (and the cross-agent equivalent AGENTS.md) is the file an AI coding agent reads at the start of every session for project context. It compounds in value but bloats easily, and bloated files get ignored — Claude drops rules when the file is too long.

## The single most important test

Before keeping any line, ask: **"Would removing this cause the agent to make a specific, identifiable mistake?"**

If you can't articulate the specific mistake the line prevents, cut the line.

## What to include vs exclude (Anthropic's cardinal rule)

| ✅ Include | ❌ Exclude |
|---|---|
| Bash commands the agent can't guess (`bun test`, custom scripts) | Anything visible from `package.json`, `tsconfig.json`, or `ls` |
| Code style rules that **differ** from language defaults | Standard conventions (`async/await`, `const` over `var`, etc.) |
| Repository etiquette (branch naming, commit format, PR rules) | Self-evident practices ("write clean code", "be helpful") |
| Architectural decisions specific to the project (why X not Y) | Long explanations or tutorials — link to `docs/X.md` instead |
| Required env vars, ports, OS quirks | File-by-file directory listings — the agent can `ls` |
| Common gotchas / non-obvious foot-guns | Stale rules referencing tools you no longer use |

## Length and structure

- Target: **under 200 lines** per file. Official wording: *"target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."*
- **It's a soft target, not a cliff — don't over-index on it.** CLAUDE.md is **never truncated**: *"CLAUDE.md files are loaded in full regardless of length, though shorter files produce better adherence."* Nothing breaks at line 201; adherence decays gradually. A 250-line file of real foot-guns beats a 190-line file that cut them to hit a number.
- **Don't confuse it with the auto-memory cap.** The *hard* 200-line/25KB limit applies only to auto memory's `MEMORY.md`, where content past the limit is **silently dropped** at load. Different file, different rule.
- Too long and Claude ignores half of it: important rules get lost in the noise.
- Use markdown headers (`## Build`, `## Style`) and bullets — not dense prose.
- **Run `/doctor`** (v2.1.206+) to get trims proposed against the real criteria: it cuts what Claude can derive from the codebase (directory layouts, dependency lists, architecture overviews) and keeps pitfalls, rationale, and conventions that differ from tool defaults. Prefer it to eyeballing. It rightsizes **skills** as well as CLAUDE.md files.
- **In a shared repo, give the file an owner and review changes to it like code.** CLAUDE.md grows the way any unowned config file does — every team appends, nobody deletes — and every line then loads for every engineer on every session whether it's relevant or not. In a monorepo, give each team's directory its own subdirectory CLAUDE.md; developers can set `claudeMdExcludes` to skip files from teams whose code they never touch.
- If you cross 200 and can't trim, split conditional content into `.claude/rules/<topic>.md` with `paths:` frontmatter (loads only when matching files are read).
- ⚠️ **`.claude/rules/` is Claude-only.** If the repo keeps instructions in `AGENTS.md` for cross-agent parity (Codex/Cursor/Gemini read it; Claude reaches it via `@AGENTS.md`), moving content into `.claude/rules/` makes it **invisible to every other agent**. Weigh the context saving against breaking the parity AGENTS.md exists for — usually not worth it for a few lines.
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

Claude Code reads `CLAUDE.md`, **not** `AGENTS.md` — if your repo has AGENTS.md (because you also use Codex / Cursor / Gemini CLI), create a CLAUDE.md whose first line is `@AGENTS.md` plus any Claude-specific additions (or symlink: `ln -s AGENTS.md CLAUDE.md`). `/init` reads an existing AGENTS.md (and `.cursorrules` etc.) when generating a CLAUDE.md.

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
- **Using CLAUDE.md for must-happen or must-never-happen behavior.** CLAUDE.md is advisory (delivered as a user message, not the system prompt). Claude follows a prompted rule most of the time, and "most of the time" fails exactly where it matters — deep in a long session, in an ambiguous situation, or when a file read during the task carries a prompt injection. Real guardrails are deterministic, in escalating order: a **hook** (`PreToolUse` can inspect a call and exit 2 to block it) for formatters, lint gates, and dangerous commands; **permissions** for what tools may touch; and **managed settings** when it must hold org-wide — those are admin-deployed and a user's local config cannot override them.
