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

labels = {
    'G1': 'G1\n(Trad-Nominal)',
    'G2': 'G2\n(Trad-Compressed)',
    'G3': 'G3\n(AI-Nominal)',
    'G4': 'G4\n(AI-Compressed)',
}
order = ['G1', 'G2', 'G3', 'G4']

# ==========================================
# Figure 1: Observed effort across groups
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
ax.axhline(y=6.0, color='gray', linestyle='--', alpha=0.6, label='Nominal Time ($t_o$)')
ax.axhline(y=3.5, color='red', linestyle='--', alpha=0.8, label='Compressed Time ($0.6t_o$)')
ax.set_xticks(x)
ax.set_xticklabels(effort_summary['Label'])
ax.set_ylabel('Effort (Person-Hours)', fontweight='bold')
ax.set_xlabel('')
ax.set_title('Observed Effort Across Experimental Groups', fontweight='bold')
ax.legend()
fig.tight_layout()
fig.savefig(REPO_ROOT / 'Fig1_Effort_Analysis.pdf', format='pdf', bbox_inches='tight')
plt.close(fig)

# ==========================================
# Figure 2: Quality distribution across groups
# ==========================================
fig, ax = plt.subplots(figsize=(8, 6))
quality_data = [df.loc[df['Group'] == group, 'Quality_Score'].to_numpy() for group in order]
box = ax.boxplot(quality_data, tick_labels=[labels[g] for g in order], patch_artist=True, widths=0.55)
box_colors = ['#95a5a6', '#95a5a6', '#a3e4a8', '#a3e4a8']
for patch, color in zip(box['boxes'], box_colors):
    patch.set_facecolor(color)

ax.axhline(y=75, color='red', linestyle='-.', linewidth=2, label='Min Acceptable Quality (75)')
if 'Success' in df.columns:
    success_rates = df.groupby('Group')['Success'].mean().reindex(order).fillna(0) * 100
else:
    success_rates = df.assign(Success=(df['Quality_Score'] >= 75).astype(int)).groupby('Group')['Success'].mean().reindex(order).fillna(0) * 100

for idx, rate in enumerate(success_rates, start=1):
    ax.text(idx, 96, f'Success: {round(rate):.0f}%', ha='center', va='bottom', fontweight='bold', fontsize=10)

ax.set_ylabel('Code Quality Score (0-100)', fontweight='bold')
ax.set_title('Composite Quality Scores Across Groups', fontweight='bold')
ax.legend(loc='lower left')
fig.tight_layout()
fig.savefig(REPO_ROOT / 'Fig2_Quality_Distribution.pdf', format='pdf', bbox_inches='tight')
plt.close(fig)

# ==========================================
# Figure 3: Illustrative theoretical curve
# ==========================================
t = np.linspace(0.4, 1.2, 200)
Eo = 1.0
alpha_classic = 4.0
alpha_ai_illustrative = 1.8
alpha_ai_low = 1.3
alpha_ai_high = 2.3

E_classic = Eo * (1 / t) ** alpha_classic
E_ai = Eo * (1 / t) ** alpha_ai_illustrative
E_ai_low = Eo * (1 / t) ** alpha_ai_low
E_ai_high = Eo * (1 / t) ** alpha_ai_high

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(t, E_classic, label='Traditional Model (Putnam: $\\alpha = 4$)', color='black', linestyle='--')
ax.plot(t, E_ai, label='Illustrative AI-Assisted Curve', color='green', linewidth=3)
ax.fill_between(t, E_ai_low, E_ai_high, color='green', alpha=0.2, label='Illustrative sensitivity band')
ax.axvspan(0.4, 0.75, color='red', alpha=0.1, label='Traditional "Impossible Region"')
ax.axvline(x=0.75, color='red', linestyle=':')
ax.set_ylim(0, 5)
ax.set_xlim(0.4, 1.1)
ax.set_xlabel('Normalized Schedule Time ($t_d / t_o$)', fontweight='bold')
ax.set_ylabel('Normalized Effort ($E / E_o$)', fontweight='bold')
ax.set_title('Illustrative Comparison: Traditional vs. AI-Assisted Curves', fontweight='bold')
ax.legend()
ax.grid(True, which='both', linestyle='--', linewidth=0.5)
fig.tight_layout()
fig.savefig(REPO_ROOT / 'Fig3_Theoretical_Curve.pdf', format='pdf', bbox_inches='tight')
plt.close(fig)

print('Figures saved: Fig1_Effort_Analysis.pdf, Fig2_Quality_Distribution.pdf, Fig3_Theoretical_Curve.pdf')
