"""Checks for the joint report of official sessions on the data kept in the repository."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
SESSIONS = [(ROOT/'dados/brutos'/name, ROOT/'evidencias/manifestos'/('sessao%d.json' % n))
            for n, name in ((1, '20261022T215204Z'), (2, '20261022T215207Z'))]
spec = importlib.util.spec_from_file_location('conferir_coleta', SCRIPTS/'conferir_coleta.py')
coleta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coleta)


@unittest.skipUnless(all(folder.exists() and manifest.exists() for folder, manifest in SESSIONS), 'dados das sessões ausentes')
class CollectionCheckTest(unittest.TestCase):
    def test_sessions_pass_and_spread_is_per_cell(self):
        report = coleta.check_collection(SESSIONS)
        self.assertEqual(report['problems'], [])
        self.assertEqual(report['processes'], 96)
        self.assertEqual(len(report['cells']), 12)
        self.assertTrue(all(len(c['sessions']) == 2 for c in report['cells']))

    def test_changed_file_and_swapped_manifest_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/SESSIONS[0][0].name
            shutil.copytree(SESSIONS[0][0], folder, ignore=shutil.ignore_patterns('scratch'))
            (folder/'b01-001-lusearch-A/resultado.json').write_text('{}')
            problems = coleta.check_collection([(folder, SESSIONS[0][1]), (SESSIONS[1][0], SESSIONS[0][1])])['problems']
            self.assertIn('%s: alterado: b01-001-lusearch-A/resultado.json' % folder.name, problems)
            self.assertIn('%s: manifesto de outra sessão (%s)' % (SESSIONS[1][0].name, folder.name), problems)


if __name__ == '__main__':
    unittest.main()
