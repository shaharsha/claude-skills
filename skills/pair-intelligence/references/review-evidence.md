# Review evidence and troubleshooting

Everyday reviews need only `references/review.md`. Read this when a round looks
wrong, when you call `codex` by hand, or when rounds are the evidence for a merge
gate in a shared clone. Each rule here was paid for by a real failure.

## What the reviewer can and can't do

Read-only restricts writes, not thinking. Measured on codex-cli 0.145.0:

| | |
|---|---|
| Run commands — `git log`, `git diff`, `grep`, `nl`, `python3` | ✅ it does this unprompted |
| Read any file in the repo | ✅ |
| Write anywhere — repo, `/tmp`, `mkdir` | ❌ no writable location exists |
| Raw network — `curl`, `urllib`, `ping` | ❌ DNS resolution fails |
| Web search | ✅ with `--search` |
| **Look at images** — scans, screenshots, diagrams | ✅ `codex exec -i FILE` — see below |
| **Run the test suite or a build** | ❌ **see below** |

`--search` is worth adding when correctness depends on something outside the
repo: whether a library API is being used as documented, whether a version has a
known advisory, whether a protocol or format is being implemented correctly.
Leave it off for reviews of internal logic — it costs latency and adds another
untrusted-input channel for no gain. It works despite the network being blocked
because the search executes at OpenAI, not locally.

**The reviewer can see images.** `codex exec` takes `-i/--image FILE` (repeatable),
and the model reads them properly — measured 2026-08-18 on eight scans: a
photographed Hungarian invoice, two banking screenshots and several contract
pages. It transcribed printed figures accurately and independently matched a
second vision model on the one number a whole calculation depended on. That makes
this worth reaching for on anything the text layer cannot carry: scanned
paperwork, screenshots, rendered UI, diagrams, a photo of a whiteboard.

`scripts/pair.sh --image` handles this for you. If you hand-roll `codex exec` — and then `--search` is rejected
(`unexpected argument '--search' found`); the config key is the only route there
too, exactly as inside the script:

```bash
cat /abs/path/prompt.md | codex exec -s read-only \
  -c 'tools.web_search=true' -m gpt-6.1-sol -c model_reasoning_effort=high \
  -i shot1.png -i shot2.png > review.md 2>review.log
```

**Pipe the prompt — do not pass it as a trailing argument.** `--image` is a
greedy multi-value flag: it swallows the trailing positional prompt as if it were
another filename, leaving codex with no prompt at all. See the hang below.

**The reviewer cannot execute your code.** Anything needing a temp directory
dies under read-only — pytest fails outright with `No usable temporary directory
found`. So every claim it makes about runtime behaviour is inference from
reading, not observation. That is the single most useful thing to hold in mind
while adjudicating: it is often right, and it has no way to check itself.

Loosening the sandbox to fix this is a bad trade. A reviewer that can write can
be induced to write by anything it reads in the repo, and you would be running
an agent with a stated goal of finding fault and the ability to act on it. If a
finding genuinely hinges on runtime behaviour, run the test yourself — you have
the tools and the context to do it properly.

One narrow exception, and it turns on *what* the reviewer is pointed at. When the
target is a **disposable copy** rather than your working tree — evidence staged
into a scratch directory for this review — `-s workspace-write` gives the
reviewer a temp dir its own tooling needs while confining it to a directory you
can regenerate. That is a different bet from granting write access to real work,
and it is worth taking when the read-only sandbox is the thing blocking the
review. It is never `danger-full-access`, which reaches the whole filesystem.

## Confirm the round actually ran

A round that did not happen and a round that found nothing look identical in a
summary. Check the artifact, not your recollection of launching it:

```bash
ls -la .codex-review/<stamp>-<label>.md      # exists => a round happened
```

⚠️ **`ls` IS NOT ENOUGH WHEN SEVERAL SESSIONS SHARE ONE CLONE.** `.codex-review/`
in a main checkout is shared, and the default `--label` gives every concurrent
session the same `<stamp>-<label>.md` filename shape. Measured 2026-08-05: **43
`*-plan.log` files in one directory, five of them within four minutes of each
other**, and a lane read two adjacent-timestamp logs as their own failed round.
They were not — one belonged to a lane reviewing a different ticket entirely.

```bash
--label tor314-plan-r5-74f9f379          # ticket + phase + session, not "plan"
grep -l "$(basename "$PROMPT_FILE")" .codex-review/*.md   # confirm BY CONTENT
```

⚠️ **A GLOB FOR THE ROUND MATCHES THE PROMPT YOU WROTE FOR IT.** Measured 2026-08-24: a lane polled
`ls "$D"/*r2*.md` for its second round, matched its own `…-r2.prompt.md`, printed `R2 MD LANDED` and
reported the round complete. **It had not started** — no `.json`, no `.md`, and `verify_artifact.sh`
correctly said `CANNOT-TELL — artifact missing`. The prompt file is written *before* the round and
sits in the same directory, so **every substring glob naming the round matches it first**.

Match the **full artifact shape** — `.codex-review/<stamp>-<label>.md`, with `<label>` anchored at
the end — or better, key on the `.json`, which no prompt file can impersonate. And note what this
is: *the needle was never in the haystack*, the same defect a review round exists to find. The lane
that hit it had confirmed exactly that flaw in its own test code two hours earlier, fixed it, and
written the commit message about it — **then rebuilt it in the wait condition.**

**A unique label proves the file is yours only if you also wrote the label.
Content proves it either way.** One lane identified theirs by grepping each
candidate for their own plan's filename: **1 of 43 matched**, so the test had 42
negatives and could say no. Another used the `.provenance` prompt hash. Either
works; `ls` and a plausible timestamp does not.

**Working in your own worktree's `.codex-review/` avoids the collision entirely**
and is the better answer when you have a worktree.

**The `.md` is the evidence.** A `.log` with no sibling `.md` is a round that
died — commonly on a usage limit, which the CLI reports as ordinary output. The
script handles this correctly (`exit 70` when the JSON is empty, otherwise
codex's own status), so **the exit code is a real signal**.

⚠️ **A round can also never start, and that one does not exit at all.** If codex
receives no prompt it prints `Reading prompt from stdin...` and waits forever —
no error, no exit code, no `.md`, and a `.log` holding that single line. Measured
2026-08-18, twice in a row from two different causes: `-i/--image` greedily
consuming the trailing positional prompt as another filename, and zsh's
`read -r -d '' PROMPT <<'EOF'` leaving `PROMPT` empty. Both look exactly like a
reviewer thinking hard for twenty minutes. **A long-running round with a `.log`
whose last line is `Reading prompt from stdin...` is hung, not busy** — kill it
and pipe the prompt in on stdin.

⚠️ **A third cause, and it bites specifically when hand-rolling from Claude Code:
passing the prompt as an argument does NOT stop codex reading stdin.** `codex
exec [PROMPT]` appends stdin as a `<stdin>` block whenever stdin is not a TTY, so
a prompt argument plus an open, never-closing stdin — which is what a Claude Code
`Bash` call gives it — waits forever with the prompt already in hand. Measured
2026-08-21 on codex-cli 0.145.0: a 10-minute timeout whose entire log was
`Reading additional input from stdin...`. **Always redirect: `< /dev/null`.** The
wrapper pipes the prompt and is unaffected; this is a hand-rolling trap only.

### A round can run, exit 0, and have read nothing

⚠️ **Codex's own sandbox cannot always start inside another agent's sandbox, and
the round completes anyway.** Measured 2026-08-21, launching `codex exec` from a
Claude Code `Bash` call: every command the reviewer tried — `cat AGENTS.md`,
`pwd`, `git diff` — died with *"the shell host failed during handshake"*. Codex
was honest about it in its final message and **still exited 0 and still wrote a
findings artifact**. So this passes every check above: the `.md` exists, the
content grep matches, the exit code is 0. The only thing that catches it is
reading the artifact's own text.

**So the artifact check has two halves, not one.** *Does a `.md` exist* and *does
it show the reviewer actually reaching the source* — a cited `file:line`, a
quoted snippet, something it could only have obtained by reading. A findings file
whose content is an apology for not being able to look is a failed round wearing
a successful round's clothes.

The fix is to stop nesting the sandboxes. Run the review with the host sandbox
off (`dangerouslyDisableSandbox: true` on the Bash call) and let **codex** hold
the read-only boundary via `-s read-only`, which is the boundary that matters:
the reviewer still cannot write, and the review is still adversarial-safe. Do not
respond by loosening `-s` — that trades the wrong one away.

**The wrapper was measured in both directions on 2026-08-04 and is correct:** a
successful round exits 0 with the `.md` and `.json` both present; a failed round
leaves no `.json`, takes the empty-output branch, and exits non-zero. So when a
failed round appears to report 0, **the fault is in how you read the exit code,
never in the script.** Three lanes each destroyed it a different way that day:

- **Piping.** `codex_review.sh … | tail -6; echo $?` reports **`tail`'s** status.
  A pipeline returns its last element, and `tail` always succeeds. Same defect as
  piping `git push`. Don't pipe it; if you must, `set -o pipefail` first.
- **Backgrounding through a task runner.** The runner's "completed (exit code 0)"
  is a fact about *the task*, not about the script. Read the script's own status.
- **A trailing command.** A compound invocation ending in `echo` reports the
  `echo`'s status — which is 0 whether or not the script died.
- **`status=$?` under zsh** (measured 2026-08-18, a fourth way found later).
  `status` is a read-only builtin in zsh, so the assignment silently fails *and*
  aborts the rest of that command line — every check written after it never runs,
  while the transcript looks like it did. The skill's examples read naturally as
  bash; on a zsh box that one variable name is a trap. Use `rc=$?`.

All of these have one fix: **capture the status INSIDE the invocation**, before any
pipe or trailing command, so the number is a measurement of the script rather
than of your shell.

The `.md` check is worth keeping regardless, because it is invariant to how you
launched the round — which is exactly the property you want from the check that
decides whether a merge was reviewed.

**Where the artifact lands follows `--repo`.** Point it at a git worktree and the
artifact outlives the session; point it at a scratch directory and it does not.
If the round is the evidence that a merge was gated, put it somewhere durable and
quote the absolute path when you report the verdict.

### Has the artifact changed since it was written?

`.provenance` carries `artifact_sha256`, the digest of the `.md` as it finally
stands. `verify_artifact.sh` compares it (TOR-482, artifact-integrity check):

```bash
scripts/verify_artifact.sh .codex-review/<stamp>-<label>.md   # one artifact
scripts/verify_artifact.sh --dir .codex-review                # every .md there
scripts/verify_artifact.sh --self-test                        # prove its verdicts fire
```

```
UNCHANGED    (0)   a valid recorded digest, and it matches
CHANGED      (1)   a valid recorded digest, and it differs
CANNOT-TELL  (2)   there is nothing to check against
```

⚠️ **CANNOT-TELL is a real verdict, not a soft pass.** Every round generated before
this existed is in that class permanently, and that is a fact about the evidence
rather than a defect in the file. Reported as UNCHANGED it would certify an
artifact nobody examined; as CHANGED it would accuse one nobody examined.

⚠️ **CHANGED is not an accusation.** It means *differs from what was recorded at
generation*. Bytes cannot separate tampering from an honest regeneration — re-running
`render_review.py` over the same `.json` rewrites the `.md` legitimately and the
digest moves. Anything claiming to tell those apart is asserting a discrimination
the method does not have.

**Directory mode prints a coverage fraction — `N of M verified` — and never a bare
"clean".** It classifies *every* `.md` present, with no round/non-round predicate:
a file it cannot verify is reported as CANNOT-TELL rather than dropped, so nothing
can leave the denominator silently. Saying *"I cannot verify `PR-BODY-x.md`"* is
true and costs one line.

**A missing hash is written as `artifact_sha256=unavailable`**, never omitted and
never as a partial value — one honest answer for every way of not having a digest.

**Two runs starting in the same second with the same label no longer collide.** The
script reserves `$BASE` with an O_EXCL create and holds the lock for the whole run;
a same-second peer takes `-2`. Before that, both runs shared every output path, and
the survivor's sidecar could match the *other* run's artifact — a confident
UNCHANGED across two different rounds.

### Can anyone still read the prompt a round cited?

`verify_prompt.sh` is the sibling check: it hashes the prompt a `.provenance`
sidecar cites and compares it with the recorded `prompt_sha256`. For a plan round
the prompt is the whole claim, so a round whose prompt is gone has recorded a
verdict about a revision nobody has.

```bash
scripts/verify_prompt.sh .codex-review/<stamp>-<label>.md   # one round
scripts/verify_prompt.sh --dir .codex-review                 # every sidecar there
```

```
VERIFIED     (0)   the cited prompt resolved and hashes to prompt_sha256
BROKEN       (1)   it resolved and its bytes differ (an edited plan, usually)
CANNOT-TELL  (2)   nothing resolved, or nothing was recorded to check against
```

## Gotchas

- **`codex exec review` cannot take a custom prompt.** Combining a scope flag
  with prompt text fails with `error: the argument '--uncommitted' cannot be
  used with '[PROMPT]'`. Since the reviewer needs your intent to be useful, this
  skill uses plain `codex exec` and describes the scope in the prompt. Don't
  "simplify" it back to the `review` subcommand. **`--base <BRANCH>` is the same
  trap** and is the tempting one, because reviewing a branch against `main` is
  exactly the common case: `codex exec review --base main "<instructions>"` fails
  with `the argument '--base <BRANCH>' cannot be used with '[PROMPT]'`. You get
  the branch scope or your intent, never both — so state the scope in the prompt
  (`get the diff with: git diff main...HEAD`) and keep the intent.
- **`-C/--cd` is a parent-level flag and the `review` subcommand rejects it**
  (`error: unexpected argument '-C' found`), which reads like a bad path rather
  than a misplaced flag. `codex exec -C <dir> …` is fine.
- **`--output-schema` is silently ignored by `codex exec review`.** It is
  accepted, exits 0, and returns prose anyway. Structured findings only work via
  `codex exec`.
- **Codex ignores CLAUDE.md by default** and reads only AGENTS.md. The script
  passes `-c 'project_doc_fallback_filenames=["CLAUDE.md"]'`, which promotes
  CLAUDE.md to a real instruction file for the run, so no AGENTS.md is needed
  anywhere. Codex resolves one file per directory in the order
  `AGENTS.override.md` → `AGENTS.md` → CLAUDE.md, which gives the precedence you
  want for free: a project that has written an AGENTS.md keeps using it, and
  CLAUDE.md fills in only where there is none. Verified on codex-cli 0.145.0
  across all three cases.
- **Claude Code's `@import` lines are not expanded** by Codex, so imported
  content silently doesn't reach the reviewer, and `~/.claude/CLAUDE.md` is
  never read at all (Codex's global slot is `~/.codex/AGENTS.md`). Inline
  anything the reviewer genuinely needs into the project file.
- **Read-only is forced by the script**, not inherited. A global
  `sandbox_mode = "danger-full-access"` in `~/.codex/config.toml` is common and
  would otherwise apply. Don't remove those flags.
- **A resumed session does not inherit its sandbox.** `codex exec resume` takes
  no `-s` flag, which reads like the sandbox belongs to the session — it does
  not. Measured on codex-cli 0.145.0: resuming a session created with
  `-s read-only` reported `sandbox: danger-full-access`, silently picking up the
  global config. The script therefore passes `-c sandbox_mode="read-only"` on
  every invocation, resume included. If you ever hand-roll a
  `codex exec resume`, pass it yourself and check the header line the run prints.
- **`--prompt-file` must be an ABSOLUTE path.** The script `cd`s into `--repo`, so a relative path is
  resolved against the repo directory, not your shell's cwd. Measured on 2026-08-18: passing
  `--prompt-file review2/README.md` from the parent directory died with
  `codex_review.sh: line 306: review2/README.md: No such file or directory` and **exit 1**, leaving a
  `.log` with no sibling `.md`. That is the same signature as a round killed by a usage limit, so the
  cause is not obvious from the artifacts — and it is easy to misread a path typo as a dead reviewer.
  The `.md`-exists check above catches it either way; this note just saves you the diagnosis. Passing
  a path *inside* the repo is fine and even useful (the reviewer can then read it as a repo file) —
  but write it absolute.

- **Artifacts land in `.codex-review/`**, which the script adds to
  `.git/info/exclude` — local to the clone, so it never shows up as a repo
  change.

