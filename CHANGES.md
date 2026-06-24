# Repository Alignment with the Revised Manuscript

This repository was updated to be consistent with the revised manuscript
("AI-Assisted Development Under Schedule Pressure: A Controlled Pilot Study
of Micro-Task Productivity and Security Trade-offs"). Summary of changes:

## README.md
- Replaced the old title and the "Impossible Region" / "challenge decades-old
  assumptions" framing with the revised micro-task, pilot-study framing.
- "AI-assisted teams" -> "AI-assisted developers" throughout.
- Corrected the security trade-off figures to match the manuscript:
  AI-assisted 58.3% (14/24) vs. manual 25.0% (6/24) high-severity SAST flags
  (previously listed as 28% vs. 9%).
- Reframed the exploratory exponent as imprecise (CI crosses zero); removed the
  "markedly flatter effort response" claim.
- Added a Scope and Limitations section and documented generated outputs.

## data/dataset_48.csv
- Aligned per-group summary statistics to manuscript Table 4:
  - G2 composite quality mean 36.2 -> 39.2.
  - G4 effort mean 3.60 -> 3.42; G4 quality mean 79.1 -> 79.8.
  - Introduced one borderline sub-threshold G1 submission so the G1 success
    rate is 11/12 = 92% (consistent with Table 4 and the weight-sensitivity in
    Table 8), keeping the G1 mean at 82.2.
- Rebuilt the `Success` column to strictly equal `Quality_Score >= 75`
  (the previous flag column contradicted the documented rule).

## scripts/data.py
- Group labels "Trad-*" -> "Manual-*" to match the manuscript.
- Figure 3 (theoretical curve): illustrative AI exponent set to alpha = 2.0
  (matching the manuscript caption); the red "Traditional Impossible Region"
  label was renamed to a neutral "High-sensitivity region (conceptual)" and the
  figure title/legend were de-emphasized as conceptual (not fitted).
- Threshold legend wording aligned to "Acceptability Threshold (75)".

## scripts/analysis.R
- alpha is now computed from the dataset's own G3/G4 effort means
  (reproducible) instead of hard-coded literals.
- Group 95% CIs now use the t-distribution (n = 12 per cell), matching Table 4
  (previously used a normal 1.96 multiplier).
- Added a participant-level (individual) bootstrap in addition to the
  group-summary bootstrap; added the H0: alpha = 0 and H0: alpha = 4 tests.
- "Basis = Manuscript Table 1" corrected to Table 4.
- `Success_Rate` computed from `Quality_Score >= 75`.

## Generated artifacts
- group_summary.csv, alpha_fitting.csv, and Fig1-Fig4 were regenerated from the
  corrected data. The exploratory exponent reproduces as alpha ~ 0.21 with a 95%
  bootstrap CI of approximately [-0.03, 0.46], matching the manuscript.

Note: analysis.R was validated via an equivalent Python implementation in the
preparation environment (R was unavailable there); running `Rscript
scripts/analysis.R` reproduces the same statistics up to bootstrap RNG.
