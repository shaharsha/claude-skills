# Fleet suite runner

`suite_slot.sh` delegates to a pinned installation of Torque's `scripts/suite_slot.py`.
Torque owns reservation policy and lifecycle tests; this repository owns only the adapter.
`acquire` is refused here: a shell from an earlier tool call does not own later work.
`claim` remains for explicitly registering already-running legacy work, not new launches.

## Coordinated installation

1. Verify the chosen Torque revision and run its `tests/structure/test_suite_slot.py` controls
   against a disposable registry. Also run `python3 -m unittest discover -s torque-orchestration
   -p test_suite_adapter.py` in this repository. Use the configured shared Python for Torque.
2. Inventory active callers, copied helpers and inlined briefs. Let existing suites finish;
   briefly stop new launches for the handoff if necessary. Do not clear leases or kill peer jobs.
3. Install the verified standalone `suite_slot.py` bytes in a stable revision-named runtime
   directory outside disposable worktrees. Record the source commit and SHA-256.
4. Write an untracked `suite-runner.json` beside the adapter with absolute `script`, `python`,
   `registry` paths and the script's `sha256`. No credentials belong in it. `TORQUE_SUITE_CONFIG`
   can choose an explicit configuration for a disposable test; it does not change policy.
5. Atomically install the adapter only once all old future writers/reapers are excluded.
   The old helper defaults to `~/.claude/torque-suite-slots`; do not expose process-group records
   there while any old helper can still reap them. Two registries must not independently admit
   work against the same host capacity. Preserve existing records and ownership.
6. Refresh dispatcher and future worker briefs. Already-running sessions do not automatically
   reload changed files. Observe a newly launched command, failure propagation, ownership and
   final cleanup before claiming adoption complete.

## Commands

From the intended Torque worktree, with its absolute interpreter and PYTHONPATH configured,
run `suite_slot.sh run --wait-seconds 60 4 -- <foreground command>`.
These numbers are operational examples, not measured capacity or latency guarantees.
All runner options precede the slot count. The command must remain in its owned process group;
backgrounding or daemonizing it is unsupported. The runner preserves command exit status and
reports incomplete cleanup. Do not pipe a Git push; verify the remote revision afterwards.

A registry override must agree with the installed configuration. `status` and `release` use the
same delegate as `run`; there is no fallback PID-only reaper. Direct pytest and unrelated hooks
remain outside cooperative admission unless separately wired. This migration does not alter
Torque's verification or merge requirements.

Rollback must preserve safe ownership and the matching instructions. Do not reinstall the old
PID-only helper over a registry containing new-format reservations.
