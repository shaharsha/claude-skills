#!/usr/bin/env bash
# Offline tests for pair.sh and codex_review.sh. Fake codex, opencode and
# agent-browser binaries stand in for the real CLIs, so this spends no model
# quota and opens no browser. Run: bash scripts/test_pair.sh
#
# What it pins down: the sandbox flags on every call (resume included), the
# exit code and STATUS for each way a turn can end, the prompt reaching Gemini
# on stdin rather than argv, browse teardown, and codex_review.sh's non-git and
# --out-dir paths.

set -uo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/pair-test.XXXXXX")" && pwd)"
trap 'rm -rf "$T"' EXIT
FAKE="$T/bin"; LOG="$T/log"; mkdir -p "$FAKE" "$LOG"
PASS=0; FAIL=0

ok()   { PASS=$((PASS + 1)); printf 'ok    %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$1"; [[ -n "${2:-}" ]] && printf '      %s\n' "$2"; }
check() { if eval "$2"; then ok "$1"; else bad "$1" "$2"; fi; }

# --- fakes ------------------------------------------------------------------------
cat > "$FAKE/codex" <<'FAKE'
#!/usr/bin/env python3
import json, os, sys, time
log = os.environ["FAKE_LOG"]
args = sys.argv[1:]
n = len([f for f in os.listdir(log) if f.startswith("codex-args")])
json.dump({"args": args, "cwd": os.getcwd(),
           "env_ab": {k: v for k, v in os.environ.items() if k.startswith("AGENT_BROWSER_")}},
          open(f"{log}/codex-args-{n}.json", "w"))
prompt = sys.stdin.read()
open(f"{log}/codex-stdin-{n}.txt", "w").write(prompt)
out = args[args.index("-o") + 1] if "-o" in args else None
mode = os.environ.get("FAKE_CODEX", "ok")
tid = "11111111-2222-3333-4444-555555555555"
if mode == "hang":
    time.sleep(30)
if "--json" in args:
    print(json.dumps({"type": "thread.started", "thread_id": tid}))
else:
    print(f"session id: {tid}")
if mode == "failed":
    print(json.dumps({"type": "turn.failed", "error": {"message": "boom"}})); sys.exit(1)
if mode == "review" and out:
    json.dump({"scan_notes": "read a.txt", "overall_verdict": "sound", "overall_explanation": "fine",
               "overall_confidence": 0.9, "findings": []}, open(out, "w"))
elif mode == "ok" and out:
    open(out, "w").write("the answer\n")
if "--json" in args:
    print(json.dumps({"type": "turn.completed", "usage": {}}))
FAKE

cat > "$FAKE/opencode-cli" <<'FAKE'
#!/usr/bin/env python3
import json, os, sys
log = os.environ["FAKE_LOG"]
args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("opencode v2.2.5"); sys.exit(0)
n = len([f for f in os.listdir(log) if f.startswith("oc-args")])
json.dump({"args": args, "cwd": os.getcwd(), "config": os.environ.get("OPENCODE_CONFIG_CONTENT", ""),
           "no_claude": os.environ.get("OPENCODE_DISABLE_CLAUDE_CODE", "")},
          open(f"{log}/oc-args-{n}.json", "w"))
open(f"{log}/oc-stdin-{n}.txt", "w").write(sys.stdin.read())
mode = os.environ.get("FAKE_OC", "ok")
sid = "ses_fake123"
ev = lambda **k: print(json.dumps(dict(sessionID=sid, **k)))
ev(type="step_start", part={})
if mode == "error":
    ev(type="error", error={"type": "provider.no-route", "message": "Model unavailable"}); sys.exit(1)
if mode == "partial":
    ev(type="text", part={"text": "Let me read the file first."})
    ev(type="step_finish", part={"reason": "tool-calls"})
    ev(type="step_start", part={})
    sys.exit(143)
ev(type="text", part={"text": "gemini answer"})
ev(type="step_finish", part={"reason": "stop", "tokens": {}})
sys.exit(1 if mode == "tool-error" else 0)
FAKE

cat > "$FAKE/agent-browser" <<FAKE
#!/bin/bash
echo "\$* | sock=\${AGENT_BROWSER_SOCKET_DIR:-} allowed=\${AGENT_BROWSER_ALLOWED_DOMAINS:-} boundaries=\${AGENT_BROWSER_CONTENT_BOUNDARIES:-} shots=\${AGENT_BROWSER_SCREENSHOT_DIR:-} downloads=\${AGENT_BROWSER_DOWNLOAD_PATH:-}" >> "$LOG/ab.log"
case "\$1" in
  open) if [[ ! -e "\$AGENT_BROWSER_SOCKET_DIR/pair.pid" ]]; then /bin/sleep 300 & echo \$! > "\$AGENT_BROWSER_SOCKET_DIR/pair.pid"; echo \$! > "$LOG/ab.pid"; fi ;;
esac
FAKE
chmod +x "$FAKE"/*

export PATH="$FAKE:$PATH" FAKE_LOG="$LOG" PAIR_OUT="$T/out" PAIR_OPENCODE="$FAKE/opencode-cli"
P="$SCRIPTS/pair.sh"
printf 'What is 2+2?\n' > "$T/prompt.md"
last_args() { ls -t "$LOG"/"$1"-args-*.json | head -1; }
jq_py() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print($2)" "$1"; }
reset_log() { rm -f "$LOG"/*; }

# --- pair.sh: codex ---------------------------------------------------------------
mkdir -p "$T/repo" && git -C "$T/repo" init -q
out="$(cd "$T/repo" && FAKE_CODEX=ok bash "$P" --prompt-file "$T/prompt.md" --name s1 2>&1)"; rc=$?
A="$(last_args codex)"
check "codex ok: exit 0 and STATUS=ok"            '[[ $rc -eq 0 && "$out" == *"STATUS=ok"* ]]'
check "codex ok: ANSWER is the last line"         '[[ "$(tail -1 <<<"$out")" == ANSWER=* ]]'
check "codex ok: read-only via -s and -c"         '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"-s read-only"*"sandbox_mode=\"read-only\""* ]]'
check "codex ok: consult uses cached web search"  '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"web_search=\"cached\""* ]]'
check "codex ok: prompt arrives on stdin"         'grep -q "2+2" "$LOG/codex-stdin-0.txt"'
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "codex ok: meta.json is valid JSON"         'python3 -c "import json;json.load(open(\"$RUN/meta.json\"))"'

out="$(FAKE_CODEX=ok bash "$P" --prompt-file "$T/prompt.md" --resume s1 2>&1)"; rc=$?
A="$(last_args codex)"
check "resume: continues the recorded thread"     '[[ "$(jq_py "$A" "\" \".join(d[\"args\"][:3])")" == "exec resume 11111111-2222-3333-4444-555555555555" ]]'
check "resume: re-forces read-only"               '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"sandbox_mode=\"read-only\""* ]]'
check "resume: runs in the original directory"    '[[ "$(jq_py "$A" "d[\"cwd\"]")" == "$(cd "$T/repo" && pwd -P)" || "$(jq_py "$A" "d[\"cwd\"]")" == "$(cd "$T/repo" && pwd)" ]]'

out="$(FAKE_CODEX=failed bash "$P" --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "codex failed turn: exit 71, STATUS=failed" '[[ $rc -eq 71 && "$out" == *"STATUS=failed"* ]]'
out="$(FAKE_CODEX=empty bash "$P" --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "codex empty answer: exit 70"               '[[ $rc -eq 70 && "$out" == *"STATUS=empty"* ]]'
out="$(FAKE_CODEX=hang bash "$P" --prompt-file "$T/prompt.md" --timeout 2 2>&1)"; rc=$?
check "codex hang: exit 124, STATUS=timeout"      '[[ $rc -eq 124 && "$out" == *"STATUS=timeout"* ]]'

out="$(FAKE_CODEX=ok bash "$P" --mode ideate --prompt-file "$T/prompt.md" 2>&1)"
W="$(sed -n 's/^WORK_DIR=//p' <<<"$out")"
check "ideate: scratch dir is outside the runs dir" '[[ -n "$W" && "$W" != "$T/out"* ]]'

printf 'x' > "$T/shot.png"
out="$(FAKE_CODEX=ok bash "$P" --prompt-file "$T/prompt.md" --image "$T/shot.png" 2>&1)"
n=$(( $(ls "$LOG"/codex-stdin-*.txt | wc -l) - 1 ))
check "codex image: path listed in the prompt, no -i flag" 'grep -q "$T/shot.png" "$LOG/codex-stdin-$n.txt" && [[ "$(jq_py "$(last_args codex)" "\"-i\" in d[\"args\"]")" == False ]]'

mkdir -p "$T/we\"ird dir"
out="$(cd "$T/we\"ird dir" && FAKE_CODEX=ok bash "$P" --prompt-file "$T/prompt.md" 2>&1)"
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "meta.json survives a quote in the cwd"     'python3 -c "import json;json.load(open(\"$RUN/meta.json\"))"'

# --- pair.sh: gemini --------------------------------------------------------------
reset_log
out="$(FAKE_OC=ok bash "$P" --engine gemini --prompt-file "$T/prompt.md" --image "$T/shot.png" --name g1 2>&1)"; rc=$?
A="$(last_args oc)"
check "gemini ok: exit 0, answer extracted"       '[[ $rc -eq 0 ]] && grep -q "gemini answer" "$(sed -n "s/^ANSWER=//p" <<<"$out")"'
check "gemini: prompt on stdin, not in argv"      'grep -q "2+2" "$LOG/oc-stdin-0.txt" && ! grep -q "2+2" "$A"'
check "gemini: read-only agent starts deny-all"   '[[ "$(jq_py "$A" "d[\"config\"]")" == *"\"action\":\"*\",\"resource\":\"*\",\"effect\":\"deny\""* ]]'
check "gemini consult: webfetch on"                '[[ "$(jq_py "$A" "d[\"config\"]")" == *"\"action\":\"webfetch\""* ]]'
out="$(FAKE_OC=ok bash "$P" --engine gemini --mode review --prompt-file "$T/prompt.md" 2>&1)"
python3 -c "import json,sys; json.loads(json.load(open(sys.argv[1]))['config'])" "$(last_args oc)" 2>/dev/null
check "gemini review: config valid, webfetch off"  '[[ $? -eq 0 && "$(jq_py "$(last_args oc)" "d[\"config\"]")" != *"webfetch"* ]]'
A="$(ls "$LOG"/oc-args-0.json)"
check "gemini: no shell outside browse"           '[[ "$(jq_py "$A" "d[\"config\"]")" != *"\"shell\""* ]]'
check "gemini: Claude instructions kept out"      '[[ "$(jq_py "$A" "d[\"no_claude\"]")" == 1 ]]'
check "gemini: image attached with -f"            '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"-f $T/shot.png"* ]]'
out="$(FAKE_OC=ok bash "$P" --engine gemini --prompt-file "$T/prompt.md" --resume g1 2>&1)"
check "gemini resume: -s carries the session id"  '[[ "$(jq_py "$(last_args oc)" "\" \".join(d[\"args\"])")" == *"-s ses_fake123"* ]]'
out="$(FAKE_OC=error bash "$P" --engine gemini --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "gemini error event: exit 71"               '[[ $rc -eq 71 ]]'
out="$(FAKE_OC=partial bash "$P" --engine gemini --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "gemini stream cut mid-turn: exit 71, STATUS=incomplete" '[[ $rc -eq 71 && "$out" == *"STATUS=incomplete"* ]]'
out="$(FAKE_OC=ok bash "$P" --engine gemini --mode ideate --prompt-file "$T/prompt.md" --name gi 2>&1)"
out="$(FAKE_OC=ok bash "$P" --prompt-file "$T/prompt.md" --resume gi 2>&1)"; rc=$?
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "resume inherits the session's engine and mode" '[[ $rc -eq 0 && "$(jq_py "$RUN/meta.json" "d[\"engine\"]+\"/\"+d[\"mode\"]")" == gemini/ideate ]]'
bash "$P" --mode consult --prompt-file "$T/prompt.md" --resume gi >/dev/null 2>&1
check "resume refuses a mode change: exit 64" '[[ $? -eq 64 ]]'
out="$(FAKE_OC=tool-error bash "$P" --engine gemini --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "gemini tool error with an answer: exit 0"  '[[ $rc -eq 0 && "$out" == *"STATUS=ok"* ]]'
out="$(FAKE_OC=ok bash "$P" --engine gemini --model google/gemini-3.8-flash --effort low --prompt-file "$T/prompt.md" 2>&1)"
check "gemini: google/ prefix not doubled"        '[[ "$(jq_py "$(last_args oc)" "\" \".join(d[\"args\"])")" == *"-m google/gemini-3.8-flash#low"* ]]'

# --- pair.sh: browse --------------------------------------------------------------
reset_log
mkdir -p "$T/empty"
out="$(FAKE_CODEX=ok bash "$P" --mode browse --domains example.com --cwd "$T/empty" --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
A="$(last_args codex)"
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
WR="$RUN/bin/pair-browser"
SOCK="$(sed -n 's/.*sock=\([^ ]*\).*/\1/p' "$LOG/ab.log" | head -1)"
check "browse: exit 0"                            '[[ $rc -eq 0 ]]'
check "browse: subdomains added to the allow-list" 'grep -q "allowed=example.com,\*.example.com" "$LOG/ab.log"'
check "browse: page text marked untrusted"        'grep -q "boundaries=1" "$LOG/ab.log"'
check "browse: screenshots and downloads pinned to shots" 'grep -q "shots=$T/empty/shots downloads=$T/empty/shots" "$LOG/ab.log"'
check "browse: no browser variables exported to codex" '[[ "$(jq_py "$A" "len(d[\"env_ab\"])")" == 0 ]]'
check "browse: codex gets workspace-write + network" '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"-s workspace-write"*"network_access=true"* ]]'
check "browse: browser closed and killed"         'grep -q "^close" "$LOG/ab.log" && ! kill -0 "$(cat "$LOG/ab.pid")" 2>/dev/null'
check "browse: private socket dir removed"        '[[ -n "$SOCK" && ! -e "$SOCK" ]]'

# The generated wrapper, exercised directly (its socket dir is gone, which the fake ignores).
mkdir -p "$SOCK"
refused_ok=1
while IFS= read -r line; do
  eval "set -- $line"
  if "$WR" "$@" >/dev/null 2>&1; then refused_ok=0; echo "      wrapper allowed: $line"; fi
done <<'CASES'
close
--json close
batch close
connect 9222
upload @e1 /etc/passwd
state save /tmp/s.json
pdf /tmp/x.pdf
open https://example.com --profile Default
open https://example.com --allowed-domains evil.com
open https://example.com -p browserbase
open file:///etc/passwd
get cdp-url
get -i cdp-url
wait --load networkidle
wait -d /tmp/download.bin
screenshot a.png /tmp/outside.png
screenshot ignored.png body /tmp/victim.png
screenshot shot.png --threshold
screenshot --threshold --allowed-domains '' 0
fill @e1 --cdp
snapshot -x
scroll sideways
CASES
check "wrapper refuses non-page commands and escaping arguments" '[[ $refused_ok -eq 1 ]]'
: > "$LOG/ab.log"
AGENT_BROWSER_SOCKET_DIR=/tmp/evil AGENT_BROWSER_ALLOWED_DOMAINS= "$WR" open "https://example.com" >/dev/null 2>&1
check "wrapper ignores the caller's AGENT_BROWSER_* variables" 'grep -q "^open https://example.com | sock=$SOCK allowed=example.com" "$LOG/ab.log"'
printf 'touch "%s/bash_env_ran"\n' "$T" > "$T/evil_env.sh"
BASH_ENV="$T/evil_env.sh" "$WR" snapshot -i >/dev/null 2>&1
check "wrapper does not run an exported BASH_ENV" '[[ ! -e "$T/bash_env_ran" ]]'
"$WR" screenshot ../../../etc/evil.png >/dev/null 2>&1
check "wrapper keeps screenshots in the shots folder" 'grep -q "^screenshot $T/empty/shots/evil.png |" "$LOG/ab.log"'
"$WR" screenshot --full --threshold 0.01 page.png >/dev/null 2>&1
check "wrapper allows screenshot --full --threshold N" 'grep -q "^screenshot --full --threshold 0.01 $T/empty/shots/page.png |" "$LOG/ab.log"'
"$WR" snapshot -i -d 3 >/dev/null 2>&1
check "wrapper allows snapshot -i -d N"            'grep -q "^snapshot -i -d 3 |" "$LOG/ab.log"'
"$WR" fill @e2 "hello world" >/dev/null 2>&1 && "$WR" get attr href @e3 >/dev/null 2>&1 && "$WR" scroll down 300 >/dev/null 2>&1
"$WR" fill @e4 "" >/dev/null 2>&1
check "wrapper allows an empty fill to clear a field" 'grep -q "^fill @e4  |" "$LOG/ab.log"'
check "wrapper allows fill, get attr and scroll"  'grep -q "^fill @e2 hello world |" "$LOG/ab.log" && grep -q "^get attr href @e3 |" "$LOG/ab.log" && grep -q "^scroll down 300 |" "$LOG/ab.log"'
rm -rf "$SOCK"

out="$(FAKE_OC=ok bash "$P" --engine gemini --mode browse --domains example.com --cwd "$T/empty" --prompt-file "$T/prompt.md" 2>&1)"
GRUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
python3 -c "import json,sys; json.loads(json.load(open(sys.argv[1]))['config'])" "$(last_args oc)" 2>/dev/null
check "gemini browse: injected agent config is valid JSON" '[[ $? -eq 0 ]]'
# Emulates OpenCode's documented matching: * spans anything, the whole command must
# match, the last matching rule wins, unmatched means ask (treated as refused here).
POLICY="$T/policy.py"
cat > "$POLICY" <<'PYPOL'
import json, re, sys
rules = json.loads(json.load(open(sys.argv[1]))["config"])["agents"]["pair"]["permissions"]
wrap = sys.argv[2]
def decide(cmd):
    effect = "ask"
    for r in rules:
        if r["action"] not in ("*", "shell"):
            continue
        rx = "^" + ".*".join(re.escape(x) for x in r["resource"].split("*")) + "$"
        if re.match(rx, cmd, re.S):
            effect = r["effect"]
    return effect
allowed = ["pair-browser open https://example.com", "pair-browser snapshot -i",
           f"{wrap} click @e1", "pair-browser screenshot a.png"]
refused = ["agent-browser open https://example.com", "agent-browser --json close",
           "pair-browser get text @e1 > /tmp/out.txt", "pair-browser open $(cat ~/.ssh/id_rsa)",
           "pair-browser open `whoami`", "curl -s https://example.com", "bash -c 'agent-browser close'"]
bad = [c for c in allowed if decide(c) != "allow"] + [c for c in refused if decide(c) == "allow"]
print("\n".join(bad))
sys.exit(1 if bad else 0)
PYPOL
pol="$(python3 "$POLICY" "$(last_args oc)" "$GRUN/bin/pair-browser" 2>&1)"
check "gemini browse: only the wrapper allowed, escapes refused" '[[ -z "$pol" ]]'
[[ -n "$pol" ]] && printf '      misjudged: %s\n' "$pol"

# --- pair.sh: argument checks -----------------------------------------------------
bash "$P" --help >/dev/null 2>&1;                                         check "--help exits 0" '[[ $? -eq 0 ]]'
bash "$P" --prompt-file prompt.md >/dev/null 2>&1;                        check "relative prompt path: exit 64" '[[ $? -eq 64 ]]'
bash "$P" --prompt-file "$T/prompt.md" --effort huge >/dev/null 2>&1;     check "bad effort: exit 64" '[[ $? -eq 64 ]]'
bash "$P" --engine gemini --prompt-file "$T/prompt.md" --schema /x >/dev/null 2>&1; check "gemini --schema: exit 64" '[[ $? -eq 64 ]]'
bash "$P" --mode browse --prompt-file "$T/prompt.md" >/dev/null 2>&1;     check "browse without domains: exit 64" '[[ $? -eq 64 ]]'
bash "$P" --mode browse --domains a.com --cwd "$T/repo" --prompt-file "$T/prompt.md" >/dev/null 2>&1
check "browse inside a git repo: exit 64" '[[ $? -eq 64 ]]'
bash "$P" --mode browse --domains " , " --cwd "$T/empty" --prompt-file "$T/prompt.md" >/dev/null 2>&1
check "browse with no usable domain: exit 64" '[[ $? -eq 64 ]]'
reset_log
FAKE_CODEX=ok bash "$P" --mode browse --domains "https://example.com/docs" --cwd "$T/empty" --prompt-file "$T/prompt.md" --name br >/dev/null 2>&1
check "browse strips scheme and path from a domain" 'grep -q "^open https://example.com | .*allowed=example.com,\*.example.com" "$LOG/ab.log"'
bash "$P" --prompt-file "$T/prompt.md" --resume br >/dev/null 2>&1
check "browse sessions are not resumable: exit 64" '[[ $? -eq 64 ]]'

out="$(cd "$T" && PAIR_OUT=relout FAKE_CODEX=ok bash "$P" --mode ideate --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "relative PAIR_OUT works when the engine runs elsewhere" '[[ $rc -eq 0 && "$out" == *"RUN_DIR=$T/relout/"* ]]'

# --- pair.sh: parallel runs keep every session label -----------------------------
for i in 1 2 3 4 5 6; do (FAKE_CODEX=ok bash "$P" --prompt-file "$T/prompt.md" --name "par$i" >/dev/null 2>&1 &) ; done
for _ in $(seq 1 50); do
  n="$(python3 -c "import json,sys; print(sum(k.startswith('par') for k in json.load(open(sys.argv[1]))))" "$T/out/sessions.json" 2>/dev/null)"
  [[ "$n" == 6 ]] && break; sleep 0.2
done
check "six parallel runs keep all six session labels" '[[ "$n" == 6 ]]'

# --- codex_review.sh --------------------------------------------------------------
mkdir -p "$T/docs" "$T/evidence" && printf 'hello\n' > "$T/docs/a.txt"
out="$(FAKE_CODEX=review bash "$SCRIPTS/codex_review.sh" --repo "$T/docs" --prompt-file "$T/prompt.md" --label t1 --out-dir "$T/evidence" 2>&1)"; rc=$?
MD="$(sed -n 's/^REVIEW_MD=//p' <<<"$out")"
check "codex_review: non-git repo accepted, exit 0" '[[ $rc -eq 0 && -f "$MD" ]]'
check "codex_review: passes --skip-git-repo-check" '[[ "$(jq_py "$(last_args codex)" "\" \".join(d[\"args\"])")" == *"--skip-git-repo-check"* ]]'
check "codex_review: artifacts under --out-dir only" '[[ "$MD" == "$T/evidence/"* && ! -e "$T/docs/.codex-review" ]]'
check "codex_review: provenance says not a git repo" 'grep -q "^tree=not a git repository" "$T"/evidence/*.provenance'
check "codex_review: heading on its own line"     'grep -q "^# Codex review" "$MD"'
check "codex_review: no _tbd_ columns"            '! grep -q "_tbd_" "$MD"'
mkdir -p "$T/fresh"
bash "$SCRIPTS/codex_review.sh" --repo "$T/fresh" --list >/dev/null 2>&1
check "codex_review --list creates nothing"       '[[ ! -e "$T/fresh/.codex-review" ]]'

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[[ $FAIL -eq 0 ]]
