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
BASE="$OUT_DIR/$STAMP-$LABEL"
RAW="$BASE.json"
MD="$BASE.md"
LOG="$BASE.log"

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

echo "RAW_JSON=$RAW"
echo "CODEX_LOG=$LOG"
[[ -n "$SESSION_ID" ]] && echo "SESSION_ID=$SESSION_ID"
[[ -n "${SESSION_KEY:-}" ]] && echo "SESSION_NAME=$SESSION_KEY"
echo "REVIEW_MD=$MD"
