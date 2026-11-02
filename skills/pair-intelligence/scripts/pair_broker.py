#!/usr/bin/env python3
"""Browser broker: the only door from a sandboxed Codex to the browser.

A Codex review or consult with --domains keeps Codex read-only, with its network
cut off by the sandbox's proxy except for one unix socket: this broker's. Codex
cannot be given agent-browser's own socket, because anything that talks to that
socket can restart the browser with no domain allow-list (measured: a client
with different settings makes the daemon relaunch Chrome its way). So pair.sh
starts this broker outside the sandbox; the model's `pair-browser` is a thin
client that sends its arguments here, and the broker runs the generated
grammar wrapper (pair-browser-host), which pins every browser setting.

usage: pair_broker.py <socket path> <wrapper> <workdir>
Limits: one command at a time, 90 s each, 300 per run, 50k characters of output.
"""
import json
import os
import socket
import subprocess
import sys

MAX_COMMANDS = 300
MAX_OUT = 50000
MAX_ERR = 8000
TIMEOUT = 90


def main():
    sock_path, wrapper, workdir = sys.argv[1:4]
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old = os.umask(0o177)
    srv.bind(sock_path)
    os.umask(old)
    srv.listen(4)
    count = 0
    while True:
        conn, _ = srv.accept()
        with conn:
            conn.settimeout(10)
            data = b""
            try:
                while not data.endswith(b"\n") and len(data) < 65536:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                req = json.loads(data.decode("utf-8"))
                argv = req.get("argv") if isinstance(req, dict) else None
                if not (isinstance(argv, list) and len(argv) <= 40
                        and all(isinstance(a, str) and "\0" not in a for a in argv)):
                    raise ValueError("expected {\"argv\": [strings]}")
            except Exception as e:  # any malformed request: answer it, never die
                reply = {"rc": 2, "out": "", "err": "pair-browser: bad request (%s)\n" % e}
            else:
                count += 1
                if count > MAX_COMMANDS:
                    reply = {"rc": 2, "out": "", "err": "pair-browser: this run's %d browser commands are used up\n" % MAX_COMMANDS}
                else:
                    try:
                        p = subprocess.run([wrapper] + argv, cwd=workdir, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT,
                                           env={"PATH": "/usr/bin:/bin"})
                        out = p.stdout.decode("utf-8", "replace")
                        err = p.stderr.decode("utf-8", "replace")
                        if len(out) > MAX_OUT:
                            out = out[:MAX_OUT] + "\n[pair-browser: output cut at %d characters]\n" % MAX_OUT
                        reply = {"rc": p.returncode, "out": out, "err": err[:MAX_ERR]}
                    except subprocess.TimeoutExpired:
                        reply = {"rc": 124, "out": "", "err": "pair-browser: the command took over %ds\n" % TIMEOUT}
                    except (OSError, ValueError) as e:
                        reply = {"rc": 2, "out": "", "err": "pair-browser: the wrapper did not run (%s)\n" % e}
            try:
                conn.sendall((json.dumps(reply) + "\n").encode("utf-8"))
            except OSError:
                pass


if __name__ == "__main__":
    main()
