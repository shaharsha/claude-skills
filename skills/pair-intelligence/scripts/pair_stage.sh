#!/usr/bin/env bash
# Stage read-only snapshots of one or more repositories, each at a chosen ref,
# into one folder, with SHAS.md recording exactly what was staged. Point
# pair.sh --cwd at that folder: Gemini reads only under --cwd, and a review that
# spans several repositories, or a ref other than the checked-out one, otherwise
# means hand-building the folder (two sessions did, 2026-11-03/04).
#
#   bash scripts/pair_stage.sh <dest> <repo>[@<ref>][:<path>,<path>...] ...
#
#   <repo>   a local clone
#   <ref>    any git ref or sha; default: the remote's default branch as last
#            fetched (origin/HEAD), else HEAD. Nothing is fetched: run
#            `git -C <repo> fetch` first if it should be current.
#   <path>   limit the snapshot to these paths (default: the whole tree)
#
# Each repository lands in <dest>/<repo folder name>/, from `git archive`: the
# tracked files at that commit, with no .git, no uncommitted changes and nothing
# git-ignored. <dest> must be new or empty.
set -euo pipefail
# One brace group, so bash reads the whole script before running it (a skills
# pull during a long archive would otherwise shift what it reads next).
{
usage() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 64; }
[[ $# -ge 2 ]] || usage
DEST="$1"; shift
if [[ -e "$DEST" && -n "$(ls -A "$DEST" 2>/dev/null)" ]]; then
  echo "$DEST is not empty; stage into a new folder" >&2; exit 64
fi
mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ROWS=()
for spec in "$@"; do
  repo="${spec%%[@:]*}"; rest="${spec#"$repo"}"
  ref=""; paths=""
  if [[ "$rest" == @* ]]; then ref="${rest#@}"; ref="${ref%%:*}"; fi
  [[ "$rest" == *:* ]] && paths="${rest#*:}"
  [[ -d "$repo" ]] || { echo "not a folder: $repo" >&2; exit 66; }
  git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository: $repo" >&2; exit 66; }
  if [[ -z "$ref" ]]; then
    ref="$(git -C "$repo" rev-parse --abbrev-ref origin/HEAD 2>/dev/null)" || ref="HEAD"
  fi
  sha="$(git -C "$repo" rev-parse --verify -q "$ref^{commit}")" || { echo "$repo has no commit $ref" >&2; exit 66; }
  name="$(basename "$(cd "$repo" && pwd)")"
  folder="$name"; n=2
  while [[ -e "$DEST/$folder" ]]; do folder="$name-$n"; n=$((n + 1)); done
  mkdir -p "$DEST/$folder"
  path_args=()
  if [[ -n "$paths" ]]; then IFS=',' read -r -a path_args <<< "$paths"; fi
  git -C "$repo" archive --format=tar "$sha" -- ${path_args[@]+"${path_args[@]}"} | tar -x -C "$DEST/$folder"
  when="$(git -C "$repo" show -s --format=%cI "$sha")"
  ROWS+=("| \`$folder/\` | \`$(cd "$repo" && pwd)\` | \`$ref\` | \`$sha\` | $when | ${paths:-all} |")
done
{
  printf '# What is staged here\n\nStaged %s by pair_stage.sh: each folder is `git archive` of one repository at the commit below (tracked files only, no uncommitted changes). Cite these shas, not a branch name: the branch may have moved since.\n\n' "$STAMP"
  printf '| Folder | Repository | Ref | Commit | Committed | Paths |\n|---|---|---|---|---|---|\n'
  printf '%s\n' "${ROWS[@]}"
} > "$DEST/SHAS.md"
echo "STAGED=$DEST"
cat "$DEST/SHAS.md"
exit
}
