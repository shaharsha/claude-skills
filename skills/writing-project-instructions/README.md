# writing-project-instructions

Author or audit a `CLAUDE.md` / `AGENTS.md` project-instruction file — the file an AI coding agent reads at the start of every session for project context. Encodes Anthropic's cardinal include/exclude rules, the under-200-line target, the falsifiability test, locations and loading semantics, AGENTS.md interop, and the compounding-engineering loop.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

A project-instruction file compounds in value and bloats just as easily, and the failure is counterintuitive: **a longer file gets followed less.** Rules get lost in noise, so the natural response to "the agent ignored my instruction" — adding another, more emphatic instruction — makes the problem worse.

There's also a lot of folklore around these files that's subtly wrong, and the skill exists partly to correct it:

- **The 200-line target is soft, and people over-index on it.** CLAUDE.md is *never truncated* — it loads in full regardless of length; adherence just decays gradually. Nothing breaks at line 201. A 250-line file of real foot-guns beats a 190-line file that cut them to hit a number.
- **The *hard* 200-line/25 KB cap is a different file.** That's auto-memory's `MEMORY.md`, where content past the limit is silently dropped at load. Conflating the two leads people to gut a CLAUDE.md for no reason.
- **Splitting into `@path` imports saves nothing.** Imported files load in full at launch. Only `paths:`-scoped rules and skills reduce startup context.
- **`.claude/rules/` is Claude-only.** If a repo keeps instructions in AGENTS.md for cross-agent parity, moving content into `.claude/rules/` makes it invisible to Codex, Cursor, and Gemini — breaking the exact parity AGENTS.md exists for.
- **CLAUDE.md is advisory, not deterministic.** It's delivered as a user message, not the system prompt. Anything that *must* always happen — formatters, lint gates, blocking dangerous commands — belongs in a hook.

## What it does

```
new file?  ──▶ read package.json / tsconfig / README / 1-2 sources
                   │  "what does this project do that ISN'T inferable from those?"
                   ▼
             scaffold ──▶ delete empty sections ──▶ wc -l

existing?  ──▶ score every line against the falsifiability test
                   │  flag: framework name-drops · directory trees · embedded
                   │        tutorials · vague rules · IMPORTANT overuse ·
                   │        contradictions · stale tool references
                   ▼
             propose a unified diff — never auto-apply
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install building-agents@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/writing-project-instructions" ~/.claude/skills/writing-project-instructions
```

## Quick start

No scripts — this is guidance the agent loads before it touches an instruction file. It should fire on any of:

- "write a CLAUDE.md for this repo"
- "my CLAUDE.md is too long — trim it"
- "why isn't Claude following my CLAUDE.md?"
- "add this rule to AGENTS.md"

It's meant to load before *any* edit to one of these files, including a one-line addition — that's when the wrong line most often gets added.

## The single most important test

Before keeping any line, ask:

> **"Would removing this cause the agent to make a specific, identifiable mistake?"**

If you can't articulate the mistake the line prevents, cut the line.

## What to include vs exclude

| ✅ Include | ❌ Exclude |
|---|---|
| Bash commands the agent can't guess (`bun test`, custom scripts) | Anything visible from `package.json`, `tsconfig.json`, or `ls` |
| Code style rules that **differ** from language defaults | Standard conventions (`async/await`, `const` over `var`) |
| Repository etiquette (branch naming, commit format, PR rules) | Self-evident practices ("write clean code") |
| Architectural decisions specific to the project (why X not Y) | Long explanations — link to `docs/X.md` instead |
| Required env vars, ports, OS quirks | File-by-file directory listings — the agent can `ls` |
| Common gotchas and non-obvious foot-guns | Stale rules referencing tools you no longer use |

## Every rule must be falsifiable

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
| `~/.claude/CLAUDE.md` | You, all projects | Every session |
| `./.claude/rules/<topic>.md` with `paths:` | Per-glob | Only when matching files open |

Subdirectory CLAUDE.md files load on demand, not at session start. Claude Code reads `CLAUDE.md`, **not** `AGENTS.md` — if your repo has AGENTS.md for cross-agent parity, add a CLAUDE.md whose first line is `@AGENTS.md`, or symlink it.

## Gotchas

- **`IMPORTANT` everywhere dilutes it.** Reserve for ≤2 genuinely load-bearing rules (security, data loss).
- **Don't hand-maintain in CLAUDE.md what auto memory already captures.** CLAUDE.md = instructions you write, team-shared, in git. Auto memory = learnings the agent writes, personal, automatic. Saying "remember X" lands in *private* auto memory — if the fact is team-relevant, say "add this to CLAUDE.md" so it's shared and versioned.
- **Don't auto-apply an audit.** The file is in git; propose the diff and let a human review it.
- **Run `/doctor`** (Claude Code v2.1.206+) for trims proposed against the real criteria — it cuts what the agent can derive from the codebase and keeps pitfalls and rationale. Better than eyeballing.

## The compounding loop

After the agent makes a non-obvious mistake, end the correction with *"update your CLAUDE.md so you don't make that mistake again."* Commit it, audit periodically, cut stale rules. Each correction prevents the same mistake forever.

Route each learning to its right home: applies-every-session fact → **CLAUDE.md**; sometimes-relevant workflow or domain knowledge → **a skill**; must-always-happen action → **a hook**.

## Related skills

- [prompt-engineer](../prompt-engineer) — the sibling for API-level system prompts and tool descriptions, as opposed to instructions for a coding agent.

## License

MIT — see [LICENSE](../../LICENSE).
