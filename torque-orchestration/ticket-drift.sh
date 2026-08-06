#!/usr/bin/env bash
# ticket-drift.sh — does the CODE already contain what this ticket asks for?
#
# WHY THIS EXISTS. On 2026-08-05 two Sprint-1 tickets (TOR-230, TOR-234) were assigned to fresh
# sessions while already merged and sitting in Backlog. Both lanes caught it before branching; both
# spin-ups were wasted. The coordinator had a written three-step rule for exactly this and skipped it
# twice, because the check lived in prose and not in a command.
#
# WHAT IT IS NOT. This does not tell you a ticket is DONE. It tells you whether a commit *naming* the
# ticket is an ancestor of origin/develop. Those differ in both directions:
#   - a closing commit may never name its ticket   -> NO-COMMIT-NAMES-IT on finished work
#   - a ticket number may appear in an unrelated body -> a candidate that closes nothing
# Measured across nine tickets on 2026-08-05, `git log --grep` returned noise in BOTH directions.
# So this narrows what you must read by hand. It never replaces reading the done-when items against
# `git show origin/develop:<path>`.
#
# The verdicts are deliberately not two-valued, because "nothing found" and "not done" are different
# claims and collapsing them is the defect this script was written after.
set -uo pipefail

REPO="${TORQUE_REPO:-$HOME/Projects/torque}"
BASE="${TORQUE_BASE:-origin/develop}"

usage() {
  cat <<'USAGE'
usage:  ticket-drift.sh TOR-123 [TOR-456 ...]
        ticket-drift.sh --stdin        # one ticket id per line
        ticket-drift.sh --self-test    # prove the instrument can find a known-present ticket

env:    TORQUE_REPO (default ~/Projects/torque)   TORQUE_BASE (default origin/develop)

verdicts
  MERGED               a commit naming it IS an ancestor of the base ref
  IN-FLIGHT            a commit naming it exists but is NOT an ancestor (unmerged branch)
  NO-COMMIT-NAMES-IT   nothing found. THIS IS NOT "not done" — see the header.
USAGE
}

cd "$REPO" 2>/dev/null || { echo "ticket-drift: no repo at $REPO" >&2; exit 2; }

# Always measure against the remote, never the working tree. A checkout parked on another branch
# answers a true question about the wrong thing.
git fetch origin --quiet 2>/dev/null

git rev-parse --verify --quiet "$BASE" >/dev/null || {
  echo "ticket-drift: base ref '$BASE' does not resolve — nothing below would mean anything" >&2
  exit 2
}

SCANNED=$(git rev-list --count "$BASE" 2>/dev/null || echo 0)
if [ "$SCANNED" -lt 1 ]; then
  echo "ticket-drift: $BASE has 0 commits — the instrument is broken, not the backlog" >&2
  exit 2
fi

# A commit that CLOSES a ticket names it in its SUBJECT ("TOR-234: …", "TOR-253 + TOR-263: …",
# or a merge whose branch slug carries it). A commit that merely MENTIONS it in the body is usually
# another ticket deferring work TO it — which is good practice and poisons a naive verdict.
#
# Measured 2026-08-05: TOR-256 reported MERGED off three ancestors that were all TOR-231 commits
# saying "deferred to TOR-256", while TOR-256's own six commits sat unmerged on a branch. The rule
# "any naming commit is an ancestor -> MERGED" discards exactly the signal that distinguishes them.
# ── Two demotions, both reading DATA rather than prose (TOR-342) ────────────────────────────────
#
# A subject-naming ancestor is NOT automatically a close. Three real false-MERGEDs, measured:
#
#   docs(TOR-143): the deletion moves to TOR-175          -> Rule A   (scope names ANOTHER ticket)
#   docs(claude): two guard clauses beside the TOR-204 bullet (TOR-204)  -> Rule B  (docs-only)
#   docs(TOR-143)…                                        found on TOR-175; the other on TOR-204
#
# Rule A alone is NOT enough and the obvious generalisation is WORSE. Measured on origin/develop,
# these four share ONE structural shape — component scope, ticket in trailing parens:
#
#   fix(pins):    … (TOR-396)     scope=pins    REAL CLOSE
#   fix(vyb):     … (TOR-349)     scope=vyb     REAL CLOSE
#   feat(serve):  … (TOR-175)     scope=serve   REAL CLOSE
#   docs(claude): … (TOR-204)     scope=claude  NOT a close
#
# So "the scope must name the searched ticket" would suppress three genuine closes. The subject
# channel cannot separate them — which is this ticket's own thesis. The FILE LIST can.
#
# ⚠️ BIAS IS DELIBERATE AND ASYMMETRIC — do not "improve" this toward balance. A false MERGED
# CANCELS a ticket and the work is deleted with nobody told; a false NOT-MERGED costs one hand-check.
# Those errors are not comparable, so this under-reports MERGED on purpose.

# Echoes "scope" | "docs" | "" (keep it).
_demote_reason() {
  local sha="$1" subject="$2" num="$3" scope files
  # Rule A — conventional-commit scope naming a DIFFERENT ticket. `docs(TOR-143):` searched for
  # TOR-175 is TOR-143's commit announcing a deferral; it closes nothing.
  scope=$(printf '%s' "$subject" | sed -n 's/^[A-Za-z+]*(\([^)]*\)):.*/\1/p')
  if printf '%s' "$scope" | grep -qiE '^tor[-_]?[0-9]+$'; then
    local snum; snum=$(printf '%s' "$scope" | sed -n 's/[^0-9]*\([0-9]*\)/\1/p')
    [ -n "$snum" ] && [ "$snum" != "$num" ] && { echo scope; return; }
  fi
  # Rule B — the commit changes ONLY documentation. Reads what the commit TOUCHED, not what it says.
  files=$(git log -1 --format= --name-only "$sha" 2>/dev/null | grep -v '^$')
  # ⚠️ EMPTY means "cannot tell", never "all files are docs" — a merge commit lists no files under
  # --name-only, and "every one of zero files is a doc" is vacuously true. Vacuous truth here would
  # demote every merge commit and hide real closes, which is the failure direction that costs work.
  [ -z "$files" ] && { echo ""; return; }
  if ! printf '%s\n' "$files" | grep -qvE '(^|/)(CLAUDE\.md|README[^/]*|AGENTS\.md)$|^docs/|\.md$'; then
    echo docs; return
  fi
  echo ""
}

check_one() {
  local t="$1" num verdict s
  num="${t#TOR-}"
  # Matches TOR-256 / tor_256 / tor256, and the chained branch form me/tor-253-263-…
  local re="[Tt][Oo][Rr][-_ ]?${num}([^0-9]|$)|[-_]${num}([^0-9]|$)"

  local strong_anc="" weak_anc="" strong_out=0 n_s_anc=0 n_s=0 n_w_anc=0
  local docs_anc="" n_docs=0 scope_anc="" n_scope=0
  while IFS=$'\t' read -r sha subject; do
    [ -z "$sha" ] && continue
    local is_anc=0
    git merge-base --is-ancestor "$sha" "$BASE" 2>/dev/null && is_anc=1
    if printf '%s' "$subject" | grep -qE "$re"; then
      if [ "$is_anc" = 1 ]; then
        local why; why=$(_demote_reason "$sha" "$subject" "$num")
        # A demoted commit counts toward NEITHER tier. A deferral announcement is not evidence of a
        # merge, and it is not evidence of in-flight work either — so it must not silently become
        # IN-FLIGHT, which would be the same false confidence wearing a different word.
        case "$why" in
          scope) n_scope=$((n_scope+1)); scope_anc="$scope_anc ${sha:0:8}" ;;
          docs)  n_docs=$((n_docs+1));   docs_anc="$docs_anc ${sha:0:8}" ;;
          *)     n_s=$((n_s+1)); n_s_anc=$((n_s_anc+1)); strong_anc="$strong_anc ${sha:0:8}" ;;
        esac
      else
        n_s=$((n_s+1)); strong_out=$((strong_out+1))
      fi
    elif [ "$is_anc" = 1 ]; then
      n_w_anc=$((n_w_anc + 1)); weak_anc="$weak_anc ${sha:0:8}"
    fi
  done < <(git log "$BASE" --all -i --grep="TOR-\?${num}\b" --format='%H%x09%s' 2>/dev/null)

  if   [ "$n_s_anc" -gt 0 ]; then verdict="MERGED"
  elif [ "$n_s"     -gt 0 ]; then verdict="IN-FLIGHT"
  elif [ "$n_w_anc" -gt 0 ]; then verdict="MENTIONED-ONLY"
  else                            verdict="NO-COMMIT-NAMES-IT"; fi

  case "$verdict" in
    MERGED)   printf '%-10s %-20s %d subject-naming commit(s) merged:%s\n' "$t" "$verdict" "$n_s_anc" "$strong_anc"
              # A commit that ANNOUNCES work moving to a ticket names it in the SUBJECT exactly like
              # one that CLOSES it. Measured 2026-08-05 on TOR-175: verdict MERGED off
              # "docs(TOR-143): the deletion moves to TOR-175", while all five files its done-when
              # says to delete were still present.
              #
              # A fifth verdict does not fix this -- the two commits are indistinguishable by shape,
              # and only the done-when separates them. So the remedy is to SHOW the subjects and make
              # the reader look, rather than to invent a category the data cannot support.
              for _s in $strong_anc; do
                printf '%-10s %-20s   %s  %s\n' "" "" "$_s" "$(git log -1 --format=%s "$_s" 2>/dev/null | cut -c1-64)"
              done
              printf '%-10s %-20s READ THOSE SUBJECTS. One that says work MOVES to this ticket closes\n' "" ""
              printf '%-10s %-20s nothing. Confirm the done-when: git show %s:<path>\n' "" "" "$BASE" ;;
    IN-FLIGHT)printf '%-10s %-20s %d subject-naming commit(s) exist, NONE merged — unmerged branch\n' "$t" "$verdict" "$strong_out" ;;
    MENTIONED-ONLY)
              printf '%-10s %-20s %d merged commit(s) only MENTION it (another ticket deferring TO it):%s\n' \
                     "$t" "$verdict" "$n_w_anc" "$weak_anc"
              printf '%-10s %-20s NOT evidence of merge.\n' "" "" ;;
    *)        printf '%-10s %-20s %s\n' "$t" "$verdict" "(not evidence it is undone — read the done-when by hand)" ;;
  esac

  # ⚠️ ANNOUNCE every suppression. A demotion nobody can see is the failure that kills guards: it gets
  # rediscovered as a bug, and the fix is usually to delete the rule. Same principle as a third exit
  # code — "I could not answer" and "the answer is no" deserve different words, at the moment it
  # matters, to the person it matters to.
  if [ "$n_scope" -gt 0 ]; then
    printf '%-10s %-20s (%d commit(s) name this ticket but carry ANOTHER ticket in scope —\n' "" "" "$n_scope"
    printf '%-10s %-20s  a deferral announcement, not a close:%s)\n' "" "" "$scope_anc"
  fi
  if [ "$n_docs" -gt 0 ]; then
    printf '%-10s %-20s (%d docs-only commit(s) suppressed — IF THIS TICKET IS DOCUMENTATION\n' "" "" "$n_docs"
    printf '%-10s %-20s  WORK, hand-check them, they may be the real close:%s)\n' "" "" "$docs_anc"
  fi
}

case "${1:-}" in
  ""|-h|--help) usage; exit 0 ;;
  --self-test)
    # A control. If this cannot find a ticket we KNOW is in the base ref, every
    # NO-COMMIT-NAMES-IT below it is uninterpretable. Run it before believing a clean sweep.
    echo "ticket-drift: base=$BASE at $(git rev-parse --short "$BASE") · $SCANNED commits scanned"
    known=$(git log "$BASE" --oneline -i --grep='TOR-[0-9]' --format='%s' -1 2>/dev/null \
            | grep -oiE 'TOR-[0-9]+' | head -1)
    if [ -z "$known" ]; then
      echo "  FAIL — no commit in $BASE names any TOR- ticket. The grep cannot work here." >&2; exit 1
    fi
    echo "  control ticket found in history: $known"
    check_one "$(echo "$known" | tr '[:lower:]' '[:upper:]')"
    echo "  -> if that line does not say MERGED, do not trust this tool's negatives."
    exit 0 ;;
  --stdin)
    # NOT mapfile: that is a bash-4 builtin and macOS ships bash 3.2 (2007, GPLv2 —
    # Apple never shipped 4.x). `#!/usr/bin/env bash` finds it. Measured 2026-08-05:
    # 40 tickets in, `mapfile: command not found`, 0 out, and EXIT 0 -- which reads as
    # "nothing in your list is already merged". The tool built to stop a clean-looking
    # zero over an unscanned corpus produced exactly one.
    TICKETS=()
    while IFS= read -r _line; do
      [ -n "$_line" ] && TICKETS+=("$_line")
    done < <(grep -oiE 'TOR-[0-9]+' | tr '[:lower:]' '[:upper:]' | sort -u)
    ;;
  *) TICKETS=("$@") ;;
esac

# An empty ticket list is a BROKEN RUN, never a clean answer. Without this the loop
# below iterates zero times and the trailing "confirm each done-when" banner still
# prints, so the output looks like a completed sweep that found nothing.
if [ "${#TICKETS[@]}" -eq 0 ]; then
  echo "ticket-drift: NO TICKETS PARSED — this is a failure, not a clean sweep." >&2
  echo "  --stdin expects TOR-<n> tokens on stdin; the argument form takes them as args." >&2
  exit 2
fi

echo "ticket-drift: base=$BASE at $(git rev-parse --short "$BASE") · $SCANNED commits in history"
echo "ticket-drift: ${#TICKETS[@]} ticket(s) to check"
echo
for t in "${TICKETS[@]}"; do
  check_one "$(echo "$t" | tr '[:lower:]' '[:upper:]')"
done
echo
echo "MERGED lines are candidates for a status change, NOT proof of completeness —"
echo "confirm each done-when item with: git show $BASE:<path>"
