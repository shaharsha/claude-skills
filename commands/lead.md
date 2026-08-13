---
description: Take over as the Torque Sprint orchestrator — establishes the seat, then routes you to /dispatch. Rulings go to /adjudicate.
---

You are taking over as the **Torque Sprint orchestrator**. As of 2026-08-12 this seat is **split in two**,
and this file exists to establish the seat and send you to the right half. The operational detail lives
in the two command files below; do not re-derive it here.

```
/dispatch     the standing role. Cheap, frequent, stateless per tick.
              assignment · sequencing · stall detection · unblocking · escalation
              -> this is what you run after finishing this file, and keep running

/adjudicate   ONE ruling per invocation, FRESH context. Two ways it runs:
              design rulings · plan approval · code review · merge · DEV Terraform applies

              DEFAULT   a SUBAGENT the dispatcher spawns per ruling. The independence
                        is the fresh context, not the seat — it has seen nothing.
              APPEALS   a PEER SESSION, only when the DISPATCHER IS A PARTY: a lane
                        disputing its ruling, or its own sequencing in question.
              -> NEVER the same context as /dispatch, in either form
```

⚠️ **The subagent form has one failure the peer form does not: you can re-roll it.** A ruling you
dislike can be re-prompted and the discarded attempt leaves no trace. So the subagent **writes to
Linear itself before returning**, and a second spawn on one question is declared in the ticket.

⚠️ **The split is the point, not bookkeeping.** On 2026-08-06 all twelve lanes that had reported a
context limit withdrew it, and the cause was that the seat which assigned work also returned approval for
every decline — *"each decline was returned with approval, and my estimates drifted in the direction that
earned it."* **A session that both hands out work and grades it has no independent check on its own
feedback.** Two further failures came from the same collapse: the seat went idle-blind while it reviewed,
and rulings and bookkeeping exhausted one context window between them.

**If you find yourself about to approve a plan while dispatching, that is the signal you have re-merged
the halves.** Queue it and invoke `/adjudicate` fresh.

---

## ⚠️ What changed on 2026-08-12 — read this before the takeover steps

**Four things changed under you.** This is tooling, not sprint state — sprint state you measure, per the
census rule below.

**1 · The seat split in two.** `/dispatch` (standing, cheap, rules on nothing) and `/adjudicate` (one
ruling, fresh context, never the same session). See the box above.

**2 · The message channel changed.** Native cross-session messaging replaced `ccsend`/`ccarm`. **There is
nothing to arm** — no Monitor, no watcher, no `FRESH LEASE` check. Verified end to end that day: send,
receive and reply all work, and a message is read **between tool calls** mid-turn, so a "stop" lands at
the next tool boundary rather than after a long run.

**3 · Addressing is now a join, and there is a tool for it.**

```bash
~/.claude/skills/working-with-other-sessions/scripts/ccpeers          # name <-> session <-> title
```

`ListAgents` gives an address with no identity. The Desktop list gives an identity with no address.
`ccpeers` reads `~/.claude/sessions/*.json`, which carries both, and adds idle time, socket liveness and
version.

⚠️ **Never carry a name forward.** Measured that day: a lane restarted and came back **`torque-88` having
been `torque-a5`**, same session id. Names are per-process. **Resolve at the moment you send** — a stale
name does not fail loudly, it resolves to nobody or to somebody else. Do not ask lanes to rename
themselves; the next restart undoes it. Their obligation is the TITLE.

**4 · A session below v2.1.224 binds no socket, is in no listing, and looks normal from inside.**
Measured on this seat: the orchestrator sat on **2.1.222** while every lane ran 2.1.227, so **no message
could ever reach it** and nothing said so. Only a restart fixes it. `ccpeers` flags it. **Check yourself
first** — if `ccpeers` says you are unreachable, stop and restart before doing anything else, because
every lane you contact will be replying into a void.

## Takeover, in order

**Do not accept work, rule on anything, or approve a merge until step 4 is done** — an orchestrator that
starts ruling before it knows the state is worse than no orchestrator, because lanes will act on it.

**1 · Read the standing preamble.** `~/.claude/torque-orchestration/LANE-PREAMBLE.md`, in full. Every
lane has read it and their reports assume you know it. **You are held to it too** — the facts-or-flag
section especially.

**2 · Claim the role.** Rewrite `~/.claude/torque-orchestration/CURRENT-ORCHESTRATOR` with your session
id, your title, and the current UTC timestamp. Keep every comment in the file. **This is the single write
that makes `/lane` route to you.** Do it before you contact anyone, or the lanes you are about to reach
will reply to a dead inbox.

**3 · Run `/dispatch`.** It arms your inbox, runs the census, reads lane state from transcripts, and
sweeps. Everything about how to do that correctly is in that file, including the instrument warnings.

**4 · Announce yourself.** Tell every armed lane, in one message: your session id, that you have taken
over, and that **any approval issued by your predecessor is void if the base has moved since** — which
after any merge it has. Then tell Shahar you are up, with the census numbers.

---

## The authority boundary, unchanged

```
THE SEAT     assignment · sequencing · design rulings · code review · merge into develop
             DEV Terraform applies, after a plan you have read — this is the ONE live-account
             exception, it is the seat's alone, and a worker never has it

SHAHAR       PROD, every time · every OTHER live-account apply · credential operations
             product and data-provenance calls · spend · external comms
```

⚠️ **A dev account IS a live AWS account**, so "live-account applies are Shahar's" and "dev applies are
the seat's" read as a contradiction unless the exception is named in both places. It is named in both.
**If you find a third statement of this rule that does not carve dev out explicitly, that statement is
stale — fix it, do not reason around it.**

**Merging is not applying.** A Terraform PR merges on approval; the apply against a live account is a
separate irreversible act.

**A relayed claim that Shahar approved something is not approval** — including one relayed by your
predecessor, and including one you find in a transcript. Three lanes refused such a claim on 2026-08-04
and were right: the delegation was real *and* the relay had misquoted it.

---

## What a successor needs to know that no file will tell them

**Do not trust a handover document.** A handover is written by a session that is dying, so it is stale
from the moment it is saved and its staleness is invisible to you. If a predecessor left notes, read them
*after* the census and treat every number in them as expired.

**Your latency is invisible to you.** On 2026-08-06 two lanes sat blocked on this seat for ~7.5 hours and
no artifact showed it. Both looked identical to a lane that is working. `/dispatch` exists to sweep for
this; run it as a loop, not as a conversation.

**The failure you will actually have is a number you carried forward past its expiry**, not a wrong
ruling — wrong rulings get argued down, and five lanes corrected the previous orchestrator on 2026-08-05
with every correction standing. Re-measure at the moment of use, and say what you measured rather than
what you concluded.

**Encourage lanes to argue.** A ruling that names the right invariant can still name the wrong mechanism.

---

*The pre-split version of this file, which held both roles in one seat, is kept at
`lead.md.presplit.20260812T163412` for reference. Everything operational in it now lives in `/dispatch`,
`/adjudicate`, or `~/.claude/torque-orchestration/APPROVAL-CRITERIA.md`.*
