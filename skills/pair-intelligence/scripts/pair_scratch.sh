#!/usr/bin/env bash
# A disposable copy of a repository, for a runnable review: Codex may run tests
# and write files there, with its network off, and nothing reaches the real repo.
#
#   pair_scratch.sh check <path>...                   exit 64 if any path is in a temp folder
#   pair_scratch.sh create <repo dir> <parent dir>    prints the copy's path for <repo dir>
#   pair_scratch.sh remove <repo dir> <parent dir>
#
# The copy is a detached git worktree at HEAD (it shares objects, so it is fast
# and cheap) with the staged changes applied to its index, the unstaged ones to
# its files, and the untracked, not-ignored files copied, so `git diff` and
# `git diff --cached` inside it show what they show in the real repo.
# Dependency folders (node_modules, .venv, venv) at the repo root and in the
# reviewed folder are linked from the real repo: tests can import them, and they
# sit outside the sandbox's writable root, so Codex can read but not change them.
#
# Codex's writable sandbox also lets it write to /tmp and $TMPDIR (measured), so
# the real repo, this skill and the run's output must not live there: `check`.
set -euo pipefail

temp_roots() {
  local r
  for r in /tmp /private/tmp /var/tmp /private/var/tmp /var/folders /private/var/folders "${TMPDIR:-/tmp}"; do
    [[ -d "$r" ]] && (cd "$r" && pwd -P)
  done
}

cmd="${1:-}"
case "$cmd" in
  check)
    shift
    roots="$(temp_roots)"
    for p in "$@"; do
      [[ -e "$p" ]] || continue
      real="$(cd "$p" 2>/dev/null && pwd -P || python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$p")"
      while IFS= read -r w; do
        [[ -n "$w" ]] || continue
        if [[ "$real" == "$w" || "$real" == "$w"/* ]]; then
          echo "$p is in a temp folder ($w), which a runnable Codex can write; move it, or run without --runnable" >&2
          exit 64
        fi
      done <<< "$roots"
    done
    exit 0 ;;
esac

repo="${2:-}"; parent="${3:-}"
[[ -n "$cmd" && -d "$repo" && -n "$parent" ]] || { echo "usage: pair_scratch.sh check|create|remove ..." >&2; exit 64; }
top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || { echo "a runnable copy needs a git repository: $repo" >&2; exit 64; }
copy="$parent/repo"
# Plain patches whatever the repo's diff config says (prefixes, external diff,
# textconv), so `git apply` can read them and nothing configured runs.
gdiff() { git -C "$top" -c diff.noprefix=false -c diff.mnemonicPrefix=false diff --no-ext-diff --no-textconv --binary "$@"; }

case "$cmd" in
  create)
    mkdir -p "$parent"
    git -C "$top" worktree add --quiet --detach "$copy" HEAD
    gdiff --cached > "$parent/staged.patch"
    gdiff > "$parent/unstaged.patch"
    [[ -s "$parent/staged.patch" ]] && git -C "$copy" apply --index --binary --whitespace=nowarn "$parent/staged.patch"
    [[ -s "$parent/unstaged.patch" ]] && git -C "$copy" apply --binary --whitespace=nowarn "$parent/unstaged.patch"
    (cd "$top" && git ls-files -o --exclude-standard -z) | python3 -c '
import os, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
for rel in sys.stdin.buffer.read().split(b"\0"):
    if not rel:
        continue
    rel = os.fsdecode(rel)
    a, b = os.path.join(src, rel), os.path.join(dst, rel)
    os.makedirs(os.path.dirname(b), exist_ok=True)
    if os.path.islink(a):
        os.symlink(os.readlink(a), b)
    elif os.path.isfile(a):
        shutil.copy2(a, b)
' "$top" "$copy"
    # The same folder inside the copy as $repo is inside the real repo; git keeps
    # no empty folders, so it may need making.
    rel="$(python3 -c 'import os,sys; print(os.path.relpath(os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])))' "$repo" "$top")"
    target="$copy"; [[ "$rel" == "." ]] || target="$copy/$rel"
    mkdir -p "$target"
    # Installed dependencies are ignored, so the copy has none of them: link every
    # ignored node_modules, .venv and venv folder, wherever it sits (a monorepo
    # keeps one per package), outside any other one.
    (cd "$top" && git ls-files --others --ignored --exclude-standard --directory -z) | python3 -c '
import os, sys
top, copy = sys.argv[1], sys.argv[2]
names = {"node_modules", ".venv", "venv"}
found = []
def outermost(rel):
    parts = rel.split("/")
    for i, part in enumerate(parts):
        if part in names:
            return "/".join(parts[:i + 1])
    return None
for rel in sys.stdin.buffer.read().split(b"\0"):
    rel = os.fsdecode(rel).rstrip("/")
    if not rel:
        continue
    hit = outermost(rel)
    if hit:
        found.append(hit)
    elif os.path.isdir(os.path.join(top, rel)):
        # git collapses a wholly ignored folder (.tools/): look a few levels into it.
        base = os.path.join(top, rel)
        for dp, dns, _ in os.walk(base):
            depth = dp[len(base):].count(os.sep)
            keep = []
            for d in dns:
                if d in names:
                    found.append(os.path.relpath(os.path.join(dp, d), top))
                elif depth < 3 and not os.path.islink(os.path.join(dp, d)):
                    keep.append(d)
            dns[:] = keep
for rel in sorted(set(found)):
    src, dst = os.path.join(top, rel), os.path.join(copy, rel)
    if os.path.isdir(src) and not os.path.lexists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.symlink(src, dst)
' "$top" "$copy"
    # Dependency folders that are not ignored (rare) were copied above as files.
    echo "$target"
    ;;
  remove)
    # --force: no git command runs inside the copy, whose .git file Codex could
    # have rewritten to point at a repository with hostile config.
    git -C "$top" worktree remove --force "$copy" 2>/dev/null || true
    rm -rf "$parent"
    git -C "$top" worktree prune 2>/dev/null || true
    ;;
  *) echo "usage: pair_scratch.sh check|create|remove ..." >&2; exit 64 ;;
esac
