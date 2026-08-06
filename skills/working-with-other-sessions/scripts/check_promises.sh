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
emit 'ccsend --list'      0 "$CCSEND" --list
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
emit 'ccsend source'      0 cat "$CCSEND"
emit 'ccarm source'       0 cat "$CCARM"

# No prose "positive control" anchor here. The previous version grepped for a documentation
# sentence, which a legitimate later edit could rephrase — turning a correct tree into
# CORPUS BROKEN. Per-surface status validation above is the structural form of the same
# assertion and does not depend on any wording surviving.

hits=0
for s in "${FORBIDDEN[@]}"; do
  if printf '%s' "$CORPUS" | grep -qF -- "$s"; then
    echo "FORBIDDEN STRING PRESENT: $s"
    hits=$((hits + 1))
  fi
done

case $hits in
  0) echo 'clean — no replaced string in any rendered surface or scanned source'; exit 0 ;;
  *) echo "FAIL — $hits forbidden string(s) present"; exit 1 ;;
esac
