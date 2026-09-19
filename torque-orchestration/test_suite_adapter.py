"""Adapter controls using disposable scripts/registries, never the live fleet."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.script = self.root / 'runner.py'
        self.script.write_text('import os,sys,json\n'
                               'print(json.dumps([sys.argv[1:],os.environ["TORQUE_SUITE_SLOTS"],os.getcwd()]))\n'
                               'raise SystemExit(23)\n')
        self.config = self.root / 'config.json'
        self.data = {'script':str(self.script), 'python':sys.executable,
                     'registry':str(self.root / 'slots'),
                     'sha256':hashlib.sha256(self.script.read_bytes()).hexdigest()}
        self.config.write_text(json.dumps(self.data))
        self.env = {k:v for k,v in os.environ.items()
                    if k not in ('TORQUE_SUITE_CONFIG','TORQUE_SUITE_SLOTS','TORQUE_SUITE_PYTHON')}
        self.env.update(TORQUE_SUITE_CONFIG=str(self.config), TORQUE_SUITE_PYTHON=sys.executable)

    def run_adapter(self, *args):
        return subprocess.run([str(HERE / 'suite_slot.sh'), *args], env=self.env,
                              cwd=self.root, text=True, capture_output=True, timeout=10)

    def test_delegates_all_supported_verbs_and_preserves_status_arguments_and_cwd(self):
        for args in [('run','--wait-seconds','0','4','--','echo','a b'),
                     ('claim','4',str(os.getpid())),('release','some slot',str(os.getpid())),
                     ('status',),('--help',)]:
            with self.subTest(args=args):
                result=self.run_adapter(*args)
                self.assertEqual(result.returncode,23,result.stderr)
                self.assertEqual(json.loads(result.stdout),
                                 [list(args),self.data['registry'],str(self.root.resolve())])

    def test_old_acquire_recipe_is_refused_before_any_runner_exec(self):
        result=self.run_adapter('acquire','4',str(os.getpid()))
        self.assertEqual(result.returncode,64)
        self.assertIn('foreground command',result.stderr)
        self.assertEqual(result.stdout,'')
        self.assertFalse((self.root/'slots').exists())

    def test_unconfigured_missing_corrupt_and_changed_runtime_refuse(self):
        for change in ('missing','malformed','digest','relative','python'):
            with self.subTest(change=change):
                data=dict(self.data)
                if change=='missing':self.config.unlink(missing_ok=True)
                elif change=='malformed':self.config.write_text('not json')
                else:
                    data[{'digest':'sha256','relative':'registry','python':'python'}[change]] = {
                        'digest':'0'*64,'relative':'relative','python':'/missing/python'}[change]
                    self.config.write_text(json.dumps(data))
                result=self.run_adapter('status')
                self.assertEqual(result.returncode,64)
                self.assertEqual(result.stdout,'')
                self.assertFalse((self.root/'slots').exists())

    def test_registry_override_cannot_create_a_second_budget(self):
        self.env['TORQUE_SUITE_SLOTS']=str(self.root/'different')
        self.assertEqual(self.run_adapter('status').returncode,64)
        self.env['TORQUE_SUITE_SLOTS']=self.data['registry']
        self.assertEqual(self.run_adapter('status').returncode,23)


def validate_brief_guidance(runner, dispatcher):
    required = (
        (runner, "only after Torque's reviewed selected-local policy is merged"),
        (runner, 'Do not wrap feedback or a migrated push in `suite_slot.sh run`'),
        (runner, 'same coordinated registry as the adapter'),
        (runner, 'A selected local pass permits PR preparation, not merging.'),
        (dispatcher, 'Verification policy belongs to those repository guides'),
        (dispatcher, 'do not wrap them in another slot command'),
        (dispatcher, 'complete CI and the reviewed current head/base remain required'),
    )
    for body, clause in required:
        assert clause in body, clause


class BriefGuidanceTests(unittest.TestCase):
    def test_current_routes_and_missing_obligation_controls(self):
        runner = (HERE / 'SUITE-RUNNER.md').read_text()
        dispatcher = (HERE.parent / 'commands/dispatch.md').read_text()
        validate_brief_guidance(runner, dispatcher)
        for clause in ('Do not wrap feedback or a migrated push in `suite_slot.sh run`',
                       'same coordinated registry as the adapter',
                       'A selected local pass permits PR preparation, not merging.'):
            with self.subTest(clause=clause), self.assertRaises(AssertionError):
                validate_brief_guidance(runner.replace(clause, ''), dispatcher)
        with self.assertRaises(AssertionError):
            validate_brief_guidance(runner, dispatcher.replace('Verification policy belongs to those repository guides', ''))


if __name__=='__main__':
    unittest.main()
