#!/usr/bin/env python3
"""pair-fs: read-only listing, search and git history for the Gemini engine.

agy in Gemini-API-key mode gives the model a file reader but no list, find or
grep tool, and pair.sh refuses every other shell command. This is how the model
looks around the project. It reads only inside the folders pair.sh pins in
PAIR_FS_ROOTS (a JSON list), follows no symlink out of them, runs nothing the
model names, and caps what it prints.

Runs under /usr/bin/python3 -I (3.9 on macOS), so no newer syntax.
"""
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

RAW_ROOTS = [os.path.normpath(r) for r in json.loads(os.environ.get("PAIR_FS_ROOTS") or "[]")]
ROOTS = [os.path.realpath(r) for r in RAW_ROOTS]
MAX_LINES = 400
MAX_BYTES = 60000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
             ".pytest_cache", ".next", ".turbo"}
# Secret files stay out of every output: search, listing of contents and git
# patches. The model's file reader (agy_gate.py) refuses the same names.
SECRET_GLOBS = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*",
                "id_ecdsa*", "id_dsa*", ".netrc", ".npmrc", ".pypirc"]
SECRET = re.compile(r"^(\.env(\..+)?|.+\.(pem|key|p12|pfx)|id_(rsa|ed25519|ecdsa|dsa).*|\.netrc|\.npmrc|\.pypirc)$",
                    re.IGNORECASE | re.DOTALL)  # DOTALL: a file name may hold a newline
SECRET_OK = re.compile(r"^\.env\.(example|sample|template|dist)$", re.IGNORECASE)


def is_secret(name):
    name = os.path.basename(name.rstrip("/"))
    return bool(SECRET.match(name)) and not SECRET_OK.match(name)
TOOL_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

USAGE = """usage: pair-fs <command> ...
  ls [PATH]                                   list a directory
  find GLOB [PATH]                            files whose name matches GLOB, e.g. find '*.py' src
  grep [-i] [-F] [-l] [-w] [--glob G] PATTERN [PATH]
                                              search file contents (regex unless -F)
  git status|diff|log|show|blame|ls-files [ARGS]
                                              read-only git; run 'pair-fs git' for the flags
PATH is absolute or relative to %s. Read a file's contents with your file-reading tool."""


def die(msg, code=2):
    sys.stderr.write("pair-fs: %s\n" % msg)
    sys.exit(code)


def inside(full, root):
    return full == root or full.startswith(root + os.sep)


def resolve(p, contents=False):
    """The real path of p, which must stay inside the roots. contents: the caller
    will print what is inside the file, so a secret (by name or link) is refused."""
    if not ROOTS:
        die("no readable folders are configured")
    given = p if os.path.isabs(p) else os.path.join(ROOTS[0], p)
    full = os.path.realpath(given)
    if not any(inside(full, r) for r in ROOTS):
        die("%s is outside the folders you may read: %s" % (p, ", ".join(ROOTS)))
    if not os.path.exists(full):
        die("%s: no such file or directory" % p)
    if contents and (is_secret(given) or is_secret(full)):
        die("%s is a secret file (.env, keys); its contents are not shown" % p)
    return full


def emit(lines, what="lines"):
    shown, size = [], 0
    for ln in lines:
        if len(shown) >= MAX_LINES or size + len(ln) > MAX_BYTES:
            sys.stdout.write("\n".join(shown) + "\n")
            sys.stdout.write("[output cut at %d %s; narrow the path or pattern]\n" % (len(shown), what))
            return
        shown.append(ln)
        size += len(ln) + 1
    sys.stdout.write("\n".join(shown) + ("\n" if shown else ""))


def run(argv, cwd, env_extra=None):
    env = {"PATH": TOOL_PATH, "LANG": "en_US.UTF-8", "HOME": "/nonexistent"}
    env.update(env_extra or {})
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    except subprocess.TimeoutExpired:
        die("timed out after 60s; narrow the path or pattern")
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def cmd_ls(args):
    if len(args) > 1:
        die("ls takes at most one path")
    d = resolve(args[0] if args else ".")
    if not os.path.isdir(d):
        die("%s is not a directory" % d)
    rows = [d + ":"]
    for e in sorted(os.scandir(d), key=lambda e: e.name):
        try:
            if e.is_symlink():
                kind, size = "link", ""
            elif e.is_dir():
                kind, size = "dir", ""
            else:
                kind, size = "file", str(e.stat().st_size)
        except OSError:
            kind, size = "?", ""
        rows.append("%-4s %9s  %s%s" % (kind, size, e.name, "/" if kind == "dir" else ""))
    emit(rows, "entries")


def cmd_find(args):
    if not 1 <= len(args) <= 2:
        die("find takes a glob and an optional path")
    glob, root = args[0], resolve(args[1] if len(args) > 1 else ".")
    by_path = "/" in glob
    out = []
    for dp, dns, fns in os.walk(root):  # does not follow symlinked directories
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for n in sorted(dns) + sorted(fns):
            full = os.path.join(dp, n)
            if fnmatch.fnmatch(os.path.relpath(full, root) if by_path else n, glob):
                out.append(full + ("/" if n in dns else ""))
        if len(out) > MAX_LINES:
            break
    if not out:
        print("no matches")
    emit(out, "matches")


def py_grep(pattern, path, flags, glob):
    """Used when ripgrep is missing: same refusals (secret names in any case, no
    symlinks followed, the usual heavy folders skipped), plain Python search."""
    try:
        rx = re.compile(re.escape(pattern) if "-F" in flags else pattern, re.IGNORECASE if "-i" in flags else 0)
    except re.error as e:
        die("bad pattern: %s" % e)
    if "-w" in flags:
        rx = re.compile(r"\b(?:%s)\b" % rx.pattern, rx.flags)
    files = [path] if os.path.isfile(path) else []
    if not files:
        for dp, dns, fns in os.walk(path):
            dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
            files += [os.path.join(dp, f) for f in sorted(fns)]
    out = []
    for f in files:
        name = os.path.basename(f)
        if os.path.islink(f) or is_secret(name) or (glob and not fnmatch.fnmatch(name, glob)):
            continue
        try:
            with open(f, "rb") as fh:
                data = fh.read(2000000)
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue
        for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if rx.search(line):
                if "-l" in flags:
                    out.append(f)
                    break
                out.append("%s:%d:%s" % (f, n, line[:300]))
        if len(out) > MAX_LINES:
            break
    if not out:
        print("no matches")
    emit(out, "lines")


def cmd_grep(args):
    flags, glob, rest, i = [], None, [], 0
    while i < len(args):
        a = args[i]
        if a == "--":
            rest += args[i + 1:]
            break
        if a in ("-i", "-F", "-l", "-w"):
            flags.append(a)
            i += 1
        elif a == "--glob":
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                die("--glob needs a value")
            glob = args[i + 1]
            i += 2
        elif a.startswith("-"):
            die("grep accepts -i, -F, -l, -w and --glob G (put -- before a pattern that starts with -); got %s" % a)
        else:
            rest.append(a)
            i += 1
    if not 1 <= len(rest) <= 2:
        die("grep takes a pattern and an optional path")
    pattern, path = rest[0], resolve(rest[1] if len(rest) > 1 else ".", contents=True)
    # PAIR_FS_FORCE_PY_GREP is for the tests; the shim's env -i keeps it from the model.
    rg = None if os.environ.get("PAIR_FS_FORCE_PY_GREP") else shutil.which("rg", path=TOOL_PATH)
    if rg:
        # Ignores .gitignore'd files like the model's own tools would; --no-config
        # keeps RIPGREP_CONFIG_PATH out, and nothing the model passes becomes a flag.
        argv = [rg, "--no-config", "--no-messages", "-n", "--no-heading", "--color=never",
                "--max-columns=300", "--max-columns-preview", "--hidden", "--glob=!.git"] + flags
        if glob:
            argv += ["--glob", glob]
        argv += ["--iglob=!" + g for g in SECRET_GLOBS] + ["-e", pattern, "--", path]
    else:
        return py_grep(pattern, path, flags, glob)
    rc, out, err = run(argv, ROOTS[0])
    if rc == 1 and not out:
        print("no matches")
        return
    if rc not in (0, 1):
        die(err.strip() or "search failed")
    emit(out.splitlines(), "lines")


# git: subcommand -> flags taken as they are. Value flags are checked by shape below.
#
# Secret files must never print, and git has many ways to name a file's
# contents (rev:path, :0:path, reflog dates, -L <range>:<file>, a blob's id,
# --follow across a rename). So no argument may name contents at all: a
# revision may not contain ":", may not resolve to a blob, -L is blame-only and
# numeric, --follow is gone, and every diff, show and log carries pathspecs that
# exclude secret files from its output. Reading a file at a revision goes
# through `cat`, which checks the path the way the file reader does.
GIT_FLAGS = {
    "status": {"-s", "--short", "-b", "--branch", "--porcelain", "-uno", "--untracked-files=no"},
    "diff": {"--stat", "--numstat", "--shortstat", "--name-only", "--name-status", "--cached",
             "--staged", "-w", "--ignore-space-change", "--word-diff", "--merge-base", "-p", "--patch"},
    "log": {"--oneline", "--stat", "--name-only", "--name-status", "-p", "--patch", "--graph",
            "--decorate", "--all", "--no-merges", "--first-parent", "--reverse", "-w"},
    "show": {"--stat", "--name-only", "--name-status", "--oneline", "-p", "--patch", "-w", "--no-patch", "-s"},
    "blame": {"-w", "-M", "-C", "-s", "-e"},
    "ls-files": {"-m", "--modified", "-o", "--others", "--exclude-standard", "-d", "--deleted"},
    "cat": set(),
}
# Values only in attached form (-U3, --format=X): several of these take an
# optional value, and git reads a separate next word as a revision, so a
# separate value would carry an unchecked object name past check_rev.
GIT_VALUE = re.compile(r"^(--max-count|--unified|--since|--until|--after|--before|--author|"
                       r"--grep|--format|--pretty|--date)=.+$|^-[0-9]+$|^-U[0-9]+$|^-n[0-9]+$")
# Repository config that names a program git could run, directly or through a
# driver: refused outright, since -c can only switch off the keys it names.
RISKY_CONFIG = re.compile(r"^(include|includeif)\.|program|command|helper|\.(clean|smudge|process)$|pager|editor|"
                          r"driver|fsmonitor|textconv|showsignature|alternate|hookspath|^alias\.|^uploadpack\.|"
                          r"^core\.(sshcommand|askpass|gitproxy)", re.IGNORECASE)
REV = re.compile(r"^[A-Za-z0-9_@^~{}+-][A-Za-z0-9._/@^~{}+-]*$")  # no ":" anywhere
SECRET_EXCLUDES = [":(exclude,icase,glob)**/" + g for g in SECRET_GLOBS]
GIT_HELP = "pair-fs git <sub> [flags] [revs] [-- paths]\n" + "\n".join(
    "  %-8s %s" % (k, " ".join(sorted(v))) for k, v in GIT_FLAGS.items() if k != "cat") + \
    "\n  values attached: -n5, -5, -U3, --max-count=5 --since=DATE --until=DATE --author=X --grep=X --format=X --date=X" + \
    "\n  blame -L START,END" + \
    "\n  cat REV PATH   the file at PATH as of revision REV (secret files refused)"
GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
           "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat"}


def git_toplevel():
    git = shutil.which("git", path=TOOL_PATH) or die("git is not installed")
    for r in ROOTS:
        if not os.path.isdir(r):  # an image passed as a root
            continue
        rc, out, _ = run([git, "-C", r, "rev-parse", "--show-toplevel"], r, GIT_ENV)
        if rc == 0 and out.strip():
            top = os.path.realpath(out.strip())
            # History covers the whole repository; a root inside it would leak the rest.
            if not any(inside(top, root) for root in ROOTS):
                die("git history covers the whole repository at %s, wider than the folders you may read; "
                    "pair-fs git is off for this run" % top)
            rc, cfg, _ = run([git, "-C", top, "config", "--list", "--includes", "--name-only"], top, GIT_ENV)
            risky = sorted({k for k in cfg.split() if RISKY_CONFIG.search(k)})
            if risky:
                die("this repository's git config sets %s, which can make git run a program; "
                    "pair-fs git is off for it" % ", ".join(risky[:5]))
            return git, top
    die("none of the readable folders is a git repository")


def secret_path(rel):
    return any(is_secret(part) for part in rel.split("/") if part)


def check_rev(git, top, token):
    """A revision or range; none of its ends may be a blob (a file's contents by id)."""
    if not REV.match(token) or "/../" in token or token.endswith("/..") or token.startswith("../"):
        die("%s is not a revision (a revision has no ':'); put file paths after --, "
            "and use 'pair-fs git cat REV PATH' for a file at a revision" % token)
    if secret_path(token):
        die("%s names a secret file (.env, keys); its contents are not shown" % token)
    for end in re.split(r"\.\.\.?", token):
        if end:
            # ^{} peels tags: an annotated tag can point straight at a blob.
            rc, kind, _ = run([git, "-C", top, "cat-file", "-t", end + "^{}"], top, GIT_ENV)
            if rc == 0 and kind.strip() == "blob":
                die("%s is a file's contents by id; use 'pair-fs git cat REV PATH'" % token)


def base_cmd(git, top, sub):
    # Repository config cannot run anything here: the fsmonitor hook, pager,
    # external diff, textconv drivers and signature programs are switched off for
    # this call, and GIT_OPTIONAL_LOCKS keeps status from rewriting the index.
    cmd = [git, "-C", top, "-c", "core.fsmonitor=false", "-c", "core.pager=cat",
           "-c", "diff.external=", "-c", "core.hooksPath=/dev/null", "-c", "color.ui=never",
           "-c", "diff.ignoreSubmodules=all", "-c", "status.submoduleSummary=false",
           "-c", "log.showSignature=false", "-c", "gpg.program=/usr/bin/false",
           "-c", "gpg.ssh.program=/usr/bin/false", "-c", "gpg.x509.program=/usr/bin/false", "--no-pager", sub]
    if sub in ("diff", "log", "show"):
        cmd += ["--no-ext-diff", "--no-textconv"]
    if sub in ("log", "show"):
        cmd += ["--no-show-signature"]
    if sub == "blame":
        cmd += ["--no-textconv"]
    if sub == "status":
        cmd += ["--ignore-submodules=all"]
    return cmd


def cmd_git_cat(git, top, rest):
    if len(rest) != 2:
        die("cat takes a revision and a path: pair-fs git cat HEAD~1 src/app.py")
    rev, path = rest
    check_rev(git, top, rev)
    rc, kind, _ = run([git, "-C", top, "cat-file", "-t", rev + "^{}"], top, GIT_ENV)
    if rc != 0 or kind.strip() != "commit":
        die("%s is not a commit" % rev)
    # A path in history, so mapped by text, never through the working tree's
    # symlinks (a file that became a link would read another file). The
    # harness names the project by its unresolved path (/tmp, /var/folders on
    # macOS), so that prefix is swapped for the resolved root first.
    if os.path.isabs(path):
        for raw, real in zip(RAW_ROOTS, ROOTS):
            if path == raw or path.startswith(raw + os.sep):
                path = real + path[len(raw):]
                break
    full = os.path.normpath(path if os.path.isabs(path) else os.path.join(top, path))
    if not inside(full, top) or not any(inside(full, r) for r in ROOTS):
        die("%s is outside the git repository %s or the folders you may read" % (path, top))
    rel = os.path.relpath(full, top)
    if rel == "." or secret_path(rel):
        die("%s is a secret file (.env, keys) or not a file; its contents are not shown" % path)
    rc, so, se = run(base_cmd(git, top, "show") + ["%s:%s" % (rev, rel)], top, GIT_ENV)
    if rc != 0:
        die(se.strip() or "git cat failed")
    emit(so.splitlines(), "lines")


def cmd_git(args):
    if not args or args[0] not in GIT_FLAGS:
        print(GIT_HELP)
        sys.exit(0 if not args else 2)
    sub, rest, out, paths, i = args[0], args[1:], [], [], 0
    git, top = git_toplevel()
    if sub == "cat":
        return cmd_git_cat(git, top, rest)
    while i < len(rest):
        a = rest[i]
        if a == "--":
            paths = rest[i + 1:]
            break
        if a in GIT_FLAGS[sub]:
            out.append(a)
        elif sub == "blame" and (a == "-L" or a.startswith("-L")):
            val = a[2:] if len(a) > 2 else (rest[i + 1] if i + 1 < len(rest) else "")
            if not re.match(r"^[0-9]+,[0-9]+$", val):
                die("blame -L takes START,END line numbers")
            out.append("-L" + val)
            i += 0 if len(a) > 2 else 1
        elif GIT_VALUE.match(a):
            if re.match(r"^--(format|pretty)=", a) and "%G" in a:
                die("signature placeholders (%G...) are not available")
            out.append(a)
        elif a.startswith("-"):
            die("git %s does not accept %s here; run 'pair-fs git' for the flags" % (sub, a))
        else:
            check_rev(git, top, a)
            out.append(a)  # a revision or range, or a path inside the repo
        i += 1
    rel = []
    for p in paths:
        full = resolve(p, contents=True)
        if not inside(full, top):
            die("%s is outside the git repository %s" % (p, top))
        rel.append(os.path.relpath(full, top))
    if sub in ("diff", "show", "log"):
        # Whatever the flags (-p, -U, --stat...), secret files stay out of the output.
        rel = (rel or ["."]) + SECRET_EXCLUDES
    rc, so, se = run(base_cmd(git, top, sub) + out + (["--"] + rel if rel else []), top, GIT_ENV)
    if rc != 0:
        die(se.strip() or "git %s failed" % sub)
    emit(so.splitlines(), "lines")


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE % (ROOTS[0] if ROOTS else "the project"))
        return
    cmds = {"ls": cmd_ls, "find": cmd_find, "grep": cmd_grep, "git": cmd_git}
    if argv[0] not in cmds:
        die("'%s' is not a pair-fs command\n%s" % (argv[0], USAGE % (ROOTS[0] if ROOTS else "the project")))
    cmds[argv[0]](argv[1:])


if __name__ == "__main__":
    main()
