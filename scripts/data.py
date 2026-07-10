"""Generate the three manuscript figure assets produced with Python."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "dataset_48.csv"
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ai-scheduling-matplotlib")
)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


GROUP_ORDER = ["G1", "G2", "G3", "G4"]
GROUP_LABELS = {
    "G1": "G1\n(Manual-Nominal)",
    "G2": "G2\n(Manual-Compressed)",
    "G3": "G3\n(AI-Nominal)",
    "G4": "G4\n(AI-Compressed)",
}

plt.rcParams.update(
    {
        "font.family": "serif",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    required = ["Group", "Effort_Hours", "Quality_Score", "Success"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in dataset: {missing}")

    unexpected_groups = sorted(set(df["Group"]) - set(GROUP_ORDER))
    counts = df["Group"].value_counts().reindex(GROUP_ORDER, fill_value=0)
    if unexpected_groups or len(df) != 48 or not (counts == 12).all():
        raise ValueError(
            "Expected exactly 12 rows for each of G1-G4; "
            f"observed counts: {counts.to_dict()}, unexpected groups: {unexpected_groups}"
        )
    if df[["Effort_Hours", "Quality_Score", "Success"]].isna().any().any():
        raise ValueError("The plotting dataset contains missing numeric values")
    expected_success = (df["Quality_Score"] >= 75).astype(int)
    if not np.array_equal(df["Success"].astype(int), expected_success):
        raise ValueError("Success must equal int(Quality_Score >= 75)")
    return df


def plot_effort(df: pd.DataFrame) -> None:
    """Create Fig1_Effort_Analysis.pdf (manuscript Figure 2)."""

    effort_mean = df.groupby("Group")["Effort_Hours"].mean().reindex(GROUP_ORDER)
    effort_sd = df.groupby("Group")["Effort_Hours"].std().reindex(GROUP_ORDER)

    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(len(GROUP_ORDER))
    colors = ["#34495e", "#34495e", "#2ecc71", "#2ecc71"]
    ax.bar(x, effort_mean, yerr=effort_sd, capsize=5, color=colors)
    for position, (value, sd, group) in enumerate(
        zip(effort_mean, effort_sd, GROUP_ORDER)
    ):
        label = f"{value:.2f}\n(Hard cap)" if group == "G2" else f"{value:.2f}"
        ax.text(
            position,
            value + sd + 0.08,
            label,
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=10,
        )
    ax.axhline(
        y=6.0,
        color="gray",
        linestyle="--",
        alpha=0.6,
        label=r"Nominal time ($t_o=6.0$ h)",
    )
    ax.axhline(
        y=3.5,
        color="red",
        linestyle="--",
        alpha=0.8,
        label=r"Compressed time (3.5 h $\approx 0.6t_o$)",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([GROUP_LABELS[group] for group in GROUP_ORDER])
    ax.set_ylim(0, 6.9)
    ax.set_ylabel("Within-task effort proxy (hours)", fontweight="bold")
    ax.set_title("Observed Within-Task Effort Across Experimental Groups", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPO_ROOT / "Fig1_Effort_Analysis.pdf", format="pdf", bbox_inches="tight")
    plt.close(fig)


def plot_quality(df: pd.DataFrame) -> None:
    """Create Fig2_Quality_Distribution.pdf (manuscript Figure 3)."""

    quality_mean = df.groupby("Group")["Quality_Score"].mean().reindex(GROUP_ORDER)
    quality_sd = df.groupby("Group")["Quality_Score"].std().reindex(GROUP_ORDER)
    success_rates = (
        df.assign(Success_From_Threshold=(df["Quality_Score"] >= 75).astype(int))
        .groupby("Group")["Success_From_Threshold"]
        .mean()
        .reindex(GROUP_ORDER)
        * 100
    )

    fig, ax = plt.subplots(figsize=(8, 6))
    x = np.arange(len(GROUP_ORDER))
    colors = ["#34495e", "#34495e", "#2ecc71", "#2ecc71"]
    ax.bar(x, quality_mean, yerr=quality_sd, capsize=5, color=colors)
    ax.axhline(
        y=75,
        color="red",
        linestyle="-.",
        linewidth=2,
        label=r"Acceptability threshold ($Q \geq 75$)",
    )
    for position, (mean, sd, rate) in enumerate(
        zip(quality_mean, quality_sd, success_rates)
    ):
        ax.text(
            position,
            mean + sd + 1.5,
            f"{mean:.1f}",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=10,
        )
        ax.text(
            position,
            103,
            f"Success: {rate:.0f}%",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=10,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([GROUP_LABELS[group] for group in GROUP_ORDER])
    ax.set_ylim(0, 112)
    ax.set_ylabel("Composite Quality Score (0-100)", fontweight="bold")
    ax.set_title("Composite Quality Scores Across Groups", fontweight="bold")
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(
        REPO_ROOT / "Fig2_Quality_Distribution.pdf", format="pdf", bbox_inches="tight"
    )
    plt.close(fig)


def plot_theoretical_curve() -> None:
    """Create Fig3_Theoretical_Curve.pdf (manuscript Figure 1).

    This is a conceptual contrast only.  The illustrative alpha=2 curve and
    band are not fitted to the participant data and are not confidence bounds.
    """

    normalized_time = np.linspace(0.4, 1.2, 200)
    alpha_classic = 4.0
    alpha_ai_illustrative = 2.0
    alpha_ai_low = 1.6
    alpha_ai_high = 2.4

    classic_effort = (1 / normalized_time) ** alpha_classic
    ai_effort = (1 / normalized_time) ** alpha_ai_illustrative
    ai_low = (1 / normalized_time) ** alpha_ai_low
    ai_high = (1 / normalized_time) ** alpha_ai_high

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(
        normalized_time,
        classic_effort,
        label=r"Classical Putnam curve ($\alpha=4$)",
        color="black",
        linestyle="--",
    )
    ax.plot(
        normalized_time,
        ai_effort,
        label=r"Illustrative AI-assisted curve ($\alpha=2.0$)",
        color="green",
        linewidth=3,
    )
    ax.fill_between(
        normalized_time,
        ai_low,
        ai_high,
        color="green",
        alpha=0.2,
        label="Conceptual sensitivity band",
    )
    ax.axvspan(
        0.4,
        0.75,
        color="red",
        alpha=0.1,
        label="High-sensitivity region (conceptual)",
    )
    ax.axvline(x=0.75, color="red", linestyle=":")
    ax.set_ylim(0, 5)
    ax.set_xlim(0.4, 1.1)
    ax.set_xlabel(r"Normalized Schedule Time ($t_d/t_o$)", fontweight="bold")
    ax.set_ylabel(r"Normalized Effort ($E/E_o$)", fontweight="bold")
    ax.set_title("Conceptual Comparison: Classical vs. AI-Assisted Curves", fontweight="bold")
    ax.legend()
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    fig.tight_layout()
    fig.savefig(
        REPO_ROOT / "Fig3_Theoretical_Curve.pdf", format="pdf", bbox_inches="tight"
    )
    plt.close(fig)


def main() -> None:
    data = load_data()
    plot_effort(data)
    plot_quality(data)
    plot_theoretical_curve()
    print(
        "Figures saved: Fig1_Effort_Analysis.pdf, "
        "Fig2_Quality_Distribution.pdf, Fig3_Theoretical_Curve.pdf"
    )


if __name__ == "__main__":
    main()
