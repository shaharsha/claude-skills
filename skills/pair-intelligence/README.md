# pair-intelligence

Give your coding agent a second model to think with. Claude Code (or any
Agent-Skills harness) calls Codex or Gemini through its CLI to review a plan or
diff, give a second opinion, brainstorm over several rounds, research the web,
look at screenshots, or drive a browser, and then checks every claim the other
model makes against the source.

## Why this exists

A model reviewing its own work in its own context finds less than a different
model reading the same artifact cold. But a second model's answer is a list of
claims, not a verdict: some are defects you missed, some are confident nonsense.
This skill standardises both halves: how to ask (fresh context, facts instead of
your conclusions, the right permissions for the job) and how to judge the answer.

It started as `codex-review`, a Codex-only reviewer. Baseline tests on other
tasks (a decision, a brainstorm, a screenshot, a live page) showed the model was
good at all of them and the review-only tooling was in the way every time.

## What it does

| Mode | For | Engine permissions |
|---|---|---|
| review | plans, diffs, code against its plan, before merge | read-only |
| consult | choosing between options, diagnosing, checking a claim | read-only |
| ideate | brainstorming in up to 3 structured rounds | read-only, empty working dir |
| research | web search, docs, images | read-only, empty working dir |
| browse | opening, clicking and screenshotting real pages | isolated browser, allow-listed domains |

Engines: **Codex** (`gpt-6.1-sol`, OS sandbox, web search) and **Gemini**
(`gemini-4-argon` through OpenCode v2, read-only by agent rules). Ask one, or both
in parallel for two independent reads.

`scripts/pair.sh` runs any mode on either engine and handles the traps both CLIs
share: hangs on an open stdin, exit 0 after a failed turn, a resumed session that
silently drops its sandbox, no timeout. `scripts/codex_review.sh` stays the Codex
review runner, with schema-enforced findings and a provenance sidecar.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install engineering-decisions@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/pair-intelligence" ~/.claude/skills/pair-intelligence
```

## Requirements

- **Codex:** the `codex` CLI on `$PATH`, signed in (tested on 0.165.0).
- **Gemini:** the OpenCode desktop app (its v2 CLI, tested on 2.2.5) with a Gemini
  API key added to OpenCode.
- **Browse:** the `agent-browser` CLI.
- `python3` and macOS or Linux. No API key of its own.

## Quick start

```bash
# A second opinion from Codex on a decision, run inside the repo it concerns
bash scripts/pair.sh --engine codex --mode consult --cwd /abs/repo \
  --prompt-file /abs/question.md

# The same question to Gemini, for an independent read
bash scripts/pair.sh --engine gemini --mode consult --cwd /abs/repo \
  --prompt-file /abs/question.md

# Brainstorm: name the session, then continue it
bash scripts/pair.sh --mode ideate --prompt-file /abs/round1.md --name names
bash scripts/pair.sh --mode ideate --prompt-file /abs/round2.md --resume names

# Have Codex browse an allow-listed site and take screenshots
bash scripts/pair.sh --mode browse --domains example.com --prompt-file /abs/task.md

# A Codex code review with structured findings
bash scripts/codex_review.sh --repo /abs/repo --prompt-file /abs/review.md --label my-change
```

Every `pair.sh` run prints `STATUS=` and ends with `ANSWER=<path>`; `codex_review.sh`
ends with `REVIEW_MD=<path>`. See [SKILL.md](SKILL.md)
for how to write each prompt and judge the answer.

## Testing changes

`bash scripts/test_pair.sh` runs offline against fake `codex`, `opencode` and
`agent-browser` binaries: sandbox flags on every call (resume included), exit codes
for each way a turn ends, Gemini's prompt on stdin, browse teardown, and the review
runner's non-git and `--out-dir` paths. It spends no model quota.

## Gotchas

- Both engines can read files beyond the ones you name and send what they read to
  their vendor. Redact secrets, and keep answer keys away from them.
- Browsing with Codex needs network access in its sandbox, so it can reach other
  hosts with curl; the domain allow-list binds only the browser.
- Gemini through OpenCode has no web search, and your global OpenCode config
  (including its MCP servers) still loads.
- Two models agreeing is weak evidence; they share many errors. Where they
  disagree is where to look.

## Related skills

- [tech-design-doc](../tech-design-doc) authors the design docs this reviews in
  plan mode.
- [writing-project-instructions](../writing-project-instructions) writes the
  `CLAUDE.md` / `AGENTS.md` that Codex loads as the project's rules.
- [prompt-engineer](../prompt-engineer) is the reference behind the prompt shapes:
  outcome-first framing and why stating your conclusion biases the reviewer.

## License

MIT, see [LICENSE](../../LICENSE).
