# ==========================================
# analysis.R: Exploratory alpha estimation for the manuscript
# ==========================================
# This script reproduces the manuscript-referenced exploratory estimate
# of the AI-assisted time-sensitivity exponent (alpha), the group-level
# summary table (Table 4), and the corresponding sensitivity figure.
#
# Notes on interpretation (consistent with the manuscript):
#   - alpha is an EXPLORATORY, task-specific descriptor, not a stable
#     parameter. Its bootstrap interval crosses zero.
#   - The estimate is derived from the observed AI-assisted conditions
#     (G3, G4) summarized in Table 4 of the manuscript.
#
# Outputs:
#   - alpha_fitting.csv
#   - group_summary.csv
#   - Fig4_Sensitivity.pdf
# Author: Mohammad Tanhaei
# ==========================================

get_script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep('^--file=', args, value = TRUE)
  if (length(file_arg) > 0) {
    return(dirname(normalizePath(sub('^--file=', '', file_arg[1]))))
  }
  return(getwd())
}

script_dir <- get_script_dir()
repo_root <- normalizePath(file.path(script_dir, '..'))
data_path <- file.path(repo_root, 'data', 'dataset_48.csv')
alpha_csv_path <- file.path(repo_root, 'alpha_fitting.csv')
summary_csv_path <- file.path(repo_root, 'group_summary.csv')
figure_path <- file.path(repo_root, 'Fig4_Sensitivity.pdf')

if (!file.exists(data_path)) {
  stop(paste('Dataset not found:', data_path))
}

df <- read.csv(data_path, stringsAsFactors = FALSE)
required_cols <- c('Group', 'Effort_Hours', 'Quality_Score', 'Success')
missing_cols <- setdiff(required_cols, names(df))
if (length(missing_cols) > 0) {
  stop(paste('Missing required columns:', paste(missing_cols, collapse = ', ')))
}

# 95% confidence intervals use the t-distribution (n = 12 per cell),
# matching the intervals reported in Table 4 of the manuscript.
mean_ci <- function(x) {
  n <- length(x)
  m <- mean(x)
  s <- sd(x)
  se <- s / sqrt(n)
  tcrit <- qt(0.975, df = n - 1)
  ci <- m + c(-1, 1) * tcrit * se
  c(mean = m, sd = s, ci_lower = ci[1], ci_upper = ci[2])
}

groups <- c('G1', 'G2', 'G3', 'G4')
group_summary <- data.frame()

for (g in groups) {
  subset_df <- df[df$Group == g, ]
  effort_stats <- mean_ci(subset_df$Effort_Hours)
  quality_stats <- mean_ci(subset_df$Quality_Score)
  # Success is the share of submissions reaching the acceptability
  # threshold Q >= 75 (see manuscript Section 4.5.2).
  success_rate <- mean(subset_df$Quality_Score >= 75) * 100
  group_summary <- rbind(
    group_summary,
    data.frame(
      Group = g,
      Effort_Mean = round(effort_stats['mean'], 4),
      Effort_SD = round(effort_stats['sd'], 4),
      Effort_CI_Lower = round(effort_stats['ci_lower'], 4),
      Effort_CI_Upper = round(effort_stats['ci_upper'], 4),
      Quality_Mean = round(quality_stats['mean'], 4),
      Quality_SD = round(quality_stats['sd'], 4),
      Quality_CI_Lower = round(quality_stats['ci_lower'], 4),
      Quality_CI_Upper = round(quality_stats['ci_upper'], 4),
      Success_Rate = round(success_rate, 4),
      stringsAsFactors = FALSE
    )
  )
}
write.csv(group_summary, summary_csv_path, row.names = FALSE)

# ------------------------------------------------------------------
# Exploratory AI-assisted time-sensitivity exponent (alpha)
# Derived from the observed AI-assisted conditions (G3 nominal, G4
# compressed) using the descriptive model E_AI ~ (t_o / t_d)^alpha.
# ------------------------------------------------------------------
compression_ratio <- 0.6  # 3.5h compressed cap ~ 0.6 * 6.0h nominal

g3_effort <- df$Effort_Hours[df$Group == 'G3']
g4_effort <- df$Effort_Hours[df$Group == 'G4']

alpha_from_means <- function(e3, e4) {
  log(mean(e4) / mean(e3)) / log(1 / compression_ratio)
}

alpha_point <- alpha_from_means(g3_effort, g4_effort)

set.seed(42)
bootstrap_reps <- 10000

# (a) Group-summary bootstrap: resample group means under the observed
#     cell means and standard deviations.
n_cell <- length(g3_effort)
boot_summary <- replicate(bootstrap_reps, {
  s3 <- max(rnorm(1, mean(g3_effort), sd(g3_effort) / sqrt(n_cell)), 1e-6)
  s4 <- max(rnorm(1, mean(g4_effort), sd(g4_effort) / sqrt(n_cell)), 1e-6)
  log(s4 / s3) / log(1 / compression_ratio)
})
ci_summary <- as.numeric(quantile(boot_summary, c(0.025, 0.975)))

# (b) Individual-level bootstrap: resample the actual participant-level
#     effort vectors (preferred when participant-level data are available).
boot_individual <- replicate(bootstrap_reps, {
  s3 <- mean(sample(g3_effort, n_cell, replace = TRUE))
  s4 <- mean(sample(g4_effort, n_cell, replace = TRUE))
  log(s4 / s3) / log(1 / compression_ratio)
})
ci_individual <- as.numeric(quantile(boot_individual, c(0.025, 0.975)))

alpha_output <- data.frame(
  Metric = c('AI_Time_Sensitivity_Exponent_GroupBootstrap',
             'AI_Time_Sensitivity_Exponent_IndividualBootstrap'),
  Point_Estimate = round(c(alpha_point, alpha_point), 3),
  CI_Lower = round(c(ci_summary[1], ci_individual[1]), 3),
  CI_Upper = round(c(ci_summary[2], ci_individual[2]), 3),
  Bootstrap_Replicates = c(bootstrap_reps, bootstrap_reps),
  Basis = c('Table 4 effort summaries for G3 and G4 (group-level bootstrap)',
            'Participant-level G3/G4 session effort (individual-level bootstrap)'),
  stringsAsFactors = FALSE
)
write.csv(alpha_output, alpha_csv_path, row.names = FALSE)

# Null-hypothesis tests reported in the manuscript (Section 5.5).
p_vs_zero <- mean(boot_individual <= 0) * 2          # two-sided vs alpha = 0
p_vs_four <- mean(boot_individual >= 4) * 2          # two-sided vs alpha = 4
p_vs_zero <- min(p_vs_zero, 1)
p_vs_four <- min(max(p_vs_four, 1 / bootstrap_reps), 1)

pdf(figure_path, width = 8, height = 6, family = 'serif')
hist(
  boot_individual,
  breaks = 30,
  col = 'gray85',
  border = 'white',
  main = 'Bootstrap Distribution of the Exploratory AI-Assisted Exponent',
  xlab = expression(hat(alpha)[AI])
)
abline(v = alpha_point, lwd = 2)
abline(v = ci_individual, lwd = 2, lty = 2)
mtext(
  sprintf('Point estimate = %.2f | 95%% bootstrap CI [%.2f, %.2f]',
          alpha_point, ci_individual[1], ci_individual[2]),
  side = 3, line = 0.5, cex = 0.85
)
dev.off()

cat('Saved:', basename(summary_csv_path), '\n')
cat('Saved:', basename(alpha_csv_path), '\n')
cat('Saved:', basename(figure_path), '\n')
cat(sprintf('alpha point estimate = %.3f\n', alpha_point))
cat(sprintf('group-bootstrap 95%% CI [%.3f, %.3f]\n', ci_summary[1], ci_summary[2]))
cat(sprintf('individual-bootstrap 95%% CI [%.3f, %.3f]\n', ci_individual[1], ci_individual[2]))
