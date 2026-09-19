"""Private fleet entry point; all reservation policy belongs to Torque's runner."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Existing acquire-in-one-tool-call recipes cannot prove that their shell owner
    # outlives the next call. Make them fail with the supported replacement.
    if argv[:1] == ['acquire']:
        print('REFUSED: launch the foreground command with suite_slot.sh run '
              '[--wait-seconds N] MAX -- COMMAND; do not acquire in a separate tool shell.',
              file=sys.stderr)
        return 64
    try:
        config_path = Path(os.environ.get('TORQUE_SUITE_CONFIG',
                                         Path(__file__).with_name('suite-runner.json')))
        config = json.loads(config_path.read_text())
        script = Path(config['script'])
        interpreter = Path(config['python'])
        registry = Path(config['registry'])
        if not all(path.is_absolute() for path in (script, interpreter, registry)):
            raise ValueError('runtime, interpreter and registry paths must be absolute')
        expected = config['sha256']
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError('a pinned runtime SHA-256 is required')
        if hashlib.sha256(script.read_bytes()).hexdigest() != expected:
            raise ValueError('installed Torque runner changed; verify and reinstall its pinned revision')
        if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
            raise ValueError('configured Python interpreter is unavailable')
        override = os.environ.get('TORQUE_SUITE_SLOTS')
        if override and Path(override).expanduser().resolve() != registry.resolve():
            raise ValueError('registry override disagrees with the coordinated fleet configuration')
        env = dict(os.environ, TORQUE_SUITE_SLOTS=str(registry))
        os.execve(str(interpreter), [str(interpreter), str(script), *argv], env)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Do not echo file contents, credentials or arbitrary JSON fields.
        detail = str(exc) if type(exc) is ValueError else type(exc).__name__
        print(f'REFUSED: suite runner configuration/runtime unavailable ({detail}); '
              'follow SUITE-RUNNER.md before adoption. No reservation was changed.', file=sys.stderr)
        return 64


if __name__ == '__main__':
    raise SystemExit(main())
