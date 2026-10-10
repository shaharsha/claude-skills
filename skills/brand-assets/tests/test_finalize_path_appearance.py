import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'finalize-svg.py'
NS = {'svg': 'http://www.w3.org/2000/svg'}

class PathAppearanceTests(unittest.TestCase):
    def finalize(self, body, *options):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.svg'
            output = Path(folder) / 'output.svg'
            source.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'+body+'</svg>', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source), '--output', str(output), '--brand', '#000000', '#FF0000', '--quiet', *options], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return ET.parse(output).getroot().findall('.//svg:path', NS)

    def test_explicit_top_level_fill_survives(self):
        paths = self.finalize('<path fill="#ff0000" d="M0 0 L10 0 L10 10 Z"/>', '--default-fill', '#000000')
        self.assertEqual(paths[0].get('fill'), '#FF0000')

    def test_missing_fill_uses_default(self):
        paths = self.finalize('<path d="M0 0 L10 0 L10 10 Z"/>', '--default-fill', '#FF0000')
        self.assertEqual(paths[0].get('fill'), '#FF0000')

    def test_inherited_rule_survives_and_explicit_rule_wins(self):
        paths = self.finalize('<g fill="#FF0000" fill-rule="evenodd"><path d="M0 0 L10 0 L10 10 Z"/><path fill-rule="nonzero" d="M1 1 L9 1 L9 9 Z"/></g>')
        self.assertEqual([path.get('fill-rule') for path in paths], ['evenodd', 'nonzero'])

if __name__ == '__main__':
    unittest.main()