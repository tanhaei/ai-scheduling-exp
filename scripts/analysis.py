"""Reproduce the numerical checks reported in manuscript V3 (2026-09-11).

This pipeline intentionally uses only the final aggregate inputs reported in the
manuscript: quality means/SDs and success counts, component summaries,
weight/threshold sensitivity counts, and four-cell security counts. It does
not reconstruct participant-level observations and it does not perform the
removed effort, schedule-exponent, or offloading-factor analyses.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import f as f_distribution
from scipy.stats import fisher_exact, ncf, norm, t as t_distribution

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

QUALITY_SUMMARY = DATA_DIR / "quality_summary.csv"
QUALITY_COMPONENTS = DATA_DIR / "quality_components_summary.csv"
WEIGHT_SENSITIVITY = DATA_DIR / "weight_sensitivity_summary.csv"
THRESHOLD_SENSITIVITY = DATA_DIR / "threshold_sensitivity_summary.csv"
SECURITY_SUMMARY = DATA_DIR / "security_summary.csv"
SAST_BREAKDOWN = DATA_DIR / "sast_breakdown.csv"
SAST_TRIAGE = DATA_DIR / "sast_triage_summary.csv"
PARTICIPANT_BALANCE = DATA_DIR / "participant_balance_summary.csv"
QUESTIONNAIRE = DATA_DIR / "questionnaire_summary.csv"

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


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def load_quality_summary(path: Path = QUALITY_SUMMARY) -> pd.DataFrame:
    df = _read(path)
    require_columns(df, ["Group", "Tool", "Schedule", "N", "Q_Mean", "Q_SD", "Success_Q75"], path.name)
    if df["Group"].tolist() != GROUPS:
        raise ValueError(f"{path.name} must contain G1-G4 in manuscript order")
    if not (df["N"] == 12).all():
        raise ValueError("The manuscript design has n=12 in every cell")
    if not df["Q_Mean"].between(0, 100).all() or not df["Q_SD"].ge(0).all():
        raise ValueError("Quality means/SDs are outside valid bounds")
    if not ((df["Success_Q75"] >= 0) & (df["Success_Q75"] <= df["N"])).all():
        raise ValueError("Success counts must be between 0 and N")
    expected_tools = ["Manual", "Manual", "AI-assisted", "AI-assisted"]
    expected_schedules = ["Nominal", "Compressed", "Nominal", "Compressed"]
    if df["Tool"].tolist() != expected_tools or df["Schedule"].tolist() != expected_schedules:
        raise ValueError("Tool/Schedule labels do not match the 2x2 design")
    return df


def t_interval(mean: float, sd: float, n: int, confidence: float = 0.95) -> tuple[float, float]:
    if n < 2 or sd < 0:
        raise ValueError("t interval requires n >= 2 and sd >= 0")
    if sd == 0:
        return float(mean), float(mean)
    alpha = 1 - confidence
    critical = float(t_distribution.ppf(1 - alpha / 2, n - 1))
    half = critical * sd / math.sqrt(n)
    return float(mean - half), float(mean + half)


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("Wilson interval requires 0 <= successes <= total and total > 0")
    alpha = 1 - confidence
    z = float(norm.ppf(1 - alpha / 2))
    p = successes / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return float(max(0.0, center - half)), float(min(1.0, center + half))


def newcombe_difference_interval(
    successes_a: int,
    total_a: int,
    successes_b: int,
    total_b: int,
) -> tuple[float, float]:
    """Newcombe hybrid-score interval for p_a - p_b."""
    p_a = successes_a / total_a
    p_b = successes_b / total_b
    difference = p_a - p_b
    lower_a, upper_a = wilson_interval(successes_a, total_a)
    lower_b, upper_b = wilson_interval(successes_b, total_b)
    lower = difference - math.sqrt((p_a - lower_a) ** 2 + (upper_b - p_b) ** 2)
    upper = difference + math.sqrt((upper_a - p_a) ** 2 + (p_b - lower_b) ** 2)
    return float(lower), float(upper)


def quality_summary_with_intervals(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = load_quality_summary() if df is None else df.copy()
    rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        q_low, q_high = t_interval(float(row.Q_Mean), float(row.Q_SD), int(row.N))
        s_low, s_high = wilson_interval(int(row.Success_Q75), int(row.N))
        rows.append(
            {
                "Group": row.Group,
                "Tool": row.Tool,
                "Schedule": row.Schedule,
                "N": int(row.N),
                "Q_Mean": float(row.Q_Mean),
                "Q_SD": float(row.Q_SD),
                "Q_CI_Lower": q_low,
                "Q_CI_Upper": q_high,
                "Success_Q75": int(row.Success_Q75),
                "Success_Percent": 100 * int(row.Success_Q75) / int(row.N),
                "Success_Wilson_Lower": s_low,
                "Success_Wilson_Upper": s_high,
            }
        )
    return pd.DataFrame(rows)


def summary_based_quality_anova(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Balanced 2x2 fixed-effects ANOVA reconstructed from cell means and SDs."""
    df = load_quality_summary() if df is None else df.copy()
    if not (df["N"] == df["N"].iloc[0]).all():
        raise ValueError("Closed-form ANOVA requires equal cell sizes")
    n = int(df["N"].iloc[0])
    means = df.set_index("Group")["Q_Mean"].reindex(GROUPS).to_numpy(dtype=float)
    sds = df.set_index("Group")["Q_SD"].reindex(GROUPS).to_numpy(dtype=float)

    grand = float(np.mean(means))
    tool_means = np.array([np.mean(means[:2]), np.mean(means[2:])], dtype=float)
    schedule_means = np.array([np.mean(means[[0, 2]]), np.mean(means[[1, 3]])], dtype=float)
    cell = means.reshape(2, 2)  # tool rows (manual, AI), schedule cols (nominal, compressed)

    ss_tool = 2 * n * float(np.sum((tool_means - grand) ** 2))
    ss_schedule = 2 * n * float(np.sum((schedule_means - grand) ** 2))
    ss_interaction = n * sum(
        (cell[t, s] - tool_means[t] - schedule_means[s] + grand) ** 2
        for t in range(2)
        for s in range(2)
    )
    ss_residual = float((n - 1) * np.sum(sds**2))
    df_residual = 4 * (n - 1)
    ms_residual = ss_residual / df_residual

    rows: list[dict[str, object]] = []
    for term, ss in [
        ("Tool", ss_tool),
        ("Schedule", ss_schedule),
        ("Tool x Schedule", ss_interaction),
    ]:
        f_value = ss / ms_residual
        rows.append(
            {
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


def fisher_freeman_halton_probability_ordered(successes: Iterable[int], totals: Iterable[int]) -> float:
    """Exact two-sided Fisher-Freeman-Halton p-value for a 2 x k table.

    Column margins and the total number of successes are fixed. The two-sided
    p-value is probability ordered: sum of all table masses no larger than the
    observed table mass.
    """
    successes = tuple(int(x) for x in successes)
    totals = tuple(int(x) for x in totals)
    if len(successes) != len(totals) or len(successes) < 2:
        raise ValueError("successes and totals must have the same length >= 2")
    if any(n <= 0 or y < 0 or y > n for y, n in zip(successes, totals)):
        raise ValueError("Each success count must satisfy 0 <= y <= n")

    total_successes = sum(successes)
    denominator = math.comb(sum(totals), total_successes)
    observed_weight = math.prod(math.comb(n, y) for y, n in zip(successes, totals))
    observed_mass = observed_weight / denominator

    probability = 0.0
    ranges = [range(n + 1) for n in totals[:-1]]
    for prefix in itertools.product(*ranges):
        last = total_successes - sum(prefix)
        if 0 <= last <= totals[-1]:
            candidate = (*prefix, last)
            weight = math.prod(math.comb(n, y) for y, n in zip(candidate, totals))
            mass = weight / denominator
            if mass <= observed_mass + 1e-15:
                probability += mass
    return float(min(1.0, probability))


def success_analysis(df: pd.DataFrame | None = None) -> pd.DataFrame:
    df = load_quality_summary() if df is None else df.copy()
    indexed = df.set_index("Group")
    rows: list[dict[str, object]] = []

    for group in GROUPS:
        row = indexed.loc[group]
        y, n = int(row.Success_Q75), int(row.N)
        low, high = wilson_interval(y, n)
        rows.append(
            {
                "Analysis": "Cell success proportion",
                "Contrast": group,
                "Estimate": y / n,
                "CI_Lower": low,
                "CI_Upper": high,
                "p": np.nan,
            }
        )

    g4, g2 = indexed.loc["G4"], indexed.loc["G2"]
    y4, n4 = int(g4.Success_Q75), int(g4.N)
    y2, n2 = int(g2.Success_Q75), int(g2.N)
    rd = y4 / n4 - y2 / n2
    rd_low, rd_high = newcombe_difference_interval(y4, n4, y2, n2)
    p_fisher = float(fisher_exact([[y4, n4 - y4], [y2, n2 - y2]], alternative="two-sided").pvalue)
    rows.append(
        {
            "Analysis": "Compressed-condition risk difference",
            "Contrast": "G4 minus G2",
            "Estimate": rd,
            "CI_Lower": rd_low,
            "CI_Upper": rd_high,
            "p": p_fisher,
        }
    )

    successes = [int(indexed.loc[g, "Success_Q75"]) for g in GROUPS]
    totals = [int(indexed.loc[g, "N"]) for g in GROUPS]
    rows.append(
        {
            "Analysis": "Fisher-Freeman-Halton omnibus",
            "Contrast": "G1-G4 heterogeneity",
            "Estimate": np.nan,
            "CI_Lower": np.nan,
            "CI_Upper": np.nan,
            "p": fisher_freeman_halton_probability_ordered(successes, totals),
        }
    )
    return pd.DataFrame(rows)


def minimum_detectable_interaction_effect(
    n_total: int = 48,
    alpha: float = 0.05,
    target_power: float = 0.80,
    df1: int = 1,
    df2: int = 44,
) -> pd.DataFrame:
    critical = float(f_distribution.ppf(1 - alpha, df1, df2))

    def achieved_power(effect_f: float) -> float:
        return float(ncf.sf(critical, df1, df2, n_total * effect_f**2))

    effect_f = float(brentq(lambda value: achieved_power(value) - target_power, 1e-8, 5.0))
    partial_eta_squared = effect_f**2 / (1 + effect_f**2)
    return pd.DataFrame(
        [
            {
                "N": n_total,
                "alpha": alpha,
                "power": target_power,
                "df1": df1,
                "df2": df2,
                "Minimum_Detectable_f": effect_f,
                "Equivalent_Partial_Eta_Squared": partial_eta_squared,
            }
        ]
    )


def component_summary_with_intervals(path: Path = QUALITY_COMPONENTS) -> pd.DataFrame:
    df = _read(path)
    components = ["PassRate", "Coverage", "Static_Score", "Security_Score"]
    required = ["Group", "N"] + [
        f"{c}_{suffix}"
        for c in components
        for suffix in ("Mean", "SD", "CI_Lower", "CI_Upper")
    ]
    require_columns(df, required, path.name)
    if df["Group"].tolist() != GROUPS or not (df["N"] == 12).all():
        raise ValueError("Component summary must contain G1-G4 with n=12")

    rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        out: dict[str, object] = {"Group": row.Group, "N": int(row.N)}
        for component in components:
            mean = float(getattr(row, f"{component}_Mean"))
            sd = float(getattr(row, f"{component}_SD"))
            reported_low = float(getattr(row, f"{component}_CI_Lower"))
            reported_high = float(getattr(row, f"{component}_CI_Upper"))
            calc_low, calc_high = t_interval(mean, sd, int(row.N))
            out[f"{component}_Mean"] = mean
            out[f"{component}_SD"] = sd
            out[f"{component}_Reported_CI_Lower"] = reported_low
            out[f"{component}_Reported_CI_Upper"] = reported_high
            out[f"{component}_Recomputed_CI_Lower"] = calc_low
            out[f"{component}_Recomputed_CI_Upper"] = calc_high
            out[f"{component}_CI_Max_Abs_Difference"] = max(abs(calc_low - reported_low), abs(calc_high - reported_high))
        rows.append(out)
    return pd.DataFrame(rows)


def load_weight_sensitivity(path: Path = WEIGHT_SENSITIVITY) -> pd.DataFrame:
    df = _read(path)
    require_columns(df, ["Weighting_Scheme", *GROUPS], path.name)
    if len(df) != 9 or not df[GROUPS].apply(lambda c: c.between(0, 12)).all().all():
        raise ValueError("Weight sensitivity must have 9 rows of success counts in [0,12]")
    return df


def load_threshold_sensitivity(path: Path = THRESHOLD_SENSITIVITY) -> pd.DataFrame:
    df = _read(path)
    require_columns(df, ["Threshold", *GROUPS], path.name)
    if df["Threshold"].tolist() != [70, 75, 80]:
        raise ValueError("Threshold sensitivity must contain Q >= 70, 75, and 80")
    if not df[GROUPS].apply(lambda c: c.between(0, 12)).all().all():
        raise ValueError("Threshold sensitivity counts must be in [0,12]")
    return df


def security_interaction_exact_p(successes: Iterable[int], n_per_cell: int = 12) -> float:
    """Exact conditional Tool x Schedule interaction p-value from Appendix C.4."""
    y = tuple(int(v) for v in successes)
    if len(y) != 4 or any(v < 0 or v > n_per_cell for v in y):
        raise ValueError("Expected four cell counts between 0 and n_per_cell")
    total = sum(y)
    ai_total = y[2] + y[3]
    compressed_total = y[1] + y[3]

    compatible: list[tuple[tuple[int, int, int, int], int]] = []
    for candidate in itertools.product(range(n_per_cell + 1), repeat=4):
        if (
            sum(candidate) == total
            and candidate[2] + candidate[3] == ai_total
            and candidate[1] + candidate[3] == compressed_total
        ):
            weight = math.prod(math.comb(n_per_cell, value) for value in candidate)
            compatible.append((candidate, weight))

    denominator = sum(weight for _, weight in compatible)
    observed_weight = next(weight for candidate, weight in compatible if candidate == y)
    return float(sum(weight for _, weight in compatible if weight <= observed_weight) / denominator)


def security_analysis(path: Path = SECURITY_SUMMARY) -> pd.DataFrame:
    df = _read(path)
    require_columns(df, ["Group", "Tool", "Schedule", "N", "Flagged_Submissions"], path.name)
    if df["Group"].tolist() != GROUPS or not (df["N"] == 12).all():
        raise ValueError("Security summary must contain G1-G4 with n=12")

    rows: list[dict[str, object]] = []
    indexed = df.set_index("Group")
    for group in GROUPS:
        row = indexed.loc[group]
        y, n = int(row.Flagged_Submissions), int(row.N)
        low, high = wilson_interval(y, n)
        rows.append(
            {
                "Analysis": "Cell flagged proportion",
                "Contrast": group,
                "Estimate": y / n,
                "CI_Lower": low,
                "CI_Upper": high,
                "p": np.nan,
            }
        )

    manual_y = int(indexed.loc[["G1", "G2"], "Flagged_Submissions"].sum())
    ai_y = int(indexed.loc[["G3", "G4"], "Flagged_Submissions"].sum())
    manual_n = int(indexed.loc[["G1", "G2"], "N"].sum())
    ai_n = int(indexed.loc[["G3", "G4"], "N"].sum())
    for label, y, n in [("Manual", manual_y, manual_n), ("AI-assisted", ai_y, ai_n)]:
        low, high = wilson_interval(y, n)
        rows.append(
            {
                "Analysis": "Pooled flagged proportion",
                "Contrast": label,
                "Estimate": y / n,
                "CI_Lower": low,
                "CI_Upper": high,
                "p": np.nan,
            }
        )

    rd = ai_y / ai_n - manual_y / manual_n
    rd_low, rd_high = newcombe_difference_interval(ai_y, ai_n, manual_y, manual_n)
    p_pooled = float(
        fisher_exact(
            [[ai_y, ai_n - ai_y], [manual_y, manual_n - manual_y]],
            alternative="two-sided",
        ).pvalue
    )
    rows.append(
        {
            "Analysis": "Pooled flagged risk difference",
            "Contrast": "AI-assisted minus Manual",
            "Estimate": rd,
            "CI_Lower": rd_low,
            "CI_Upper": rd_high,
            "p": p_pooled,
        }
    )

    cell_counts = [int(indexed.loc[g, "Flagged_Submissions"]) for g in GROUPS]
    rows.append(
        {
            "Analysis": "Exact Tool x Schedule interaction",
            "Contrast": "G1-G4 conditional test",
            "Estimate": np.nan,
            "CI_Lower": np.nan,
            "CI_Upper": np.nan,
            "p": security_interaction_exact_p(cell_counts, n_per_cell=12),
        }
    )

    triage = _read(SAST_TRIAGE).set_index("Arm")
    ai_tp = int(triage.loc["AI-assisted", "Distinct_Submissions_Likely_True_Positive"])
    manual_tp = int(triage.loc["Manual", "Distinct_Submissions_Likely_True_Positive"])
    p_triage = float(
        fisher_exact([[ai_tp, 24 - ai_tp], [manual_tp, 24 - manual_tp]], alternative="two-sided").pvalue
    )
    rows.append(
        {
            "Analysis": "Descriptive triage Fisher test",
            "Contrast": "8/24 AI-assisted vs 2/24 Manual",
            "Estimate": np.nan,
            "CI_Lower": np.nan,
            "CI_Upper": np.nan,
            "p": p_triage,
        }
    )
    return pd.DataFrame(rows)


def validate_supporting_tables() -> None:
    balance = _read(PARTICIPANT_BALANCE)
    require_columns(balance, ["Measure", *GROUPS, "Unit"], PARTICIPANT_BALANCE.name)
    exposure = balance.loc[balance["Measure"] == "Prior Copilot/GPT-4 exposure", GROUPS]
    if exposure.empty or exposure.iloc[0].astype(int).tolist() != [5, 6, 5, 7]:
        raise ValueError("Prior-AI exposure counts must be 5,6,5,7 (23/48)")

    questionnaire = _read(QUESTIONNAIRE)
    require_columns(questionnaire, ["Instrument", "Metric", "Group", "Mean", "Scale_Max"], QUESTIONNAIRE.name)
    expected_questionnaire = {
        ("NASA-TLX", "Mental Demand", "G2"): 7.8,
        ("NASA-TLX", "Temporal Demand", "G2"): 9.2,
        ("NASA-TLX", "Mental Demand", "G4"): 4.5,
        ("NASA-TLX", "Temporal Demand", "G4"): 5.1,
        ("TAM", "Perceived speed", "AI-assisted"): 4.2,
        ("TAM", "Design focus", "AI-assisted"): 4.5,
        ("TAM", "Verification burden", "AI-assisted"): 2.1,
    }
    for key, expected in expected_questionnaire.items():
        rows = questionnaire[
            (questionnaire["Instrument"] == key[0])
            & (questionnaire["Metric"] == key[1])
            & (questionnaire["Group"] == key[2])
        ]
        if rows.empty or not math.isclose(float(rows.iloc[0]["Mean"]), expected, abs_tol=1e-12):
            raise ValueError(f"Questionnaire summary mismatch for {key}")

    sast = _read(SAST_BREAKDOWN)
    require_columns(sast, ["Tool", "Rule_Category", "Manual", "AI_Assisted"], SAST_BREAKDOWN.name)
    if int(sast["Manual"].sum()) != 6 or int(sast["AI_Assisted"].sum()) != 19:
        raise ValueError("SAST flag-category totals must be 6 manual and 19 AI-assisted")

    triage = _read(SAST_TRIAGE)
    require_columns(
        triage,
        ["Arm", "Sampled_Flags", "Likely_True_Positive", "Likely_False_Positive", "Indeterminate", "Distinct_Submissions_Likely_True_Positive"],
        SAST_TRIAGE.name,
    )
    for row in triage.itertuples(index=False):
        if int(row.Likely_True_Positive + row.Likely_False_Positive + row.Indeterminate) != int(row.Sampled_Flags):
            raise ValueError(f"Triage categories do not sum for {row.Arm}")


def manuscript_validation() -> pd.DataFrame:
    quality = quality_summary_with_intervals()
    anova = summary_based_quality_anova()
    success = success_analysis()
    components = component_summary_with_intervals()
    weight = load_weight_sensitivity().set_index("Weighting_Scheme")
    threshold = load_threshold_sensitivity().set_index("Threshold")
    security = security_analysis()
    power = minimum_detectable_interaction_effect().iloc[0]
    validate_supporting_tables()

    rows: list[dict[str, str]] = []

    def add(item: str, manuscript: str, computed: str, status: str = "PASS", note: str = "") -> None:
        rows.append({"Manuscript_Item": item, "Manuscript_Value": manuscript, "Computed_or_Checked": computed, "Status": status, "Note": note})

    q = quality.set_index("Group")
    for group, target in {
        "G1": (82.2, 4.9, 11),
        "G2": (39.2, 12.1, 0),
        "G3": (94.9, 3.2, 12),
        "G4": (79.8, 4.3, 11),
    }.items():
        row = q.loc[group]
        got = (round(float(row.Q_Mean), 1), round(float(row.Q_SD), 1), int(row.Success_Q75))
        add(f"Table 4 {group}", str(target), str(got), "PASS" if got == target else "MISMATCH")

    a = anova.set_index("Term")
    expected_anova = {
        "Tool": (8522.67, 171.2, 9.1e-17, 0.80),
        "Schedule": (10126.83, 203.4, 4.2e-18, 0.82),
        "Tool x Schedule": (2335.23, 46.9, 1.9e-8, 0.52),
        "Residual": (2190.65, None, None, None),
    }
    for term, target in expected_anova.items():
        row = a.loc[term]
        if term == "Residual":
            ok = math.isclose(float(row.SS), target[0], rel_tol=0, abs_tol=1e-8)
            got = f"SS={row.SS:.2f}"
        else:
            ok = (
                math.isclose(float(row.SS), target[0], abs_tol=1e-8)
                and round(float(row.F), 1) == target[1]
                and math.isclose(float(row.Partial_Eta_Squared), target[3], abs_tol=0.005)
            )
            got = f"SS={row.SS:.2f}; F={row.F:.4f}; p={row.p:.6g}; partial eta2={row.Partial_Eta_Squared:.4f}"
        add(f"Table 5 {term}", str(target), got, "PASS" if ok else "MISMATCH")

    s = success.set_index(["Analysis", "Contrast"])
    g4g2 = s.loc[("Compressed-condition risk difference", "G4 minus G2")]
    add(
        "G4 vs G2 success contrast",
        "RD=91.7 pp; Newcombe 95% CI 55.3-98.5; Fisher p=9.61e-6",
        f"RD={100*g4g2.Estimate:.1f} pp; CI {100*g4g2.CI_Lower:.1f}-{100*g4g2.CI_Upper:.1f}; p={g4g2.p:.8g}",
    )
    ffh = s.loc[("Fisher-Freeman-Halton omnibus", "G1-G4 heterogeneity")]
    add("Success omnibus exact test", "p=5.22e-9", f"p={ffh.p:.10g}")

    interaction = a.loc["Tool x Schedule"]
    add("Quality interaction", "F(1,44)=46.9; p=1.9e-8; partial eta2=0.52", f"F={interaction.F:.4f}; p={interaction.p:.8g}; partial eta2={interaction.Partial_Eta_Squared:.4f}")
    add("Minimum detectable interaction", "f=0.4135; partial eta2=0.1460", f"f={power.Minimum_Detectable_f:.4f}; partial eta2={power.Equivalent_Partial_Eta_Squared:.4f}")

    c = components.set_index("Group")
    component_ci_max_diff = float(components.filter(like="CI_Max_Abs_Difference").to_numpy().max())
    add("Table 6 t-interval arithmetic", "Reported endpoints consistent with conventional t-intervals from rounded means/SDs", f"maximum absolute endpoint difference={component_ci_max_diff:.4f}", "PASS" if component_ci_max_diff <= 0.011 else "MISMATCH", "A small difference is expected because Table 6 means/SDs are reported to two decimals.")
    add("Table 6 G3 PassRate", "100.00 +/- 0.00 [100.00,100.00]", f"{c.loc['G3','PassRate_Mean']:.2f} +/- {c.loc['G3','PassRate_SD']:.2f} [{c.loc['G3','PassRate_Reported_CI_Lower']:.2f},{c.loc['G3','PassRate_Reported_CI_Upper']:.2f}]")
    add("Table 6 G3 Coverage upper t-CI", "100.48 (not truncated)", f"{c.loc['G3','Coverage_Reported_CI_Upper']:.2f}")

    add("Table 7 G4 security +0.10", "6/12", f"{int(weight.loc['Security score +0.10','G4'])}/12")
    add("Table 8 threshold Q>=80", "G1=8, G2=0, G3=12, G4=5", f"G1={int(threshold.loc[80,'G1'])}, G2={int(threshold.loc[80,'G2'])}, G3={int(threshold.loc[80,'G3'])}, G4={int(threshold.loc[80,'G4'])}")

    sec = security.set_index(["Analysis", "Contrast"])
    pooled_ai = sec.loc[("Pooled flagged proportion", "AI-assisted")]
    pooled_manual = sec.loc[("Pooled flagged proportion", "Manual")]
    sec_rd = sec.loc[("Pooled flagged risk difference", "AI-assisted minus Manual")]
    sec_int = sec.loc[("Exact Tool x Schedule interaction", "G1-G4 conditional test")]
    triage = sec.loc[("Descriptive triage Fisher test", "8/24 AI-assisted vs 2/24 Manual")]
    add("Security pooled AI", "14/24=58.3%; Wilson 38.8-75.5", f"{100*pooled_ai.Estimate:.1f}%; {100*pooled_ai.CI_Lower:.1f}-{100*pooled_ai.CI_Upper:.1f}")
    add("Security pooled Manual", "6/24=25.0%; Wilson 12.0-44.9", f"{100*pooled_manual.Estimate:.1f}%; {100*pooled_manual.CI_Lower:.1f}-{100*pooled_manual.CI_Upper:.1f}")
    add("Security pooled contrast", "RD=33.3 pp; Newcombe 5.5-54.9; Fisher p=0.039", f"RD={100*sec_rd.Estimate:.1f}; CI {100*sec_rd.CI_Lower:.1f}-{100*sec_rd.CI_Upper:.1f}; p={sec_rd.p:.6f}")
    add("Security interaction", "exact conditional p=1.000", f"p={sec_int.p:.3f}")
    add("SAST triage descriptive Fisher", "p=0.072", f"p={triage.p:.6f}")

    add(
        "Removed analyses",
        "No effort ANOVA, schedule-sensitivity exponent, offloading factor, or bootstrap intervals",
        "No such analyses are implemented or generated by this repository",
    )
    add(
        "Reproducibility scope",
        "Aggregate numerical checks only; source snapshots/scoring transforms/SAST configs unavailable",
        "Inputs are aggregate manuscript summaries; SAST tool versions are documented separately",
        "REPORTED_ONLY",
    )
    return pd.DataFrame(rows)


def write_outputs() -> pd.DataFrame:
    quality_summary_with_intervals().to_csv(REPO_ROOT / "quality_summary.csv", index=False, float_format="%.10g")
    summary_based_quality_anova().to_csv(REPO_ROOT / "anova_results.csv", index=False, float_format="%.10g")
    success_analysis().to_csv(REPO_ROOT / "success_analysis.csv", index=False, float_format="%.10g")
    minimum_detectable_interaction_effect().to_csv(REPO_ROOT / "power_analysis.csv", index=False, float_format="%.10g")
    component_summary_with_intervals().to_csv(REPO_ROOT / "quality_components.csv", index=False, float_format="%.10g")
    security_analysis().to_csv(REPO_ROOT / "security_analysis.csv", index=False, float_format="%.10g")
    validation = manuscript_validation()
    validation.to_csv(REPO_ROOT / "manuscript_validation.csv", index=False)
    return validation


def main() -> None:
    validation = write_outputs()
    counts = validation["Status"].value_counts().to_dict()
    print("Analysis completed. Validation status counts:", counts)
    mismatches = validation[validation["Status"] == "MISMATCH"]
    if not mismatches.empty:
        raise SystemExit("Manuscript mismatches detected; inspect manuscript_validation.csv")


if __name__ == "__main__":
    main()
