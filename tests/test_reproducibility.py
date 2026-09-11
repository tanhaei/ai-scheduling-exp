from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analysis  # noqa: E402
import data as plotting  # noqa: E402


class ReproducibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quality = analysis.load_quality_summary()

    def test_final_2x2_inputs(self) -> None:
        self.assertEqual(self.quality["Group"].tolist(), ["G1", "G2", "G3", "G4"])
        self.assertEqual(self.quality["N"].tolist(), [12, 12, 12, 12])
        np.testing.assert_allclose(self.quality["Q_Mean"], [82.2, 39.2, 94.9, 79.8])
        np.testing.assert_allclose(self.quality["Q_SD"], [4.9, 12.1, 3.2, 4.3])
        self.assertEqual(self.quality["Success_Q75"].tolist(), [11, 0, 12, 11])

    def test_table_4_quality_intervals_and_success_wilson(self) -> None:
        table = analysis.quality_summary_with_intervals().set_index("Group")
        expected_q_ci = {
            "G1": (79.1, 85.3),
            "G2": (31.5, 46.9),
            "G3": (92.9, 96.9),
            "G4": (77.1, 82.5),
        }
        expected_wilson = {
            "G1": (64.6, 98.5),
            "G2": (0.0, 24.2),
            "G3": (75.8, 100.0),
            "G4": (64.6, 98.5),
        }
        for group in analysis.GROUPS:
            row = table.loc[group]
            self.assertEqual(
                (round(100 * row.Success_Wilson_Lower, 1), round(100 * row.Success_Wilson_Upper, 1)),
                expected_wilson[group],
            )
            self.assertEqual(
                (round(row.Q_CI_Lower, 1), round(row.Q_CI_Upper, 1)),
                expected_q_ci[group],
            )

    def test_table_5_summary_anova(self) -> None:
        table = analysis.summary_based_quality_anova().set_index("Term")
        self.assertAlmostEqual(table.loc["Tool", "SS"], 8522.67, 8)
        self.assertAlmostEqual(table.loc["Schedule", "SS"], 10126.83, 8)
        self.assertAlmostEqual(table.loc["Tool x Schedule", "SS"], 2335.23, 8)
        self.assertAlmostEqual(table.loc["Residual", "SS"], 2190.65, 8)
        self.assertAlmostEqual(table.loc["Residual", "MS"], 49.7875, 8)
        self.assertAlmostEqual(table.loc["Tool x Schedule", "F"], 46.90394175, 7)
        self.assertAlmostEqual(table.loc["Tool x Schedule", "p"], 1.90594122e-8, places=15)
        self.assertAlmostEqual(table.loc["Tool x Schedule", "Partial_Eta_Squared"], 0.51597258, 7)

    def test_success_exact_statistics(self) -> None:
        table = analysis.success_analysis().set_index(["Analysis", "Contrast"])
        contrast = table.loc[("Compressed-condition risk difference", "G4 minus G2")]
        omnibus = table.loc[("Fisher-Freeman-Halton omnibus", "G1-G4 heterogeneity")]
        self.assertAlmostEqual(contrast.Estimate, 11 / 12)
        self.assertAlmostEqual(contrast.CI_Lower, 0.5533502838, 9)
        self.assertAlmostEqual(contrast.CI_Upper, 0.9851349056, 9)
        self.assertAlmostEqual(contrast.p, 9.6148299137e-6, places=14)
        self.assertAlmostEqual(omnibus.p, 5.2247403046e-9, places=17)

    def test_minimum_detectable_interaction_effect(self) -> None:
        row = analysis.minimum_detectable_interaction_effect().iloc[0]
        self.assertAlmostEqual(row.Minimum_Detectable_f, 0.4135, 4)
        self.assertAlmostEqual(row.Equivalent_Partial_Eta_Squared, 0.1460, 4)

    def test_table_6_component_summaries(self) -> None:
        table = analysis.component_summary_with_intervals().set_index("Group")
        self.assertEqual((table.loc["G1", "PassRate_Mean"], table.loc["G1", "PassRate_SD"]), (85.05, 7.33))
        self.assertEqual((round(table.loc["G1", "PassRate_Reported_CI_Lower"], 2), round(table.loc["G1", "PassRate_Reported_CI_Upper"], 2)), (80.40, 89.70))
        self.assertEqual((table.loc["G3", "PassRate_Mean"], table.loc["G3", "PassRate_SD"]), (100.0, 0.0))
        self.assertEqual((table.loc["G3", "PassRate_Reported_CI_Lower"], table.loc["G3", "PassRate_Reported_CI_Upper"]), (100.0, 100.0))
        self.assertEqual(round(table.loc["G3", "Coverage_Reported_CI_Upper"], 2), 100.48)
        self.assertEqual((round(table.loc["G4", "Security_Score_Reported_CI_Lower"], 2), round(table.loc["G4", "Security_Score_Reported_CI_Upper"], 2)), (53.38, 68.52))
        self.assertLessEqual(table.filter(like="CI_Max_Abs_Difference").to_numpy().max(), 0.011)

    def test_table_7_weight_sensitivity(self) -> None:
        table = analysis.load_weight_sensitivity().set_index("Weighting_Scheme")
        self.assertEqual(table.loc["Original weights", analysis.GROUPS].astype(int).tolist(), [11, 0, 12, 11])
        self.assertEqual(table.loc["Coverage +0.10", analysis.GROUPS].astype(int).tolist(), [12, 0, 12, 10])
        self.assertEqual(table.loc["Security score +0.10", analysis.GROUPS].astype(int).tolist(), [10, 0, 12, 6])
        self.assertEqual(table.loc["Static score -0.10", analysis.GROUPS].astype(int).tolist(), [11, 0, 12, 9])

    def test_table_8_threshold_sensitivity(self) -> None:
        table = analysis.load_threshold_sensitivity().set_index("Threshold")
        self.assertEqual(table.loc[70, analysis.GROUPS].astype(int).tolist(), [12, 0, 12, 12])
        self.assertEqual(table.loc[75, analysis.GROUPS].astype(int).tolist(), [11, 0, 12, 11])
        self.assertEqual(table.loc[80, analysis.GROUPS].astype(int).tolist(), [8, 0, 12, 5])

    def test_security_statistics(self) -> None:
        table = analysis.security_analysis().set_index(["Analysis", "Contrast"])
        ai = table.loc[("Pooled flagged proportion", "AI-assisted")]
        manual = table.loc[("Pooled flagged proportion", "Manual")]
        difference = table.loc[("Pooled flagged risk difference", "AI-assisted minus Manual")]
        interaction = table.loc[("Exact Tool x Schedule interaction", "G1-G4 conditional test")]
        triage = table.loc[("Descriptive triage Fisher test", "8/24 AI-assisted vs 2/24 Manual")]

        self.assertAlmostEqual(ai.Estimate, 14 / 24)
        self.assertEqual((round(100 * ai.CI_Lower, 1), round(100 * ai.CI_Upper, 1)), (38.8, 75.5))
        self.assertAlmostEqual(manual.Estimate, 6 / 24)
        self.assertEqual((round(100 * manual.CI_Lower, 1), round(100 * manual.CI_Upper, 1)), (12.0, 44.9))
        self.assertEqual((round(100 * difference.CI_Lower, 1), round(100 * difference.CI_Upper, 1)), (5.5, 54.9))
        self.assertAlmostEqual(difference.p, 0.03921025999, 10)
        self.assertEqual(interaction.p, 1.0)
        self.assertAlmostEqual(triage.p, 0.07226467309, 10)

    def test_supporting_tables(self) -> None:
        analysis.validate_supporting_tables()  # raises on any mismatch

    def test_validation_has_no_mismatch(self) -> None:
        validation = analysis.manuscript_validation()
        self.assertFalse((validation["Status"] == "MISMATCH").any())

    def test_figure_generation(self) -> None:
        paths = [
            plotting.plot_within_window_success(),
            plotting.plot_composite_quality(),
            plotting.plot_threshold_sensitivity(),
        ]
        for path in paths:
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
