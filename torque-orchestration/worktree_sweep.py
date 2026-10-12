#!/usr/bin/env python3
"""Sweep finished Torque worktrees (Shahar, 2026-10-12: cleanup is part of the
lane process, not a promise).

Dry run by default; --apply removes. Removal is ONLY `git worktree remove`
(never --force, never a branch delete). A worktree is removed only when ALL hold:
  1. not the main checkout, not locked, not listed in PROTECT_FILE;
  2. no running process has its cwd inside it;
  3. `git status --porcelain` is empty (no edits, no untracked files);
  4. HEAD is on a remote: an ancestor of origin/develop or contained in a remote branch;
  5. its branch's PR is MERGED or CLOSED, or (no PR / detached) HEAD is in origin/develop;
  6. no activity for IDLE_HOURS (newest mtime of its gitdir HEAD/index/logs).
Worktrees with no PR and no activity for FLAG_DAYS are printed for Shahar, never removed.

Usage: worktree_sweep.py [--repo PATH] [--apply] [--idle-hours 3] [--flag-days 2]
       worktree_sweep.py --one PATH --apply   (merge seat: remove one PR's worktree after its merge)
Log: ~/.claude/torque-orchestration/worktree-sweep.log
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
PROTECT_FILE = HOME / ".claude/torque-orchestration/worktree-protect.txt"
LOG = HOME / ".claude/torque-orchestration/worktree-sweep.log"


def git(repo, *args, check=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r


def worktrees(repo):
    out = git(repo, "worktree", "list", "--porcelain", check=True).stdout
    wts, cur = [], {}
    for line in out.splitlines() + [""]:
        if not line:
            if cur:
                wts.append(cur)
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v or True
    return wts


def busy_cwds():
    r = subprocess.run(["lsof", "-d", "cwd", "-Fn"], capture_output=True, text=True)
    return [l[1:] for l in r.stdout.splitlines() if l.startswith("n/")]


def last_activity(path):
    gitfile = Path(path) / ".git"
    try:
        gitdir = Path(gitfile.read_text().split("gitdir:", 1)[1].strip())
    except Exception:
        return time.time()  # unknown -> treat as active (never removed)
    cands = [gitdir / "HEAD", gitdir / "index", gitdir / "logs" / "HEAD"]
    return max((c.stat().st_mtime for c in cands if c.exists()), default=time.time())


def pr_states(repo):
    r = subprocess.run(
        ["gh", "pr", "list", "--state", "all", "--limit", "3000",
         "--json", "headRefName,headRefOid,state,number,updatedAt"],
        cwd=repo, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"refused: gh pr list failed ({r.stderr.strip()}); PR state UNKNOWN, nothing removed")
    best = {}
    for p in json.loads(r.stdout):
        b = p["headRefName"]
        # an OPEN PR on the branch wins; otherwise the newest
        if b not in best or p["state"] == "OPEN" or (
                best[b]["state"] != "OPEN" and p["updatedAt"] > best[b]["updatedAt"]):
            best[b] = p
    return best


def classify(repo, wt, prs, busy, protect, idle_h, flag_d, now):
    path = wt["worktree"]
    if wt.get("bare") or Path(path).resolve() == Path(repo).resolve():
        return "skip", "main checkout"
    if wt.get("locked"):
        return "skip", "locked"
    if any(path == p or path.startswith(p.rstrip("/") + "/") for p in protect):
        return "skip", "protected"
    if any(c == path or c.startswith(path + "/") for c in busy):
        return "skip", "a process has its cwd here"
    if not Path(path).exists():
        return "skip", "missing dir (run `git worktree prune` by hand)"
    st = git(path, "status", "--porcelain")
    if st.returncode:
        return "skip", "git status failed"
    if st.stdout.strip():
        return "skip", "dirty tree"
    head = wt.get("HEAD", "")
    branch = str(wt.get("branch", "")).removeprefix("refs/heads/")
    pr = prs.get(branch) if branch else None
    in_develop = git(repo, "merge-base", "--is-ancestor", head, "origin/develop").returncode == 0
    # a squash-merged PR's head never reaches develop and GitHub deletes its branch;
    # HEAD == the PR's last pushed head is the "nothing unpushed" proof there
    pushed_as_pr = bool(pr) and pr.get("headRefOid") == head
    on_remote = in_develop or pushed_as_pr or bool(git(repo, "branch", "-r", "--contains", head).stdout.strip())
    if not on_remote:
        return "skip", "HEAD not on any remote (unpushed work)"
    idle_h_now = (now - last_activity(path)) / 3600
    if pr and pr["state"] == "OPEN":
        return "skip", f"PR #{pr['number']} open"
    finished = (pr and pr["state"] in ("MERGED", "CLOSED")) or (not pr and in_develop)
    if not finished:
        if idle_h_now >= flag_d * 24:
            return "flag", f"no PR, idle {idle_h_now/24:.1f} d"
        return "skip", "no PR, not in develop"
    if idle_h_now < idle_h:
        return "skip", f"finished but active {idle_h_now:.1f} h ago"
    why = f"PR #{pr['number']} {pr['state']}" if pr else "HEAD in origin/develop"
    return "remove", f"{why}, idle {idle_h_now:.1f} h"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(HOME / "Projects/torque"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--idle-hours", type=float, default=3)
    ap.add_argument("--flag-days", type=float, default=2)
    ap.add_argument("--one", help="only this worktree path (merge seat, post-merge)")
    a = ap.parse_args()
    repo = a.repo
    if git(repo, "fetch", "-q", "origin", "develop").returncode:
        sys.exit("refused: fetch of origin/develop failed; nothing removed")
    protect = [l.strip() for l in PROTECT_FILE.read_text().splitlines()
               if l.strip() and not l.startswith("#")] if PROTECT_FILE.exists() else []
    prs, busy, now = pr_states(repo), busy_cwds(), time.time()
    wts = worktrees(repo)
    if a.one:
        target = str(Path(a.one).resolve())
        wts = [w for w in wts if str(Path(w["worktree"]).resolve()) == target]
        if not wts:
            sys.exit(f"refused: {a.one} is not a worktree of {repo}")
        a.idle_hours = 0  # the seat just confirmed the merge; still requires clean + pushed
    counts, flagged, removed = {}, [], 0
    with LOG.open("a") as log:
        log.write(f"\n== {time.strftime('%Y-%m-%dT%H:%M:%S')} repo={repo} apply={a.apply} one={a.one}\n")
        for wt in wts:
            verdict, why = classify(repo, wt, prs, busy, protect, a.idle_hours, a.flag_days, now)
            counts[verdict] = counts.get(verdict, 0) + 1
            line = f"{verdict:6} {wt['worktree']}  ({why})"
            if verdict == "flag":
                flagged.append(line)
            if verdict == "remove" and a.apply:
                r = git(repo, "worktree", "remove", wt["worktree"])
                ok = r.returncode == 0
                removed += ok
                line += "  -> removed" if ok else f"  -> FAILED: {r.stderr.strip()}"
            log.write(line + "\n")
            if verdict != "skip" or a.one:
                print(line)
    free = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.splitlines()[-1]
    print(f"\nsummary: {counts}  removed={removed}  (dry run)" if not a.apply
          else f"\nsummary: {counts}  removed={removed}")
    print(f"disk: {free}")
    if flagged:
        print(f"\nFLAG FOR SHAHAR ({len(flagged)} worktrees, no PR, idle >= {a.flag_days} d):")
        print("\n".join(flagged))
        with LOG.open("a") as log:
            log.write(f"FLAG FOR SHAHAR ({len(flagged)} worktrees, no PR, idle >= {a.flag_days} d):\n")
            log.writelines(f"FLAG {l}\n" for l in flagged)


if __name__ == "__main__":
    main()
