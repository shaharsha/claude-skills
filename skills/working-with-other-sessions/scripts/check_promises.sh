#!/usr/bin/env bash
# check_promises.sh — TOR-474 (ccsend promised reception it cannot deliver).
#
# `armed` means a heartbeat mtime looked fresh and a separately-read pid exists. That is a
# LEASE, not receipt: a watcher whose Monitor consumer has detached keeps its lease fresh AND
# drains the inbox, so the message is consumed and nobody sees it (TOR-425, ccarm's inbox
# drain has no single-owner fencing). Every user-facing surface must therefore say
# ARMED / ACCEPTED / PICKED UP, never "delivered" or "will receive".
#
# WHAT THIS PROVES, exactly: it is a REGRESSION check over the strings this ticket replaced.
# It CANNOT prove no promise exists — "promises" is an open set and no fixed list closes it.
# Closure came from a one-time enumeration of every rendered surface, which is a review
# artifact, not a command. Claiming more for this script than regression would be TOR-474's
# own defect committed by its verification step.
#
# EXIT  0 clean · 1 a forbidden string is present · 2 the probe broke · 3 THE CORPUS IS BROKEN
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$HERE")"
CCSEND="$HERE/ccsend"
CCARM="$HERE/ccarm"

# EXACT strings, matched with grep -F. Not a regex of fragments.
#
# Two measured reasons this is a fixed-string list and not a pattern:
#   (a) a fragment cannot tell a promise from its NEGATION — an earlier draft used
#       `will receive`, which matched the replacement text "who is armed (not who will
#       receive)" and reported FAIL at four correct sites;
#   (b) a hand-built pattern silently misses case and wording variants — the first version
#       missed "who can receive RIGHT NOW", "To become reachable yourself", and "A message
#       reaches an idle session", all of which this commit replaced. Measured: 3 of 4 MISS.
FORBIDDEN=(
  'who can receive right now'
  'who can receive RIGHT NOW'
  'show who can receive right now'
  'armed sessions can receive now'
  'can receive once it runs'
  'it arrives now'
  'arrives only if one is armed'
  'is the only current truth'
  'To become reachable yourself'
  'make THIS session reachable'
  'the backlog *is* delivered on arm'
  'sitting idle waiting for'
  'lets a message reach this session'
  'A message reaches an idle session'
  'can *I* still receive?'
  'delivers messages between sessions'
  'deliver a message to another agent session'
  "so other sessions can reach it"
  '✓ delivered'
  'a fresh lease; NOT proof'
)

CORPUS=''

# emit <label> <expected-status> <cmd...>
#
# Validates the STATUS as well as the output. Checking only for non-empty output is not
# enough and it was a real defect: `cat /missing/README.md` writes an error to stderr, 2>&1
# captures it, the corpus looks populated, and the checker reported a clean tree. Measured —
# it exited 0. A surface that failed is not a surface with no promises in it.
emit() {
  local label="$1" want="$2"; shift 2
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  [ "$rc" = "$want" ] || { echo "CORPUS BROKEN — $label exited $rc, expected $want"; exit 3; }
  [ -n "$out" ]       || { echo "CORPUS BROKEN — no output from: $label"; exit 3; }
  CORPUS+="$out"$'\n'
}

emit 'ccsend --help'      0 "$CCSEND" --help
# --list runs against EMPTY roots. Live session TITLES are rendered into its output
# (ccsend:552 prints title[:52]), so with the real roots the corpus contains ~51 titles
# nobody here controls — and a lane titled e.g. "Why it arrives now is misleading" would
# match a forbidden fragment and fail a correct tree. Demonstrated. The header and footer
# strings this probe exists to check are emitted regardless of how many sessions exist.
# Guard BOTH mktemps. Unchecked, a failure (read-only sandbox, full or unusable TMPDIR)
# leaves the substitution EMPTY — and ccsend reads `os.environ.get(...) or <default>`, so an
# empty CCREAD_MAILBOX is FALSY and falls back to the REAL mailbox. Measured. The isolation
# silently does not happen, live titles re-enter the corpus, and the run still reports clean:
# the r2-F2 fix undone with no signal.
ISO_ROOT="$(mktemp -d)" || { echo "CORPUS BROKEN — cannot create isolation root"; exit 3; }
ISO_MB="$(mktemp -d)"   || { echo "CORPUS BROKEN — cannot create isolation mailbox"; rmdir "$ISO_ROOT" 2>/dev/null; exit 3; }
[ -d "$ISO_ROOT" ] && [ -d "$ISO_MB" ] || { echo "CORPUS BROKEN — isolation dirs missing"; exit 3; }
# CLAUDE_CODE_SESSION_ID is unset too: the caller's own row is pinned into the listing by
# design, and while its title under empty roots is the fixed literal "(no transcript)" and
# therefore safe, unsetting it makes the corpus fully deterministic — 0 rows, header only.
# (The footer prints only when rows are omitted, so it is covered by the source scan below.)
LIST_OUT="$(env -u CLAUDE_CODE_SESSION_ID CCREAD_ROOT="$ISO_ROOT" CCREAD_MAILBOX="$ISO_MB" \
            "$CCSEND" --list 2>&1)"; list_rc=$?
[ "$list_rc" = 0 ] || { echo "CORPUS BROKEN — isolated --list exited $list_rc, expected 0"; exit 3; }
[ -n "$LIST_OUT" ] || { echo "CORPUS BROKEN — no output from: isolated ccsend --list"; exit 3; }
CORPUS+="$LIST_OUT"$'\n'
# Assert the PROPERTY, not the mechanism: under isolation the listing must contain ZERO
# session rows. If any row appears, something leaked a real root in and the corpus is
# contaminated with titles nobody here controls — exactly what this probe exists to prevent.
#
# Scoped to the LIST output alone. Asserting over the accumulated corpus attributed any
# row-shaped line to --list no matter which surface produced it: documenting the row format
# in ccsend's docstring makes `--help` render it legitimately, and a CORRECT tree then exits 3
# claiming the isolation failed. Measured.
if printf '%s' "$LIST_OUT" | grep -qE '^(📬 armed|   unarmed) '; then
  echo "CORPUS BROKEN — isolated --list produced session rows; isolation did not take effect"
  rmdir "$ISO_ROOT" "$ISO_MB" 2>/dev/null
  exit 3
fi
rmdir "$ISO_ROOT" "$ISO_MB" 2>/dev/null || true
emit 'ccarm --help'       0 "$CCARM"  --help
emit 'argparse error'     2 "$CCSEND" --timeout nope --ping
emit 'SKILL.md'           0 cat "$SKILL_DIR/SKILL.md"
emit 'README.md'          0 cat "$SKILL_DIR/README.md"

# SOURCE scan, unioned with the rendered surfaces above.
#
# Rendered output alone CANNOT cover every promise: the send receipt and the --arm hint live
# on branches that need a real target with a live lease, and fabricating one is fragile
# (measured: a hand-built heartbeat gave FRESH LEASE to `--self` while the send path still
# refused, so the fixture did not reproduce the branch it existed to reach). Those were the
# ticket's worst sites — `✓ delivered … it arrives now` is printed on every send — so leaving
# them uncovered would exempt precisely what matters most.
#
# Scanning the source covers EVERY branch, rendered or not. It is weaker in one specific way
# and the weakness is named rather than hidden: a string reachable only through source is
# proof the literal is absent from the code, not proof of what a user sees. The two together
# are strictly stronger than either alone.
# Whole-line comments are stripped from the SOURCE scan. A maintainer writing a truthful
# note — "# the old wording 'it arrives now' was removed" — is not a promise, but a
# context-free fixed string cannot tell an affirmation from a citation of one. Demonstrated:
# such a comment made the checker FAIL a correct tree.
#
# RESIDUE, named rather than hidden: a TRAILING comment on a line of code is not stripped,
# so quoting an old string after live code still trips it. Move such a note to its own line.
# Python source: drop COMMENT tokens, keep STRING tokens. The previous rule was a lexical
# sed on lines starting with `#`, which is syntax-BLIND in both directions — it removed a
# `# it arrives now` line living inside a live triple-quoted string, hiding a real promise.
# tokenize knows the difference; sed cannot.
strip_py_comments() {
  python3 - "$1" <<'PYEOF'
import io, sys, tokenize
src = open(sys.argv[1], encoding='utf-8').read()
out, last = [], (1, 0)
try:
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            continue
        out.append(tok)
except (tokenize.TokenError, IndentationError):
    # Tokenizing failed: emit the file UNCHANGED rather than a partial one. A truncated
    # corpus would hide promises in whatever came after the failure point.
    sys.stdout.write(src); sys.exit(0)
sys.stdout.write(tokenize.untokenize(out))
PYEOF
}
# Shell source: no tokenizer here, so the lexical rule stays.
#
# RESIDUE, named and LIVE — I first wrote that ccarm "contains no heredoc today" and the
# control I cited in the same sentence refuted it. ccarm:179-196 IS a heredoc (`done
# <<RECOVER_EOF`), and four of its body lines begin with `#`. Stripping those is harmless
# because they are genuine shell comments inside code the heredoc evaluates — but the gap is
# real, not hypothetical: a forbidden string placed on a `#`-leading line inside a heredoc
# body would be missed. Keep such text off `#`-leading lines in shell sources.
strip_sh_comments() { sed -E 's/^[[:space:]]*#.*$//' "$1"; }
emit 'ccsend source'      0 strip_py_comments "$CCSEND"
emit 'ccarm source'       0 strip_sh_comments "$CCARM"

# No prose "positive control" anchor here. The previous version grepped for a documentation
# sentence, which a legitimate later edit could rephrase — turning a correct tree into
# CORPUS BROKEN. Per-surface status validation above is the structural form of the same
# assertion and does not depend on any wording surviving.

# Read grep's status explicitly. `if grep -qF ...; then` collapses EVERY nonzero status
# into the else-branch, so an operational grep error (2) was indistinguishable from "no
# match" and the script reported CLEAN — while documenting an exit 2 that no path could
# produce. A documented state that cannot occur is a false claim about the instrument.
hits=0
for s in "${FORBIDDEN[@]}"; do
  printf '%s' "$CORPUS" | grep -qF -- "$s"; g=$?
  case $g in
    0) echo "FORBIDDEN STRING PRESENT: $s"; hits=$((hits + 1)) ;;
    1) ;;
    *) echo "PROBE BROKE — grep exited $g on: $s; nothing was concluded"; exit 2 ;;
  esac
done

case $hits in
  0) echo 'clean — no replaced string in any rendered surface or scanned source'; exit 0 ;;
  *) echo "FAIL — $hits forbidden string(s) present"; exit 1 ;;
esac
