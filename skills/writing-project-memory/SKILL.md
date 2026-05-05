---
name: writing-project-memory
description: Use when authoring or auditing a CLAUDE.md, AGENTS.md, or other project-level instruction file for an AI coding agent. Triggers on "write a CLAUDE.md", "draft a CLAUDE.md for this project", "audit my CLAUDE.md", "trim my CLAUDE.md", "is my CLAUDE.md too long", "what should go in my CLAUDE.md", "why isn't Claude following my CLAUDE.md", or the equivalent for AGENTS.md.
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

- Target: **under 200 lines.** Boris Cherny's own CLAUDE.md is ~100 lines.
- Past 200 lines, adherence drops. Past 400, the agent ignores half of it.
- Use markdown headers (`## Build`, `## Style`) and bullets — not dense prose.
- If you cross 200 and can't trim, split conditional content into `.claude/rules/<topic>.md` with `paths:` frontmatter (loads only when matching files are read).

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

Subdirectory CLAUDE.md files load on demand, not at session start. Claude Code reads `CLAUDE.md`, **not** `AGENTS.md` — if your repo has AGENTS.md (because you also use Codex / Cursor / Gemini CLI), create a CLAUDE.md whose first line is `@AGENTS.md` plus any Claude-specific additions.

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

After Claude makes a non-obvious mistake, ask *"add this to CLAUDE.md so it doesn't happen again"* (or use the `#` shortcut). Commit to git; audit periodically and cut stale rules. The file compounds in value — each correction prevents the same mistake forever.

## Common mistakes

- **Listing the framework stack.** `package.json` shows it.
- **Reproducing the directory tree.** Agent can `ls`.
- **`IMPORTANT` everywhere.** Reserve for ≤2 truly load-bearing rules (security, data loss).
- **Embedded tutorials.** A 30-line auth explanation goes in `docs/auth.md`. Link, don't inline.
