# shellcheck shell=bash
# Sourced by pair.sh and codex_review.sh: the Codex features a second-opinion
# run must not have.
#
# --ignore-user-config drops the user's MCP servers and plugins from config.toml,
# but these features are on by default without any config (codex-cli 0.165,
# `codex features list`). Measured 2026-11-04: with --ignore-user-config alone, a
# read-only consult listed the account's ChatGPT app connectors
# (list_mcp_resources -> server "codex_apps"), which act through the user's
# account outside the sandbox; with these off, it listed none. Browser and
# computer use drive a real browser or desktop, hooks run local commands, and a
# reviewer needs no image generation or plugin installs.
#
# -c features.<name>=false rather than --disable <name>: a name a later Codex
# drops is then an unknown config key, not an unknown flag.
CODEX_LOCKDOWN=()
for _feature in apps plugins remote_plugin plugin_sharing browser_use browser_use_external \
    browser_use_full_cdp_access computer_use in_app_browser in_app_local_automation hooks \
    image_generation skill_mcp_dependency_install tool_suggest; do
  CODEX_LOCKDOWN+=(-c "features.$_feature=false")
done
unset _feature

# --- folders no second opinion may read ----------------------------------------------
# Codex's read-only sandbox reads the whole disk: on 2026-11-12 a reviewer pointed
# at one repository opened a benchmark answer-key folder beside it on its own.
# A permission profile denies reads of named paths (codex-cli 0.165:
# permissions.<profile>.filesystem = {"<abs path>" = "deny"}; tested with `codex
# sandbox` on 2026-11-13: cat, ls, stat, cp -r, git -C, a symlink into the folder
# and the /private spelling were all refused). Passing -s to `codex exec` turns a
# profile off, so a run with denied folders passes none.
#
# The list: one path per line in ${XDG_CONFIG_HOME:-~/.config}/pair-intelligence/deny-read
# (# starts a comment), then PAIR_DENY_READ (colon-separated), then --deny-read.
# Each must be absolute or start with ~/. Sets PAIR_DENY (array of absolute paths)
# and PAIR_DENY_TABLE (the TOML inline table, empty when there is nothing to deny).
pair_deny_load() {  # args: the --deny-read values
  local cfg="${XDG_CONFIG_HOME:-$HOME/.config}/pair-intelligence/deny-read" tmp p
  tmp="$(mktemp "${TMPDIR:-/tmp}/pair-deny.XXXXXX")"
  python3 - "$cfg" "${PAIR_DENY_READ:-}" "$@" > "$tmp" <<'PY' || { rm -f "$tmp"; return 64; }
import os, sys
cfg, env, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
items = []
if os.path.isfile(cfg):
    for line in open(cfg, encoding="utf-8", errors="replace"):
        line = line.split("#", 1)[0].strip()
        if line:
            items.append(line)
items += [p for p in env.split(":") if p.strip()] + flags
paths = []
for p in items:
    p = p.strip()
    if p.startswith("~/"):
        p = os.path.join(os.path.expanduser("~"), p[2:])
    if not os.path.isabs(p):
        sys.stderr.write("a folder no reviewer may read must be an absolute path or start with ~/: %s\n" % p)
        sys.exit(64)
    # Both spellings: the path as given and with its links resolved.
    for q in (os.path.normpath(p), os.path.realpath(p)):
        if q not in paths:
            paths.append(q)
# A denied path inside a git repository can be read from its object store without
# opening the file: `git show HEAD:held/key.txt`, a reflog entry, a stash, even a
# loose object left by a `git add` that was undone. No check of history finds them
# all (a review, 2026-11-13, found four ways past one), so the repository's git
# directory is denied with it, whatever git knows about the path, and named on the
# second output. Keep answer keys outside the repositories you review.
import subprocess
def common_dir(d):
    r = subprocess.run(["git", "-C", d, "-c", "core.fsmonitor=false", "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    return os.path.realpath(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else ""
# Where git keeps the history of a denied path: the repository around it, and any
# repository, linked worktree or submodule inside a denied folder, whose storage
# may live outside it (a worktree's .git is a file pointing elsewhere; found in a
# review, 2026-11-13).
places = []
for p in list(paths):
    d = p
    while not os.path.isdir(d) and d != os.path.dirname(d):
        d = os.path.dirname(d)
    places.append(d)
    if os.path.isdir(p):
        seen = 0
        def unreadable(err):
            # A folder that cannot be listed may hide a worktree: refuse rather than guess.
            sys.stderr.write("cannot check %s for git repositories (%s); deny-read needs to list every folder in it\n"
                             % (getattr(err, "filename", p), err.strerror or err))
            sys.exit(64)
        for root, dirs, files in os.walk(p, onerror=unreadable):
            seen += 1
            if seen > 200000:
                sys.stderr.write("%s is too large to check for git repositories inside it; deny a narrower folder\n" % p)
                sys.exit(64)
            if ".git" in dirs or ".git" in files:
                places.append(root)
            dirs[:] = [x for x in dirs if x != ".git"]
gitdirs = []
for d in places:
    common = common_dir(d)
    if not common:
        continue
    if common not in paths:
        paths.append(common)
    if common not in gitdirs:
        gitdirs.append(common)
sys.stdout.write("".join(q + "\0" for q in paths) + "\0" + "".join(q + "\0" for q in gitdirs))
PY
  PAIR_DENY=(); PAIR_DENY_GITDIRS=()
  local part=0
  while IFS= read -r -d '' p; do
    if [[ -z "$p" ]]; then part=1; continue; fi
    if [[ $part -eq 0 ]]; then PAIR_DENY+=("$p"); else PAIR_DENY_GITDIRS+=("$p"); fi
  done < "$tmp"
  rm -f "$tmp"
  PAIR_DENY_TABLE=""
  [[ ${#PAIR_DENY[@]} -gt 0 ]] && PAIR_DENY_TABLE="$(python3 -c 'import json, sys; print("{" + ",".join("%s=\"deny\"" % json.dumps(p) for p in sys.argv[1:]) + "}")' "${PAIR_DENY[@]}")"
  return 0
}

# Refuse a folder or file that overlaps a denied path either way: a root inside a
# denied folder, or a denied path inside a root. Used for Gemini's readable roots
# (--cwd and each --image: it reads under them by its own rules) and for the
# repository a --runnable copy is made from (the copy would carry the files out
# of the denied folder into an allowed one).
pair_deny_overlap() {  # $1: what it is (for the message), $2: the path
  local p
  for p in ${PAIR_DENY[@]+"${PAIR_DENY[@]}"}; do
    if python3 -c 'import os,sys; c,p=os.path.realpath(sys.argv[1]),os.path.realpath(sys.argv[2]); sys.exit(0 if os.path.commonpath((c,p)) in (c,p) else 1)' "$2" "$p"; then
      echo "$1 $2 overlaps $p, which no reviewer may read (the pair-intelligence deny-read list); stage only what the run needs with pair_stage.sh and point there" >&2
      return 64
    fi
  done
}

# Refuse a run in a repository whose git directory is denied (a denied path lies
# inside it, or inside a linked worktree of it): the run could not read history.
pair_deny_repo_check() {  # $1: the repository the run reads
  local common g
  common="$(git -C "$1" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 0
  common="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$common")"
  for g in ${PAIR_DENY_GITDIRS[@]+"${PAIR_DENY_GITDIRS[@]}"}; do
    if [[ "$g" == "$common" ]]; then
      echo "the repository at $1 holds a path no reviewer may read, so its git directory is denied with it and the run could not read its history; stage what the run needs with pair_stage.sh (no history) and point there, or keep the denied path outside the repository" >&2
      return 64
    fi
  done
}

# Prove, inside the very tier the run will use, that each denied path that exists
# is refused, through its resolved spelling (a symlink itself sits in an allowed
# folder; what it points to is what must be refused). `ls -d DIR/.` and `wc -c
# FILE` print nothing of the contents even when allowed. This also catches a later
# Codex that renames or drops the profile keys.
pair_deny_preflight() {  # $1: the folder to run in; rest: the sandbox tier's -c arguments
  local dir="$1" p real out; shift
  for p in ${PAIR_DENY[@]+"${PAIR_DENY[@]}"}; do
    [[ -e "$p" ]] || continue
    real="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$p")"
    if [[ -d "$real" ]]; then
      out="$(cd "$dir" && codex sandbox "$@" -- /bin/ls -d "$real/." 2>&1)"
    else
      out="$(cd "$dir" && codex sandbox "$@" -- /usr/bin/wc -c "$real" 2>&1)"
    fi
    if [[ "$out" != *"Operation not permitted"* ]]; then
      echo "the deny-read check failed, so Codex was not started: inside the run's sandbox $p was readable ($out)" >&2
      return 71
    fi
  done
}

# The sandbox tier for a run with denied folders: read-only, or the writable
# runnable copy with its network off (sandbox_workspace_write.network_access is
# ignored once a profile is active). Sets CODEX_DENY_TIER.
pair_deny_tier() {  # $1: :read-only or :workspace
  CODEX_DENY_TIER=(-c 'default_permissions="pair_review"' -c "permissions.pair_review.extends=\"$1\""
                   -c "permissions.pair_review.filesystem=$PAIR_DENY_TABLE")
  [[ "$1" == ":workspace" ]] && CODEX_DENY_TIER+=(-c 'permissions.pair_review.network.enabled=false')
  return 0
}
