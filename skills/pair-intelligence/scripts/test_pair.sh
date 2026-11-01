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
import json, os, subprocess, sys, time
log = os.environ["FAKE_LOG"]
args = sys.argv[1:]
if args[:1] == ["sandbox"]:
    # `codex sandbox <profile flags> <cmd...>`: record the flags; FAKE_SANDBOX=run
    # runs the command unsandboxed (so a preflight sees the open network and fails).
    open(f"{log}/codex-sandbox.json", "w").write(json.dumps(args))
    if os.environ.get("FAKE_SANDBOX", "pass") == "run":
        i = args.index("/usr/bin/python3")
        sys.exit(subprocess.run(args[i:]).returncode)
    print(json.dumps({"broker_answers": True, "internet_refused": True, "repo_read_only": True,
                      "browser_socket_unreachable": True}))
    sys.exit(0)
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
if mode == "browse-client":
    r = subprocess.run(["pair-browser", "open", "https://example.com/page"], capture_output=True, text=True)
    open(f"{log}/codex-browse.txt", "w").write(f"rc={r.returncode}\n{r.stdout}{r.stderr}")
    mode = "ok"
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

# A fake agy that does what the real one does with hooks: for each scripted tool
# call (FAKE_AGY_TOOLS, a JSON list of [name, args]) it runs the PreToolUse hook
# from $HOME/.gemini/config/hooks.json, and runs an approved command in a shell.
cat > "$FAKE/agy" <<'FAKE'
#!/usr/bin/env python3
import json, os, subprocess, sys, time
log = os.environ["FAKE_LOG"]
args = sys.argv[1:]
n = len([f for f in os.listdir(log) if f.startswith("agy-args")])
json.dump({"args": args, "cwd": os.getcwd(), "home": os.environ.get("HOME", ""),
           "policy": os.environ.get("PAIR_GATE_POLICY", ""),
           "key": os.environ.get("GEMINI_API_KEY", ""), "adc_auth": os.environ.get("AGY_ADC_AUTH", ""),
           "adc": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
           "location": os.environ.get("GOOGLE_CLOUD_LOCATION", "")}, open(f"{log}/agy-args-{n}.json", "w"))
stdin = sys.stdin.read()
open(f"{log}/agy-stdin-{n}.txt", "w").write(stdin)
mode = os.environ.get("FAKE_AGY", "ok")
if mode == "hang":
    time.sleep(30)
ev = lambda **k: print(json.dumps(k), flush=True)
# Like agy: start every .agents/mcp_config.json server from the workspace up to
# the repository root (measured on agy 1.4.12, even with MCP tools denied).
d = os.getcwd()
while True:
    cfg = os.path.join(d, ".agents", "mcp_config.json")
    if os.path.exists(cfg):
        for srv in json.load(open(cfg)).get("mcpServers", {}).values():
            subprocess.run([srv["command"]] + srv.get("args", []))
    if os.path.exists(os.path.join(d, ".git")) or d == "/":
        break
    d = os.path.dirname(d)
hooks = json.load(open(os.path.join(os.environ["HOME"], ".gemini/config/hooks.json")))
cmd = [h["command"] for v in hooks.values() for m in v.get("PreToolUse", []) for h in m["hooks"]][0]
for name, targs in json.loads(os.environ.get("FAKE_AGY_TOOLS", "[]")):
    p = subprocess.run(["/bin/sh", "-c", cmd], input=json.dumps({"toolCall": {"name": name, "args": targs}}),
                       capture_output=True, text=True)
    d = json.loads(p.stdout or '{"decision": "none"}')
    info = {"parameters": targs}
    if d["decision"] in ("allow", "auto_approve"):
        if name == "run_command":
            r = subprocess.run(["/bin/sh", "-c", targs["CommandLine"]], capture_output=True, text=True)
            info["output"] = r.stdout + r.stderr
        state = "DONE"
    else:
        state, info["error"] = "ERROR", {"message": "tool call denied by pre-tool hook: " + d.get("reason", "")}
    with open(f"{log}/agy-tools-{n}.jsonl", "a") as f:
        f.write(json.dumps({"tool": name, "decision": d["decision"], "output": info.get("output", "")}) + "\n")
    ev(event="step_update", step_update={"step_type": "tool", "tool_name": name, "state": state, "tool_info": info})
if mode == "nores":
    sys.exit(0)
res = {"conversation_id": "conv-fake-1", "status": "SUCCESS", "response": "agy answer", "usage": {}}
if mode == "denied":
    res.update(response="", denied_actions=[{"action": "read_file", "display_name": "ReadFile"}])
if mode == "error":
    res.update(status="ERROR", response="")
if mode == "cut":
    res.update(response="partial essay")
    sys.stderr.write("[agy] print timeout after 590s with turn in progress; returning partial output\n")
ev(event="result", result=res)
FAKE

cat > "$FAKE/agent-browser" <<FAKE
#!/bin/bash
echo "\$* | sock=\${AGENT_BROWSER_SOCKET_DIR:-} allowed=\${AGENT_BROWSER_ALLOWED_DOMAINS:-} boundaries=\${AGENT_BROWSER_CONTENT_BOUNDARIES:-} shots=\${AGENT_BROWSER_SCREENSHOT_DIR:-} downloads=\${AGENT_BROWSER_DOWNLOAD_PATH:-} cwd=\$PWD" >> "$LOG/ab.log"
case "\$1" in
  get) if [[ "\${2:-}" == url && -f "$T/ab-url" ]]; then cat "$T/ab-url"; fi ;;
  click) if [[ -f "$T/ab-url-after-click" ]]; then mv "$T/ab-url-after-click" "$T/ab-url"; fi ;;
  open) if [[ ! -e "\$AGENT_BROWSER_SOCKET_DIR/pair.pid" ]]; then /bin/sleep 300 & echo \$! > "\$AGENT_BROWSER_SOCKET_DIR/pair.pid"; echo \$! > "$LOG/ab.pid"; fi ;;
esac
FAKE
chmod +x "$FAKE"/*

export PATH="$FAKE:$PATH" FAKE_LOG="$LOG" PAIR_OUT="$T/out" PAIR_OPENCODE="$FAKE/opencode-cli"
# The OpenCode sections below predate agy; the agy section passes --backend agy.
export PAIR_GEMINI_BACKEND=opencode PAIR_AGY="$FAKE/agy" PAIR_AGY_HOME="$T/agyhome" GEMINI_API_KEY="fake-key-123"
# Key mode unless a test asks for Vertex: this machine may hold a real agy ADC copy.
export PAIR_AGY_AUTH=key
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
check "codex: user config ignored (MCP, plugins), doc limit kept" '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"--ignore-user-config"*"project_doc_max_bytes=400000"* ]]'
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

# --- pair.sh: gemini on agy -------------------------------------------------------
reset_log
mkdir -p "$T/arepo/.agents" && git -C "$T/arepo" init -q && printf 'marker: plum-7\n' > "$T/arepo/notes.txt"
printf '{"mcpServers":{"x":{"command":"/usr/bin/touch","args":["%s/mcp_ran"]}}}' "$T" > "$T/arepo/.agents/mcp_config.json"
AREPO="$(cd "$T/arepo" && pwd -P)"
TOOLS='[["run_command",{"CommandLine":"pair-fs ls"}],["run_command",{"CommandLine":"ls -la"}],
 ["read_file",{"Path":"'"$AREPO"'/notes.txt"}],["read_file",{"Path":"/etc/hosts"}],
 ["search_web",{"query":"q"}],["read_url_content",{"Url":"https://example.com"}],
 ["schedule",{"DurationSeconds":60,"Prompt":"hi"}],["run_command",{"CommandLine":"pair-fs ls; id"}]]'
out="$(cd "$T/arepo" && FAKE_AGY=ok FAKE_AGY_TOOLS="$TOOLS" bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" --name a1 2>&1)"; rc=$?
A="$(last_args agy)"; RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
dec() { python3 -c "import json,sys; print(' '.join(json.loads(l)['decision'] for l in open(sys.argv[1])))" "$LOG/agy-tools-0.jsonl"; }
check "agy ok: exit 0, answer and conversation id"  '[[ $rc -eq 0 && "$out" == *"SESSION_ID=conv-fake-1"* ]] && grep -q "agy answer" "$RUN/answer.md"'
check "agy: workspace is a scratch dir, not the repo" '[[ "$(jq_py "$A" "d[\"cwd\"]")" != "$AREPO"* && "$(jq_py "$A" "d[\"cwd\"]")" == *pair-agy.* ]]'
check "agy: scratch workspace removed after the run" '[[ ! -e "$(jq_py "$A" "d[\"cwd\"]")" ]]'
mcp_after_run=0; [[ -e "$T/mcp_ran" ]] && mcp_after_run=1
(cd "$AREPO" && HOME="$T/agyhome" FAKE_AGY=ok "$FAKE/agy" < /dev/null >/dev/null 2>&1)
mcp_control=0; [[ -e "$T/mcp_ran" ]] && mcp_control=1; rm -f "$T/mcp_ran"
check "agy: the repo's .agents MCP server never starts (control: the fake starts it from inside the repo)" '[[ $mcp_after_run -eq 0 && $mcp_control -eq 1 ]]'
check "agy: private HOME with the gate as its hook"  '[[ "$(jq_py "$A" "d[\"home\"]")" == "$T/agyhome" ]] && grep -q "agy_gate.py" "$T/agyhome/.gemini/config/hooks.json"'
check "agy: key in the environment, not argv"      '[[ "$(jq_py "$A" "d[\"key\"]")" == fake-key-123 && "$(jq_py "$A" "\" \".join(d[\"args\"])")" != *fake-key-123* ]]'
check "agy: prompt on stdin with the harness block" 'grep -q "2+2" "$LOG/agy-stdin-0.txt" && grep -q "pair-fs" "$LOG/agy-stdin-0.txt" && [[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" != *"2+2"* ]]'
check "agy: consult model id carries the effort"   '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"--model gemini-4-argon-high"* ]]'
check "agy: settings floor denies writes, MCP, URL actions" '[[ "$(cat "$(jq_py "$A" "d[\"args\"][d[\"args\"].index(\"--settings\")+1]")")" == *"write_file(*)"*"execute_url(*)"*"read_url(*)"*"mcp(*)"* ]]'
check "agy gate (consult): wrapper yes, ls no, repo read yes, /etc no, search yes, fetch no, schedule no, chain no" \
  '[[ "$(dec)" == "auto_approve deny auto_approve deny auto_approve deny deny deny" ]]'
check "agy: pair-fs ran inside the repo"           'grep -q "notes.txt" "$LOG/agy-tools-0.jsonl"'
check "agy: tools.txt lists each call and refusal" 'grep -q "^DONE  read_file" "$RUN/tools.txt" && grep -q "^ERROR schedule" "$RUN/tools.txt"'
check "agy: gate decisions logged in the run dir"  '[[ $(wc -l < "$RUN/gate.log") -eq 8 ]]'
out="$(cd "$T/arepo" && FAKE_AGY=ok bash "$P" --engine gemini --prompt-file "$T/prompt.md" --resume a1 2>&1)"; rc=$?
check "agy resume: --conversation, backend inherited" '[[ $rc -eq 0 && "$(jq_py "$(last_args agy)" "\" \".join(d[\"args\"])")" == *"--conversation conv-fake-1"* ]]'
out="$(cd "$T/arepo" && FAKE_AGY=ok bash "$P" --engine gemini --backend opencode --prompt-file "$T/prompt.md" --resume a1 2>&1)"; rc=$?
check "agy resume refuses another backend: exit 64" '[[ $rc -eq 64 ]]'
reset_log
out="$(cd "$T/arepo" && FAKE_AGY=ok FAKE_AGY_TOOLS='[["search_web",{"query":"q"}]]' bash "$P" --engine gemini --backend agy --mode review --prompt-file "$T/prompt.md" 2>&1)"
check "agy review: web search refused"             '[[ "$(dec)" == deny ]]'
reset_log
out="$(FAKE_AGY=ok FAKE_AGY_TOOLS='[["read_url_content",{"Url":"https://example.com"}]]' bash "$P" --engine gemini --backend agy --mode research --prompt-file "$T/prompt.md" 2>&1)"
check "agy research: read_url_content refused (pair-fetch is the reader)" '[[ "$(dec)" == deny ]]'
out="$(cd "$T/arepo" && FAKE_AGY=ok bash "$P" --engine gemini --backend agy --model gemini-3.8-flash-low --prompt-file "$T/prompt.md" 2>&1)"
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "agy: a model id with an effort is kept as is" '[[ "$(jq_py "$(last_args agy)" "\" \".join(d[\"args\"])")" == *"--model gemini-3.8-flash-low "* && "$(jq_py "$RUN/meta.json" "d[\"effort\"]")" == low ]]'
out="$(cd "$T/arepo" && FAKE_AGY=denied bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "agy soft-denied run (SUCCESS, empty): exit 71, STATUS=denied" '[[ $rc -eq 71 && "$out" == *"STATUS=denied"* ]]'
out="$(cd "$T/arepo" && FAKE_AGY=error bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "agy error result: exit 71"                  '[[ $rc -eq 71 && "$out" == *"STATUS=failed"* ]]'
out="$(cd "$T/arepo" && FAKE_AGY=nores bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "agy stream without a result: not ok"        '[[ $rc -ne 0 && "$out" != *"STATUS=ok"* ]]'
out="$(cd "$T/arepo" && FAKE_AGY=hang bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" --timeout 2 2>&1)"; rc=$?
check "agy hang: exit 124"                         '[[ $rc -eq 124 ]]'
bash "$P" --engine gemini --backend agy --cwd "$HOME" --prompt-file "$T/prompt.md" >/dev/null 2>&1
check "agy refuses the home directory as --cwd: exit 64" '[[ $? -eq 64 ]]'
(unset GEMINI_API_KEY; HOME="$T/nohome" bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" >/dev/null 2>&1)
check "agy without an API key: exit 69"            '[[ $? -eq 69 ]]'
bash "$P" --backend agy --prompt-file "$T/prompt.md" >/dev/null 2>&1
check "--backend with codex: exit 64"              '[[ $? -eq 64 ]]'
# Vertex AI route: picked automatically when one adc-agy-*.json copy exists.
mkdir -p "$T/vhome/.config/gcloud"
printf '{"type":"authorized_user","quota_project_id":"proj-x"}' > "$T/vhome/.config/gcloud/adc-agy-proj-x.json"
out="$(cd "$T/arepo" && HOME="$T/vhome" PAIR_AGY_AUTH=auto FAKE_AGY=ok bash "$P" --engine gemini --backend agy --cwd "$T/arepo" --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
A="$(last_args agy)"; RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "vertex auto: ADC copy found, no API key passed" '[[ $rc -eq 0 && "$(jq_py "$A" "d[\"adc_auth\"]+\" \"+d[\"location\"]")" == "true global" && "$(jq_py "$A" "d[\"adc\"]")" == *adc-agy-proj-x.json && -z "$(jq_py "$A" "d[\"key\"]")" ]]'
check "vertex: settings carry no modelProvider (it would switch to key mode)" '! grep -q modelProvider "$(jq_py "$A" "d[\"args\"][d[\"args\"].index(\"--settings\")+1]")"'
check "vertex: meta.json names the billed project" '[[ "$(jq_py "$RUN/meta.json" "d[\"auth\"]")" == vertex:proj-x ]]'
out="$(cd "$T/arepo" && HOME="$T/vhome" PAIR_AGY_AUTH=key FAKE_AGY=ok bash "$P" --engine gemini --backend agy --cwd "$T/arepo" --prompt-file "$T/prompt.md" 2>&1)"
check "PAIR_AGY_AUTH=key wins over an ADC copy" '[[ "$(jq_py "$(last_args agy)" "d[\"key\"]")" == fake-key-123 && -z "$(jq_py "$(last_args agy)" "d[\"adc_auth\"]")" ]]'
(cd "$T/arepo" && PAIR_AGY_AUTH=vertex PAIR_AGY_ADC="$T/none.json" bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" >/dev/null 2>&1)
check "PAIR_AGY_AUTH=vertex without an ADC copy: exit 69" '[[ $? -eq 69 ]]'
cp "$T/vhome/.config/gcloud/adc-agy-proj-x.json" "$T/application_default_credentials.json"
(cd "$T/arepo" && PAIR_AGY_AUTH=vertex PAIR_AGY_ADC="$T/application_default_credentials.json" bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" >/dev/null 2>&1)
check "the main ADC file is refused: exit 64"      '[[ $? -eq 64 ]]'
printf '{"type":"authorized_user"}' > "$T/adc-noproj.json"
(cd "$T/arepo" && PAIR_AGY_AUTH=vertex PAIR_AGY_ADC="$T/adc-noproj.json" bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" >/dev/null 2>&1)
check "an ADC copy without quota_project_id: exit 69" '[[ $? -eq 69 ]]'

python3 - "$T/out/sessions.json" <<'PYS'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["legacy"] = {"session_id": "ses_old", "engine": "gemini", "mode": "consult", "cwd": "/tmp"}
json.dump(d, open(p, "w"))
PYS
reset_log
out="$(PAIR_GEMINI_BACKEND= FAKE_OC=ok bash "$P" --prompt-file "$T/prompt.md" --resume legacy 2>&1)"; rc=$?
check "a Gemini session recorded before agy resumes on OpenCode" '[[ $rc -eq 0 && "$(jq_py "$(last_args oc)" "\" \".join(d[\"args\"])")" == *"-s ses_old"* ]]'
out="$(cd "$T/arepo" && FAKE_AGY=cut bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "agy's own print timeout (partial answer, SUCCESS): exit 124, STATUS=timeout" '[[ $rc -eq 124 && "$out" == *"STATUS=timeout"* ]]'

# --- pair_fs.py and agy_gate.py, directly -------------------------------------------
FS() { PAIR_FS_ROOTS="[\"$AREPO\"]" /usr/bin/python3 -I "$SCRIPTS/pair_fs.py" "$@"; }
printf 'SECRET123\n' > "$AREPO/.env"; ln -s /etc "$AREPO/etclink"; printf 'a\n' > "$AREPO/a.txt"
git -C "$AREPO" add a.txt notes.txt >/dev/null && git -C "$AREPO" -c user.email=t@t -c user.name=t commit -qm init
check "pair-fs ls and find inside the root"        'FS ls | grep -q notes.txt && FS find "*.txt" | grep -q a.txt'
check "pair-fs grep finds content"                 'FS grep plum | grep -q "notes.txt:1:marker: plum-7"'
check "pair-fs refuses a path outside the roots"   '! FS ls /etc >/dev/null 2>&1 && ! FS grep root /etc/passwd >/dev/null 2>&1 && ! FS ls ../.. >/dev/null 2>&1'
check "pair-fs refuses a symlink out of the root"  '! FS ls etclink >/dev/null 2>&1 && ! FS grep root etclink >/dev/null 2>&1'
check "pair-fs grep skips secret files"            '[[ "$(FS grep SECRET123)" == "no matches" ]]'
FS grep --pre=/bin/sh x >/dev/null 2>&1; r1=$?; FS grep -- -x >/dev/null 2>&1; r2=$?
check "pair-fs grep refuses unknown flags, takes a dash pattern after --" '[[ $r1 -eq 2 && $r2 -eq 0 ]]'
check "pair-fs git log and show work"              'FS git log --oneline | grep -q init && FS git show HEAD:a.txt | grep -q "^a$"'
git -C "$AREPO" config core.fsmonitor "touch $T/fsmonitor_ran"
git -C "$AREPO" config core.pager "touch $T/pager_ran"
FS git status >/dev/null 2>&1; r1=$?; FS git diff >/dev/null 2>&1
check "pair-fs git refuses a repo whose config names a program, and runs none" '[[ $r1 -eq 2 && ! -e "$T/fsmonitor_ran" && ! -e "$T/pager_ran" ]]'
git -C "$AREPO" config --unset core.fsmonitor; git -C "$AREPO" config --unset core.pager
git -C "$AREPO" config gpg.program "touch $T/gpg_ran"
check "pair-fs git refuses gpg.program in repo config" '! FS git log --oneline >/dev/null 2>&1 && [[ ! -e "$T/gpg_ran" ]]'
git -C "$AREPO" config --unset gpg.program
check "pair-fs git refuses a repo wider than its roots" '! PAIR_FS_ROOTS="[\"$AREPO/many\"]" /usr/bin/python3 -I "$SCRIPTS/pair_fs.py" git log --oneline >/dev/null 2>&1'
git -C "$AREPO" add -f .env >/dev/null 2>&1; git -C "$AREPO" -c user.email=t@t -c user.name=t commit -qm "track env" >/dev/null 2>&1
check "pair-fs never prints a secret: grep path, symlink, case, rev:path, patches" '! FS grep SECRET .env >/dev/null 2>&1 && ln -sf .env "$AREPO/innocent.txt" && ! FS grep SECRET innocent.txt >/dev/null 2>&1 && ! FS git show HEAD:.env >/dev/null 2>&1 && ! FS git show HEAD | grep -q SECRET123 && ! FS git log -p | grep -q SECRET123'
check "pair-fs refuses signature placeholders"     '! FS git log "--format=%G?" >/dev/null 2>&1'
check "pair-fs git refuses --output and no-index paths" '! FS git log --output=/tmp/pair-x >/dev/null 2>&1 && ! FS git diff /etc/hosts /etc/passwd >/dev/null 2>&1 && ! FS git diff -- /etc/hosts >/dev/null 2>&1'
mkdir -p "$AREPO/many" && (cd "$AREPO/many" && for i in $(seq 1 450); do : > "f$i.txt"; done)
check "pair-fs caps long output"                   'FS find "*.txt" many | grep -q "output cut"'
# G <policy> <tool> <key> <value>: the gate's decision for one call.
G() { python3 -c 'import json,sys; print(json.dumps({"toolCall": {"name": sys.argv[1], "args": {sys.argv[2]: sys.argv[3]}}}))' "$2" "$3" "$4" \
        | PAIR_GATE_POLICY="$1" /usr/bin/python3 -I "$SCRIPTS/agy_gate.py" | python3 -c 'import json,sys; print(json.load(sys.stdin)["decision"])'; }
printf '{"roots":["%s"],"web":"off","commands":["pair-fs"],"bin":"/x/bin"}' "$AREPO" > "$T/pol.json"
check "gate: no policy refuses everything"         '[[ "$(G /nonexistent read_file Path "$AREPO/a.txt")" == deny ]]'
check "gate: wrapper by absolute path is allowed"  '[[ "$(G "$T/pol.json" run_command CommandLine "/x/bin/pair-fs ls")" == auto_approve ]]'
check "gate: a lookalike command is refused"       '[[ "$(G "$T/pol.json" run_command CommandLine "pair-fsx ls")" == deny && "$(G "$T/pol.json" run_command CommandLine "env pair-fs ls")" == deny ]]'
check "gate: \$, backslash and newline refused"    '[[ "$(G "$T/pol.json" run_command CommandLine "pair-fs grep \$HOME")" == deny && "$(G "$T/pol.json" run_command CommandLine "pair-fs ls \\")" == deny && "$(G "$T/pol.json" run_command CommandLine "pair-fs ls
id")" == deny ]]'
check "gate: .env inside the root refused"         '[[ "$(G "$T/pol.json" read_file Path "$AREPO/.env")" == deny ]]'
check "gate: zsh glob qualifier, glob, brace, tilde, =cmd refused" '[[ "$(G "$T/pol.json" run_command CommandLine "pair-fs ls /tmp/x*(e:'"'"'touch y'"'"':)")" == deny && "$(G "$T/pol.json" run_command CommandLine "pair-fs ls /*")" == deny && "$(G "$T/pol.json" run_command CommandLine "pair-fs ls {a,b}")" == deny && "$(G "$T/pol.json" run_command CommandLine "pair-fs ls ~")" == deny && "$(G "$T/pol.json" run_command CommandLine "pair-fs ls =ls")" == deny ]]'
check "gate: a quoted regex passes"                '[[ "$(G "$T/pol.json" run_command CommandLine "pair-fs grep '"'"'def (.*)\$'"'"' .")" == auto_approve && "$(G "$T/pol.json" run_command CommandLine "pair-fs grep \"a (b) [c]*\" .")" == auto_approve ]]'
check "gate: a link to .env and .ENV refused"      '[[ "$(G "$T/pol.json" read_file Path "$AREPO/innocent.txt")" == deny && "$(G "$T/pol.json" read_file Path "$AREPO/.ENV")" == deny ]]'
check "gate: read through a symlink out of the root refused" '[[ "$(G "$T/pol.json" read_file Path "$AREPO/etclink/hosts")" == deny ]]'
check "gate: relative read paths refused"          '[[ "$(G "$T/pol.json" read_file Path "notes.txt")" == deny ]]'
check "gate: unknown tools refused"                '[[ "$(G "$T/pol.json" invoke_subagent Prompt x)" == deny ]]'

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
check "browse: browser host runs from the empty socket dir" 'grep -Eq "^open https://example.com \| .* cwd=(/private)?$SOCK$" "$LOG/ab.log"'

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

# --- pair.sh: a live browser in review and consult ---------------------------------
reset_log
out="$(cd "$T/repo" && FAKE_CODEX=browse-client bash "$P" --mode review --domains example.com --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
A="$(last_args codex)"; RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "codex review + domains: exit 0"             '[[ $rc -eq 0 ]]'
check "codex review + domains: broker profile, no -s" '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"default_permissions=\"pair_browse\""*"network_proxy"* && "$(jq_py "$A" "\" \".join(d[\"args\"])")" != *" -s "* ]]'
check "codex review + domains: only the broker socket allowed" '[[ "$(jq_py "$A" "\" \".join(d[\"args\"])")" == *"unix_sockets={\""*"/broker.sock\"=\"allow\"}"* ]]'
check "codex review + domains: preflight ran in the same profile" 'grep -q "pair_browse" "$LOG/codex-sandbox.json" && grep -q preflight.py "$LOG/codex-sandbox.json"'
check "codex review + domains: model's pair-browser reaches the browser via the broker" 'grep -q "^rc=0" "$LOG/codex-browse.txt" && grep -q "^open https://example.com/page | " "$LOG/ab.log"'
check "codex review + domains: screenshots go to the run dir, not the repo" 'grep -q "shots=$RUN/shots " "$LOG/ab.log" && [[ ! -e "$T/repo/shots" ]]'
check "codex review + domains: real wrapper kept off the model's PATH" '[[ -x "$RUN/host/pair-browser-host" && "$(head -2 "$RUN/bin/pair-browser")" == *python3* ]]'
reset_log
out="$(cd "$T/repo" && FAKE_SANDBOX=run FAKE_CODEX=ok bash "$P" --mode consult --domains example.com --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
check "failed preflight: exit 71 and Codex never starts" '[[ $rc -eq 71 && "$out" == *"preflight failed"* ]] && ! ls "$LOG"/codex-args-*.json >/dev/null 2>&1'
bash "$P" --mode review --domains localhost --cwd "$T/repo" --prompt-file "$T/prompt.md" >/dev/null 2>&1
check "a local host without a port: exit 64"       '[[ $? -eq 64 ]]'
(cd "$T/repo" && PAIR_OUT="$T/repo/.runs" bash "$P" --mode review --domains example.com --prompt-file "$T/prompt.md" >/dev/null 2>&1)
check "screenshots inside a git repository: exit 64" '[[ $? -eq 64 ]]'
reset_log
out="$(FAKE_CODEX=ok bash "$P" --mode browse --domains localhost:5173,example.com --cwd "$T/empty" --prompt-file "$T/prompt.md" 2>&1)"
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"; WR="$RUN/bin/pair-browser"
SOCK="$(sed -n 's/.*sock=\([^ ]*\).*/\1/p' "$LOG/ab.log" | head -1)"; mkdir -p "$SOCK"
check "local host: allow-list gets the bare host, start page keeps the port" 'grep -q "^open http://localhost:5173 | .*allowed=localhost,example.com,\*.example.com" "$LOG/ab.log"'
"$WR" open http://localhost:5173/app >/dev/null 2>&1; r1=$?
"$WR" open http://localhost:9222/json >/dev/null 2>&1; r2=$?
"$WR" eval "1+1" >/dev/null 2>&1; r3=$?
check "local host: pinned port opens, another port and eval refused" '[[ $r1 -eq 0 && $r2 -eq 2 && $r3 -eq 2 ]]'
printf 'http://localhost:5173/app\n' > "$T/ab-url"; printf 'http://localhost:6000/\n' > "$T/ab-url-after-click"
r4o="$("$WR" click @e1 2>&1)"; r4=$?
check "local host: a click that lands on another port: output withheld, page sent back, exit 3" '[[ $r4 -eq 3 && "$r4o" == *withheld* ]] && grep -q "^back |" "$LOG/ab.log"'
: > "$LOG/ab.log"; printf 'http://LOCALHOST:6000/\n' > "$T/ab-url"
"$WR" get text body >/dev/null 2>&1; r5=$?
check "local host: nothing reads a page left on an unpinned port" '[[ $r5 -eq 2 ]] && ! grep -q "^get text" "$LOG/ab.log" && grep -q "^back |" "$LOG/ab.log"'
rm -f "$T/ab-url"
r6=0; for u in http://LOCALHOST:9222/ http://localhost.:9222/ http://127.1:9222/ http://2130706433:9222/ 'http://localhost:9222\@localhost:5173/' http://u@localhost:5173/ 'http://[::1]:5173/'; do
  "$WR" open "$u" >/dev/null 2>&1 && { r6=1; echo "      wrapper opened: $u"; }; done
"$WR" read http://localhost:5173/x >/dev/null 2>&1; r7=$?
check "local host: other spellings of loopback, backslash and userinfo URLs refused" '[[ $r6 -eq 0 ]]'
check "local host: read <url> refused (it follows redirects past the pin)" '[[ $r7 -eq 2 ]]'
rm -f "$T/ab-url"; rm -rf "$SOCK"
grep -q "eval" "$RUN/prompt.md"
check "local host: the harness does not offer eval" '[[ $? -ne 0 ]]'
reset_log
out="$(cd "$T/arepo" && FAKE_AGY=ok FAKE_AGY_TOOLS='[["run_command",{"CommandLine":"pair-browser snapshot -i"}],["run_command",{"CommandLine":"pair-fs ls"}]]' bash "$P" --engine gemini --backend agy --domains example.com --prompt-file "$T/prompt.md" 2>&1)"; rc=$?
RUN="$(sed -n 's/^RUN_DIR=//p' <<<"$out")"
check "agy consult + domains: browser and pair-fs both allowed" '[[ $rc -eq 0 && "$(dec)" == "auto_approve auto_approve" ]] && grep -q "^snapshot -i |" "$LOG/ab.log"'
check "agy consult + domains: may read its screenshots in the run dir" 'grep -q "$RUN/shots" "$RUN/agy-policy.json"'
bash "$P" --engine gemini --backend opencode --domains example.com --cwd "$T/arepo" --prompt-file "$T/prompt.md" >/dev/null 2>&1
check "opencode + domains outside browse: exit 64"  '[[ $? -eq 64 ]]'
reset_log
out="$(FAKE_AGY=ok FAKE_AGY_TOOLS='[["run_command",{"CommandLine":"pair-fetch https://example.com"}]]' bash "$P" --engine gemini --backend agy --mode research --prompt-file "$T/prompt.md" 2>&1)"
check "agy research: pair-fetch offered and allowed" '[[ "$(dec)" == auto_approve ]] && grep -q "pair-fetch <url>" "$LOG/agy-stdin-0.txt"'
reset_log
out="$(cd "$T/arepo" && FAKE_AGY=ok FAKE_AGY_TOOLS='[["run_command",{"CommandLine":"pair-fetch https://example.com"}]]' bash "$P" --engine gemini --backend agy --prompt-file "$T/prompt.md" 2>&1)"
check "agy consult (search only): pair-fetch refused" '[[ "$(dec)" == deny ]]'

# --- broker and pair-fetch, directly ------------------------------------------------
BS="$(mktemp -d /tmp/pbt.XXXX)"
printf '#!/bin/bash\necho "wrapped: $*"\n' > "$BS/wrap"; chmod +x "$BS/wrap"
python3 -I "$SCRIPTS/pair_broker.py" "$BS/b.sock" "$BS/wrap" "$BS" & BPID=$!
for _ in $(seq 1 50); do [[ -S "$BS/b.sock" ]] && break; sleep 0.1; done
breq() { python3 -c 'import json,socket,sys
c=socket.socket(socket.AF_UNIX); c.connect(sys.argv[1]); c.sendall(sys.argv[2].encode()+b"\n"); d=b""
while True:
    b=c.recv(65536)
    if not b: break
    d+=b
print(json.loads(d)["rc"], json.loads(d)["out"].strip())' "$BS/b.sock" "$1"; }
check "broker runs the wrapper with the model's arguments" '[[ "$(breq "{\"argv\": [\"get\", \"url\"]}")" == "0 wrapped: get url" ]]'
check "broker refuses malformed requests and keeps serving" '[[ "$(breq "{\"argv\": \"get url\"}")" == 2* && "$(breq "not json")" == 2* && "$(breq "[]")" == 2* && "$(breq "null")" == 2* && "$(breq "{\"argv\": [\"x\"]}")" == "0 wrapped: x" ]]'
check "broker socket is private to this user"      '[[ "$(stat -f %Lp "$BS/b.sock")" == 600 ]]'
mkdir -p "$BS/empty"
pf="$(/usr/bin/python3 -I "$SCRIPTS/pair_preflight.py" "$BS/b.sock" "$BS/empty" "$BS" 2>/dev/null)"
check "preflight: no browser socket to test is a failure" '[[ "$pf" == *"\"browser_socket_unreachable\": false"* ]]'
python3 -c 'import socket,sys,time; s=socket.socket(socket.AF_UNIX); s.bind(sys.argv[1]); s.listen(1); time.sleep(20)' "$BS/pair.sock" & LPID=$!
for _ in $(seq 1 30); do [[ -S "$BS/pair.sock" ]] && break; sleep 0.1; done
pf="$(/usr/bin/python3 -I "$SCRIPTS/pair_preflight.py" "$BS/b.sock" "$BS" "$BS" 2>/dev/null)"
check "preflight: a connectable browser socket counts as reachable" '[[ "$pf" == *"\"browser_socket_unreachable\": false"* ]]'
kill $LPID $BPID 2>/dev/null; rm -rf "$BS"
PF() { /usr/bin/python3 -I "$SCRIPTS/pair_fetch.py" "$@" >/dev/null 2>&1; }
check "pair-fetch refuses local, private and metadata hosts" '! PF http://localhost:8080/ && ! PF http://127.0.0.1/ && ! PF http://10.0.0.1/ && ! PF http://169.254.169.254/latest/meta-data/ && ! PF "http://[::1]/"'
check "pair-fetch refuses other schemes and credentials" '! PF file:///etc/passwd && ! PF ftp://example.com/ && ! PF https://user:pw@example.com/ && ! PF --max-chars'

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
check "codex_review: ignores the user config"     '[[ "$(jq_py "$(last_args codex)" "\" \".join(d[\"args\"])")" == *"--ignore-user-config"*"project_doc_max_bytes=400000"* ]]'
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
