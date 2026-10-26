#!/usr/bin/env python3
"""Check several official sessions together: Git copy against each manifest, each session against the protocol,
and the spread between sessions (E2). Reads only; can write one new report."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manifesto = load('manifesto')
conferir = load('conferir_sessao')

E2_LIMIT = 0.05   # Largest / smallest session median of energy - 1, main applications


def spread(values):
    return max(values) / min(values) - 1


def between_sessions(reports, roles):
    """Per application × configuration: session medians and their spread. No comparison between configurations."""
    medians = {}
    for report in reports:
        cells = {}
        for row in report['processes']:
            cells.setdefault((row['application'], row['configuration']), []).append(row)
        for key, rows in cells.items():
            medians.setdefault(key, []).append({
                'session': report['session_folder'],
                'energy_j': statistics.median(r['energy_j'] for r in rows),
                'time_s': statistics.median(r['time_s'] for r in rows),
                'power_w': statistics.median(r['power_w'] for r in rows)})
    table = []
    for (app, conf), sessions in sorted(medians.items()):
        table.append({'application': app, 'role': roles[app], 'configuration': conf, 'sessions': sessions,
                      'spread_energy': spread([s['energy_j'] for s in sessions]),
                      'spread_time': spread([s['time_s'] for s in sessions]),
                      'spread_power': spread([s['power_w'] for s in sessions])})
    return table


def check_collection(pairs):
    """pairs: (session folder, manifest path). Returns the combined report."""
    config = json.loads((ROOT/'config/execucao.json').read_text(encoding='utf-8'))
    roles = {app: spec['role'] for app, spec in config['applications'].items()}
    problems, reports, sessions = [], [], []
    for folder, manifest_path in pairs:
        folder = Path(folder)
        manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
        if manifest['session_folder'] != folder.resolve().name:
            problems.append('%s: manifesto de outra sessão (%s)' % (folder.name, manifest['session_folder']))
        problems += ['%s: %s' % (folder.name, p) for p in manifesto.check(folder, manifest, skip_scratch=True)]
        report = conferir.check_session(folder)
        problems += ['%s: %s' % (folder.name, p) for p in report['problems']]
        reports.append(report)
        idle = [r['idle_power_w'] for r in report['processes'] if r['idle_power_w'] is not None]
        sessions.append({'session': folder.resolve().name, 'seed': report['seed'], 'first_block': report['first_block'],
                         'folder_sha256': manifest['folder_sha256'],
                         'first_environment_at_utc': manifest['summary']['first_environment_at_utc'],
                         'checked_processes': report['checked_processes'], 'attempts': report['session']['attempts'],
                         'failures': report['session']['failures'], 'retries': report['session']['retries'],
                         'elapsed_minutes': report['session']['elapsed_minutes'],
                         'idle_celsius': report['session']['idle_celsius'],
                         'median_idle_power_w': statistics.median(idle) if idle else None})
    cells = between_sessions(reports, roles)
    main = [c for c in cells if c['role'] == 'principal']
    e2 = {'limit': E2_LIMIT, 'sessions': len(pairs), 'max_spread_energy_main': max((c['spread_energy'] for c in main), default=None),
          'cells_above_limit': ['%s-%s' % (c['application'], c['configuration']) for c in main if c['spread_energy'] > E2_LIMIT]}
    attempts = sum(s['attempts'] for s in sessions)
    failures = sum(len(s['failures']) for s in sessions)
    return {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'problems': problems,
            'processes': sum(s['checked_processes'] for s in sessions), 'attempts': attempts, 'failures': failures,
            'sessions': sessions, 'e2': e2, 'cells': cells}


def percent(value):
    return '-' if value is None else '%.1f%%' % (100 * value)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Conferir em conjunto as sessões oficiais já encerradas.')
    parser.add_argument('--sessao', type=Path, action='append', required=True, help='Pasta da sessão; repetir para cada sessão.')
    parser.add_argument('--manifesto', type=Path, action='append', required=True, help='Manifesto da sessão, na mesma ordem.')
    parser.add_argument('--saida', type=Path, help='Relatório JSON novo.')
    args = parser.parse_args(argv)
    if len(args.sessao) != len(args.manifesto):
        parser.error('Informe um manifesto para cada sessão.')
    report = check_collection(list(zip(args.sessao, args.manifesto)))
    for s in report['sessions']:
        print('%s código %d: %d processos, %d falhas, %.0f min, ociosa %.0f °C, potência ociosa %.2f W' % (
            s['session'], s['seed'], s['checked_processes'], len(s['failures']), s['elapsed_minutes'], s['idle_celsius'],
            s['median_idle_power_w']))
    print('Total: %d processos, %d tentativas, %d falhas' % (report['processes'], report['attempts'], report['failures']))
    print('%-9s %-12s %-4s %12s %12s %12s' % ('aplicação', 'papel', 'conf', 'E2 energia', 'E2 tempo', 'E2 potência'))
    for c in report['cells']:
        print('%-9s %-12s %-4s %12s %12s %12s' % (c['application'], c['role'], c['configuration'], percent(c['spread_energy']),
              percent(c['spread_time']), percent(c['spread_power'])))
    e2 = report['e2']
    print('E2 (principais, %d sessões): maior diferença %s, limite %s, acima do limite: %s' % (
        e2['sessions'], percent(e2['max_spread_energy_main']), percent(e2['limit']), ', '.join(e2['cells_above_limit']) or 'nenhuma'))
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
