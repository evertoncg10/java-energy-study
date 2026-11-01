import json
from pathlib import Path

import pytest

from pae_analise.avaliacao import (
    AnalysisSettings,
    compare_configurations,
    criterion_e1,
    criterion_e2,
    criterion_e5,
    criterion_e6,
    decompose_energy,
    evaluate_hypotheses,
)
from pae_analise.consolidacao import ProcessRecord

from .conftest import needs_data

FAST = AnalysisSettings(resamples=500)


@needs_data
def test_e2_matches_the_collection_check(official_records: list[ProcessRecord], root: Path) -> None:
    """O E2 calculado aqui deve ser igual ao do relatório de conferência da coleta (T24)."""
    reference = json.loads(
        (root / "evidencias" / "conferencias" / "coleta-sessoes1a4.json").read_text(encoding="utf-8")
    )
    e2 = criterion_e2(official_records)
    assert e2["max_main"] == pytest.approx(reference["e2"]["max_spread_energy_main"])
    assert sorted(e2["above_limit"]) == sorted(reference["e2"]["cells_above_limit"])
    assert e2["met"] is False


@needs_data
def test_e1_uses_15_processes_per_cell(official_records: list[ProcessRecord]) -> None:
    e1 = criterion_e1(official_records)
    assert len(e1["cells"]) == 12
    assert all(cell["n"] == 15 for cell in e1["cells"])


@needs_data
def test_e5_and_e6_on_the_official_collection(official_records: list[ProcessRecord], root: Path) -> None:
    e5 = criterion_e5(official_records, root)
    assert e5["complete"] == 180 and e5["met"]
    e6 = criterion_e6(root, sorted({r.session for r in official_records}))
    assert len(e6["sessions"]) == 4 and e6["met"]


@needs_data
def test_comparisons_cover_every_app_metric_and_ratio(official_records: list[ProcessRecord]) -> None:
    rows = compare_configurations(official_records, FAST)
    assert len(rows) == 3 * 6 * 3
    assert all(r["blocks"] == 15 for r in rows)
    assert all(r["ci_low"] <= r["ratio"] <= r["ci_high"] for r in rows)
    assert all(r["p_holm"] >= r["p_value"] for r in rows)


@needs_data
def test_decomposition_adds_up_per_block(official_records: list[ProcessRecord]) -> None:
    for row in decompose_energy(official_records):
        assert row["blocks"] == 15


def _row(app: str, metric: str, comparison: str, low: float, high: float) -> dict[str, object]:
    return {
        "application": app,
        "role": "principal",
        "metric": metric,
        "comparison": comparison,
        "ratio": (low + high) / 2,
        "ci_low": low,
        "ci_high": high,
    }


def test_hypothesis_rules_follow_the_registration() -> None:
    rows = [
        _row("x", "energy_j", "D/C", 0.95, 0.99),
        _row("x", "power_w", "D/C", 0.99, 1.01),
        _row("x", "gc_heap_after_median_mb", "D/C", 0.90, 1.01),
        _row("x", "gc_pauses", "D/C", 1.00, 1.05),
        _row("x", "gc_pause_time_ms", "D/C", 0.80, 0.95),
        _row("x", "power_w", "B/A", 1.01, 1.03),
        _row("x", "power_w", "C/B", 0.97, 1.01),
    ]
    decisions = {r["hypothesis"]: r["decision"] for r in evaluate_hypotheses(rows)}
    assert decisions == {
        "H1": "apoiada",
        "H2": "apoiada",
        "H3a": "não apoiada",
        "H3b": "apoiada",
        "H5 (B/A)": "refutada",
        "H5 (C/B)": "inconclusiva",
    }
