import csv
import json
from pathlib import Path

import pytest

from pae_analise.cli import find_root, main

from .conftest import needs_data


@needs_data
def test_full_analysis_writes_every_output(root: Path, tmp_path: Path) -> None:
    out = tmp_path / "analise"
    code = main(["--raiz", str(root), "analisar", "--saida", str(out), "--reamostragens", "200", "--sem-figuras"])
    assert code == 0
    for name in (
        "base-oficial.csv",
        "base-oficial.json",
        "base-pilotos.csv",
        "descritiva.csv",
        "razoes.csv",
        "decomposicao.csv",
        "hipoteses.csv",
        "criterios.json",
        "h4.json",
        "metadados.json",
        "resumo.txt",
    ):
        assert (out / name).is_file(), name
    with (out / "base-oficial.csv").open(encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 180
    meta = json.loads((out / "metadados.json").read_text(encoding="utf-8"))
    assert meta["settings"]["resamples"] == 200
    assert len(meta["input_sha256"]) == 64


@needs_data
def test_never_overwrites_an_existing_output(root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "consolidacao"
    assert main(["--raiz", str(root), "consolidar", "--saida", str(out)]) == 0
    assert main(["--raiz", str(root), "consolidar", "--saida", str(out)]) == 2
    assert "não será sobrescrita" in capsys.readouterr().err


@needs_data
def test_results_are_reproducible_with_the_same_seed(root: Path, tmp_path: Path) -> None:
    args = ["--raiz", str(root), "analisar", "--reamostragens", "300", "--sem-figuras", "--saida"]
    assert main([*args, str(tmp_path / "a")]) == 0
    assert main([*args, str(tmp_path / "b")]) == 0
    assert (tmp_path / "a" / "razoes.csv").read_bytes() == (tmp_path / "b" / "razoes.csv").read_bytes()


def test_find_root_walks_up(root: Path) -> None:
    assert find_root(root / "analise" / "src") == root
