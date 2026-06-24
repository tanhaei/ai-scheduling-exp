# AI-Assisted Development Under Schedule Pressure (Pilot Study)

This repository contains the **datasets** and **analysis scripts** for the following research paper:

**Title:** AI-Assisted Development Under Schedule Pressure: A Controlled Pilot Study of Micro-Task Productivity and Security Trade-offs
**Authors:** Mohammad Tanhaei, Roohallah Alizadehsani
**Journal:** The Journal of Systems and Software

## 📋 Overview

Classical software project-scheduling models (most notably the **Putnam software equation** and **Brooks' Law**) describe schedule compression as a **project-scale** phenomenon driven by staffing, coordination, and communication overhead. These models were developed for multi-person, multi-month projects and are **not tested or revised** by this study.

Instead, this work uses them only as **contextual framing** for a controlled **micro-task** experiment: a 2×2 between-subjects pilot with **48 professional Python developers** from a regulated health-systems company. The design crosses *tool support* (manual vs. GitHub Copilot/GPT-4) with *schedule condition* (nominal 6.0-hour vs. compressed 3.5-hour hard cap) on a bounded hospital bed-management task.

The study reports that, in the compressed condition, **AI-assisted developers** more often submitted artifacts above a pre-defined acceptability threshold than manual developers under the same time cap. The exploratory AI-assisted time-sensitivity exponent is small but **imprecise** ($\hat{\alpha}_{AI} \approx 0.21$, 95% bootstrap CI approximately $[-0.03, 0.46]$); because the interval crosses zero, it is treated as a **pilot descriptive estimate**, not a stable parameter, and it does **not** establish that AI assistance "flattens" any general scheduling curve. A concurrent **security trade-off** was observed: static-analysis tools flagged more high-severity indicators in AI-assisted submissions.

## 📂 Repository Structure

```
git/
├── data/
│   └── dataset_48.csv        # Raw experimental data (48 participants, synthetic)
├── scripts/
│   ├── data.py               # Data preprocessing and figure generation (Python)
│   └── analysis.R            # Exploratory alpha estimation, group summary, sensitivity plot (R)
├── group_summary.csv         # Generated: per-group means, SDs, t-based 95% CIs, success rates
├── alpha_fitting.csv         # Generated: exploratory alpha point estimate and bootstrap CIs
└── requirements.txt          # Python dependencies
```

### File Descriptions

* **data/dataset_48.csv** — Metrics for the 48 participants. Columns:
  * `Group`: Experimental group (G1–G4)
  * `Effort_Hours`: Within-task effort proxy in person-hours (G2 is the 3.5h hard cap)
  * `Quality_Score`: Composite quality score (0–100)
  * `Success`: Acceptability flag, defined strictly as `Quality_Score >= 75` (manuscript Section 4.5.2)
* **scripts/data.py** — Loads the dataset and generates Figures 1–3 (observed effort, composite quality distribution, and the *conceptual* theoretical curve). The theoretical curve is illustrative only and is **not** fitted to the data.
* **scripts/analysis.R** — Reproduces the group-level summary (Table 4), the exploratory AI time-sensitivity estimate, and the bootstrap sensitivity figure (Figure 4).

## 🚀 Usage

### Prerequisites

You will need **Python 3.9+** and **R**. Install the Python dependencies:

```
pip install -r requirements.txt
```

### Running the Analysis

1. **Figures (Python):**
   `python scripts/data.py`

2. **Exploratory alpha estimation and group summary (R):**
   `Rscript scripts/analysis.R`

## 📊 Key Findings

Based on the analysis (interpreted in light of the pilot sample size of n = 12 per cell):

* **Acceptability under compression:** In the compressed condition, AI-assisted developers reached the acceptability threshold (`Q >= 75`) far more often (**G4: 92%**) than manual developers (**G2: 0%**). Nominal-condition success was 92% (G1, manual) and 100% (G3, AI). The 0% manual-compressed rate was driven primarily by **functional incompleteness** at the hard cap, not by completed low-quality work.
* **Schedule sensitivity:** The exploratory exponent was $\hat{\alpha}_{AI} \approx 0.21$ with a wide 95% bootstrap CI of approximately $[-0.03, 0.46]$. Because the interval crosses zero, the study does **not** claim a definitive flattening of the project-scale Putnam curve; the contrast with the classical value ($\alpha = 4$) is descriptive and applies only at the micro-task level.
* **Security trade-off:** Static-analysis (SAST) tools flagged high-severity indicators in **58.3% (14/24)** of AI-assisted submissions versus **25.0% (6/24)** of manual submissions. These are reported as **security-risk indicators**, not confirmed exploitable vulnerabilities, and motivate pairing AI-driven acceleration with secure-coding review and security gates.

## ⚠️ Scope and Limitations

This is a **controlled pilot** limited to individual developers performing a short, bounded task. Results should **not** be extrapolated to multi-team, multi-month enterprise projects without longitudinal replication. The dataset is **synthetic** and provided to reproduce the manuscript's reported summary statistics and figures.

## 📝 Citation

If you use this dataset or code, please cite:

Tanhaei, M., & Alizadehsani, R. *AI-Assisted Development Under Schedule Pressure: A Controlled Pilot Study of Micro-Task Productivity and Security Trade-offs.* The Journal of Systems and Software.

## ⚖️ License

This project is licensed under the **MIT License**. You are free to use the data with appropriate attribution.
