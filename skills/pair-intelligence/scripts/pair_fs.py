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

ROOTS = [os.path.realpath(r) for r in json.loads(os.environ.get("PAIR_FS_ROOTS") or "[]")]
MAX_LINES = 400
MAX_BYTES = 60000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
             ".pytest_cache", ".next", ".turbo"}
# Secret files stay out of search output; the model's file reader refuses them too.
SECRET_GLOBS = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*",
                ".netrc", ".npmrc", ".pypirc"]
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


def resolve(p):
    if not ROOTS:
        die("no readable folders are configured")
    full = os.path.realpath(p if os.path.isabs(p) else os.path.join(ROOTS[0], p))
    if not any(inside(full, r) for r in ROOTS):
        die("%s is outside the folders you may read: %s" % (p, ", ".join(ROOTS)))
    if not os.path.exists(full):
        die("%s: no such file or directory" % p)
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
    pattern, path = rest[0], resolve(rest[1] if len(rest) > 1 else ".")
    rg = shutil.which("rg", path=TOOL_PATH)
    if rg:
        # Ignores .gitignore'd files like the model's own tools would; --no-config
        # keeps RIPGREP_CONFIG_PATH out, and nothing the model passes becomes a flag.
        argv = [rg, "--no-config", "--no-messages", "-n", "--no-heading", "--color=never",
                "--max-columns=300", "--max-columns-preview", "--hidden", "--glob=!.git"] + flags
        if glob:
            argv += ["--glob", glob]
        argv += ["--glob=!" + g for g in SECRET_GLOBS] + ["-e", pattern, "--", path]
    else:
        argv = ["/usr/bin/grep", "-rnI", "--exclude-dir=.git", "--exclude-dir=node_modules"] + flags
        if glob:
            argv += ["--include", glob]
        argv += ["--exclude=" + g for g in SECRET_GLOBS] + ["-e", pattern, "--", path]
    rc, out, err = run(argv, ROOTS[0])
    if rc == 1 and not out:
        print("no matches")
        return
    if rc not in (0, 1):
        die(err.strip() or "search failed")
    emit(out.splitlines(), "lines")


# git: subcommand -> flags taken as they are. Value flags are checked by shape below.
GIT_FLAGS = {
    "status": {"-s", "--short", "-b", "--branch", "--porcelain", "-uno", "--untracked-files=no"},
    "diff": {"--stat", "--numstat", "--shortstat", "--name-only", "--name-status", "--cached",
             "--staged", "-w", "--ignore-space-change", "--word-diff", "--merge-base", "-p", "--patch"},
    "log": {"--oneline", "--stat", "--name-only", "--name-status", "-p", "--patch", "--graph",
            "--decorate", "--all", "--no-merges", "--first-parent", "--reverse", "--follow", "-w"},
    "show": {"--stat", "--name-only", "--name-status", "--oneline", "-p", "--patch", "-w", "--no-patch", "-s"},
    "blame": {"-w", "-M", "-C", "-s", "-e"},
    "ls-files": {"-m", "--modified", "-o", "--others", "--exclude-standard", "-d", "--deleted"},
}
GIT_VALUE = re.compile(r"^(-n|-U|-L|--max-count|--unified|--since|--until|--after|--before|--author|"
                       r"--grep|--format|--pretty|--date)(=.+)?$|^-[0-9]+$|^-U[0-9]+$|^-n[0-9]+$")
REV = re.compile(r"^[A-Za-z0-9_@^~{}:+-][A-Za-z0-9._/@^~{}:+-]*$")
GIT_HELP = "pair-fs git <sub> [flags] [revs] [-- paths]\n" + "\n".join(
    "  %-8s %s" % (k, " ".join(sorted(v))) for k, v in GIT_FLAGS.items()) + \
    "\n  value flags: -n N, -N, -U N, -L a,b (blame), --max-count= --since= --until= --author= --grep= --format= --date="


def git_toplevel():
    git = shutil.which("git", path=TOOL_PATH) or die("git is not installed")
    for r in ROOTS:
        rc, out, _ = run([git, "-C", r, "rev-parse", "--show-toplevel"], r)
        if rc == 0 and out.strip():
            return git, os.path.realpath(out.strip())
    die("none of the readable folders is a git repository")


def cmd_git(args):
    if not args or args[0] not in GIT_FLAGS:
        print(GIT_HELP)
        sys.exit(0 if not args else 2)
    sub, rest, out, paths, i = args[0], args[1:], [], [], 0
    git, top = git_toplevel()
    while i < len(rest):
        a = rest[i]
        if a == "--":
            paths = rest[i + 1:]
            break
        if a in GIT_FLAGS[sub]:
            out.append(a)
        elif GIT_VALUE.match(a):
            if "=" in a or re.match(r"^-[0-9]+$|^-U[0-9]+$|^-n[0-9]+$", a):
                out.append(a)
            else:
                if i + 1 >= len(rest) or rest[i + 1].startswith("-"):
                    die("%s needs a value" % a)
                out += [a, rest[i + 1]]
                i += 1
        elif a.startswith("-"):
            die("git %s does not accept %s here; run 'pair-fs git' for the flags" % (sub, a))
        elif REV.match(a) and "/../" not in a and not a.endswith("/..") and not a.startswith("../"):
            out.append(a)  # a revision, range, rev:path, or a path inside the repo
        else:
            die("%s is not a revision; put file paths after --" % a)
        i += 1
    rel = []
    for p in paths:
        full = resolve(p)
        if not inside(full, top):
            die("%s is outside the git repository %s" % (p, top))
        rel.append(os.path.relpath(full, top))
    # Repository config cannot run anything here: the fsmonitor hook, pager,
    # external diff and textconv drivers are all switched off for this call,
    # and GIT_OPTIONAL_LOCKS keeps status from rewriting the index.
    base = [git, "-C", top, "-c", "core.fsmonitor=false", "-c", "core.pager=cat",
            "-c", "diff.external=", "-c", "core.hooksPath=/dev/null", "-c", "color.ui=never",
            "-c", "diff.ignoreSubmodules=all", "-c", "status.submoduleSummary=false", "--no-pager", sub]
    if sub in ("diff", "log", "show"):
        base += ["--no-ext-diff", "--no-textconv"]
    if sub == "blame":
        base += ["--no-textconv"]
    if sub == "status":
        base += ["--ignore-submodules=all"]
    rc, so, se = run(base + out + (["--"] + rel if rel else []), top,
                     {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
                      "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat"})
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
