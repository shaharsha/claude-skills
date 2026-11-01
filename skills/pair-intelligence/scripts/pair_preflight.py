#!/usr/bin/env python3
"""Run inside Codex's sandbox before a review or consult with a live browser.

pair.sh runs this with `codex sandbox` and the same permission profile Codex
will get. Codex starts only if all four hold: the broker answers, the internet
is refused, the repository cannot be written, and agent-browser's own socket is
out of reach. network_proxy is an experimental Codex feature, so this is
checked every run rather than trusted.

usage: pair_preflight.py <broker socket> <browser socket dir> <repo dir>
Prints one JSON object; exits 1 when any check fails.
"""
import json
import os
import socket
import sys
import urllib.request

broker, sockdir, repo = sys.argv[1:4]
res = {}


def talk(path, payload):
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.settimeout(30)
    c.connect(path)
    c.sendall(payload)
    data = b""
    while True:
        chunk = c.recv(65536)
        if not chunk:
            break
        data += chunk
    return data


try:
    res["broker_answers"] = json.loads(talk(broker, b'{"argv": ["get", "url"]}\n')).get("rc") == 0
except Exception:
    res["broker_answers"] = False

try:
    urllib.request.urlopen("https://example.com", timeout=8)
    res["internet_refused"] = False
except Exception:
    res["internet_refused"] = True

probe = os.path.join(repo, ".pair-preflight-%d" % os.getpid())
try:
    with open(probe, "w") as f:
        f.write("x")
    os.remove(probe)
    res["repo_read_only"] = False
except OSError:
    res["repo_read_only"] = True

others = [os.path.join(sockdir, f) for f in os.listdir(sockdir)
          if f.endswith(".sock") and os.path.join(sockdir, f) != broker]
reachable = []
for path in others:
    try:
        talk(path, b"{}\n")
        reachable.append(path)
    except Exception:
        pass
res["browser_socket_unreachable"] = not reachable

print(json.dumps(res))
sys.exit(0 if all(res.values()) else 1)
