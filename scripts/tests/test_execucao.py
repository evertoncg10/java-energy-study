"""Focused checks for identity, output preservation and privilege boundaries."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1]/'executar.py'
spec = importlib.util.spec_from_file_location('execucao', MODULE)
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)
CONFIG = json.loads((MODULE.parents[1]/'config/execucao.json').read_text())


class ExecutionTest(unittest.TestCase):
    def setUp(self):
        self.config = copy.deepcopy(CONFIG)
        self.selection = {'expected_java_home':'/tmp/jdk-esperado', 'java_executable':'/tmp/jdk-esperado/bin/java'}
        self.identity = {'java_version':'25.0.3','java_runtime_version':'25.0.3+9-LTS',
                         'java_vendor':'Eclipse Adoptium','java_home':'/tmp/jdk-esperado',
                         'use_g1_gc':'true','use_compact_object_headers':'true'}

    def test_parses_actual_property_and_flag_format(self):
        identity = run.parse_identity('     bool UseG1GC = true {product} {command line}\n     bool UseCompactObjectHeaders = false {product}\n',
                                      '    java.version = 25.0.3\n    java.runtime.version = 25.0.3+9-LTS\n    java.home = /tmp/jdk-esperado\n    java.vendor = Eclipse Adoptium\n')
        self.assertEqual(identity['java_runtime_version'], '25.0.3+9-LTS')
        self.assertEqual(identity['use_compact_object_headers'], 'false')

    def test_rejects_wrong_runtime_build(self):
        self.identity['java_runtime_version'] = '25.0.3+outro'
        with self.assertRaisesRegex(ValueError,'Versão completa'):
            run.require_identity(self.identity,self.config['configurations']['D'],self.selection)

    def test_rejects_wrong_vendor(self):
        self.identity['java_vendor'] = 'Outro fornecedor'
        with self.assertRaisesRegex(ValueError,'Fornecedor'):
            run.require_identity(self.identity,self.config['configurations']['D'],self.selection)

    def test_rejects_wrong_compact_flag(self):
        with self.assertRaisesRegex(ValueError,'cabeçalhos'):
            run.require_identity(self.identity,self.config['configurations']['C'],self.selection)

    def test_rejects_runtime_executable_change(self):
        self.identity['java_executable'] = '/tmp/outro-java/bin/java'
        with self.assertRaisesRegex(ValueError,'executável'):
            run.require_identity(self.identity,self.config['configurations']['D'],self.selection)

    def test_official_collection_requires_frozen_protocol(self):
        self.config['protocol_status'] = 'provisorio'
        with self.assertRaisesRegex(ValueError,'protocolo provisório'):
            run.require_config(self.config,'oficial')

    def test_rejects_changed_study_configuration(self):
        self.config['configurations']['B']['java_feature'] = 25
        with self.assertRaisesRegex(ValueError,'desenho do estudo'):
            run.require_config(self.config,'verificacao')

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'dados/verificacao/existente';out.mkdir(parents=True)
            evidence=out/'amostra-original.json';evidence.write_text('preservar')
            with patch.object(run,'ROOT',root),contextlib.redirect_stderr(io.StringIO()):
                code=run.main(['preparar','--configuracao','A','--saida',str(out)])
            self.assertEqual(code,2)
            self.assertEqual(evidence.read_text(),'preservar')
            self.assertEqual(sorted(x.name for x in out.iterdir()),['amostra-original.json'])

    def test_rejects_output_in_wrong_category(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(run,'ROOT',root),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    run.main(['preparar','--configuracao','A','--categoria','piloto','--saida',str(root/'dados/brutos/errado')])
            self.assertFalse((root/'dados/brutos/errado').exists())

    def test_privileged_release_rejects_arbitrary_file(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'energy_uj';f.write_text('10')
            with self.assertRaisesRegex(ValueError,'apenas no contador'):
                run.permission_command(f)

    @unittest.skipIf(os.geteuid()==0,'permission boundary requires an unprivileged user')
    def test_unattended_denied_read_does_not_call_sudo(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);(d/'name').write_text('package-0');(d/'max_energy_range_uj').write_text('100')
            f=d/'energy_uj';f.write_text('10');f.chmod(0)
            try:
                with patch.object(run.subprocess,'run') as sudo:
                    with self.assertRaises(PermissionError):
                        run.rapl_check(d,False,'executar',[])
                    sudo.assert_not_called()
            finally:
                f.chmod(0o600)

    @unittest.skipIf(os.geteuid()==0,'permission boundary requires an unprivileged user')
    def test_release_without_terminal_does_not_call_sudo(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);(d/'name').write_text('package-0');(d/'max_energy_range_uj').write_text('100')
            f=d/'energy_uj';f.write_text('10');f.chmod(0)
            try:
                with patch.object(run.sys.stdin,'isatty',return_value=False),patch.object(run.subprocess,'run') as sudo:
                    with self.assertRaisesRegex(PermissionError,'terminal interativo'):
                        run.rapl_check(d,True,'preparar',[])
                    sudo.assert_not_called()
            finally:
                f.chmod(0o600)

    def test_stopped_counter_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);(d/'name').write_text('package-0');(d/'max_energy_range_uj').write_text('100');(d/'energy_uj').write_text('10')
            with self.assertRaisesRegex(ValueError,'sem avanço'):
                run.rapl_check(d,False,'preparar',[])


if __name__ == '__main__':
    unittest.main()
