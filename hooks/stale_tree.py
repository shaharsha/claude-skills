#!/usr/bin/env python3
"""Stamp WHICH TREE and HOW STALE onto every Bash call that runs in a git repo.

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
"""
import json
import os
import subprocess
import sys
import time

TIMEOUT = 3.0
# Only stamp commands that could be READING the tree for evidence. A stamp on
# every `echo` is noise, and noise is what gets tuned out -- the failure mode
# this whole class is about.
TRIGGERS = ("git ", "grep", "rg ", "cat ", "sed ", "awk ", "head ", "tail ",
            "ls ", "find ", "pytest", "npm ", "python", "uv ", "wc ", "diff ")
# Bases to measure against, in order. First one that resolves wins.
BASES = ("origin/develop", "origin/main", "origin/master")


# How old the cached ref may get before this hook asks for a refresh, and how long
# it waits before asking again for the same repo.
REF_MAX_AGE = 900.0        # 15 min
REFETCH_COOLDOWN = 600.0   # 10 min between attempts per repo, success or failure
STAMPS = os.path.join(os.path.expanduser("~/.claude"), ".stale_tree_fetch")


def git(args, cwd):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                           text=True, timeout=TIMEOUT)
        return (p.returncode, p.stdout.strip(), p.stderr.strip())
    except (OSError, subprocess.SubprocessError):
        return (127, "", "git unavailable or timed out")


def maybe_refresh(top, base, age):
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
        key = str(abs(hash(top)))
        stamp = os.path.join(STAMPS, key)
        try:
            if time.time() - os.path.getmtime(stamp) < REFETCH_COOLDOWN:
                return
        except OSError:
            pass
        with open(stamp, "w") as fh:      # written BEFORE the spawn, so a fetch that
            fh.write(top)                 # hangs still consumes its cooldown slot
        remote, _, ref = base.partition("/")
        subprocess.Popen(
            ["git", "fetch", "--quiet", remote, ref],
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
        return "age unknown"
    if sec < 90:
        return f"{int(sec)}s old"
    if sec < 5400:
        return f"{int(sec // 60)}m old"
    return f"{int(sec // 3600)}h{int((sec % 3600) // 60):02d}m old"


def emit(context):
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": context}}, sys.stdout)
    sys.stdout.write("\n")


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if payload.get("tool_name") != "Bash":
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

    rc, top, _ = git(["rev-parse", "--show-toplevel"], cwd)
    if rc != 0:
        return 0                                   # not a git repo: nothing to say

    rc, head, _ = git(["rev-parse", "--short", "HEAD"], cwd)
    rc2, branch, _ = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if rc != 0:
        emit(f"⚠️ STALENESS: CANNOT DETERMINE — `git rev-parse HEAD` failed in {top}. "
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
    for base in BASES:
        rcb, _, _ = git(["rev-parse", "--verify", "--quiet", base], cwd)
        if rcb == 0:
            rcc, count, _ = git(["rev-list", "--count", f"HEAD..{base}"], cwd)
            if rcc != 0 or not count.isdigit():
                emit(f"⚠️ STALENESS: CANNOT DETERMINE against {base} in {top} — "
                     "rev-list failed. Not a pass.")
                return 0
            raw_age = ref_age(gitdir, base) if rcg == 0 else None
            # Report the PRE-fetch age, then ask for a refresh for next time. Order
            # matters: computing the line first guarantees this call can never
            # report a freshness it did not have.
            age = human(raw_age)
            maybe_refresh(top, base, raw_age)
            n = int(count)
            # The word BEHIND carries the number; the parenthetical carries the
            # expiry. Both, always -- the count alone is the trap, not the fix.
            lead = "⚠️ STALE TREE" if n > 0 else "TREE"
            note = ""
            if n > 0:
                note = (f"  <- evidence from this tree describes a revision {n} "
                        f"commit(s) older than {base}")
            emit(f"{lead}: {top}  HEAD {head} ({branch})  BEHIND {n} vs {base}  "
                 f"[last fetched {age}]{note}\n"
                 f"cwd at command START; a `cd` inside the command is not followed.")
            return 0

    emit(f"⚠️ STALENESS: CANNOT DETERMINE — no {'/'.join(BASES)} ref in {top}. "
         "The tree may be current or 1000 behind; this check did not run. "
         "exit 0 here is NOT a clean result.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        # Never break a Bash call over provenance. A crash here is silent BY
        # DESIGN and it is the one silent path in the file -- justified because
        # the alternative is a hook that can wedge the session.
        sys.exit(0)
