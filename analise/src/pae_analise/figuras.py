"""Figuras da análise (opcional; requer ``matplotlib``).

Figuras em PNG (300 dpi) e PDF:
    razoes        razões B/A, C/B e D/C de energia, tempo e potência com IC 95%, por aplicação;
    decomposicao  razão de potência × razão de tempo de cada comparação, com curvas de mesma energia;
    memoria       efeito dos cabeçalhos compactos (D/C) em energia, heap e coleta de lixo;
    sessoes       mediana de energia por sessão (critério E2), por aplicação × configuração;
    energia       energia por processo em cada configuração (material suplementar);
    fluxo         etapas do protocolo PAE-JVM (diagrama, não depende dos dados).
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any

from pae_analise.avaliacao import COMPARISONS, official_valid
from pae_analise.consolidacao import ProcessRecord

CONFIG_COLORS = {"A": "#4C78A8", "B": "#F58518", "C": "#54A24B", "D": "#B279A2"}
METRIC_STYLE = {"energy_j": ("energia", "o"), "time_s": ("tempo", "s"), "power_w": ("potência", "^")}
APP_COLORS = {"lusearch": "#4C78A8", "pmd": "#E45756", "avrora": "#9D9D9D"}
COMPARISON_MARKERS = {"B/A": "o", "C/B": "s", "D/C": "^"}
MEMORY_METRICS = {
    "energy_j": "energia",
    "gc_heap_after_median_mb": "heap após a coleta",
    "gc_pauses": "número de coletas",
    "gc_pause_time_ms": "tempo de pausa",
}


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


def _row(rows: Sequence[dict[str, Any]], app: str, metric: str, comparison: str) -> dict[str, Any] | None:
    return next(
        (r for r in rows if r["application"] == app and r["metric"] == metric and r["comparison"] == comparison),
        None,
    )


def _app_label(app: str, rows: Sequence[dict[str, Any]]) -> str:
    role = next((r.get("role") for r in rows if r["application"] == app), None)
    return f"{app} (exploratória)" if role == "exploratorio" else app


def _percent_axis(axis: Any) -> None:
    """Mostra uma razão como variação percentual (1,05 -> +5%)."""
    from matplotlib.ticker import FuncFormatter

    def label(value: float, _: object) -> str:
        percent = round((value - 1) * 100, 1)
        if percent == 0:
            return "0%"
        text = f"{percent:+.0f}" if percent.is_integer() else f"{percent:+.1f}"
        return f"{text}%".replace(".", ",")

    axis.set_major_formatter(FuncFormatter(label))


def plot_decomposition(comparisons: Sequence[dict[str, Any]], folder: Path) -> list[Path]:
    """Razão de potência (eixo y) contra razão de tempo (eixo x), com IC 95% nos dois eixos.

    Como E = P × t, os pontos sobre a mesma curva y = k/x têm a mesma razão de energia k.
    Ponto à esquerda da linha vertical: ficou mais rápido; acima da horizontal: passou a consumir mais por segundo.
    """
    plt = _pyplot()
    apps = sorted({r["application"] for r in comparisons})
    points: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
    for app in apps:
        for comparison in COMPARISON_MARKERS:
            time_row = _row(comparisons, app, "time_s", comparison)
            power_row = _row(comparisons, app, "power_w", comparison)
            if time_row and power_row:
                points.append((app, comparison, time_row, power_row))
    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    if points:
        xs = [v for *_, t, _ in points for v in (t["ci_low"], t["ci_high"])]
        ys = [v for *_, p in points for v in (p["ci_low"], p["ci_high"])]
        span = max(max(abs(v - 1) for v in xs + ys), 0.02) * 1.25
        low, high = 1 - span, 1 + span
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        grid = [low + (high - low) * i / 200 for i in range(201)]
        step = 0.05 if span > 0.08 else 0.02
        levels = sorted({round(1 + step * k, 4) for k in range(-6, 7) if abs(step * k) < span * 1.6})
        for level in levels:
            curve = [(x, level / x) for x in grid if low <= level / x <= high]
            if not curve:
                continue
            style = {"color": "black", "linewidth": 0.9} if level == 1 else {"color": "#BBBBBB", "linewidth": 0.6}
            ax.plot([c[0] for c in curve], [c[1] for c in curve], linestyle="--", zorder=1, **style)
            change = round((level - 1) * 100)
            ax.annotate(
                "E 0%" if change == 0 else f"E {change:+d}%",
                curve[0],  # Ponto da curva na borda superior ou esquerda do gráfico.
                fontsize=6.5,
                color="#555555",
                xytext=(3, -9),
                textcoords="offset points",
            )
        ax.axvline(1.0, color="#DDDDDD", linewidth=0.6, zorder=0)
        ax.axhline(1.0, color="#DDDDDD", linewidth=0.6, zorder=0)
    for app, comparison, time_row, power_row in points:
        ax.errorbar(
            time_row["ratio"],
            power_row["ratio"],
            xerr=[[time_row["ratio"] - time_row["ci_low"]], [time_row["ci_high"] - time_row["ratio"]]],
            yerr=[[power_row["ratio"] - power_row["ci_low"]], [power_row["ci_high"] - power_row["ratio"]]],
            fmt=COMPARISON_MARKERS[comparison],
            color=APP_COLORS.get(app, "black"),
            markersize=6,
            capsize=2,
            linewidth=0.8,
            zorder=3,
        )
    _percent_axis(ax.xaxis)
    _percent_axis(ax.yaxis)
    ax.set_xlabel("variação do tempo (razão das medianas, IC 95%)")
    ax.set_ylabel("variação da potência média (IC 95%)")
    handles = [
        plt.Line2D([], [], color=APP_COLORS.get(app, "black"), linewidth=3, label=_app_label(app, comparisons))
        for app in apps
    ]
    handles += [
        plt.Line2D([], [], color="black", marker=marker, linestyle="", label=comparison)
        for comparison, marker in COMPARISON_MARKERS.items()
    ]
    handles.append(plt.Line2D([], [], color="black", linestyle="--", linewidth=0.9, label="mesma energia"))
    ax.legend(handles=handles, fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    ax.set_aspect("equal")
    fig.tight_layout()
    paths = _save(fig, folder, "decomposicao")
    plt.close(fig)
    return paths


def plot_memory(comparisons: Sequence[dict[str, Any]], folder: Path, comparison: str = "D/C") -> list[Path]:
    """Razões D/C (cabeçalhos compactos ligados ÷ desligados) de energia, heap e coleta de lixo, com IC 95%."""
    plt = _pyplot()
    apps = sorted({r["application"] for r in comparisons})
    metrics = list(MEMORY_METRICS)
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    offsets = [(i - (len(apps) - 1) / 2) * 0.22 for i in range(len(apps))]
    for offset, app in zip(offsets, apps, strict=True):
        for y, metric in enumerate(metrics):
            row = _row(comparisons, app, metric, comparison)
            if row is None or row["ratio"] is None:
                continue
            ax.errorbar(
                row["ratio"],
                y + offset,
                xerr=[[row["ratio"] - row["ci_low"]], [row["ci_high"] - row["ratio"]]],
                fmt="o",
                color=APP_COLORS.get(app, "black"),
                markersize=5,
                capsize=3,
                linewidth=0.9,
                label=_app_label(app, comparisons) if y == 0 else None,
            )
    ax.axvline(1.0, color="grey", linewidth=0.8, linestyle="--")
    ax.set_yticks(range(len(metrics)), [MEMORY_METRICS[m] for m in metrics])
    ax.invert_yaxis()
    _percent_axis(ax.xaxis)
    ax.set_xlabel(f"variação {comparison} (razão das medianas, IC 95%)")
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.tight_layout()
    paths = _save(fig, folder, "memoria")
    plt.close(fig)
    return paths


# Etapas do PAE-JVM: (título, descrição, requisitos atendidos).
PAE_JVM_STEPS: tuple[tuple[str, str, str], ...] = (
    ("1. Registro prévio", "hipóteses H1–H5,\nlimites E1–E7 e\ncódigo de sorteio", "R3, R6"),
    ("2. Preparação verificada", "JDK pelo SDKMAN conferido\ndentro da JVM; SHA-256\ndos jars; na tomada", "R1, R6"),
    ("3. Sessão em blocos", "blocos completos\n(A, B, C, D) em\nordem sorteada", "R2, R3"),
    ("4. Execução medida", "núcleos P fixos, espera\ntérmica, aquecimentos,\n3 iterações com RAPL", "R1, R4, R5"),
    ("5. Conferência", "manifesto SHA-256,\nfalhas preservadas,\nnova tentativa no bloco", "R6"),
    ("6. Análise", "razão das medianas\npareada por bloco,\nIC bootstrap, Holm, A12", "R4"),
    ("7. Avaliação", "critérios E1–E7\n(FEDS: risco técnico\ne eficácia)", "R1–R7"),
)


def plot_flow(folder: Path) -> list[Path]:
    """Diagrama das etapas do PAE-JVM em duas linhas (em "U"), com o ciclo de refinamento da DSR."""
    plt = _pyplot()
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    width, height, gap_x, gap_y = 2.3, 1.45, 0.45, 0.75
    # Linha de cima da esquerda para a direita (1–4); linha de baixo da direita para a esquerda (5–7).
    columns = [0, 1, 2, 3, 3, 2, 1]
    rows = [0, 0, 0, 0, 1, 1, 1]
    positions = [(c * (width + gap_x), -r * (height + gap_y)) for c, r in zip(columns, rows, strict=True)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for (x, y), (title, body, reqs) in zip(positions, PAE_JVM_STEPS, strict=True):
        final = title.startswith("7.")
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor="#F6E8E8" if final else "#E8EEF6",
                edgecolor="#333333",
                linewidth=0.8,
            )
        )
        ax.text(x + width / 2, y + height - 0.2, title, ha="center", va="center", fontsize=7.5, weight="bold")
        ax.text(x + width / 2, y + height / 2 - 0.12, body, ha="center", va="center", fontsize=6.5, linespacing=1.3)
        ax.text(x + width - 0.07, y + 0.1, reqs, ha="right", va="center", fontsize=5.8, color="#555555")

    def arrow(start: tuple[float, float], end: tuple[float, float], **kwargs: Any) -> None:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=9, linewidth=0.9, **kwargs))

    for (x0, y0), (x1, y1) in pairwise(positions):
        if y0 != y1:
            arrow((x0 + width / 2, y0), (x1 + width / 2, y1 + height), color="#333333")
        elif x1 > x0:
            arrow((x0 + width, y0 + height / 2), (x1, y1 + height / 2), color="#333333")
        else:
            arrow((x0, y0 + height / 2), (x1 + width, y1 + height / 2), color="#333333")
    (xe, ye), (xs, ys) = positions[-1], positions[1]
    arrow((xe + width / 2, ye + height), (xs + width / 2, ys), color="#A03030", linestyle="--")
    ax.text(
        xe - 0.15,
        ye + height / 2,
        "ciclo de projeto da DSR:\nas avaliações dos pilotos\n(T11 e T12) refinaram\nas etapas 2 a 6",
        fontsize=6.5,
        color="#A03030",
        ha="right",
        va="center",
    )
    ax.set_xlim(-0.1, 4 * (width + gap_x) - gap_x + 0.1)
    ax.set_ylim(-(height + gap_y) - 0.1, height + 0.1)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    paths = _save(fig, folder, "fluxo")
    plt.close(fig)
    return paths
