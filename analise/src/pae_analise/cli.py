"""Linha de comando ``pae-analise``.

Comandos:
    consolidar   grava a base consolidada (uma linha por processo) da coleta oficial e dos pilotos;
    analisar     consolida e roda toda a análise (descritiva, razões, critérios, hipóteses,
                 sensibilidade exploratória e figuras).

Exemplos (a partir da raiz do repositório):
    pae-analise consolidar --saida resultados/consolidacao
    pae-analise analisar --saida resultados/analise
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from pae_analise import __version__, figuras, sensibilidade
from pae_analise.avaliacao import (
    AnalysisSettings,
    compare_configurations,
    criterion_e1,
    criterion_e2,
    criterion_e3,
    criterion_e4,
    criterion_e5,
    criterion_e6,
    decompose_energy,
    describe_cells,
    evaluate_hypotheses,
    hypothesis_h4,
)
from pae_analise.consolidacao import consolidate, consolidate_pilots, load_config
from pae_analise.relatorio import (
    metadata,
    prepare_output,
    records_as_json,
    records_as_rows,
    summary_text,
    write_csv,
    write_json,
)

log = logging.getLogger("pae_analise")


def find_root(start: Path) -> Path:
    """Sobe a partir de ``start`` até achar a raiz do repositório (pasta com ``config/execucao.json``)."""
    for folder in (start, *start.parents):
        if (folder / "config" / "execucao.json").is_file():
            return folder
    raise FileNotFoundError("Raiz do repositório não encontrada; informe --raiz.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pae-analise", description="Análise dos dados do protocolo PAE-JVM.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--raiz", type=Path, help="Raiz do repositório (padrão: procurada a partir da pasta atual).")
    parser.add_argument("-v", "--verboso", action="store_true", help="Mostra mensagens de andamento.")
    commands = parser.add_subparsers(dest="comando", required=True)

    consolidar = commands.add_parser("consolidar", help="Gera a base consolidada (uma linha por processo).")
    consolidar.add_argument("--saida", type=Path, required=True, help="Pasta nova para os arquivos.")

    analisar = commands.add_parser("analisar", help="Consolida e roda a análise completa.")
    analisar.add_argument("--saida", type=Path, required=True, help="Pasta nova para os arquivos.")
    analisar.add_argument(
        "--reamostragens", type=int, default=10_000, help="Reamostragens do bootstrap (padrão 10000)."
    )
    analisar.add_argument("--semente", type=int, default=20261101, help="Semente do bootstrap (padrão 20261101).")
    analisar.add_argument("--sem-figuras", action="store_true", help="Não gera figuras.")
    return parser


def run_consolidate(root: Path, output: Path) -> int:
    records = consolidate(root)
    pilots = consolidate_pilots(root, load_config(root))
    prepare_output(output)
    write_csv(output / "base-oficial.csv", records_as_rows(records))
    write_json(output / "base-oficial.json", records_as_json(records))
    write_csv(output / "base-pilotos.csv", records_as_rows(pilots))
    invalid = [r for r in records if not r.valid]
    print(f"Base oficial: {len(records)} processos, {len(records) - len(invalid)} válidos.")
    print(f"Pilotos: {len(pilots)} processos (base separada).")
    for record in invalid:
        print(f"INVÁLIDO {record.source}: {'; '.join(record.problems)}")
    return 0 if not invalid else 1


def run_analysis(root: Path, output: Path, settings: AnalysisSettings, with_figures: bool) -> int:
    log.info("Consolidando os dados brutos de %s", root)
    records = consolidate(root)
    pilots = consolidate_pilots(root, load_config(root))
    prepare_output(output)
    log.info("Calculando razões com %d reamostragens", settings.resamples)
    comparisons = compare_configurations(records, settings)
    sessions = sorted({r.session for r in records})
    criteria = {
        "E1": criterion_e1(records),
        "E2": criterion_e2(records),
        "E3": criterion_e3(comparisons),
        "E4": criterion_e4(records),
        "E5": criterion_e5(records, root),
        "E6": criterion_e6(root, sessions),
    }
    hypotheses = evaluate_hypotheses(comparisons)
    h4 = hypothesis_h4(comparisons)
    decomposition = decompose_energy(records)
    omnibus = sensibilidade.omnibus_tests(records)
    contrasts = sensibilidade.contrast_tests(records, comparisons, settings.level)

    write_csv(output / "base-oficial.csv", records_as_rows(records))
    write_json(output / "base-oficial.json", records_as_json(records))
    write_csv(output / "base-pilotos.csv", records_as_rows(pilots))
    write_csv(output / "descritiva.csv", describe_cells(records))
    write_csv(output / "razoes.csv", comparisons)
    write_csv(output / "decomposicao.csv", decomposition)
    write_csv(output / "hipoteses.csv", hypotheses)
    write_json(output / "criterios.json", criteria)
    write_json(output / "h4.json", h4)
    write_csv(output / "sensibilidade-global.csv", omnibus)
    write_csv(output / "sensibilidade-contrastes.csv", contrasts)
    write_json(output / "metadados.json", metadata(root, records, settings))
    text = summary_text(records, comparisons, criteria, hypotheses, h4, decomposition)
    text += "\n".join(sensibilidade.summary_lines(omnibus, contrasts)) + "\n"
    (output / "resumo.txt").write_text(text, encoding="utf-8")

    if with_figures:
        if figuras.available():
            folder = output / "figuras"
            folder.mkdir()
            figuras.plot_ratios(comparisons, folder)
            figuras.plot_decomposition(comparisons, folder)
            figuras.plot_memory(comparisons, folder)
            figuras.plot_sessions(criteria["E2"], folder)
            figuras.plot_energy(records, folder)
            figuras.plot_flow(folder)
        else:
            print("Aviso: matplotlib não instalado; figuras não geradas (pip install -e .[figuras]).")
    print(text, end="")
    print(f"Resultados gravados em {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verboso else logging.WARNING, format="%(message)s")
    try:
        root = (args.raiz or find_root(Path.cwd())).resolve()
        if args.comando == "consolidar":
            return run_consolidate(root, args.saida)
        settings = AnalysisSettings(resamples=args.reamostragens, seed=args.semente)
        return run_analysis(root, args.saida, settings, not args.sem_figuras)
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
