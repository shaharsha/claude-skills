# claude-skills

Personal Agent Skills library, published as the `shaharsha-skills` marketplace. Each skill is a folder under `skills/<name>/` with a `SKILL.md`. Skills are consumed by Claude Code, Codex, Cursor, and other Agent-Skills harnesses — keep them harness-agnostic (no assumptions about a specific host's tools).

**Edit skills here, in this repo.** Each is symlinked into `~/.claude/skills/<name>`, so that path *is* this repo — don't expect a separate editable copy under `~/.claude/skills`.

## Adding or renaming a skill — update ALL of these

Miss one and the skill ships half-wired (installs but isn't listed, or is listed but 404s):

1. `skills/<name>/SKILL.md` — frontmatter `name` + `description`. The description is *when to trigger* (third-person "Use when…", keyword-rich); it's the only thing that makes the skill fire, so it is not a workflow summary.
2. `skills/<name>/README.md` — the GitHub landing page for that folder. **SKILL.md is for the model; README.md is for the human** — it links into SKILL.md and `reference/` rather than restating procedure. Sections: pitch, why it exists, what it does, install (marketplace + monorepo path), requirements, quick start, gotchas, related skills, license. Copy the shape from any existing one.
3. `.claude-plugin/marketplace.json` — add `./skills/<name>` to the **main `shaharsha-skills` plugin** (and update its "All N skills" count in that plugin's description) **and** to the fitting **category plugin**; bump `metadata.version`.
4. `README.md` — the matching `/plugin install <category>@shaharsha-skills` comment line, plus a one-line row in that category's table. One sentence, not a paragraph — the long description lives in the skill's own README.
5. `~/Projects/shahar-sh/public/skills.html` — **separate repo.** Add a skill card, append the name to the `<meta name="description">` list, and bump the two "N skills" counts. Pushing `main` there auto-deploys to Cloudflare Pages (`gh run watch` to confirm).
6. `ln -s "$PWD/skills/<name>" ~/.claude/skills/<name>` — the symlink that makes it loadable locally.

**Cross-skill links:** relative (`../<name>`) only for skills *in this repo* — they must resolve on GitHub. Anything else gets an upstream URL (Anthropic's live at `github.com/anthropics/skills/tree/main/skills/<name>`) or plain text. A `../<name>/` pointing outside `skills/` is always a 404.

## Naming

A skill `name` must not contain `claude` or `anthropic` — the Agent-Skills spec rejects those at marketplace validation. Use hyphenated, gerund-leaning names (`writing-project-instructions`, not `claude-md-writer`).

## Scripts inside a skill

- Prefer **stdlib-only Python** (or plain bash) so a skill runs with no `pip install`.
- Ship a per-skill `.gitignore` covering `__pycache__/`, `*.pyc`, and credential files.
- **Never commit API keys.** Read them from an env var or `~/.config/<tool>/…`; never hardcode a key in a script or a committed command.

## Authoring & meta

Default branch `main`. For *how* to write and test a skill, use the `skill-creator` and `superpowers:writing-skills` skills; for this file, `writing-project-instructions`.
