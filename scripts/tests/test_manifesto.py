"""Checks for the session manifest: hashes, summary, no overwrite and detection of changes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manifesto', SCRIPTS/'manifesto.py')
manifesto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifesto)


def fake_session(root):
    base = root/'dados/brutos/20261024T170000Z'
    (base/'b01-001-pmd-D').mkdir(parents=True)
    plan = {'category': 'oficial', 'seed': 20261101, 'first_block': 1, 'blocks': 1, 'created_at_utc': '2026-10-24T16:55:00+00:00',
            'session_warmup': {'name': 'aquecimento-maquina'}, 'runs': [{'name': 'b01-001-pmd-D'}, {'name': 'b01-002-lusearch-C'}]}
    (base/'plano-antes-execucao.json').write_text(json.dumps(plan))
    (base/'b01-001-pmd-D/resultado.json').write_text('{"status": "success"}')
    (base/'20261024T170000Z-ambiente-inicial.json').write_text('{"at_utc": "2026-10-24T17:00:00+00:00"}')
    (base/'20261024T170000Z-ambiente-final.json').write_text('{"at_utc": "2026-10-24T18:00:00+00:00"}')
    (base/'20261024T170000Z-resumo-sessao.json').write_text('{"status": "complete", "failure": null, "elapsed_seconds": 3600}')
    records = [{'name': 'aquecimento-maquina', 'success': True}, {'name': 'b01-001-pmd-D', 'success': True},
               {'name': 'b01-002-lusearch-C', 'success': False}, {'name': 'b01-002-lusearch-C-repeticao', 'success': True}]
    (base/'progresso.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    return base


class ManifestTest(unittest.TestCase):
    def test_summary_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = fake_session(Path(temp))
            data = manifesto.make_manifest(base)
            self.assertEqual(data['file_count'], 6)
            self.assertEqual(data['summary']['planned_processes'], 3)
            self.assertEqual(data['summary']['attempts'], 4)
            self.assertEqual(data['summary']['failures'], ['b01-002-lusearch-C'])
            self.assertEqual(data['summary']['retries'], ['b01-002-lusearch-C-repeticao'])
            self.assertEqual(data['summary']['first_environment_at_utc'], '2026-10-24T17:00:00+00:00')
            self.assertEqual(data['folder_sha256'], manifesto.make_manifest(base)['folder_sha256'])

    def test_check_detects_changed_missing_and_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            base = fake_session(Path(temp))
            data = manifesto.make_manifest(base)
            self.assertEqual(manifesto.check(base, data), [])
            (base/'b01-001-pmd-D/resultado.json').write_text('{"status": "failure"}')
            (base/'progresso.jsonl').unlink()
            (base/'extra.txt').write_text('x')
            self.assertEqual(manifesto.check(base, data),
                             ['faltando: progresso.jsonl', 'a mais: extra.txt', 'alterado: b01-001-pmd-D/resultado.json'])

    def test_check_can_ignore_scratch_left_out_of_git(self):
        with tempfile.TemporaryDirectory() as temp:
            base = fake_session(Path(temp))
            (base/'b01-001-pmd-D/scratch').mkdir()
            (base/'b01-001-pmd-D/scratch/stdout.log').write_text('saida da carga')
            data = manifesto.make_manifest(base)
            (base/'b01-001-pmd-D/scratch/stdout.log').unlink()
            self.assertEqual(manifesto.check(base, data), ['faltando: b01-001-pmd-D/scratch/stdout.log'])
            self.assertEqual(manifesto.check(base, data, skip_scratch=True), [])

    def test_cli_never_overwrites_and_rejects_output_inside_session(self):
        with tempfile.TemporaryDirectory() as temp:
            base = fake_session(Path(temp))
            out = Path(temp)/'evidencias/manifestos/sessao1.json'
            self.assertEqual(manifesto.main(['gerar', '--sessao', str(base), '--saida', str(out)]), 0)
            with self.assertRaises(FileExistsError):
                manifesto.main(['gerar', '--sessao', str(base), '--saida', str(out)])
            with self.assertRaises(ValueError):
                manifesto.main(['gerar', '--sessao', str(base), '--saida', str(base/'manifesto.json')])
            self.assertEqual(manifesto.main(['conferir', '--sessao', str(base), '--manifesto', str(out)]), 0)


if __name__ == '__main__':
    unittest.main()
