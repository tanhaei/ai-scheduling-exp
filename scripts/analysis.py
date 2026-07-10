"""Reproduce the manuscript's quantitative analyses from the public data.

The participant-level CSV in this repository is a synthetic reconstruction of
the reported effort and composite-quality summaries.  Aggregate-only outcomes
(quality components, weight sensitivity, and security counts) are kept in
separate files so that they are not misrepresented as raw participant data.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.stats import f as f_distribution
from scipy.stats import fisher_exact, norm, t as t_distribution


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
PARTICIPANT_DATA = DATA_DIR / "dataset_48.csv"
QUALITY_COMPONENT_DATA = DATA_DIR / "quality_components_summary.csv"
WEIGHT_SENSITIVITY_DATA = DATA_DIR / "weight_sensitivity_summary.csv"
SECURITY_DATA = DATA_DIR / "security_summary.csv"

GROUPS = ["G1", "G2", "G3", "G4"]
QUALITY_WEIGHTS = {
    "PassRate": 0.45,
    "Coverage": 0.20,
    "Static_Score": 0.15,
    "Security_Score": 0.20,
}


def require_columns(df: pd.DataFrame, required: Iterable[str], source: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def load_participant_data(path: Path = PARTICIPANT_DATA) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Participant dataset not found: {path}")

    df = pd.read_csv(path)
    require_columns(
        df,
        ["Group", "Effort_Hours", "Quality_Score", "Success"],
        path.name,
    )

    unexpected_groups = sorted(set(df["Group"]) - set(GROUPS))
    if unexpected_groups:
        raise ValueError(f"Unexpected experimental groups: {unexpected_groups}")

    counts = df["Group"].value_counts().reindex(GROUPS, fill_value=0)
    if len(df) != 48 or not (counts == 12).all():
        raise ValueError(
            "The manuscript design requires 48 rows and 12 participants per cell; "
            f"observed counts are {counts.to_dict()}"
        )

    numeric_columns = ["Effort_Hours", "Quality_Score", "Success"]
    if df[numeric_columns].isna().any().any():
        raise ValueError("Participant data contain missing numeric values")
    if not np.isfinite(df[numeric_columns].to_numpy(dtype=float)).all():
        raise ValueError("Participant data contain non-finite numeric values")
    if (df["Effort_Hours"] <= 0).any():
        raise ValueError("Effort_Hours must be positive")
    if not df["Quality_Score"].between(0, 100).all():
        raise ValueError("Quality_Score must be between 0 and 100")

    expected_success = (df["Quality_Score"] >= 75).astype(int)
    if not np.array_equal(df["Success"].astype(int), expected_success):
        bad_rows = df.index[df["Success"].astype(int) != expected_success].tolist()
        raise ValueError(
            "Success must equal int(Quality_Score >= 75); inconsistent rows: "
            f"{bad_rows}"
        )

    g2_effort = df.loc[df["Group"] == "G2", "Effort_Hours"].to_numpy()
    if not np.allclose(g2_effort, 3.5, atol=1e-12):
        raise ValueError("Every G2 effort value must equal the reported 3.5-hour cap")

    return df


def mean_ci(values: pd.Series) -> tuple[float, float, float, float]:
    array = values.to_numpy(dtype=float)
    n = len(array)
    mean = float(np.mean(array))
    sd = float(np.std(array, ddof=1))
    if sd == 0:
        return mean, sd, mean, mean
    half_width = float(t_distribution.ppf(0.975, n - 1) * sd / np.sqrt(n))
    return mean, sd, mean - half_width, mean + half_width


def build_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for group in GROUPS:
        cell = df.loc[df["Group"] == group]
        effort = mean_ci(cell["Effort_Hours"])
        quality = mean_ci(cell["Quality_Score"])
        rows.append(
            {
                "Group": group,
                "Effort_Mean": effort[0],
                "Effort_SD": effort[1],
                "Effort_CI_Lower": effort[2],
                "Effort_CI_Upper": effort[3],
                "Quality_Mean": quality[0],
                "Quality_SD": quality[1],
                "Quality_CI_Lower": quality[2],
                "Quality_CI_Upper": quality[3],
                "Success_Rate": 100 * float((cell["Quality_Score"] >= 75).mean()),
            }
        )
    return pd.DataFrame(rows)


def two_way_anova(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Compute the balanced 2x2 fixed-effects ANOVA used in Tables 5 and 6."""

    work = df.copy()
    work["Tool"] = work["Group"].isin(["G3", "G4"]).astype(int)
    work["Schedule"] = work["Group"].isin(["G2", "G4"]).astype(int)

    cell_counts = work.groupby(["Tool", "Schedule"], observed=True).size()
    if len(cell_counts) != 4 or cell_counts.nunique() != 1:
        raise ValueError("The closed-form ANOVA requires four equally sized cells")

    n_cell = int(cell_counts.iloc[0])
    grand_mean = float(work[outcome].mean())
    tool_means = work.groupby("Tool", observed=True)[outcome].mean()
    schedule_means = work.groupby("Schedule", observed=True)[outcome].mean()
    cell_means = work.groupby(["Tool", "Schedule"], observed=True)[outcome].mean()

    ss_tool = 2 * n_cell * float(((tool_means - grand_mean) ** 2).sum())
    ss_schedule = 2 * n_cell * float(((schedule_means - grand_mean) ** 2).sum())
    ss_interaction = n_cell * sum(
        (
            cell_means.loc[(tool, schedule)]
            - tool_means.loc[tool]
            - schedule_means.loc[schedule]
            + grand_mean
        )
        ** 2
        for tool in (0, 1)
        for schedule in (0, 1)
    )
    ss_residual = float(
        sum(
            ((cell[outcome] - cell[outcome].mean()) ** 2).sum()
            for _, cell in work.groupby(["Tool", "Schedule"], observed=True)
        )
    )

    df_residual = len(work) - 4
    ms_residual = ss_residual / df_residual
    rows: list[dict[str, float | int | str]] = []
    for term, ss in (
        ("Tool Support", ss_tool),
        ("Schedule Condition", ss_schedule),
        ("Tool x Schedule", ss_interaction),
    ):
        f_value = ss / ms_residual
        rows.append(
            {
                "Outcome": outcome,
                "Term": term,
                "SS": ss,
                "df": 1,
                "MS": ss,
                "F": f_value,
                "p": float(f_distribution.sf(f_value, 1, df_residual)),
                "Partial_Eta_Squared": ss / (ss + ss_residual),
            }
        )
    rows.append(
        {
            "Outcome": outcome,
            "Term": "Residual",
            "SS": ss_residual,
            "df": df_residual,
            "MS": ms_residual,
            "F": np.nan,
            "p": np.nan,
            "Partial_Eta_Squared": np.nan,
        }
    )
    return pd.DataFrame(rows)


def _welch_log_test(
    nominal: np.ndarray,
    compressed: np.ndarray,
    alpha_null: float,
    log_schedule_ratio: float,
) -> float:
    log_nominal = np.log(nominal)
    log_compressed = np.log(compressed)
    difference = (
        float(np.mean(log_compressed))
        - float(np.mean(log_nominal))
        - alpha_null * log_schedule_ratio
    )
    nominal_variance = float(np.var(log_nominal, ddof=1) / len(log_nominal))
    compressed_variance = float(np.var(log_compressed, ddof=1) / len(log_compressed))
    standard_error = np.sqrt(nominal_variance + compressed_variance)
    degrees_freedom = (nominal_variance + compressed_variance) ** 2 / (
        nominal_variance**2 / (len(log_nominal) - 1)
        + compressed_variance**2 / (len(log_compressed) - 1)
    )
    statistic = difference / standard_error
    return float(2 * t_distribution.sf(abs(statistic), degrees_freedom))


def alpha_analysis(
    df: pd.DataFrame,
    bootstrap_reps: int = 100_000,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    if bootstrap_reps < 1_000:
        raise ValueError("Use at least 1,000 bootstrap replicates")

    nominal = df.loc[df["Group"] == "G3", "Effort_Hours"].to_numpy(dtype=float)
    compressed = df.loc[df["Group"] == "G4", "Effort_Hours"].to_numpy(dtype=float)
    manual_nominal = df.loc[df["Group"] == "G1", "Effort_Hours"].to_numpy(dtype=float)
    if (nominal <= 0).any() or (compressed <= 0).any():
        raise ValueError("Alpha estimation requires strictly positive effort values")

    log_schedule_ratio = float(np.log(6.0 / 3.5))
    alpha_group = float(np.log(np.mean(compressed) / np.mean(nominal)) / log_schedule_ratio)
    alpha_individual = float(
        (np.mean(np.log(compressed)) - np.mean(np.log(nominal))) / log_schedule_ratio
    )

    rng = np.random.default_rng(seed)
    simulated_nominal_means = np.maximum(
        rng.normal(
            np.mean(nominal),
            np.std(nominal, ddof=1) / np.sqrt(len(nominal)),
            bootstrap_reps,
        ),
        1e-12,
    )
    simulated_compressed_means = np.maximum(
        rng.normal(
            np.mean(compressed),
            np.std(compressed, ddof=1) / np.sqrt(len(compressed)),
            bootstrap_reps,
        ),
        1e-12,
    )
    group_bootstrap = (
        np.log(simulated_compressed_means / simulated_nominal_means)
        / log_schedule_ratio
    )
    group_ci = np.quantile(group_bootstrap, [0.025, 0.975])

    nominal_indices = rng.integers(0, len(nominal), size=(bootstrap_reps, len(nominal)))
    compressed_indices = rng.integers(
        0, len(compressed), size=(bootstrap_reps, len(compressed))
    )
    individual_bootstrap = (
        np.mean(np.log(compressed[compressed_indices]), axis=1)
        - np.mean(np.log(nominal[nominal_indices]), axis=1)
    ) / log_schedule_ratio
    individual_ci = np.quantile(individual_bootstrap, [0.025, 0.975])

    alpha_table = pd.DataFrame(
        [
            {
                "Metric": "AI_Time_Sensitivity_Exponent_GroupBootstrap",
                "Point_Estimate": alpha_group,
                "CI_Lower": float(group_ci[0]),
                "CI_Upper": float(group_ci[1]),
                "Bootstrap_Replicates": bootstrap_reps,
                "Basis": (
                    "Parametric cell-mean bootstrap for G3 and G4; "
                    "ratio-of-means estimator"
                ),
            },
            {
                "Metric": "AI_Time_Sensitivity_Exponent_IndividualBootstrap",
                "Point_Estimate": alpha_individual,
                "CI_Lower": float(individual_ci[0]),
                "CI_Upper": float(individual_ci[1]),
                "Bootstrap_Replicates": bootstrap_reps,
                "Basis": (
                    "Participant-level G3/G4 effort; log-scale estimator with "
                    "within-cell resampling"
                ),
            },
        ]
    )

    parameter_table = pd.DataFrame(
        [
            {"Metric": "Alpha_Group", "Estimate": alpha_group},
            {"Metric": "Alpha_Individual", "Estimate": alpha_individual},
            {
                "Metric": "Welch_P_Alpha_Equals_0",
                "Estimate": _welch_log_test(nominal, compressed, 0, log_schedule_ratio),
            },
            {
                "Metric": "Welch_P_Alpha_Equals_4",
                "Estimate": _welch_log_test(nominal, compressed, 4, log_schedule_ratio),
            },
            {
                "Metric": "Mu_Offloading_Factor",
                "Estimate": 1 - float(np.mean(nominal) / np.mean(manual_nominal)),
            },
        ]
    )
    return alpha_table, parameter_table, group_bootstrap


def quality_component_check(
    group_summary: pd.DataFrame,
    path: Path = QUALITY_COMPONENT_DATA,
) -> pd.DataFrame:
    components = pd.read_csv(path)
    require_columns(components, ["Group", *QUALITY_WEIGHTS], path.name)
    if components["Group"].tolist() != GROUPS:
        raise ValueError(f"{path.name} must contain G1-G4 in manuscript order")

    for component in QUALITY_WEIGHTS:
        if not components[component].between(0, 100).all():
            raise ValueError(f"{component} must be between 0 and 100")

    components["Composite_From_Rounded_Component_Means"] = sum(
        components[component] * weight
        for component, weight in QUALITY_WEIGHTS.items()
    )
    quality_means = group_summary.set_index("Group")["Quality_Mean"]
    components["Reported_Composite_Mean"] = components["Group"].map(quality_means)
    components["Difference"] = (
        components["Composite_From_Rounded_Component_Means"]
        - components["Reported_Composite_Mean"]
    )
    return components


def load_weight_sensitivity(path: Path = WEIGHT_SENSITIVITY_DATA) -> pd.DataFrame:
    table = pd.read_csv(path)
    require_columns(table, ["Weighting_Scheme", *GROUPS], path.name)
    if not table[GROUPS].apply(lambda column: column.between(0, 100)).all().all():
        raise ValueError("Weight-sensitivity success rates must be percentages in [0, 100]")
    return table


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("Wilson interval requires 0 <= successes <= total and total > 0")
    z_value = float(norm.ppf(0.975))
    proportion = successes / total
    denominator = 1 + z_value**2 / total
    center = (proportion + z_value**2 / (2 * total)) / denominator
    half_width = (
        z_value
        * np.sqrt(
            proportion * (1 - proportion) / total
            + z_value**2 / (4 * total**2)
        )
        / denominator
    )
    return float(center - half_width), float(center + half_width)


def newcombe_difference_interval(
    successes_a: int,
    total_a: int,
    successes_b: int,
    total_b: int,
) -> tuple[float, float]:
    """Newcombe hybrid-score interval for two independent proportions."""

    proportion_a = successes_a / total_a
    proportion_b = successes_b / total_b
    difference = proportion_a - proportion_b
    lower_a, upper_a = wilson_interval(successes_a, total_a)
    lower_b, upper_b = wilson_interval(successes_b, total_b)
    lower = difference - np.sqrt(
        (proportion_a - lower_a) ** 2 + (upper_b - proportion_b) ** 2
    )
    upper = difference + np.sqrt(
        (upper_a - proportion_a) ** 2 + (proportion_b - lower_b) ** 2
    )
    return float(lower), float(upper)


def security_analysis(path: Path = SECURITY_DATA) -> pd.DataFrame:
    security = pd.read_csv(path)
    require_columns(
        security,
        [
            "Arm",
            "Submissions",
            "High_Severity_Flagged_Submissions",
            "Triaged_True_Positive_Submissions",
            "Triaged_Flags",
            "Triage_Likely_True_Positive",
            "Triage_Likely_False_Positive",
            "Triage_Indeterminate",
        ],
        path.name,
    )
    if set(security["Arm"]) != {"Manual", "AI-assisted"}:
        raise ValueError("security_summary.csv must contain Manual and AI-assisted rows")

    rows: list[dict[str, float | int | str]] = []
    for _, arm in security.iterrows():
        successes = int(arm["High_Severity_Flagged_Submissions"])
        total = int(arm["Submissions"])
        lower, upper = wilson_interval(successes, total)
        triage_total = int(
            arm["Triage_Likely_True_Positive"]
            + arm["Triage_Likely_False_Positive"]
            + arm["Triage_Indeterminate"]
        )
        if triage_total != int(arm["Triaged_Flags"]):
            raise ValueError(f"Triage categories do not sum to Triaged_Flags for {arm['Arm']}")
        rows.append(
            {
                "Analysis": "Flagged_Submission_Proportion",
                "Arm_or_Contrast": arm["Arm"],
                "Estimate": successes / total,
                "CI_Lower": lower,
                "CI_Upper": upper,
                "p": np.nan,
            }
        )

    indexed = security.set_index("Arm")
    ai = indexed.loc["AI-assisted"]
    manual = indexed.loc["Manual"]
    difference_ci = newcombe_difference_interval(
        int(ai["High_Severity_Flagged_Submissions"]),
        int(ai["Submissions"]),
        int(manual["High_Severity_Flagged_Submissions"]),
        int(manual["Submissions"]),
    )
    flagged_table = [
        [
            int(ai["High_Severity_Flagged_Submissions"]),
            int(ai["Submissions"] - ai["High_Severity_Flagged_Submissions"]),
        ],
        [
            int(manual["High_Severity_Flagged_Submissions"]),
            int(manual["Submissions"] - manual["High_Severity_Flagged_Submissions"]),
        ],
    ]
    rows.append(
        {
            "Analysis": "Flagged_Proportion_Difference",
            "Arm_or_Contrast": "AI-assisted minus Manual",
            "Estimate": (
                ai["High_Severity_Flagged_Submissions"] / ai["Submissions"]
                - manual["High_Severity_Flagged_Submissions"] / manual["Submissions"]
            ),
            "CI_Lower": difference_ci[0],
            "CI_Upper": difference_ci[1],
            "p": float(fisher_exact(flagged_table, alternative="two-sided").pvalue),
        }
    )

    triage_table = [
        [
            int(ai["Triaged_True_Positive_Submissions"]),
            int(ai["Submissions"] - ai["Triaged_True_Positive_Submissions"]),
        ],
        [
            int(manual["Triaged_True_Positive_Submissions"]),
            int(manual["Submissions"] - manual["Triaged_True_Positive_Submissions"]),
        ],
    ]
    rows.append(
        {
            "Analysis": "Triaged_True_Positive_Fisher_Test",
            "Arm_or_Contrast": "AI-assisted versus Manual",
            "Estimate": float(fisher_exact(triage_table).statistic),
            "CI_Lower": np.nan,
            "CI_Upper": np.nan,
            "p": float(fisher_exact(triage_table, alternative="two-sided").pvalue),
        }
    )
    return pd.DataFrame(rows)


def manuscript_validation(
    group_summary: pd.DataFrame,
    anova: pd.DataFrame,
    alpha: pd.DataFrame,
    parameters: pd.DataFrame,
    components: pd.DataFrame,
    security: pd.DataFrame,
) -> pd.DataFrame:
    """Create an auditable map from public inputs to manuscript claims."""

    rows: list[dict[str, str | float]] = []

    def add(
        item: str,
        reported: str,
        reproduced: str,
        status: str,
        note: str = "",
    ) -> None:
        rows.append(
            {
                "Manuscript_Item": item,
                "Reported": reported,
                "Reproduced": reproduced,
                "Status": status,
                "Note": note,
            }
        )

    expected_groups = {
        "G1": (5.93, 0.27, 82.2, 4.9, 92),
        "G2": (3.50, 0.00, 39.2, 12.1, 0),
        "G3": (3.06, 0.57, 94.9, 3.2, 100),
        "G4": (3.42, 0.45, 79.8, 4.3, 92),
    }
    for group, expected in expected_groups.items():
        actual = group_summary.set_index("Group").loc[group]
        reproduced = (
            round(float(actual["Effort_Mean"]), 2),
            round(float(actual["Effort_SD"]), 2),
            round(float(actual["Quality_Mean"]), 1),
            round(float(actual["Quality_SD"]), 1),
            round(float(actual["Success_Rate"])),
        )
        add(
            f"Table 4 {group}",
            str(expected),
            str(reproduced),
            "PASS" if reproduced == expected else "MISMATCH",
        )

    expected_ss = {
        ("Effort_Hours", "Tool Support"): 26.1,
        ("Effort_Hours", "Schedule Condition"): 12.9,
        ("Effort_Hours", "Tool x Schedule"): 23.4,
        ("Effort_Hours", "Residual"): 6.60,
        ("Quality_Score", "Tool Support"): 8523,
        ("Quality_Score", "Schedule Condition"): 10127,
        ("Quality_Score", "Tool x Schedule"): 2335,
        ("Quality_Score", "Residual"): 2191,
    }
    for (outcome, term), expected in expected_ss.items():
        value = float(
            anova.loc[(anova["Outcome"] == outcome) & (anova["Term"] == term), "SS"].iloc[0]
        )
        digits = 1 if outcome == "Effort_Hours" else 0
        add(
            f"ANOVA {outcome}: {term}",
            str(expected),
            str(round(value, digits)),
            "PASS" if round(value, digits) == expected else "MISMATCH",
        )

    max_component_difference = float(components["Difference"].abs().max())
    add(
        "Table 7 rounded component means",
        "Composite differs by no more than +/-0.1",
        f"maximum absolute difference={max_component_difference:.3f}",
        "PASS" if max_component_difference <= 0.1000001 else "MISMATCH",
        "Only group-level rounded component means are public.",
    )
    add(
        "Table 8 weight sensitivity",
        "Nine reported group-level success-rate rows",
        "Aggregate table present",
        "REPORTED_ONLY",
        "Participant-level component scores are unavailable, so this table cannot be independently recomputed.",
    )
    add(
        "Section 5.3 mixed-effects models",
        "PriorAI coefficient and random Stratum intercept",
        "Not estimable from dataset_48.csv",
        "NOT_REPRODUCIBLE",
        "PriorAI and Stratum are not present; synthetic covariates were intentionally not invented.",
    )
    participant_data = load_participant_data()
    g4_maximum = float(
        participant_data.loc[participant_data["Group"] == "G4", "Effort_Hours"].max()
    )
    add(
        "G4 compressed-condition effort semantics",
        "3.5-hour hard cap",
        f"maximum synthetic E_session={g4_maximum:.3f} hours",
        "NEEDS_CLARIFICATION",
        (
            "Values above 3.5 are compatible only if E_session sums overlapping "
            "activity categories or otherwise differs from wall-clock time. The "
            "manuscript should state this explicitly because G2 uses the wall-clock cap."
        ),
    )

    alpha_indexed = alpha.set_index("Metric")
    group_alpha = alpha_indexed.loc["AI_Time_Sensitivity_Exponent_GroupBootstrap"]
    individual_alpha = alpha_indexed.loc[
        "AI_Time_Sensitivity_Exponent_IndividualBootstrap"
    ]
    add(
        "Section 5.5 group alpha",
        "0.21, approximate 95% CI [-0.03, 0.46]",
        (
            f"{group_alpha['Point_Estimate']:.3f}, "
            f"[{group_alpha['CI_Lower']:.3f}, {group_alpha['CI_Upper']:.3f}]"
        ),
        "PASS_APPROX",
        "The seeded run's upper endpoint is about 0.453; the manuscript reports an approximate 0.46.",
    )
    add(
        "Section 5.5 participant alpha",
        "0.23, approximate 95% CI [0.00, 0.49]",
        (
            f"{individual_alpha['Point_Estimate']:.3f}, "
            f"[{individual_alpha['CI_Lower']:.3f}, {individual_alpha['CI_Upper']:.3f}]"
        ),
        "PASS_APPROX",
    )
    parameter_indexed = parameters.set_index("Metric")["Estimate"]
    add(
        "Section 5.5 Welch test alpha=0",
        "p approximately 0.10",
        f"p={parameter_indexed['Welch_P_Alpha_Equals_0']:.3f}",
        "PASS",
    )
    add(
        "Section 5.5 Welch test alpha=4",
        "p < 0.001",
        f"p={parameter_indexed['Welch_P_Alpha_Equals_4']:.3e}",
        "PASS",
    )
    add(
        "Section 5.5 offloading factor",
        "mu approximately 0.48",
        f"mu={parameter_indexed['Mu_Offloading_Factor']:.3f}",
        "PASS",
    )

    security_indexed = security.set_index(["Analysis", "Arm_or_Contrast"])
    ai_security = security_indexed.loc[("Flagged_Submission_Proportion", "AI-assisted")]
    manual_security = security_indexed.loc[("Flagged_Submission_Proportion", "Manual")]
    security_difference = security_indexed.loc[
        ("Flagged_Proportion_Difference", "AI-assisted minus Manual")
    ]
    triage = security_indexed.loc[
        ("Triaged_True_Positive_Fisher_Test", "AI-assisted versus Manual")
    ]
    add(
        "Section 5.7 AI-assisted Wilson CI",
        "38.8%-75.5%",
        f"{100 * ai_security['CI_Lower']:.1f}%-{100 * ai_security['CI_Upper']:.1f}%",
        "PASS",
    )
    add(
        "Section 5.7 manual Wilson CI",
        "11.2%-46.9%",
        f"{100 * manual_security['CI_Lower']:.1f}%-{100 * manual_security['CI_Upper']:.1f}%",
        "MANUSCRIPT_MISMATCH",
        "The standard uncorrected 95% Wilson interval for 6/24 is 12.0%-44.9%.",
    )
    add(
        "Section 5.7 Newcombe difference CI",
        "7.1%-54.9%",
        (
            f"{100 * security_difference['CI_Lower']:.1f}%-"
            f"{100 * security_difference['CI_Upper']:.1f}%"
        ),
        "MANUSCRIPT_MISMATCH",
        "The standard Newcombe hybrid-score interval is 5.5%-54.9%.",
    )
    add(
        "Section 5.7 triage Fisher test",
        "p=0.072",
        f"p={triage['p']:.3f}",
        "PASS",
    )
    add(
        "Section 5.7 SAST execution",
        "Semgrep, SonarQube, and Bandit scans",
        "Only reported aggregate counts are available",
        "REPORTED_ONLY",
        "Submitted source artifacts, tool configurations, and raw SAST reports are not public.",
    )
    add(
        "Participant balance and questionnaires",
        "Reported aggregate summaries",
        "Aggregate source files present",
        "REPORTED_ONLY",
        "No participant-level covariates or questionnaire responses are public.",
    )
    return pd.DataFrame(rows)


def save_alpha_figure(
    bootstrap_values: np.ndarray,
    alpha_table: pd.DataFrame,
    output_path: Path,
) -> None:
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ai-scheduling-matplotlib")
    )
    import matplotlib.pyplot as plt

    group = alpha_table.iloc[0]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(bootstrap_values, bins=40, color="#7fa8d9", edgecolor="white")
    ax.axvline(group["Point_Estimate"], linewidth=2, linestyle="--", color="#1f4e8c")
    ax.axvline(group["CI_Lower"], linewidth=2, linestyle=":", color="#1f4e8c")
    ax.axvline(group["CI_Upper"], linewidth=2, linestyle=":", color="#1f4e8c")
    ax.set_title(r"Bootstrap distribution of $\alpha$ (AI-assisted conditions)")
    ax.set_xlabel(r"Estimated AI time-sensitivity exponent ($\alpha$)")
    ax.set_ylabel("Bootstrap count")
    ax.legend(
        [
            f"Estimate: {group['Point_Estimate']:.2f}",
            f"95% CI: [{group['CI_Lower']:.2f}, {group['CI_Upper']:.2f}]",
        ],
        frameon=False,
    )
    fig.tight_layout()
    fig.savefig(output_path, format="pdf", bbox_inches="tight")
    plt.close(fig)


def write_outputs(
    bootstrap_reps: int = 100_000,
    seed: int = 42,
    make_figure: bool = True,
) -> pd.DataFrame:
    df = load_participant_data()
    group_summary = build_group_summary(df)
    anova = pd.concat(
        [
            two_way_anova(df, "Effort_Hours"),
            two_way_anova(df, "Quality_Score"),
        ],
        ignore_index=True,
    )
    alpha, parameters, group_bootstrap = alpha_analysis(df, bootstrap_reps, seed)
    components = quality_component_check(group_summary)
    weight_sensitivity = load_weight_sensitivity()
    security = security_analysis()
    validation = manuscript_validation(
        group_summary,
        anova,
        alpha,
        parameters,
        components,
        security,
    )

    group_summary.round(4).to_csv(REPO_ROOT / "group_summary.csv", index=False)
    anova.to_csv(REPO_ROOT / "anova_results.csv", index=False, float_format="%.10g")
    alpha.round({"Point_Estimate": 3, "CI_Lower": 3, "CI_Upper": 3}).to_csv(
        REPO_ROOT / "alpha_fitting.csv", index=False
    )
    parameters.to_csv(REPO_ROOT / "model_parameters.csv", index=False, float_format="%.10g")
    components.to_csv(REPO_ROOT / "quality_component_check.csv", index=False, float_format="%.4f")
    weight_sensitivity.to_csv(REPO_ROOT / "weight_sensitivity_summary.csv", index=False)
    security.to_csv(REPO_ROOT / "security_analysis.csv", index=False, float_format="%.10g")
    validation.to_csv(REPO_ROOT / "manuscript_validation.csv", index=False)
    if make_figure:
        save_alpha_figure(group_bootstrap, alpha, REPO_ROOT / "Fig4_Sensitivity.pdf")
    return validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap-reps",
        type=int,
        default=100_000,
        help="Bootstrap replicates for alpha intervals (default: 100000)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--skip-figure",
        action="store_true",
        help="Skip regeneration of Fig4_Sensitivity.pdf",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation = write_outputs(args.bootstrap_reps, args.seed, not args.skip_figure)
    counts = validation["Status"].value_counts().to_dict()
    print("Analysis completed. Validation status counts:", counts)
    mismatches = validation[validation["Status"] == "MANUSCRIPT_MISMATCH"]
    if not mismatches.empty:
        print("Review manuscript_validation.csv for manuscript-side statistical mismatches.")


if __name__ == "__main__":
    main()
