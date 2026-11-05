#!/usr/bin/env python3
"""Análise da sessão ingênua do critério E7 (T45), fora da amostra oficial.

Lê os processos de uma sessão ingênua (dados/ingenua/<sessão>), calcula as mesmas razões do protocolo
(B/A, C/B, D/C) com a repetição no papel do bloco e compara a conclusão e a variação com a coleta
oficial (resultados/oficial-20261101-termos). O critério E7 é descritivo: o que se relata é se a
medição ingênua mudaria a conclusão.

Uso, na pasta raiz do projeto:
    python3 scripts/analisar_ingenua.py --sessao dados/ingenua/<sessão> --saida resultados/<pasta nova>
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analise" / "src"))

from pae_analise.consolidacao import PILOT, build_record, read_json  # noqa: E402
from pae_analise.estatistica import coefficient_of_variation, paired_block_ratio  # noqa: E402

OFFICIAL = ROOT / "resultados" / "oficial-20261101-termos"
COMPARISONS = (("B", "A"), ("C", "B"), ("D", "C"))
METRICS = {"energy_j": "energia", "time_s": "tempo", "power_w": "potência média"}
MAIN = ("lusearch", "pmd")


def direction(low: float, high: float) -> str:
    if high < 1:
        return "menor"
    if low > 1:
        return "maior"
    return "sem diferença"


def package_celsius(path: Path) -> float | None:
    if not path.is_file():
        return None
    for zone in read_json(path).get("thermal_zones", []):
        if zone.get("type") == "x86_pkg_temp":
            return int(zone["temperature_millicelsius"]) / 1000
    return None


def load_session(folder: Path) -> list[dict]:
    config = read_json(ROOT / "config" / "ingenua-e7.json")
    rows = []
    for process in sorted(p for p in folder.iterdir() if p.is_dir() and (p / "resultado.json").is_file()):
        record = build_record(process, ROOT, config, PILOT, folder.name)
        rep = int(process.name[1:3])
        rows.append(
            {
                "name": process.name,
                "repetition": rep,
                "order": int(process.name[4:7]),
                "application": record.application,
                "configuration": record.configuration,
                "java_runtime_version": record.java_runtime_version,
                "compact_headers": record.compact_headers,
                "energy_j": record.energy_j,
                "time_s": record.time_s,
                "power_w": record.power_w,
                "gc_pauses": record.gc_pauses,
                "start_celsius": package_celsius(process / "system-before.json"),
                "valid": record.valid,
                "problems": "; ".join(record.problems),
            }
        )
    return rows


def official_tables() -> tuple[dict, dict]:
    ratios = {}
    with (OFFICIAL / "razoes.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            ratios[(row["application"], row["metric"], row["comparison"])] = row
    cvs = {}
    with (OFFICIAL / "descritiva.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            cvs[(row["application"], row["configuration"], row["metric"])] = row
    return ratios, cvs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sessao", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # acentos corretos no terminal do Windows
    if args.saida.exists():
        print(f"A pasta de saída já existe e não será sobrescrita: {args.saida}", file=sys.stderr)
        return 2

    rows = load_session(args.sessao)
    invalid = [r["name"] for r in rows if not r["valid"]]
    official_ratios, official_cvs = official_tables()
    apps = sorted({r["application"] for r in rows})

    descriptive = []
    for app in apps:
        for conf in "ABCD":
            cell = [r for r in rows if r["application"] == app and r["configuration"] == conf and r["valid"]]
            for metric in METRICS:
                values = [float(r[metric]) for r in cell]
                ref = official_cvs.get((app, conf, metric))
                descriptive.append(
                    {
                        "application": app,
                        "configuration": conf,
                        "metric": metric,
                        "n": len(values),
                        "median": statistics.median(values),
                        "cv": coefficient_of_variation(values),
                        "official_median": float(ref["median"]) if ref else None,
                        "official_cv": float(ref["cv"]) if ref else None,
                    }
                )

    comparison = []
    for app in apps:
        for num, den in COMPARISONS:
            for metric in METRICS:
                by_rep: dict[int, dict[str, float]] = {}
                for r in rows:
                    if r["application"] == app and r["valid"] and r["configuration"] in (num, den):
                        by_rep.setdefault(r["repetition"], {})[r["configuration"]] = float(r[metric])
                pairs = {k: (v[num], v[den]) for k, v in by_rep.items() if num in v and den in v}
                ratio = paired_block_ratio(pairs)
                ref = official_ratios.get((app, metric, f"{num}/{den}"))
                naive_dir = direction(ratio.ci_low, ratio.ci_high)
                off_dir = direction(float(ref["ci_low"]), float(ref["ci_high"])) if ref else None
                comparison.append(
                    {
                        "application": app,
                        "role": "principal" if app in MAIN else "exploratorio",
                        "metric": metric,
                        "comparison": f"{num}/{den}",
                        "repetitions": ratio.blocks,
                        "naive_ratio": ratio.estimate,
                        "naive_ci_low": ratio.ci_low,
                        "naive_ci_high": ratio.ci_high,
                        "naive_half_width_pp": ratio.half_width * 100,
                        "naive_direction": naive_dir,
                        "official_ratio": float(ref["ratio"]) if ref else None,
                        "official_ci_low": float(ref["ci_low"]) if ref else None,
                        "official_ci_high": float(ref["ci_high"]) if ref else None,
                        "official_half_width_pp": float(ref["half_width_pp"]) if ref else None,
                        "official_direction": off_dir,
                        "same_direction": naive_dir == off_dir if off_dir else None,
                    }
                )

    # Efeito da posição fixa: temperatura no início de cada processo, por configuração.
    position = []
    for app in apps:
        for conf in "ABCD":
            temps = [r["start_celsius"] for r in rows if r["application"] == app and r["configuration"] == conf]
            temps = [t for t in temps if t is not None]
            position.append(
                {"application": app, "configuration": conf, "median_start_celsius": statistics.median(temps)}
            )

    args.saida.mkdir(parents=True)
    write_csv(args.saida / "base-ingenua.csv", rows)
    write_csv(args.saida / "descritiva-ingenua.csv", descriptive)
    write_csv(args.saida / "comparacao-e7.csv", comparison)
    write_csv(args.saida / "temperatura-por-posicao.csv", position)
    summary = report(args.sessao, rows, invalid, descriptive, comparison, position)
    write_text(args.saida / "resumo-e7.txt", summary)
    write_text(
        args.saida / "metadados.json",
        json.dumps(
            {
                "sessao": args.sessao.name,
                "processos": len(rows),
                "invalidos": invalid,
                "referencia_oficial": OFFICIAL.relative_to(ROOT).as_posix(),
                "bootstrap": {"reamostragens": 10000, "nivel": 0.95, "semente": 20261101, "bloco": "repetição"},
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
    )
    print(summary)
    return 0


def write_text(path: Path, text: str) -> None:
    # Fim de linha sempre LF, como no pacote de análise, para o arquivo sair igual no Windows e no Linux.
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in row.items()})


def report(session: Path, rows, invalid, descriptive, comparison, position) -> str:
    lines = [
        "CRITÉRIO E7 – COMPARAÇÃO COM A MEDIÇÃO INGÊNUA (descritivo, fora da amostra oficial)",
        f"Sessão: {session.name}  processos: {len(rows)}  inválidos: {len(invalid)}",
        "Medição ingênua: ordem fixa A, B, C, D; sem núcleos fixos; sem pausas; 1 preparação + 1 iteração medida.",
        "Desvio: o registro prévio fala em 'sem preparação'; o medidor exige ao menos 1 iteração de preparação.",
        "",
        "Razões (mediana ingênua com IC 95% bootstrap pareado por repetição) contra a coleta oficial:",
    ]
    for row in comparison:
        mark = "igual" if row["same_direction"] else "DIFERENTE"
        lines.append(
            f"  {row['application']:<9} {row['comparison']} {METRICS[row['metric']]:<15}"
            f" ingênua {row['naive_ratio']:.4f} [{row['naive_ci_low']:.4f}; {row['naive_ci_high']:.4f}]"
            f" {row['naive_direction']:<13}"
            f" oficial {row['official_ratio']:.4f} [{row['official_ci_low']:.4f}; {row['official_ci_high']:.4f}]"
            f" {row['official_direction']:<13} conclusão {mark}"
        )
    main_rows = [r for r in comparison if r["role"] == "principal"]
    changed = [r for r in main_rows if not r["same_direction"]]
    lines += [
        "",
        (
            f"Cargas principais: {len(main_rows) - len(changed)} de {len(main_rows)} conclusões iguais;"
            f" {len(changed)} mudariam com a medição ingênua."
        ),
    ]
    for r in changed:
        lines.append(
            f"  mudaria: {r['application']} {r['comparison']} {METRICS[r['metric']]}"
            f" (oficial {r['official_direction']}, ingênua {r['naive_direction']})"
        )
    widths = [(r["naive_half_width_pp"], r["official_half_width_pp"]) for r in main_rows if r["metric"] == "energy_j"]
    lines += [
        "",
        "Meia-largura do IC da energia (pontos percentuais), cargas principais:",
        (
            f"  ingênua mediana {statistics.median(w[0] for w in widths):.2f} pp;"
            f" oficial mediana {statistics.median(w[1] for w in widths):.2f} pp"
        ),
        "",
        "CV da energia por carga x configuração (ingênua / oficial):",
    ]
    for row in descriptive:
        if row["metric"] == "energy_j":
            lines.append(
                f"  {row['application']:<9} {row['configuration']}"
                f"  {row['cv'] * 100:5.2f}% / {row['official_cv'] * 100:5.2f}%"
                f"   mediana {row['median']:.1f} J / {row['official_median']:.1f} J"
            )
    lines += ["", "Temperatura do pacote no início do processo (mediana, °C), pela posição fixa:"]
    for row in position:
        lines.append(f"  {row['application']:<9} {row['configuration']}  {row['median_start_celsius']:.0f}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
