"""Consolidação dos dados brutos: uma linha por processo (T19).

Para cada processo da coleta oficial (pastas de ``dados/brutos``) e dos pilotos (``dados/piloto``),
lê os arquivos gravados pela execução e produz um :class:`ProcessRecord`. Cada linha guarda o caminho
da pasta de origem e o SHA-256 do ``resultado.json``, para que todo número possa ser ligado ao arquivo
original. Nada é alterado nos dados brutos.

Definições (adendo do protocolo T13):
    energia do processo   média da energia do pacote nas iterações medidas;
    tempo do processo     média do tempo das iterações medidas;
    potência média        soma das energias ÷ soma dos tempos das iterações medidas;
    sobrecarga do medidor média do tempo DaCapo das iterações medidas ÷ tempo DaCapo da última preparação − 1.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pae_analise.gclog import parse_gc_log

OFFICIAL = "oficial"
PILOT = "piloto"
SESSION_WARMUP = "aquecimento-maquina"

REQUIRED_FILES = (
    "resultado.json",
    "command.json",
    "config.json",
    "java-preflight.json",
    "sdkman.json",
    "gc.log",
    "system-before.json",
    "system-after.json",
    "medidor/iterations.jsonl",
    "medidor/summary.json",
)


@dataclass
class ProcessRecord:
    """Uma linha da base consolidada. Campos ausentes ficam ``None``."""

    category: str
    session: str
    seed: int | None
    block: int | None
    order: int | None
    name: str
    application: str
    role: str | None
    configuration: str
    java_runtime_version: str | None
    compact_headers: str | None
    energy_j: float | None
    time_s: float | None
    power_w: float | None
    energy_iterations_j: list[float]
    time_iterations_s: list[float]
    measured_iterations: int
    warmup_iterations: int
    last_warmup_dacapo_ms: float | None
    measured_dacapo_mean_ms: float | None
    meter_overhead: float | None
    gc_pauses: int | None
    gc_young_pauses: int | None
    gc_full_pauses: int | None
    gc_other_pauses: int | None
    gc_pause_time_ms: float | None
    gc_heap_after_median_mb: float | None
    idle_power_w: float | None
    start_celsius: float | None
    wall_seconds: float | None
    valid: bool
    problems: list[str] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    source: str = ""
    result_sha256: str | None = None

    def as_row(self) -> dict[str, Any]:
        """Dicionário plano para CSV (listas viram texto separado por ``|``)."""
        row: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                row[key] = "|".join(str(v) for v in value)
            else:
                row[key] = value
        return row


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_config(root: Path) -> dict[str, Any]:
    """Lê ``config/execucao.json`` (protocolo fixado na T13)."""
    config: dict[str, Any] = read_json(root / "config" / "execucao.json")
    return config


def _as_int(value: Any) -> int | None:
    """Número do bloco ou da ordem; ``None`` quando ausente ou não numérico (pilotos usam rótulos)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _compact_flag(identity: dict[str, Any]) -> str | None:
    value = identity.get("use_compact_object_headers")
    return None if value is None else str(value)


def _measurement_problems(result: dict[str, Any], measured: list[dict[str, Any]], expected: int | None) -> list[str]:
    problems: list[str] = []
    if result.get("status") != "success":
        problems.append(f"status {result.get('status')}")
    if not result.get("measurement_verified"):
        problems.append("medição não verificada")
    verified = result.get("verified_measurement") or {}
    if not verified.get("energy_j") or not verified.get("time_s"):
        problems.append("energia ou tempo ausente")
    if expected is not None and len(measured) != expected:
        problems.append(f"{len(measured)} iterações medidas (esperado {expected})")
    if any(item.get("status") != "measurement_valid" for item in measured):
        problems.append("iteração medida inválida")
    if any(not item.get("dacapo_valid", False) for item in measured):
        problems.append("validação do DaCapo falhou")
    if any(item.get("counter_wraps") for item in measured):
        problems.append("volta do contador RAPL")
    return problems


def build_record(
    folder: Path,
    root: Path,
    config: dict[str, Any],
    category: str,
    session: str,
    seed: int | None = None,
    plan_entry: dict[str, Any] | None = None,
    progress: dict[str, Any] | None = None,
) -> ProcessRecord:
    """Monta a linha de um processo a partir da sua pasta."""
    result: dict[str, Any] = read_json(folder / "resultado.json")
    verified: dict[str, Any] = result.get("verified_measurement") or {}
    iterations = read_json_lines(folder / "medidor" / "iterations.jsonl")
    warmups = [item for item in iterations if item.get("warmup")]
    measured = [item for item in iterations if not item.get("warmup")]
    identity_path = folder / "java-preflight.json"
    identity: dict[str, Any] = read_json(identity_path) if identity_path.is_file() else {}

    application = str((plan_entry or {}).get("application") or result.get("application"))
    configuration = str((plan_entry or {}).get("configuration") or result.get("configuration"))
    app_spec = config["applications"].get(application, {})
    expected = config.get("measured_iterations") if category == OFFICIAL else None

    energies = [float(v) for v in verified.get("measured_energy_j") or []]
    times = [float(v) for v in verified.get("measured_time_s") or []]
    energy = verified.get("energy_j")
    time_s = verified.get("time_s")
    if energies and times:
        power = sum(energies) / sum(times)
    elif energy and time_s:
        power = float(energy) / float(time_s)
    else:
        power = None

    warmup_ms = [float(v) for v in verified.get("warmup_dacapo_ms") or []] or [
        float(item["dacapo_duration_ms"]) for item in warmups if item.get("dacapo_duration_ms")
    ]
    measured_ms = [float(v) for v in verified.get("measured_dacapo_ms") or []] or [
        float(item["dacapo_duration_ms"]) for item in measured if item.get("dacapo_duration_ms")
    ]
    last_warmup = warmup_ms[-1] if warmup_ms else None
    measured_mean = statistics.mean(measured_ms) if measured_ms else None
    overhead = measured_mean / last_warmup - 1 if measured_mean and last_warmup else None

    gc = parse_gc_log(folder / "gc.log")
    problems = _measurement_problems(result, measured, expected)
    if gc is not None and gc.unparsed_pause_lines:
        problems.append(f"{gc.unparsed_pause_lines} linhas de pausa fora do formato")
    if category == OFFICIAL:
        # O log de GC passou a ser gravado no piloto da T12; na coleta oficial ele é obrigatório.
        if gc is None or not gc.uses_g1:
            problems.append("gc.log ausente ou sem G1")
        conf = config["configurations"][configuration]
        if identity.get("java_runtime_version") != conf["runtime_version"]:
            problems.append(f"versão do Java {identity.get('java_runtime_version')}")
        expected_compact = None if conf["compact_headers"] is None else str(conf["compact_headers"]).lower()
        if _compact_flag(identity) != expected_compact:
            problems.append("opção de cabeçalhos compactos diferente da configuração")

    block = (plan_entry or {}).get("block", result.get("block_id"))
    order = (plan_entry or {}).get("order", result.get("order"))
    cooling = (progress or {}).get("cooling") or {}
    return ProcessRecord(
        category=category,
        session=session,
        seed=seed,
        block=_as_int(block),
        order=_as_int(order),
        name=folder.name,
        application=application,
        role=app_spec.get("role"),
        configuration=configuration,
        java_runtime_version=identity.get("java_runtime_version") or verified.get("java_runtime_version"),
        compact_headers=_compact_flag(identity),
        energy_j=float(energy) if energy else None,
        time_s=float(time_s) if time_s else None,
        power_w=power,
        energy_iterations_j=energies,
        time_iterations_s=times,
        measured_iterations=len(measured),
        warmup_iterations=len(warmups),
        last_warmup_dacapo_ms=last_warmup,
        measured_dacapo_mean_ms=measured_mean,
        meter_overhead=overhead,
        gc_pauses=gc.pauses if gc else None,
        gc_young_pauses=gc.young_pauses if gc else None,
        gc_full_pauses=gc.full_pauses if gc else None,
        gc_other_pauses=gc.other_pauses if gc else None,
        gc_pause_time_ms=gc.pause_time_ms if gc else None,
        gc_heap_after_median_mb=gc.heap_after_median_mb if gc else None,
        idle_power_w=(result.get("idle_baseline") or {}).get("mean_power_w"),
        start_celsius=cooling.get("start_celsius"),
        wall_seconds=(progress or {}).get("wall_seconds") or result.get("total_wall_seconds"),
        valid=not problems,
        problems=problems,
        missing_files=[name for name in REQUIRED_FILES if not (folder / name).is_file()],
        source=folder.relative_to(root).as_posix() if folder.is_relative_to(root) else folder.as_posix(),
        result_sha256=sha256_file(folder / "resultado.json"),
    )


def official_session_folders(root: Path) -> list[Path]:
    """Pastas de sessão oficial: as que têm um plano gravado antes da execução."""
    base = root / "dados" / "brutos"
    return sorted(p for p in base.iterdir() if (p / "plano-antes-execucao.json").is_file()) if base.is_dir() else []


def consolidate_official_session(folder: Path, root: Path, config: dict[str, Any]) -> list[ProcessRecord]:
    """Uma linha por processo do plano da sessão. O aquecimento da máquina não entra."""
    plan: dict[str, Any] = read_json(folder / "plano-antes-execucao.json")
    progress = {item["name"]: item for item in read_json_lines(folder / "progresso.jsonl")}
    records = []
    for entry in plan["runs"]:
        process = folder / entry["name"]
        if not (process / "resultado.json").is_file():
            records.append(_missing_record(process, root, entry, folder.name, plan.get("seed")))
            continue
        records.append(
            build_record(
                process, root, config, OFFICIAL, folder.name, plan.get("seed"), entry, progress.get(entry["name"])
            )
        )
    return records


def _missing_record(folder: Path, root: Path, entry: dict[str, Any], session: str, seed: int | None) -> ProcessRecord:
    return ProcessRecord(
        category=OFFICIAL,
        session=session,
        seed=seed,
        block=entry.get("block"),
        order=entry.get("order"),
        name=entry["name"],
        application=entry["application"],
        role=None,
        configuration=entry["configuration"],
        java_runtime_version=None,
        compact_headers=None,
        energy_j=None,
        time_s=None,
        power_w=None,
        energy_iterations_j=[],
        time_iterations_s=[],
        measured_iterations=0,
        warmup_iterations=0,
        last_warmup_dacapo_ms=None,
        measured_dacapo_mean_ms=None,
        meter_overhead=None,
        gc_pauses=None,
        gc_young_pauses=None,
        gc_full_pauses=None,
        gc_other_pauses=None,
        gc_pause_time_ms=None,
        gc_heap_after_median_mb=None,
        idle_power_w=None,
        start_celsius=None,
        wall_seconds=None,
        valid=False,
        problems=["pasta do processo ausente"],
        missing_files=list(REQUIRED_FILES),
        source=folder.relative_to(root).as_posix() if folder.is_relative_to(root) else folder.as_posix(),
    )


def _pilot_process_folders(base: Path) -> Iterator[tuple[str, Path]]:
    for session in sorted(p for p in base.iterdir() if p.is_dir()):
        for process in sorted(p for p in session.iterdir() if (p / "resultado.json").is_file()):
            yield session.name, process


def consolidate_pilots(root: Path, config: dict[str, Any]) -> list[ProcessRecord]:
    """Pilotos T11 e T12: mantidos em base separada, nunca misturados com a coleta oficial."""
    base = root / "dados" / "piloto"
    if not base.is_dir():
        return []
    return [build_record(process, root, config, PILOT, session) for session, process in _pilot_process_folders(base)]


def consolidate(root: Path, sessions: Iterable[Path] | None = None) -> list[ProcessRecord]:
    """Base oficial completa (todas as sessões, na ordem das pastas)."""
    config = load_config(root)
    folders = list(sessions) if sessions is not None else official_session_folders(root)
    records: list[ProcessRecord] = []
    for folder in folders:
        records.extend(consolidate_official_session(folder, root, config))
    return records
