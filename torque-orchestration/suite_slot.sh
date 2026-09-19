#!/bin/sh
# Delegate to the pinned Torque runner. Configuration and coordinated installation:
# see SUITE-RUNNER.md. No local reaper or implicit shared-registry default.
exec "${TORQUE_SUITE_PYTHON:-python3}" "$(dirname "$0")/suite_adapter.py" "$@"
