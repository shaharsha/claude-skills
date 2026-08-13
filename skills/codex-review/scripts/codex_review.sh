#!/usr/bin/env bash
# Run one read-only Codex review and write both a JSON result and a rendered
# Markdown review into <repo>/.codex-review/.
#
# The read-only sandbox is forced here rather than left to the user's
# ~/.codex/config.toml, which commonly sets danger-full-access globally. A
# review has no reason to write, and a reviewer that cannot write also cannot
# be talked into writing by anything it reads in the repo.
#
# Sessions are persisted and given a label, so a later run can either continue
# the same reviewer (--resume, keeps its context) or start a clean one. Codex
# has an internal thread_name, but nothing sets it from `codex exec`, so this
# keeps its own label -> session-id map in .codex-review/sessions.json.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MODEL="${CODEX_REVIEW_MODEL:-gpt-5.6-sol}"
EFFORT="${CODEX_REVIEW_EFFORT:-high}"
REPO=""
PROMPT_FILE=""
LABEL="review"
NAME=""
RESUME=""
SCHEMA="$SKILL_DIR/assets/findings.schema.json"
EPHEMERAL=0
SEARCH=0

usage() {
  cat >&2 <<'USAGE'
usage: codex_review.sh --repo <dir> --prompt-file <file> [options]

  --repo <dir>          Repository root the reviewer works in (required)
  --prompt-file <file>  File containing the review prompt (required)
  --name <label>        Remember this session under <label> so it can be resumed
  --resume <label|uuid> Continue an existing reviewer instead of starting fresh.
                        Keeps its context; inherits its read-only sandbox.
  --label <name>        Slug for the output filenames (default: review)
  --model <id>          Codex model (default: gpt-5.6-sol)
  --effort <level>      low|medium|high|xhigh|max (default: high)
  --schema <file>       JSON Schema for the result (default: bundled findings schema)
  --no-schema           Ask for prose instead of structured findings
  --search              Give the reviewer web search. Runs server-side, so it
                        works under the read-only sandbox with no local network.
  --ephemeral           Don't persist the session (cannot be resumed later)
  --list                Print known session labels for --repo and exit

Prints the paths it wrote, with REVIEW_MD=<path> last.
USAGE
  exit 64
}

LIST_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)        REPO="${2:-}"; shift 2 ;;
    --prompt-file) PROMPT_FILE="${2:-}"; shift 2 ;;
    --name)        NAME="${2:-}"; shift 2 ;;
    --resume)      RESUME="${2:-}"; shift 2 ;;
    --label)       LABEL="${2:-}"; shift 2 ;;
    --model)       MODEL="${2:-}"; shift 2 ;;
    --effort)      EFFORT="${2:-}"; shift 2 ;;
    --schema)      SCHEMA="${2:-}"; shift 2 ;;
    --no-schema)   SCHEMA=""; shift ;;
    --search)      SEARCH=1; shift ;;
    --ephemeral)   EPHEMERAL=1; shift ;;
    --list)        LIST_ONLY=1; shift ;;
    -h|--help)     usage ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

[[ -n "$REPO" ]] || usage
[[ -d "$REPO" ]] || { echo "not a directory: $REPO" >&2; exit 66; }
REPO="$(cd "$REPO" && pwd)"
OUT_DIR="$REPO/.codex-review"
SESSIONS="$OUT_DIR/sessions.json"

# --- attribution ---------------------------------------------------------------
# Artifacts land in ONE directory per repo, so when several agents review in the
# same clone the filenames are all "<stamp>-review.md" and nothing distinguishes
# them. Measured 2026-08-05: three lanes' artifacts sat side by side in one
# .codex-review/, separable only by timestamp -- and the rendered .md names no
# branch, so a misread makes one lane cite another lane's verdict.
#
# --label already existed and was simply not used. Defaulting it from the branch
# makes the common case attributable without anyone remembering a flag, which is
# the difference between a guard and a request for vigilance.
if [[ "$LABEL" == "review" ]]; then
  _branch="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ -n "$_branch" && "$_branch" != "HEAD" ]]; then
    # me/tor-222-gained-cases -> tor-222-gained-cases, then trimmed for filename sanity
    LABEL="$(printf '%s' "${_branch##*/}" | tr -c 'A-Za-z0-9._-' '-' | cut -c1-48)"
    LABEL="${LABEL%-}"
    [[ -n "$LABEL" ]] || LABEL="review"
  fi
fi

if [[ $LIST_ONLY -eq 1 ]]; then
  python3 - "$SESSIONS" <<'PY'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1])
if not p.exists():
    print("no sessions recorded"); raise SystemExit(0)
d = json.loads(p.read_text() or "{}")
if not d:
    print("no sessions recorded"); raise SystemExit(0)
w = max(len(k) for k in d)
for k, v in sorted(d.items(), key=lambda kv: kv[1].get("updated_at", ""), reverse=True):
    print(f"{k:<{w}}  {v['session_id']}  {v.get('updated_at','')}  {v.get('label','')}")
PY
  exit 0
fi

[[ -n "$PROMPT_FILE" ]] || usage
[[ -f "$PROMPT_FILE" ]] || { echo "no such prompt file: $PROMPT_FILE" >&2; exit 66; }
command -v codex >/dev/null || { echo "codex CLI not found on PATH" >&2; exit 69; }
[[ -n "$RESUME" && "$EPHEMERAL" -eq 1 ]] && { echo "--resume and --ephemeral are incompatible" >&2; exit 64; }

mkdir -p "$OUT_DIR"

# Keep review artifacts out of git without touching the tracked .gitignore.
# .git/info/exclude is local to this clone, so it never shows up as a change.
GIT_DIR="$(git -C "$REPO" rev-parse --git-dir 2>/dev/null || true)"
if [[ -n "$GIT_DIR" ]]; then
  [[ "$GIT_DIR" = /* ]] || GIT_DIR="$REPO/$GIT_DIR"
  EXCLUDE="$GIT_DIR/info/exclude"
  mkdir -p "$(dirname "$EXCLUDE")"
  grep -qxF '.codex-review/' "$EXCLUDE" 2>/dev/null || echo '.codex-review/' >> "$EXCLUDE"
fi

# Resolve --resume through the label map; fall through if it's already a UUID.
RESUME_ID=""
if [[ -n "$RESUME" ]]; then
  RESUME_ID="$(python3 - "$SESSIONS" "$RESUME" <<'PY'
import json, sys, pathlib, re
p, key = pathlib.Path(sys.argv[1]), sys.argv[2]
d = json.loads(p.read_text() or "{}") if p.exists() else {}
if key in d:
    print(d[key]["session_id"])
elif re.fullmatch(r"[0-9a-fA-F-]{36}", key):
    print(key)
PY
)"
  if [[ -z "$RESUME_ID" ]]; then
    echo "unknown session label: $RESUME" >&2
    echo "known labels:" >&2
    "$0" --repo "$REPO" --list >&2
    exit 66
  fi
fi

STAMP="$(date +%Y%m%d-%H%M%S)"

# --- reserve a unique $BASE ----------------------------------------------------
# $STAMP is second-resolution, so two runs started in the same second with the same
# label would otherwise share every output path. That is not merely untidy. Run A
# renders its .md; run B overwrites it, hashes it and writes B's sidecar; A then
# hashes the file B left behind and writes A's sidecar last. The recorded hash
# MATCHES the bytes on disk, so a verifier reports UNCHANGED for a pair whose sha,
# prompt hash and session belong to a different round -- a confident wrong answer,
# and one that is undetectable from the two files alone.
#
# `set -o noclobber` with `: >` is an O_EXCL create: the create IS the mutual
# exclusion, so there is no window between testing and taking, which a
# `[[ -e ]]` check followed by a write would have.
_reserve_base() {
  local n=1 candidate="$OUT_DIR/$STAMP-$LABEL"
  # Probe once. Without this an unwritable directory looks like 99 collisions and
  # reports the wrong cause.
  [[ -w "$OUT_DIR" ]] || { echo "artifact directory is not writable: $OUT_DIR" >&2; exit 73; }
  while :; do
    # Two different collisions, and the lock only covers one of them. The O_EXCL
    # create excludes a CONCURRENT peer; it says nothing about a run that already
    # finished this second and released its lock at exit. Without the second test a
    # later same-second, same-label run silently overwrites a completed round's
    # artifacts. So: probe for any output already at this base, then take the lock.
    # The probe is check-then-act and cannot stand alone -- the lock is what closes
    # the race -- but the completed-run case has no race to lose.
    # `.prompt.md` is in this list because the durable-prompt copy below writes it. A base
    # whose ONLY surviving output is a prompt copy is still a taken base, and omitting it
    # would let a later run overwrite the one artifact that proves what was reviewed.
    if [[ -e "$candidate.md" || -e "$candidate.json" || -e "$candidate.log" \
       || -e "$candidate.provenance" || -e "$candidate.prompt.md" ]]; then
      :
    elif (set -o noclobber; : > "$candidate.lock") 2>/dev/null; then
      BASE="$candidate"
      return 0
    fi
    n=$((n + 1))
    if (( n > 99 )); then
      echo "could not reserve a unique artifact base: $OUT_DIR/$STAMP-$LABEL (99 taken)" >&2
      exit 70
    fi
    candidate="$OUT_DIR/$STAMP-$LABEL-$n"
  done
}
_reserve_base

# ⚠️ THE LOCK IS HELD FOR THE WHOLE RUN, AND ITS LIFETIME IS THE PROTECTION -- not
# the reservation above. Release it any earlier than process exit and a same-second
# peer acquires $BASE while this run is still writing, which reopens the collision
# the block above exists to close, with a lock in front of it. This line looks
# tidy-uppable and is not: do NOT move it earlier or scope it to the reservation.
trap 'rm -f "$BASE.lock"' EXIT

RAW="$BASE.json"
MD="$BASE.md"
LOG="$BASE.log"

# --- what the reviewer actually READ -------------------------------------------
# Captured BEFORE the run, because the tree can move under a long review.
#
# A verdict and the bytes it read are one unit. Without the sha, "three rounds,
# all clean" is a claim about a revision nobody can name -- measured 2026-08-05:
# a lane's round covered dbcaeaa while they were asking for approval on ae2495f,
# three commits later, and nothing in the .md could have revealed it. The sha
# appeared only in the .log, and only because the reviewer happened to run git
# while exploring: incidental, not recorded.
#
# DIRTY is not a footnote. codex reads the WORKING TREE, so with uncommitted
# changes the review covers no commit at all and the sha alone would overstate it.
# The PROMPT is the other half, and for a PLAN round it is the ONLY half that matters:
# a plan lives in ~/.claude/plans/, outside the repo and outside git, so the repo sha
# says nothing about the bytes reviewed. Measured 2026-08-05: a lane's plan changed three
# times while the repo sha it would have recorded stayed put, and "round 3 covers the
# previous revision" was recoverable only because codex volunteered a hash in its scan
# notes -- incidental on two rounds, absent on the third.
PROMPT_SHA="$(shasum -a 256 "$PROMPT_FILE" 2>/dev/null | awk '{print $1}')"
PROMPT_SHA="${PROMPT_SHA:-unknown}"

# OWN THE BYTES YOU CITE. Until 2026-08-07 the header pointed at the CALLER's path, whose
# lifetime this script does not control -- and lanes keep their prompts under /private/tmp
# scratchpads that clear, or inside worktrees that get removed. Measured that day, two lanes
# independently: 4 of one lane's 7 rounds already cited prompts destroyed by a /private/tmp
# clear (one round died mid-flight with CODEX_SCRIPT_EXIT=66 for exactly that reason), and
# another lost ALL artifacts of six rounds -- reviews included, not just prompts -- when its
# worktree was removed.
#
# A DANGLING citation is worse than an absent one: the sha256 makes it read as VERIFIABLE, so
# a reader believes they could check bytes that are gone, and nothing in the artifact says
# otherwise. The record looks complete. That is the same shape this header exists to prevent.
#
# Copied BEFORE the codex run, deliberately. A round that dies mid-flight is precisely the case
# where the prompt is most needed -- to relaunch it unchanged -- and most likely to be lost.
#
# ⚠️ THIS DEPENDS ON $BASE BEING RESERVED ALREADY (see _reserve_base above). Two same-second
# rounds sharing a base would otherwise have one overwrite the other's prompt copy, which is
# the collision that block exists to close -- and it would corrupt the record in the one
# direction this comment says is worst: a citation that still resolves, to the wrong bytes.
PROMPT_COPY="$BASE.prompt.md"
PROMPT_ORIGIN="$PROMPT_FILE"
if cp "$PROMPT_FILE" "$PROMPT_COPY" 2>/dev/null; then
  PROMPT_CITE="$PROMPT_COPY"
else
  # Never fail the round over provenance, but never silently downgrade the claim either:
  # cite the caller's path and say plainly that it may not outlive this round.
  PROMPT_COPY=""
  PROMPT_CITE="$PROMPT_FILE"
  echo "codex_review: WARNING could not copy the prompt next to the artifact." >&2
  echo "codex_review: citing $PROMPT_FILE, which this script does not control and may not outlive the round." >&2
fi
REVIEW_SHA="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
REVIEW_BRANCH="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
if [[ -n "$(git -C "$REPO" status --porcelain 2>/dev/null)" ]]; then
  REVIEW_DIRTY="DIRTY — uncommitted changes present; this verdict covers the WORKING TREE, not $REVIEW_SHA"
else
  REVIEW_DIRTY="clean"
fi

COMMON=(
  -m "$MODEL"
  -c "model_reasoning_effort=\"$EFFORT\""
  -c 'approval_policy="never"'
  # Verified, and contrary to what the -s flag's absence on `resume` suggests:
  # a resumed session does NOT inherit its original sandbox. Without this line a
  # resume silently falls back to the user's global config, which is frequently
  # danger-full-access. This must stay in COMMON, not the fresh-session branch.
  -c 'sandbox_mode="read-only"'
  # Codex reads AGENTS.md natively and ignores CLAUDE.md. This makes CLAUDE.md a
  # first-class instruction file for the run, so the reviewer is held to the same
  # project rules the author was, with no AGENTS.md needed anywhere.
  -c 'project_doc_fallback_filenames=["CLAUDE.md"]'
  -o "$RAW"
)
[[ -n "$SCHEMA" ]] && COMMON+=(--output-schema "$SCHEMA")
# `codex exec` rejects the --search flag; the config key is the only route. The
# search runs server-side at OpenAI, so it needs no egress from the sandbox --
# which is the only way to get web access here at all, since read-only blocks
# curl outright and macOS seatbelt ignores network_access even in write modes.
[[ "$SEARCH" -eq 1 ]] && COMMON+=(-c 'tools.web_search=true')

if [[ -n "$RESUME_ID" ]]; then
  # resume accepts neither -s nor -C. The working root comes from the original
  # session; the sandbox does not, which is why COMMON sets it via -c.
  CODEX_ARGS=(exec resume "$RESUME_ID" "${COMMON[@]}")
else
  CODEX_ARGS=(exec -C "$REPO" -s read-only "${COMMON[@]}")
  [[ "$EPHEMERAL" -eq 1 ]] && CODEX_ARGS+=(--ephemeral)
fi

# `-` makes stdin the whole prompt. Redirecting stdin from the file also stops
# codex from blocking on an inherited non-tty stdin.
set +e
(cd "$REPO" && codex "${CODEX_ARGS[@]}" - < "$PROMPT_FILE") > "$LOG" 2>&1
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo "codex exited $STATUS; last lines of $LOG:" >&2
  tail -20 "$LOG" >&2
  exit $STATUS
fi
[[ -s "$RAW" ]] || { echo "codex produced no output; see $LOG" >&2; exit 70; }

SESSION_ID="$(grep -oE 'session id: [0-9a-f-]{36}' "$LOG" | head -1 | awk '{print $3}' || true)"
[[ -z "$SESSION_ID" && -n "$RESUME_ID" ]] && SESSION_ID="$RESUME_ID"

# Record the session so a later run can continue this exact reviewer.
if [[ -n "$SESSION_ID" && "$EPHEMERAL" -eq 0 ]]; then
  KEY="${NAME:-$RESUME}"
  [[ -z "$KEY" ]] && KEY="$STAMP-$LABEL"
  python3 - "$SESSIONS" "$KEY" "$SESSION_ID" "$LABEL" <<'PY'
import json, pathlib, sys, datetime
p, key, sid, label = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
d = json.loads(p.read_text() or "{}") if p.exists() else {}
d[key] = {"session_id": sid, "label": label,
          "updated_at": datetime.datetime.now(datetime.timezone.utc)
                        .isoformat(timespec="seconds").replace("+00:00", "Z")}
p.write_text(json.dumps(d, indent=2) + "\n")
PY
  SESSION_KEY="$KEY"
fi

if [[ -n "$SCHEMA" ]]; then
  python3 "$SKILL_DIR/scripts/render_review.py" \
    --input "$RAW" --output "$MD" --repo "$REPO" \
    --model "$MODEL" --effort "$EFFORT" \
    --session "${SESSION_ID:-unknown}" --session-key "${SESSION_KEY:-}"
else
  cp "$RAW" "$MD"
fi

# Stamp provenance into the artifact the gate rule actually points at. Only for
# the rendered-markdown path -- without --schema the .md is a copy of the raw
# JSON, and prepending prose would corrupt it, so that case gets the sidecar only.
if [[ -n "$SCHEMA" && -f "$MD" ]]; then
  PROV="$(printf '> **Reviewed:** `%s` on `%s` — working tree %s\n> **Prompt artifact:** `%s`  sha256 `%s`\n> **Prompt origin:** `%s`\n> **Label:** `%s` · **Session:** `%s`\n>\n> *A verdict covers the bytes it read — the repo sha AND the prompt hash. For a PLAN\n> round the repo sha is nearly meaningless and the prompt hash is the whole claim.\n> Cite them, or the citation is about a revision nobody has.*\n\n' \
      "$REVIEW_SHA" "$REVIEW_BRANCH" "$REVIEW_DIRTY" "$PROMPT_CITE" "$PROMPT_SHA" "$PROMPT_ORIGIN" "$LABEL" "${SESSION_ID:-unknown}")"
  printf '%s' "$PROV" | cat - "$MD" > "$MD.tmp" && mv "$MD.tmp" "$MD"
fi
# Hash of the artifact AS IT FINALLY STANDS. Two things about this are load-bearing.
#
# WHY HERE, after the banner rewrite above: that rewrite is part of PRODUCING the
# artifact -- the banner IS the artifact -- so the bytes a later reader must be able
# to check include it. Hashing before the prepend would record a digest that can
# never match its own file on any --schema round, and the defect would ship green
# and surface only the first time somebody tried to verify something.
#
# WHY GUARDED: `set -euo pipefail` is in force (top of file), and an unguarded
# VAR="$(cmd)" carries the command's status, so a failure here would abort the
# script AFTER a paid review has already run -- losing the sidecar entirely. A hash
# that cannot be computed must degrade to an honest `unavailable`, never to a lost
# artifact. `|| true` on the substitution and a `:-` default are both required: the
# first stops the abort, the second covers a success that produced no output.
# `|| ARTIFACT_SHA=unavailable` sits OUTSIDE the substitution, deliberately. Written
# as "$(pipeline || true)" the failure is swallowed INSIDE, so a hasher that exits
# non-zero while emitting a valid-looking digest passes the shape check below and
# gets recorded as fact -- and every later verification then reports CHANGED for an
# untouched artifact. The `||` form keeps the pipeline's status (pipefail is on) and
# still cannot abort under `set -e`, because a compound with `||` is tested.
ARTIFACT_SHA="$(shasum -a 256 "$MD" 2>/dev/null | awk '{print $1}')" || ARTIFACT_SHA="unavailable"
# Then shape-check, because SUCCESS is not the same as a digest: a hasher exiting 0
# with malformed output would otherwise be recorded verbatim, putting a value in the
# sidecar that looks like data and is not. `unavailable` is the single honest answer
# for every way of not having a digest, so a reader never interprets a novel one.
[[ "$ARTIFACT_SHA" =~ ^[0-9a-f]{64}$ ]] || ARTIFACT_SHA="unavailable"

# Machine-readable sidecar, written UNCONDITIONALLY -- this is what a checker must read.
# The markdown header above exists only on the --schema path (without it the .md IS the raw
# JSON and prepending prose would corrupt it), so a checker keyed on the header would
# silently pass every --no-schema round: a check that cannot fail, on the artifact that
# decides whether a merge was reviewed.
# `prompt=` deliberately names the DURABLE copy beside this artifact, not the caller's path --
# that is the whole point of the copy above. `prompt_origin=` keeps the caller's path so the
# trail back to the author's working copy is not lost, and `prompt_durable=` lets a checker
# tell the two apart without string-matching a directory.
#
# ⚠️ `prompt_sha256` HASHES THE ORIGINAL, AND THE COPY IS BYTE-IDENTICAL TO IT BY
# CONSTRUCTION (plain cp, no rewriting). Both facts are needed together: the hash is what
# makes the durable copy checkable rather than merely present. If anything is ever
# interposed between the read and the copy, this claim breaks silently -- the citation
# would still resolve, to bytes whose hash no longer matches, which is the one failure
# mode worse than a dangling path.
printf 'sha=%s\nbranch=%s\ntree=%s\nprompt=%s\nprompt_sha256=%s\nprompt_origin=%s\nprompt_durable=%s\nlabel=%s\nsession=%s\nstamp=%s\nartifact_sha256=%s\n' \
  "$REVIEW_SHA" "$REVIEW_BRANCH" "$REVIEW_DIRTY" "$PROMPT_CITE" "$PROMPT_SHA" \
  "$PROMPT_ORIGIN" "$([[ -n "$PROMPT_COPY" ]] && echo yes || echo no)" \
  "$LABEL" "${SESSION_ID:-unknown}" "$STAMP" "$ARTIFACT_SHA" > "$BASE.provenance"

echo "RAW_JSON=$RAW"
echo "CODEX_LOG=$LOG"
echo "REVIEWED_SHA=$REVIEW_SHA"
echo "REVIEWED_TREE=$REVIEW_DIRTY"
[[ -n "$SESSION_ID" ]] && echo "SESSION_ID=$SESSION_ID"
[[ -n "${SESSION_KEY:-}" ]] && echo "SESSION_NAME=$SESSION_KEY"
echo "REVIEW_MD=$MD"
