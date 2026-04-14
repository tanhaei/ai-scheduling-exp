# ==========================================
# analysis.R: Exploratory alpha estimation for the manuscript
# ==========================================
# This script reproduces the manuscript-referenced exploratory estimate
# of the AI-assisted time-sensitivity exponent (alpha) and generates the
# corresponding sensitivity figure.
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

mean_ci <- function(x) {
  n <- length(x)
  m <- mean(x)
  s <- sd(x)
  se <- s / sqrt(n)
  ci <- m + c(-1, 1) * 1.96 * se
  c(mean = m, sd = s, ci_lower = ci[1], ci_upper = ci[2])
}

groups <- c('G1', 'G2', 'G3', 'G4')
group_summary <- data.frame(
  Group = character(0),
  Effort_Mean = numeric(0),
  Effort_SD = numeric(0),
  Effort_CI_Lower = numeric(0),
  Effort_CI_Upper = numeric(0),
  Quality_Mean = numeric(0),
  Quality_SD = numeric(0),
  Quality_CI_Lower = numeric(0),
  Quality_CI_Upper = numeric(0),
  Success_Rate = numeric(0),
  stringsAsFactors = FALSE
)

for (g in groups) {
  subset_df <- df[df$Group == g, ]
  effort_stats <- mean_ci(subset_df$Effort_Hours)
  quality_stats <- mean_ci(subset_df$Quality_Score)
  group_summary <- rbind(
    group_summary,
    data.frame(
      Group = g,
      Effort_Mean = effort_stats['mean'],
      Effort_SD = effort_stats['sd'],
      Effort_CI_Lower = effort_stats['ci_lower'],
      Effort_CI_Upper = effort_stats['ci_upper'],
      Quality_Mean = quality_stats['mean'],
      Quality_SD = quality_stats['sd'],
      Quality_CI_Lower = quality_stats['ci_lower'],
      Quality_CI_Upper = quality_stats['ci_upper'],
      Success_Rate = mean(subset_df$Success) * 100,
      stringsAsFactors = FALSE
    )
  )
}
write.csv(group_summary, summary_csv_path, row.names = FALSE)

# Manuscript-referenced summary values from Table 1 (G3/G4)
reported_mean_g3 <- 3.06
reported_sd_g3 <- 0.57
reported_mean_g4 <- 3.42
reported_sd_g4 <- 0.45
reported_n <- 12
compression_ratio <- 0.6

alpha_point <- log(reported_mean_g4 / reported_mean_g3) / log(1 / compression_ratio)

set.seed(42)
bootstrap_reps <- 10000
sampled_g3 <- pmax(rnorm(bootstrap_reps, mean = reported_mean_g3, sd = reported_sd_g3 / sqrt(reported_n)), 1e-6)
sampled_g4 <- pmax(rnorm(bootstrap_reps, mean = reported_mean_g4, sd = reported_sd_g4 / sqrt(reported_n)), 1e-6)
alpha_boot <- log(sampled_g4 / sampled_g3) / log(1 / compression_ratio)
alpha_ci <- as.numeric(quantile(alpha_boot, c(0.025, 0.975)))

alpha_output <- data.frame(
  Metric = 'AI_Time_Sensitivity_Exponent',
  Point_Estimate = round(alpha_point, 3),
  CI_Lower = round(alpha_ci[1], 3),
  CI_Upper = round(alpha_ci[2], 3),
  Bootstrap_Replicates = bootstrap_reps,
  Basis = 'Manuscript Table 1 effort summaries for G3 and G4',
  stringsAsFactors = FALSE
)
write.csv(alpha_output, alpha_csv_path, row.names = FALSE)

pdf(figure_path, width = 8, height = 6, family = 'serif')
hist(
  alpha_boot,
  breaks = 30,
  col = 'gray85',
  border = 'white',
  main = 'Bootstrap Distribution of the Exploratory AI-Assisted Exponent',
  xlab = expression(hat(alpha)[AI])
)
abline(v = alpha_point, lwd = 2)
abline(v = alpha_ci, lwd = 2, lty = 2)
mtext(
  sprintf('Point estimate = %.2f | 95%% bootstrap CI [%.2f, %.2f]', alpha_point, alpha_ci[1], alpha_ci[2]),
  side = 3,
  line = 0.5,
  cex = 0.85
)
dev.off()

cat('Saved:', basename(summary_csv_path), '\n')
cat('Saved:', basename(alpha_csv_path), '\n')
cat('Saved:', basename(figure_path), '\n')
