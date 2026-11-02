#!/usr/bin/env bash
# A disposable copy of a repository, for a runnable review: Codex may run tests
# and write files there, with its network off, and nothing reaches the real repo.
#
#   pair_scratch.sh create <repo dir> <parent dir>   prints the copy's path for <repo dir>
#   pair_scratch.sh remove <repo dir> <parent dir>
#
# The copy is a detached git worktree at HEAD (it shares objects, so it is fast
# and cheap), with the uncommitted changes applied and the untracked, not-ignored
# files copied, so it holds exactly what a review of the working tree reads.
# Dependency folders (node_modules, .venv, venv) are linked from the real repo:
# tests can import them, and they sit outside the sandbox's writable root, so
# Codex can read but not change them.
set -euo pipefail

cmd="${1:-}"; repo="${2:-}"; parent="${3:-}"
[[ -n "$cmd" && -d "$repo" && -n "$parent" ]] || { echo "usage: pair_scratch.sh create|remove <repo> <parent>" >&2; exit 64; }
top="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null)" || { echo "a runnable copy needs a git repository: $repo" >&2; exit 64; }
copy="$parent/repo"

case "$cmd" in
  create)
    mkdir -p "$parent"
    git -C "$top" worktree add --quiet --detach "$copy" HEAD
    git -C "$top" diff HEAD --binary > "$parent/changes.patch"
    if [[ -s "$parent/changes.patch" ]]; then
      git -C "$copy" apply --binary --whitespace=nowarn "$parent/changes.patch"
    fi
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
    for d in node_modules .venv venv; do
      [[ -e "$top/$d" && ! -e "$copy/$d" ]] && ln -s "$top/$d" "$copy/$d"
    done
    # The same folder inside the copy as $repo is inside the real repo.
    rel="$(python3 -c 'import os,sys; print(os.path.relpath(os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])))' "$repo" "$top")"
    if [[ "$rel" == "." ]]; then echo "$copy"; else echo "$copy/$rel"; fi
    ;;
  remove)
    git -C "$top" worktree remove --force "$copy" 2>/dev/null || true
    git -C "$top" worktree prune 2>/dev/null || true
    rm -rf "$parent"
    ;;
  *) echo "usage: pair_scratch.sh create|remove <repo> <parent>" >&2; exit 64 ;;
esac
