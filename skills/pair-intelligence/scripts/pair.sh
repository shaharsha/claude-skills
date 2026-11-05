#!/usr/bin/env bash
# Run one turn with a second model (Codex, or Gemini through agy or OpenCode)
# and capture its answer.
#
# Every pair-intelligence mode goes through here except a Codex review, which
# keeps codex_review.sh (findings schema, provenance sidecar, verify scripts).
#
# What this script owns, so a caller never has to rediscover it:
#   - the permission tier for the mode: read-only unless the mode is browse;
#   - closed stdin: every CLI here blocks forever on an open non-tty stdin;
#   - a wall-clock timeout: none of them has one;
#   - success read from the event stream, not the exit code: all of them can
#     exit 0 after a failed turn, and Codex exits 0 when its tools failed;
#   - a label -> session map, so a later turn continues the same conversation;
#   - for agy: a private HOME, an empty workspace outside any repository, and a
#     default-deny tool gate (agy_gate.py), because agy's own rules leave
#     search, scheduling and subagents ungoverned;
#   - for browse: an isolated agent-browser started OUTSIDE the sandbox (Chrome
#     cannot start inside Codex's macOS sandbox) and torn down on exit.

set -euo pipefail

# The whole script is one brace group: bash then reads all of it before running
# any of it. Without this, editing the file during a long run (a skills-repo pull,
# say) makes bash resume reading at a shifted offset and die with a syntax error
# after the model has already answered.
{
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENGINE=""
BACKEND=""
MODE=""
PROMPT_FILE=""
CWD=""
IMAGES=()
NAME=""
RESUME=""
LABEL=""
MODEL=""
EFFORT=""
WEB=""
SCHEMA=""
TIMEOUT=""
WEB_BUDGET=""
DOMAINS=""
RUNNABLE=0
OUT_ROOT="${PAIR_OUT:-$HOME/.cache/pair-intelligence}"
OPENCODE="${PAIR_OPENCODE:-/Applications/OpenCode.app/Contents/Resources/opencode-cli}"
AGY="${PAIR_AGY:-agy}"
# agy's own home, never the user's: their signed-in account, settings and any
# hooks, MCP servers or plugins they add stay out of these runs.
AGY_HOME="${PAIR_AGY_HOME:-$HOME/.local/share/pair-intelligence/agy-home}"

usage() {
  cat >&2 <<'USAGE'
usage: pair.sh --prompt-file <abs path> [options]

  --engine codex|gemini   Which model to ask (default: codex, or the resumed session's)
  --backend agy|opencode  Gemini only: the CLI that runs it (default: agy, or
                          PAIR_GEMINI_BACKEND)
  --mode <mode>           consult | ideate | research | browse | review
                          (default: consult, or the resumed session's).
                          Sets tier, effort, web and timeout.
                          A Codex review should use codex_review.sh instead.
  --prompt-file <file>    The prompt (required; absolute path)
  --cwd <dir>             Where the model works. Default: the current directory
                          for review/consult; an empty scratch dir otherwise.
  --image <file|dir>      Image for the model to look at (repeatable); a folder
                          adds every .png/.jpg/.jpeg/.gif/.webp in it, sorted
  --name <label>          Remember this session under <label>
  --resume <label>        Continue a session started with --name
  --label <slug>          Names the run directory (default: <mode>-<engine>)
  --model <id>            Override the model
  --effort <level>        Codex: low|medium|high|xhigh|max. Gemini: low|medium|high
  --web off|cached|live   Web access (default by mode). Codex: its search tool.
                          Gemini/agy: cached = search only, live = search and
                          page fetches. Gemini/OpenCode: anything but off = fetch.
  --web-budget <n>        Gemini/agy only: searches plus page reads allowed in
                          the turn (default 40 for research, else 20)
  --schema <file>         Codex only: JSON Schema the answer must match
  --timeout <secs>        Wall-clock limit (default by mode). On agy, tools are
                          refused after 70% of it, so time is left to answer.
  --domains <a.com,b.com> Open a live browser limited to these domains (required
                          for browse; optional for the other modes). A local host
                          needs its port: localhost:5173
  --runnable              Codex review/consult only: run in a disposable copy of
                          the repo where it may run tests and write files, with
                          its network off. Not resumable.
  --selftest              Live checks of the guarantees this script relies on
                          (run after an agy or codex upgrade) and exit
  --list                  Print remembered session labels and exit

Prints RUN_DIR, SESSION_ID, SESSION_NAME, STATUS, READS (files the model read)
and TREE (the commit of --cwd, +uncommitted if it had changes), with ANSWER=<path> last.
Exit: 0 answered, 64 usage, 66 missing input, 69 missing CLI or credentials, 70 empty answer,
      71 the turn failed or ended without a final step, 75 Gemini quota ran
      out (retry later), 72 the model read no file (review/consult), 124 timed out.
USAGE
  exit "${1:-64}"
}

LIST_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --engine)      ENGINE="${2:-}"; shift 2 ;;
    --backend)     BACKEND="${2:-}"; shift 2 ;;
    --mode)        MODE="${2:-}"; shift 2 ;;
    --prompt-file) PROMPT_FILE="${2:-}"; shift 2 ;;
    --cwd)         CWD="${2:-}"; shift 2 ;;
    --image)
      if [[ -d "${2:-}" ]]; then
        _before=${#IMAGES[@]}
        while IFS= read -r _img; do IMAGES+=("$_img"); done < <(python3 -c '
import os, sys
d = os.path.abspath(sys.argv[1])
for n in sorted(os.listdir(d)):
    if n.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")) and os.path.isfile(os.path.join(d, n)):
        print(os.path.join(d, n))' "$2")
        [[ ${#IMAGES[@]} -gt $_before ]] || { echo "--image: no images in $2" >&2; exit 66; }
      else
        IMAGES+=("${2:-}")
      fi
      shift 2 ;;
    --name)        NAME="${2:-}"; shift 2 ;;
    --resume)      RESUME="${2:-}"; shift 2 ;;
    --label)       LABEL="${2:-}"; shift 2 ;;
    --model)       MODEL="${2:-}"; shift 2 ;;
    --effort)      EFFORT="${2:-}"; shift 2 ;;
    --web)         WEB="${2:-}"; shift 2 ;;
    --schema)      SCHEMA="${2:-}"; shift 2 ;;
    --timeout)     TIMEOUT="${2:-}"; shift 2 ;;
    --web-budget)  WEB_BUDGET="${2:-}"; shift 2 ;;
    --domains)     DOMAINS="${2:-}"; shift 2 ;;
    --runnable)    RUNNABLE=1; shift ;;
    --selftest)    exec bash "$SKILL_DIR/scripts/pair_selftest.sh" ;;
    --list)        LIST_ONLY=1; shift ;;
    -h|--help)     usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done

mkdir -p "$OUT_ROOT"
# Absolute, because the engine runs after a cd into its working directory.
OUT_ROOT="$(cd "$OUT_ROOT" && pwd)"
SESSIONS="$OUT_ROOT/sessions.json"

if [[ $LIST_ONLY -eq 1 ]]; then
  python3 - "$SESSIONS" <<'PY'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text() or "{}") if p.exists() else {}
if not d:
    print("no sessions recorded"); raise SystemExit(0)
w = max(len(k) for k in d)
for k, v in sorted(d.items(), key=lambda kv: kv[1].get("updated_at", ""), reverse=True):
    eng = v["engine"] + ("/" + v["backend"] if v.get("backend") else "")
    print(f"{k:<{w}}  {eng:<13}  {v['mode']:<8}  {v['session_id']}  {v.get('updated_at','')}")
PY
  exit 0
fi

# --- resume lookup ----------------------------------------------------------------
# Before any defaults: a resumed conversation keeps its engine, backend, mode and
# directory.
RESUME_ID=""
if [[ -n "$RESUME" ]]; then
  read -r RESUME_ID RESUME_ENGINE RESUME_BACKEND RESUME_MODE RESUME_CWD < <(python3 - "$SESSIONS" "$RESUME" <<'PY'
import json, sys, pathlib
p, key = pathlib.Path(sys.argv[1]), sys.argv[2]
d = json.loads(p.read_text() or "{}") if p.exists() else {}
v = d.get(key)
# Gemini sessions recorded before agy existed ran on OpenCode.
backend = v.get("backend") or ("opencode" if v["engine"] == "gemini" else "-") if v else "-"
print(f"{v['session_id']} {v['engine']} {backend} {v.get('mode', 'consult')} {v['cwd']}" if v else "- - - - -")
PY
  ) || true
  if [[ -z "$RESUME_ID" || "$RESUME_ID" == "-" ]]; then
    echo "unknown session label: $RESUME (see --list)" >&2; exit 66
  fi
  : "${ENGINE:=$RESUME_ENGINE}"
  : "${MODE:=$RESUME_MODE}"
  [[ "$RESUME_ENGINE" == "$ENGINE" ]] || { echo "session $RESUME belongs to $RESUME_ENGINE, not $ENGINE" >&2; exit 64; }
  if [[ "$RESUME_BACKEND" != "-" ]]; then
    : "${BACKEND:=$RESUME_BACKEND}"
    [[ "$RESUME_BACKEND" == "$BACKEND" ]] || { echo "session $RESUME ran on $RESUME_BACKEND, not $BACKEND" >&2; exit 64; }
  fi
  # Changing mode would change the permission tier of a live conversation.
  [[ "$RESUME_MODE" == "$MODE" ]] || { echo "session $RESUME is a $RESUME_MODE session; it cannot continue as $MODE" >&2; exit 64; }
  [[ "$MODE" != "browse" ]] || { echo "browse sessions are not resumable: start a fresh one" >&2; exit 64; }
  # The conversation lives in the directory it started in.
  CWD="$RESUME_CWD"
fi
: "${ENGINE:=codex}"
: "${MODE:=consult}"

case "$ENGINE" in codex|gemini) ;; *) echo "--engine must be codex or gemini" >&2; exit 64 ;; esac
if [[ "$ENGINE" == "gemini" ]]; then
  : "${BACKEND:=${PAIR_GEMINI_BACKEND:-agy}}"
  case "$BACKEND" in agy|opencode) ;; *) echo "--backend must be agy or opencode" >&2; exit 64 ;; esac
else
  [[ -z "$BACKEND" ]] || { echo "--backend applies to --engine gemini only" >&2; exit 64; }
fi
case "$MODE" in consult|ideate|research|browse|review) ;; *) echo "unknown --mode: $MODE" >&2; exit 64 ;; esac
[[ -n "$PROMPT_FILE" ]] || usage
[[ "$PROMPT_FILE" = /* ]] || { echo "--prompt-file must be an absolute path" >&2; exit 64; }
[[ -f "$PROMPT_FILE" ]] || { echo "no such prompt file: $PROMPT_FILE" >&2; exit 66; }
[[ -n "$(tr -d '[:space:]' < "$PROMPT_FILE")" ]] || { echo "the prompt file is empty: $PROMPT_FILE" >&2; exit 66; }
for img in ${IMAGES[@]+"${IMAGES[@]}"}; do
  [[ "$img" = /* && -f "$img" ]] || { echo "--image must be an existing absolute path: $img" >&2; exit 66; }
done
if [[ "$MODE" == "browse" && -z "$DOMAINS" ]]; then
  echo "browse needs --domains (the browser refuses every other domain)" >&2; exit 64
fi
if [[ -n "$DOMAINS" ]]; then
  command -v agent-browser >/dev/null || { echo "agent-browser not found on PATH" >&2; exit 69; }
  # OpenCode's file reader cannot leave its working directory, and outside browse
  # that directory is the project, where screenshots may not be written.
  if [[ "$BACKEND" == "opencode" && "$MODE" != "browse" ]]; then
    echo "a live browser outside browse mode needs --backend agy or --engine codex" >&2; exit 64
  fi
fi
if [[ $RUNNABLE -eq 1 ]]; then
  [[ "$ENGINE" == "codex" ]] || { echo "--runnable is Codex-only (Gemini has no shell to run code with)" >&2; exit 64; }
  case "$MODE" in review|consult) ;; *) echo "--runnable is for review and consult" >&2; exit 64 ;; esac
  [[ -z "$RESUME" && -z "$NAME" ]] || { echo "--runnable rounds are not resumable: the copy is removed after the run" >&2; exit 64; }
  git -C "${CWD:-$PWD}" rev-parse --git-dir >/dev/null 2>&1 || { echo "--runnable needs a git repository as --cwd" >&2; exit 64; }
fi
if [[ -n "$SCHEMA" ]]; then
  [[ "$ENGINE" == "codex" ]] || { echo "--schema is Codex-only" >&2; exit 64; }
  [[ "$SCHEMA" = /* && -f "$SCHEMA" ]] || { echo "--schema must be an existing absolute path" >&2; exit 66; }
fi
[[ "$TIMEOUT" =~ ^[0-9]*$ ]] || { echo "--timeout takes whole seconds" >&2; exit 64; }
if [[ -n "$WEB_BUDGET" ]]; then
  [[ "$WEB_BUDGET" =~ ^[0-9]+$ ]] || { echo "--web-budget takes a whole number" >&2; exit 64; }
  # Only agy's tool calls pass through a gate this script owns; Codex and OpenCode
  # search inside their own process, where nothing can count. A warning, not a
  # refusal: a run started in the background with both engines' flags should go on.
  if [[ "$BACKEND" != "agy" ]]; then
    echo "pair.sh: WARNING --web-budget applies to Gemini on agy only; ignored for this run" >&2
    WEB_BUDGET=""
  fi
fi

GEMINI_KEY=""
AGY_AUTH=""
AGY_PROJECT=""
if [[ "$ENGINE" == "codex" ]]; then
  command -v codex >/dev/null || { echo "codex CLI not found on PATH" >&2; exit 69; }
elif [[ "$BACKEND" == "agy" ]]; then
  command -v "$AGY" >/dev/null || { echo "agy (Antigravity CLI) not found; brew install --cask antigravity-cli, set PAIR_AGY, or use --backend opencode" >&2; exit 69; }
  # Never the Antigravity login: Google's terms forbid driving agy from other
  # tools with it. Two routes instead, and neither secret reaches argv or output:
  #   vertex - plain Vertex AI on a GCP project (startup credits), through
  #            ~/.config/gcloud/adc-agy-*.json: best a service-account key with
  #            only Vertex AI User, which never expires; or a copy of your own
  #            ADC whose quota_project_id names the project, which Google ends on
  #            a schedule. agy takes the project from the file before any
  #            environment variable, so the main ADC file (pinned to another
  #            project) is refused;
  #   key    - a Gemini API key (AI Studio).
  # auto picks vertex when PAIR_AGY_ADC names a file, or the adc-agy-*.json files
  # hold exactly one service-account key, or there is exactly one such file;
  # else key.
  AGY_AUTH="${PAIR_AGY_AUTH:-auto}"
  AGY_ADC="${PAIR_AGY_ADC:-}"
  AGY_PROJECT=""
  if [[ "$AGY_AUTH" != key && -z "$AGY_ADC" ]]; then
    AGY_ADC="$(python3 - "$HOME"/.config/gcloud/adc-agy-*.json <<'PY'
import json, os, sys
files = [f for f in sys.argv[1:] if os.path.isfile(f)]
def kind(f):
    try:
        return json.load(open(f)).get("type", "")
    except Exception:
        return ""
sa = [f for f in files if kind(f) == "service_account"]
print(sa[0] if len(sa) == 1 else files[0] if len(files) == 1 else "")
PY
)"
  fi
  case "$AGY_AUTH" in
    auto) if [[ -n "$AGY_ADC" && -f "$AGY_ADC" ]]; then AGY_AUTH=vertex; else AGY_AUTH=key; fi ;;
    vertex) [[ -n "$AGY_ADC" && -f "$AGY_ADC" ]] || { echo "PAIR_AGY_AUTH=vertex needs an ADC copy for agy: set PAIR_AGY_ADC, or create ~/.config/gcloud/adc-agy-<project>.json" >&2; exit 69; } ;;
    key) ;;
    *) echo "PAIR_AGY_AUTH must be auto, vertex or key" >&2; exit 64 ;;
  esac
  if [[ "$AGY_AUTH" == vertex ]]; then
    # Resolved, so a link to the main ADC is caught and a relative path survives
    # the cd into the scratch workspace.
    AGY_ADC="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$AGY_ADC")"
    [[ "$(basename "$AGY_ADC")" != application_default_credentials.json ]] \
      || { echo "refusing the main ADC file for agy: its quota project may bill another client; use a copy (PAIR_AGY_ADC)" >&2; exit 64; }
    # agy bills quota_project_id when the file has one (a user ADC copy always
    # does), else a service-account key's project_id: record the same project.
    AGY_PROJECT="$(python3 -c 'import json,sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("quota_project_id") or (d.get("project_id", "") if d.get("type") == "service_account" else ""))
except Exception: pass' "$AGY_ADC" 2>/dev/null)"
    [[ -n "$AGY_PROJECT" ]] || { echo "$AGY_ADC names no project (quota_project_id, or a service-account key's project_id), so agy would not know which project to bill" >&2; exit 69; }
    # Google ends these logins on a schedule (invalid_rapt), and agy then says
    # "Run 'agy' to log in", pointing at the one login this skill must not use.
    # One token refresh up front tells it apart; a network hiccup is not a verdict.
    ADC_STATE="$(PAIR_AGY_ADC_CHECK="${PAIR_AGY_ADC_CHECK:-}" python3 - "$AGY_ADC" <<'PY'
import json, os, sys, urllib.error, urllib.parse, urllib.request
mode = os.environ.get("PAIR_AGY_ADC_CHECK", "")   # skip | expired: for the offline tests
if mode in ("skip", "expired"):
    print({"skip": "ok", "expired": "expired"}[mode]); sys.exit()
try:
    d = json.load(open(sys.argv[1]))
    if d.get("type") != "authorized_user":
        print("ok"); sys.exit()
    data = urllib.parse.urlencode({"client_id": d["client_id"], "client_secret": d["client_secret"],
                                   "refresh_token": d["refresh_token"], "grant_type": "refresh_token"}).encode()
    urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=10)
    print("ok")
except urllib.error.HTTPError as e:
    print("expired" if e.code in (400, 401) else "unknown")
except Exception:
    print("unknown")
PY
)"
    if [[ "$ADC_STATE" == expired ]]; then
      HINT="the Vertex AI login in $AGY_ADC has expired: run 'gcloud auth application-default login', then refresh the copy (~/.local/bin/agy-vertex --refresh-adc on this Mac)"
      if [[ "${PAIR_AGY_AUTH:-auto}" == vertex ]]; then
        echo "$HINT" >&2; exit 69
      fi
      echo "pair.sh: $HINT; this run uses the Gemini API key instead" >&2
      AGY_AUTH=key; AGY_PROJECT=""
    fi
  fi
  if [[ "$AGY_AUTH" == vertex ]]; then
    :
  else
    GEMINI_KEY="${GEMINI_API_KEY:-}"
    [[ -n "$GEMINI_KEY" ]] || GEMINI_KEY="$(python3 -c 'import json,os
try: print(json.load(open(os.path.expanduser("~/.local/share/opencode/auth.json")))["google"]["key"])
except Exception: pass' 2>/dev/null)"
    [[ -n "$GEMINI_KEY" ]] || { echo "no Gemini API key: set GEMINI_API_KEY, or log OpenCode in to Google (auth.json)" >&2; exit 69; }
  fi
else
  [[ -x "$OPENCODE" ]] || { echo "OpenCode v2 CLI not found at $OPENCODE (set PAIR_OPENCODE)" >&2; exit 69; }
  # v1 and v2 share one database but not one flag set; v1 on a v2-migrated
  # database is known to break it.
  "$OPENCODE" --version 2>/dev/null | grep -q 'v2\.' || { echo "$OPENCODE is not OpenCode v2" >&2; exit 69; }
fi

# --- per-mode defaults ----------------------------------------------------------
# Effort: a consult or brainstorm at Codex's high effort took 2-5 minutes a round
# in the baseline runs; review keeps high because that is where depth pays.
if [[ "$ENGINE" == "codex" ]]; then
  : "${MODEL:=gpt-6.1-sol}"
  case "$MODE" in
    review)   : "${EFFORT:=high}";   : "${WEB:=off}" ;;
    consult)  : "${EFFORT:=medium}"; : "${WEB:=cached}" ;;
    ideate)   : "${EFFORT:=medium}"; : "${WEB:=cached}" ;;
    research) : "${EFFORT:=medium}"; : "${WEB:=live}" ;;
    browse)   : "${EFFORT:=low}";    : "${WEB:=off}" ;;
  esac
else
  # Gemini 4 Argon at low effort spent 0 reasoning tokens and got a math check
  # wrong; keep it at medium or above unless the caller says otherwise.
  : "${MODEL:=gemini-4-argon}"
  case "$MODE" in
    review|consult) : "${EFFORT:=high}" ;;
    *)              : "${EFFORT:=medium}" ;;
  esac
  # "off" leaves a review of a private repo no channel to send file contents out
  # (search queries and fetched URLs both carry text). On agy, cached is search
  # only and live adds page fetches; on OpenCode, which has no search, anything
  # but off turns on webfetch.
  case "$MODE" in review|browse) : "${WEB:=off}" ;; research) : "${WEB:=live}" ;; *) : "${WEB:=cached}" ;; esac
fi
# Gemini 4 Argon at high effort reviews slowly: 4 of 10 successful reviews on
# 2026-11-02/04 ran past 1000 s, and one was cut at 1200 s while writing.
[[ "$ENGINE" == gemini && "$MODE" == review ]] && : "${TIMEOUT:=1800}"
case "$MODE" in
  review)  : "${TIMEOUT:=1200}" ;;
  research|browse) : "${TIMEOUT:=900}" ;;
  *)       : "${TIMEOUT:=600}" ;;
esac
# agy, given unlimited search, spent a whole review on 159 searches and returned
# nothing (measured): it gets a web budget and stops using tools at 70% of the time.
case "$MODE" in research) : "${WEB_BUDGET:=40}" ;; *) : "${WEB_BUDGET:=20}" ;; esac
case "$WEB" in off|cached|live|"") ;; *) echo "--web must be off, cached or live" >&2; exit 64 ;; esac
if [[ "$ENGINE" == "codex" ]]; then
  case "$EFFORT" in low|medium|high|xhigh|max) ;; *) echo "Codex --effort: low|medium|high|xhigh|max" >&2; exit 64 ;; esac
else
  case "$EFFORT" in low|medium|high) ;; *) echo "Gemini --effort: low|medium|high" >&2; exit 64 ;; esac
  MODEL="${MODEL#google/}"
  # agy names a model and its effort together (gemini-4-argon-high).
  if [[ "$BACKEND" == "agy" ]]; then
    if [[ "$MODEL" =~ -(low|medium|high)$ ]]; then EFFORT="${BASH_REMATCH[1]}"; else MODEL="$MODEL-$EFFORT"; fi
  fi
fi
: "${LABEL:=$MODE-$ENGINE}"
LABEL="$(printf '%s' "$LABEL" | tr -c 'A-Za-z0-9._-' '-' | cut -c1-48)"

# --- run directory --------------------------------------------------------------
# Outside the repo on purpose: the old review wrapper wrote into the repo it read,
# which a "don't touch this repo" consult cannot allow. mkdir is atomic, so two
# same-second runs with one label get different directories.
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR=""
for n in "" -2 -3 -4 -5 -6 -7 -8 -9; do
  if mkdir "$OUT_ROOT/$STAMP-$LABEL$n" 2>/dev/null; then RUN_DIR="$OUT_ROOT/$STAMP-$LABEL$n"; break; fi
done
[[ -n "$RUN_DIR" ]] || { echo "could not create a run directory under $OUT_ROOT" >&2; exit 73; }

if [[ -z "$CWD" ]]; then
  case "$MODE" in
    review|consult) CWD="$PWD" ;;
    # No repo, no secrets: a model with web content in its context should have
    # nothing private within reach of its working directory. A random temp dir,
    # not one beside the run directories: a model that goes looking around its
    # cwd finds other runs' answers there (measured: Gemini quoted another
    # session's brainstorm), which ends the independence of a two-engine round.
    *) CWD="$(mktemp -d "${TMPDIR:-/tmp}/pair-work.XXXXXX")" ;;
  esac
fi
# A remembered conversation whose temp dir was cleaned up gets an empty one back.
mkdir -p "$CWD"
CWD="$(cd "$CWD" && pwd)"
# A browsing model reads untrusted pages with network on; keep it away from code.
if [[ "$MODE" == "browse" ]] && git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
  echo "browse will not run inside a git repository ($CWD); use an empty --cwd" >&2; exit 64
fi
# agy may read only what pair.sh names, starting with the working directory; a
# home directory there would open every credential file in it.
if [[ "$BACKEND" == "agy" ]] && [[ "$CWD" == "/" || "$CWD" == "$(cd "$HOME" && pwd)" ]]; then
  echo "Gemini reads only inside --cwd, and $CWD is too wide; pass the project folder" >&2; exit 64
fi

# Say where the run lives before it starts: events.jsonl there grows as the model
# works, which is the only progress there is until STATUS.
echo "pair.sh: started; follow $RUN_DIR/events.jsonl" >&2
# The model reads --cwd. Output written inside it (this run's own stdout or
# stderr, or the run folder) is readable by it, and by a second engine asked the
# same question in the same folder (measured 2026-11-05: each engine's run log
# sat where the other could read it). The paths of fds 1 and 2 come from the OS.
python3 - "$CWD" "$RUN_DIR" <<'PY' || true
import fcntl, os, sys
cwd, run_dir = os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])
def inside(p):
    return os.path.commonpath((cwd, p)) == cwd   # also right for --cwd /
def path_of(fd):
    try:
        if hasattr(fcntl, "F_GETPATH"):          # macOS
            return os.path.realpath(fcntl.fcntl(fd, fcntl.F_GETPATH, b"\0" * 1024).split(b"\0", 1)[0].decode())
        return os.path.realpath(os.readlink("/proc/self/fd/%d" % fd))   # Linux
    except (OSError, ValueError):
        return ""
seen = []
for fd, label in ((1, "stdout"), (2, "stderr")):
    p = path_of(fd)
    if p and os.path.isfile(p) and inside(p):
        seen.append("%s goes to %s" % (label, p))
if inside(run_dir):
    seen.append("the run folder is %s" % run_dir)
if seen:
    sys.stderr.write("pair.sh: WARNING %s, inside --cwd %s: the model can read it, and so can a second engine asked "
                     "in the same folder. Write logs and PAIR_OUT outside --cwd.\n" % ("; ".join(seen), cwd))
PY

PROMPT="$RUN_DIR/prompt.md"
EVENTS="$RUN_DIR/events.jsonl"
ERRLOG="$RUN_DIR/stderr.log"
ANSWER="$RUN_DIR/answer.md"

# --- a runnable copy -----------------------------------------------------------------
# Where the engine works: the directory itself, or for --runnable a disposable
# copy of its repository (pair_scratch.sh), removed on exit.
RUN_CWD="$CWD"
SHOTS=""
SCRATCH_PARENT=""
AGY_WS=""
cleanup() {
  [[ -n "$AGY_WS" ]] && rm -rf "$AGY_WS"
  [[ -n "$SCRATCH_PARENT" ]] && bash "$SKILL_DIR/scripts/pair_scratch.sh" remove "$CWD" "$SCRATCH_PARENT" >/dev/null 2>&1
  pb_cleanup
  return 0
}
# shellcheck source=pair_browser.sh
source "$SKILL_DIR/scripts/pair_browser.sh"
trap cleanup EXIT
if [[ $RUNNABLE -eq 1 ]]; then
  # A runnable Codex may write to temp folders: the real repo, this skill (the
  # host runs its scripts later) and the run's files must not be in one.
  bash "$SKILL_DIR/scripts/pair_scratch.sh" check "$(git -C "$CWD" rev-parse --show-toplevel)" "$SKILL_DIR" "$RUN_DIR" || exit 64
  SCRATCH_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/pair-run.XXXXXX")"
  RUN_CWD="$(bash "$SKILL_DIR/scripts/pair_scratch.sh" create "$CWD" "$SCRATCH_PARENT")" \
    || { echo "could not make a runnable copy of $CWD" >&2; exit 71; }
fi

# --- live browser: an isolated agent-browser host ---------------------------------
# All of it lives in pair_browser.sh, shared with codex_review.sh.
if [[ -n "$DOMAINS" ]]; then
  # Screenshots never land in a repository: in browse they go inside the scratch
  # working directory (an OpenCode agent may not read outside it), otherwise in
  # the run directory.
  if [[ "$MODE" == "browse" ]]; then SHOTS="$CWD/shots"; else SHOTS="$RUN_DIR/shots"; fi
  PB_DIR="$RUN_DIR"
  PB_CHECK_DIR="$CWD"
  PB_SANDBOX_CWD="$RUN_CWD"
  PB_BASE_PROFILE=":read-only"; [[ $RUNNABLE -eq 1 ]] && PB_BASE_PROFILE=":workspace"
  pb_setup
fi

# --- agy: what Gemini may touch ---------------------------------------------------
# agy offers the model no list or search tool in API-key mode, and its gate
# refuses every shell command but these wrappers, so pair-fs is how it looks
# around; the harness block says so, since the model cannot discover it.
if [[ "$BACKEND" == "agy" ]]; then
  AGY_ROOTS=("$CWD" ${IMAGES[@]+"${IMAGES[@]}"})
  [[ -n "$SHOTS" && "$SHOTS" != "$CWD"/* ]] && AGY_ROOTS+=("$SHOTS")
  AGY_CMDS=()
  [[ -n "$DOMAINS" ]] && AGY_CMDS+=(pair-browser)
  if [[ "$MODE" != "browse" ]]; then
    AGY_CMDS+=(pair-fs)
    mkdir -p "$RUN_DIR/bin"
    ROOTS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "${AGY_ROOTS[@]}")"
    # bash -p and env -i for the same reasons as pair-browser: the model's shell
    # environment must not reach the code that does the reading.
    printf '#!/bin/bash -p\n# pair-fs: generated by pair.sh for one run.\nexec /usr/bin/env -i PATH=/usr/bin:/bin PAIR_FS_ROOTS=%q /usr/bin/python3 -I %q "$@"\n' \
      "$ROOTS_JSON" "$SKILL_DIR/scripts/pair_fs.py" > "$RUN_DIR/bin/pair-fs"
    chmod 755 "$RUN_DIR/bin/pair-fs"
  fi
  # agy can search but has no page reader in API-key mode; live web gets one.
  if [[ "$WEB" == "live" ]]; then
    AGY_CMDS+=(pair-fetch)
    mkdir -p "$RUN_DIR/bin"
    printf '#!/bin/bash -p\n# pair-fetch: generated by pair.sh for one run.\nexec /usr/bin/env -i PATH=/usr/bin:/bin /usr/bin/python3 -I %q "$@"\n' \
      "$SKILL_DIR/scripts/pair_fetch.py" > "$RUN_DIR/bin/pair-fetch"
    chmod 755 "$RUN_DIR/bin/pair-fetch"
  fi
fi

# --- the prompt -------------------------------------------------------------------
dur() { if [[ $1 -ge 120 ]]; then echo "$(( $1 / 60 )) minutes"; else echo "$1 seconds"; fi; }
{
  [[ -n "$DOMAINS" ]] && pb_harness
  if [[ $RUNNABLE -eq 1 ]]; then
    printf '<harness>\nYou are working in a disposable copy of the repository at %s: the same commit with the same uncommitted changes. You may run tests and scripts and write files there; nothing you change reaches the real repository, and the network is off (no package downloads). Dependency folders such as node_modules or .venv are links to the real ones and read-only.\n</harness>\n\n' "$RUN_CWD"
  fi
  if [[ "$BACKEND" == "agy" && "$MODE" != "browse" ]]; then
    case "$WEB" in
      off)    WEBLINE="Web search is off for this run." ;;
      cached) WEBLINE="You can search the web (search_web); reading pages is off." ;;
      live)   WEBLINE="You can search the web (search_web), and read a page as text by running \`pair-fetch <url>\`: check claims against the page itself, not the search snippet." ;;
    esac
    printf '<harness>\nThe project is the folder %s. Read files with your file-reading tool, using absolute paths under it.\n' "$CWD"
    printf 'To list folders, find files by name, search contents or read git history, run the `pair-fs` command (on your PATH):\n'
    printf '  pair-fs ls [PATH] | pair-fs find GLOB [PATH] | pair-fs grep [-i] [-F] [-l] [--glob G] PATTERN [PATH] | pair-fs git status|diff|log|show|blame [ARGS] | pair-fs git cat REV PATH\n'
    printf 'PATH is absolute or relative to the project folder; `pair-fs git` with no subcommand prints the accepted flags. Put search patterns and any text with spaces or symbols in single quotes: outside quotes the shell accepts only letters, digits and _./:@,+=%%-. Nothing else runs: other shell commands, writing files and reading outside the project or secret files are refused with a reason. %s\n</harness>\n\n' "$WEBLINE"
  fi
  if [[ "$BACKEND" == "agy" ]]; then
    # A turn cut off by the time limit in the middle of tool calls returns no text
    # at all, so the model is told its budget up front, and the gate enforces it.
    BUDGETLINE=""
    [[ "$WEB" != off ]] && BUDGETLINE=" Web searches and page reads are limited to $WEB_BUDGET in all; spend them on what matters most."
    printf '<harness>\nYou have about %s for this turn. After about %s every tool call is refused, so finish looking things up by then and leave time to write your answer: a turn cut off by the time limit returns nothing.%s Quote a file only with text you read from it in this turn, with its path and line; anything you recall or paraphrase, say so.\n</harness>\n\n' \
      "$(dur "$TIMEOUT")" "$(dur $(( TIMEOUT * 7 / 10 )))" "$BUDGETLINE"
  fi
  cat "$PROMPT_FILE"
  # Codex opens images with its view_image tool and agy with its file reader;
  # OpenCode gets them attached with -f. Codex's own -i flag is avoided: it is
  # variadic and swallows the prompt that follows it.
  if [[ ${#IMAGES[@]} -gt 0 && "$BACKEND" != "opencode" ]]; then
    TOOLNAME="image viewing tool"; [[ "$BACKEND" == "agy" ]] && TOOLNAME="file-reading tool"
    printf '\n\n<images>\nThese local image files are part of the task. Open each one with your %s:\n' "$TOOLNAME"
    for img in "${IMAGES[@]}"; do printf -- '- %s\n' "$img"; done
    printf '</images>\n'
  fi
} > "$PROMPT"

# --- timeout --------------------------------------------------------------------
run_limited() {
  if command -v timeout >/dev/null; then timeout --kill-after=15 "$TIMEOUT" "$@"
  elif command -v gtimeout >/dev/null; then gtimeout --kill-after=15 "$TIMEOUT" "$@"
  else perl -e 'alarm shift; exec @ARGV or die "exec: $!"' "$TIMEOUT" "$@"
  fi
}

# --- run ------------------------------------------------------------------------
# What the model read: the commit of --cwd, and whether files there differed
# from it, recorded before the run because the tree can move during it.
TREE=""
if git -C "$CWD" rev-parse --verify -q HEAD >/dev/null 2>&1; then
  TREE="$(git -C "$CWD" rev-parse HEAD)"
  [[ -n "$(git -C "$CWD" status --porcelain 2>/dev/null | head -1)" ]] && TREE="$TREE+uncommitted"
fi
START="$(date +%s)"
RETRIED=0
RETRY_FROM=0
set +e
if [[ "$ENGINE" == "codex" ]]; then
  if [[ $USE_BROKER -eq 1 ]]; then
    # Any mode with a browser, browse included: read-only (or the writable copy)
    # with one unix socket open, the broker's.
    TIER=("${CODEX_BROKER_TIER[@]}")
    SANDBOX_FLAG=()
  elif [[ $RUNNABLE -eq 1 ]]; then
    # Writes only inside the disposable copy (and temp dirs), network off.
    TIER=(-c 'sandbox_mode="workspace-write"' -c 'sandbox_workspace_write.network_access=false')
    SANDBOX_FLAG=(-s workspace-write)
  else
    # Forced on every call, resume included: a resumed session does not inherit
    # its sandbox, and this machine's global config is commonly full access.
    TIER=(-c 'sandbox_mode="read-only"')
    SANDBOX_FLAG=(-s read-only)
  fi
  case "$WEB" in off) WEBCFG='web_search="disabled"' ;; cached) WEBCFG='web_search="cached"' ;; live) WEBCFG='web_search="live"' ;; esac
  # --ignore-user-config: the user's config.toml loads MCP servers (Linear, with
  # write tools) and the ChatGPT app's browser and computer-use plugins, all
  # outside the sandbox. Auth still comes from CODEX_HOME. The project-doc limit
  # it set is restated, or a long CLAUDE.md is cut at 32 KiB.
  # shellcheck source=codex_lockdown.sh
  source "$SKILL_DIR/scripts/codex_lockdown.sh"
  COMMON=(--json --skip-git-repo-check --ignore-user-config "${CODEX_LOCKDOWN[@]}" -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\""
          -c 'approval_policy="never"' -c "$WEBCFG" "${TIER[@]}"
          -c 'project_doc_fallback_filenames=["CLAUDE.md"]' -c 'project_doc_max_bytes=400000' -o "$ANSWER")
  [[ -n "$SCHEMA" ]] && COMMON+=(--output-schema "$SCHEMA")
  if [[ -n "$RESUME_ID" ]]; then
    ARGS=(exec resume "$RESUME_ID" "${COMMON[@]}" -)
  else
    ARGS=(exec -C "$RUN_CWD" ${SANDBOX_FLAG[@]+"${SANDBOX_FLAG[@]}"} "${COMMON[@]}" -)
  fi
  (cd "$RUN_CWD" && PATH="$RUN_DIR/bin:$PATH" run_limited codex "${ARGS[@]}" < "$PROMPT") > "$EVENTS" 2> "$ERRLOG"
  RC=$?
elif [[ "$BACKEND" == "agy" ]]; then
  # The workspace is an empty folder outside any repository. agy loads hooks,
  # MCP servers, rules and agents from .agents/ in its workspace and every parent
  # up to the repository root, and it starts a repo's MCP servers even when MCP
  # tools are denied (measured), so the project is a folder it may read, never
  # its workspace.
  AGY_WS="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/pair-agy.XXXXXX")" && pwd -P)"
  if git -C "$AGY_WS" rev-parse --git-dir >/dev/null 2>&1; then
    echo "agy's scratch workspace $AGY_WS is inside a git repository; set TMPDIR elsewhere" >&2; exit 71
  fi
  POLICY="$RUN_DIR/agy-policy.json"
  python3 - "$POLICY" "$WEB" "$RUN_DIR/bin" "$RUN_DIR/gate.log" "$(( $(date +%s) + TIMEOUT * 7 / 10 ))" "$WEB_BUDGET" \
    "${AGY_CMDS[*]:-}" "${AGY_ROOTS[@]}" <<'PY'
import json, sys
path, web, bindir, log, until, budget, cmds, *roots = sys.argv[1:]
json.dump({"roots": roots, "web": web, "commands": cmds.split(), "bin": bindir, "log": log,
           "tools_until": int(until), "web_budget": int(budget)}, open(path, "w"), indent=2)
PY
  # The gate lives in agy's private home; rewritten every run (same bytes, atomic)
  # so a moved skill folder or a hand edit cannot leave a stale or open gate.
  mkdir -p "$AGY_HOME/.gemini/config"
  python3 - "$AGY_HOME/.gemini/config/hooks.json" "$SKILL_DIR/scripts/agy_gate.py" <<'PY'
import json, os, shlex, sys, tempfile
dest, gate = sys.argv[1], sys.argv[2]
body = {"pair-intelligence-gate": {"PreToolUse": [{"matcher": "*", "hooks": [
    {"type": "command", "command": "/usr/bin/python3 -I " + shlex.quote(gate), "timeout": 20}]}]}}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), prefix=".hooks.")
with os.fdopen(fd, "w") as f:
    json.dump(body, f, indent=2)
os.replace(tmp, dest)
PY
  # The settings floor under the gate: agy enforces these even if the gate fails.
  SETTINGS="$RUN_DIR/agy-settings.json"
  python3 - "$SETTINGS" "$WEB" "${AGY_CMDS[*]:-}" "$AGY_AUTH" <<'PY'
import json, sys
path, web, cmds, auth = sys.argv[1], sys.argv[2], sys.argv[3].split(), sys.argv[4]
deny = ["write_file(*)", "execute_url(*)", "read_url(*)", "mcp(*)", "command(regex:.*[;&|`$<>\\n\\r].*)"]
settings = {"permissions": {"allow": ["command(%s)" % c for c in cmds], "deny": deny}}
if auth == "key":
    settings["modelProvider"] = "gemini"   # on the Vertex route this would switch back to key mode
json.dump(settings, open(path, "w"), indent=2)
PY
  python3 -c 'import json,sys; print(json.dumps({"event": "user", "message": {"content": open(sys.argv[1]).read()}}))' \
    "$PROMPT" > "$RUN_DIR/agy-input.jsonl"
  ARGS=(--settings "$SETTINGS" --model "$MODEL" --input-format stream-json --output-format stream-json
        --print-timeout "$(( TIMEOUT > 20 ? TIMEOUT - 10 : TIMEOUT ))s" --disable-slash-commands)
  [[ -n "$RESUME_ID" ]] && ARGS+=(--conversation "$RESUME_ID")
  if [[ "$AGY_AUTH" == vertex ]]; then
    AUTH_ENV=(AGY_ADC_AUTH=true GOOGLE_CLOUD_LOCATION=global GOOGLE_APPLICATION_CREDENTIALS="$AGY_ADC")
  else
    AUTH_ENV=(GEMINI_API_KEY="$GEMINI_KEY")
  fi
  run_agy() {  # $1: input file; appends to the event and error logs
    (cd "$AGY_WS" && unset GEMINI_API_KEY GOOGLE_API_KEY GOOGLE_CLOUD_QUOTA_PROJECT AGY_ADC_AUTH GOOGLE_APPLICATION_CREDENTIALS \
       && export HOME="$AGY_HOME" PAIR_GATE_POLICY="$POLICY" PATH="$RUN_DIR/bin:$PATH" "${AUTH_ENV[@]}" \
       && run_limited "$AGY" "${ARGS[@]}" < "$1") >> "$EVENTS" 2>> "$ERRLOG"
  }
  : > "$EVENTS"; : > "$ERRLOG"
  run_agy "$RUN_DIR/agy-input.jsonl"
  RC=$?
  # On the Vertex route agy once failed in 20 s with "authentication required"
  # and the next run worked (2026-11-03): a token fetch that failed, not the key,
  # which the check above had just used. One retry; agy's own advice in that
  # message is to use its login, which this skill must not.
  if [[ $RC -ne 0 && ! -s "$EVENTS" && "$AGY_AUTH" == vertex ]] && grep -qE 'authentication (required|failed)' "$ERRLOG"; then
    echo "agy: could not authenticate to Vertex AI; retrying once" >> "$ERRLOG"
    sleep "${PAIR_AGY_AUTH_RETRY_WAIT:-5}"
    run_agy "$RUN_DIR/agy-input.jsonl"
    RC=$?
  fi
  # A Vertex project's tokens-per-minute quota can run out mid-turn (429
  # RESOURCE_EXHAUSTED, the turn then marked ERROR). Wait a minute and continue
  # the same conversation once, if the time budget allows.
  # Not when the answer was already complete: twice the 429 came after the
  # answer's step had finished, and a retry only wrote the answer again.
  python3 - "$EVENTS" > "$RUN_DIR/.quota" <<'PY'
import json, sys
last, step, answered = None, None, False
for line in open(sys.argv[1], errors="replace"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("event") == "step_update":
        s = e.get("step_update") or {}
        step = (s.get("step_type"), s.get("state"))
    elif e.get("event") == "result":
        last = e.get("result") or {}
        answered = step == ("agent_response", "DONE") and bool((last.get("response") or "").strip())
if last and last.get("status") != "SUCCESS" and "RESOURCE_EXHAUSTED" in (last.get("error") or "") and not answered:
    print(last.get("conversation_id", ""))
PY
  QUOTA_CONV="$(cat "$RUN_DIR/.quota")"; rm -f "$RUN_DIR/.quota"
  RETRY_WAIT="${PAIR_AGY_RETRY_WAIT:-60}"
  LEFT=$(( TIMEOUT - ($(date +%s) - START) - RETRY_WAIT ))
  if [[ -n "$QUOTA_CONV" && "$AGY_AUTH" == vertex && $LEFT -gt 120 ]]; then
    echo "agy: Vertex AI quota exhausted; retrying once in ${RETRY_WAIT}s with the ${LEFT}s left (conversation $QUOTA_CONV)" >> "$ERRLOG"
    sleep "$RETRY_WAIT"
    RETRIED=1
    # The retry gets what is left of the budget, not a fresh one, and its own
    # point after which tools are refused; the web budget carries over.
    TIMEOUT=$LEFT
    for i in "${!ARGS[@]}"; do
      [[ "${ARGS[$i]}" == --print-timeout ]] && ARGS[$((i + 1))]="$(( LEFT > 20 ? LEFT - 10 : LEFT ))s"
    done
    python3 - "$POLICY" "$(( $(date +%s) + LEFT * 7 / 10 ))" <<'PY'
import json, os, sys
p = sys.argv[1]
d = json.load(open(p))
d["tools_until"] = int(sys.argv[2])
json.dump(d, open(p + ".new", "w"), indent=2)
os.replace(p + ".new", p)
PY
    python3 -c 'import json; print(json.dumps({"event": "user", "message": {"content": "Your last turn was cut off by a rate limit. Finish the task and give your complete final answer."}}))' \
      > "$RUN_DIR/agy-retry.jsonl"
    [[ -n "$RESUME_ID" ]] || ARGS+=(--conversation "$QUOTA_CONV")
    # The outcome is the retry's alone: a retry that ends with no result must not
    # be read as the first attempt's quota error again.
    RETRY_FROM="$(python3 -c 'import sys; print(len(open(sys.argv[1], errors="replace").read().splitlines()))' "$EVENTS")"
    run_agy "$RUN_DIR/agy-retry.jsonl"
    RC=$?
  fi
else
  # A read-only agent: deny everything, then allow reading and fetching. Tools it
  # may not use are not even offered to the model. external_directory falls under
  # the deny, so it cannot read outside its working directory either.
  AGENT_CFG='{"agents":{"pair":{"description":"read-only second opinion","permissions":[
    {"action":"*","resource":"*","effect":"deny"},
    {"action":"read","resource":"*","effect":"allow"},
    {"action":"glob","resource":"*","effect":"allow"},
    {"action":"grep","resource":"*","effect":"allow"},'
  [[ "$WEB" == off ]] || AGENT_CFG+='
    {"action":"webfetch","resource":"*","effect":"allow"},'
  AGENT_CFG+='
    {"action":"read","resource":"*.env","effect":"deny"},
    {"action":"read","resource":"*.env.*","effect":"deny"}'
  if [[ "$MODE" == "browse" ]]; then
    # OpenCode has no OS sandbox, so its shell is confined by rule: the generated
    # pair-browser wrapper is the only command allowed (agent-browser itself is
    # not), and the wrapper validates everything after it. What the shell itself
    # would carry out is refused on the raw text: redirection, $ expansion,
    # command substitution, and the parentheses, braces and tilde through which
    # zsh runs code from a glob qualifier (*(e:'cmd':)) or expands other text.
    # Any deny wins.
    for cmd in pair-browser "$WRAP"; do
      AGENT_CFG+=",
    {\"action\":\"shell\",\"resource\":\"$cmd *\",\"effect\":\"allow\"}"
      for pat in '*>*' '*<*' '*$*' '*`*' '*(*' '*)*' '*{*' '*}*' '*~*'; do
        AGENT_CFG+=",
    {\"action\":\"shell\",\"resource\":\"$cmd $pat\",\"effect\":\"deny\"}"
      done
    done
  fi
  AGENT_CFG+=']}}}'
  ARGS=(run --standalone --agent pair -m "google/$MODEL#$EFFORT" --format json --title "$LABEL")
  for img in ${IMAGES[@]+"${IMAGES[@]}"}; do ARGS+=(-f "$img"); done
  [[ -n "$RESUME_ID" ]] && ARGS+=(-s "$RESUME_ID")
  # OPENCODE_DISABLE_CLAUDE_CODE keeps Claude's own CLAUDE.md and skills out of
  # the other model's context (v1 loads them; v2 reads only AGENTS.md).
  # The prompt goes on stdin, not as an argument, where any local process could
  # read it in `ps`.
  (cd "$CWD" && PATH="$RUN_DIR/bin:$PATH" OPENCODE_CONFIG_CONTENT="$AGENT_CFG" OPENCODE_DISABLE_CLAUDE_CODE=1 \
     run_limited "$OPENCODE" "${ARGS[@]}" < "$PROMPT") > "$EVENTS" 2> "$ERRLOG"
  RC=$?
fi
set -e
SECS=$(( $(date +%s) - START ))

# --- read the outcome from the events -------------------------------------------
STATUS="failed"; SESSION_ID="-"
# Written to a file, not read through <(...): bash mis-parses a heredoc this long
# inside a process substitution.
python3 - "${BACKEND:-$ENGINE}" "$EVENTS" "$ANSWER" "$RC" "$RUN_DIR/tools.txt" "$ERRLOG" "$RETRY_FROM" \
  "$MODE" "$RUN_CWD" > "$RUN_DIR/.status" <<'PY'
import json, os, shlex, sys, pathlib
engine, events, answer, rc = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), int(sys.argv[4])
errlog = pathlib.Path(sys.argv[6])
retry_from = int(sys.argv[7])   # agy: events before this line belong to the attempt before a retry
evs, before_retry = [], set()
for i, line in enumerate(events.read_text(errors="replace").splitlines() if events.exists() else []):
    try: evs.append(json.loads(line))
    except ValueError: continue
    if i < retry_from:
        before_retry.add(len(evs) - 1)
sid, failed, completed, denied, quota, results = "", False, False, False, False, 0
reads = -1   # files the model read: shell commands for Codex, file tools for agy; -1 unknown
step = None   # agy: the (type, state) of the last step before each result
if engine == "codex":
    reads = 0
    for e in evs:
        t = e.get("type", "")
        # Codex reads files only through shell commands (cat, rg, git, sed).
        if t == "item.completed" and (e.get("item") or {}).get("type") == "command_execution":
            reads += 1
        if t == "thread.started": sid = e.get("thread_id", "") or sid
        elif t == "turn.failed": failed = True
        elif t == "turn.completed": completed = True
elif engine == "agy":
    # One "result" event ends a turn. agy reports SUCCESS and exits 0 even when a
    # permission it could not ask for ended the run with no answer; that shows
    # only in denied_actions. tools.txt lists every tool call and the gate's
    # verdict, so the caller can see what Gemini read and searched.
    lines = []
    for n, e in enumerate(evs):
        if e.get("event") == "step_update":
            s = e.get("step_update") or {}
            step = (s.get("step_type"), s.get("state"))
            if s.get("step_type") == "tool" and s.get("state") in ("DONE", "ERROR"):
                info = s.get("tool_info") or {}
                params = info.get("parameters") or {}
                if s["state"] == "DONE":
                    reads = max(reads, 0)
                    if s.get("tool_name") in ("read_file", "view_file"):
                        reads += 1
                    elif s.get("tool_name") == "run_command":
                        # The gate runs pair-fs by name or by its full path.
                        try:
                            argv0 = shlex.split(str(params.get("CommandLine", "")))[:1]
                        except ValueError:
                            argv0 = []
                        reads += bool(argv0) and os.path.basename(argv0[0]) == "pair-fs"
                arg = params.get("CommandLine") or params.get("Path") or params.get("query") \
                    or params.get("Url") or json.dumps(params)[:200]
                err = (info.get("error") or {}).get("message", "")
                lines.append(f"{s['state']:<5} {s.get('tool_name', '?'):<16} {arg}" + (f"  -> {err[:200]}" if err else ""))
        elif e.get("event") == "result":
            r = e.get("result") or {}
            results += 1
            sid = r.get("conversation_id", "") or sid
            if r.get("error"):
                # agy keeps the reason inside the result, not on stderr.
                hint = (" (Vertex AI quota: retry later, or PAIR_AGY_AUTH=key)"
                        if "RESOURCE_EXHAUSTED" in r["error"] else "")
                with open(sys.argv[6], "a") as f:
                    f.write("agy: %s%s\n" % (r["error"], hint))
            # After a retry the outcome and the answer are the retry's: neither the
            # cut-off first turn's text nor its error may stand in for them.
            if n in before_retry:
                continue
            completed = r.get("status") == "SUCCESS"
            failed = not completed
            denied = bool(r.get("denied_actions"))
            quota = failed and "RESOURCE_EXHAUSTED" in (r.get("error") or "")
            if quota and step == ("agent_response", "DONE") and (r.get("response") or "").strip():
                # The answer's step had finished before the 429 (a later call hit
                # it), so the answer is whole.
                quota, failed, completed = False, False, True
                with open(sys.argv[6], "a") as f:
                    f.write("agy: the 429 came after the answer was complete; the answer is whole\n")
            if (r.get("response") or "").strip():
                answer.write_text(r["response"].strip() + "\n")
            elif answer.exists():
                answer.unlink()
    pathlib.Path(sys.argv[5]).write_text("\n".join(lines) + ("\n" if lines else ""))
    reads = max(reads, 0)
else:
    texts = []
    for e in evs:
        sid = sid or e.get("sessionID", "")
        t = e.get("type")
        part = e.get("part") or {}
        if t == "error": failed = True
        elif t == "text": texts.append(part.get("text", ""))
        # A turn is done when its LAST step finished with reason "stop"; a step that
        # ended in tool calls, or a stream cut off after step_start, is not done.
        elif t == "step_start": completed = False
        elif t == "step_finish": completed = part.get("reason", "stop") == "stop"
    if texts:
        answer.write_text("\n\n".join(x for x in texts if x).strip() + "\n")
# agy's own --print-timeout returns what it has so far as SUCCESS with exit 0;
# only its stderr says the turn was cut (measured). A turn that ended on the
# quota is reported as that even when the print timeout fired too (agy was then
# waiting out the 429): more time would not have helped.
errtext = errlog.read_text(errors="replace") if errlog.exists() else ""
agy_cut = engine == "agy" and "print timeout after" in errtext
auth = engine == "agy" and not results and rc != 0 and ("authentication required" in errtext or "authentication failed" in errtext)
if rc in (124, 137, 142):
    status = "timeout"
elif auth:
    status = "auth"
elif quota:
    status = "quota"
elif agy_cut:
    status = "timeout"
elif denied:
    status = "denied"
elif failed:
    status = "failed"
elif not answer.exists() or not answer.read_text(errors="replace").strip():
    status = "empty"
elif not completed:
    status = "incomplete"
else:
    status = "ok"
# A review or consult that read nothing answered from the prompt alone, yet looks
# like any good run (measured three times on 2026-11-02/04: a prompt saying "you
# cannot run anything", which Codex took as a ban on reading, and a run inside
# another sandbox). Only when the folder holds something to read besides images.
mode, cwd = sys.argv[8], sys.argv[9]
images = (".png", ".jpg", ".jpeg", ".gif", ".webp")
try:
    material = any(n != ".git" and not n.lower().endswith(images) for n in os.listdir(cwd))
except OSError:
    material = False
if status == "ok" and reads == 0 and mode in ("review", "consult") and material:
    status = "unread"
print(status, sid or "-", reads)
PY
read -r STATUS SESSION_ID READS < "$RUN_DIR/.status" || true
# agy cites search results as grounding redirect links, which a reader cannot
# check as given; the answer gets the pages they point to (pair_links.py).
if [[ "$BACKEND" == agy && -s "$ANSWER" ]] && grep -q 'vertexaisearch\.cloud\.google\.com/grounding-api-redirect/' "$ANSWER"; then
  python3 "$SKILL_DIR/scripts/pair_links.py" "$ANSWER" "$RUN_DIR/source-links.json" >&2 || true
fi
rm -f "$RUN_DIR/.status"

if [[ "$STATUS" == "ok" && "$SESSION_ID" != "-" ]]; then
  KEY="${NAME:-$RESUME}"
  if [[ -n "$KEY" ]]; then
    python3 - "$SESSIONS" "$KEY" "$SESSION_ID" "$ENGINE" "$MODE" "$CWD" "$BACKEND" <<'PY'
import json, pathlib, sys, datetime
p, key, sid, engine, mode, cwd, backend = pathlib.Path(sys.argv[1]), *sys.argv[2:8]
import fcntl, os, tempfile
# Parallel runs (two engines at once) each read, add one label and write back; the
# lock makes that sequence exclusive so neither drops the other's label.
with open(p.parent / ".sessions.lock", "w") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    d = json.loads(p.read_text() or "{}") if p.exists() else {}
    d[key] = {"session_id": sid, "engine": engine, "mode": mode, "cwd": cwd,
              "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    if backend:
        d[key]["backend"] = backend
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".sessions.")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(d, indent=2) + "\n")
    os.replace(tmp, p)
PY
  fi
fi

python3 - "$RUN_DIR/meta.json" "$ENGINE" "$MODE" "$MODEL" "$EFFORT" "$WEB" "$CWD" "$STATUS" \
  "$RC" "$SECS" "$SESSION_ID" "${NAME:-$RESUME}" "$DOMAINS" "$BACKEND" "${AGY_AUTH:+$AGY_AUTH${AGY_PROJECT:+:$AGY_PROJECT}}" \
  "${READS:--1}" "$TREE" <<'PY'
import json, sys
keys = ["engine", "mode", "model", "effort", "web", "cwd", "status", "exit_code",
        "seconds", "session_id", "session_name", "domains", "backend", "auth", "reads", "tree"]
meta = dict(zip(keys, sys.argv[2:]))
meta["exit_code"], meta["seconds"], meta["reads"] = int(meta["exit_code"]), int(meta["seconds"]), int(meta["reads"])
json.dump(meta, open(sys.argv[1], "w"), indent=2)
PY

echo "RUN_DIR=$RUN_DIR"
echo "WORK_DIR=$CWD"
echo "SESSION_ID=$SESSION_ID"
[[ -n "${NAME:-$RESUME}" ]] && echo "SESSION_NAME=${NAME:-$RESUME}"
echo "STATUS=$STATUS"
[[ "${READS:--1}" != -1 ]] && echo "READS=$READS"
[[ -n "$TREE" ]] && echo "TREE=$TREE"
echo "ANSWER=$ANSWER"
case "$STATUS" in
  ok)      exit 0 ;;
  timeout)
    if [[ -s "$ANSWER" ]]; then
      echo "timed out after ${SECS}s; $ANSWER holds only what arrived before the cut; see $ERRLOG" >&2
    else
      CALLS=""
      [[ -s "$RUN_DIR/tools.txt" ]] && CALLS=" It had made $(wc -l < "$RUN_DIR/tools.txt" | tr -d ' ') tool calls; see $RUN_DIR/tools.txt."
      echo "timed out after ${SECS}s with no answer: the turn was cut while the model was still working, and a cut turn returns none of its text.${CALLS} Rerun with a narrower prompt or a longer --timeout; see $ERRLOG" >&2
    fi
    exit 124 ;;
  quota)
    if [[ $RETRIED -eq 1 ]]; then WHY="it ran out again on the one retry"
    elif [[ "$AGY_AUTH" != vertex ]]; then WHY="the API key route is not retried"
    elif [[ ${LEFT:-0} -le 120 ]]; then WHY="too little of the time limit was left to wait and retry"
    else WHY="agy named no conversation to continue"; fi
    HAVE="there is no answer"; [[ -s "$ANSWER" ]] && HAVE="$ANSWER holds what Gemini wrote before that, possibly cut short"
    NOW="Wait a few minutes and rerun; a narrower prompt or a lower --web-budget sends fewer tokens per minute."
    [[ "$AGY_AUTH" == vertex ]] && NOW="To rerun now, set PAIR_AGY_AUTH=key (the Gemini API key has its own quota), or wait a few minutes; a narrower prompt or a lower --web-budget sends fewer tokens per minute."
    echo "the Gemini quota ran out (429 RESOURCE_EXHAUSTED) and $WHY; $HAVE. $NOW See $ERRLOG" >&2
    exit 75 ;;
  auth)
    if [[ "$AGY_AUTH" == vertex ]]; then
      echo "agy could not authenticate to Vertex AI with $AGY_ADC, twice. This skill never uses agy's own login, whatever agy's message says; rerun in a minute, and if it persists check that key or set PAIR_AGY_AUTH=key. See $ERRLOG" >&2
    else
      echo "agy rejected the Gemini API key (authentication failed); check GEMINI_API_KEY or OpenCode's auth.json, or use the Vertex AI route. This skill never uses agy's own login. See $ERRLOG" >&2
    fi
    exit 69 ;;
  unread)
    echo "the model read no file in $RUN_CWD, so its answer rests on your prompt alone; $ANSWER holds it. Usual causes: the prompt said it may not run anything (Codex reads files only through shell commands, so say it may read and run read-only commands), or this ran inside another sandbox (run pair.sh outside your harness's sandbox). If the question needed no file, use the answer as it is." >&2
    exit 72 ;;
  empty)
    if [[ $RETRIED -eq 1 ]]; then
      echo "no answer: the one retry after the Vertex AI quota error ended without one; see $ERRLOG and $EVENTS" >&2
    else
      echo "no answer; see $ERRLOG and $EVENTS" >&2
    fi
    exit 70 ;;
  incomplete) echo "the turn ended without a final step; $ANSWER holds only what arrived" >&2; exit 71 ;;
  denied)  echo "agy ended the turn on a permission it could not ask for; see $RUN_DIR/tools.txt and $ERRLOG" >&2; exit 71 ;;
  *)       echo "the turn failed; see $ERRLOG and $EVENTS" >&2; tail -5 "$ERRLOG" >&2; exit 71 ;;
esac
exit
}
