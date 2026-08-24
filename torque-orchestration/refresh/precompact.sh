#!/usr/bin/env bash
# PreCompact: dump live, mechanically-knowable state so the post-compaction
# re-seed carries CURRENT facts rather than whatever was true hours ago.
# Never fails the compaction: every command is guarded, and we always exit 0.
set +e
OUT="$HOME/.claude/torque-orchestration/refresh/live-state.md"
R="$HOME/Projects/torque"
{
  echo "## Live state, captured at compaction ($(date -u '+%Y-%m-%dT%H:%MZ'))"
  echo
  git -C "$R" fetch -q origin 2>/dev/null
  echo "- origin/develop: $(git -C "$R" rev-parse --short origin/develop 2>/dev/null || echo unknown)"
  echo "- origin/main:    $(git -C "$R" rev-parse --short origin/main 2>/dev/null || echo unknown)"
  echo "- main is behind develop by: $(git -C "$R" rev-list --count origin/main..origin/develop 2>/dev/null || echo unknown) commits"
  echo
  echo "### Open PRs (torque)"
  gh pr list --repo Torque-Capital/torque --state open \
     --json number,title -q '.[] | "- #\(.number) \(.title[0:70])"' 2>/dev/null | head -12 || echo "- (unavailable)"
  echo
  echo "### Open PRs (torque-infra)"
  gh pr list --repo Torque-Capital/torque-infra --state open \
     --json number,title -q '.[] | "- #\(.number) \(.title[0:70])"' 2>/dev/null | head -6 || echo "- (unavailable)"
  echo
  echo "### Sprint 1 — In Progress"
  echo "- (read from Linear: project 'Sprint 1 — Platform generisation')"
} > "$OUT" 2>/dev/null

# Raise the flag the UserPromptSubmit leg reads. SessionStart(compact) stdout is
# NOT injected into context (Claude Code bug #15174 - the hook RUNS, the stdout is
# dropped), so delivery moved to UserPromptSubmit, one of only three events the
# docs list as injecting stdout into context.
touch "$(dirname "$0")/.reseed-pending" 2>/dev/null

exit 0
