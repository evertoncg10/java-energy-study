#!/usr/bin/env python3
"""Figuras do artigo focado nos cabeçalhos compactos do Java 25.

O artigo usa só a parte da coleta oficial que compara o Java 25 sem e com cabeçalhos compactos
(pergunta QC1, hipóteses H1 a H4). Este script gera, a partir dos resultados já publicados, as
duas figuras do artigo sem mudar nenhum número.

    fluxo-cabecalhos    etapas do PAE-JVM, com as hipóteses H1–H4 e sem o A12;
    memoria-cabecalhos  mudança ao ligar os cabeçalhos compactos na energia, no heap e na coleta
                        de lixo, com o eixo escrito "com e sem cabeçalhos compactos".

As figuras do estudo completo, com H1–H5 e a notação D/C, continuam em
resultados/oficial-20261101-termos/figuras.

Uso, na pasta raiz do projeto:
    python scripts/figuras_artigo_cabecalhos.py --saida resultados/<pasta nova>

Arquivos gerados: fluxo-cabecalhos.png/.pdf, memoria-cabecalhos.png/.pdf e metadados.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analise" / "src"))

from pae_analise import figuras  # noqa: E402

RATIOS = ROOT / "resultados" / "oficial-20261101-termos" / "razoes.csv"
NUMBERS = ("ratio", "ci_low", "ci_high")
XLABEL = "variação com e sem cabeçalhos compactos (razão das medianas, IC 95%)"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_comparisons(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            item: dict[str, object] = dict(row)
            for key in NUMBERS:
                item[key] = float(row[key]) if row[key] else None
            rows.append(item)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", type=Path, required=True, help="Pasta nova para as figuras.")
    args = parser.parse_args(argv)
    if not figuras.available():
        print("matplotlib não está instalado.", file=sys.stderr)
        return 1
    if args.saida.exists() and any(args.saida.iterdir()):
        print(
            f"A pasta {args.saida} já tem arquivos; escolha uma pasta nova.",
            file=sys.stderr,
        )
        return 1
    args.saida.mkdir(parents=True, exist_ok=True)

    comparisons = read_comparisons(RATIOS)
    paths = figuras.plot_flow(args.saida, steps=figuras.PAE_JVM_STEPS_CABECALHOS, name="fluxo-cabecalhos")
    paths += figuras.plot_memory(comparisons, args.saida, xlabel=XLABEL, name="memoria-cabecalhos")

    metadata = {
        "script": "scripts/figuras_artigo_cabecalhos.py",
        "entrada": RATIOS.relative_to(ROOT).as_posix(),
        "entrada_sha256": sha256(RATIOS),
        "arquivos": [p.name for p in paths],
    }
    (args.saida / "metadados.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for path in paths:
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
