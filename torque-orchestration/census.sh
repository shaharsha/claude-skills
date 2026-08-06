#!/usr/bin/env bash
# census.sh — what is the state of the sprint RIGHT NOW, derived from artifacts.
#
# WHY THIS EXISTS. The orchestrator session holds the queue, the approvals in flight, and which lane
# owns what — and none of that is written down anywhere durable. On 2026-08-05 the orchestrator was
# one context window away from taking all of it with it. A handover document does not solve this:
# a handover is written by a session that is dying, so it is stale from the moment it is saved, and
# its staleness is invisible to whoever reads it next.
#
# So this asks the ARTIFACTS instead. Everything below is observed at run time: GitHub for PRs and CI,
# the mailbox for who is alive, git for what landed. A successor runs this and knows the state without
# trusting a word from its predecessor.
#
# WHAT IT CANNOT SEE, and you must ask the lanes for:
#   - unpushed work in a lane's worktree (invisible to every git question you can ask)
#   - a plan waiting on approval that never became a PR
#   - which lane owns which ticket, if they have not opened a PR yet
#   - anything on Shahar's desk
# That list is the reason step 4 of /lead is "ask every armed lane", not "read this output".
set -uo pipefail

REPO="${TORQUE_REPO:-$HOME/Projects/torque}"
GH_REPO="${TORQUE_GH_REPO:-Torque-Capital/torque}"
CCSEND="$HOME/.claude/skills/reading-session-transcripts/scripts/ccsend"

cd "$REPO" 2>/dev/null || { echo "census: no repo at $REPO" >&2; exit 2; }

echo "=================================================================="
echo " TORQUE SPRINT CENSUS — $(date -u '+%Y-%m-%d %H:%M:%SZ')"
echo " Everything below is MEASURED NOW. Nothing is recalled."
echo "=================================================================="
echo

# ---------------------------------------------------------------- git
git fetch origin --quiet 2>/dev/null
DEV=$(git rev-parse origin/develop 2>/dev/null)
MAIN=$(git rev-parse origin/main 2>/dev/null)
if [ -z "$DEV" ]; then
  echo "census: origin/develop does not resolve — the instrument is broken, not the sprint." >&2
  exit 2
fi
echo "## BRANCHES"
printf '  develop  %s  %s\n' "${DEV:0:8}" "$(git log -1 --format=%s "$DEV" | cut -c1-56)"
printf '  main     %s  develop is %s commits ahead of it\n' "${MAIN:0:8}" "$(git rev-list --count "$MAIN..$DEV" 2>/dev/null)"
echo

# ---------------------------------------------------------------- PRs
# Note the deliberate absence of a pipe into anything whose exit status we then read.
echo "## OPEN PRs  (behind-count is against develop as of this run)"
PR_JSON=$(gh pr list --repo "$GH_REPO" --state open --limit 50 \
            --json number,title,isDraft,headRefOid,headRefName,mergeStateStatus 2>/dev/null)
if [ -z "$PR_JSON" ] || [ "$PR_JSON" = "[]" ]; then
  echo "  (none open — verify that is real: 'gh auth status' and re-run, because an auth"
  echo "   failure and an empty queue produce the SAME output here)"
else
  # No backslashes inside the f-strings: that is a SyntaxError before Python 3.12, and the first
  # version of this script hit it. What made it worth a comment is that the traceback printed, the
  # PR section came back empty, every other section rendered normally, and the script EXITED 0 --
  # a census that silently omits the entire queue and reports success. Hence the row count below.
  echo "$PR_JSON" | python3 -c '
import json,sys,subprocess
prs=json.load(sys.stdin); dev=sys.argv[1]; n=0
for p in sorted(prs,key=lambda x:x["number"]):
    h=p["headRefOid"]
    r=subprocess.run(["git","rev-list","--count","%s..%s"%(h,dev)],capture_output=True,text=True)
    behind=r.stdout.strip() or "?"
    d="DRAFT " if p["isDraft"] else "      "
    print("  #%-4s %s%s  behind %3s  %-9s %s" % (p["number"],d,h[:8],behind,p["mergeStateStatus"],p["title"][:52]))
    n+=1
if n==0:
    print("census: PR list parsed to ZERO rows — a crash and an empty queue look identical here.",
          file=sys.stderr)
    sys.exit(3)
' "$DEV" || {
    echo
    echo "  ^^ THE PR SECTION FAILED. This is NOT an empty queue." >&2
    echo "     Every other section above rendered fine, which is what makes this easy to miss." >&2
    exit 3
  }
fi
echo
echo "  behind 0 = ready to approve on. Anything else must re-merge FIRST — an approval"
echo "  is a claim about a diff against a base, and it expires when either moves."
echo

# ---------------------------------------------------------------- merged today
TODAY=$(date -u '+%Y-%m-%d')
N_MERGED=$(gh pr list --repo "$GH_REPO" --state merged --limit 60 --json mergedAt \
             --jq "[.[]|select(.mergedAt>\"${TODAY}T00:00:00Z\")]|length" 2>/dev/null)
echo "## MERGED TODAY: ${N_MERGED:-?}"
echo

# ---------------------------------------------------------------- lanes
echo "## LIVE SESSIONS"
if [ -x "$CCSEND" ]; then
  ARMED=$("$CCSEND" --list 2>/dev/null | grep -c '📬 armed')
  echo "  armed and reachable: ${ARMED:-0}"
  "$CCSEND" --list 2>/dev/null | grep '📬 armed' | sed 's/^/  /'
  if [ "${ARMED:-0}" -eq 0 ]; then
    echo "  ^ ZERO armed sessions is a finding, not a quiet sprint. Either everyone is"
    echo "    genuinely gone, or ccsend is broken and you are about to conclude the first."
  fi
else
  echo "  ccsend not found at $CCSEND — cannot see any lane. This is a BROKEN INSTRUMENT,"
  echo "  not an empty roster." >&2
fi
echo

cat <<'TAIL'
## WHAT THIS OUTPUT CANNOT TELL YOU

  - unpushed work in a lane's worktree — invisible to every git question that exists
  - a plan waiting on your approval that never became a PR
  - which lane owns which ticket before they open one
  - anything on Shahar's desk

Ask the lanes. A census of artifacts plus a round of "what are you on, what is blocked on
me, what have you parked" is the whole handover — and unlike a document, both halves are
true at the moment you read them.
TAIL
