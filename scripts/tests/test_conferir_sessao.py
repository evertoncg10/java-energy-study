"""Checks for the session quality report on the official session 1 data kept in the repository."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
SESSION = SCRIPTS.parent/'dados/brutos/20261022T215204Z'
spec = importlib.util.spec_from_file_location('conferir_sessao', SCRIPTS/'conferir_sessao.py')
conferir = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conferir)


@unittest.skipUnless((SESSION/'plano-antes-execucao.json').exists(), 'dados da sessão 1 ausentes')
class SessionCheckTest(unittest.TestCase):
    def copy(self, temp):
        target = Path(temp)/SESSION.name
        shutil.copytree(SESSION, target, ignore=shutil.ignore_patterns('scratch'))
        return target

    def test_session_one_passes(self):
        report = conferir.check_session(SESSION)
        self.assertEqual(report['problems'], [])
        self.assertEqual(report['checked_processes'], 48)
        self.assertEqual(len(report['cells']), 12)

    def test_detects_wrong_jvm_option_and_missing_process(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy(temp)
            preflight = folder/'b01-003-avrora-D/java-preflight.json'
            data = json.loads(preflight.read_text())
            data['use_compact_object_headers'] = 'false'
            preflight.write_text(json.dumps(data))
            shutil.rmtree(folder/'b01-004-pmd-B')
            problems = conferir.check_session(folder)['problems']
            self.assertIn('b01-003-avrora-D: opções da JVM diferentes da configuração D', problems)
            self.assertIn('b01-004-pmd-B: pasta ausente', problems)

    def test_detects_order_not_drawn_from_code(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy(temp)
            plan_path = folder/'plano-antes-execucao.json'
            plan = json.loads(plan_path.read_text())
            plan['seed'] = 1
            plan_path.write_text(json.dumps(plan))
            self.assertIn('ordem do plano difere da sorteada pelo código 1', conferir.check_session(folder)['problems'])

    def test_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'sessao1.json'
            self.assertEqual(conferir.main(['--sessao', str(SESSION), '--saida', str(out)]), 0)
            with self.assertRaises(FileExistsError):
                conferir.main(['--sessao', str(SESSION), '--saida', str(out)])


if __name__ == '__main__':
    unittest.main()
