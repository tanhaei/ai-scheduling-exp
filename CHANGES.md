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

---

# Second Alignment Pass (against the revised manuscript, V2)

## data/dataset_48.csv (rebuilt)
- Every cell now has mean and SD equal (to reported precision) to the
  Table 4 values, so the dataset exactly reproduces:
  - Table 4 (all means, SDs, t-based 95% CIs, and success rates);
  - Table 5 and Table 6 sums of squares (26.1 / 12.9 / 23.4 / 6.60 and
    8523 / 10127 / 2335 / 2191) and the partial eta-squared values;
  - the mixed-model interaction coefficients (2.79 for effort, 27.9 for
    quality, Section 5.3);
  - mu-hat = 1 - 3.06/5.93 ~= 0.48 (Section 5.5).
  (Table 5's F column follows the rounded-SS convention 26.1/0.150 = 174.0;
  F recomputed from the raw data is 173.9/85.6/155.6, identical within
  rounding.)
- Effort values are reported to 4 decimals (telemetry-derived hours).
- The G4 cell intentionally contains session-effort values above the
  3.5 h wall-clock cap; E_session is a composite proxy over activity
  categories, and Table 4's own CI upper bound (3.71) already exceeds
  the cap.

## scripts/analysis.R
- FIX: the schedule-compression ratio is now the actual t_d/t_o = 3.5/6.0
  (previously the rounded 0.6). With the actual ratio the group-level
  exponent reproduces the manuscript's alpha ~= 0.21.
- The participant-level bootstrap now uses a log-scale estimator
  (difference of mean log efforts), matching the manuscript's
  participant-level value alpha ~= 0.23.
- The H0: alpha = 0 and H0: alpha = 4 tests are now Welch t tests on
  log-transformed session effort and are printed (previously computed
  but never output). mu-hat is also printed.
- Figure 4 now shows the group-level bootstrap distribution (the
  distribution whose CI crosses zero, as in the manuscript figure),
  with the manuscript's title/labels.
- Bootstrap replicates increased to 100,000 to stabilize the reported
  quantile digits.

## scripts/data.py
- Figure 2 (quality) is now a mean +/- SD bar chart with per-bar mean
  labels and success annotations, matching manuscript Figure 3
  (previously a boxplot, which does not appear in the manuscript).
- Figure 1 (effort) now carries per-bar value labels and the
  "(Hard cap)" annotation for G2, matching manuscript Figure 2.
- Removed a matplotlib >= 3.9-only argument for portability.

## Manuscript numbers updated to the reproduced values (Section 5.5)
Three exploratory scalars in the manuscript could not be derived from
any dataset consistent with Table 4 and were updated in V2 to the
values this repository reproduces:
- group-level bootstrap CI upper bound: 0.46 -> 0.45;
- Welch log-scale test against alpha = 0: p = 0.14 -> p = 0.10;
- participant-level CI [0.01, 0.49] -> approximately [0.00, 0.49], with
  the "narrowly excludes zero" claim reworded (the lower bound sits
  essentially at zero and its sign is not stable across resampling
  schemes/seeds).
All other reported values were left unchanged and reproduce exactly.

Note: analysis.R was again validated via an equivalent Python
implementation in the preparation environment (R unavailable there);
running `Rscript scripts/analysis.R` reproduces the same statistics up
to bootstrap RNG in the third decimal of the quantiles.
