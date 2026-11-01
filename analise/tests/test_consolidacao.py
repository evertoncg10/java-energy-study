import json
import shutil
from pathlib import Path

import pytest

from pae_analise.consolidacao import OFFICIAL, ProcessRecord, build_record, consolidate, load_config

from .conftest import needs_data


@needs_data
def test_official_base_has_one_valid_row_per_planned_process(official_records: list[ProcessRecord]) -> None:
    assert len(official_records) == 180
    assert all(r.valid for r in official_records), [r.problems for r in official_records if not r.valid]
    assert {r.category for r in official_records} == {OFFICIAL}
    assert not any(r.name == "aquecimento-maquina" for r in official_records)
    assert len({(r.session, r.name) for r in official_records}) == 180


@needs_data
def test_values_come_from_the_original_files(official_records: list[ProcessRecord], root: Path) -> None:
    record = official_records[0]
    result = json.loads((root / record.source / "resultado.json").read_text(encoding="utf-8"))
    measured = result["verified_measurement"]
    assert record.energy_j == measured["energy_j"]
    assert record.time_s == measured["time_s"]
    assert record.power_w == pytest.approx(sum(measured["measured_energy_j"]) / sum(measured["measured_time_s"]))
    assert record.energy_j == pytest.approx(record.power_w * record.time_s)
    assert len(record.result_sha256 or "") == 64


@needs_data
def test_blocks_and_configurations_are_complete(official_records: list[ProcessRecord]) -> None:
    cells = {(r.application, r.configuration, r.block) for r in official_records}
    assert len(cells) == 3 * 4 * 15
    assert {r.block for r in official_records} == set(range(1, 16))


@needs_data
def test_detects_a_wrong_compact_header_flag(root: Path, tmp_path: Path) -> None:
    session = root / "dados" / "brutos" / "20261022T215204Z"
    plan = json.loads((session / "plano-antes-execucao.json").read_text(encoding="utf-8"))
    entry = next(e for e in plan["runs"] if e["configuration"] == "D")
    copy = tmp_path / entry["name"]
    shutil.copytree(session / entry["name"], copy, ignore=shutil.ignore_patterns("scratch"))
    preflight = copy / "java-preflight.json"
    data = json.loads(preflight.read_text(encoding="utf-8"))
    data["use_compact_object_headers"] = "false"
    preflight.write_text(json.dumps(data), encoding="utf-8")
    record = build_record(copy, tmp_path, load_config(root), OFFICIAL, session.name, plan["seed"], entry)
    assert not record.valid
    assert "opção de cabeçalhos compactos diferente da configuração" in record.problems


@needs_data
def test_missing_process_folder_becomes_an_invalid_row(root: Path, tmp_path: Path) -> None:
    session = root / "dados" / "brutos" / "20261022T215214Z"
    copy = tmp_path / "dados" / "brutos" / session.name
    shutil.copytree(session, copy, ignore=shutil.ignore_patterns("scratch"))
    shutil.copytree(root / "config", tmp_path / "config")
    plan = json.loads((copy / "plano-antes-execucao.json").read_text(encoding="utf-8"))
    removed = plan["runs"][0]["name"]
    shutil.rmtree(copy / removed)
    records = consolidate(tmp_path)
    missing = next(r for r in records if r.name == removed)
    assert not missing.valid
    assert missing.problems == ["pasta do processo ausente"]
    assert sum(r.valid for r in records) == len(plan["runs"]) - 1
