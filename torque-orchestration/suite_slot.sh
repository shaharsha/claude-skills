#!/bin/bash
# Fleet suite serializer. Atomic slot acquisition via mkdir (POSIX-atomic; works on macOS).
# MOVED 2026-09-17 from /private/tmp/torque-suite-slots/ — /private/tmp was WIPED during an
# account migration and took this script and every slot record with it. Slots now live under ~/.claude.
#
#   suite_slot.sh acquire <max_slots> <owner_pid>   -> prints SLOT=<path>
#   suite_slot.sh claim   <max_slots> <owner_pid>   -> same, but SKIPS the start bar; ONLY for a suite
#                                                      that is ALREADY RUNNING and needs re-registering
#   suite_slot.sh release <slot_path> [owner_pid]   -> frees a slot
#   suite_slot.sh status                            -> held slots + the live Postgres reading
#
# EXIT CODES — a retry loop must treat these differently:
#   0  got the slot, go
#   1  WAIT and retry (full, or over the start bar)
#   2  PROBE-FAILED — cannot read pg_stat_activity. FATAL, not a wait: folding it into the retry
#      branch turns a persistent probe failure into an infinite silent wait.
#  64  FATAL usage error (missing/dead owner pid). NEVER retry.
#
# OWNER_PID IS REQUIRED AND MUST OUTLIVE THIS SCRIPT. Use a LAUNCHER script that lives for the run:
#
#     while :; do
#       OUT=$(suite_slot.sh acquire 4 $$); rc=$?          # NEVER pipe this into sed
#       [ "$rc" = 0 ] && { SLOT=$(printf '%s' "$OUT" | sed -n 's/^SLOT=\([^ ]*\).*/\1/p'); break; }
#       [ "$rc" = 64 ] && { echo "FATAL 64: $OUT"; exit 64; }
#       [ "$rc" = 2 ]  && { echo "FATAL 2: $OUT"; exit 2; }
#       sleep 120
#     done
#     [ -n "$SLOT" ] || { echo "acquire returned 0 with no SLOT= — refusing to run"; exit 64; }
#     trap 'suite_slot.sh release "$SLOT" $$' EXIT INT TERM
#     <suite>
#
#   🔴 DO NOT PIPE `acquire` INTO `sed`: a pipeline carries the LAST stage's status, so a FULL (rc 1)
#   reads as 0 and the suite runs OFF-LEDGER with an empty $SLOT. Measured 2026-09-17.
#
# START: client backends < 70 of 100 AND a free slot.
# ABANDON: only on a real error in your suite log, or backends >= 95.
set -u
ROOT="${TORQUE_SUITE_SLOTS:-$HOME/.claude/torque-suite-slots}"
DIR="$ROOT/slots"
mkdir -p "$DIR"
PSQL_DSN="${TORQUE_SLOT_DSN:-postgresql://$USER@localhost:5432/postgres}"
GRACE=90

backends() {
  psql "$PSQL_DSN" -tAc \
    "SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend'" 2>/dev/null
}
now() { date -u +%s; }

reap() {
  for s in "$DIR"/slot* "$DIR"/over-*; do
    [ -d "$s" ] || continue
    pid=$(cat "$s/pid" 2>/dev/null)
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then continue; fi
    born=$(cat "$s/born" 2>/dev/null || echo 0)
    age=$(( $(now) - born ))
    if [ -z "${pid:-}" ] && [ "$age" -lt "$GRACE" ]; then continue; fi
    rm -rf "$s"
  done
}

case "${1:-}" in
  acquire|claim)
    MODE="$1"; MAX="${2:-}"; OWNER="${3:-}"
    if [ -z "$MAX" ] || [ -z "$OWNER" ]; then
      echo "REFUSED: usage: acquire <max_slots> <owner_pid>  (owner must OUTLIVE this script)"; exit 64
    fi
    if ! kill -0 "$OWNER" 2>/dev/null; then
      echo "REFUSED: owner pid $OWNER is not alive"; exit 64
    fi
    reap
    b=$(backends)
    if [ -z "$b" ]; then echo "PROBE-FAILED: cannot read pg_stat_activity — this is NOT a pass"; exit 2; fi
    if [ "$MODE" = "acquire" ] && [ "$b" -ge 70 ]; then
      echo "OVER-BAR: $b client backends >= 70; do not start"; exit 1
    fi
    for i in $(seq 1 "$MAX"); do
      if mkdir "$DIR/slot$i" 2>/dev/null; then
        now > "$DIR/slot$i/born"; pwd > "$DIR/slot$i/cwd"; echo "$OWNER" > "$DIR/slot$i/pid"
        echo "SLOT=$DIR/slot$i BACKENDS=$b OWNER=$OWNER"; exit 0
      fi
    done
    if [ "$MODE" = "claim" ]; then
      o="$DIR/over-$OWNER"; mkdir -p "$o"
      now > "$o/born"; pwd > "$o/cwd"; echo "$OWNER" > "$o/pid"
      echo "SLOT=$o BACKENDS=$b OWNER=$OWNER OVERFLOW=yes (cap $MAX already held)"; exit 0
    fi
    echo "FULL: $MAX slots held, $b backends; wait and retry"; exit 1
    ;;
  release)
    SLOT="${2:-}"; CLAIMED_BY="${3:-}"
    [ -z "$SLOT" ] && { echo "REFUSED: usage: release <slot_path> [owner_pid]"; exit 64; }
    [ -d "$SLOT" ] || { echo "GONE=$SLOT (already released or reaped)"; exit 0; }
    owner=$(cat "$SLOT/pid" 2>/dev/null)
    if [ -n "${owner:-}" ] && kill -0 "$owner" 2>/dev/null \
       && [ "$owner" != "${CLAIMED_BY:-}" ] && [ "$owner" != "$PPID" ] && [ "$owner" != "$$" ]; then
      echo "REFUSED: $SLOT is held by LIVE pid $owner, not you. Not releasing."; exit 64
    fi
    rm -rf "$SLOT" && echo "RELEASED=$SLOT"
    ;;
  status)
    reap
    echo "BACKENDS=$(backends)"
    for s in "$DIR"/slot* "$DIR"/over-*; do
      [ -d "$s" ] || continue
      pid=$(cat "$s/pid" 2>/dev/null); alive=no; kill -0 "${pid:-0}" 2>/dev/null && alive=yes
      # `cwd` is where ACQUIRE was called from, which is NOT necessarily the tree under test — a launcher
      # can cd afterwards (measured 2026-09-17: four slots all recorded one worktree while their pytest
      # ran in four others). The live directory of the owner's youngest pytest child is the real subject.
      live=""; if [ "$alive" = yes ]; then
        for c in $(pgrep -P "$pid" 2>/dev/null); do
          case "$(ps -o args= -p "$c" 2>/dev/null)" in *pytest*) live=$(lsof -a -p "$c" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p');; esac
        done
        [ -z "$live" ] && live=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
      fi
      echo "HELD $s pid=${pid:-none} alive=$alive running_in=${live:-?} acquired_from=$(cat "$s/cwd" 2>/dev/null)"
    done
    ;;
  *) echo "usage: suite_slot.sh acquire <max> <owner_pid> | claim | release <slot> | status"; exit 64 ;;
esac
