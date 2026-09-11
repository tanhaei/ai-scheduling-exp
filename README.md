# AI-Assisted Development Under Schedule Pressure (Pilot Study)

Reproducibility package for:

**AI-Assisted Development Under Schedule Pressure: A Controlled Pilot Study of Micro-Task Productivity and Security Trade-offs**  
Mohammad Tanhaei and Roohallah Alizadehsani, *The Journal of Systems and Software*.

## Scope of this revision

This repository is aligned with manuscript V3 dated 2026-09-11. The paper studies a controlled 2 x 2 pilot experiment with 48 professional Python developers (12 per cell), crossing tool support (manual vs. GitHub Copilot/GPT-4) with schedule condition (6.0-hour nominal vs. 3.5-hour compressed hard cap).

The repository reproduces the manuscript's **aggregate numerical checks**. It intentionally does **not** reconstruct participant-level observations from aggregate summaries. It also does not implement analyses removed from the manuscript: there is no effort ANOVA, schedule-sensitivity exponent, offloading factor, or related bootstrap analysis.

## Reference analysis environment

Appendix C of the manuscript reports the following numerical-analysis environment:

- Python 3.12.13
- NumPy 2.3.5
- SciPy 1.17.0
- pandas 2.2.3
- Matplotlib 3.10.8

The Python package versions are pinned in `requirements.txt`.

## Final manuscript inputs

The `data/` directory contains only values needed for the analyses reported in the current manuscript:

- `quality_summary.csv`: Table 4 quality means, SDs, cell sizes, and Q >= 75 success counts.
- `quality_components_summary.csv`: Table 6 component means and SDs.
- `weight_sensitivity_summary.csv`: Table 7 final success counts under +/-0.10 weight perturbations.
- `threshold_sensitivity_summary.csv`: Table 8 final success counts at Q >= 70, 75, and 80.
- `security_summary.csv`: Table 9 four-cell high-severity SAST submission counts.
- `sast_breakdown.csv`: Table 10 rule-category flag counts.
- `sast_triage_summary.csv`: Table 11 limited manual-triage summary.
- `sast_tool_versions.csv`: SAST executable versions reported in the manuscript, with the documented configuration limitations.
- `participant_balance_summary.csv`: Table 1 participant-balance summaries, including prior-AI exposure counts 5/12, 6/12, 5/12, and 7/12 (23/48 total).
- `questionnaire_summary.csv`: descriptive NASA-TLX/TAM values retained in Appendix B.

The original participant source snapshots, questionnaire records, detailed SAST reports, and executable transformations used to derive the static/security component scores are not included. Therefore, the repository checks the calculations supported by the final reported summaries; it does not claim independent re-measurement of those unavailable source records.

## What is reproduced

The main Python pipeline reproduces or checks:

- Table 4 t-based 95% CIs and Wilson success intervals.
- G4 vs. G2 two-sided Fisher exact test and Newcombe risk-difference interval.
- Fisher-Freeman-Halton exact omnibus test across the four success cells.
- Table 5 summary-based 2 x 2 ANOVA for continuous composite quality and partial eta-squared.
- The minimum detectable Tool x Schedule interaction effect (`f = 0.4135`, partial eta-squared `= 0.1460`).
- Table 6 component t-intervals from the final means and SDs.
- Tables 7 and 8 sensitivity grids as final reported inputs.
- Table 9 cell and pooled security proportions, Wilson intervals, pooled Fisher exact test, and Newcombe interval.
- Appendix C.4 exact conditional Tool x Schedule security interaction test from counts `(3, 3, 7, 7)`.
- The descriptive 8/24 vs. 2/24 triage Fisher calculation.
- Figures 1-3 directly from the final manuscript values.

## Run

```bash
python -m pip install -r requirements.txt
python scripts/analysis.py
python scripts/data.py
python -m unittest discover -s tests -v
```

`python scripts/analysis.py` writes:

- `quality_summary.csv`
- `anova_results.csv`
- `success_analysis.csv`
- `power_analysis.csv`
- `quality_components.csv`
- `security_analysis.csv`
- `manuscript_validation.csv`

`python scripts/data.py` writes:

- `Fig1_Within_Window_Success.pdf`
- `Fig2_Composite_Quality.pdf`
- `Fig3_Threshold_Sensitivity.pdf`

## Interpretation limits

The security results are SAST screening indicators, not confirmed exploitability. The security analysis is post hoc, and the manuscript's limited manual triage is descriptive rather than a blinded complete validation study. Likewise, the sensitivity grids are final reported inputs; without participant-level component scores, they cannot be independently re-derived from the group means alone.
