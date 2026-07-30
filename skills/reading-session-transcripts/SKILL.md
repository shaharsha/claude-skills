---
name: reading-session-transcripts
description: Use when you need to know what another agent session did, said or decided — auditing parallel sessions running in worktrees, finding which session owns a branch or PR, checking whether one is blocked or has drifted onto someone else's ticket, or recovering a session that vanished from the session list. Also use when a finding exists only in a session's prose and not in any diff, PR or ticket, or when a `.jsonl` transcript is too large to read with grep, jq or cat. Triggers include "what is that other session doing", "which session opened this PR", "look at all the sessions", "read the session jsonl", "my session disappeared", "did another session already fix this".
---

# Reading session transcripts

## Core principle

**A session's reasoning survives only in its prose.** The diff shows what changed; the PR shows the pitch; the ticket shows the plan. What the session *found*, what it refuted, what it flagged about its own work, and what it decided not to do exist nowhere but the transcript.

A transcript is ~95% tool calls and tool results. Reading it with `cat`, `grep` or `jq` buries the conversation under machine noise — which is why the interesting parts get missed.

## When to use

- Several sessions run in parallel and you need to know what each is doing, or whether two have collided
- A PR, branch or commit appeared and you need its owner
- A session is idle and you need to know whether it is blocked on a question
- A session disappeared from the session list
- You suspect work was already done, or already refuted, somewhere else
- You are about to repeat an investigation another session may have finished

**Not for:** reading your own current conversation, or grepping code. Use ordinary tools for those.

## Quick reference

`scripts/ccread` — stdlib Python, no install.

| Need | Command |
|---|---|
| What's running, and what's stale | `ccread` |
| Only recent | `ccread --since 2026-07-29` |
| Read one session's conversation | `ccread "TOR-55"` |
| What is it doing right now | `ccread <id> --last 20` |
| Only since this morning | `ccread <id> --from 06:00` |
| With tool calls interleaved | `ccread <id> --tools` |
| Find a topic in one session | `ccread <id> --grep codex` |
| Find a topic across all sessions | `ccread --all --grep "credential" --since 2026-07-29` |

Sessions resolve by id prefix **or** title/cwd substring, so `ccread "TOR-55"` beats copying a uuid.

The listing marks 🟢 active / 🟡 recent / ⚪ stale, plus `worktree-filed` and `N copies` — see *Orphaned transcripts* below.

Run `ccread --help` for the rest.

## How transcripts are stored

Three facts explain nearly every surprise:

1. **A transcript is filed by cwd**, at `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`. The slug encodes the directory the session ran in.
2. **A session that changes directory gets a new file** under the new slug. One session can therefore have several copies on disk, only the newest of which is current.
3. **Most `type: "user"` entries are not from a human.** They carry `tool_result` blocks. A real human turn is a bare string, or a list containing a `text` block — and even then the harness injects turns (skill re-invocations, compaction notices, interrupt markers) that read like speech.

`ccread` handles all three. If you parse transcripts by hand, handle them yourself or your answer will be wrong.

## Orphaned transcripts

Deleting a worktree does not delete the transcript of a session that ran in it — it strands it. The file stays under a project directory whose folder no longer exists, so the session vanishes from the harness's list while sitting intact on disk. `ccread` still finds it and flags it `worktree-filed`.

To make it openable again, copy it into the surviving project's directory and repoint its `cwd`:

```python
import json
SRC, DST = "<orphan>.jsonl", "<project-dir>/<same-name>.jsonl"
STALE, NEW = "/path/to/deleted/worktree", "/path/to/main/checkout"
with open(SRC) as fi, open(DST, "w") as fo:
    for line in fi:
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except ValueError:
            fo.write(line)          # keep unparseable lines byte-for-byte
            continue
        c = o.get("cwd")
        if isinstance(c, str) and c.startswith(STALE):
            o["cwd"] = NEW + c[len(STALE):]
        fo.write(json.dumps(o, ensure_ascii=False) + "\n")
```

**Parse per line; never `sed` the file.** A transcript is full of commands that mention its own worktree path. A find-replace "fixes" the file by silently falsifying the session's record of what it actually ran — and that record is the whole reason the file is worth keeping. Copy rather than move, so a live session writing to the original is undisturbed.

## Common mistakes

| Mistake | What happens | Instead |
|---|---|---|
| Reading only tool calls | You see what ran, not what was concluded. The finding is in the prose. | Read the conversation first; add `--tools` when you need the mechanics |
| `--from 07:00` on an overnight session | Matches 07:00 **every** day it ran, so yesterday leaks in | `ccread` anchors a bare `HH:MM` to the session's last day; pass a full ISO stamp to be explicit |
| Filtering sessions by date but not turns | A months-long session passes the filter, then dumps months of prose | `--since` bounds both |
| Treating every `type: "user"` as the human | Tool results and injected notices drown the real instructions | Take only `text` blocks, and drop harness-injected ones |
| Assuming one file per session | You read a stale copy and report outdated conclusions | Take the newest copy per session id |
| `sed`-ing a transcript to repair paths | Rewrites the session's own recorded commands | Parse per line, touch only the top-level `cwd` |

## Real-world impact

On one day of eight parallel sessions, reading prose rather than diffs surfaced: a session disclosing that it had leaked a production credential into its own log; a session that independently refuted a measurement three other sessions had built on; a session that checked out a different branch inside another session's worktree; and a session's own verdict that its rollout was *"verified but not verifiable"* — which is what produced the check that replaced it.

None of that appears in a commit, a PR body, or a ticket.
