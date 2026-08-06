#!/usr/bin/env bash
# check_promises.sh — TOR-474 (ccsend promises reception it cannot deliver).
#
# `armed` means a heartbeat mtime looked fresh and a separately-read pid exists. That is a
# LEASE. It is not receipt: a watcher whose Monitor consumer has detached keeps its lease
# fresh AND drains the inbox, so the message is consumed and nobody sees it (TOR-425,
# detached-watcher drain). Every user-facing surface must therefore say ARMED / ACCEPTED,
# never "delivered" or "will receive".
#
# WHAT THIS PROVES, exactly:
#   It is a REGRESSION check over the known promise strings. It CANNOT prove no promise
#   exists — "promises" is an open set and no fixed pattern closes it. Closure came from a
#   one-time enumeration of every rendered surface, which is a review artifact, not a
#   command. Claiming more for this script than regression would be TOR-474's own defect
#   committed by its verification step.
#
# EXIT CODES — four, because "the corpus is wrong" is neither a pass nor a failure:
#   0  clean
#   1  a promise string is present (printed above the verdict)
#   2  the probe itself broke; nothing was concluded
#   3  THE CORPUS IS BROKEN — a surface rendered nothing, so silence proves nothing
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$HERE")"
CCSEND="$HERE/ccsend"
CCARM="$HERE/ccarm"

# The patterns are the SPECIFIC strings that were there before, not generic fragments.
#
# This matters and it is not tidiness: the first draft used the fragment `will receive`,
# which matched my own replacement text "who is armed (not who will receive)" — a
# DISCLAIMER — and reported FAIL at four sites that were correct. A fragment cannot tell a
# promise from its negation, which is the same "fix what PROMISES, keep what WARNS"
# distinction this ticket turns on, reappearing inside the check meant to enforce it.
# A regression check encodes the strings it is guarding against regressing to.
PROMISES='can receive right now|can receive now|can receive once|it arrives now'
PROMISES+='|arrives only if|only current truth|make THIS session reachable|delivered on arm'
PROMISES+='|sitting idle waiting|reach this session even|armed and reachable'
PROMISES+='|still receive\?|delivers messages between'

CORPUS=''

# Per-surface non-emptiness, NOT a global byte floor.
#
# A surface that fails to render contributes zero strings, and to a grep "nothing rendered"
# is indistinguishable from "nothing wrong" — the vacuous pass this ticket exists to remove.
# Per-surface because it NAMES the broken surface instead of reporting an aggregate, and
# because any global threshold is a fact about today's docs that rots as they grow.
emit() {
  local label="$1"; shift
  local out
  out="$("$@" 2>&1)"
  [ -n "$out" ] || { echo "CORPUS BROKEN — no output from: $label"; exit 3; }
  CORPUS+="$out"$'\n'
}

emit 'ccsend --help'   "$CCSEND" --help
emit 'ccsend --list'   "$CCSEND" --list
emit 'ccsend --self'   "$CCSEND" --self          # exit 1 here is a verdict, not a failure
emit 'ccarm --help'    "$CCARM"  --help
emit 'argparse error'  "$CCSEND" --timeout nope --ping
emit 'SKILL.md'        cat "$SKILL_DIR/SKILL.md"
emit 'README.md'       cat "$SKILL_DIR/README.md"

# Positive control: a string that MUST be present. If it is absent the corpus is wrong —
# every surface could have rendered an error banner and still contained no promise.
#
# The anchor must be VERSION-STABLE, i.e. present both before and after this ticket's edits.
# The first draft anchored on 'fleet inventory' — a string this ticket INTRODUCED — so
# running the script against the pre-fix text returned CORPUS BROKEN (3) instead of the
# promises-found (1) it should have. The control could only ever pass on an already-fixed
# tree, which makes it useless as the two-direction check it exists to be. Measured: old=1
# new=1 for the anchor below, against old=0 new=1 for the string it replaced.
ANCHOR='Encoding: Monitor turns each stdout LINE'
printf '%s' "$CORPUS" | grep -q "$ANCHOR" || {
  echo "CORPUS BROKEN — positive control absent ($ANCHOR); not asserting cleanliness"
  exit 3
}

printf '%s' "$CORPUS" | grep -nE "$PROMISES"; rc=$?
# `rc=$?` after a pipe is CORRECT here and is a deliberate exception to the usual
# "read statuses by redirect, never after a pipe" rule: grep is the LAST stage, so $? IS
# grep's status, which is exactly what is being read. Do not "fix" this into a redirect.
case $rc in
  0) echo 'FAIL — a promise string is present (listed above)'; exit 1 ;;
  1) echo 'clean — no known promise string in any rendered surface'; exit 0 ;;
  *) echo "PROBE BROKE — grep exited $rc; nothing was concluded"; exit 2 ;;
esac
