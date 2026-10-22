"""Checks for the T12 additions: core affinity, k measured iterations, session plan and decision rules."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = load('execucao', 'executar.py')
session = load('sessao', 'sessao.py')
rules = load('analise', 'analisar_piloto_t12.py')
PILOT = json.loads((SCRIPTS.parent/'config/piloto-t12.json').read_text())
CONFIG = json.loads((SCRIPTS.parent/'config/execucao.json').read_text())


class AffinityTest(unittest.TestCase):
    def fake_sysfs(self, root, performance, siblings):
        (root/'devices/cpu_core').mkdir(parents=True)
        (root/'devices/cpu_core/cpus').write_text(performance+'\n')
        for cpu, text in siblings.items():
            d = root/f'devices/system/cpu/cpu{cpu}/topology'
            d.mkdir(parents=True)
            (d/'core_cpus_list').write_text(text+'\n')

    def test_one_logical_cpu_per_performance_core(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_sysfs(root, '0-11', {c: '%d-%d' % (c - c % 2, c - c % 2 + 1) for c in range(12)})
            self.assertEqual(run.affinity_cpus('cpu_core_um_por_nucleo', root), [0, 2, 4, 6, 8, 10])

    def test_parses_comma_lists(self):
        self.assertEqual(run.cpu_list('0,2,4-6'), {0, 2, 4, 5, 6})

    def test_no_policy_keeps_scheduler_default(self):
        self.assertIsNone(run.affinity_cpus(None))


class ConfigTest(unittest.TestCase):
    def test_pilot_config_is_valid_and_not_official(self):
        run.require_config(PILOT, 'piloto')
        with self.assertRaisesRegex(ValueError, 'protocolo provisório'):
            run.require_config(PILOT, 'oficial')

    def test_per_application_warmup_overrides_global(self):
        self.assertEqual(run.warmups(PILOT, 'lusearch'), 5)
        self.assertEqual(run.warmups(CONFIG, 'pmd'), CONFIG['warmup_iterations'])

    def test_old_configs_keep_one_measured_iteration(self):
        self.assertEqual(run.measured_count(CONFIG), 1)

    def test_rejects_unknown_affinity_and_bad_measured_count(self):
        bad = copy.deepcopy(PILOT)
        bad['cpu_affinity'] = 'todos'
        with self.assertRaisesRegex(ValueError, 'núcleos'):
            run.require_config(bad, 'piloto')
        bad = copy.deepcopy(PILOT)
        bad['measured_iterations'] = 0
        with self.assertRaisesRegex(ValueError, 'medidas'):
            run.require_config(bad, 'piloto')


class ResultTest(unittest.TestCase):
    def write_run(self, root, warm, measured, summary_count=None):
        meter = root/'medidor'
        meter.mkdir(parents=True)
        identity = {'java_version': '25.0.3', 'java_runtime_version': '25.0.3+9-LTS', 'java_vendor': 'Eclipse Adoptium',
                    'java_home': '/tmp/jdk', 'use_g1_gc': 'true', 'use_compact_object_headers': 'true',
                    'max_heap_bytes': 1024**3, 'available_processors': 6}
        (meter/'jvm.json').write_text(json.dumps(identity))
        (meter/'summary.json').write_text(json.dumps({'status': 'measurement_valid', 'failure': None, 'application': 'pmd',
                                                      'measured_iterations': summary_count or measured}))
        lines = [{'warmup': True, 'energy_j': None, 'time_s': None, 'status': 'warmup_valid', 'dacapo_valid': True,
                  'application': 'pmd', 'failure': None, 'dacapo_duration_ms': 3500} for _ in range(warm)]
        lines += [{'warmup': False, 'energy_j': 120.0 + i, 'time_s': 3.0, 'status': 'measurement_valid', 'dacapo_valid': True,
                   'application': 'pmd', 'failure': None, 'dacapo_duration_ms': 3000} for i in range(measured)]
        (meter/'iterations.jsonl').write_text('\n'.join(json.dumps(x) for x in lines))
        params = {'input_size': 'default', 'thread_count': 1, 'iterations': warm + measured, 'measured_iterations': measured,
                  'methodology': 'ITERATE', 'validation': True, 'validate_output': True, 'ignore_validation_failure': False}
        (meter/'metadata.json').write_text(json.dumps({'configuration': 'D', 'category': 'pilot',
                                                       'dacapo_build_version': PILOT['dacapo']['version'],
                                                       'dacapo_parameters': params,
                                                       'meter_artifact': {'sha256': PILOT['meter']['sha256']},
                                                       'dacapo_artifact': {'sha256': PILOT['dacapo']['sha256']}}))

    def test_observation_is_mean_of_the_measured_iterations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(root, 12, 3)
            result = run.require_result(root, PILOT['configurations']['D'], {'expected_java_home': '/tmp/jdk', 'java_executable': '/tmp/jdk/bin/java'},
                                        PILOT, 'pmd', PILOT['applications']['pmd'], 'D', 'pilot', [0, 2, 4, 6, 8, 10])
            self.assertEqual(result['measured_energy_j'], [120.0, 121.0, 122.0])
            self.assertAlmostEqual(result['energy_j'], 121.0)

    def test_rejects_missing_measured_iteration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(root, 12, 2, summary_count=3)
            with self.assertRaisesRegex(ValueError, 'Quantidade de iterações'):
                run.require_result(root, PILOT['configurations']['D'], {'expected_java_home': '/tmp/jdk', 'java_executable': '/tmp/jdk/bin/java'},
                                   PILOT, 'pmd', PILOT['applications']['pmd'], 'D', 'pilot')

    def test_rejects_jvm_that_saw_more_cpus_than_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_run(root, 12, 3)
            with self.assertRaisesRegex(ValueError, 'núcleos'):
                run.require_result(root, PILOT['configurations']['D'], {'expected_java_home': '/tmp/jdk', 'java_executable': '/tmp/jdk/bin/java'},
                                   PILOT, 'pmd', PILOT['applications']['pmd'], 'D', 'pilot', [0, 2, 4, 6])


class PlanTest(unittest.TestCase):
    def test_every_block_holds_each_cell_once_and_seed_reproduces_order(self):
        plan = session.make_plan(PILOT, SCRIPTS.parent/'config/piloto-t12.json', 'piloto', 3, 20261024)
        again = session.make_plan(PILOT, SCRIPTS.parent/'config/piloto-t12.json', 'piloto', 3, 20261024)
        self.assertEqual([r['name'] for r in plan['runs']], [r['name'] for r in again['runs']])
        self.assertEqual(len(plan['runs']), 36)
        for block in (1, 2, 3):
            cells = {(r['application'], r['configuration']) for r in plan['runs'] if r['block'] == block}
            self.assertEqual(len(cells), 12)
        self.assertFalse(plan['session_warmup']['analyzed'])


class RuleTest(unittest.TestCase):
    def test_plateau_after_slow_first_iteration(self):
        self.assertEqual(rules.plateau_start([6000, 3600, 3400, 3350, 3340, 3330, 3335, 3332]), 3)

    def test_worst_configuration_sets_warmups(self):
        flat = [[100] * 10] * 3
        slow = [[200, 150, 120, 101, 100, 100, 100, 100, 100, 100]] * 3
        result = rules.warmup_rule({'A': flat, 'D': slow}, 15)
        self.assertEqual(result['warmup_iterations'], 4)
        self.assertTrue(result['plateau_reached'])

    def test_short_plateau_is_not_accepted(self):
        result = rules.warmup_rule({'A': [[300, 250, 200, 150, 120, 100, 100, 100]] * 3}, 15)
        self.assertFalse(result['plateau_reached'])

    def test_pooled_cv_reproduces_t11_avrora(self):
        groups = [[87.400167, 80.949744], [110.325645, 87.119711], [75.8756, 83.52481], [76.114796, 81.409948]]
        cv, freedom = rules.pooled_cv(groups)
        self.assertAlmostEqual(cv, 0.097, places=3)
        self.assertEqual(freedom, 4)

    def test_processes_needed_is_clamped(self):
        self.assertEqual(rules.processes_needed(0.02), 15)
        self.assertEqual(rules.processes_needed(0.06), 23)
        self.assertEqual(rules.processes_needed(0.12), 30)


if __name__ == '__main__':
    unittest.main()
