#!/usr/bin/env bash
# Stage read-only snapshots of one or more repositories, each at a chosen ref,
# and any loose files, into one folder, with SHAS.md recording exactly what was
# staged. Point pair.sh --cwd at that folder: Gemini reads only under --cwd, and
# a review that spans several repositories, or a ref other than the checked-out
# one, otherwise means hand-building the folder (two sessions did, 2026-11-03/04).
#
#   bash scripts/pair_stage.sh [--exclude GLOB]... <dest> <spec>...
#
#   <spec>   <repo>[@<ref>][:<path>,<path>...]   a snapshot of a local clone
#            file:<path>                          a loose file or folder, copied
#   <ref>    any git ref or sha; default: the remote's default branch as last
#            fetched (origin/HEAD), else HEAD. Nothing is fetched: run
#            `git -C <repo> fetch` first if it should be current. A remote ref
#            that is behind the remote gets a warning (one `git ls-remote`).
#            The same repository can be listed twice, at two refs.
#   <path>   limit the snapshot to these paths (default: the whole tree)
#   --exclude GLOB   leave out matching files (repeatable): '*.mp4', '*.pdf'
#
# Each repository lands in <dest>/<repo folder name>/, from `git archive`: the
# tracked files at that commit, with no .git, no uncommitted changes and nothing
# git-ignored. Loose files land in <dest>/files/ under their full path, and
# SHAS.md maps each copy to its original, so a reader knows which path is real.
# <dest> must be new or empty.
set -euo pipefail
# One brace group, so bash reads the whole script before running it (a skills
# pull during a long archive would otherwise shift what it reads next).
{
usage() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 64; }
EXCLUDES=()
while [[ "${1:-}" == --exclude ]]; do
  [[ -n "${2:-}" ]] || usage
  EXCLUDES+=("--exclude=$2"); shift 2
done
[[ $# -ge 2 ]] || usage
DEST="$1"; shift
if [[ -e "$DEST" && -n "$(ls -A "$DEST" 2>/dev/null)" ]]; then
  echo "$DEST is not empty; stage into a new folder" >&2; exit 64
fi
mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ROWS=(); FILES=(); WARNED=0
for spec in "$@"; do
  if [[ "$spec" == file:* ]]; then
    src="${spec#file:}"
    [[ -e "$src" ]] || { echo "no such file or folder: $src" >&2; exit 66; }
    src="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$src")"
    target="$DEST/files$src"
    mkdir -p "$(dirname "$target")"
    if [[ -d "$src" ]]; then
      (cd "$src" && tar -c ${EXCLUDES[@]+"${EXCLUDES[@]}"} -f - .) | (mkdir -p "$target" && tar -x -C "$target")
      FILES+=("| \`files$src/\` | \`$src/\` | folder |")
    else
      cp -p "$src" "$target"
      FILES+=("| \`files$src\` | \`$src\` | \`$(shasum -a 256 "$src" | cut -c1-16)\` |")
    fi
    continue
  fi
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
  # A remote-tracking ref is only as fresh as the last fetch, and `git fetch
  # origin main` does not always move it (seen 2026-11-06): ask the remote.
  note=""
  full="$(git -C "$repo" rev-parse --symbolic-full-name "$ref" 2>/dev/null || true)"
  if [[ "$full" == refs/remotes/*/* ]]; then
    remote="${full#refs/remotes/}"; branch="${remote#*/}"; remote="${remote%%/*}"
    there="$(GIT_TERMINAL_PROMPT=0 perl -e 'alarm 15; exec @ARGV' git -C "$repo" ls-remote "$remote" "refs/heads/$branch" 2>/dev/null | cut -f1 || true)"
    if [[ -n "$there" && "$there" != "$sha" ]]; then
      note=" (behind $remote, now at \`${there:0:12}\`)"
      echo "pair_stage: WARNING $repo $ref is $sha, but $remote has $there: run git -C $repo fetch $remote, then stage again" >&2
      WARNED=1
    fi
  fi
  name="$(basename "$(cd "$repo" && pwd)")"
  folder="$name"; n=2
  while [[ -e "$DEST/$folder" ]]; do folder="$name-$n"; n=$((n + 1)); done
  mkdir -p "$DEST/$folder"
  path_args=()
  if [[ -n "$paths" ]]; then IFS=',' read -r -a path_args <<< "$paths"; fi
  git -C "$repo" archive --format=tar "$sha" -- ${path_args[@]+"${path_args[@]}"} | tar -x ${EXCLUDES[@]+"${EXCLUDES[@]}"} -C "$DEST/$folder"
  when="$(git -C "$repo" show -s --format=%cI "$sha")"
  ROWS+=("| \`$folder/\` | \`$(cd "$repo" && pwd)\` | \`$ref\`$note | \`$sha\` | $when | ${paths:-all} |")
done
{
  printf '# What is staged here\n\nStaged %s by pair_stage.sh. Each repository folder is `git archive` of one repository at the commit below (tracked files only, no uncommitted changes). Cite these shas, not a branch name: the branch may have moved since.\n' "$STAMP"
  [[ ${#EXCLUDES[@]} -gt 0 ]] && printf '\nLeft out: %s\n' "$(printf '%s ' "${EXCLUDES[@]#--exclude=}")"
  if [[ ${#ROWS[@]} -gt 0 ]]; then
    printf '\n| Folder | Repository | Ref | Commit | Committed | Paths |\n|---|---|---|---|---|---|\n'
    printf '%s\n' "${ROWS[@]}"
  fi
  if [[ ${#FILES[@]} -gt 0 ]]; then
    printf '\nLoose files are copies. The program reads the original path, not the copy here; reason about the original.\n\n| Copy | Original | sha256 |\n|---|---|---|\n'
    printf '%s\n' "${FILES[@]}"
  fi
} > "$DEST/SHAS.md"
echo "STAGED=$DEST"
cat "$DEST/SHAS.md"
[[ $WARNED -eq 0 ]] || echo "pair_stage: a ref above is behind its remote; SHAS.md says which" >&2
exit
}
