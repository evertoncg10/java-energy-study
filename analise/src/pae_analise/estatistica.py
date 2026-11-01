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


# ---------------------------------------------------------------- análise de sensibilidade (exploratória)
#
# Testes usados só na análise de sensibilidade, que não faz parte do registro prévio. As distribuições
# são calculadas com as funções gama e beta incompletas regularizadas (Press et al., Numerical Recipes,
# cap. 6), para manter o núcleo sem dependências externas. Os testes conferem os valores com o scipy.


def _regularized_gamma_lower(a: float, x: float) -> float:
    """P(a, x): função gama incompleta inferior regularizada."""
    if x <= 0:
        return 0.0
    log_prefix = a * math.log(x) - x - math.lgamma(a)
    if x < a + 1:  # Série.
        term = total = 1 / a
        denominator = a
        for _ in range(1000):
            denominator += 1
            term *= x / denominator
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return total * math.exp(log_prefix)
    # Fração contínua de Lentz para Q(a, x).
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return 1 - math.exp(log_prefix) * h


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c = 1.0
    d = 1 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1 / d
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return h


def _regularized_beta(a: float, b: float, x: float) -> float:
    """I_x(a, b): função beta incompleta regularizada."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(log_front) * _beta_continued_fraction(a, b, x) / a
    return 1 - math.exp(log_front) * _beta_continued_fraction(b, a, 1 - x) / b


def chi2_sf(statistic: float, df: float) -> float:
    """P(X ≥ statistic) para X com distribuição qui-quadrado com ``df`` graus de liberdade."""
    return 1.0 if statistic <= 0 else max(0.0, 1 - _regularized_gamma_lower(df / 2, statistic / 2))


def f_sf(statistic: float, df1: float, df2: float) -> float:
    """P(X ≥ statistic) para X com distribuição F(df1, df2)."""
    if statistic <= 0:
        return 1.0
    return _regularized_beta(df2 / 2, df1 / 2, df2 / (df2 + df1 * statistic))


def t_sf_two_sided(statistic: float, df: float) -> float:
    """P(|T| ≥ |statistic|) para T com distribuição t de Student."""
    return _regularized_beta(df / 2, 0.5, df / (df + statistic * statistic))


def t_quantile(probability: float, df: float) -> float:
    """Quantil da t de Student (0,5 < probability < 1), por bisseção."""
    if not 0.5 < probability < 1:
        raise ValueError("probability deve estar entre 0,5 e 1")
    target = 2 * (1 - probability)  # Cauda bilateral.
    low, high = 0.0, 1.0
    while t_sf_two_sided(high, df) > target:
        high *= 2
    for _ in range(200):
        middle = (low + high) / 2
        if t_sf_two_sided(middle, df) > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2


@dataclass(frozen=True)
class OmnibusTest:
    """Teste global entre configurações nos mesmos blocos."""

    statistic: float
    df1: float
    df2: float | None
    p_value: float
    blocks: int


def friedman(table: Sequence[Sequence[float]]) -> OmnibusTest:
    """Teste de Friedman: cada linha é um bloco, cada coluna uma configuração (postos dentro do bloco).

    Aproximação qui-quadrado com correção de empates (igual a ``scipy.stats.friedmanchisquare``).
    """
    n = len(table)
    k = len(table[0]) if table else 0
    if n < 2 or k < 2 or any(len(row) != k for row in table):
        raise ValueError("tabela completa com ao menos 2 blocos e 2 configurações")
    rank_rows = [_ranks(row) for row in table]
    rank_sums = [sum(row[j] for row in rank_rows) for j in range(k)]
    statistic = 12 / (n * k * (k + 1)) * sum(r * r for r in rank_sums) - 3 * n * (k + 1)
    ties = 0
    for row in table:
        counts: dict[float, int] = {}
        for value in row:
            counts[value] = counts.get(value, 0) + 1
        ties += sum(t**3 - t for t in counts.values())
    correction = 1 - ties / (n * (k**3 - k))
    statistic = statistic / correction if correction > 0 else 0.0
    return OmnibusTest(statistic=statistic, df1=k - 1, df2=None, p_value=chi2_sf(statistic, k - 1), blocks=n)


def block_anova(table: Sequence[Sequence[float]]) -> OmnibusTest:
    """ANOVA de dois fatores sem interação (blocos completos casualizados): F da configuração.

    Cada linha é um bloco e cada coluna uma configuração. O bloco entra como fator para retirar a
    variação entre blocos e sessões do erro.
    """
    n = len(table)
    k = len(table[0]) if table else 0
    if n < 2 or k < 2 or any(len(row) != k for row in table):
        raise ValueError("tabela completa com ao menos 2 blocos e 2 configurações")
    grand = sum(sum(row) for row in table) / (n * k)
    column_means = [sum(row[j] for row in table) / n for j in range(k)]
    row_means = [sum(row) / k for row in table]
    ss_columns = n * sum((m - grand) ** 2 for m in column_means)
    ss_rows = k * sum((m - grand) ** 2 for m in row_means)
    ss_total = sum((v - grand) ** 2 for row in table for v in row)
    ss_error = ss_total - ss_columns - ss_rows
    df1, df2 = k - 1, (k - 1) * (n - 1)
    if ss_error <= 0:
        return OmnibusTest(statistic=math.inf, df1=df1, df2=df2, p_value=0.0, blocks=n)
    statistic = (ss_columns / df1) / (ss_error / df2)
    return OmnibusTest(statistic=statistic, df1=df1, df2=df2, p_value=f_sf(statistic, df1, df2), blocks=n)


@dataclass(frozen=True)
class PairedLogTest:
    """Teste t pareado sobre log(x/y): razão das médias geométricas com IC."""

    ratio: float
    ci_low: float
    ci_high: float
    statistic: float
    p_value: float
    pairs: int


def paired_log_t(pairs: Sequence[tuple[float, float]], level: float = 0.95) -> PairedLogTest:
    """Teste t pareado no log da razão de cada bloco. É o contraste da ANOVA em blocos para duas configurações."""
    differences = [math.log(x / y) for x, y in pairs]
    n = len(differences)
    if n < 2:
        raise ValueError("são necessários ao menos 2 pares")
    mean = statistics.mean(differences)
    error = statistics.stdev(differences) / math.sqrt(n)
    if error == 0:
        p_value = 1.0 if mean == 0 else 0.0
        statistic = 0.0 if mean == 0 else math.copysign(math.inf, mean)
        return PairedLogTest(math.exp(mean), math.exp(mean), math.exp(mean), statistic, p_value, n)
    statistic = mean / error
    margin = t_quantile(1 - (1 - level) / 2, n - 1) * error
    return PairedLogTest(
        ratio=math.exp(mean),
        ci_low=math.exp(mean - margin),
        ci_high=math.exp(mean + margin),
        statistic=statistic,
        p_value=t_sf_two_sided(statistic, n - 1),
        pairs=n,
    )


@dataclass(frozen=True)
class SignedRank:
    statistic: float
    p_value: float
    pairs: int


def wilcoxon_signed_rank(pairs: Sequence[tuple[float, float]]) -> SignedRank:
    """Teste de Wilcoxon pareado bilateral, exato por enumeração (diferenças nulas são descartadas).

    A estatística é a soma dos postos das diferenças positivas. Com empates entre |diferenças|,
    a distribuição exata é calculada com os postos médios observados.
    """
    differences = [x - y for x, y in pairs if x != y]
    n = len(differences)
    if n == 0:
        return SignedRank(statistic=0.0, p_value=1.0, pairs=0)
    if n > 25:
        raise ValueError("enumeração exata limitada a 25 pares")
    ranks = _ranks([abs(d) for d in differences])
    positive = sum(r for r, d in zip(ranks, differences, strict=True) if d > 0)
    # Distribuição da soma de postos com sinais ao acaso: contagem por soma (postos × 2 são inteiros).
    counts: dict[int, int] = {0: 1}
    for rank in ranks:
        step = round(rank * 2)
        updated: dict[int, int] = dict(counts)
        for total, count in counts.items():
            updated[total + step] = updated.get(total + step, 0) + count
        counts = updated
    total_cases = 2**n
    mean = sum(ranks)  # Em dobro: média da soma (sum(ranks) / 2) × 2.
    observed = round(positive * 2)
    distance = abs(observed - mean)
    extreme = sum(count for total, count in counts.items() if abs(total - mean) >= distance - 1e-9)
    return SignedRank(statistic=positive, p_value=min(1.0, extreme / total_cases), pairs=n)
