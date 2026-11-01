"""Leitura do log de coleta de lixo gravado com ``-Xlog:gc`` (coletor G1).

Cada pausa aparece numa linha como::

    [2.242s][info][gc] GC(3) Pause Young (Normal) (G1 Evacuation Pause) 626M->13M(1024M) 1.330ms

As medidas seguem o adendo do protocolo (T13): número de linhas ``Pause``, soma dos tempos dessas
linhas e mediana do heap depois de cada pausa (o valor depois da seta). O log cobre o processo
inteiro, incluindo as preparações.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from pathlib import Path

_UNIT_TO_MB = {"K": 1 / 1024, "M": 1.0, "G": 1024.0}

_PAUSE = re.compile(
    r"GC\(\d+\) (?P<kind>Pause .*?) "
    r"(?P<before>\d+(?:\.\d+)?)(?P<bu>[KMG])->(?P<after>\d+(?:\.\d+)?)(?P<au>[KMG])"
    r"\((?P<cap>\d+(?:\.\d+)?)(?P<cu>[KMG])\) (?P<ms>\d+(?:\.\d+)?)ms\s*$"
)


@dataclass(frozen=True)
class GcSummary:
    """Medidas de coleta de lixo de um processo."""

    uses_g1: bool
    pauses: int
    young_pauses: int
    full_pauses: int
    other_pauses: int
    pause_time_ms: float
    heap_after_median_mb: float | None
    unparsed_pause_lines: int


def _to_mb(value: str, unit: str) -> float:
    return float(value) * _UNIT_TO_MB[unit]


def parse_gc_text(text: str) -> GcSummary:
    """Resume o texto de um ``gc.log``. Linhas de pausa fora do formato esperado são contadas à parte."""
    uses_g1 = False
    young = full = other = unparsed = 0
    total_ms = 0.0
    heap_after: list[float] = []
    for line in text.splitlines():
        if "Using G1" in line:
            uses_g1 = True
            continue
        if " Pause " not in line:
            continue
        match = _PAUSE.search(line)
        if match is None:
            unparsed += 1
            continue
        kind = match["kind"]
        if kind.startswith("Pause Young"):
            young += 1
        elif kind.startswith("Pause Full"):
            full += 1
        else:
            other += 1  # Remark e Cleanup do ciclo concorrente.
        total_ms += float(match["ms"])
        heap_after.append(_to_mb(match["after"], match["au"]))
    return GcSummary(
        uses_g1=uses_g1,
        pauses=young + full + other,
        young_pauses=young,
        full_pauses=full,
        other_pauses=other,
        pause_time_ms=total_ms,
        heap_after_median_mb=statistics.median(heap_after) if heap_after else None,
        unparsed_pause_lines=unparsed,
    )


def parse_gc_log(path: Path) -> GcSummary | None:
    """Lê um ``gc.log``; devolve ``None`` se o arquivo não existir."""
    if not path.is_file():
        return None
    return parse_gc_text(path.read_text(encoding="utf-8", errors="replace"))
