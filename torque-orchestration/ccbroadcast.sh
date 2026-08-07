#!/bin/bash
# ccbroadcast — send one message to every armed lane, then PROVE each one landed.
#
# WHY THIS EXISTS (2026-08-06). The orchestrator hand-rolled `for s in $LANES; do ccsend …`
# twice in ten minutes. Both times it reached ZERO of 28 lanes and both times it reported
# success, because **zsh does not word-split an unquoted scalar** — the loop ran ONCE with all
# 28 ids as a single "session id", ccsend rejected it, and stderr went to /dev/null.
#
# That exact trap is already documented in LANE-PREAMBLE §4 (`for s in $SPELLINGS` searching for
# one 14-word pattern). Knowing it did not prevent it. So the remedy is not a better loop, it is
# not writing the loop:
#
#   * `#!/bin/bash` — bash DOES word-split, and this file is never sourced by an interactive zsh
#   * the recipient list is an ARRAY, expanded "${arr[@]}"
#   * every send's exit status is captured INSIDE the invocation, never after a pipe
#   * and the run ends by reading each RECIPIENT'S OWN inbox directory for the message body
#
# The last one is the point. A send loop that prints a tick per iteration is not evidence any
# message arrived — `ccsend` exit 0 means "the target was armed and the message was spooled",
# which is ACCEPTANCE, not DELIVERY. This script verifies the artifact on the receiving side and
# EXITS NON-ZERO if any lane is missing it, so a partial broadcast cannot read as a whole one.
#
# usage:  ccbroadcast.sh --file <path>  [--to <id> ...]   # default: every armed lane except me
set -uo pipefail

CCSEND="$HOME/.claude/skills/working-with-other-sessions/scripts/ccsend"
MSGS="$HOME/.claude/mailbox/msgs"
SELF="$(grep -E '^SESSION_ID=' "$HOME/.claude/torque-orchestration/CURRENT-ORCHESTRATOR" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')"

FILE=""; declare -a EXPLICIT=()
while [ $# -gt 0 ]; do
  case "$1" in
    --file) FILE="$2"; shift 2;;
    --to)   EXPLICIT+=("$2"); shift 2;;
    *) echo "unknown arg: $1" >&2; exit 64;;
  esac
done
[ -n "$FILE" ] && [ -f "$FILE" ] || { echo "ccbroadcast: --file <path> is required and must exist" >&2; exit 64; }

# ⚠️ The fingerprint MUST be unique PER RUN, not per message.
#
# The first version of this script verified against the message's own first line. A lane caught
# why that is wrong within minutes: after ANY successful attempt, that line is in the recipient's
# directory forever — so a retry cannot tell "my send just landed" from "an earlier send landed",
# reports everyone missing, and sends again. They received the resume broadcast TWICE,
# byte-identical, and told me rather than ignoring it.
#
# Their diagnosis is the durable half: BOTH failures come from having no PER-RECIPIENT,
# PER-ATTEMPT result to check. The first loop reported success and delivered nothing; the second
# delivered twice. Same missing thing, opposite symptoms.
#
# So: stamp a run id into the copy that is actually sent, and verify THAT.
RUN_ID="bcast-$(date -u +%Y%m%dT%H%M%SZ)-$$"
SENT_COPY="$(mktemp -t ccbroadcast)"
cp "$FILE" "$SENT_COPY"
printf '\n<!-- %s -->\n' "$RUN_ID" >> "$SENT_COPY"
FINGERPRINT="$RUN_ID"
trap 'rm -f "$SENT_COPY"' EXIT
FILE="$SENT_COPY"

declare -a LANES=()
if [ ${#EXPLICIT[@]} -gt 0 ]; then
  LANES=("${EXPLICIT[@]}")
else
  while read -r sid; do
    [ -n "$sid" ] && [ "$sid" != "$SELF" ] && LANES+=("$sid")
  done < <("$CCSEND" --list 2>/dev/null | awk '/^📬 armed/ {print $3}')
fi
[ ${#LANES[@]} -gt 0 ] || { echo "ccbroadcast: no armed lanes found — refusing to report success" >&2; exit 3; }

echo "ccbroadcast: ${#LANES[@]} recipients, fingerprint: ${FINGERPRINT:0:44}…"

declare -a REFUSED=()
for sid in "${LANES[@]}"; do
  if "$CCSEND" "$sid" --file "$FILE" >/dev/null 2>&1; then :; else REFUSED+=("$sid"); fi
done

# VERIFY on the receiving side. This is the half a send loop cannot do.
declare -a MISSING=()
for sid in "${LANES[@]}"; do
  dir="$(ls -d "$MSGS/$sid"* 2>/dev/null | head -1)"
  if [ -n "$dir" ] && grep -rqF "$FINGERPRINT" "$dir" 2>/dev/null; then :; else MISSING+=("$sid"); fi
done

echo "  sent-accepted : $(( ${#LANES[@]} - ${#REFUSED[@]} )) / ${#LANES[@]}"
echo "  VERIFIED landed: $(( ${#LANES[@]} - ${#MISSING[@]} )) / ${#LANES[@]}"
[ ${#REFUSED[@]} -gt 0 ] && echo "  REFUSED (not armed): ${REFUSED[*]}"
[ ${#MISSING[@]} -gt 0 ] && echo "  ⚠️  NOT DELIVERED   : ${MISSING[*]}"

# A control: the fingerprint must NOT appear in a directory we did not send to. If it does, the
# verification is matching something other than this broadcast and its zeros mean nothing.
stray=0
for dir in "$MSGS"/*/; do
  s="$(basename "$dir" | cut -c1-8)"
  [ "$s" = "$SELF" ] && continue
  printf '%s\n' "${LANES[@]}" | grep -qx "$s" && continue
  grep -rqF "$FINGERPRINT" "$dir" 2>/dev/null && stray=$((stray+1))
done
echo "  control (stray matches, want 0): $stray"

[ ${#MISSING[@]} -eq 0 ] || exit 1
exit 0
