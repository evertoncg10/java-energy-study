"""Análise de sensibilidade EXPLORATÓRIA (fora do registro prévio).

Pergunta: as conclusões da análise principal (razão das medianas com IC bootstrap pareado por bloco)
mudariam com outros métodos razoáveis? Nada aqui altera critérios ou decisões das hipóteses.

1. Testes globais por aplicação × medida, com A, B, C e D nos mesmos blocos:
   Friedman (postos dentro do bloco) e ANOVA em blocos casualizados sobre o log da medida.
2. Para cada comparação B/A, C/B e D/C: teste t pareado no log (razão das médias geométricas com IC 95%)
   e Wilcoxon pareado exato, ambos com Holm na mesma família da análise principal (aplicação × medida).
3. Concordância: a análise principal e o teste t indicam a mesma coisa (efeito para baixo, para cima
   ou nenhum efeito, conforme o IC exclua ou contenha 1)?
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from pae_analise.avaliacao import COMPARISONS, _value, official_valid
from pae_analise.consolidacao import ProcessRecord
from pae_analise.estatistica import (
    block_anova,
    friedman,
    holm,
    paired_log_t,
    wilcoxon_signed_rank,
)

SENSITIVITY_METRICS: dict[str, str] = {
    "energy_j": "energia",
    "time_s": "tempo",
    "power_w": "potência média",
}
CONFIGURATIONS = ("A", "B", "C", "D")


def _direction(ci_low: float, ci_high: float) -> str:
    if ci_high < 1:
        return "menor"
    if ci_low > 1:
        return "maior"
    return "sem diferença"


def _complete_blocks(records: Sequence[ProcessRecord], app: str, metric: str) -> dict[int, dict[str, float]]:
    """Blocos em que as quatro configurações têm valor positivo da medida."""
    blocks: dict[int, dict[str, float]] = {}
    for record in records:
        if record.application != app or record.block is None:
            continue
        value = _value(record, metric)
        if value is not None and value > 0:
            blocks.setdefault(record.block, {})[record.configuration] = value
    return {b: v for b, v in blocks.items() if all(c in v for c in CONFIGURATIONS)}


def omnibus_tests(records: Sequence[ProcessRecord]) -> list[dict[str, Any]]:
    """Friedman e ANOVA em blocos (log da medida) por aplicação × medida."""
    valid = official_valid(records)
    rows: list[dict[str, Any]] = []
    for app in sorted({r.application for r in valid}):
        role = next(r.role for r in valid if r.application == app)
        for metric, label in SENSITIVITY_METRICS.items():
            blocks = _complete_blocks(valid, app, metric)
            if len(blocks) < 2:
                continue
            table = [[blocks[b][c] for c in CONFIGURATIONS] for b in sorted(blocks)]
            fr = friedman(table)
            anova = block_anova([[math.log(v) for v in row] for row in table])
            rows.append(
                {
                    "application": app,
                    "role": role,
                    "metric": metric,
                    "label": label,
                    "blocks": fr.blocks,
                    "friedman_chi2": fr.statistic,
                    "friedman_df": fr.df1,
                    "friedman_p": fr.p_value,
                    "anova_f": anova.statistic,
                    "anova_df1": anova.df1,
                    "anova_df2": anova.df2,
                    "anova_p": anova.p_value,
                }
            )
    return rows


def contrast_tests(
    records: Sequence[ProcessRecord], comparisons: Sequence[dict[str, Any]], level: float = 0.95
) -> list[dict[str, Any]]:
    """Teste t pareado no log e Wilcoxon por comparação, ao lado do resultado da análise principal."""
    valid = official_valid(records)
    rows: list[dict[str, Any]] = []
    for app in sorted({r.application for r in valid}):
        role = next(r.role for r in valid if r.application == app)
        for metric, label in SENSITIVITY_METRICS.items():
            blocks = _complete_blocks(valid, app, metric)
            family: list[dict[str, Any]] = []
            for numerator, denominator in COMPARISONS:
                pairs = [(blocks[b][numerator], blocks[b][denominator]) for b in sorted(blocks)]
                if len(pairs) < 2:
                    continue
                t_test = paired_log_t(pairs, level)
                signed = wilcoxon_signed_rank(pairs)
                comparison = f"{numerator}/{denominator}"
                main = next(
                    (
                        r
                        for r in comparisons
                        if r["application"] == app and r["metric"] == metric and r["comparison"] == comparison
                    ),
                    None,
                )
                main_direction = _direction(main["ci_low"], main["ci_high"]) if main else None
                t_direction = _direction(t_test.ci_low, t_test.ci_high)
                family.append(
                    {
                        "application": app,
                        "role": role,
                        "metric": metric,
                        "label": label,
                        "comparison": comparison,
                        "pairs": t_test.pairs,
                        "main_ratio": main["ratio"] if main else None,
                        "main_ci_low": main["ci_low"] if main else None,
                        "main_ci_high": main["ci_high"] if main else None,
                        "main_direction": main_direction,
                        "geo_ratio": t_test.ratio,
                        "geo_ci_low": t_test.ci_low,
                        "geo_ci_high": t_test.ci_high,
                        "t_statistic": t_test.statistic,
                        "t_p": t_test.p_value,
                        "t_direction": t_direction,
                        "wilcoxon_w_plus": signed.statistic,
                        "wilcoxon_p": signed.p_value,
                        "agrees": main_direction == t_direction if main_direction else None,
                    }
                )
            for key in ("t_p", "wilcoxon_p"):
                for row, adjusted in zip(family, holm([r[key] for r in family]), strict=True):
                    row[f"{key}_holm"] = adjusted
            rows.extend(family)
    return rows


def summary_lines(omnibus: Sequence[dict[str, Any]], contrasts: Sequence[dict[str, Any]]) -> list[str]:
    lines = ["", "Análise de sensibilidade (EXPLORATÓRIA, fora do registro prévio):"]
    for row in omnibus:
        lines.append(
            f"  {row['application']:<9} {row['label']:<15} Friedman χ²({row['friedman_df']:.0f}) ="
            f" {row['friedman_chi2']:.2f}, p = {row['friedman_p']:.3g};"
            f" ANOVA em blocos (log) F({row['anova_df1']:.0f}, {row['anova_df2']:.0f}) ="
            f" {row['anova_f']:.2f}, p = {row['anova_p']:.3g}"
        )
    disagreements = [r for r in contrasts if r["agrees"] is False]
    lines.append(
        f"  Contrastes com a mesma conclusão da análise principal: {sum(1 for r in contrasts if r['agrees'])}"
        f" de {sum(1 for r in contrasts if r['agrees'] is not None)}"
    )
    for row in disagreements:
        lines.append(
            f"    diferente: {row['application']} {row['label']} {row['comparison']}: principal"
            f" {row['main_direction']} [{row['main_ci_low']:.4f}; {row['main_ci_high']:.4f}],"
            f" teste t {row['t_direction']} [{row['geo_ci_low']:.4f}; {row['geo_ci_high']:.4f}]"
        )
    return lines
