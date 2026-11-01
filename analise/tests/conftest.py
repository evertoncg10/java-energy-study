from pathlib import Path

import pytest

from pae_analise.consolidacao import ProcessRecord, consolidate

ROOT = Path(__file__).resolve().parents[2]
HAS_OFFICIAL_DATA = (ROOT / "dados" / "brutos").is_dir() and any((ROOT / "dados" / "brutos").iterdir())

needs_data = pytest.mark.skipif(not HAS_OFFICIAL_DATA, reason="dados oficiais ausentes")


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def official_records() -> list[ProcessRecord]:
    if not HAS_OFFICIAL_DATA:
        pytest.skip("dados oficiais ausentes")
    return consolidate(ROOT)
