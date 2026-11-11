from pathlib import Path
from typing import Any

import pytest

from pae_analise import figuras

pytest.importorskip("matplotlib")


def _rows() -> list[dict[str, Any]]:
    rows = []
    for app, role in (("lusearch", "principal"), ("avrora", "exploratorio")):
        for comparison in ("B/A", "C/B", "D/C"):
            for metric in ("energy_j", "time_s", "power_w", "gc_heap_after_median_mb", "gc_pauses", "gc_pause_time_ms"):
                rows.append(
                    {
                        "application": app,
                        "role": role,
                        "metric": metric,
                        "comparison": comparison,
                        "ratio": 0.97,
                        "ci_low": 0.95,
                        "ci_high": 0.99,
                    }
                )
    return rows


@pytest.mark.parametrize(
    ("name", "draw"),
    [
        ("decomposicao", lambda rows, folder: figuras.plot_decomposition(rows, folder)),
        ("memoria", lambda rows, folder: figuras.plot_memory(rows, folder)),
        ("fluxo", lambda rows, folder: figuras.plot_flow(folder)),
        (
            "memoria-cabecalhos",
            lambda rows, folder: figuras.plot_memory(rows, folder, xlabel="com e sem", name="memoria-cabecalhos"),
        ),
        (
            "fluxo-cabecalhos",
            lambda rows, folder: figuras.plot_flow(
                folder, steps=figuras.PAE_JVM_STEPS_CABECALHOS, name="fluxo-cabecalhos"
            ),
        ),
    ],
)
def test_figures_write_png_and_pdf(name: str, draw: Any, tmp_path: Path) -> None:
    paths = draw(_rows(), tmp_path)
    assert [p.name for p in paths] == [f"{name}.png", f"{name}.pdf"]
    assert all(p.stat().st_size > 0 for p in paths)
    with pytest.raises(FileExistsError):
        draw(_rows(), tmp_path)


def test_article_steps_drop_h5_and_a12() -> None:
    full = " ".join(body for _, body, _ in figuras.PAE_JVM_STEPS)
    article = " ".join(body for _, body, _ in figuras.PAE_JVM_STEPS_CABECALHOS)
    assert "H1–H5" in full and "A12" in full
    assert "H1–H4" in article and "H5" not in article and "A12" not in article
    assert "(A, B, C, D)" not in article
    assert len(figuras.PAE_JVM_STEPS_CABECALHOS) == len(figuras.PAE_JVM_STEPS)


def test_percent_labels_use_comma_and_sign() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    figuras._percent_axis(ax.xaxis)
    formatter = ax.xaxis.get_major_formatter()
    assert [formatter(v, 0) for v in (1.0, 1.05, 0.975, 0.9)] == ["0%", "+5%", "-2,5%", "-10%"]
    plt.close(fig)
