#!/usr/bin/env python3
"""Freeze a finished session folder with a SHA-256 manifest, or check a folder against one."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def list_files(folder):
    files = []
    for path in sorted(p for p in folder.rglob('*') if p.is_file()):
        files.append({'path': path.relative_to(folder).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha256(path)})
    return files


def folder_digest(files):
    # One hash over the sorted list, short enough to copy into a Trello card or the article.
    lines = ''.join('%s  %s\n' % (f['sha256'], f['path']) for f in files)
    return hashlib.sha256(lines.encode('utf-8')).hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def summarize(folder):
    plan = read_json(folder/'plano-antes-execucao.json') or {}
    summaries = []
    for path in sorted(folder.glob('*-resumo-sessao.json')):
        data = read_json(path) or {}
        summaries.append({'file': path.name, 'status': data.get('status'), 'failure': data.get('failure'),
                          'elapsed_seconds': data.get('elapsed_seconds')})
    records = []
    progress = folder/'progresso.jsonl'
    if progress.exists():
        records = [json.loads(line) for line in progress.read_text(encoding='utf-8').splitlines() if line.strip()]
    stamps = [d.get('at_utc') for p in sorted(folder.glob('*-ambiente-*.json')) if (d := read_json(p))]
    stamps = sorted(s for s in stamps if s)
    return {'category': plan.get('category'), 'seed': plan.get('seed'), 'first_block': plan.get('first_block'),
            'blocks': plan.get('blocks'), 'planned_processes': len(plan.get('runs', [])) + (1 if plan.get('session_warmup') else 0),
            'plan_created_at_utc': plan.get('created_at_utc'),
            'first_environment_at_utc': stamps[0] if stamps else None, 'last_environment_at_utc': stamps[-1] if stamps else None,
            'attempts': len(records), 'successes': sum(1 for r in records if r.get('success')),
            'failures': [r.get('name') for r in records if not r.get('success')],
            'retries': [r.get('name') for r in records if str(r.get('name', '')).endswith('-repeticao')],
            'sessions': summaries}


def make_manifest(folder, plan=None):
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise FileNotFoundError('Pasta da sessão não encontrada: '+str(folder))
    files = list_files(folder)
    if not files:
        raise ValueError('Pasta da sessão vazia: '+str(folder))
    try:
        relative = folder.relative_to(ROOT).as_posix()
    except ValueError:
        relative = None
    manifest = {'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'session_folder': folder.name, 'session_path_in_repository': relative,
                'summary': summarize(folder), 'file_count': len(files), 'total_bytes': sum(f['bytes'] for f in files),
                'folder_sha256': folder_digest(files), 'files': files}
    if plan:
        manifest['registered_plan'] = {'path': Path(plan).name, 'sha256': sha256(Path(plan))}
    return manifest


def check(folder, manifest):
    folder = Path(folder).resolve()
    expected = {f['path']: f for f in manifest['files']}
    found = {f['path']: f for f in list_files(folder)}
    problems = []
    for path in sorted(expected.keys() - found.keys()):
        problems.append('faltando: '+path)
    for path in sorted(found.keys() - expected.keys()):
        problems.append('a mais: '+path)
    for path in sorted(expected.keys() & found.keys()):
        if expected[path]['sha256'] != found[path]['sha256']:
            problems.append('alterado: '+path)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description='Gerar ou conferir o manifesto SHA-256 de uma sessão encerrada.')
    sub = parser.add_subparsers(dest='modo', required=True)
    g = sub.add_parser('gerar')
    g.add_argument('--sessao', type=Path, required=True, help='Pasta da sessão, por exemplo dados/brutos/20261024T170000Z.')
    g.add_argument('--saida', type=Path, required=True, help='Arquivo novo do manifesto, fora da pasta da sessão.')
    g.add_argument('--plano', type=Path, help='Plano registrado antes da sessão, para conferir o hash.')
    c = sub.add_parser('conferir')
    c.add_argument('--sessao', type=Path, required=True)
    c.add_argument('--manifesto', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.modo == 'gerar':
        if args.saida.resolve().is_relative_to(args.sessao.resolve()):
            raise ValueError('O manifesto deve ficar fora da pasta da sessão.')
        manifest = make_manifest(args.sessao, args.plano)
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        with args.saida.open('x', encoding='utf-8') as stream:  # Never overwrite an earlier manifest.
            json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        s = manifest['summary']
        print('MANIFESTO=%s arquivos=%d bytes=%d tentativas=%d sucessos=%d falhas=%d' % (
            args.saida, manifest['file_count'], manifest['total_bytes'], s['attempts'], s['successes'], len(s['failures'])))
        print('SHA256_PASTA='+manifest['folder_sha256'])
        return 0
    manifest = json.loads(args.manifesto.read_text(encoding='utf-8'))
    problems = check(args.sessao, manifest)
    for problem in problems:
        print(problem)
    print('CONFERE' if not problems else 'NAO_CONFERE (%d diferenças)' % len(problems))
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
