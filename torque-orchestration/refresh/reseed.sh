#!/usr/bin/env bash
# SessionStart(compact): emit a short factual block so the post-compaction
# context knows what this session is and which documents govern it.
# The governing documents total ~550 KB and CANNOT be emitted here (hook output
# is capped at 10,000 chars), so this names them and carries the live state.
set +e

# Log every invocation. The caller names itself in RESEED_LEG so the log can
# separate "the SessionStart leg ran but its stdout was dropped" from "the
# SessionStart leg never ran at all" - different faults, different fixes.
printf "%s leg=%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${RESEED_LEG:-sessionstart}" \
  >> "$(dirname "$0")/fired.log" 2>/dev/null

cat <<'EOF'
This session is the Torque Sprint-1 DISPATCHER (/dispatch). Compaction has just run.

Its governing documents are NOT in context after compaction and must be read before
acting on anything they cover. They are, with why each matters:

  CLAUDE.md (repo root, ~286 KB) — operating invariants. Contains rules that are
    load-bearing and routinely mis-remembered: never re-transcribe a count (query it
    fresh), ask git about the ARTIFACT not the checkout, redirect never pipe, -n 4 not
    -n auto, never re-capture the frozen baseline, prod applies are Shahar's.

  docs/v2-architecture/2026-07-12-torque-v2-technical-design.md — §8 (migration scope:
    all 54 non-LX slots, no cut-line) and §15 item 8 + its 2026-08-22 addendum (TOR-734:
    the three DECISION pages become authored HTML declaring a computation ref; the frame
    may NOT call the API).

  docs/v2-architecture/2026-07-08-torque-v2-agentic-platform-design.md — §3 (the
    2026-08-10 acceptance bar: a VALUE difference refuses permanently, a RENDERING
    difference needs per-slot human sign-off) and §10 item 7.

  ~/.claude/commands/dispatch.md — this seat's own definition. THE DISPATCHER RULES ON
    NOTHING: not design, not plans, not code, not merges, and no Terraform apply of any
    kind. Those are /adjudicate, spawned fresh, one ruling per invocation.

  ~/.claude/commands/lead.md — the seat split and the authority boundary.

  ~/.claude/torque-orchestration/LANE-PREAMBLE.md (~1615 lines) — §1 is the
    AUTHORISATION ROOT; §4 the instrument rules; §5 facts-or-flag verbatim.

  Linear: project "Sprint 1 — Platform generisation" — read In Progress and the Urgent/
    High backlog. Ticket bodies AND comments; get_issue alone returns a stale world.

Standing facts that survive compaction badly and have each been got wrong at least once:
  - This seat holds NO merge, ruling or apply authority. Spawn /adjudicate.
  - PROD is Shahar's every time. DEV Terraform applies are /adjudicate's, never this seat's.
  - A count written in prose rots. Re-measure before citing any number.
EOF
LIVE="$HOME/.claude/torque-orchestration/refresh/live-state.md"
if [ -f "$LIVE" ]; then echo; cat "$LIVE"; fi
exit 0
