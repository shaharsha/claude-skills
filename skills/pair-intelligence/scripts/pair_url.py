#!/usr/bin/env python3
"""Canonical host checks for the browser's local-port pinning.

agent-browser's allow-list matches host names and ignores ports, and every
agent-browser session on the machine listens on loopback, so a local host is
pinned to the exact host:port given. Chrome canonicalizes hosts before it
connects (LOCALHOST, localhost., 127.1, 2130706433 and 0x7f.0.0.1 all reach
loopback, and a backslash counts as a slash), so the pin compares canonical
forms, and anything this cannot canonicalize is refused rather than guessed.

usage:
  pair_url.py domain <entry>            -> "local <host> <port>" or "remote <host> <port|->"
  pair_url.py check <url> [<pin> ...]   -> exit 0 if allowed; 2 with a reason if not
  pair_url.py where <url>               -> "local <host>:<port>" or "remote" (for the page check)
Runs under /usr/bin/python3 -I (3.9 on macOS), so no newer syntax.
"""
import ipaddress
import re
import socket
import sys
import urllib.parse


class Refused(Exception):
    pass


def canon_host(host):
    """Lowercase, no trailing dot, IPv4 in dotted-quad form; refuse what Chrome may read differently."""
    if not host or not re.match(r"^[A-Za-z0-9.\-\[\]:]+$", host):
        raise Refused("host %r has characters a browser may reinterpret" % host)
    h = host.lower().rstrip(".")
    if not h or ".." in h:
        raise Refused("host %r is not a host name" % host)
    if h.startswith("["):
        raise Refused("IPv6 hosts are not supported here; use localhost:PORT or a host name")
    last = h.split(".")[-1]
    if re.match(r"^([0-9]+|0x[0-9a-f]*)$", last):
        # A host whose last label is a number is an IPv4 address to Chrome (URL
        # standard "ends in a number"), in decimal, octal or hex, with 1-4 parts.
        try:
            h = socket.inet_ntoa(socket.inet_aton(h))
        except OSError:
            raise Refused("host %r is not a valid address" % host)
    return h


def is_local(h):
    if h == "localhost" or h.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


def split_url(url):
    if any(c in url for c in "\\\t\r\n ") or any(ord(c) < 32 or ord(c) > 126 for c in url):
        raise Refused("URLs with backslashes, spaces, control or non-ASCII characters are refused")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise Refused("expected an http(s) URL, got %r" % url)
    if "@" in parts.netloc:
        raise Refused("URLs with a user name or password are refused")
    host = parts.netloc
    port = None
    m = re.match(r"^(.*?)(?::([0-9]*))?$", host)
    host, port = m.group(1), m.group(2)
    if port == "":
        port = None
    h = canon_host(host)
    p = int(port) if port else (443 if parts.scheme == "https" else 80)
    return h, p


def main():
    try:
        cmd = sys.argv[1]
        if cmd == "domain":
            d = sys.argv[2].strip()
            d = re.sub(r"^[a-zA-Z]+://", "", d).split("/")[0]
            if not d:
                print("empty")
                return
            m = re.match(r"^(.*?)(?::([0-9]+))?$", d)
            raw, port = m.group(1), m.group(2)
            wildcard = raw.startswith("*.")
            h = canon_host(raw[2:] if wildcard else raw)
            if is_local(h):
                if wildcard or not port:
                    raise Refused("give %s with its port (e.g. %s:5173); a local host is pinned to one port" % (h, h))
                print("local %s %s" % (h, port))
            else:
                print("remote %s%s %s" % ("*." if wildcard else "", h, port or "-"))
        elif cmd == "check":
            h, p = split_url(sys.argv[2])
            pins = sys.argv[3:]
            if is_local(h) and "%s:%d" % (h, p) not in pins:
                raise Refused("local pages are limited to %s; %s:%d is not one of them"
                              % (" ".join(pins) or "none", h, p))
        elif cmd == "where":
            try:
                h, p = split_url(sys.argv[2])
            except Refused:
                print("unknown")
                return
            print("local %s:%d" % (h, p) if is_local(h) else "remote")
        else:
            raise Refused("unknown command")
    except Refused as e:
        sys.stderr.write("pair-browser: %s\n" % e)
        sys.exit(2)
    except (IndexError, ValueError) as e:
        sys.stderr.write("pair-browser: bad URL (%s)\n" % e)
        sys.exit(2)


if __name__ == "__main__":
    main()
