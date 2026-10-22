#!/usr/bin/env python3
"""Prepare or run one JVM with SDKMAN selection and preserved process evidence."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {'verificacao': ('verificacao', 'verification'),
              'piloto': ('piloto', 'pilot'), 'oficial': ('brutos', 'official')}
INJECTED_OPTIONS = ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS', 'CLASSPATH')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def create_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def parse_identity(stdout, stderr):
    props = dict(re.findall(r'^\s*(java\.(?:version|runtime.version|vendor|home)) = (.+)$', stderr, re.M))
    flags = dict(re.findall(r'^\s*\w+\s+(UseG1GC|UseCompactObjectHeaders)\s*(?::=|=)\s*(\S+)', stdout, re.M))
    return {'java_version': props.get('java.version'), 'java_runtime_version': props.get('java.runtime.version'),
            'java_vendor': props.get('java.vendor'), 'java_home': props.get('java.home'),
            'use_g1_gc': flags.get('UseG1GC'), 'use_compact_object_headers': flags.get('UseCompactObjectHeaders')}


def require_identity(identity, spec, selection):
    if identity.get('java_version') != spec['java_version'] or identity.get('java_runtime_version') != spec['runtime_version']:
        raise ValueError('Versão completa do Java diverge da configuração solicitada.')
    if int(identity['java_version'].split('.')[0]) != spec['java_feature']:
        raise ValueError('Versão principal do Java incorreta.')
    if identity.get('java_vendor') != 'Eclipse Adoptium':
        raise ValueError('Fornecedor diferente de Eclipse Temurin/Eclipse Adoptium.')
    if Path(identity['java_home']).resolve() != Path(selection['expected_java_home']).resolve():
        raise ValueError('java.home diverge do SDK selecionado.')
    if identity.get('use_g1_gc') != 'true':
        raise ValueError('G1 não está ativo.')
    compact = spec['compact_headers']
    expected = None if compact is None else str(compact).lower()
    if identity.get('use_compact_object_headers') != expected:
        raise ValueError('Estado dos cabeçalhos compactos incorreto.')
    if 'java_executable' in identity and Path(identity['java_executable']).resolve() != Path(selection['java_executable']).resolve():
        raise ValueError('O processo usou outro executável Java.')


def require_config(config, category):
    if config['schema_version'] != 1:
        raise ValueError('Versão de configuração desconhecida.')
    expected = {'A': (17, None), 'B': (21, None), 'C': (25, False), 'D': (25, True)}
    for name, (feature, compact) in expected.items():
        spec = config['configurations'][name]
        if spec['java_feature'] != feature or spec['compact_headers'] is not compact:
            raise ValueError('As configurações A/B/C/D não correspondem ao desenho do estudo.')
        if spec['sdkman_id'] != spec['java_version'] + '-tem':
            raise ValueError('SDKMAN ID não corresponde à versão Temurin fixada.')
    for app, params in config['applications'].items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', app) or not re.fullmatch(r'[a-z]+', params['input']):
            raise ValueError('Nome de aplicação/entrada inválido.')
        if type(params['threads']) is not int or params['threads'] < 1:
            raise ValueError('Quantidade de threads inválida.')
        if any(not re.fullmatch(r'[1-9][0-9]*[kKmMgG]', params[k]) for k in ['heap_initial', 'heap_max']):
            raise ValueError('Heap inválido.')
    for app in config['applications']:
        if type(warmups(config, app)) is not int or warmups(config, app) < 1:
            raise ValueError('É necessária pelo menos uma preparação.')
    if type(measured_count(config)) is not int or not 1 <= measured_count(config) <= 10:
        raise ValueError('Quantidade de iterações medidas inválida (1 a 10).')
    if config.get('cpu_affinity') not in AFFINITY_POLICIES:
        raise ValueError('Política de núcleos desconhecida.')
    if type(config.get('idle_baseline_seconds', 0)) not in (int, float) or not 0 <= config.get('idle_baseline_seconds', 0) <= 60:
        raise ValueError('Linha de base ociosa deve ter de 0 a 60 s.')
    if type(config.get('gc_log', False)) is not bool:
        raise ValueError('gc_log deve ser verdadeiro ou falso.')
    if type(config['process_timeout_seconds']) is not int or config['process_timeout_seconds'] < 1:
        raise ValueError('Limite de duração inválido.')
    if category == 'oficial' and config.get('protocol_status') != 'fixado':
        raise ValueError('Coleta oficial bloqueada: protocolo provisório. Fixar regras na T13 antes da coleta.')


def permission_command(energy):
    target = energy.resolve(strict=True)
    if not re.fullmatch(r'/sys/devices/virtual/powercap/intel-rapl/intel-rapl:\d+/energy_uj', str(target)):
        raise ValueError('Liberação administrativa permitida apenas no contador RAPL de pacote reconhecido em sysfs.')
    return ['sudo', 'chown', '--', str(os.getuid()), str(target)]


def rapl_check(directory, allow_release, mode, events):
    directory = directory.resolve(strict=True)
    domain = (directory/'name').read_text().strip()
    limit = int((directory/'max_energy_range_uj').read_text())
    if not re.fullmatch(r'package-\d+', domain) or limit <= 0:
        raise ValueError('É necessário um domínio RAPL de pacote com limite válido.')
    energy = directory/'energy_uj'
    event = {'phase': 'rapl_after_sdkman', 'at_utc': stamp(), 'directory': str(directory),
             'domain': domain, 'release_requested': allow_release, 'release_performed': False}
    events.append(event)
    try:
        first = int(energy.read_text())
    except PermissionError:
        if not allow_release:
            raise PermissionError('Contador sem leitura. Execute preparar --liberar-leitura em terminal interativo antes da sessão automática.')
        if mode != 'preparar' or not sys.stdin.isatty():
            raise PermissionError('Liberação exige modo preparar e terminal interativo; execução automática não aguarda senha.')
        command = permission_command(energy)
        print('Liberar leitura somente deste contador:\n' + shlex.join(command), flush=True)
        event['release_command'] = command
        # The user's terminal handles sudo. Never capture its input or store a password.
        completed = subprocess.run(command, check=False, timeout=120)
        event['release_exit_code'] = completed.returncode
        if completed.returncode:
            raise PermissionError('A liberação falhou; nenhuma tarefa será iniciada.')
        event['release_performed'] = True
        first = int(energy.read_text())
    before = time.monotonic_ns()
    time.sleep(0.05)
    last = int(energy.read_text())
    after = time.monotonic_ns()
    if not (0 <= first < limit and 0 <= last < limit) or first == last:
        raise ValueError('Contador fora do intervalo ou sem avanço na verificação.')
    event.update(first_energy_uj=first, last_energy_uj=last, before_nanos=before, after_nanos=after,
                 range_uj=limit, uid=energy.stat().st_uid, mode=oct(energy.stat().st_mode & 0o777), readable=True)
    return directory


def stop_group(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    except ProcessLookupError:
        proc.wait()


def process(command, cwd, env, stdout, stderr, timeout, cpus=None):
    pin = (lambda: os.sched_setaffinity(0, cpus)) if cpus else None
    with stdout.open('x') as out, stderr.open('x') as err:
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True, preexec_fn=pin)
        try:
            return proc.wait(timeout=timeout)
        except BaseException as error:
            stop_group(proc)
            error.terminated_returncode = proc.returncode
            raise


def require_result(run, spec, selection, config, app, params, configuration, category, cpus=None):
    meter = run/'medidor'
    identity = json.loads((meter/'jvm.json').read_text())
    require_identity(identity, spec, selection)
    if identity['max_heap_bytes'] != heap_bytes(params['heap_max']):
        raise ValueError('O heap máximo efetivo diverge da configuração.')
    if cpus and identity.get('available_processors') != len(cpus):
        raise ValueError('A JVM não ficou restrita aos núcleos escolhidos.')
    summary = json.loads((meter/'summary.json').read_text())
    metadata = json.loads((meter/'metadata.json').read_text())
    iterations = [json.loads(x) for x in (meter/'iterations.jsonl').read_text().splitlines()]
    warm, count = warmups(config, app), measured_count(config)
    if summary['status'] != 'measurement_valid' or summary['failure'] is not None or summary['application'] != app or summary['measured_iterations'] != count:
        raise ValueError('Resumo do medidor inválido.')
    if len(iterations) != warm + count:
        raise ValueError('Quantidade de iterações inesperada.')
    if any(not x['warmup'] or x['energy_j'] is not None or x['time_s'] is not None or x['status'] != 'warmup_valid' or not x['dacapo_valid'] for x in iterations[:warm]):
        raise ValueError('Preparação inválida ou confundida com medição.')
    measured = iterations[warm:]
    for x in measured:
        if x['warmup'] or x['status'] != 'measurement_valid' or not x['dacapo_valid'] or any(not isinstance(x[k], (int, float)) or not math.isfinite(x[k]) or x[k] <= 0 for k in ['energy_j','time_s']):
            raise ValueError('Tarefa medida inválida.')
    if metadata['configuration'] != configuration or metadata['category'] != category or metadata['dacapo_build_version'] != config['dacapo']['version']:
        raise ValueError('Configuração, categoria ou versão da suíte divergente.')
    if any(x['application'] != app or x['failure'] is not None for x in iterations):
        raise ValueError('Identidade ou falha nas iterações diverge do esperado.')
    options = metadata['dacapo_parameters']
    if options['input_size'] != params['input'] or int(options['thread_count']) != params['threads'] or options['iterations'] != warm+count or options.get('measured_iterations', 1) != count or options['methodology'] != 'ITERATE' or not options['validation'] or not options['validate_output'] or options['ignore_validation_failure']:
        raise ValueError('Parâmetros ou validação DaCapo divergentes.')
    for name in ['meter','dacapo']:
        if metadata[name+'_artifact']['sha256'] != config[name]['sha256']:
            raise ValueError('Artefato efetivamente usado diverge da configuração.')
    # The process is the statistical unit: its observation is the mean of its measured iterations.
    return {'java_runtime_version': identity['java_runtime_version'], 'application': app,
            'energy_j': sum(x['energy_j'] for x in measured) / count, 'time_s': sum(x['time_s'] for x in measured) / count,
            'measured_energy_j': [x['energy_j'] for x in measured], 'measured_time_s': [x['time_s'] for x in measured],
            'warmup_dacapo_ms': [x['dacapo_duration_ms'] for x in iterations[:warm]],
            'measured_dacapo_ms': [x['dacapo_duration_ms'] for x in measured],
            'available_processors': identity.get('available_processors'), 'validation': True}


def heap_bytes(value):
    return int(value[:-1]) * {'k':1024, 'm':1024**2, 'g':1024**3}[value[-1].lower()]


def warmups(config, app):
    """Per-application warmup count; the global value is the default."""
    return config['applications'][app].get('warmup_iterations', config['warmup_iterations'])


def measured_count(config):
    return config.get('measured_iterations', 1)


AFFINITY_POLICIES = (None, 'cpu_core_um_por_nucleo')


def cpu_list(text):
    cpus = set()
    for part in text.strip().split(','):
        first, _, last = part.partition('-')
        cpus.update(range(int(first), int(last or first) + 1))
    return cpus


def affinity_cpus(policy, sysfs=Path('/sys')):
    """P-cores only (Intel hybrid cpu_core PMU), one logical CPU per physical core."""
    if policy is None:
        return None
    performance = cpu_list((sysfs/'devices/cpu_core/cpus').read_text())
    chosen = sorted(cpu for cpu in performance
                    if cpu == min(cpu_list((sysfs/f'devices/system/cpu/cpu{cpu}/topology/core_cpus_list').read_text())))
    if not chosen:
        raise ValueError('Nenhum núcleo de desempenho encontrado para a afinidade.')
    return chosen


def idle_baseline(directory, seconds):
    """Package energy with no workload running, just before the JVM starts."""
    energy = directory/'energy_uj'
    limit = int((directory/'max_energy_range_uj').read_text())
    first, before = int(energy.read_text()), time.monotonic_ns()
    time.sleep(seconds)
    last, after = int(energy.read_text()), time.monotonic_ns()
    joules = ((last - first) % limit) / 1e6
    return {'seconds': (after - before) / 1e9, 'energy_j': joules, 'mean_power_w': joules / ((after - before) / 1e9),
            'first_energy_uj': first, 'last_energy_uj': last}



def host_state():
    def read(path):
        try:
            return path.read_text().strip()
        except OSError:
            return None
    supplies = []
    for directory in Path('/sys/class/power_supply').glob('*'):
        if read(directory/'type') == 'Mains':
            supplies.append({'name':directory.name, 'online':read(directory/'online')})
    vmstat = dict(line.split() for line in (read(Path('/proc/vmstat')) or '').splitlines() if len(line.split()) == 2)
    try:
        profile = subprocess.run(['powerprofilesctl', 'get'], capture_output=True, text=True, timeout=5).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        profile = None
    cpufreq = Path('/sys/devices/system/cpu/cpu0/cpufreq')
    return {'at_utc':stamp(), 'mains':supplies,
            'swap_pages':{k:int(vmstat[k]) for k in ['pswpin','pswpout'] if k in vmstat},
            'power_profile':profile, 'platform_profile':read(Path('/sys/firmware/acpi/platform_profile')),
            'no_turbo':read(Path('/sys/devices/system/cpu/intel_pstate/no_turbo')),
            'governor':read(cpufreq/'scaling_governor'), 'energy_performance_preference':read(cpufreq/'energy_performance_preference'),
            'meminfo':read(Path('/proc/meminfo')), 'loadavg':read(Path('/proc/loadavg')),
            'thermal_zones':[{'name':d.name, 'type':read(d/'type'), 'temperature_millicelsius':read(d/'temp')}
                             for d in Path('/sys/class/thermal').glob('thermal_zone*')]}


def require_mains(state):
    if not any(supply['online'] == '1' for supply in state['mains']):
        raise ValueError('Notebook sem alimentação externa confirmada.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Preparar ou executar uma tarefa com SDKMAN e verificação RAPL.')
    parser.add_argument('modo', choices=['preparar','executar'])
    parser.add_argument('--configuracao', choices=list('ABCD'), required=True)
    parser.add_argument('--aplicacao')
    parser.add_argument('--categoria', choices=CATEGORIES, default='verificacao')
    parser.add_argument('--saida', type=Path)
    parser.add_argument('--config', type=Path, default=ROOT/'config/execucao.json')
    parser.add_argument('--sdkman-dir', type=Path, default=Path.home()/'.sdkman')
    parser.add_argument('--rapl-dir', type=Path, help='Diagnóstico; padrão definido no JSON.')
    parser.add_argument('--liberar-leitura', action='store_true', help='Somente preparar, no terminal do pesquisador, quando houver acesso negado.')
    parser.add_argument('--sessao', default='verificacao')
    parser.add_argument('--bloco')
    parser.add_argument('--ordem', type=int)
    args = parser.parse_args(argv)
    if args.modo == 'executar' and not args.aplicacao:
        parser.error('executar exige --aplicacao')
    if args.liberar_leitura and args.modo != 'preparar':
        parser.error('--liberar-leitura somente pode ser usado em preparar')
    parent = (ROOT/'dados'/CATEGORIES[args.categoria][0]).resolve()
    output = args.saida or parent/(datetime.now().strftime('%Y-%m-%d_%H%M%S')+'-'+uuid4().hex[:8])
    output = (output if output.is_absolute() else ROOT/output).resolve()
    if not output.is_relative_to(parent) or output == parent:
        parser.error('A saída deve ser um diretório novo dentro de '+str(parent))
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
    except FileExistsError:
        print('Saída já existe; nenhum arquivo foi sobrescrito: '+str(output), file=sys.stderr)
        return 2
    result = {'schema_version':1, 'started_at_utc':stamp(), 'mode':args.modo, 'configuration':args.configuracao,
              'category':CATEGORIES[args.categoria][1], 'application':args.aplicacao, 'output':str(output),
              'status':'failure', 'events':[], 'process_exit_code':None, 'workload_launched':False, 'measurement_verified':False,
              'session_id':args.sessao, 'block_id':args.bloco, 'order':args.ordem}
    started = time.monotonic()
    code = 2
    lock = None
    try:
        create_json(output/'started.json', {'at_utc':stamp(), 'wrapper_pid':os.getpid(), 'mode':args.modo})
        if os.geteuid() == 0:
            raise ValueError('Execute como pesquisador, sem sudo no script inteiro.')
        if any(os.environ.get(k) for k in INJECTED_OPTIONS):
            raise ValueError('Remova opções Java herdadas antes de executar: '+', '.join(k for k in INJECTED_OPTIONS if os.environ.get(k)))
        lock_path = ROOT/'dados/verificacao/.execucao.lock'
        lock_path.parent.mkdir(parents=True,exist_ok=True)
        lock = lock_path.open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = args.config.read_bytes()
        with (output/'config.json').open('xb') as stream:
            stream.write(raw)
        config = json.loads(raw)
        require_config(config, args.categoria)
        if args.categoria == 'oficial' and (not args.bloco or args.ordem is None or args.sessao == 'verificacao'):
            raise ValueError('Coleta oficial exige sessão, bloco e ordem do protocolo fixado.')
        result['config_sha256'] = hashlib.sha256(raw).hexdigest()
        create_json(output/'automation.json', {'source_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'scripts/executar.py',ROOT/'scripts/executar.sh',ROOT/'scripts/selecionar-java.sh']}})
        spec = config['configurations'][args.configuracao]
        params = config['applications'].get(args.aplicacao)
        if args.modo == 'executar' and params is None:
            raise ValueError('Aplicação ausente da configuração.')
        helper = ROOT/'scripts/selecionar-java.sh'
        command = ['bash', str(helper), str(args.sdkman_dir.resolve()), spec['sdkman_id'], str(output/'sdkman.json')]
        result['sdkman_command'] = command
        rc = process(command, ROOT, os.environ.copy(), output/'sdkman.stdout.log', output/'sdkman.stderr.log', 60)
        if rc:
            raise ValueError('SDKMAN não selecionou o JDK; conferir os logs, sem fallback para outro Java.')
        selection = json.loads((output/'sdkman.json').read_text())
        result['events'].append({'phase':'sdkman_selected', 'at_utc':stamp(), 'jdk':spec['sdkman_id'], 'java':selection['java_executable']})
        env = os.environ.copy()
        env.update(JAVA_HOME=selection['java_home'], LC_ALL='C')
        env['PATH'] = str(Path(selection['java_executable']).parent)+':'+env.get('PATH','')
        flags = ['-XX:+UseG1GC']
        if spec['compact_headers'] is not None:
            flags += ['-XX:'+('+' if spec['compact_headers'] else '-')+'UseCompactObjectHeaders']
        preflight = [selection['java_executable'], *flags, '-XX:+PrintFlagsFinal', '-XshowSettings:properties', '-version']
        rc = process(preflight, ROOT, env, output/'java-preflight.stdout.log', output/'java-preflight.stderr.log', 30)
        if rc:
            raise ValueError('O Java rejeitou as opções de pré-verificação.')
        identity = parse_identity((output/'java-preflight.stdout.log').read_text(), (output/'java-preflight.stderr.log').read_text())
        require_identity(identity, spec, selection)
        create_json(output/'java-preflight.json',identity)
        result['events'].append({'phase':'java_identity_verified', 'at_utc':stamp()})
        rapl = rapl_check(args.rapl_dir or Path(config['rapl_directory']), args.liberar_leitura, args.modo, result['events'])
        state = host_state()
        create_json(output/'system-before.json', state)
        require_mains(state)
        if args.modo == 'preparar':
            result['status'] = 'prepared'
            code = 0
        else:
            artifacts = {}
            for name in ['meter','dacapo']:
                path = (ROOT/config[name]['path']).resolve(strict=True)
                actual = sha256(path)
                if actual != config[name]['sha256']:
                    raise ValueError('SHA-256 divergente para '+name)
                artifacts[name] = {'path':str(path), 'sha256':actual}
            create_json(output/'artifacts.json',artifacts)
            cpus = affinity_cpus(config.get('cpu_affinity'))
            result['cpu_affinity'] = {'policy':config.get('cpu_affinity'), 'cpus':cpus}
            gc_log = []
            if config.get('gc_log'):
                if ':' in str(output):
                    raise ValueError('Caminho de saída com ":" não pode receber o log de GC.')
                gc_log = ['-Xlog:gc:file='+str(output/'gc.log')]
            command = [selection['java_executable'], '-Xms'+params['heap_initial'], '-Xmx'+params['heap_max'], *flags, *gc_log,
                       '-Dstudy.configuration='+args.configuracao, '-Dstudy.category='+CATEGORIES[args.categoria][1],
                       '-Dstudy.sessionId='+args.sessao, '-Dstudy.runId='+output.name,
                       '-Dstudy.output='+str(output/'medidor'), '-Dstudy.raplDir='+str(rapl),
                       '-Dstudy.sampleMillis='+str(config['sample_interval_ms']), '-Dstudy.maxGapMillis='+str(config['max_gap_ms']),
                       '-Dstudy.powerUpperBoundW='+str(config['assumed_power_upper_bound_w']),
                       '-Dstudy.measuredIterations='+str(measured_count(config))]
            for key, value in [('blockId',args.bloco), ('order',args.ordem)]:
                if value is not None:
                    command += ['-Dstudy.'+key+'='+str(value)]
            command += ['-jar', artifacts['meter']['path'], '-c', 'br.edu.utfpr.javaenergy.EnergyCallback',
                        '-n', str(warmups(config, args.aplicacao)+measured_count(config)), '-s', params['input'], '-t', str(params['threads']),
                        '--scratch-directory', str(output/'scratch'), args.aplicacao]
            create_json(output/'command.json', {'command':command, 'cwd':str(ROOT), 'timeout_seconds':config['process_timeout_seconds'], 'cpu_affinity':cpus})
            if config.get('idle_baseline_seconds'):
                result['idle_baseline'] = idle_baseline(rapl, config['idle_baseline_seconds'])
                create_json(output/'idle-baseline.json', result['idle_baseline'])
            result['events'].append({'phase':'workload_launch', 'at_utc':stamp()})
            result['workload_launched'] = True # Exact measurement boundaries remain in the Java records.
            result['process_exit_code'] = process(command, ROOT, env, output/'stdout.log', output/'stderr.log', config['process_timeout_seconds'], cpus)
            state = host_state()
            create_json(output/'system-after.json', state)
            require_mains(state)
            if result['process_exit_code'] != 0:
                raise ValueError('Processo Java terminou com erro; registros preservados.')
            result['verified_measurement'] = require_result(output, spec, selection, config, args.aplicacao, params, args.configuracao, CATEGORIES[args.categoria][1], cpus)
            result['measurement_verified'] = True
            result['status'] = 'success'
            code = 0
    except subprocess.TimeoutExpired as error:
        result['failure'] = 'Limite de duração excedido: '+str(error.timeout)+' s'
        result['timeout'] = True
        result['terminated_process_exit_code'] = getattr(error, 'terminated_returncode', None)
        if result['workload_launched']:
            result['process_exit_code'] = result['terminated_process_exit_code']
        code = 124
    except (Exception, KeyboardInterrupt) as error:
        result['failure'] = type(error).__name__+': '+str(error)
        if result['workload_launched'] and result['process_exit_code'] is None:
            result['process_exit_code'] = getattr(error,'terminated_returncode', None)
        code = 130 if isinstance(error, KeyboardInterrupt) else 2
    finally:
        result['finished_at_utc'] = stamp()
        result['total_wall_seconds'] = time.monotonic()-started
        result['wrapper_exit_code'] = code
        create_json(output/'resultado.json',result)
        if lock is not None:
            lock.close()
    print(json.dumps({'status':result['status'], 'output':str(output), 'failure':result.get('failure')},ensure_ascii=False))
    return code


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Sinal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
