"""Funções estatísticas usadas na análise, só com a biblioteca padrão.

Análise principal (registro prévio): razão das medianas com intervalo de confiança bootstrap de 95%
pareado por bloco, com 10 000 reamostragens dos blocos. Complementares: Mann–Whitney com correção de
Holm dentro de cada família e tamanho de efeito A12 de Vargha–Delaney.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


def coefficient_of_variation(values: Sequence[float]) -> float | None:
    """Desvio-padrão amostral ÷ média. ``None`` com menos de dois valores."""
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    return statistics.stdev(values) / mean if mean else None


def spread(values: Sequence[float]) -> float | None:
    """Maior ÷ menor − 1 (critério E2)."""
    if not values or min(values) <= 0:
        return None
    return max(values) / min(values) - 1


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Percentil com interpolação linear (mesmo método do ``numpy.percentile`` padrão)."""
    if not sorted_values:
        raise ValueError("lista vazia")
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


@dataclass(frozen=True)
class RatioEstimate:
    """Razão das medianas (numerador ÷ denominador) com intervalo de confiança."""

    estimate: float
    ci_low: float
    ci_high: float
    blocks: int
    resamples: int
    level: float

    @property
    def half_width(self) -> float:
        """Meia-largura do intervalo (critério E3 usa em pontos percentuais: × 100)."""
        return (self.ci_high - self.ci_low) / 2

    def contains(self, value: float) -> bool:
        return self.ci_low <= value <= self.ci_high


def paired_block_ratio(
    pairs: Mapping[int, tuple[float, float]],
    resamples: int = 10_000,
    level: float = 0.95,
    seed: int = 20261101,
) -> RatioEstimate:
    """Razão das medianas com IC bootstrap percentil pareado por bloco.

    ``pairs`` liga cada bloco ao par (valor do numerador, valor do denominador) medido nesse bloco.
    Em cada reamostragem sorteiam-se blocos com reposição e recalcula-se mediana(numerador) ÷
    mediana(denominador) com os blocos sorteados; assim o efeito da sessão e do bloco, comum aos dois
    valores do par, é preservado.
    """
    if len(pairs) < 2:
        raise ValueError("são necessários ao menos 2 blocos com o par completo")
    blocks = sorted(pairs)
    numerators = [pairs[b][0] for b in blocks]
    denominators = [pairs[b][1] for b in blocks]
    estimate = statistics.median(numerators) / statistics.median(denominators)
    rng = random.Random(seed)
    n = len(blocks)
    ratios = []
    for _ in range(resamples):
        picks = [rng.randrange(n) for _ in range(n)]
        ratios.append(
            statistics.median(numerators[i] for i in picks) / statistics.median(denominators[i] for i in picks)
        )
    ratios.sort()
    alpha = (1 - level) / 2
    return RatioEstimate(
        estimate=estimate,
        ci_low=_percentile(ratios, alpha),
        ci_high=_percentile(ratios, 1 - alpha),
        blocks=n,
        resamples=resamples,
        level=level,
    )


def _ranks(values: Sequence[float]) -> list[float]:
    """Postos médios (empates recebem a média dos postos)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


@dataclass(frozen=True)
class MannWhitney:
    u: float
    p_value: float


def mann_whitney(x: Sequence[float], y: Sequence[float]) -> MannWhitney:
    """Teste de Mann–Whitney bilateral, aproximação normal com correção de empates e de continuidade."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        raise ValueError("amostras vazias")
    ranks = _ranks([*x, *y])
    rank_sum = sum(ranks[:n1])
    u1 = rank_sum - n1 * (n1 + 1) / 2
    mean_u = n1 * n2 / 2
    n = n1 + n2
    ties: dict[float, int] = {}
    for value in [*x, *y]:
        ties[value] = ties.get(value, 0) + 1
    tie_term = sum(t**3 - t for t in ties.values())
    variance = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))
    if variance <= 0:
        return MannWhitney(u=u1, p_value=1.0)
    z = (abs(u1 - mean_u) - 0.5) / math.sqrt(variance)
    p_value = math.erfc(max(z, 0.0) / math.sqrt(2))
    return MannWhitney(u=u1, p_value=min(1.0, p_value))


def holm(p_values: Sequence[float]) -> list[float]:
    """Valores de p ajustados pelo método de Holm, na ordem original."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def vargha_delaney_a12(x: Sequence[float], y: Sequence[float]) -> float:
    """A12: probabilidade de um valor de ``x`` ser maior que um de ``y`` (empates valem metade)."""
    if not x or not y:
        raise ValueError("amostras vazias")
    greater = sum(1 for a in x for b in y if a > b)
    equal = sum(1 for a in x for b in y if a == b)
    return (greater + 0.5 * equal) / (len(x) * len(y))


def a12_magnitude(a12: float) -> str:
    """Classificação usual de Vargha e Delaney (desprezível, pequeno, médio, grande)."""
    distance = abs(a12 - 0.5)
    if distance < 0.06:
        return "desprezível"
    if distance < 0.14:
        return "pequeno"
    if distance < 0.21:
        return "médio"
    return "grande"
