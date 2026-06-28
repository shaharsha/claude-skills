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

- Target: **under 200 lines** per file — official docs guidance: "Longer files consume more context and reduce adherence."
- Too long and Claude ignores half of it: important rules get lost in the noise.
- Use markdown headers (`## Build`, `## Style`) and bullets — not dense prose.
- If you cross 200 and can't trim, split conditional content into `.claude/rules/<topic>.md` with `paths:` frontmatter (loads only when matching files are read).
- Splitting into `@path` imports does **not** save context — imported files load in full at launch. Only `paths:`-scoped rules and skills reduce startup context.

## Specificity — every rule must be falsifiable

A reviewer should be able to point at code and say "this rule was violated."

| ❌ Vague | ✅ Concrete |
|---|---|
| "Format code properly." | "2-space indentation, no semicolons, single quotes." |
| "Test your changes." | "Run `bun run typecheck && bun test` before commit." |
| "Be careful with auth." | "JWT validated in `src/middleware.ts` only — never per-route." |

## Locations and loading

| File | Scope | Loaded |
|---|---|---|
| `./CLAUDE.md` | Team, in git | Every session |
| `./CLAUDE.local.md` | You, gitignored | Every session, after CLAUDE.md |
| `~/.claude/CLAUDE.md` | You, all your projects | Every session |
| `./.claude/rules/<topic>.md` with `paths:` | Per-glob | Only when matching files open |

Subdirectory CLAUDE.md files load on demand, not at session start. Claude Code reads `CLAUDE.md`, **not** `AGENTS.md` — if your repo has AGENTS.md (because you also use Codex / Cursor / Gemini CLI), create a CLAUDE.md whose first line is `@AGENTS.md` plus any Claude-specific additions (or symlink: `ln -s AGENTS.md CLAUDE.md`). `/init` reads an existing AGENTS.md (and `.cursorrules` etc.) when generating a CLAUDE.md.

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
- **Using CLAUDE.md for must-happen behavior.** CLAUDE.md is advisory (delivered as a user message, not the system prompt). Anything that must always run — formatters, lint gates, blocking dangerous commands — belongs in a hook, which is deterministic.
