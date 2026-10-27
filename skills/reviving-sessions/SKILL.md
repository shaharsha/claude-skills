---
name: reviving-sessions
description: Use when a Claude Code session exists on disk but the Claude desktop app does not list, open or name it - a session started with `claude -p` or from a shell script, from the VS Code extension, or under another account; a session that vanished from the sidebar after its worktree was deleted; headless lanes all called "General coding session"; a rename that answers "not found", reports success and changes nothing, or shows different names in two accounts; or when you need what an ENDED or Desktop-invisible session said and its .jsonl transcript is too large for cat or grep. Triggers include "my session disappeared", "why don't I see my sessions in the sidebar", "open this CLI session in the desktop app", "start a session from the shell and show it in Desktop", "name the headless lanes". Not for routine messaging, listing, reading, starting, renaming or archiving of sessions the desktop app already lists - its own session tools do that; a rename that fails or differs between accounts still belongs here.
---

# Reviving sessions

The desktop app's session tools — `list_sessions`, `send_message`, `list_events`,
`search_session_transcripts`, `start_session`, `set_session_title`, `archive_session` — cover
every session the app has **indexed**. This skill is for the ones it has not: sessions created
outside it (`claude -p`, the VS Code extension, another account), transcripts stranded on disk,
and transcripts too large or too old for its tools. It also covers the renames those tools get
wrong on indexed sessions: one that silently changes nothing, or lands in only one account.

🔴 **A session the app lists and is running: ask it, don't read it.** Send it a message
(`mcp__ccd_session_mgmt__send_message`, its `local_…` id from `list_sessions`) and wait for the
reply. A transcript is mostly tool-call stubs, and reading it is your guess at its state; its own
answer is its current view. (Shahar, 2026-10-20: *"contact it, don't read its transcripts."*)
Looking up a running session's title or transcript id in the `ccread` listing is fine; reading its
conversation to learn its state is not.

## When to use

- A session is on disk but missing from the desktop sidebar, or a client shows sessions another does not
- A session vanished after its worktree was deleted or it changed directory
- You start a session from a shell and need it to appear, named, in the desktop app
- A rename fails, silently does nothing, or differs between two accounts
- A session has ended, or the app does not have it, and you need what it said or decided

**Not for:** routine work on a session the app already lists — message, read, rename, start or
archive it with the app's tools. A rename that fails or differs between accounts is still this
skill. Not for reading your own conversation, or grepping code.

## First: is the app really missing it?

```
1  list_sessions                                    <- ALWAYS start here
2  find it by cwd + title + isRunning, and use the local_… id EXACTLY AS LISTED
3  ONLY if it is genuinely absent from that listing: adopt it (below)
4  VERIFY in list_sessions, never from a tool's return value
```

⚠️ **THERE ARE TWO ID REGISTRIES AND THEY DO NOT ALWAYS AGREE.**

```
~/.claude/sessions/*.json    the CLI and transcript side (ccread, ListAgents)   one uuid
Desktop session registry     list_sessions · set_session_title · send_message    SOMETIMES a different uuid
```

**Observed on four sessions the same evening, and the version nibble predicted it every time:**

```
local_74f9f379-36df-4b81…   v4   matches the transcript uuid
local_0b3c1d9a-9447-5562…   v5   transcript side is f3dd9167 — DIFFERENT
local_1c640b3e-2656-5798…   v5   transcript side is 2c88dc86 — DIFFERENT
```

A **v5** id is derived rather than random, so the app minted its own for a session it did not
create. *(Pattern held 4/4; the mechanism is inferred, the divergence is measured.)*

🔑 **So `"Session not found"` HAS TWO CAUSES:**

```
1  the app genuinely never indexed it            -> adoption is the fix
2  you passed the TRANSCRIPT-side uuid where the
   tool wants the DESKTOP one                    -> the session is already there; just list it
```

**Treating cause 2 as impossible is what sends you to adopt an already-indexed session, and that
writes a second sidebar row.** Measured 2026-08-12: a rename on the transcript-side uuid returned
*not found*, the reader went straight to adoption, and the session **had been in `list_sessions` all
along**. The human saw two rows for one session.

**A title is not an identifier.** When an id fails, the natural recovery is to look the session up
in `list_sessions` by the title you can see. Measured 2026-08-10: a rename against a `local_…` id
matched by title answered *"Renamed session …"* and the lane's title never changed — the entry had
no transcript at all. Match on cwd + title + `isRunning` together, and verify afterwards.

## Making a session visible in the desktop app

Each client only lists sessions **it** created. The VS Code extension enumerates
`~/.claude/projects/`, so it sees everything; the desktop app reads its own index and so sees only
its own. Upstream gap: anthropics/claude-code #49775, #66229, #65674, #62980.

The desktop app registers the **`claude://`** scheme. This is **not** the `claude-cli://` scheme in
the public docs — that one opens a *terminal*, not the app. The routes are undocumented; both were
read out of `/Applications/Claude.app/Contents/Resources/app.asar` and verified live 2026-08-07.

```bash
open "claude://code/new?q=<urlencoded>&folder=/abs/path"   # prefill a prompt, UNSENT
open "claude://resume?session=<BARE uuid>"                 # adopt an EXISTING session, no restart
```

**Assume this is undiscoverable.** Measured 2026-08-07: an agent asked to surface a session in the
sidebar searched `claude --help` and concluded *"None exists."* There is no CLI flag for it, so an
agent working from `--help` reports the task impossible rather than find these.

### Adoption — only after `list_sessions` has shown the session is absent

```bash
open "claude://resume?session=<BARE uuid>"     # the app adopts it and writes its own index entry
sleep 3                                        # the entry appears titleless
# the adopted entry is local_<the SAME bare uuid>; confirm it in list_sessions before using it
```

**Measured 2026-08-10 on three lanes:** `set_session_title` returned *not found* for every id form;
after `claude://resume` each appeared in `list_sessions` (with no `title` key), and the rename then
succeeded.

⚠️ **Adoption fronts the session in the app** — a visible UI action, not a silent index write. Fine
when you were asked; do not do it in bulk without saying so.

⚠️ **Adoption can leave a duplicate, and the stale row can look MORE alive than the real one.**
Measured 2026-08-12: after `claude://resume` the sidebar showed two entries per lane — the adopted
session (correctly titled) and the original phantom (old title) — and the **phantoms rendered with
the filled/active marker while the real sessions rendered hollow**. Say this to the human before
adopting, and leave the cleanup to them: `archive_session` stops the session's process and by
default cleans up its worktree. **A wrong archive costs a worktree; a duplicate row costs nothing.**

### Starting a session from a shell and showing it in the app

`code/new` takes `q` (or `prompt`), `folder` (repeatable), `file`. **There is no autosubmit
parameter** — the only `autoSubmit` in the bundle is voice dictation. To create a session *and* send
its first message:

```bash
SID=$(uuidgen | tr 'A-Z' 'a-z')
claude --session-id "$SID" -p "first message"   # creates + sends, headless
open "claude://resume?session=$SID"             # the app adopts it and writes its own index entry
sleep 3                                         # the entry appears titleless
# then set_session_title (MCP) on its local_… id from list_sessions   # ← REQUIRED, see below
```

The title step comes **after** the `open`: until the app has adopted the session,
`set_session_title` answers *not found*.

🔴 **THE TITLE STEP IS NOT OPTIONAL, AND OMITTING IT IS WHY EVERY HEADLESS LANE IS CALLED "General
coding session".** A headless session gets **no title record of any kind** — measured 2026-08-13:

```
1b703d78   interactive     aiTitle='Test Zapfloor API endpoints with Postman'
a6eea7a7   interactive     aiTitle='Debug Metabase join query with text field…'
31436a41   claude -p       aiTitle=None      <- nothing generated AT ALL
a0a4b8f3   claude -p       aiTitle=None
```

An interactive session gets an auto-generated `aiTitle`. A `-p` session gets none, so the app falls
back to its placeholder, and **only an explicit `set_session_title` (which writes `customTitle`)
ever names it.** The plausible mechanism — that an identical boilerplate first line is being
*summarised into* something generic — is wrong: there is no summary at all, so rewording briefs
changes nothing.

`claude --session-id` and `claude -r <id> -p` are in `--help` and agents find them unaided — the
deep links are the part worth remembering. Two caveats: `--bare` and `--safe-mode` skip hooks, so a
session started either way never registers itself; and sessions created with `-p` do not appear in
the `--resume` picker, though they resume fine by id.

## Renaming a session the app did not create

`mcp__ccd_session_mgmt__set_session_title` renames **another** session; it refuses the one you are
in, so your own title is the human's job.

### ✅ Verify a rename by its effect, never by its return value

`set_session_title` can answer *"Renamed session …"* and change nothing you can see. Measured
2026-08-12: four renames, four *"Renamed"* returns, four sessions unchanged — the rows had been
matched by title and had no transcript behind them. **The warning about this was already in the
file and its author walked into it anyway**, so the defence is a check, not a warning:

```bash
# BEFORE, required: find the session's transcript id, and keep it
ccread --since <its start date>   # the listing: id (first 8 chars of the transcript uuid), cwd, title
#   match the row you will rename by cwd + title + time. For a v4 desktop id it is simply the
#   same uuid; for a v5 id the app minted, this listing is the only link. No match: stop, and do
#   not adopt a session list_sessions already shows.
find ~/.claude/projects -name '<uuid-from-list_sessions>*.jsonl' | wc -l   # optional extra evidence
#   1 -> the listed id IS the transcript uuid      0 -> cannot tell from the id (normal for v5)

# AFTER, required: the tool also writes customTitle into the transcript, so
ccread --since <its start date> | grep <transcript id>   # must show the new title
# ...and list_sessions must show it too. This reads the listing only, not the conversation.
```

If neither changed, the row was not the session you meant — go back to `list_sessions`.

🔴 **A 0 does NOT mean "this session does not exist", and NEVER archive on it.** Run over a whole
listing the same hour, **12 of 12 desktop-native entries returned 0**, including one reporting
`isRunning: true`.

### It lands in only one account

**`set_session_title` updates only the signed-in account's index entry.** Measured 2026-08-07: after
one rename the same session read `Demo: session created + prompted automatically` under one account
and the stale `Reply with exactly this and nothing else: Second demo sessio…` under the other. A
machine with two accounts drifts further apart with every rename, and neither side looks wrong.

What saves it is that the tool **also writes `customTitle` into the transcript**, and the transcript
is one file both accounts read. So the durable form of a rename is: set the title, then propagate
that `customTitle` into every account's index entry. No session tool writes another account's
index from here: re-run `set_session_title` from a session signed into that account, with the
`local_…` id *that* account lists. Syncing 394 entries that way resolved 7
divergences, one of them a session reading `Elementor MCP integration` under one account and its raw
first message `I need to add the elementor-mcp` under the other.

**Never sync from `aiTitle`.** Lanes that start with the same first step all summarise to the same
string, so an aiTitle sweep renames a whole sprint's lanes identically and destroys the names their
human uses out loud.

### When you must not touch the UI: write the record yourself

`ccread` reads `customTitle` out of the transcript JSONL — there is no separate title store, and the
rename tool's own durable half is exactly this record. So append one line to the session's newest
transcript:

```python
rec = json.dumps({"type": "custom-title", "sessionId": sid, "customTitle": title})
assert json.loads(rec)                        # never append a line you have not parsed
open(transcript, "a").write(rec + "\n")
```

`sid` is the **bare** uuid, no prefix. Copy the shape from a real record rather than inventing it —
it is three fields. **Verify with `ccread`**, never from a tool's return value. This does not update
any desktop index entry, so the sidebar may still show the old name.

## How transcripts are stored

1. **A transcript is filed by cwd**, at `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`. The slug encodes the directory the session ran in.
2. **A session that changes directory gets a new file** under the new slug. One session can have several copies on disk, only the newest of which is current.
3. **Most `type: "user"` entries are not from a human.** They carry `tool_result` blocks. A real human turn is a bare string, or a list containing a `text` block — and even then the harness injects turns (skill re-invocations, compaction notices, interrupt markers) that read like speech.
4. **The session's name lives in `type: "custom-title"` (`customTitle`), not `type: "ai-title"` (`aiTitle`).** Both appear, repeatedly. `aiTitle` summarises the first message; `customTitle` is a human rename and is what the picker shows. Take the last of each and prefer the custom one.

`ccread` handles all four. If you parse transcripts by hand, handle them yourself. One extra trap in
(4): a rename is written to whichever copy was live when it happened, so a session renamed **before**
it moved worktrees carries its real name only in the *older* file. `ccread` inherits a human-set name
across that swap while still reading the newest copy for content.

## Orphaned transcripts

**First, check whether the worktree still exists — the common case is not orphaning at all.**
Sessions are listed by **cwd**, so a session that ran in a worktree only appears in the picker *from
that directory*. From the main checkout it is absent, which looks identical to having been lost.
Measured 2026-07-30: a session reported missing had its worktree intact, and opening that folder
brought it straight back. `ccread <id>` prints the recorded `cwd`; test it with `[ -d ]` first.
**Do not run the recovery below in that case** — copying leaves two transcripts, and if the copy is
resumed the original silently diverges.

Deleting a worktree does not delete the transcript of a session that ran in it — it strands it under
a project directory whose folder no longer exists, so the session vanishes from the list while
sitting intact on disk. `ccread` still finds it and flags it `worktree-filed`. To make it openable
again, copy it into the surviving project's directory and repoint its `cwd`:

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

**Parse per line; never `sed` the file.** A transcript is full of commands that mention its own
worktree path; a find-replace silently falsifies the session's record of what it ran. Copy rather
than move, so a live session writing to the original is undisturbed.

## Reading a session the app cannot show you — `ccread`

For a session that has ended, that the app never indexed, or whose transcript is too large for
`list_events`. A session's reasoning survives only in its prose — what it found, refuted, flagged or
decided not to do is in no diff, PR or ticket — and a transcript is ~95% tool calls, so `cat`, `grep`
and `jq` bury it. `ccread` (in `scripts/`, no install) prints only what was said.

| Need | Command |
|---|---|
| Every session on disk, live and stale | `ccread` |
| Which lane is which (every title goes stale) | `ccread --doing` |
| Only recent | `ccread --since 2026-07-29` |
| Read one session's conversation | `ccread "TOR-55"` |
| The end of it | `ccread <id> --last 20` |
| Only since this morning | `ccread <id> --from 06:00` |
| With tool calls interleaved | `ccread <id> --tools` |
| Find a topic in one session | `ccread <id> --grep codex` |
| Find a topic across all sessions | `ccread --all --grep "credential" --since 2026-07-29` |

Sessions resolve by id prefix **or** title/cwd substring. The listing marks 🟢 active / 🟡 recent /
⚪ stale, plus `worktree-filed` and `N copies`. Run `ccread --help` for the rest.

**A title — even a human-set one — goes stale.** It names the ticket the lane *started* on; hours
later the lane may be three tickets downstream, and the title reads authoritative because a person
wrote it. Measured 2026-08-04: a lane named `Sprint1 TOR-197: legacy data into silver` was building
the chart compiler. Resolve by title to *find* a session; confirm what it did with
`ccread <id> --last 2` before acting on it.

**A handoff is a summary, and a summary of two things describes one of them.** When a session's
handoff covers more than one subject it tends to characterise the one its author looked at hardest
and assume the other matches. Measured 2026-07-30: a handoff named one difference between two
near-identical page slots; reading both sources found **eight**, two of which inverted the
handoff's advice. Use a handoff to find what to look at, then look at it.

## Common mistakes

| Mistake | What happens | Instead |
|---|---|---|
| Adopting on a bare *"not found"* | A second sidebar row for a session that was indexed all along | `list_sessions` first; see the two causes |
| Trusting *"Renamed session …"* | Nothing changed: the row was not the session you meant | Verify with `ccread` and `list_sessions` afterwards |
| Archiving a row the id check returned 0 for | Stops a live session and deletes its worktree | Leave duplicate rows to the human |
| Starting `claude -p` lanes with no title step | Every lane reads "General coding session" | Adopt, then `set_session_title` |
| Reading a stale transcript copy | You report outdated conclusions | Take the newest copy per session id (`ccread` does) |
| `sed`-ing a transcript to repair paths | Rewrites the session's own recorded commands | Parse per line, touch only the top-level `cwd` |
| `--from 07:00` on an overnight session | Matches 07:00 **every** day it ran | `ccread` anchors a bare `HH:MM` to the last day; pass a full ISO stamp to be explicit |
