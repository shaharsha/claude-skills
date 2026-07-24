# claude-skills

Personal Agent Skills library, published as the `shaharsha-skills` marketplace. Each skill is a folder under `skills/<name>/` with a `SKILL.md`. Skills are consumed by Claude Code, Codex, Cursor, and other Agent-Skills harnesses — keep them harness-agnostic (no assumptions about a specific host's tools).

**Edit skills here, in this repo.** Each is symlinked into `~/.claude/skills/<name>`, so that path *is* this repo — don't expect a separate editable copy under `~/.claude/skills`.

## Adding or renaming a skill — update ALL of these

Miss one and the skill ships half-wired (installs but isn't listed, or is listed but 404s):

1. `skills/<name>/SKILL.md` — frontmatter `name` + `description`. The description is *when to trigger* (third-person "Use when…", keyword-rich); it's the only thing that makes the skill fire, so it is not a workflow summary.
2. `.claude-plugin/marketplace.json` — add `./skills/<name>` to the **main `shaharsha-skills` plugin** (and update its "All N skills" count in that plugin's description) **and** to the fitting **category plugin**; bump `metadata.version`.
3. `README.md` — the matching `/plugin install <category>@shaharsha-skills` comment line, plus a `#### [<name>](skills/<name>)` entry with a description paragraph.
4. `~/Projects/shahar-sh/public/skills.html` — **separate repo.** Add a skill card and append the name to the `<meta name="description">` list. Pushing `main` there auto-deploys to Cloudflare Pages (`gh run watch` to confirm).
5. `ln -s "$PWD/skills/<name>" ~/.claude/skills/<name>` — the symlink that makes it loadable locally.

## Naming

A skill `name` must not contain `claude` or `anthropic` — the Agent-Skills spec rejects those at marketplace validation. Use hyphenated, gerund-leaning names (`writing-project-instructions`, not `claude-md-writer`).

## Scripts inside a skill

- Prefer **stdlib-only Python** (or plain bash) so a skill runs with no `pip install`.
- Ship a per-skill `.gitignore` covering `__pycache__/`, `*.pyc`, and credential files.
- **Never commit API keys.** Read them from an env var or `~/.config/<tool>/…`; never hardcode a key in a script or a committed command.

## Authoring & meta

Default branch `main`. For *how* to write and test a skill, use the `skill-creator` and `superpowers:writing-skills` skills; for this file, `writing-project-instructions`.
