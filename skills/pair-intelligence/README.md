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

Any mode can add a live browser with `--domains`: a review can open the running
page and compare it with the code, and the model stays read-only.

Engines: **Codex** (`gpt-6.1-sol`, OS sandbox, web search) and **Gemini**
(`gemini-4-argon` through the Antigravity CLI `agy`, behind a default-deny tool
gate, with Google search; OpenCode as a fallback). Ask one, or both in parallel
for two independent reads.

`scripts/pair.sh` runs any mode on either engine and handles the traps these CLIs
share: hangs on an open stdin, exit 0 after a failed turn (agy even reports a
timed-out partial answer as success), a resumed session that silently drops its
sandbox, no timeout. `scripts/codex_review.sh` stays the Codex
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
- **Gemini:** the Antigravity CLI `agy` (tested on 1.4.12) with either Vertex AI
  credentials (an `~/.config/gcloud/adc-agy-<project>.json` copy of your ADC file
  whose `quota_project_id` is the project to bill) or a Gemini API key in
  `GEMINI_API_KEY`. Never your Antigravity login. Or `--backend opencode` with the
  OpenCode desktop app (its v2 CLI, tested on 2.2.5).
- **A live browser:** the `agent-browser` CLI.
- `python3` and macOS or Linux. No API key of its own.

## Setup

What a run needs inside the run (agy's private home and tool gate, the browser
host, its socket and the Codex broker), `pair.sh` builds itself and removes
afterwards. Set up once only what you will use:

**Codex**

```bash
brew install --cask codex      # or: npm install -g @openai/codex
codex login                    # a ChatGPT plan
```

**Gemini, with an API key** (the quick route)

```bash
brew install --cask antigravity-cli
export GEMINI_API_KEY=...      # from Google AI Studio; OpenCode's saved Google key also works
```

**Gemini, on Vertex AI** (bills a GCP project, so startup credits apply). Best:
a service account with only the Vertex AI User role, whose key never expires:

```bash
gcloud iam service-accounts create pair-intelligence-agy --project MY_PROJECT
gcloud projects add-iam-policy-binding MY_PROJECT --role roles/aiplatform.user \
  --member serviceAccount:pair-intelligence-agy@MY_PROJECT.iam.gserviceaccount.com
(umask 077; gcloud iam service-accounts keys create ~/.config/gcloud/adc-agy-sa-MY_PROJECT.json \
  --iam-account pair-intelligence-agy@MY_PROJECT.iam.gserviceaccount.com)
```

If your organization blocks key creation (`iam.disableServiceAccountKeyCreation`,
on by default in newer organizations), lift it on that project only
(`gcloud resource-manager org-policies disable-enforce
iam.disableServiceAccountKeyCreation --project MY_PROJECT`), create the key, then
restore it (`gcloud resource-manager org-policies delete
iam.disableServiceAccountKeyCreation --project MY_PROJECT`): an existing key keeps
working. The other way is a copy of your own login pinned to the project (agy
takes the project from the file's `quota_project_id`); Google ends that login on
a schedule, so it needs renewing:

```bash
gcloud services enable aiplatform.googleapis.com --project MY_PROJECT
gcloud auth application-default login
python3 -c 'import json, os
d = os.path.expanduser("~/.config/gcloud")
adc = json.load(open(d + "/application_default_credentials.json"))
adc["quota_project_id"] = "MY_PROJECT"
os.umask(0o077)
json.dump(adc, open(d + "/adc-agy-MY_PROJECT.json", "w"))'
```

With exactly one `adc-agy-*.json` present, Gemini runs on Vertex AI (a run's
`meta.json` records `auth: vertex:<project>`); `PAIR_AGY_AUTH=key` forces the API
key. Google ends this login on a schedule; when it has, `pair.sh` falls back to
the API key and prints the fix: `gcloud auth application-default login`, then
redo the copy.

**A live browser**

```bash
npm install -g agent-browser
agent-browser install          # downloads its browser
```

**Check it**: `bash scripts/test_pair.sh` runs offline; `bash scripts/pair.sh
--selftest` checks the live CLIs (a few cents: two short Gemini turns and one
short Codex turn), worth rerunning after an agy or codex upgrade. A missing CLI
or credential makes `pair.sh` exit 69 with a message naming what to install or
set.

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

# A review that checks the code against the running page (Codex stays read-only)
bash scripts/codex_review.sh --repo /abs/repo --domains localhost:5173 \
  --prompt-file /abs/review.md --label ui-change

# A review where Codex may run the tests, in a disposable copy with no network
bash scripts/codex_review.sh --repo /abs/repo --runnable \
  --prompt-file /abs/review.md --label with-tests

# A Codex code review with structured findings
bash scripts/codex_review.sh --repo /abs/repo --prompt-file /abs/review.md --label my-change
```

Every `pair.sh` run prints `STATUS=` and ends with `ANSWER=<path>`; `codex_review.sh`
ends with `REVIEW_MD=<path>`. See [SKILL.md](SKILL.md)
for how to write each prompt and judge the answer.

## Testing changes

`bash scripts/test_pair.sh` runs offline against fake `codex`, `agy`, `opencode`
and `agent-browser` binaries: sandbox flags on every call (resume included), exit
codes for each way a turn ends, the agy tool gate against zsh expansion and secret
files, `pair-fs` confinement and its git rules, the browser wrapper's grammar and
local-port pinning, the Codex broker and preflight, and the review runner's
non-git and `--out-dir` paths. It spends no model quota.

## Gotchas

- Both engines can read files beyond the ones you name and send what they read to
  their vendor. Redact secrets, and keep answer keys away from them.
- Codex reaches the browser through a broker socket and otherwise has no network,
  in every mode. With `--runnable` it can run tests in a disposable copy of the
  repo, still without network, so tests that download anything fail.
- Gemini's secret-file protection works by file name (`.env`, key files); a
  secret pasted into an ordinary file is just text to it.
- A Vertex AI project's tokens-per-minute quota can run out on a long Gemini
  review (`429 RESOURCE_EXHAUSTED`, `STATUS=quota`, exit 75); retry later, lower
  `--web-budget`, or set `PAIR_AGY_AUTH=key`.
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
