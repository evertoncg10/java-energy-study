import math

import pytest

from pae_analise.estatistica import (
    a12_magnitude,
    coefficient_of_variation,
    holm,
    mann_whitney,
    paired_block_ratio,
    spread,
    vargha_delaney_a12,
)


def test_coefficient_of_variation_and_spread() -> None:
    assert coefficient_of_variation([10.0]) is None
    assert coefficient_of_variation([9.0, 10.0, 11.0]) == pytest.approx(0.1)
    assert spread([100.0, 105.0, 102.0]) == pytest.approx(0.05)


def test_holm_matches_textbook_example() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_a12_and_magnitude() -> None:
    assert vargha_delaney_a12([1.0, 2.0], [1.0, 2.0]) == 0.5
    assert vargha_delaney_a12([3.0, 4.0], [1.0, 2.0]) == 1.0
    assert a12_magnitude(0.5) == "desprezível"
    assert a12_magnitude(0.62) == "pequeno"
    assert a12_magnitude(0.30) == "médio"
    assert a12_magnitude(1.0) == "grande"


def test_mann_whitney_against_reference_value() -> None:
    # Cálculo à mão: postos de x = 1, 2, 3, 5, 6 -> U = 17 - 15 = 2; z = (|2 - 12,5| - 0,5) / 4,787 -> p = 0,0367.
    x = [1.1, 2.2, 3.3, 4.4, 5.5]
    y = [3.5, 6.6, 7.7, 8.8, 9.9]
    result = mann_whitney(x, y)
    assert result.u == 2
    assert result.p_value == pytest.approx(0.0367, abs=0.001)


def test_identical_samples_give_p_one() -> None:
    assert mann_whitney([1.0, 1.0], [1.0, 1.0]).p_value == 1.0


def test_paired_block_ratio_is_deterministic_and_brackets_the_estimate() -> None:
    pairs = {b: (100.0 * (1 + 0.01 * b), 105.0 * (1 + 0.01 * b)) for b in range(1, 16)}
    first = paired_block_ratio(pairs, resamples=2000, seed=7)
    second = paired_block_ratio(pairs, resamples=2000, seed=7)
    assert first == second
    assert first.estimate == pytest.approx(100 / 105)
    assert first.ci_low <= first.estimate <= first.ci_high
    assert first.blocks == 15


def test_pairing_removes_a_shared_block_effect() -> None:
    # Uma deriva grande comum aos dois lados do par não pode alargar o intervalo da razão.
    pairs = {b: (0.97 * math.exp(0.1 * b), math.exp(0.1 * b)) for b in range(1, 16)}
    result = paired_block_ratio(pairs, resamples=2000)
    assert result.ci_low == pytest.approx(0.97) and result.ci_high == pytest.approx(0.97)


def test_paired_block_ratio_needs_two_blocks() -> None:
    with pytest.raises(ValueError):
        paired_block_ratio({1: (1.0, 1.0)})


def test_mann_whitney_with_ties_matches_scipy() -> None:
    # Referência: scipy.stats.mannwhitneyu(x, y, method="asymptotic", use_continuity=True) -> U=6,5, p=0,24184
    result = mann_whitney([1, 2, 2, 3, 5], [2, 3, 4, 4, 6])
    assert result.u == 6.5
    assert result.p_value == pytest.approx(0.2418443040494631, rel=1e-9)
