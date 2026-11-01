"""Gravação dos resultados: tabelas CSV, JSON e um resumo em texto.

A pasta de saída precisa ser nova; nenhum resultado anterior é sobrescrito.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pae_analise import __version__
from pae_analise.avaliacao import AnalysisSettings
from pae_analise.consolidacao import ProcessRecord


def prepare_output(path: Path) -> Path:
    """Cria a pasta de saída; recusa uma pasta que já exista."""
    if path.exists():
        raise FileExistsError(f"A pasta de saída já existe e não será sobrescrita: {path}")
    path.mkdir(parents=True)
    return path


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    """CSV em UTF-8, separado por vírgula e com ponto decimal (padrão para Python, R e planilhas em inglês)."""
    columns: list[str] = []
    for row in rows:
        columns.extend(key for key in row if key not in columns)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(v) for k, v in row.items()})


# Casas significativas gravadas. Diferenças na última casa de funções como erfc entre Windows e Linux
# (da ordem de 1e-16) desaparecem, e os arquivos ficam idênticos byte a byte nos dois sistemas.
SIGNIFICANT_DIGITS = 12


def stable(value: Any) -> Any:
    """Arredonda todos os números reais (também dentro de listas e dicionários) para 12 casas significativas."""
    if isinstance(value, float):
        return float(f"{value:.{SIGNIFICANT_DIGITS}g}") if math.isfinite(value) else value
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [stable(v) for v in value]
    return value


def _cell(value: Any) -> Any:
    value = stable(value)
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_json(path: Path, data: Any) -> None:
    """JSON em UTF-8 com fim de linha LF em qualquer sistema."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(stable(data), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def write_text(path: Path, text: str) -> None:
    """Texto em UTF-8 com fim de linha LF em qualquer sistema; recusa sobrescrever."""
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def records_as_rows(records: Sequence[ProcessRecord]) -> list[dict[str, Any]]:
    return [r.as_row() for r in records]


def records_as_json(records: Sequence[ProcessRecord]) -> list[dict[str, Any]]:
    return [asdict(r) for r in records]


def _git_commit(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def input_fingerprint(records: Sequence[ProcessRecord]) -> str:
    """SHA-256 da lista ordenada (origem, SHA-256 do resultado.json): identifica os dados de entrada."""
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda r: r.source):
        digest.update(f"{record.source}\t{record.result_sha256}\n".encode())
    return digest.hexdigest()


def metadata(root: Path, records: Sequence[ProcessRecord], settings: AnalysisSettings) -> dict[str, Any]:
    return {
        "tool": "pae-analise",
        "version": __version__,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repository_commit": _git_commit(root),
        "settings": asdict(settings),
        "official_processes": sum(1 for r in records if r.category == "oficial"),
        "input_sha256": input_fingerprint([r for r in records if r.category == "oficial"]),
    }


def _pct(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value * 100:.{digits}f}%"


def _yes(flag: bool) -> str:
    return "atendido" if flag else "NÃO atendido"


def summary_text(
    records: Sequence[ProcessRecord],
    comparisons: Sequence[dict[str, Any]],
    criteria: dict[str, Any],
    hypotheses: Sequence[dict[str, Any]],
    h4: dict[str, Any],
    decomposition: Sequence[dict[str, Any]],
) -> str:
    """Resumo legível em português, para conferência rápida."""
    official = [r for r in records if r.category == "oficial"]
    lines = [
        "RESUMO DA ANÁLISE PAE-JVM",
        f"Processos oficiais: {len(official)} ({sum(r.valid for r in official)} válidos)",
        "",
        "Critérios do artefato (limites do registro prévio):",
        f"  E1 repetibilidade: maior CV de energia nas principais = {_pct(criteria['E1']['max_main'])}"
        f" (limite 5%) -> {_yes(criteria['E1']['met'])}",
        f"  E2 entre sessões: maior diferença nas principais = {_pct(criteria['E2']['max_main'])}"
        f" (limite 5%) -> {_yes(criteria['E2']['met'])};"
        f" acima: {', '.join(criteria['E2']['above_limit']) or 'nenhuma'}",
    ]
    for cell in criteria["E3"]["cells"]:
        lines.append(
            f"  E3 meia-largura IC D/C energia {cell['application']}: {cell['half_width_pp']:.2f} pp (limite 3 pp)"
        )
    lines.append(f"  E3 -> {_yes(criteria['E3']['met'])}")
    lines.append(
        f"  E4 sobrecarga do medidor (mediana <= 2%) -> {_yes(criteria['E4']['met'])};"
        f" em valor absoluto -> {_yes(criteria['E4']['met_absolute'])}"
    )
    e5 = criteria["E5"]
    lines.append(f"  E5 rastreabilidade: {e5['complete']}/{e5['processes']} processos completos -> {_yes(e5['met'])}")
    lines.append(f"  E6 viabilidade -> {_yes(criteria['E6']['met'])}")
    for session in criteria["E6"]["sessions"]:
        lines.append(
            f"     {session['session']}: {session['elapsed_minutes']:.0f} min, {session['attempts']} tentativas,"
            f" {len(session['failures'])} falhas"
        )
    lines += ["", "Razões entre configurações (mediana, IC 95% pareado por bloco):"]
    for row in comparisons:
        if row["metric"] in ("energy_j", "time_s", "power_w"):
            lines.append(
                f"  {row['application']:<9} {row['comparison']} {row['label']:<20} {row['ratio']:.4f}"
                f" [{row['ci_low']:.4f}; {row['ci_high']:.4f}]  ({row['change_pct']:+.2f}%)"
            )
    lines += ["", "Hipóteses:"]
    for row in hypotheses:
        tag = "" if row["role"] == "principal" else " (exploratória)"
        lines.append(f"  {row['hypothesis']:<9} {row['application']:<9} {row['decision']}{tag}")
    lines.append(
        f"  H4 (descritiva): ordem por redução de energia {h4['order_by_energy_reduction']},"
        f" por redução de heap {h4['order_by_heap_reduction']}"
    )
    lines += ["", "Decomposição exploratória log E = log P + log t (mediana entre blocos):"]
    for row in decomposition:
        share = "-" if row["time_share"] is None else f"{row['time_share'] * 100:.0f}%"
        lines.append(
            f"  {row['application']:<9} {row['comparison']} energia {row['energy_change_pct']:+.2f}%,"
            f" potência {row['power_change_pct']:+.2f}%, tempo {row['time_change_pct']:+.2f}%, parcela do tempo {share}"
        )
    return "\n".join(lines) + "\n"
