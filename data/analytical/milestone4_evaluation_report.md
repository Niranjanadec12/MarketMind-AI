# MarketMind AI — Milestone 4 Evaluation Report

## 1. Purpose

This report consolidates the recorded evaluation results for forecasting,
customer segmentation, churn prediction, product recommendations, and
anomaly detection.

Metrics are reported as measured. The evaluation methods differ between
modules, so the results should not be compared directly across modules.

## 2. Sales Forecasting

### Evaluation setup
- Test period: 2018-04-13 onward.
- Training data ended: 2018-04-12.
- Test observations: 139.
- Metrics: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE),
  and R-squared (R2).

### Results

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| XGBoost | 6644.2445 | 8252.8331 | 0.5361 |
| Random Forest | 5961.1877 | 7784.5598 | 0.5873 |
| Prophet | 10054.2631 | 13127.8120 | -0.1738 |

### Interpretation and limitations
- Random Forest had the lowest MAE and RMSE and the highest R2 among
  these three evaluated models.
- Prophet's negative R2 indicates that it performed worse than predicting
  the test-set mean under the R2 comparison.
- Prophet produced a warning because yearly seasonality was enabled with
  less than approximately two years of training history.
- These results apply to the recorded test period and do not guarantee
  performance on future periods.

## 3. Customer Segmentation

### Evaluation setup
- Segmentation algorithms: K-Means and hierarchical clustering.
- Number of clusters: 3 for each model.
- Customers segmented: 93,357.
- K-Means silhouette evaluation sample: up to 2,000.
- Hierarchical clustering used a 5,000-customer training sample, then
  assigned all customers using the learned cluster centers.
- Hierarchical silhouette evaluation sample: up to 2,000.

### Results

| Method | Silhouette Score |
|---|---:|
| K-Means | 0.4569 |
| Hierarchical clustering | 0.4330 |

### Interpretation and limitations
- K-Means had the higher recorded silhouette score.
- Silhouette scores were computed on samples, not every customer.
- The hierarchical model was trained on a subset and applied to the
  full customer population.
- Silhouette scores indicate cluster separation under the chosen
  representation; they do not by themselves prove business usefulness.

## 4. Churn Prediction

### Evaluation setup
- Model: Logistic Regression.
- Feature window: 180 days.
- Snapshot cutoff: 2018-05-31.
- Label window: 90 days, ending 2018-08-29.
- Total customers: 38,454.
- Training customers: 30,763.
- Test customers: 7,691.
- Split: 80/20 with random_state=42 and stratification.
- Target definition: churn = 1 when no purchase occurred during the
  label window; churn = 0 when at least one purchase occurred.

### Held-out results

| Metric | Result |
|---|---:|
| Accuracy | 0.601612 |
| Precision | 0.994167 |
| Recall | 0.602435 |
| F1 score | 0.750245 |
| ROC-AUC | 0.583718 |
| Average precision | 0.994342 |
| Churn label rate | 0.993213 |

### Interpretation and limitations
- The recorded churn label rate was 99.3213%, indicating severe class
  imbalance under the current target definition.
- High precision and average precision must be interpreted in the
  context of this very high positive-class prevalence.
- ROC-AUC of 0.583718 indicates weak discrimination between the two
  classes.
- Accuracy alone is not sufficient for judging this model.
- The label definition and class distribution should be reviewed before
  relying on the model for customer-retention decisions.

## 5. Product Recommendation Engine

### Evaluation setup
- Evaluation method: deterministic, single-item historical holdout.
- Eligible customers: 5,334.
- Evaluation customers: 1,000.
- One previously observed product was hidden per evaluation customer.
- Recommendations evaluated per customer: 5.
- Training interactions after holding out products: 98,785.
- Held-out interactions: 1,000.

### Held-out results

| Metric | Result |
|---|---:|
| Precision@5 | 0.022200 |
| Recall@5 | 0.111000 |
| Hit rate@5 | 0.111000 |
| Customers with a hit in top 5 | 111 / 1,000 |
| Recommendations returned | 5,000 |
| Customers with already-owned products recommended | 0 |

### Interpretation and limitations
- The engine recovered the hidden product in the top five for 111 of
  1,000 evaluation customers.
- Precision@5 corresponds to 111 matches across 5,000 recommendation
  slots.
- Recall@5 equals hit rate@5 because only one relevant product was
  held out per customer.
- This is a historical recovery test, not a temporal test of future
  preferences.
- The results do not establish that the engine will predict future
  purchases accurately.

## 6. Anomaly Detection

### Evaluation setup
- Evaluation type: synthetic benchmark, not verified real-world labels.
- Source dataset: sales analytics.
- Source records available: 112,650.
- Training records: 8,000 unmodified records.
- Unmodified test records treated as normal: 1,000.
- Synthetic anomalies injected: 500.
- Features used: 9.
- Statistical thresholds learned from training data: 6.
- Isolation Forest contamination setting: 0.01.
- Synthetic anomalies were created by increasing two randomly selected
  eligible numerical features to extreme positive values.
- Statistical thresholds were calculated from the training data.
- The alert-combination policy included Isolation Forest flags,
  statistical flags, and sales domain rules.

### Synthetic test results

| Metric | Result |
|---|---:|
| Detection accuracy | 0.748667 (74.87%) |
| False-positive rate | 0.006000 (0.60%) |
| Detection rate / Recall | 0.258000 (25.80%) |
| True positives | 129 |
| True negatives | 994 |
| False positives | 6 |
| False negatives | 371 |

### Interpretation and limitations
- The detector identified 129 of the 500 injected anomalies.
- The low false-positive rate is specific to this benchmark and does not
  guarantee a low real-world false-positive rate.
- Detection recall was 25.80%, so most injected anomalies were missed.
- Unmodified test records were treated as normal for scoring, even
  though some may contain genuine anomalies.
- Synthetic anomalies were deliberately extreme and may not resemble
  real fraud, unusual customer activity, or inventory problems.
- These metrics must not be described as verified real-world detection
  accuracy.
- The existing alert output is not independently labelled ground truth.

## 7. Overall Summary

| Module | Main recorded result | Important caveat |
|---|---|---|
| Forecasting | Random Forest: MAE 5961.1877, R2 0.5873 | One recorded held-out period |
| Segmentation | K-Means silhouette: 0.4569 | Scores computed on samples |
| Churn prediction | F1: 0.750245; ROC-AUC: 0.583718 | Severe class imbalance |
| Recommendations | Precision@5: 0.0222; Recall@5: 0.1110 | Single-item historical holdout |
| Anomaly detection | Accuracy: 74.87%; FPR: 0.60% | Synthetic benchmark; recall 25.80% |

## 8. Conclusion and Next Steps

The evaluation runs have produced measurable baseline results for all five
modules. The results should be retained as a baseline rather than treated
as proof of production readiness.

Recommended follow-up work:
1. Investigate churn target imbalance and assess metrics for both classes.
2. Evaluate recommendations using a time-based holdout and broader
   relevance criteria if suitable data is available.
3. Improve anomaly detection recall and test against independently
   reviewed real anomalies when labels become available.
4. Re-evaluate forecasting over additional time periods.
5. Preserve the evaluation setup and random seeds so future results can
   be compared consistently.

No production-readiness claim is made by this report.
