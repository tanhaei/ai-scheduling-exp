from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analysis  # noqa: E402


class ReproducibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = analysis.load_participant_data()
        cls.group_summary = analysis.build_group_summary(cls.data).set_index("Group")

    def test_design_and_success_rule(self) -> None:
        self.assertEqual(len(self.data), 48)
        self.assertEqual(
            self.data["Group"].value_counts().reindex(analysis.GROUPS).tolist(),
            [12, 12, 12, 12],
        )
        expected = (self.data["Quality_Score"] >= 75).astype(int)
        np.testing.assert_array_equal(self.data["Success"].astype(int), expected)

    def test_table_4_group_summaries(self) -> None:
        expected = {
            "G1": (5.93, 0.27, 82.2, 4.9, 92),
            "G2": (3.50, 0.00, 39.2, 12.1, 0),
            "G3": (3.06, 0.57, 94.9, 3.2, 100),
            "G4": (3.42, 0.45, 79.8, 4.3, 92),
        }
        for group, target in expected.items():
            row = self.group_summary.loc[group]
            actual = (
                round(row["Effort_Mean"], 2),
                round(row["Effort_SD"], 2),
                round(row["Quality_Mean"], 1),
                round(row["Quality_SD"], 1),
                round(row["Success_Rate"]),
            )
            self.assertEqual(actual, target)

    def test_tables_5_and_6_anova(self) -> None:
        effort = analysis.two_way_anova(self.data, "Effort_Hours").set_index("Term")
        quality = analysis.two_way_anova(self.data, "Quality_Score").set_index("Term")

        effort_expected = {
            "Tool Support": 26.1,
            "Schedule Condition": 12.9,
            "Tool x Schedule": 23.4,
            "Residual": 6.60,
        }
        quality_expected = {
            "Tool Support": 8523,
            "Schedule Condition": 10127,
            "Tool x Schedule": 2335,
            "Residual": 2191,
        }
        for term, target in effort_expected.items():
            self.assertEqual(round(effort.loc[term, "SS"], 1), target)
        for term, target in quality_expected.items():
            self.assertEqual(round(quality.loc[term, "SS"]), target)

        self.assertAlmostEqual(effort.loc["Tool Support", "Partial_Eta_Squared"], 0.80, 2)
        self.assertAlmostEqual(quality.loc["Tool x Schedule", "Partial_Eta_Squared"], 0.52, 2)

    def test_alpha_and_offloading_estimates(self) -> None:
        alpha_table, parameters, _ = analysis.alpha_analysis(
            self.data, bootstrap_reps=20_000, seed=42
        )
        group = alpha_table.iloc[0]
        individual = alpha_table.iloc[1]
        values = parameters.set_index("Metric")["Estimate"]

        self.assertAlmostEqual(group["Point_Estimate"], 0.206, 3)
        self.assertLess(group["CI_Lower"], 0)
        self.assertGreater(group["CI_Upper"], 0.40)
        self.assertAlmostEqual(individual["Point_Estimate"], 0.228, 3)
        self.assertLess(individual["CI_Lower"], 0.02)
        self.assertAlmostEqual(values["Welch_P_Alpha_Equals_0"], 0.10, 2)
        self.assertLess(values["Welch_P_Alpha_Equals_4"], 0.001)
        self.assertAlmostEqual(values["Mu_Offloading_Factor"], 0.48, 2)

    def test_quality_components_match_composite_with_rounding(self) -> None:
        checked = analysis.quality_component_check(self.group_summary.reset_index())
        self.assertLessEqual(checked["Difference"].abs().max(), 0.1000001)
        rounded_components = checked[
            ["PassRate", "Coverage", "Static_Score", "Security_Score"]
        ].to_numpy()
        expected = np.array(
            [[85, 85, 82, 73], [20, 30, 70, 68], [100, 95, 90, 87], [86, 81, 85, 61]]
        )
        np.testing.assert_array_equal(rounded_components, expected)

    def test_weight_sensitivity_table(self) -> None:
        sensitivity = analysis.load_weight_sensitivity().set_index("Weighting_Scheme")
        self.assertEqual(sensitivity.loc["Original weights", "G4"], 92)
        self.assertEqual(sensitivity.loc["Security score +0.10", "G4"], 83)
        self.assertEqual(sensitivity.loc["PassRate -0.10", "G1"], 83)
        self.assertEqual(sensitivity.loc["Security score -0.10", "G4"], 100)

    def test_security_counts_and_standard_intervals(self) -> None:
        security = analysis.security_analysis().set_index(["Analysis", "Arm_or_Contrast"])
        ai = security.loc[("Flagged_Submission_Proportion", "AI-assisted")]
        manual = security.loc[("Flagged_Submission_Proportion", "Manual")]
        difference = security.loc[
            ("Flagged_Proportion_Difference", "AI-assisted minus Manual")
        ]
        triage = security.loc[
            ("Triaged_True_Positive_Fisher_Test", "AI-assisted versus Manual")
        ]

        self.assertAlmostEqual(ai["Estimate"], 14 / 24)
        self.assertAlmostEqual(manual["Estimate"], 6 / 24)
        self.assertAlmostEqual(ai["CI_Lower"], 0.3883467, 6)
        self.assertAlmostEqual(ai["CI_Upper"], 0.7553240, 6)
        self.assertAlmostEqual(manual["CI_Lower"], 0.1199937, 6)
        self.assertAlmostEqual(manual["CI_Upper"], 0.4489944, 6)
        self.assertAlmostEqual(difference["CI_Lower"], 0.0547322, 6)
        self.assertAlmostEqual(difference["CI_Upper"], 0.5489312, 6)
        self.assertAlmostEqual(triage["p"], 0.0722647, 6)


if __name__ == "__main__":
    unittest.main()
