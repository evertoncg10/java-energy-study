#!/usr/bin/env python3
"""Apply the T12 rules, fixed before the pilot, to a pilot session. Reads only; writes one new summary file."""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys

TOLERANCE = 0.03          # Rule 1: iterations within 3% of the median of the last 3
TAIL = 3
MIN_STABLE = 5            # A plateau must hold for at least 5 iterations
WARMUP_CAPS = {'avrora': 15, 'pmd': 15, 'lusearch': 6}
MAX_MDE = 0.10            # Rule 2: smallest detectable difference with n = 30
TARGET_DELTA = 0.05       # Rule 3: size n to detect 5% in D/C
N_FLOOR, N_CEILING = 15, 30
Z_FACTOR = 2.8            # z(0.975) + z(0.80)


def plateau_start(series, tolerance=TOLERANCE, tail=TAIL):
    """First 1-based iteration from which every later one stays within tolerance of the tail median."""
    reference = statistics.median(series[-tail:])
    for start in range(1, len(series) + 1):
        if all(abs(x - reference) / reference <= tolerance for x in series[start - 1:]):
            return start
    return len(series)


def warmup_rule(curves_by_configuration, cap):
    """Worst configuration decides, so no JDK is favoured; k - 1 warmups plus 1 of margin = k."""
    per_configuration = {}
    for configuration, curves in sorted(curves_by_configuration.items()):
        length = min(len(c) for c in curves)
        median_curve = [statistics.median(c[i] for c in curves) for i in range(length)]
        start = plateau_start(median_curve)
        per_configuration[configuration] = {'median_curve_ms': median_curve, 'plateau_start': start,
                                            'stable_iterations': length - start + 1}
    warmups = max(x['plateau_start'] for x in per_configuration.values())
    reached = all(x['stable_iterations'] >= MIN_STABLE for x in per_configuration.values())
    return {'warmup_iterations': warmups, 'plateau_reached': reached, 'within_cap': warmups <= cap, 'cap': cap,
            'by_configuration': per_configuration}


def pooled_cv(groups):
    """Within-configuration coefficient of variation, pooled across configurations."""
    squares, freedom = 0.0, 0
    for values in groups:
        if len(values) < 2:
            continue
        mean = statistics.mean(values)
        squares += sum(((x - mean) / mean) ** 2 for x in values)
        freedom += len(values) - 1
    if freedom == 0:
        raise ValueError('São necessários pelo menos 2 processos numa configuração.')
    return math.sqrt(squares / freedom), freedom


def smallest_detectable(cv, n):
    return Z_FACTOR * cv * math.sqrt(2 / n)


def processes_needed(cv, delta=TARGET_DELTA):
    return min(N_CEILING, max(N_FLOOR, math.ceil(2 * Z_FACTOR ** 2 * (cv / delta) ** 2)))


def load(base):
    records = [json.loads(x) for x in (base/'progresso.jsonl').read_text().splitlines()]
    plan = json.loads((base/'plano-antes-execucao.json').read_text())
    config = json.loads(Path(plan['config']).read_text())
    processes, failures = [], []
    for record in records:
        if record['name'].startswith('aquecimento-maquina'):
            continue
        if not record['success']:
            failures.append(record)
            continue
        result = json.loads((Path(record['output'])/'resultado.json').read_text())
        processes.append({**record, 'measurement': result['verified_measurement'],
                          'idle_baseline': result.get('idle_baseline')})
    return plan, config, processes, failures


def analyze(base):
    plan, config, processes, failures = load(base)
    report = {'session': str(base), 'category': plan['category'], 'config_sha256': plan['config_sha256'],
              'rules': {'tolerance': TOLERANCE, 'tail': TAIL, 'min_stable': MIN_STABLE, 'warmup_caps': WARMUP_CAPS,
                        'max_mde_at_30': MAX_MDE, 'target_delta': TARGET_DELTA, 'n_range': [N_FLOOR, N_CEILING]},
              'failures': [{'name': f['name'], 'failure': f.get('failure')} for f in failures], 'applications': {}}
    for app in plan['applications']:
        mine = [p for p in processes if p['application'] == app]
        curves, energy, energy_first, time_s = {}, {}, {}, {}
        overhead, walls, cooling = [], [], []
        for p in mine:
            m = p['measurement']
            curves.setdefault(p['configuration'], []).append(m['warmup_dacapo_ms'] + m['measured_dacapo_ms'])
            energy.setdefault(p['configuration'], []).append(m['energy_j'])
            energy_first.setdefault(p['configuration'], []).append(m['measured_energy_j'][0])
            time_s.setdefault(p['configuration'], []).append(m['time_s'])
            # The sampler runs only in measured iterations: last warmup (off) vs first measured (on).
            overhead.append(100 * (m['measured_dacapo_ms'][0] / m['warmup_dacapo_ms'][-1] - 1))
            walls.append(p['wall_seconds'] - sum(m['warmup_dacapo_ms'] + m['measured_dacapo_ms']) / 1000)
            cooling.append(p['cooling']['waited_seconds'])
        if not mine:
            report['applications'][app] = {'processes': 0, 'keep': False, 'reason': 'sem processos válidos'}
            continue
        warm = warmup_rule(curves, WARMUP_CAPS.get(app, 15))
        cv, freedom = pooled_cv(energy.values())
        cv_first, _ = pooled_cv(energy_first.values())
        cv_time, _ = pooled_cv(time_s.values())
        mde = smallest_detectable(cv, N_CEILING)
        app_failures = [f for f in failures if f['application'] == app]
        keep = warm['plateau_reached'] and warm['within_cap'] and mde <= MAX_MDE and not app_failures
        steady = statistics.median(x for c in curves.values() for curve in c for x in curve[warm['warmup_iterations'] - 1:])
        report['applications'][app] = {
            'processes': len(mine), 'failures': len(app_failures), 'warmup': warm,
            'energy_cv': cv, 'energy_cv_first_measured_only': cv_first, 'time_cv': cv_time, 'degrees_of_freedom': freedom,
            'smallest_detectable_at_30': mde, 'keep': keep, 'processes_needed': processes_needed(cv),
            'overhead_pct': {'median': statistics.median(overhead), 'min': min(overhead), 'max': max(overhead),
                             'plateau_reached': warm['plateau_reached']},
            'seconds_per_process_estimate': statistics.median(walls) + (warm['warmup_iterations'] + config.get('measured_iterations', 1)) * steady / 1000
                                            + plan['pause_min_seconds'] + statistics.median(cooling),
            'idle_baseline_power_w': statistics.median(p['idle_baseline']['mean_power_w'] for p in mine) if mine[0]['idle_baseline'] else None}
    kept = [a for a, r in report['applications'].items() if r['keep']]
    n = max((report['applications'][a]['processes_needed'] for a in kept), default=None)
    report['decision'] = {'applications': kept, 'processes_per_cell': n,
                          'warmup_iterations': {a: report['applications'][a]['warmup']['warmup_iterations'] for a in kept}}
    if n:
        per_block = 4 * sum(report['applications'][a]['seconds_per_process_estimate'] for a in kept)
        report['decision']['estimated_collection_hours'] = n * per_block / 3600
    waits = [p['cooling'] for p in processes]
    report['thermal'] = {'timeouts': sum(w['timed_out'] for w in waits),
                         'median_wait_seconds': statistics.median(w['waited_seconds'] for w in waits) if waits else None}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Aplicar as regras da T12 a uma sessão do piloto 2.')
    parser.add_argument('sessao', type=Path)
    args = parser.parse_args(argv)
    report = analyze(args.sessao.resolve(strict=True))
    out = args.sessao/'ANALISE_T12.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    for app, r in report['applications'].items():
        if not r['processes']:
            print(app, r['reason'])
            continue
        print('%s: preparações=%d (regime %s), CV energia=%.1f%% (só 1ª medida %.1f%%), menor diferença com n=30=%.1f%%, manter=%s, n necessário=%d'
              % (app, r['warmup']['warmup_iterations'], 'atingido' if r['warmup']['plateau_reached'] else 'NÃO atingido',
                 100 * r['energy_cv'], 100 * r['energy_cv_first_measured_only'], 100 * r['smallest_detectable_at_30'],
                 'sim' if r['keep'] else 'NÃO', r['processes_needed']))
    print('DECISAO='+json.dumps(report['decision'], ensure_ascii=False))
    print('ARQUIVO='+str(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
