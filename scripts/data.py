import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd

# تنظیمات برای خروجی PDF و فونت‌های استاندارد
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams.update({
    "font.family": "serif",
    "pdf.fonttype": 42,   # برای جلوگیری از تبدیل فونت به منحنی
    "ps.fonttype": 42
})

# خواندن دیتاست واقعی
df = pd.read_csv('data/dataset_48.csv')

# ==========================================
# نمودار ۱: مقایسه تلاش (Effort) - بر اساس دیتاست
# ==========================================
effort_summary = df.groupby('Group')['Effort_Hours'].agg(['mean', 'std']).reset_index()
effort_summary.columns = ['Group', 'Effort', 'SD']
# Labelهای گروهی
labels = {
    'G1': 'G1\n(Trad-Nominal)',
    'G2': 'G2\n(Trad-Compressed)',
    'G3': 'G3\n(AI-Nominal)',
    'G4': 'G4\n(AI-Compressed)'
}
effort_summary['Group'] = effort_summary['Group'].map(labels)

plt.figure(figsize=(8, 6))
colors = ["#34495e", "#34495e", "#2ecc71", "#2ecc71"]
bar = sns.barplot(x='Group', y='Effort', data=effort_summary, palette=colors, capsize=.1, errorbar=None)

# اضافه کردن Error Bars دستی
x_coords = [p.get_x() + 0.5 * p.get_width() for p in bar.patches]
y_coords = [p.get_height() for p in bar.patches]
plt.errorbar(x=x_coords, y=y_coords, yerr=effort_summary['SD'], fmt='none', c='black', capsize=5)

plt.axhline(y=6.0, color='gray', linestyle='--', alpha=0.5, label='Nominal Time ($t_o$)')
plt.axhline(y=3.5, color='red', linestyle='--', alpha=0.7, label='Compressed Time ($0.6t_o$)')

plt.ylabel('Effort (Person-Hours)', fontweight='bold')
plt.xlabel('')
plt.title('Impact of AI on Effort under Time Pressure', fontweight='bold')
plt.legend()
plt.tight_layout()
plt.savefig('Fig1_Effort_Analysis.pdf', format='pdf', bbox_inches='tight')
plt.close()

# ==========================================
# نمودار ۲: توزیع کیفیت (Quality) - بر اساس دیتاست
# ==========================================
plt.figure(figsize=(8, 6))
box = sns.boxplot(x='Group', y='Quality_Score', data=df, palette="Set2", width=0.5)
plt.axhline(y=75, color='red', linestyle='-.', linewidth=2, label='Min Acceptable Quality (75)')

# Annotation برای Success Rate (محاسبه از دیتاست)
success_rates = df.groupby('Group')['Success'].mean().round(2) * 100
for i, (group, rate) in enumerate(success_rates.items()):
    plt.text(i, 95, f'Success: {rate}%', ha='center', va='bottom', fontweight='bold', fontsize=10)

plt.ylabel('Code Quality Score (0-100)', fontweight='bold')
plt.title('Code Quality Distribution Across Groups', fontweight='bold')
plt.legend(loc='lower left')
plt.tight_layout()
plt.savefig('Fig2_Quality_Distribution.pdf', format='pdf', bbox_inches='tight')
plt.close()

# ==========================================
# نمودار ۳: منحنی تئوری (Theoretical Curve) - بدون تغییر، اما با CI
# ==========================================
t = np.linspace(0.4, 1.2, 100)
Eo = 1.0
E_classic = Eo * (1/t)**4
alpha_ai = 1.8
E_ai = Eo * (1/t)**alpha_ai

# CI bands برای α AI: [1.6, 2.0]
E_ai_low = Eo * (1/t)**1.6
E_ai_high = Eo * (1/t)**2.0

plt.figure(figsize=(8, 6))
plt.plot(t, E_classic, label='Traditional Model (Putnam: $\\alpha=4$)', color='black', linestyle='--')
plt.plot(t, E_ai, label='AI-Assisted Model ($\\alpha\\approx1.8$)', color='green', linewidth=3)

# Shaded band برای CI
plt.fill_between(t, E_ai_low, E_ai_high, color='green', alpha=0.2, label='95% CI: [1.6-2.0]')

plt.axvspan(0.4, 0.75, color='red', alpha=0.1, label='Traditional "Impossible Region"')
plt.axvline(x=0.75, color='red', linestyle=':')

plt.ylim(0, 5)
plt.xlim(0.4, 1.1)
plt.xlabel('Normalized Schedule Time ($t_d / t_o$)', fontweight='bold')
plt.ylabel('Normalized Effort ($E / E_o$)', fontweight='bold')
plt.title('Flattening the Cost Curve: AI vs. Traditional', fontweight='bold')
plt.legend()
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.tight_layout()
plt.savefig('Fig3_Theoretical_Curve.pdf', format='pdf', bbox_inches='tight')
plt.close()

print("All three figures saved as PDF files based on the dataset.")