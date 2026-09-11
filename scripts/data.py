"""Generate manuscript Figures 1-3 directly from the final reported summaries."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ai-scheduling-matplotlib"))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from analysis import (  # noqa: E402
    GROUPS,
    load_quality_summary,
    load_threshold_sensitivity,
    quality_summary_with_intervals,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANUAL_COLOR = "#667085"
AI_COLOR = "#178579"
THRESHOLD_COLOR = "#b96a6a"
GROUP_TICK_LABELS = ["G1\nManual\nNominal", "G2\nManual\nCompressed", "G3\nAI\nNominal", "G4\nAI\nCompressed"]

plt.rcParams.update({"font.family": "serif", "pdf.fonttype": 42, "ps.fonttype": 42})


def plot_within_window_success() -> Path:
    summary = quality_summary_with_intervals().set_index("Group").reindex(GROUPS)
    proportions = summary["Success_Percent"].to_numpy(dtype=float)
    lower = 100 * summary["Success_Wilson_Lower"].to_numpy(dtype=float)
    upper = 100 * summary["Success_Wilson_Upper"].to_numpy(dtype=float)
    counts = summary["Success_Q75"].to_numpy(dtype=int)
    n = summary["N"].to_numpy(dtype=int)
    x = np.arange(4)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for indices, label, color in [([0, 1], "Manual", MANUAL_COLOR), ([2, 3], "AI-assisted", AI_COLOR)]:
        idx = np.array(indices)
        ax.errorbar(
            x[idx],
            proportions[idx],
            yerr=np.maximum(0.0, np.vstack((proportions[idx] - lower[idx], upper[idx] - proportions[idx]))),
            fmt="o",
            capsize=4,
            linewidth=1.5,
            color=color,
            label=label,
        )
    for xpos, pct, y, total in zip(x, proportions, counts, n):
        ax.text(xpos, min(102, pct + 4), f"{y}/{total}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, GROUP_TICK_LABELS)
    ax.set_ylabel("Within-window success (%)")
    ax.set_ylim(-3, 108)
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    output = REPO_ROOT / "Fig1_Within_Window_Success.pdf"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_composite_quality() -> Path:
    summary = load_quality_summary().set_index("Group").reindex(GROUPS)
    means = summary["Q_Mean"].to_numpy(dtype=float)
    sds = summary["Q_SD"].to_numpy(dtype=float)
    x = np.arange(4)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for indices, label, color in [([0, 1], "Manual", MANUAL_COLOR), ([2, 3], "AI-assisted", AI_COLOR)]:
        idx = np.array(indices)
        ax.errorbar(x[idx], means[idx], yerr=sds[idx], fmt="o", capsize=4, linewidth=1.5, color=color, label=label)
    ax.axhline(75, linestyle="--", linewidth=1.3, color=THRESHOLD_COLOR, label=r"Acceptability threshold ($Q\geq75$)")
    for xpos, mean, sd in zip(x, means, sds):
        ax.text(xpos, mean + sd + 2.0, f"{mean:.1f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, GROUP_TICK_LABELS)
    ax.set_ylabel("Composite quality score (0-100)")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    output = REPO_ROOT / "Fig2_Composite_Quality.pdf"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_threshold_sensitivity() -> Path:
    table = load_threshold_sensitivity().set_index("Threshold")
    x = np.arange(4)
    width = 0.23
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for offset, threshold in zip([-width, 0.0, width], [70, 75, 80]):
        values = table.loc[threshold, GROUPS].to_numpy(dtype=int)
        bars = ax.bar(x + offset, values, width, label=rf"$Q\geq{threshold}$")
        ax.bar_label(bars, padding=2, fontsize=8)
    ax.set_xticks(x, GROUPS)
    ax.set_ylabel("Acceptable submissions / 12")
    ax.set_ylim(0, 13)
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    fig.tight_layout()
    output = REPO_ROOT / "Fig3_Threshold_Sensitivity.pdf"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def main() -> None:
    outputs = [plot_within_window_success(), plot_composite_quality(), plot_threshold_sensitivity()]
    print("Figures saved:", ", ".join(path.name for path in outputs))


if __name__ == "__main__":
    main()
