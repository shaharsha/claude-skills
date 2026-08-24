#!/usr/bin/env bash
# UserPromptSubmit: deliver the post-compaction re-seed block.
#
# WHY NOT SessionStart(compact): that event fires and the hook RUNS, but Claude
# Code does not inject its stdout into context (anthropics/claude-code#15174,
# closed as duplicate; reproduced here on 2.1.237 on 2026-08-24). The docs list
# UserPromptSubmit as one of only three events whose stdout IS injected, so the
# delivery leg moved here and PreCompact raises a flag for it to read.
#
# It emits NOTHING unless a compaction has happened since the last delivery, so
# the ordinary per-prompt cost is one file test.
set +e
DIR="$(cd "$(dirname "$0")" && pwd)"
FLAG="$DIR/.reseed-pending"

[ -f "$FLAG" ] || exit 0
rm -f "$FLAG" 2>/dev/null          # clear FIRST: a failure below must not re-emit forever

RESEED_LEG=userpromptsubmit "$DIR/reseed.sh" 2>/dev/null
exit 0
