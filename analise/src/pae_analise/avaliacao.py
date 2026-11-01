"""Critérios de avaliação do artefato (E1–E6) e hipóteses (H1–H5) do registro prévio.

Os limites e as regras de decisão vêm de ``config/registro-previo.json`` e do desenho DSR
(seções 5.2 e 5.3) e não são alterados aqui. Só entram processos oficiais válidos.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pae_analise.consolidacao import OFFICIAL, ProcessRecord, read_json, read_json_lines
from pae_analise.estatistica import (
    a12_magnitude,
    coefficient_of_variation,
    holm,
    mann_whitney,
    paired_block_ratio,
    spread,
    vargha_delaney_a12,
)

# Comparações registradas: (numerador, denominador).
COMPARISONS: tuple[tuple[str, str], ...] = (("B", "A"), ("C", "B"), ("D", "C"))

# Medidas comparadas, na ordem das tabelas. Nome do campo → rótulo.
METRICS: dict[str, str] = {
    "energy_j": "energia (J)",
    "time_s": "tempo (s)",
    "power_w": "potência média (W)",
    "gc_heap_after_median_mb": "heap após coleta (MB)",
    "gc_pauses": "número de coletas",
    "gc_pause_time_ms": "tempo de pausas (ms)",
}

E1_LIMIT = 0.05
E2_LIMIT = 0.05
E3_LIMIT_PP = 3.0
E4_LIMIT = 0.02
E6_SESSION_SECONDS = 5400
E6_FAILURE_SHARE = 0.05
POWER_BAND = (0.98, 1.02)


@dataclass(frozen=True)
class AnalysisSettings:
    resamples: int = 10_000
    level: float = 0.95
    seed: int = 20261101


def official_valid(records: Sequence[ProcessRecord]) -> list[ProcessRecord]:
    return [r for r in records if r.category == OFFICIAL and r.valid]


def _cells(records: Sequence[ProcessRecord]) -> dict[tuple[str, str], list[ProcessRecord]]:
    cells: dict[tuple[str, str], list[ProcessRecord]] = defaultdict(list)
    for record in records:
        cells[(record.application, record.configuration)].append(record)
    return dict(sorted(cells.items()))


def _value(record: ProcessRecord, metric: str) -> float | None:
    value = getattr(record, metric)
    return None if value is None else float(value)


def _roles(records: Sequence[ProcessRecord]) -> dict[str, str]:
    return {r.application: r.role or "" for r in records}


# ---------------------------------------------------------------- estatísticas descritivas


def describe_cells(records: Sequence[ProcessRecord]) -> list[dict[str, Any]]:
    """Mediana, média, CV, mínimo e máximo de cada medida por aplicação × configuração."""
    rows: list[dict[str, Any]] = []
    for (app, conf), group in _cells(official_valid(records)).items():
        for metric, label in {**METRICS, "meter_overhead": "sobrecarga do medidor"}.items():
            values = [v for v in (_value(r, metric) for r in group) if v is not None]
            if not values:
                continue
            rows.append(
                {
                    "application": app,
                    "role": group[0].role,
                    "configuration": conf,
                    "metric": metric,
                    "label": label,
                    "n": len(values),
                    "median": statistics.median(values),
                    "mean": statistics.mean(values),
                    "cv": coefficient_of_variation(values),
                    "min": min(values),
                    "max": max(values),
                }
            )
    return rows


# ---------------------------------------------------------------- razões entre configurações


def compare_configurations(records: Sequence[ProcessRecord], settings: AnalysisSettings) -> list[dict[str, Any]]:
    """Razões B/A, C/B e D/C de cada medida, com IC pareado por bloco, Mann–Whitney, Holm e A12.

    A família de Holm é aplicação × medida (as três comparações).
    """
    valid = official_valid(records)
    by_cell = {(r.application, r.configuration, r.block): r for r in valid}
    applications = sorted({r.application for r in valid})
    roles = _roles(valid)
    rows: list[dict[str, Any]] = []
    for app in applications:
        for metric, label in METRICS.items():
            family: list[dict[str, Any]] = []
            for numerator, denominator in COMPARISONS:
                pairs: dict[int, tuple[float, float]] = {}
                for (a, conf, block), record in by_cell.items():
                    if a != app or conf != numerator or block is None:
                        continue
                    other = by_cell.get((app, denominator, block))
                    x, y = _value(record, metric), _value(other, metric) if other else None
                    if x is not None and y is not None:
                        pairs[block] = (x, y)
                if len(pairs) < 2:
                    continue
                ratio = paired_block_ratio(pairs, settings.resamples, settings.level, settings.seed)
                xs = [p[0] for p in pairs.values()]
                ys = [p[1] for p in pairs.values()]
                test = mann_whitney(xs, ys)
                a12 = vargha_delaney_a12(xs, ys)
                family.append(
                    {
                        "application": app,
                        "role": roles.get(app),
                        "metric": metric,
                        "label": label,
                        "comparison": f"{numerator}/{denominator}",
                        "blocks": ratio.blocks,
                        "median_numerator": statistics.median(xs),
                        "median_denominator": statistics.median(ys),
                        "ratio": ratio.estimate,
                        "ci_low": ratio.ci_low,
                        "ci_high": ratio.ci_high,
                        "change_pct": (ratio.estimate - 1) * 100,
                        "half_width_pp": ratio.half_width * 100,
                        "mann_whitney_u": test.u,
                        "p_value": test.p_value,
                        "a12": a12,
                        "a12_magnitude": a12_magnitude(a12),
                    }
                )
            for row, adjusted in zip(family, holm([r["p_value"] for r in family]), strict=True):
                row["p_holm"] = adjusted
            rows.extend(family)
    return rows


def _find(rows: Sequence[dict[str, Any]], app: str, metric: str, comparison: str) -> dict[str, Any] | None:
    for row in rows:
        if row["application"] == app and row["metric"] == metric and row["comparison"] == comparison:
            return row
    return None


# ---------------------------------------------------------------- decomposição log E = log P + log t


def decompose_energy(records: Sequence[ProcessRecord]) -> list[dict[str, Any]]:
    """Decomposição exploratória: em cada bloco, log(E_x/E_y) = log(P_x/P_y) + log(t_x/t_y).

    Como E = P × t em cada processo, a igualdade é exata por bloco. Relata-se a mediana entre blocos
    de cada termo e a parcela do tempo na mudança de energia (mediana do termo de tempo ÷ mediana
    do termo de energia), quando a mudança de energia é de pelo menos 1% (abaixo disso a parcela fica instável).
    """
    valid = official_valid(records)
    by_cell = {(r.application, r.configuration, r.block): r for r in valid}
    rows: list[dict[str, Any]] = []
    for app in sorted({r.application for r in valid}):
        for numerator, denominator in COMPARISONS:
            log_e, log_p, log_t = [], [], []
            for (a, conf, block), x in by_cell.items():
                y = by_cell.get((app, denominator, block))
                if a != app or conf != numerator or y is None:
                    continue
                if not (x.energy_j and y.energy_j and x.time_s and y.time_s and x.power_w and y.power_w):
                    continue
                log_e.append(math.log(x.energy_j / y.energy_j))
                log_p.append(math.log(x.power_w / y.power_w))
                log_t.append(math.log(x.time_s / y.time_s))
            if not log_e:
                continue
            median_e = statistics.median(log_e)
            median_t = statistics.median(log_t)
            rows.append(
                {
                    "application": app,
                    "comparison": f"{numerator}/{denominator}",
                    "blocks": len(log_e),
                    "median_log_energy": median_e,
                    "median_log_power": statistics.median(log_p),
                    "median_log_time": median_t,
                    "energy_change_pct": (math.exp(median_e) - 1) * 100,
                    "power_change_pct": (math.exp(statistics.median(log_p)) - 1) * 100,
                    "time_change_pct": (math.exp(median_t) - 1) * 100,
                    "time_share": median_t / median_e if abs(median_e) >= 0.01 else None,
                }
            )
    return rows


# ---------------------------------------------------------------- critérios E1–E6


def criterion_e1(records: Sequence[ProcessRecord]) -> dict[str, Any]:
    """CV da energia entre os processos de cada aplicação × configuração (todas as sessões)."""
    cells: list[dict[str, Any]] = []
    for (app, conf), group in _cells(official_valid(records)).items():
        cv = coefficient_of_variation([r.energy_j for r in group if r.energy_j])
        cells.append({"application": app, "role": group[0].role, "configuration": conf, "n": len(group), "cv": cv})
    main = [c for c in cells if c["role"] == "principal"]
    return {
        "limit": E1_LIMIT,
        "cells": cells,
        "max_main": max((c["cv"] for c in main if c["cv"] is not None), default=None),
        "met": all(c["cv"] is not None and c["cv"] <= E1_LIMIT for c in main),
    }


def criterion_e2(records: Sequence[ProcessRecord]) -> dict[str, Any]:
    """Maior ÷ menor mediana de energia entre sessões − 1, por aplicação × configuração."""
    cells: list[dict[str, Any]] = []
    for (app, conf), group in _cells(official_valid(records)).items():
        sessions: dict[str, list[float]] = defaultdict(list)
        for record in group:
            if record.energy_j:
                sessions[record.session].append(record.energy_j)
        medians = {s: statistics.median(v) for s, v in sorted(sessions.items())}
        cells.append(
            {
                "application": app,
                "role": group[0].role,
                "configuration": conf,
                "session_medians": medians,
                "spread": spread(list(medians.values())),
            }
        )
    main = [c for c in cells if c["role"] == "principal"]
    return {
        "limit": E2_LIMIT,
        "cells": cells,
        "max_main": max((c["spread"] for c in main if c["spread"] is not None), default=None),
        "above_limit": [f"{c['application']}-{c['configuration']}" for c in main if (c["spread"] or 0) > E2_LIMIT],
        "met": all(c["spread"] is not None and c["spread"] <= E2_LIMIT for c in main),
    }


def criterion_e3(comparisons: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Meia-largura do IC 95% da razão D/C da energia, em pontos percentuais."""
    cells: list[dict[str, Any]] = [
        {"application": r["application"], "role": r["role"], "half_width_pp": r["half_width_pp"]}
        for r in comparisons
        if r["metric"] == "energy_j" and r["comparison"] == "D/C"
    ]
    main = [c for c in cells if c["role"] == "principal"]
    return {
        "limit_pp": E3_LIMIT_PP,
        "cells": cells,
        "met": bool(main) and all(c["half_width_pp"] <= E3_LIMIT_PP for c in main),
    }


def criterion_e4(records: Sequence[ProcessRecord]) -> dict[str, Any]:
    """Mediana da sobrecarga do medidor por aplicação × configuração.

    Regra registrada: mediana ≤ 2%. Também se relata o valor absoluto, porque valores negativos
    (iterações medidas mais rápidas que a última preparação) indicam aquecimento residual, não custo do medidor.
    """
    cells: list[dict[str, Any]] = []
    for (app, conf), group in _cells(official_valid(records)).items():
        values = [r.meter_overhead for r in group if r.meter_overhead is not None]
        median = statistics.median(values) if values else None
        cells.append({"application": app, "role": group[0].role, "configuration": conf, "median": median})
    main = [c for c in cells if c["role"] == "principal"]
    return {
        "limit": E4_LIMIT,
        "cells": cells,
        "met": all(c["median"] is not None and c["median"] <= E4_LIMIT for c in main),
        "met_absolute": all(c["median"] is not None and abs(c["median"]) <= E4_LIMIT for c in main),
    }


def criterion_e5(records: Sequence[ProcessRecord], root: Path) -> dict[str, Any]:
    """Processos oficiais com evidência completa e sessões com manifesto SHA-256 registrado."""
    official = [r for r in records if r.category == OFFICIAL]
    manifests = {}
    for path in sorted((root / "evidencias" / "manifestos").glob("sessao*.json")):
        manifests[read_json(path).get("session_folder")] = path.name
    incomplete = [r.name for r in official if r.missing_files]
    sessions = sorted({r.session for r in official})
    without_manifest = [s for s in sessions if s not in manifests]
    complete = len(official) - len(incomplete)
    return {
        "processes": len(official),
        "complete": complete,
        "share": complete / len(official) if official else None,
        "incomplete": incomplete,
        "manifests": {s: manifests.get(s) for s in sessions},
        "sessions_without_manifest": without_manifest,
        "met": bool(official) and not incomplete and not without_manifest,
    }


def criterion_e6(root: Path, sessions: Sequence[str]) -> dict[str, Any]:
    """Tempo de máquina por sessão e proporção de falhas (tentativas sem sucesso)."""
    rows: list[dict[str, Any]] = []
    for session in sessions:
        folder = root / "dados" / "brutos" / session
        summaries = sorted(folder.glob("*-resumo-sessao.json"))
        summary = read_json(summaries[-1]) if summaries else {}
        progress = read_json_lines(folder / "progresso.jsonl")
        failures = [p["name"] for p in progress if not p.get("success")]
        elapsed = float(summary.get("elapsed_seconds") or 0)
        rows.append(
            {
                "session": session,
                "status": summary.get("status"),
                "elapsed_minutes": elapsed / 60,
                "attempts": len(progress),
                "failures": failures,
                "failure_share": len(failures) / len(progress) if progress else None,
                "idle_celsius": (summary.get("idle_temperature") or {}).get("median_celsius"),
                "met": elapsed <= E6_SESSION_SECONDS
                and (len(failures) / len(progress) if progress else 1) <= E6_FAILURE_SHARE,
            }
        )
    return {
        "limit_minutes": E6_SESSION_SECONDS / 60,
        "limit_failure_share": E6_FAILURE_SHARE,
        "sessions": rows,
        "met": bool(rows) and all(r["met"] for r in rows),
    }


# ---------------------------------------------------------------- hipóteses H1–H5


def _below_one(row: dict[str, Any] | None) -> bool:
    return row is not None and row["ci_high"] < 1


def _above_one(row: dict[str, Any] | None) -> bool:
    return row is not None and row["ci_low"] > 1


def _power_decision(row: dict[str, Any] | None) -> str:
    """Regra de H2 e H5. Dentro da faixa [0,98; 1,02] → apoiada; senão, se o IC exclui 1 → refutada."""
    if row is None:
        return "sem dados"
    low, high = POWER_BAND
    if low <= row["ci_low"] and row["ci_high"] <= high:
        return "apoiada"
    if not (row["ci_low"] <= 1 <= row["ci_high"]):
        return "refutada"
    return "inconclusiva"


def evaluate_hypotheses(comparisons: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Decisão de cada hipótese por aplicação, conforme as regras registradas."""
    rows: list[dict[str, Any]] = []
    for app in sorted({r["application"] for r in comparisons}):
        role = next(r["role"] for r in comparisons if r["application"] == app)
        energy = _find(comparisons, app, "energy_j", "D/C")
        if energy is None:
            h1 = "sem dados"
        elif _below_one(energy):
            h1 = "apoiada"
        elif _above_one(energy):
            h1 = "refutada"
        else:
            h1 = "inconclusiva"
        heap = _find(comparisons, app, "gc_heap_after_median_mb", "D/C")
        pauses = _find(comparisons, app, "gc_pauses", "D/C")
        pause_time = _find(comparisons, app, "gc_pause_time_ms", "D/C")
        rows.extend(
            [
                {"hypothesis": "H1", "application": app, "role": role, "decision": h1},
                {
                    "hypothesis": "H2",
                    "application": app,
                    "role": role,
                    "decision": _power_decision(_find(comparisons, app, "power_w", "D/C")),
                },
                {
                    "hypothesis": "H3a",
                    "application": app,
                    "role": role,
                    "decision": "apoiada" if _below_one(heap) else ("sem dados" if heap is None else "não apoiada"),
                },
                {
                    "hypothesis": "H3b",
                    "application": app,
                    "role": role,
                    "decision": "apoiada"
                    if (_below_one(pauses) or _below_one(pause_time))
                    else ("sem dados" if pauses is None and pause_time is None else "não apoiada"),
                },
                {
                    "hypothesis": "H5 (B/A)",
                    "application": app,
                    "role": role,
                    "decision": _power_decision(_find(comparisons, app, "power_w", "B/A")),
                },
                {
                    "hypothesis": "H5 (C/B)",
                    "application": app,
                    "role": role,
                    "decision": _power_decision(_find(comparisons, app, "power_w", "C/B")),
                },
            ]
        )
    return rows


def hypothesis_h4(comparisons: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """H4 (descritiva): ordem das aplicações pela razão D/C de energia e pela de heap."""
    apps = sorted({r["application"] for r in comparisons})
    energy = {a: r["ratio"] for a in apps if (r := _find(comparisons, a, "energy_j", "D/C"))}
    heap = {a: r["ratio"] for a in apps if (r := _find(comparisons, a, "gc_heap_after_median_mb", "D/C"))}
    order_energy = sorted(energy, key=energy.__getitem__)
    order_heap = sorted(heap, key=heap.__getitem__)
    return {
        "energy_ratio": energy,
        "heap_ratio": heap,
        "order_by_energy_reduction": order_energy,
        "order_by_heap_reduction": order_heap,
        "same_order": order_energy == order_heap,
    }
