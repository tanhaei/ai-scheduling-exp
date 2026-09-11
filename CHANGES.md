# Alignment changes for manuscript V3 (2026-09-11)

This revision updates the repository to match the final analyses and figures in `V3(20260911-075333).pdf`.

## Removed obsolete analyses and assets

- Removed the participant-level reconstructed `dataset_48.csv` from the active reproducibility pipeline.
- Removed the effort ANOVA, effort summaries, schedule-sensitivity exponent (`alpha`), offloading factor (`mu`), bootstrap analyses, and their output files.
- Removed the old theoretical Putnam/AI curve and effort/sensitivity figures.
- Removed the obsolete R analysis mirror because the current manuscript's Appendix C specifies the Python analysis environment and the R script implemented analyses that are no longer in the paper.

## Added/updated current analyses

- Rebuilt the quality analysis from the final Table 4 means, SDs, n=12 per cell, and success counts.
- Added the summary-based quality ANOVA exactly as described in Appendix C.2, including residual SSE = 2190.65.
- Added the G4-vs-G2 Fisher exact test and Newcombe risk-difference interval.
- Added the probability-ordered Fisher-Freeman-Halton exact test across all four success cells.
- Added the minimum detectable interaction effect calculation (`f = 0.4135`, partial eta-squared `= 0.1460`).
- Updated Table 6 component means/SDs and t-interval calculations.
- Replaced the old weight-sensitivity percentages with the final Table 7 success counts.
- Added the final Table 8 threshold-sensitivity counts.
- Replaced pooled-only security input with the final four-cell counts `(3, 3, 7, 7)` and added the exact conditional Tool x Schedule interaction calculation from Appendix C.4.
- Preserved the pooled security comparison (14/24 vs. 6/24), standard Wilson/Newcombe intervals, and descriptive triage Fisher calculation.
- Added reported SAST executable versions and explicit notes that the rulesets/configuration artifacts are unavailable.

## Figures

The plotting pipeline now generates the three figures present in the manuscript:

1. `Fig1_Within_Window_Success.pdf`
2. `Fig2_Composite_Quality.pdf`
3. `Fig3_Threshold_Sensitivity.pdf`

All figure values are read directly from the final manuscript summary files.

## Tests

The unit tests now check the exact final manuscript values for Tables 4-11 where arithmetic reproduction is possible, the exact omnibus/interaction tests, power calculation, supporting summaries, and successful figure generation. Any manuscript mismatch causes the main analysis pipeline to exit with an error.
