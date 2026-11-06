#!/usr/bin/env python3
"""Stamp WHICH TREE and HOW STALE onto Bash calls in a git repo, when the answer changes.

WHY THIS EXISTS
---------------
On 2026-08-13 the Sprint dispatcher ran source citations out of the Torque main
checkout -- greps, file-existence checks -- and filed them into tickets as
statements about `develop`. The checkout was 223 COMMITS BEHIND origin/develop.
Every citation was a TRUE STATEMENT ABOUT THE WRONG REVISION. They happened to
reproduce after a fast-forward, so nothing shipped wrong. That is luck.

The existing rule -- "print the tree and the branch in the same command that runs
the suite" -- was followed, and did not help:

    TREE ~/Projects/torque  BRANCH develop     <- says WHERE, not HOW STALE
                                                  and `develop` READS as current

⚠️ A rule that fires for one failure (wrong tree) and is blind to its neighbour
(right tree, wrong time), while looking like it covers both, is worse than no
rule: it produces the FEELING of having checked. This hook exists because that
fleet has measured, repeatedly, that a second CONVENTION buys nothing -- the
rules were all written down and all broken by their own authors, several within
an hour of writing them. So this is code the harness runs, not text to remember.

The repo has ~226 worktrees, ~170 of them over 100 commits behind. In that repo
"I measured it in the checkout" IS NOT A PROVENANCE CLAIM: a bare grep answers
about whichever of 226 trees you are standing in, and says nothing about which.

WHY IT REPORTS THE REF'S AGE, ALWAYS
------------------------------------
The count is measured against the CACHED remote ref. Measured on this machine,
that ref was 9h17m old -- so `behind 0` off a stale ref reproduces the original
failure with a number attached, which is MORE convincing and equally wrong.

    behind-count vs cached ref     13.6 ms      <- affordable per call, no network
    git fetch                      network      <- NOT done here, deliberately

So freshness is a separate job (a periodic fetch). This hook promises only:
"here is what I know, and here is how old it is." That is the one thing it can
always say honestly.

FAILING LOUD
------------
Half the failures this addresses are already silent, so a guard that goes quiet
when it breaks adds a layer rather than a floor. Every branch below either emits
a line or is a deliberate, documented no-op:

    not a git repo          -> silent (correct: nothing to say)
    no remote ref           -> "CANNOT DETERMINE" + why       NEVER silent
    detached HEAD           -> says so
    git missing / times out -> "CANNOT DETERMINE" + why       NEVER silent

⚠️ And it must never block: it exits 0 on every path, including its own crash.
A staleness hook that breaks a Bash call is worse than the staleness.

WHY IT STAMPS ONLY WHEN THE ANSWER CHANGES (2026-11-06)
-------------------------------------------------------
Text a hook injects is re-sent with every later request until a compaction. Measured
over 14 days on this machine: 155,763 stamps, on 83% of all Bash calls, each re-read by
95-170 later requests -- $512 at API list prices, 94% of what all hooks cost. Nearly
every stamp repeated the one before it.

So the hook still MEASURES on every evidence command, but only SAYS something when the
answer differs from the last stamp in the same conversation: another tree, HEAD, branch
or base, a different BEHIND count, a fetch age in another bucket, or a check that now
fails or recovers. The last stamp in context is always the current answer, give or take
the fetch age inside its bucket. The same 14 days under this rule: $29-45.

    state       one file per conversation, keyed on session_id + agent_id. A subagent
                gets its own, so its first call stamps even if the parent's tree did
                not change.
    reset       `stale_tree.py --reset` on every SessionStart (startup, resume, clear,
                compact, fork): after a compaction the old stamp is gone from context,
                so the next call must stamp again. SessionStart carries no agent_id,
                so the whole session's state goes, subagents included.
    fail-open   no session_id, state that cannot be read, written or locked, a run near
                the hook's timeout, or two different answers in parallel calls ->
                stamp, as before. Suppression is the optimisation; a stamp is the safe
                default. Even with nothing changed, a conversation is re-stamped every
                2 hours, which bounds what a missed reset can cost.

WHICH BASE (2026-11-06)
-----------------------
BASES used to be a fixed list with origin/develop first. In torque, develop stopped
moving on 2026-10-15 and fell 3,328 commits behind main, and 90% of stamps were measured
against it: the main checkout read "BEHIND 0" while it was 40 commits behind
origin/main. The original failure with a number attached, which is the shape this file
keeps meeting.

Now, first that resolves: `git config staletree.base`, then origin/HEAD (the remote's
default branch, refreshed by the background fetch), then main, master, develop.
"""
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

TIMEOUT = 3.0
# Only stamp commands that could be READING the tree for evidence. A stamp on
# every `echo` is noise, and noise is what gets tuned out -- the failure mode
# this whole class is about.
TRIGGERS = ("git ", "grep", "rg ", "cat ", "sed ", "awk ", "head ", "tail ",
            "ls ", "find ", "pytest", "npm ", "python", "uv ", "wc ", "diff ")
# Fallback bases, in order, after `git config staletree.base` and origin/HEAD.
# First one that resolves wins. develop last: see WHICH BASE above.
BASES = ("origin/main", "origin/master", "origin/develop")


# How old the cached ref may get before this hook asks for a refresh, and how long
# it waits before asking again for the same repo.
REF_MAX_AGE = 900.0        # 15 min
REFETCH_COOLDOWN = 600.0   # 10 min between attempts per repo, success or failure
STAMPS = os.path.join(os.path.expanduser("~/.claude"), ".stale_tree_fetch")
STATE_DIR = os.path.join(os.path.expanduser("~/.claude"), ".stale_tree_state")
STATE_MAX_AGE = 7 * 86400  # --reset prunes other sessions' state older than this
# The settings give this hook a 10 s timeout, and Claude Code discards the output of a
# hook it cancels. So: at most BUDGET seconds of git, then CANNOT DETERMINE is stamped
# rather than nothing; and state is saved only before SAVE_DEADLINE, because a run
# killed after saving but before Claude Code read its stamp would suppress a stamp
# nobody saw. A late run forgets the state instead, and the next call stamps again.
BUDGET = 7.5
SAVE_DEADLINE = 8.0
# Parallel Bash calls land in context in MESSAGE order but run their hooks in TIME
# order, so when two calls with different answers overlap, the state cannot know which
# stamp is last in context. Two different answers this close together -> forget, and
# let the next call stamp.
OVERLAP_WINDOW = 5.0
# Upper bound on silence: even with nothing changed, stamp again after this long. It
# bounds what a missed --reset (hook not registered, cancelled, failed) can cost.
MAX_SILENCE = 7200.0
# Fetch-age buckets, in seconds. A stamp is re-issued when the age moves into another
# bucket; the background fetch keeps a working repo inside the first one.
AGE_BUCKETS = (1800.0, 7200.0, 43200.0)   # 30 min, 2 h, 12 h


class OutOfTime(Exception):
    """The run's git budget is spent; main() stamps CANNOT DETERMINE instead."""


_deadline = float("inf")          # set by main(): monotonic end of the git budget


def git(args, cwd):
    left = _deadline - time.monotonic()
    if left <= 0.05:
        raise OutOfTime()
    limit = min(TIMEOUT, left)
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                           text=True, timeout=limit)
        return (p.returncode, p.stdout.strip(), p.stderr.strip())
    except subprocess.TimeoutExpired:
        if limit < TIMEOUT:
            raise OutOfTime()
        return (127, "", "git timed out")
    except (OSError, subprocess.SubprocessError):
        return (127, "", "git unavailable or timed out")


def _digest(s):
    # 🔴 NOT hash(): Python salts str hashing per process (see maybe_refresh).
    return hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()[:16]


def fetch_marker(repo, base):
    """File the background fetch touches only after it fetched `base` successfully."""
    return os.path.join(STAMPS, _digest(f"{repo}\0{base}") + ".ok")


def candidate_bases(cwd):
    """Bases to try, best first: the configured one, the remote's default, then BASES."""
    out = []
    rc, configured, _ = git(["config", "--get", "staletree.base"], cwd)
    if rc == 0 and configured:
        out.append(configured)
    rc, default, _ = git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd)
    if rc == 0 and default:
        out.append(default)
    return out + [b for b in BASES if b not in out]


def maybe_refresh(top, repo, base, age):
    """
    Fire-and-forget `git fetch` when the cached ref has gone stale.

    THIS IS THE OTHER HALF OF THE PAIR. The count is measured against a CACHED ref,
    so the hook can only ever be as current as the last fetch. Left alone, that ref
    decays without limit: measured on this machine, ~/Projects/Playground's ref was
    ELEVEN MONTHS old and every `behind 0` from it was meaningless. Nobody would
    have noticed, because nothing was wrong with the answer's SHAPE.

    ⚠️ THE HOOK STILL REPORTS THE PRE-FETCH AGE, ALWAYS. This never improves the
    number it is currently printing -- it improves the NEXT call's. Reporting a
    freshness this call did not have would be the exact substitution the hook
    exists to prevent, committed by the hook itself.

    THREE THINGS KEEP IT FROM BECOMING A PROBLEM OF ITS OWN:
      · detached and never waited on. A hook that blocks a Bash call on the
        network is worse than any staleness.
      · rate-limited per repo by a stamp file, written BEFORE the spawn and on
        every attempt including failures -- so an unreachable remote costs one
        attempt per cooldown, not one per Bash call.
      · silent by design HERE, uniquely in this file: the fetch is an optimisation,
        and its failure is already visible as the age that keeps growing in the
        line above. That is the loud channel; a second one would just be noise.
    """
    if age is not None and age < REF_MAX_AGE:
        return
    try:
        os.makedirs(STAMPS, exist_ok=True)
        # 🔴 NOT hash(). Python SALTS str hashing per process (PYTHONHASHSEED), so
        # every invocation computed a DIFFERENT stamp filename, the cooldown never
        # matched once, and every triggering Bash call spawned an unthrottled fetch.
        # Measured 2026-08-16: 143 stamp files, one per invocation, and two runs of
        # hash("/x") in the same second returning different integers.
        #
        # ⚠️ The rate limit was the ONE thing keeping this from hammering the network
        # on every command, and it was decorative from the first commit. It looked
        # like a cooldown, it created files that looked like stamps, and it throttled
        # nothing -- a guard whose failure is invisible because its output is
        # indistinguishable from its success.
        #
        # Keyed on the repo's COMMON gitdir plus the base, not the worktree: every
        # worktree of a repo shares its remote refs, so one fetch serves all ~226 of
        # them, and a worktree measuring another base keeps its own slot.
        name = base[len("refs/remotes/"):] if base.startswith("refs/remotes/") else base
        remote, _, ref = name.partition("/")
        rc, remotes, _ = git(["remote"], top)
        if rc != 0 or not ref or remote not in remotes.split():
            return                        # a local base (or unknown remote): no fetch
        cooldown = os.path.join(STAMPS, _digest(f"{repo}\0{base}"))
        try:
            if time.time() - os.path.getmtime(cooldown) < REFETCH_COOLDOWN:
                return
        except OSError:
            pass
        with open(cooldown, "w") as fh:   # written BEFORE the spawn, so a fetch that
            fh.write(repo)                # hangs still consumes its cooldown slot
        # Two more jobs ride on the same detached fetch:
        #   · the marker is touched only when THIS base was fetched successfully, so
        #     ref_age() can tell "base checked" from "some other ref fetched";
        #   · set-head refreshes origin/HEAD, so the next retired default branch is
        #     noticed instead of measured against for three weeks.
        subprocess.Popen(
            ["sh", "-c",
             'git fetch --quiet "$1" "$2" && : > "$3"; '
             'git remote set-head "$1" --auto >/dev/null 2>&1',
             "sh", remote, ref, fetch_marker(repo, base)],
            cwd=top, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        return


def ref_age(gitdir, base):
    """
    Seconds since this repo last FETCHED. None if it cannot be determined.

    🔴 FETCH_HEAD, NOT THE REF FILE. Git only rewrites `refs/remotes/<base>` when
    the branch MOVES, so the ref's mtime answers "when did the remote branch last
    change" -- a different question from "when did we last check", and the wrong
    one. FETCH_HEAD is rewritten by every fetch, including a no-op.

    Measured 2026-08-13, and the numbers are the whole argument:

        ~/Projects/Playground   fetch succeeds, exit 0
                                FETCH_HEAD           10:23:40 -> 10:23:44   moved
                                refs/…/origin/develop 2025-09-16 19:41:04   UNCHANGED

    That repo has been dormant since September, so the first version of this
    function reported `ref 7934h old` -- ELEVEN MONTHS -- immediately after a
    successful fetch, and would have done so forever while re-fetching every
    cooldown.

    ⚠️ AND IT WAS INVISIBLE ON EVERY REPO I BUILT AGAINST. On an active repo the
    two timestamps coincide (both 10:20:56 on claude-skills), because a branch
    that moves often makes "last moved" and "last checked" nearly the same number.
    **It works on the population I tested and fails on the population it exists
    for** -- the second bug in this file with exactly that shape, after
    --absolute-git-dir reported "age unknown" for worktrees.
    """
    # ⚠️ AND FETCH_HEAD IS NOT ABOUT `base` EITHER (2026-11-06). Any fetch rewrites it,
    # including `git fetch origin some-feature`, which leaves origin/main untouched. So
    # once this hook's own fetch of `base` has succeeded, its marker is the answer:
    # the newer of the marker and the loose ref (a ref that MOVED was fetched then).
    # FETCH_HEAD stays the fallback until that first successful fetch.
    now = time.time()
    try:
        marked = now - os.path.getmtime(fetch_marker(gitdir, base))
    except OSError:
        marked = None
    if marked is not None:
        try:
            return min(marked, now - os.path.getmtime(os.path.join(gitdir, "refs", "remotes", base)))
        except OSError:
            return marked
    for p in (os.path.join(gitdir, "FETCH_HEAD"),):
        try:
            return time.time() - os.path.getmtime(p)
        except OSError:
            pass
    # Never fetched in this clone: fall back to the ref, and accept that the
    # number then means "last moved". Better than None, and a fresh clone's ref
    # was written at clone time, which IS when it was last checked.
    loose = os.path.join(gitdir, "refs", "remotes", base)
    for p in (loose, os.path.join(gitdir, "packed-refs")):
        try:
            return time.time() - os.path.getmtime(p)
        except OSError:
            continue
    return None


def human(sec):
    if sec is None:
        return None
    if sec < 90:
        return f"{int(sec)}s"
    if sec < 5400:
        return f"{int(sec // 60)}m"
    return f"{int(sec // 3600)}h{int((sec % 3600) // 60):02d}m"


def age_bucket(sec):
    """0 for a fresh ref, higher for older; unknown is the worst bucket."""
    if sec is None:
        return len(AGE_BUCKETS) + 1
    return sum(1 for limit in AGE_BUCKETS if sec >= limit)


def tilde(p):
    home = os.path.expanduser("~")
    return "~" + p[len(home):] if p == home or p.startswith(home + os.sep) else p


def emit(context):
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": context}}, sys.stdout)
    sys.stdout.write("\n")


def state_file(payload):
    """This conversation's state file, or None when the payload names no session."""
    sid = payload.get("session_id")
    if not isinstance(sid, str) or not sid:
        return None
    agent = payload.get("agent_id") or "main"
    return os.path.join(STATE_DIR, _digest(sid), _digest(str(agent)) + ".json")


def read_record(path):
    try:
        with open(path) as fh:
            rec = json.load(fh)
        return rec if isinstance(rec, dict) and isinstance(rec.get("at"), (int, float)) else None
    except (OSError, ValueError):
        return None


def save_record(path, key, now):
    try:
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w") as fh:
            json.dump({"key": key, "at": now}, fh)
        os.replace(tmp, path)             # atomic: a reader sees old or new
        return True
    except OSError:
        return False


def forget(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def lock(path):
    """A per-conversation lock, held for the read-decide-save step. None if not got."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
    except OSError:
        return None
    give_up = time.monotonic() + 1.0
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if time.monotonic() > give_up:
                os.close(fd)
                return None
            time.sleep(0.02)


def stamp(payload, key, context):
    """
    Emit `context` unless the last stamp in this conversation had the same key.

    ⚠️ The state must always describe the LAST stamp delivered, or be absent. So the
    new key is saved BEFORE the stamp is printed, and whenever that cannot be
    guaranteed -- no lock, a save that failed or would land too close to the hook's
    timeout, two different answers overlapping (see OVERLAP_WINDOW) -- the state is
    forgotten instead. Silence needs all of: the lock, a record that reads back
    intact with the same key, younger than MAX_SILENCE, in a directory this run
    could also have written (so a reset that failed to delete cannot leave a key
    that suppresses). Everything else stamps.
    """
    path = state_file(payload)
    if path is None:
        emit(context)
        return
    fd = lock(path)
    try:
        rec = read_record(path) if fd is not None else None
        now = time.time()
        if (rec is not None and rec.get("key") == key and now - rec["at"] < MAX_SILENCE
                and os.access(os.path.dirname(path), os.W_OK)):
            return
        overlap = rec is not None and rec.get("key") != key and now - rec["at"] < OVERLAP_WINDOW
        if fd is None or overlap or time.monotonic() >= _save_by or not save_record(path, key, now):
            forget(path)
    finally:
        if fd is not None:
            os.close(fd)                  # closing the descriptor releases the lock
    emit(context)


def reset():
    """
    SessionStart (`--reset`): forget this session's stamps, prune old state.

    After a compaction, /clear or a resume, the stamps this session's state
    remembers may no longer be in context, so the next call must stamp again.
    SessionStart carries no agent_id, and also fires when a subagent compacts,
    so the whole session goes: over-stamping once is cheap, a missing stamp is
    the failure this file exists for.
    """
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = None
    sid = payload.get("session_id") if isinstance(payload, dict) else None
    if isinstance(sid, str) and sid:
        shutil.rmtree(os.path.join(STATE_DIR, _digest(sid)), ignore_errors=True)
    try:
        now = time.time()
        for name in os.listdir(STATE_DIR):
            d = os.path.join(STATE_DIR, name)
            if now - os.path.getmtime(d) > STATE_MAX_AGE:
                shutil.rmtree(d, ignore_errors=True)
    except OSError:
        pass
    return 0


_save_by = float("inf")           # set by main(): monotonic SAVE_DEADLINE


def main():
    global _deadline, _save_by
    started = time.monotonic()
    _deadline, _save_by = started + BUDGET, started + SAVE_DEADLINE
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return 0
    command = ti.get("command") or ""
    if not any(t in command for t in TRIGGERS):
        return 0

    # ⚠️ The command may `cd` somewhere else entirely, and this hook CANNOT know
    # where -- the string is not the shell. So the stamp names the cwd the
    # command STARTS in, and says so, rather than implying it followed the cd.
    # Claiming to have measured the tree a command ended up in would be the very
    # thing this hook exists to prevent, one level up.
    cwd = payload.get("cwd") or os.getcwd()
    if not os.path.isdir(cwd):
        return 0

    try:
        rc, top, _ = git(["rev-parse", "--show-toplevel"], cwd)
    except OutOfTime:
        rc = 127                                   # same as git timing out here
    if rc != 0:
        return 0                                   # not a git repo: nothing to say
    try:
        return measure(payload, cwd, top)
    except OutOfTime:
        # Out of budget means Claude Code would have cancelled the hook and dropped
        # whatever it printed. Saying so is the floor; silence is not allowed here.
        stamp(payload, ["cannot", top, "time"],
              f"⚠️ STALENESS: CANNOT DETERMINE: the check of {top} ran out of time "
              "(git slow under load). Not a pass; treat evidence from this tree as unattributed.")
        return 0


def measure(payload, cwd, top):
    rc, head, _ = git(["rev-parse", "HEAD"], cwd)
    rc2, branch, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if rc != 0:
        stamp(payload, ["cannot", top, "head"],
              f"⚠️ STALENESS: CANNOT DETERMINE — `git rev-parse HEAD` failed in {top}. "
              "Not a pass; treat any evidence from this tree as unattributed.")
        return 0
    if branch == "HEAD":
        branch = "DETACHED"

    # ⚠️ --git-common-dir, NOT --absolute-git-dir. In a WORKTREE the latter returns
    # that worktree's private gitdir (.git/worktrees/<name>), which holds no
    # refs/remotes -- so the ref age came back "unknown" on exactly the population
    # this hook exists for: ~226 worktrees, ~170 of them 100+ commits behind.
    # Measured on a controlled 151-behind probe, which is the only reason it was
    # caught: the main checkout resolved fine and would have shipped the bug.
    rcg, gitdir, _ = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)
    if rcg != 0:
        rcg, gitdir, _ = git(["rev-parse", "--git-common-dir"], cwd)
        if rcg == 0 and not os.path.isabs(gitdir):
            gitdir = os.path.join(cwd, gitdir)
    bases = candidate_bases(cwd)
    for base in bases:
        rcb, _, _ = git(["rev-parse", "--verify", "--quiet", base], cwd)
        if rcb == 0:
            rcc, count, _ = git(["rev-list", "--count", f"HEAD..{base}"], cwd)
            if rcc != 0 or not count.isdigit():
                stamp(payload, ["cannot", top, "rev-list", base],
                      f"⚠️ STALENESS: CANNOT DETERMINE against {base} in {top}: "
                      "rev-list failed. Not a pass.")
                return 0
            raw_age = ref_age(gitdir, base) if rcg == 0 else None
            # Report the PRE-fetch age, then ask for a refresh for next time. Order
            # matters: computing the line first guarantees this call can never
            # report a freshness it did not have.
            age = human(raw_age)
            maybe_refresh(top, gitdir if rcg == 0 else top, base, raw_age)
            n = int(count)
            # The word BEHIND carries the number; the fetch age carries the expiry.
            # Both, always -- the count alone is the trap, not the fix. One line,
            # because the stamp is now re-read only when it changes.
            fetched = f"fetched {age} ago" if age else "fetch age unknown"
            line = (f"{tilde(top)} {head[:10]} ({branch}) BEHIND {n} vs {base}, {fetched}; "
                    "start cwd, cd not followed")
            if n > 0:
                context = (f"⚠️ STALE TREE: {line}. Evidence from this tree describes a "
                           f"revision {n} commit(s) older than {base}.")
            else:
                context = f"TREE: {line}"
            stamp(payload, [top, head, branch, base, n, age_bucket(raw_age)], context)
            return 0

    stamp(payload, ["cannot", top, "no-base"],
          f"⚠️ STALENESS: CANNOT DETERMINE — no {'/'.join(bases)} ref in {top}. "
          "The tree may be current or 1000 behind; this check did not run. "
          "exit 0 here is NOT a clean result.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(reset() if sys.argv[1:] == ["--reset"] else main())
    except BaseException:
        # Never break a Bash call over provenance. A crash here is silent BY
        # DESIGN and it is the one silent path in the file -- justified because
        # the alternative is a hook that can wedge the session.
        sys.exit(0)
