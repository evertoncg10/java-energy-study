"""Testes do cálculo descritivo do peso das pausas de coleta (scripts/analisar_pausas.py)."""

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = ROOT / "resultados" / "pausas-gc-20261107"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("analisar_pausas", ROOT / "scripts" / "analisar_pausas.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(app: str, config: str, pause_ms: str, wall_s: str, valid: str = "True") -> dict[str, str]:
    return {
        "application": app,
        "role": "principal",
        "configuration": config,
        "gc_pause_time_ms": pause_ms,
        "wall_seconds": wall_s,
        "valid": valid,
    }


def test_fraction_is_median_of_pause_over_wall_time() -> None:
    pausas = load_script()
    base = [
        row("pmd", "C", "100", "10"),
        row("pmd", "C", "200", "10"),
        row("pmd", "C", "900", "10"),
        row("pmd", "C", "5000", "10", valid="False"),
    ]
    (only,) = pausas.pause_table(base)
    assert only["processes"] == 3
    assert only["median_pause_fraction_pct"] == 2.0
    assert only["median_gc_pause_time_ms"] == 200.0


def test_effect_uses_configuration_c_and_main_applications_only() -> None:
    pausas = load_script()
    table = [
        {"application": "pmd", "role": "principal", "configuration": "C", "median_pause_fraction_pct": 0.8},
        {"application": "pmd", "role": "principal", "configuration": "D", "median_pause_fraction_pct": 0.7},
        {"application": "avrora", "role": "exploratorio", "configuration": "C", "median_pause_fraction_pct": 0.1},
    ]
    ratios = [
        {"application": "pmd", "metric": "gc_pause_time_ms", "comparison": "D/C", "change_pct": "-10"},
        {"application": "pmd", "metric": "energy_j", "comparison": "D/C", "change_pct": "1"},
        {"application": "avrora", "metric": "gc_pause_time_ms", "comparison": "D/C", "change_pct": "2"},
    ]
    (effect,) = pausas.effect_table(table, pausas.pause_reduction(ratios))
    assert effect["application"] == "pmd"
    assert abs(effect["max_time_effect_pct"] - 0.08) < 1e-12


def test_regenerated_files_match_the_published_ones(tmp_path: Path) -> None:
    pausas = load_script()
    out = tmp_path / "pausas"
    assert pausas.main(["--saida", str(out)]) == 0
    for name in ("pausas.csv", "efeito-pausas.csv", "resumo-pausas.txt", "metadados.json"):
        assert (out / name).read_bytes() == (PUBLISHED / name).read_bytes(), name


def test_refuses_a_folder_that_is_not_empty(tmp_path: Path) -> None:
    pausas = load_script()
    (tmp_path / "algo.txt").write_text("x", encoding="utf-8")
    assert pausas.main(["--saida", str(tmp_path)]) == 2
