from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / 'data' / 'dataset_48.csv'

plt.rcParams.update({
    'font.family': 'serif',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})


def validate_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f'Missing required columns in dataset: {missing}')


# Load dataset
if not DATA_PATH.exists():
    raise FileNotFoundError(f'Dataset not found: {DATA_PATH}')

df = pd.read_csv(DATA_PATH)
validate_columns(df, ['Group', 'Effort_Hours', 'Quality_Score'])

# Group labels match the manuscript (manual vs. AI-assisted developers).
labels = {
    'G1': 'G1\n(Manual-Nominal)',
    'G2': 'G2\n(Manual-Compressed)',
    'G3': 'G3\n(AI-Nominal)',
    'G4': 'G4\n(AI-Compressed)',
}
order = ['G1', 'G2', 'G3', 'G4']

# ==========================================
# Figure 1: Observed within-task effort across groups
# ==========================================
effort_summary = (
    df.groupby('Group', as_index=False)['Effort_Hours']
    .agg(['mean', 'std'])
    .reset_index()
    .rename(columns={'mean': 'Effort', 'std': 'SD'})
)
effort_summary = effort_summary[effort_summary['Group'].isin(order)].copy()
effort_summary['Label'] = effort_summary['Group'].map(labels)

fig, ax = plt.subplots(figsize=(8, 6))
x = np.arange(len(effort_summary))
colors = ['#34495e', '#34495e', '#2ecc71', '#2ecc71']
ax.bar(x, effort_summary['Effort'], yerr=effort_summary['SD'], capsize=5, color=colors)
for xi, (val, grp) in enumerate(zip(effort_summary['Effort'], effort_summary['Group'])):
    label = f'{val:.2f}\n(Hard cap)' if grp == 'G2' else f'{val:.2f}'
    ax.text(xi, val + 0.18, label, ha='center', va='bottom', fontweight='bold', fontsize=10)
ax.axhline(y=6.0, color='gray', linestyle='--', alpha=0.6, label='Nominal Time ($t_o$)')
ax.axhline(y=3.5, color='red', linestyle='--', alpha=0.8, label='Compressed Time ($0.6t_o$)')
ax.set_xticks(x)
ax.set_xticklabels(effort_summary['Label'])
ax.set_ylim(0, 6.9)
ax.set_ylabel('Effort (Person-Hours)', fontweight='bold')
ax.set_xlabel('')
ax.set_title('Observed Within-Task Effort Across Experimental Groups', fontweight='bold')
ax.legend()
fig.tight_layout()
fig.savefig(REPO_ROOT / 'Fig1_Effort_Analysis.pdf', format='pdf', bbox_inches='tight')
plt.close(fig)

# ==========================================
# Figure 2: Composite quality scores across groups (mean +/- SD),
# matching manuscript Figure 3.
# ==========================================
fig, ax = plt.subplots(figsize=(8, 6))
q_mean = df.groupby('Group')['Quality_Score'].mean().reindex(order)
q_sd = df.groupby('Group')['Quality_Score'].std().reindex(order)
bar_colors = ['#34495e', '#34495e', '#2ecc71', '#2ecc71']
x = np.arange(len(order))
ax.bar(x, q_mean, yerr=q_sd, capsize=5, color=bar_colors)

ax.axhline(y=75, color='red', linestyle='-.', linewidth=2, label='Acceptability Threshold (75)')
# Success is reported as the share of submissions reaching Q >= 75.
success_rates = (df.assign(S=(df['Quality_Score'] >= 75).astype(int))
                 .groupby('Group')['S'].mean().reindex(order).fillna(0) * 100)

for xi, (mval, rate) in enumerate(zip(q_mean, success_rates)):
    ax.text(xi, mval + 1.5, f'{mval:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.text(xi, 103, f'Success: {rate:.0f}%', ha='center', va='bottom', fontweight='bold', fontsize=10)

ax.set_xticks(x)
ax.set_xticklabels([labels[g] for g in order])
ax.set_ylim(0, 112)
ax.set_ylabel('Composite Quality Score (0-100)', fontweight='bold')
ax.set_title('Composite Quality Scores Across Groups', fontweight='bold')
ax.legend(loc='lower left')
fig.tight_layout()
fig.savefig(REPO_ROOT / 'Fig2_Quality_Distribution.pdf', format='pdf', bbox_inches='tight')
plt.close(fig)

# ==========================================
# Figure 3: Illustrative (conceptual) theoretical curve
# This figure is a conceptual contrast only; it is NOT fitted to the
# experimental data. The AI-assisted curve uses an illustrative exponent
# (alpha = 2.0), matching the manuscript figure caption.
# ==========================================
t = np.linspace(0.4, 1.2, 200)
Eo = 1.0
alpha_classic = 4.0
alpha_ai_illustrative = 2.0
alpha_ai_low = 1.6
alpha_ai_high = 2.4

E_classic = Eo * (1 / t) ** alpha_classic
E_ai = Eo * (1 / t) ** alpha_ai_illustrative
E_ai_low = Eo * (1 / t) ** alpha_ai_low
E_ai_high = Eo * (1 / t) ** alpha_ai_high

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(t, E_classic, label='Classical Putnam curve ($\\alpha = 4$)', color='black', linestyle='--')
ax.plot(t, E_ai, label='Illustrative AI-assisted curve ($\\alpha = 2.0$)', color='green', linewidth=3)
ax.fill_between(t, E_ai_low, E_ai_high, color='green', alpha=0.2, label='Conceptual sensitivity band')
ax.axvspan(0.4, 0.75, color='red', alpha=0.1, label='High-sensitivity region (conceptual)')
ax.axvline(x=0.75, color='red', linestyle=':')
ax.set_ylim(0, 5)
ax.set_xlim(0.4, 1.1)
ax.set_xlabel('Normalized Schedule Time ($t_d / t_o$)', fontweight='bold')
ax.set_ylabel('Normalized Effort ($E / E_o$)', fontweight='bold')
ax.set_title('Conceptual Comparison: Classical vs. AI-Assisted Curves', fontweight='bold')
ax.legend()
ax.grid(True, which='both', linestyle='--', linewidth=0.5)
fig.tight_layout()
fig.savefig(REPO_ROOT / 'Fig3_Theoretical_Curve.pdf', format='pdf', bbox_inches='tight')
plt.close(fig)

print('Figures saved: Fig1_Effort_Analysis.pdf, Fig2_Quality_Distribution.pdf, Fig3_Theoretical_Curve.pdf')
