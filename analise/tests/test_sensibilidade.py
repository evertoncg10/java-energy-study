"""Análise de sensibilidade exploratória. Valores de referência calculados com scipy 1.14."""

import math

import pytest

from pae_analise.avaliacao import AnalysisSettings, compare_configurations
from pae_analise.consolidacao import ProcessRecord
from pae_analise.estatistica import (
    block_anova,
    chi2_sf,
    f_sf,
    friedman,
    paired_log_t,
    t_quantile,
    t_sf_two_sided,
    wilcoxon_signed_rank,
)
from pae_analise.sensibilidade import contrast_tests, omnibus_tests

from .conftest import needs_data

# Linhas = blocos; colunas = A, B, C, D. Há um empate no 4º bloco.
TABLE = [
    [10.2, 10.8, 9.9, 11.1],
    [9.7, 10.1, 9.5, 10.6],
    [10.5, 10.9, 10.0, 11.4],
    [10.0, 10.0, 9.8, 10.9],
    [10.3, 11.0, 10.1, 11.2],
    [9.9, 10.4, 9.6, 10.8],
]
PAIRS_DC = [(row[3], row[2]) for row in TABLE]


def test_distributions_match_scipy() -> None:
    assert chi2_sf(7.5, 3) == pytest.approx(0.0575584519726364, rel=1e-9)
    assert f_sf(2.5, 3, 42) == pytest.approx(0.07250743593253524, rel=1e-9)
    assert t_quantile(0.975, 14) == pytest.approx(2.144786687917804, rel=1e-9)
    assert t_sf_two_sided(-2.144786687917804, 14) == pytest.approx(0.05, rel=1e-9)


def test_friedman_matches_scipy_with_ties() -> None:
    result = friedman(TABLE)
    assert result.statistic == pytest.approx(17.745762711864412, rel=1e-9)
    assert result.p_value == pytest.approx(0.0004962729506176979, rel=1e-9)
    assert (result.df1, result.blocks) == (3, 6)


def test_block_anova_on_logs() -> None:
    result = block_anova([[math.log(v) for v in row] for row in TABLE])
    assert result.statistic == pytest.approx(88.65132343302109, rel=1e-9)
    assert result.p_value == pytest.approx(9.041115965027855e-10, rel=1e-6)
    assert (result.df1, result.df2) == (3, 15)


def test_paired_log_t_gives_geometric_mean_ratio() -> None:
    result = paired_log_t(PAIRS_DC)
    assert result.ratio == pytest.approx(1.1204799290762404, rel=1e-9)
    assert result.ci_low == pytest.approx(1.10884501303809, rel=1e-9)
    assert result.ci_high == pytest.approx(1.1322369282455977, rel=1e-9)
    assert result.statistic == pytest.approx(28.014710265441717, rel=1e-9)
    assert result.p_value == pytest.approx(1.0850818026738978e-06, rel=1e-6)


def test_wilcoxon_exact() -> None:
    result = wilcoxon_signed_rank(PAIRS_DC)
    assert result.statistic == 21  # Todas as 6 diferenças são positivas: 1 + 2 + ... + 6.
    assert result.p_value == pytest.approx(0.03125)
    assert wilcoxon_signed_rank([(1.0, 1.0), (2.0, 2.0)]).p_value == 1.0


def test_incomplete_table_is_rejected() -> None:
    with pytest.raises(ValueError):
        friedman([[1.0, 2.0], [1.0]])


@needs_data
def test_main_applications_agree_with_the_main_analysis(official_records: list[ProcessRecord]) -> None:
    records = official_records
    comparisons = compare_configurations(records, AnalysisSettings(resamples=500))
    omnibus = omnibus_tests(records)
    assert {(r["application"], r["metric"]) for r in omnibus} >= {("pmd", "energy_j"), ("lusearch", "energy_j")}
    assert all(r["blocks"] == 15 for r in omnibus)
    contrasts = contrast_tests(records, comparisons)
    assert len(contrasts) == 27
    main = [r for r in contrasts if r["role"] == "principal"]
    assert main and all(r["agrees"] for r in main)
