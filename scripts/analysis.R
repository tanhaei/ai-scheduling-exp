# ==========================================
# analysis.R: Nonlinear Least-Squares Fitting for Putnam Model
# ==========================================
# This script fits the AI-adjusted Putnam model to the experimental data.
# Model: E = E_o * (t_o / t_d)^alpha
# Fits separate models for Traditional (G1/G2) and AI-Assisted (G3/G4) groups.
# Outputs: alpha_fitting.csv with alpha, 95% CI, and R².
# Author: Mohammad Tanhaei
# Date: 2025-12-04
# ==========================================

# Load required libraries
library(nls)      # For nonlinear least-squares
library(dplyr)    # For data manipulation
library(broom)    # For tidy summaries (optional)

# Read the dataset
df <- read.csv("../data/dataset_48.csv")
cat("Dataset loaded: n =", nrow(df), "samples\n")

# Add normalized schedule time (t_d / t_o): 1.0 for Nominal, 0.6 for Compressed
df$td_to <- ifelse(df$Group %in% c("G2", "G4"), 0.6, 1.0)

# Aggregate effort means by unique t_d (2 points per model: t=1 and t=0.6)
trad_agg <- df[df$Group %in% c("G1", "G2"), ] %>%
  group_by(td_to) %>%
  summarise(Effort = mean(Effort_Hours), .groups = 'drop')
cat("Traditional aggregate:\n")
print(trad_agg)

ai_agg <- df[df$Group %in% c("G3", "G4"), ] %>%
  group_by(td_to) %>%
  summarise(Effort = mean(Effort_Hours), .groups = 'drop')
cat("AI aggregate:\n")
print(ai_agg)

# Define the Putnam model function
putnam_model <- function(td, alpha, Eo) {
  Eo * (1 / td)^alpha
}

# Fit Traditional Model (start with alpha=3.8, Eo=5.0)
cat("\nFitting Traditional Model...\n")
fit_trad <- tryCatch({
  nls(Effort ~ putnam_model(td_to, alpha, Eo), 
      data = trad_agg, 
      start = list(alpha = 3.8, Eo = 5.0),
      trace = TRUE,
      control = nls.control(maxiter = 100, warnOnly = TRUE))
}, error = function(e) {
  cat("Warning: Fitting issues for Traditional. Using OLS approximation.\n")
  # Fallback: Linearize log(E) = log(Eo) + alpha * log(1/td)
  lm(log(Effort) ~ log(1 / td_to), data = trad_agg)
})

# Fit AI-Assisted Model (start with alpha=1.8, Eo=3.0)
cat("\nFitting AI-Assisted Model...\n")
fit_ai <- tryCatch({
  nls(Effort ~ putnam_model(td_to, alpha, Eo), 
      data = ai_agg, 
      start = list(alpha = 1.8, Eo = 3.0),
      trace = TRUE,
      control = nls.control(maxiter = 100, warnOnly = TRUE))
}, error = function(e) {
  cat("Warning: Fitting issues for AI. Using OLS approximation.\n")
  lm(log(Effort) ~ log(1 / td_to), data = ai_agg)
})

# Extract parameters (handle lm fallback)
extract_alpha <- function(fit) {
  if (inherits(fit, "nls")) {
    alpha <- coef(fit)["alpha"]
    se <- summary(fit)$parameters["alpha", "Std. Error"]
  } else {  # lm fallback
    alpha <- coef(fit)[2]  # Slope is alpha
    se <- summary(fit)$coefficients[2, 2]
  }
  ci <- alpha + c(-1.96 * se, 1.96 * se)
  return(list(alpha = alpha, ci_lower = ci[1], ci_upper = ci[2], se = se))
}

alpha_trad <- extract_alpha(fit_trad)
alpha_ai <- extract_alpha(fit_ai)

# Calculate R²
calc_r2 <- function(fit, data) {
  if (inherits(fit, "nls")) {
    y_pred <- predict(fit)
  } else {
    y_pred <- exp(predict(fit))
  }
  y_obs <- data$Effort
  1 - sum((y_obs - y_pred)^2) / sum((y_obs - mean(y_obs))^2)
}

r2_trad <- calc_r2(fit_trad, trad_agg)
r2_ai <- calc_r2(fit_ai, ai_agg)

# Prepare output DataFrame
output <- data.frame(
  Model = c("Traditional", "AI-Assisted"),
  Alpha = c(alpha_trad$alpha, alpha_ai$alpha),
  Alpha_CI_Lower = c(alpha_trad$ci_lower, alpha_ai$ci_lower),
  Alpha_CI_Upper = c(alpha_trad$ci_upper, alpha_ai$ci_upper),
  R2 = c(r2_trad, r2_ai),
  stringsAsFactors = FALSE
)

# Save to CSV
write.csv(output, "alpha_fitting.csv", row.names = FALSE)
cat("\nFitting Results:\n")
print(output)
cat("\nCSV saved: alpha_fitting.csv\n")

# Optional: Plot fitted curves (requires ggplot2)
# library(ggplot2)
# t_seq <- seq(0.4, 1.2, length.out = 100)
# pred_trad <- predict(fit_trad, newdata = data.frame(td_to = t_seq))
# pred_ai <- predict(fit_ai, newdata = data.frame(td_to = t_seq))
# plot_data <- data.frame(t = t_seq, Trad = pred_trad, AI = pred_ai)
# ggplot(plot_data, aes(x = t)) + geom_line(aes(y = Trad, color = "Traditional")) + geom_line(aes(y = AI, color = "AI")) + labs(title = "Fitted Effort Curves")