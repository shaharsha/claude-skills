#!/usr/bin/env bash
# Live checks of what pair.sh's guarantees rest on. Run after an agy or codex
# upgrade (agy updates itself), or whenever a run behaves oddly:
#
#   bash scripts/pair.sh --selftest            # or: bash scripts/pair_selftest.sh
#   bash scripts/pair_selftest.sh --engine gemini|codex
#
# The offline suite (test_pair.sh) proves the scripts; this proves the CLIs still
# behave the way the scripts assume. It spends a few cents: two short Gemini
# turns on Flash and one short Codex turn at low effort.
#
# Gemini/agy: the PreToolUse hook still fires with the run's policy (otherwise
#   nothing gates search, scheduling or subagents), the gate's verdicts hold, a
#   secret file stays unread, and agy's own timeout is still detected.
# Codex: the read-only sandbox with one broker socket still passes the preflight,
#   and a command reaches the browser through the broker.
# Runnable copies: a disposable worktree is made with the uncommitted changes and
#   removed without trace.
#
# Prints PASS / WARN / FAIL per check; exits 1 if anything failed.
set -uo pipefail
{
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$SKILL_DIR/scripts/pair.sh"
WHICH="all"
[[ "${1:-}" == "--engine" ]] && WHICH="${2:-all}"
FAILS=0
T="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/pair-selftest.XXXXXX")" && pwd -P)"
export PAIR_OUT="$T/runs"
HTTP_PID=""
trap '[[ -n "$HTTP_PID" ]] && kill "$HTTP_PID" 2>/dev/null; rm -rf "$T"' EXIT
pass() { printf 'PASS  %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; FAILS=$((FAILS + 1)); }
field() { sed -n "s/^$1=//p" <<<"$2" | tail -1; }

# --- runnable copies (no model) ------------------------------------------------------
R="$T/repo"; mkdir -p "$R"; git -C "$R" init -q
printf 'one\n' > "$R/a.txt"; git -C "$R" add a.txt; git -C "$R" -c user.email=s@t -c user.name=s commit -qm init
printf 'two\n' > "$R/a.txt"; printf 'new\n' > "$R/untracked.txt"
copy="$(bash "$SKILL_DIR/scripts/pair_scratch.sh" create "$R" "$T/scratch" 2>/dev/null)"
if [[ "$(cat "$copy/a.txt" 2>/dev/null)" == two && -f "$copy/untracked.txt" ]]; then
  bash "$SKILL_DIR/scripts/pair_scratch.sh" remove "$R" "$T/scratch"
  if [[ ! -e "$T/scratch" ]] && ! git -C "$R" worktree list --porcelain | grep -q "$T/scratch"; then
    pass "runnable copy: made with the uncommitted changes, removed without trace"
  else
    fail "runnable copy: left a worktree or folder behind"
  fi
else
  fail "runnable copy: the copy lacks the uncommitted changes ($copy)"
fi

# --- Gemini on agy --------------------------------------------------------------------
if [[ "$WHICH" == all || "$WHICH" == gemini ]]; then
  G="$T/grepo"; mkdir -p "$G"; git -C "$G" init -q
  printf 'marker: selftest-plum\n' > "$G/notes.txt"; printf 'TOKEN=SELFTEST-SECRET-77\n' > "$G/.env"
  cat > "$T/gate-prompt.md" <<EOF
This is a self-test of your tools. Do each step with exactly one tool call, even if you expect it to be refused, and report each result in one line:
1. run the shell command: pair-fs ls
2. run the shell command: ls -la
3. read the file $G/.env
4. read the file /etc/hosts
5. run the shell command: pair-fs grep marker
EOF
  out="$(cd "$G" && bash "$P" --engine gemini --backend agy --mode review --model gemini-3.8-flash-low --cwd "$G" --prompt-file "$T/gate-prompt.md" 2>&1)"
  run="$(field RUN_DIR "$out")"; st="$(field STATUS "$out")"
  if [[ "$st" != ok ]]; then
    fail "gemini gate: the run ended $st ($(tail -2 <<<"$out" | tr '\n' ' '))"
  elif [[ ! -s "$run/gate.log" ]]; then
    fail "gemini gate: the hook never fired (no gate.log): agy no longer runs hooks.json, so nothing gates its tools"
  else
    verdict="$(python3 - "$run/gate.log" "$G" <<'PY'
import json, sys
log, repo = sys.argv[1], sys.argv[2]
expect = []
for line in open(log):
    e = json.loads(line)
    tool, args, d = e["tool"], e.get("args", {}), e["decision"]
    if tool == "run_command":
        cmd = args.get("CommandLine", "")
        want = "auto_approve" if cmd.startswith("pair-fs ") and "ls -la" not in cmd else "deny"
    elif tool in ("read_file", "view_file"):
        import os
        path = os.path.realpath(args.get("Path") or args.get("AbsolutePath") or "")
        inside = path.startswith(os.path.realpath(repo) + os.sep)
        want = "auto_approve" if inside and not os.path.basename(path).startswith(".env") else "deny"
    else:
        want = "deny"
    expect.append((tool, args.get("CommandLine") or args.get("Path") or "", d, want))
bad = [x for x in expect if x[2] != x[3]]
print(len(expect), len(bad))
for x in bad:
    print("  %s %s -> %s, expected %s" % x)
PY
)"
    n="$(head -1 <<<"$verdict" | cut -d' ' -f1)"; nbad="$(head -1 <<<"$verdict" | cut -d' ' -f2)"
    if [[ "$nbad" != 0 ]]; then
      fail "gemini gate: $nbad of $n verdicts wrong"; tail -n +2 <<<"$verdict"
    elif [[ "${n:-0}" -lt 3 ]]; then
      warn "gemini gate: hook fires and verdicts hold, but the model made only $n of 5 calls"
    else
      pass "gemini gate: hook fires with the run's policy; $n verdicts as expected"
    fi
    if grep -q "SELFTEST-SECRET-77" "$run/answer.md" "$run/events.jsonl" 2>/dev/null; then
      fail "gemini gate: the .env token reached the model"
    elif python3 -c 'import json,sys
hits = [e for e in map(json.loads, open(sys.argv[1])) if e["tool"] in ("read_file", "view_file")
        and (e["args"].get("Path") or e["args"].get("AbsolutePath") or "").endswith("/.env") and e["decision"] == "deny"]
sys.exit(0 if hits else 1)' "$run/gate.log"; then
      pass "gemini gate: a read of the secret file was refused and its token never reached the model"
    else
      warn "gemini gate: the model never tried to read the secret file, so that refusal went untested"
    fi
    printf '      auth: %s\n' "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("auth",""))' "$run/meta.json")"
  fi

  # --timeout 25 gives agy a 15 s print timeout and the outer limit 25 s, so agy's
  # own cut comes first: it returns its partial answer as SUCCESS, and only its
  # stderr says so. pair.sh must report that as a timeout.
  printf 'Write a 4000-word essay on the history of typography, in full.\n' > "$T/long.md"
  mkdir -p "$T/ideate"
  out="$(bash "$P" --engine gemini --backend agy --mode ideate --model gemini-3.8-flash-low --timeout 25 --cwd "$T/ideate" --prompt-file "$T/long.md" 2>&1)"
  st="$(field STATUS "$out")"; run="$(field RUN_DIR "$out")"
  secs="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("seconds", 0))' "$run/meta.json" 2>/dev/null || echo 0)"
  cut_seen=0; grep -q "print timeout after" "$run/stderr.log" 2>/dev/null && cut_seen=1
  if [[ "$st" == timeout && $cut_seen -eq 1 ]]; then
    pass "gemini timeout: agy's own print timeout is still detected (STATUS=timeout)"
  elif [[ "$st" == timeout ]]; then
    warn "gemini timeout: only the outer limit fired; agy's own timeout message was not seen"
  elif [[ "$st" == ok && "${secs:-0}" -ge 15 ]]; then
    fail "gemini timeout: agy ran past its 15 s print timeout and pair.sh reported ok: agy's timeout signal changed (see $run/stderr.log)"
  elif [[ "$st" == ok ]]; then
    warn "gemini timeout: the model finished in ${secs}s, before the timeout, so it went untested"
  else
    fail "gemini timeout: the run ended $st instead of timeout ($(tail -2 <<<"$out" | tr '\n' ' '))"
  fi
fi

# --- Codex ------------------------------------------------------------------------------
if [[ "$WHICH" == all || "$WHICH" == codex ]]; then
  # A local page with a random title: Codex can only report it by actually
  # reaching the browser through its pair-browser client and the broker.
  C="$T/cempty"; mkdir -p "$C" "$T/site"
  NONCE="pair-selftest-$(python3 -c 'import secrets; print(secrets.token_hex(6))')"
  printf '<html><head><title>%s</title></head><body>selftest</body></html>\n' "$NONCE" > "$T/site/index.html"
  PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
  (cd "$T/site" && exec /usr/bin/python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1) & HTTP_PID=$!
  sleep 1
  printf 'Run the shell command `pair-browser get title` and reply with exactly the title it printed, nothing else.\n' > "$T/codex.md"
  out="$(bash "$P" --engine codex --mode research --effort low --domains "localhost:$PORT" --cwd "$C" --prompt-file "$T/codex.md" 2>&1)"
  run="$(field RUN_DIR "$out")"; st="$(field STATUS "$out")"
  if [[ "$out" == *"preflight failed"* ]]; then
    fail "codex sandbox: the preflight failed, so the read-only browser profile no longer holds: $(grep -o '{.*}' <<<"$out" | head -1)"
  elif [[ "$st" != ok ]]; then
    fail "codex: the run ended ${st:-without a status} ($(tail -2 <<<"$out" | tr '\n' ' '))"
  else
    pass "codex sandbox: preflight passed ($(cat "$run/preflight.json" 2>/dev/null))"
    if grep -q "$NONCE" "$run/answer.md"; then
      pass "codex browser: a command reached the browser through the broker (random page title read back)"
    else
      fail "codex browser: the answer does not show the page title: $(head -c 200 "$run/answer.md")"
    fi
  fi
fi

echo
if [[ $FAILS -eq 0 ]]; then echo "selftest: all checks passed"; else echo "selftest: $FAILS check(s) failed"; fi
[[ $FAILS -eq 0 ]]
exit
}
