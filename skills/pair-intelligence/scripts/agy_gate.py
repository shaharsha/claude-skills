#!/usr/bin/env python3
"""PreToolUse hook that decides every tool call of the Gemini engine (agy).

pair.sh runs agy with a private HOME whose hooks.json points here, and passes
this run's policy in PAIR_GATE_POLICY (agy hands its environment to hooks). The
gate is default-deny, because agy's own permission rules cannot express what
pair.sh needs:
  - an Ask in headless mode silently ends the run with an empty answer, while a
    hook's "deny" reaches the model as a tool error and the run continues;
  - search_web, schedule, send_message and the subagent tools have no
    permission action at all.
No policy, an unreadable policy or a crash here all end in a refusal: agy's
settings floor (writes, MCP and URL actuation denied) still holds, and anything
left falls to Ask, which ends the run.

Policy JSON: {"roots": [...], "web": "off|cached|live", "commands": [...], "log": path}
Runs under /usr/bin/python3 -I (3.9 on macOS), so no newer syntax.
"""
import json
import os
import re
import shlex
import sys

# agy runs a command line in zsh (measured: a `*(.)` glob qualifier expanded).
# Outside quotes only these characters pass, so no glob, glob qualifier
# (*(e:'cmd':) runs code), brace, tilde, $, redirection or separator reaches it.
SAFE_BARE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:@,+=%-")
SECRET = re.compile(r"^(\.env(\..+)?|.+\.(pem|key|p12|pfx)|id_(rsa|ed25519|ecdsa|dsa).*|\.netrc|\.npmrc|\.pypirc)$",
                    re.IGNORECASE | re.DOTALL)  # DOTALL: a file name may hold a newline
SECRET_OK = re.compile(r"^\.env\.(example|sample|template|dist)$", re.IGNORECASE)


def shell_plain(line):
    """True if zsh would run this line as one command with every word taken literally.

    Single quotes are fully literal in zsh; inside double quotes only $, backquote,
    backslash and ! do anything, so those are refused there. Bare words use
    SAFE_BARE, and none may start with = (zsh expands =cmd to a path).
    """
    state, word_start = "bare", True
    for c in line:
        if state == "single":
            if c in "\n\r":
                return False
            if c == "'":
                state, word_start = "bare", False
        elif state == "double":
            if c in "$`\\!\n\r":
                return False
            if c == '"':
                state, word_start = "bare", False
        elif c == " ":
            word_start = True
        elif c == "'":
            state = "single"
        elif c == '"':
            state = "double"
        elif c not in SAFE_BARE or (word_start and c == "="):
            return False
        else:
            word_start = False
    return state == "bare"


def secret(path):
    names = {os.path.basename(path), os.path.basename(os.path.realpath(path))}
    return any(SECRET.match(n) and not SECRET_OK.match(n) for n in names if n)


def load_policy():
    path = os.environ.get("PAIR_GATE_POLICY", "")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def main():
    pol = load_policy()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    call = event.get("toolCall") or {}
    name, args = call.get("name", ""), call.get("args") or {}

    def decide(decision, reason=""):
        if pol and pol.get("log"):
            try:
                with open(pol["log"], "a") as f:
                    f.write(json.dumps({"tool": name, "decision": decision, "reason": reason,
                                        "args": {k: str(v)[:300] for k, v in args.items()}}) + "\n")
            except OSError:
                pass
        sys.stdout.write(json.dumps({"decision": decision, "reason": reason}))
        sys.exit(0)

    if not pol:
        decide("deny", "no pair-intelligence policy for this run; every tool is refused")
    roots = [os.path.realpath(r) for r in pol.get("roots", [])]
    web = pol.get("web", "off")
    commands = pol.get("commands", [])
    bindir = pol.get("bin", "")

    def readable(p):
        if not p or not os.path.isabs(p):
            return False
        full = os.path.realpath(p)
        return any(full == r or full.startswith(r + os.sep) for r in roots)

    if name == "run_command":
        line = str(args.get("CommandLine", ""))
        if not shell_plain(line):
            decide("deny", "the shell (zsh) would expand or chain part of that command: use one %s command, "
                   "only letters, digits and _./:@,+=%%- outside quotes, and put patterns or text in single "
                   "quotes" % " or ".join(commands))
        try:
            argv = shlex.split(line)
        except ValueError:
            decide("deny", "the command could not be parsed")
        allowed = set(commands) | {os.path.join(bindir, c) for c in commands if bindir}
        if argv and argv[0] in allowed:
            decide("auto_approve")
        decide("deny", "only these commands run here: %s (run one with no arguments for its usage)"
               % ", ".join(commands) if commands else "no shell commands run here")

    if name in ("read_file", "view_file"):
        p = str(args.get("Path") or args.get("AbsolutePath") or args.get("path") or "")
        if secret(p):
            decide("deny", "secret files (.env, keys) are not readable, under any name or link")
        if readable(p):
            decide("auto_approve")
        decide("deny", "reading is limited to: %s (use absolute paths)" % ", ".join(roots))

    if name == "search_web":
        if web in ("cached", "live"):
            decide("auto_approve")
        decide("deny", "web search is off for this run")
    if name == "read_url_content":
        # pair-fetch is the page reader: it refuses local and private addresses.
        decide("deny", "use `pair-fetch <url>` to read a page" if web == "live" else "reading pages is off for this run")

    decide("deny", "%s is not available in this run" % (name or "this tool"))


if __name__ == "__main__":
    main()
