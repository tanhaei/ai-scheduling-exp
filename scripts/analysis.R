# ==========================================
# analysis.R: Exploratory alpha estimation for the manuscript
# ==========================================
# Reproduces the manuscript-referenced exploratory estimate of the
# AI-assisted time-sensitivity exponent (alpha, Section 5.5), the
# group-level summary table (Table 4), and Figure 4.
#
# Notes on interpretation (consistent with the manuscript):
#   - alpha is an EXPLORATORY, task-specific descriptor, not a stable
#     parameter. Both bootstrap intervals include zero.
#   - The group-level estimate fits Eq. (2) to the observed AI-assisted
#     cell means (G3 nominal, G4 compressed); the participant-level
#     estimate uses a log-scale estimator with participant resampling.
#   - The schedule-compression ratio is the ACTUAL ratio of the two
#     conditions, t_d / t_o = 3.5 / 6.0 (Table 3), not the rounded 0.6
#     used descriptively in the text.
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
# Descriptive model (manuscript Eq. 2): E_AI ~ (t_o / t_d)^alpha,
# fitted to the observed AI-assisted conditions (G3 nominal, G4
# compressed). The compression ratio is the actual t_d / t_o = 3.5/6.
# ------------------------------------------------------------------
t_o <- 6.0
t_d <- 3.5
log_ratio <- log(t_o / t_d)

g3_effort <- df$Effort_Hours[df$Group == 'G3']
g4_effort <- df$Effort_Hours[df$Group == 'G4']
n_cell <- length(g3_effort)

# Group-level (plug-in) estimator: ratio of cell means.
alpha_group <- log(mean(g4_effort) / mean(g3_effort)) / log_ratio

# Participant-level (log-scale) estimator: difference of mean logs.
alpha_indiv <- (mean(log(g4_effort)) - mean(log(g3_effort))) / log_ratio

set.seed(42)
bootstrap_reps <- 100000

# (a) Group-summary bootstrap: resample cell means under the observed
#     means and standard errors (normal approximation). This is the
#     distribution shown in Figure 4.
boot_group <- replicate(bootstrap_reps, {
  s3 <- max(rnorm(1, mean(g3_effort), sd(g3_effort) / sqrt(n_cell)), 1e-6)
  s4 <- max(rnorm(1, mean(g4_effort), sd(g4_effort) / sqrt(n_cell)), 1e-6)
  log(s4 / s3) / log_ratio
})
ci_group <- as.numeric(quantile(boot_group, c(0.025, 0.975)))

# (b) Participant-level bootstrap: resample the raw effort vectors and
#     recompute the log-scale estimator.
boot_indiv <- replicate(bootstrap_reps, {
  s3 <- sample(g3_effort, n_cell, replace = TRUE)
  s4 <- sample(g4_effort, n_cell, replace = TRUE)
  (mean(log(s4)) - mean(log(s3))) / log_ratio
})
ci_indiv <- as.numeric(quantile(boot_indiv, c(0.025, 0.975)))

alpha_output <- data.frame(
  Metric = c('AI_Time_Sensitivity_Exponent_GroupBootstrap',
             'AI_Time_Sensitivity_Exponent_IndividualBootstrap'),
  Point_Estimate = round(c(alpha_group, alpha_indiv), 3),
  CI_Lower = round(c(ci_group[1], ci_indiv[1]), 3),
  CI_Upper = round(c(ci_group[2], ci_indiv[2]), 3),
  Bootstrap_Replicates = c(bootstrap_reps, bootstrap_reps),
  Basis = c('Cell means/SDs for G3 and G4 (group-level bootstrap, ratio-of-means estimator)',
            'Participant-level G3/G4 session effort (log-scale estimator, participant resampling)'),
  stringsAsFactors = FALSE
)
write.csv(alpha_output, alpha_csv_path, row.names = FALSE)

# Null-hypothesis tests reported in the manuscript (Section 5.5):
# Welch t tests on log-transformed session effort against alpha = 0
# (no schedule sensitivity) and alpha = 4 (classical project-scale value).
welch_log_test <- function(alpha0) {
  d <- mean(log(g4_effort)) - mean(log(g3_effort)) - alpha0 * log_ratio
  v3 <- var(log(g3_effort)) / n_cell
  v4 <- var(log(g4_effort)) / n_cell
  se <- sqrt(v3 + v4)
  dfree <- (v3 + v4)^2 / (v3^2 / (n_cell - 1) + v4^2 / (n_cell - 1))
  2 * pt(abs(d / se), df = dfree, lower.tail = FALSE)
}
p_vs_zero <- welch_log_test(0)
p_vs_four <- welch_log_test(4)

# Descriptive offloading factor implied by the nominal-schedule cells
# (manuscript Section 5.5): mu-hat = 1 - E(G3)/E(G1).
g1_effort <- df$Effort_Hours[df$Group == 'G1']
mu_hat <- 1 - mean(g3_effort) / mean(g1_effort)

# Figure 4: bootstrap distribution of the group-level exploratory
# exponent (the interval crossing zero motivates cautious
# interpretation; see manuscript Figure 4).
pdf(figure_path, width = 8, height = 6, family = 'serif')
hist(
  boot_group,
  breaks = 40,
  col = '#7fa8d9',
  border = 'white',
  main = expression(paste('Bootstrap distribution of ', alpha, ' (AI-assisted conditions)')),
  xlab = expression(paste('Estimated AI time-sensitivity exponent (', alpha, ')')),
  ylab = 'Bootstrap count'
)
abline(v = alpha_group, lwd = 2, lty = 2, col = '#1f4e8c')
abline(v = ci_group, lwd = 2, lty = 3, col = '#1f4e8c')
legend(
  'topright',
  legend = c(sprintf('Estimate: %.2f', alpha_group),
             sprintf('95%% CI: [%.2f, %.2f]', ci_group[1], ci_group[2])),
  lty = c(2, 3), lwd = 2, col = '#1f4e8c', bty = 'n'
)
dev.off()

cat('Saved:', basename(summary_csv_path), '\n')
cat('Saved:', basename(alpha_csv_path), '\n')
cat('Saved:', basename(figure_path), '\n')
cat(sprintf('alpha (group, plug-in)      = %.3f, 95%% bootstrap CI [%.3f, %.3f]\n',
            alpha_group, ci_group[1], ci_group[2]))
cat(sprintf('alpha (participant, log)    = %.3f, 95%% bootstrap CI [%.3f, %.3f]\n',
            alpha_indiv, ci_indiv[1], ci_indiv[2]))
cat(sprintf('Welch log-scale test vs alpha=0: p = %.3f\n', p_vs_zero))
cat(sprintf('Welch log-scale test vs alpha=4: p < 0.001 (exact %.1e)\n', p_vs_four))
cat(sprintf('mu-hat (offloading factor) = %.3f\n', mu_hat))
