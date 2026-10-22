#!/usr/bin/env python3
"""Plan and run one session of complete blocks, one new JVM per process, through executar.py."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('execucao', ROOT/'scripts/executar.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def make_plan(config, config_path, category, blocks, seed, applications=None, pause=10, delta=8.0, max_wait=120,
              idle_seconds=60, session_warmup=('pmd', 'B'), budget=None, first_block=1):
    """Every block holds each application × configuration once, in an order drawn from the seed."""
    applications = applications or sorted(config['applications'])
    if any(app not in config['applications'] for app in applications) or blocks < 1 or first_block < 1:
        raise ValueError('Aplicações ou quantidade de blocos inválidas.')
    if category == 'oficial':
        # Official sessions split the frozen design; block numbers continue across sessions.
        fixed = config['session']
        if sorted(applications) != sorted(config['applications']) or first_block + blocks - 1 > fixed['blocks']:
            raise ValueError('Sessão oficial deve usar todas as aplicações e caber nos %d blocos fixados.' % fixed['blocks'])
        if (pause, delta, max_wait) != (fixed['pause_min_seconds'], fixed['idle_plus_celsius'], fixed['max_wait_seconds']):
            raise ValueError('Pausa e limite térmico da sessão oficial devem ser os fixados na configuração.')
    rng = random.Random(seed)
    runs = []
    for block in range(first_block, first_block + blocks):
        cells = [(app, conf) for app in applications for conf in 'ABCD']
        rng.shuffle(cells)
        for app, conf in cells:
            runs.append({'block': block, 'order': len(runs) + 1, 'application': app, 'configuration': conf,
                         'name': 'b%02d-%03d-%s-%s' % (block, len(runs) + 1, app, conf)})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    parent = ROOT/'dados'/run.CATEGORIES[category][0]
    return {'schema_version': 1, 'created_at_utc': run.stamp(), 'category': category,
            'config': str(Path(config_path).resolve()), 'config_sha256': run.sha256(Path(config_path)),
            'output': str(parent/stamp), 'seed': seed, 'blocks': blocks, 'first_block': first_block,
            'applications': applications,
            'session_warmup': {'application': session_warmup[0], 'configuration': session_warmup[1],
                               'name': 'aquecimento-maquina', 'analyzed': False},
            'pause_min_seconds': pause, 'thermal_gate': {'sensor': 'x86_pkg_temp', 'idle_plus_celsius': delta,
                                                          'max_wait_seconds': max_wait, 'idle_reference_seconds': idle_seconds},
            'failure_retries': 1, 'session_limit_seconds': budget, 'runs': runs}


def package_temperature():
    for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:
            if (zone/'type').read_text().strip() == 'x86_pkg_temp':
                return int((zone/'temp').read_text()) / 1000
        except OSError:
            continue
    return None


def idle_reference(seconds):
    readings = []
    for _ in range(max(1, int(seconds))):
        readings.append(package_temperature())
        time.sleep(1)
    values = [x for x in readings if x is not None]
    return {'seconds': seconds, 'median_celsius': statistics.median(values) if values else None, 'readings': readings}


def cool_down(plan, limit):
    """Fixed minimum pause, then wait for the package to approach its idle temperature."""
    time.sleep(plan['pause_min_seconds'])
    started, start_temp = time.monotonic(), package_temperature()
    temp = start_temp
    while limit is not None and temp is not None and temp > limit:
        if time.monotonic() - started >= plan['thermal_gate']['max_wait_seconds']:
            return {'limit_celsius': limit, 'start_celsius': start_temp, 'end_celsius': temp,
                    'waited_seconds': time.monotonic() - started, 'timed_out': True}
        time.sleep(2)
        temp = package_temperature()
    return {'limit_celsius': limit, 'start_celsius': start_temp, 'end_celsius': temp,
            'waited_seconds': time.monotonic() - started, 'timed_out': False}


def execute(plan, base, entry, block, order):
    out = base/entry['name']
    cmd = ['bash', str(ROOT/'scripts/executar.sh'), 'executar', '--configuracao', entry['configuration'],
           '--aplicacao', entry['application'], '--categoria', plan['category'], '--config', plan['config'],
           '--saida', str(out), '--sessao', base.name, '--bloco', str(block), '--ordem', str(order)]
    started = time.monotonic()
    code = run.process(cmd, ROOT, os.environ.copy(), base/(entry['name']+'-cli.stdout.log'),
                       base/(entry['name']+'-cli.stderr.log'), 900)
    result_file = out/'resultado.json'
    result = json.loads(result_file.read_text()) if result_file.exists() else {'status': 'failure', 'failure': 'sem resultado.json'}
    return {'name': entry['name'], 'application': entry['application'], 'configuration': entry['configuration'],
            'block': block, 'order': order, 'code': code, 'success': code == 0 and result.get('measurement_verified') is True,
            'output': str(out), 'wall_seconds': time.monotonic() - started, 'failure': result.get('failure')}


def run_session(plan_path, resume=False):
    plan = json.loads(Path(plan_path).read_text())
    if run.sha256(Path(plan['config'])) != plan['config_sha256']:
        raise ValueError('A configuração mudou depois do plano; gerar um plano novo.')
    base = Path(plan['output'])
    if base.exists() and not resume:
        raise FileExistsError('Saída já existe; use --retomar ou um plano novo: '+str(base))
    base.mkdir(parents=True, exist_ok=resume)
    progress = base/'progresso.jsonl'
    done = set()
    if resume and progress.exists():
        for record in map(json.loads, progress.read_text().splitlines()):
            # A cell is finished once it passed or its single retry was already used.
            if record['success'] or record['name'].endswith('-repeticao'):
                done.add(record['name'].removesuffix('-repeticao'))
    else:
        run.create_json(base/'plano-antes-execucao.json', plan)
    started = time.monotonic()
    session = base.name+('-retomada-'+datetime.now(timezone.utc).strftime('%H%M%S') if resume else '')
    run.create_json(base/(session+'-ambiente-inicial.json'), run.host_state())
    idle = idle_reference(plan['thermal_gate']['idle_reference_seconds'])
    run.create_json(base/(session+'-temperatura-ociosa.json'), idle)
    limit = None if idle['median_celsius'] is None else idle['median_celsius'] + plan['thermal_gate']['idle_plus_celsius']
    records, failure, consecutive = [], None, 0

    def log(record):
        records.append(record)
        with progress.open('a') as stream:
            stream.write(json.dumps(record, ensure_ascii=False)+'\n')
        print(record['name'], 'ok' if record['success'] else 'FALHA', flush=True)

    def attempt(entry, block, order, name=None):
        nonlocal consecutive
        if plan['session_limit_seconds'] and time.monotonic() - started >= plan['session_limit_seconds']:
            raise TimeoutError('Orçamento da sessão encerrado; resultados parciais preservados.')
        run.require_mains(run.host_state())
        entry = dict(entry, name=name or entry['name'])
        cooling = cool_down(plan, limit)
        record = execute(plan, base, entry, block, order)
        record['cooling'] = cooling
        log(record)
        consecutive = 0 if record['success'] else consecutive + 1
        if consecutive >= 3:
            raise RuntimeError('Três falhas seguidas; interromper e investigar.')
        return record

    try:
        warm = plan['session_warmup']
        attempt({'application': warm['application'], 'configuration': warm['configuration']}, 0, 0,
                warm['name']+('-'+session if resume else ''))
        first = plan.get('first_block', 1)
        for block in range(first, first + plan['blocks']):
            failed = []
            for entry in (x for x in plan['runs'] if x['block'] == block):
                if entry['name'] in done:
                    continue
                if not attempt(entry, block, entry['order'])['success']:
                    failed.append(entry)
            for entry in failed:  # One retry at the end of the same block; the failure stays recorded.
                attempt(entry, block, entry['order'], entry['name']+'-repeticao')
    except BaseException as error:
        failure = type(error).__name__+': '+str(error)
        print(failure, flush=True)
    finally:
        run.create_json(base/(session+'-ambiente-final.json'), run.host_state())
        run.create_json(base/(session+'-resumo-sessao.json'), {
            'status': 'complete' if failure is None else 'incomplete', 'failure': failure, 'category': plan['category'],
            'elapsed_seconds': time.monotonic() - started, 'idle_temperature': idle, 'thermal_limit_celsius': limit,
            'records': records})
        print('SESSAO='+str(base), flush=True)
    return 0 if failure is None else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description='Planejar ou executar uma sessão em blocos completos.')
    sub = parser.add_subparsers(dest='modo', required=True)
    p = sub.add_parser('planejar')
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--categoria', choices=run.CATEGORIES, required=True)
    p.add_argument('--blocos', type=int, required=True)
    p.add_argument('--semente', type=int, required=True)
    p.add_argument('--aplicacoes', nargs='+')
    p.add_argument('--primeiro-bloco', type=int, default=1, help='Número do primeiro bloco, para continuar a numeração entre sessões.')
    p.add_argument('--pausa-minima', type=int)
    p.add_argument('--acima-da-ociosa', type=float)
    p.add_argument('--espera-maxima', type=int)
    p.add_argument('--orcamento-segundos', type=int)
    p.add_argument('--plano', type=Path, required=True, help='Arquivo novo onde o plano é gravado antes da execução.')
    e = sub.add_parser('executar')
    e.add_argument('--plano', type=Path, required=True)
    e.add_argument('--retomar', action='store_true', help='Continuar uma sessão interrompida, sem repetir o que já passou.')
    args = parser.parse_args(argv)
    if args.modo == 'planejar':
        config = json.loads(args.config.read_text())
        run.require_config(config, args.categoria)
        fixed = config.get('session', {})
        pause = args.pausa_minima if args.pausa_minima is not None else fixed.get('pause_min_seconds', 10)
        delta = args.acima_da_ociosa if args.acima_da_ociosa is not None else fixed.get('idle_plus_celsius', 8.0)
        wait = args.espera_maxima if args.espera_maxima is not None else fixed.get('max_wait_seconds', 120)
        plan = make_plan(config, args.config, args.categoria, args.blocos, args.semente, args.aplicacoes,
                         pause, delta, wait, budget=args.orcamento_segundos, first_block=args.primeiro_bloco)
        args.plano.parent.mkdir(parents=True, exist_ok=True)
        run.create_json(args.plano, plan)
        print('PLANO='+str(args.plano)+' processos='+str(len(plan['runs'])+1)+' saida='+plan['output'])
        return 0
    return run_session(args.plano, args.retomar)


if __name__ == '__main__':
    sys.exit(main())
