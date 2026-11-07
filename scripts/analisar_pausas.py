#!/usr/bin/env python3
"""Peso das pausas de coleta de lixo no tempo de cada processo (cálculo descritivo).

Este cálculo não faz parte do registro prévio. Ele explica por que a redução da coleta de lixo com os
cabeçalhos compactos (H3b) não apareceu na energia (H1). Para cada processo válido da base oficial,
divide o tempo total de pausa de coleta pelo tempo total do processo e, para cada aplicação e
configuração, guarda a mediana dessa fração. Depois estima o efeito máximo da redução de pausas
medida em D/C (resultados/oficial-20261101-termos/razoes.csv) sobre o tempo total.

Uso, na pasta raiz do projeto:
    python scripts/analisar_pausas.py --saida resultados/<pasta nova>

Para conferir os arquivos publicados:
    python scripts/analisar_pausas.py --saida resultados/pausas-reproducao
    python scripts/comparar_resultados.py resultados/pausas-gc-20261107 resultados/pausas-reproducao

Arquivos gerados: pausas.csv, resumo-pausas.txt e metadados.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL = ROOT / "resultados" / "oficial-20261101-termos"
CONFIGURATIONS = ("A", "B", "C", "D")
LABELS = {
    "A": "Java 17",
    "B": "Java 21",
    "C": "Java 25 sem cabeçalhos compactos",
    "D": "Java 25 com cabeçalhos compactos",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def pause_table(base: list[dict[str, str]]) -> list[dict[str, object]]:
    """Mediana, por aplicação e configuração, da fração do tempo do processo gasta em pausas de coleta."""
    valid = [r for r in base if r["valid"] == "True"]
    rows: list[dict[str, object]] = []
    for application in sorted({r["application"] for r in valid}):
        for configuration in CONFIGURATIONS:
            group = [r for r in valid if r["application"] == application and r["configuration"] == configuration]
            if not group:
                continue
            fractions = [float(r["gc_pause_time_ms"]) / 1000 / float(r["wall_seconds"]) for r in group]
            rows.append(
                {
                    "application": application,
                    "role": group[0]["role"],
                    "configuration": configuration,
                    "processes": len(group),
                    "median_gc_pause_time_ms": statistics.median(float(r["gc_pause_time_ms"]) for r in group),
                    "median_wall_seconds": statistics.median(float(r["wall_seconds"]) for r in group),
                    "median_pause_fraction_pct": statistics.median(fractions) * 100,
                }
            )
    return rows


def pause_reduction(ratios: list[dict[str, str]]) -> dict[str, float]:
    """Mudança percentual do tempo de pausa em D/C, por aplicação, lida de razoes.csv."""
    return {
        r["application"]: float(r["change_pct"])
        for r in ratios
        if r["metric"] == "gc_pause_time_ms" and r["comparison"] == "D/C"
    }


def effect_table(table: list[dict[str, object]], reduction: dict[str, float]) -> list[dict[str, object]]:
    """Efeito máximo da redução de pausas sobre o tempo total, nas aplicações principais.

    É a fração de pausas em C multiplicada pela mudança das pausas em D/C.
    """
    rows: list[dict[str, object]] = []
    for row in table:
        application = str(row["application"])
        if row["configuration"] != "C" or row["role"] != "principal" or application not in reduction:
            continue
        fraction = float(str(row["median_pause_fraction_pct"]))
        change = reduction[application]
        rows.append(
            {
                "application": application,
                "pause_fraction_c_pct": fraction,
                "pause_change_dc_pct": change,
                "max_time_effect_pct": fraction * abs(change) / 100,
            }
        )
    return rows


def fmt(value: object) -> object:
    return f"{value:.6g}" if isinstance(value, float) else value


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: fmt(v) for k, v in row.items()})


def pct(value: float) -> str:
    return f"{value:.2f}%".replace(".", ",")


def report(table: list[dict[str, object]], effects: list[dict[str, object]], base: Path) -> str:
    lines = [
        "Peso das pausas de coleta de lixo no tempo de cada processo",
        "Cálculo descritivo, fora do registro prévio.",
        f"Entrada: {base.relative_to(ROOT).as_posix() if base.is_relative_to(ROOT) else base.name}",
        "",
        "Mediana de (tempo de pausa de coleta / tempo total do processo), processos válidos:",
    ]
    for row in table:
        label = LABELS[str(row["configuration"])]
        lines.append(
            f"  {row['application']:<9} {row['configuration']}  {pct(float(str(row['median_pause_fraction_pct']))):>6}"
            f"  ({row['processes']} processos; {label})"
        )
    lines += [
        "",
        "Efeito máximo da redução de pausas com os cabeçalhos compactos (D/C) sobre o tempo total,"
        " nas aplicações principais:",
    ]
    for row in effects:
        lines.append(
            f"  {row['application']:<9} pausas em C {pct(float(str(row['pause_fraction_c_pct'])))}"
            f" x mudança das pausas em D/C {pct(float(str(row['pause_change_dc_pct'])))}"
            f" = no máximo {pct(float(str(row['max_time_effect_pct'])))} do tempo total"
        )
    lines += [
        "",
        "Leitura: mesmo que toda a redução de pausas virasse redução de tempo, o efeito ficaria abaixo",
        "da margem de erro do protocolo para a energia (cerca de 1,3 pontos percentuais em D/C).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--saida", type=Path, required=True, help="pasta nova para os arquivos gerados")
    parser.add_argument("--base", type=Path, default=OFFICIAL / "base-oficial.csv", help="base consolidada")
    parser.add_argument("--razoes", type=Path, default=OFFICIAL / "razoes.csv", help="razões com IC 95%%")
    args = parser.parse_args(argv)

    if args.saida.exists() and any(args.saida.iterdir()):
        print(f"A pasta {args.saida} já existe e não está vazia. Use uma pasta nova.", file=sys.stderr)
        return 2
    args.saida.mkdir(parents=True, exist_ok=True)

    table = pause_table(read_rows(args.base))
    effects = effect_table(table, pause_reduction(read_rows(args.razoes)))
    summary = report(table, effects, args.base.resolve())

    write_csv(args.saida / "pausas.csv", table)
    write_csv(args.saida / "efeito-pausas.csv", effects)
    write_text(args.saida / "resumo-pausas.txt", summary)
    write_text(
        args.saida / "metadados.json",
        json.dumps(
            {
                "calculo": "descritivo, fora do registro prévio",
                "input_sha256": {"base": sha256(args.base), "razoes": sha256(args.razoes)},
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
    )
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
