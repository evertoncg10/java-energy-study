#!/usr/bin/env python3
"""Check the quality of a finished official session against the frozen protocol. Reads only; can write one new report."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sessao', ROOT/'scripts/sessao.py')
sessao = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessao)

SESSION_LIMIT_SECONDS = 5400   # E6: at most 1h30 of machine time per session
MAX_FAILURE_SHARE = 0.05       # E6: failures at most 5%
MIN_SAMPLE_SHARE = 0.9         # At least 90% of the samples expected from the measured time
IDLE_TOLERANCE_SECONDS = 0.5


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def check_order(folder, plan, config):
    """Draw the order again from the registered code and compare it with the plan used."""
    redrawn = sessao.make_plan(config, ROOT/'config/execucao.json', plan['category'], plan['blocks'], plan['seed'],
                               applications=plan['applications'], first_block=plan['first_block'])
    key = lambda runs: [(r['block'], r['order'], r['application'], r['configuration'], r['name']) for r in runs]
    return [] if key(redrawn['runs']) == key(plan['runs']) else ['ordem do plano difere da sorteada pelo código %s' % plan['seed']]


def check_run(folder, entry, plan, config):
    """All protocol checks for one process; returns (problems, row for the descriptive tables)."""
    name = entry['name']
    base = folder/name
    problems = []
    if not base.is_dir():
        return ['%s: pasta ausente' % name], None
    result = read_json(base/'resultado.json')
    if result.get('status') != 'success' or not result.get('measurement_verified'):
        problems.append('%s: status %s' % (name, result.get('status')))
    if result.get('config_sha256') != plan['config_sha256']:
        problems.append('%s: configuração diferente da registrada no plano' % name)
    if str(result.get('block_id')) != str(entry['block']) or result.get('order') != entry['order']:
        problems.append('%s: bloco ou ordem diferente do plano' % name)
    conf = config['configurations'][entry['configuration']]
    identity = read_json(base/'java-preflight.json')
    measured = result.get('verified_measurement') or {}
    expected_compact = None if conf['compact_headers'] is None else str(conf['compact_headers']).lower()
    if identity.get('java_runtime_version') != conf['runtime_version'] or measured.get('java_runtime_version') != conf['runtime_version']:
        problems.append('%s: versão do Java %s' % (name, identity.get('java_runtime_version')))
    if identity.get('use_compact_object_headers') != expected_compact or identity.get('use_g1_gc') != 'true':
        problems.append('%s: opções da JVM diferentes da configuração %s' % (name, entry['configuration']))
    if len(result.get('cpu_affinity', {}).get('cpus', [])) != measured.get('available_processors'):
        problems.append('%s: afinidade de núcleos diferente dos processadores vistos pela JVM' % name)
    if abs(result.get('idle_baseline', {}).get('seconds', 0) - config['idle_baseline_seconds']) > IDLE_TOLERANCE_SECONDS:
        problems.append('%s: linha de base ociosa fora de %d s' % (name, config['idle_baseline_seconds']))
    iterations = read_lines(base/'medidor/iterations.jsonl')
    warm = [i for i in iterations if i['warmup']]
    meas = [i for i in iterations if not i['warmup']]
    if len(warm) != config['applications'][entry['application']]['warmup_iterations'] or len(meas) != config['measured_iterations']:
        problems.append('%s: %d preparações e %d medições' % (name, len(warm), len(meas)))
    if not all(i.get('dacapo_valid') for i in iterations) or not all(i.get('status') == 'measurement_valid' for i in meas):
        problems.append('%s: iteração inválida no DaCapo ou no medidor' % name)
    max_gap = max((i['max_gap_nanos'] for i in meas), default=0) / 1e6
    sample_share = min((i['sample_count'] * config['sample_interval_ms'] / 1000 / i['time_s'] for i in meas), default=0)
    if any(i.get('counter_wraps') for i in meas):
        problems.append('%s: volta do contador RAPL numa medição' % name)
    if max_gap > config['max_gap_ms']:
        problems.append('%s: intervalo entre leituras de %.0f ms' % (name, max_gap))
    if sample_share < MIN_SAMPLE_SHARE:
        problems.append('%s: só %.0f%% das leituras esperadas' % (name, 100 * sample_share))
    gc_log = base/'gc.log'
    if not gc_log.exists() or 'Using G1' not in gc_log.read_text(encoding='utf-8', errors='replace'):
        problems.append('%s: gc.log ausente ou sem G1' % name)
    before, after = read_json(base/'system-before.json'), read_json(base/'system-after.json')
    on_ac = all(m.get('online') == '1' for m in before.get('mains', []) + after.get('mains', []))
    if not on_ac:
        problems.append('%s: fora da tomada' % name)
    swap = sum(after['swap_pages'][k] - before['swap_pages'][k] for k in ('pswpin', 'pswpout'))
    times = [i['time_s'] for i in meas]
    row = {'name': name, 'block': entry['block'], 'application': entry['application'], 'configuration': entry['configuration'],
           'energy_j': measured.get('energy_j'), 'time_s': measured.get('time_s'),
           'power_w': measured['energy_j'] / measured['time_s'] if measured.get('time_s') else None,
           'intrusion': statistics.mean(times) / (warm[-1]['dacapo_duration_ms'] / 1000) - 1 if warm and times else None,
           'max_gap_ms': max_gap, 'sample_share': sample_share, 'swap_pages': swap,
           'idle_power_w': result.get('idle_baseline', {}).get('mean_power_w')}
    return problems, row


def cv(values):
    return statistics.stdev(values) / statistics.mean(values) if len(values) > 1 else None


def describe(rows, config):
    """Per application × configuration: variation only. Effects between configurations are left for the analysis (T25)."""
    cells = {}
    for row in rows:
        cells.setdefault((row['application'], row['configuration']), []).append(row)
    table = []
    for (app, conf), group in sorted(cells.items()):
        table.append({'application': app, 'role': config['applications'][app]['role'], 'configuration': conf,
                      'processes': len(group), 'cv_energy': cv([r['energy_j'] for r in group]),
                      'cv_time': cv([r['time_s'] for r in group]), 'cv_power': cv([r['power_w'] for r in group]),
                      'median_intrusion': statistics.median(r['intrusion'] for r in group)})
    return table


def check_session(folder):
    folder = Path(folder).resolve()
    plan = read_json(folder/'plano-antes-execucao.json')
    config = read_json(ROOT/'config/execucao.json')
    summaries = sorted(folder.glob('*-resumo-sessao.json'))
    records = read_lines(folder/'progresso.jsonl')
    problems = check_order(folder, plan, config)
    if plan.get('category') != 'oficial':
        problems.append('sessão não é oficial')
    if sessao.run.sha256(ROOT/'config/execucao.json') != plan['config_sha256']:
        problems.append('config/execucao.json atual difere do registrado no plano')
    entries = plan['runs']
    rows = []
    for entry in entries:
        found, row = check_run(folder, entry, plan, config)
        problems += found
        if row:
            rows.append(row)
    summary = read_json(summaries[-1]) if summaries else {}
    elapsed = summary.get('elapsed_seconds') or 0
    failures = [r['name'] for r in records if not r.get('success')]
    cooling = [r.get('cooling') or {} for r in records]
    if summary.get('status') != 'complete':
        problems.append('sessão com status %s' % summary.get('status'))
    if elapsed > SESSION_LIMIT_SECONDS:
        problems.append('sessão levou %.0f min (limite E6: 90 min)' % (elapsed / 60))
    if records and len(failures) / len(records) > MAX_FAILURE_SHARE:
        problems.append('%d falhas em %d tentativas (limite E6: 5%%)' % (len(failures), len(records)))
    session = {'status': summary.get('status'), 'elapsed_minutes': elapsed / 60, 'attempts': len(records),
               'failures': failures, 'retries': [r['name'] for r in records if r['name'].endswith('-repeticao')],
               'idle_celsius': (summary.get('idle_temperature') or {}).get('median_celsius'),
               'thermal_limit_celsius': summary.get('thermal_limit_celsius'),
               'max_start_celsius': max((c.get('start_celsius') or 0 for c in cooling), default=None),
               'cooling_timeouts': sum(1 for c in cooling if c.get('timed_out')),
               'cooling_wait_seconds': sum(c.get('waited_seconds') or 0 for c in cooling),
               'swap_pages': sum(r['swap_pages'] for r in rows),
               'max_gap_ms': max((r['max_gap_ms'] for r in rows), default=None),
               'min_sample_share': min((r['sample_share'] for r in rows), default=None)}
    return {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'session_folder': folder.name,
            'seed': plan['seed'], 'first_block': plan['first_block'], 'blocks': plan['blocks'],
            'planned_processes': len(entries), 'checked_processes': len(rows), 'problems': problems,
            'session': session, 'cells': describe(rows, config), 'processes': rows}


def percent(value):
    return '-' if value is None or (isinstance(value, float) and math.isnan(value)) else '%.1f%%' % (100 * value)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Conferir a qualidade de uma sessão oficial encerrada.')
    parser.add_argument('--sessao', type=Path, required=True, help='Pasta da sessão, por exemplo dados/brutos/20261022T215204Z.')
    parser.add_argument('--saida', type=Path, help='Relatório JSON novo, fora da pasta da sessão.')
    args = parser.parse_args(argv)
    if args.saida and args.saida.resolve().is_relative_to(args.sessao.resolve()):
        raise ValueError('O relatório deve ficar fora da pasta da sessão.')
    report = check_session(args.sessao)
    s = report['session']
    print('Sessão %s: %s, %.0f min, %d tentativas, %d falhas, %d repetições' % (
        report['session_folder'], s['status'], s['elapsed_minutes'], s['attempts'], len(s['failures']), len(s['retries'])))
    print('Processos conferidos: %d de %d' % (report['checked_processes'], report['planned_processes']))
    print('Temperatura ociosa %.0f °C, limite %.0f °C, maior no início %.0f °C, esperas esgotadas %d' % (
        s['idle_celsius'], s['thermal_limit_celsius'], s['max_start_celsius'], s['cooling_timeouts']))
    print('Maior intervalo entre leituras %.0f ms; menor cobertura de leituras %s; páginas de swap %d' % (
        s['max_gap_ms'], percent(s['min_sample_share']), s['swap_pages']))
    print('%-9s %-12s %-4s %3s %9s %9s %9s %10s' % ('aplicação', 'papel', 'conf', 'n', 'CV energ', 'CV tempo', 'CV potên', 'intrusão'))
    for c in report['cells']:
        print('%-9s %-12s %-4s %3d %9s %9s %9s %10s' % (c['application'], c['role'], c['configuration'], c['processes'],
              percent(c['cv_energy']), percent(c['cv_time']), percent(c['cv_power']), percent(c['median_intrusion'])))
    for problem in report['problems']:
        print('PROBLEMA: '+problem)
    print('CONFERE' if not report['problems'] else 'NAO_CONFERE (%d problemas)' % len(report['problems']))
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        with args.saida.open('x', encoding='utf-8') as stream:  # Never overwrite an earlier report.
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    return 0 if not report['problems'] else 1


if __name__ == '__main__':
    sys.exit(main())
