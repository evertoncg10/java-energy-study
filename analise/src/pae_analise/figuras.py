"""Figuras da análise (opcional; requer ``matplotlib``).

Três figuras, em PNG (300 dpi) e PDF:
    razoes      razões B/A, C/B e D/C de energia, tempo e potência com IC 95%, por aplicação;
    energia     energia por processo em cada configuração, por aplicação;
    sessoes     mediana de energia por sessão (critério E2), por aplicação × configuração.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pae_analise.avaliacao import COMPARISONS, official_valid
from pae_analise.consolidacao import ProcessRecord

CONFIG_COLORS = {"A": "#4C78A8", "B": "#F58518", "C": "#54A24B", "D": "#B279A2"}
METRIC_STYLE = {"energy_j": ("energia", "o"), "time_s": ("tempo", "s"), "power_w": ("potência", "^")}


def available() -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def _pyplot() -> Any:
    import matplotlib

    matplotlib.use("Agg")  # Sem janela: grava direto em arquivo.
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Any, folder: Path, name: str) -> list[Path]:
    paths = []
    for extension in ("png", "pdf"):
        path = folder / f"{name}.{extension}"
        if path.exists():
            raise FileExistsError(path)
        fig.savefig(path, dpi=300, bbox_inches="tight")
        paths.append(path)
    return paths


def plot_ratios(comparisons: Sequence[dict[str, Any]], folder: Path) -> list[Path]:
    plt = _pyplot()
    apps = sorted({r["application"] for r in comparisons})
    fig, axes = plt.subplots(1, len(apps), figsize=(4 * len(apps), 3.6), sharey=True)
    axes = [axes] if len(apps) == 1 else list(axes)
    labels = [f"{n}/{d}" for n, d in COMPARISONS]
    for ax, app in zip(axes, apps, strict=True):
        for offset, (metric, (label, marker)) in zip((-0.2, 0.0, 0.2), METRIC_STYLE.items(), strict=True):
            for y, comparison in enumerate(labels):
                row = next(
                    (
                        r
                        for r in comparisons
                        if r["application"] == app and r["metric"] == metric and r["comparison"] == comparison
                    ),
                    None,
                )
                if row is None:
                    continue
                ax.errorbar(
                    row["ratio"],
                    y + offset,
                    xerr=[[row["ratio"] - row["ci_low"]], [row["ci_high"] - row["ratio"]]],
                    fmt=marker,
                    color="black",
                    capsize=3,
                    markersize=5,
                    label=label if y == 0 else None,
                )
        ax.axvline(1.0, color="grey", linewidth=0.8, linestyle="--")
        ax.set_yticks(range(len(labels)), labels)
        ax.set_title(app)
        ax.set_xlabel("razão das medianas (IC 95%)")
        ax.invert_yaxis()
    axes[0].legend(loc="best", fontsize=8)
    fig.tight_layout()
    paths = _save(fig, folder, "razoes")
    plt.close(fig)
    return paths


def plot_energy(records: Sequence[ProcessRecord], folder: Path) -> list[Path]:
    plt = _pyplot()
    valid = official_valid(records)
    apps = sorted({r.application for r in valid})
    fig, axes = plt.subplots(1, len(apps), figsize=(4 * len(apps), 3.6))
    axes = [axes] if len(apps) == 1 else list(axes)
    for ax, app in zip(axes, apps, strict=True):
        confs = sorted({r.configuration for r in valid if r.application == app})
        data = [
            [r.energy_j for r in valid if r.application == app and r.configuration == c and r.energy_j] for c in confs
        ]
        box = ax.boxplot(data, patch_artist=True, widths=0.6)
        ax.set_xticks(range(1, len(confs) + 1), confs)
        for patch, conf in zip(box["boxes"], confs, strict=True):
            patch.set_facecolor(CONFIG_COLORS.get(conf, "white"))
            patch.set_alpha(0.6)
        ax.set_title(app)
        ax.set_ylabel("energia do pacote por iteração (J)")
    fig.tight_layout()
    paths = _save(fig, folder, "energia")
    plt.close(fig)
    return paths


def plot_sessions(e2: dict[str, Any], folder: Path) -> list[Path]:
    plt = _pyplot()
    apps = sorted({c["application"] for c in e2["cells"]})
    fig, axes = plt.subplots(1, len(apps), figsize=(4 * len(apps), 3.6))
    axes = [axes] if len(apps) == 1 else list(axes)
    for ax, app in zip(axes, apps, strict=True):
        for cell in (c for c in e2["cells"] if c["application"] == app):
            values = list(cell["session_medians"].values())
            ax.plot(
                range(1, len(values) + 1),
                values,
                marker="o",
                color=CONFIG_COLORS.get(cell["configuration"]),
                label=cell["configuration"],
            )
        ax.set_title(app)
        ax.set_xlabel("sessão")
        ax.set_ylabel("mediana da energia (J)")
        ax.legend(fontsize=8)
    fig.tight_layout()
    paths = _save(fig, folder, "sessoes")
    plt.close(fig)
    return paths
