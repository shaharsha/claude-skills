# Fleet suite runner

`suite_slot.sh` delegates to a pinned installation of Torque's `scripts/suite_slot.py`.
Torque owns reservation policy and lifecycle tests; this repository owns only the adapter.
`acquire` is refused here: a shell from an earlier tool call does not own later work.
`claim` remains for explicitly registering already-running legacy work, not new launches.

## Coordinated installation

Integrate [Torque #1053](https://github.com/Torque-Capital/torque/pull/1053) before choosing the runtime for [this adapter, #26](https://github.com/shaharsha/claude-skills/pull/26). Install from a verified clean revision containing that change; an earlier installation must be reverified and replaced at the coordinated handoff. A GitHub merge alone does not update a machine.

Resolve the complete installed path before updating a local checkout: `~/.claude/torque-orchestration` may itself be a symlink, even when `suite_slot.sh` is a regular file. Updating that checkout can immediately replace the live helper. Stage the runtime, configuration and adapter in a separate checkout/directory first. Do not pull the live linked checkout until the exclusion and installation steps below are ready.

1. Verify the chosen Torque revision and run its `tests/structure/test_suite_slot.py` controls
   against a disposable registry. Also run `python3 -m unittest discover -s torque-orchestration
   -p test_suite_adapter.py` in this repository. Use the configured shared Python for Torque.
2. Inventory active callers, copied helpers and inlined briefs. Let existing suites finish;
   briefly stop new launches for the handoff if necessary. Do not clear leases or kill peer jobs.
3. Install the verified standalone `suite_slot.py` bytes in a stable revision-named runtime
   directory outside disposable worktrees. Record the source commit and SHA-256.
4. Write an untracked `suite-runner.json` beside the adapter with absolute `script`, `python`,
   `registry` paths, the script's `sha256`, and the full verified `source_commit` object ID.
   Derive the commit and digest from the same clean source checkout; the adapter validates their
   format and installed bytes, not the truth of an installer's commit declaration.
   No credentials belong in it. `TORQUE_SUITE_CONFIG`
   can choose an explicit configuration for a disposable test; it does not change policy.
5. Atomically install the adapter only once all old future writers/reapers are excluded.
   The old helper defaults to `~/.claude/torque-suite-slots`; do not expose process-group records
   there while any old helper can still reap them. Two registries must not independently admit
   work against the same host capacity. Preserve existing records and ownership.
6. Refresh dispatcher and future worker briefs. Already-running sessions do not automatically
   reload changed files. Observe a newly launched command, failure propagation, ownership and
   final cleanup before claiming adoption complete.

Before resuming launches, run `suite_slot.sh provenance` from the intended Torque checkout.
This command validates the installation and reports its configured source commit/digest and
checkout comparison as MATCH, DIFFERENT or UNKNOWN, without executing the runner or touching
reservations. Output always includes `source_commit_verified: false`: the commit is an installer
declaration, even when the measured runner bytes MATCH. It compares the nearest checkout's
`scripts/suite_slot.py` bytes, including from
a nested directory or linked worktree. It does not use inherited Git environment variables.
Normal delegation warns on DIFFERENT or UNKNOWN and still uses the verified pinned runtime.
DIFFERENT means review/reinstall may be needed, not that the installed version is necessarily
older; UNKNOWN means the source comparison could not be made. A newer commit with identical
runner bytes still matches. Neither ancestry nor a digest alone establishes compatibility.

Fleet adoption still requires disposition of [TOR-1334](https://linear.app/torque-capital/issue/TOR-1334), not merely merging this adapter. Torque's testing guide and `docs/instruction-migration/push-gate-review.md` explain generation checks and the remaining conservative handling of unverifiable leaderless groups. Never resolve such ambiguity by expiring live work or clearing another session's reservation. The observed launcher handoff and representative concurrent-work acceptance remain required.

## Commands

From the intended Torque worktree, with its absolute interpreter and PYTHONPATH configured,
run `suite_slot.sh run --units 1 --wait-seconds 60 4 -- <single-worker command>`.
Declare the actual worker demand: four workers need `--units 4 4`. The final positional
number is the eligible slot range, not the worker demand. `run 1` is slot1-only,
can block FIFO while other slots are free, and is not host-wide exclusivity.
A shared-resource lock is a separate requirement.

After installing a verified Torque runner that supports `run-shared`, the default
four-unit pool also accepts `suite_slot.sh run-shared --units 1 -- <single-worker command>`;
a four-worker diagnostic uses `--units 4`. This mode is not the private-10 profile.
Check the pinned runtime's help before using the new mode; merging its source does
not update the installed runtime. Until coordinated installation, retain the explicit
`run --units 1 4` form. Refresh copied future briefs; leave live commands and leases alone.

These numbers are operational examples, not measured capacity or latency guarantees.
Legacy runner options precede the slot count; named-mode options precede `--`. The command must remain in its owned process group;
backgrounding or daemonizing it is unsupported. The runner preserves command exit status and
reports incomplete cleanup. Do not pipe a Git push; verify the remote revision afterwards.

A registry override must agree with the installed configuration. `status` and `release` use the
same delegate as `run`; there is no fallback PID-only reaper. Direct pytest and unrelated hooks
remain outside cooperative admission unless separately wired. This migration does not alter
Torque's verification or merge requirements.

Rollback must preserve safe ownership and the matching instructions. Do not reinstall the old
PID-only helper over a registry containing new-format reservations.

## Handoff to Torque's selected-feedback policy

This section applies only after Torque's reviewed selected-local policy is merged; it does not activate that policy or install this adapter. Read the lane's current `docs/agents/testing.md` and `docs/agents/workflow.md` before constructing its verification brief.

The supported `python -m scripts.feedback` command and migrated push hook already own execution admission. Do not wrap feedback or a migrated push in `suite_slot.sh run`: a nested cache miss refuses, and an extra reservation can consume capacity without useful work. Configure their TORQUE_SUITE_SLOTS to the same coordinated registry as the adapter. Use affected-test declarations for normal changes. For eligible shared or unknown scope, choose `--defer-full-to-ci` with explicit affected tests; complete required CI still runs before merge. Reserve `--full` for deliberately requested full local diagnostics, not as the default for every lane. Raw foreground diagnostic commands still need the adapter's ownership wrapper.

A selected local pass permits PR preparation, not merging. Preserve complete required CI, reviewed head/base, current-base verification and independent remote-push proof. Refresh future briefs at the coordinated handoff; existing copied instructions do not update themselves. Never introduce another registry to make a blocked lane run.

## Private PostgreSQL and FIFO adoption

Torque's current testing guide owns the exact environment and command contract.
After the corresponding implementation is merged into the lane, configure
`TORQUE_TEST_POSTGRES=private` and a validated PostgreSQL18 binary directory for
DB-dependent feedback; clear conflicting connection overrides as that guide requires.
Do not point tests at RDS or a protected restore. Configure the same environment for
the feedback invocation and its normal push hook so valid evidence can be reused.

The optional `TORQUE_FEEDBACK_PROFILE=private-10` widens the shared admission range.
Do not enable it while older full callers still reserve only four units. Coordinate
all future callers and copied briefs first, let admitted jobs drain, and pin the merged
FIFO runner. Every full diagnostic must reserve the entire configured range.
Use supported feedback for ordinary verification; a raw diagnostic wrapper must
declare its capacity demand with `--units` rather than silently reserve one slot for
a multi-worker full suite. Never wrap feedback in another reservation.

FIFO prevents new selected arrivals overtaking a queued full diagnostic; it does not
make full work fast or promise sub-minute results behind it. Observe the next actual
conforming command and cleanup from each resumed session before claiming adoption.
A provenance MATCH alone cannot prove copied briefs or worktree-native runners changed.

## Waiting versus execution

Updated Torque feedback results retain fresh invocation totals and admission timing.
Read `timing.total_seconds` and `timing.admission.queue_seconds` separately; execution
includes process-group drain/cleanup, and total excludes interpreter/import startup
and the final result write/print. Cache hits have a fresh total and no admission record.
Missing timing in an older runtime is unavailable, not zero waiting. These diagnostics
do not replace the actual process status or invocation-result verifier in Torque's guide.
