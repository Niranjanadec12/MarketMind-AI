# MarketMind AI — Milestone 4 Model Evaluation Report

## 1. Objective

Evaluate the forecasting and customer segmentation models using quantitative metrics before proceeding to the next milestone tasks.

## 2. Forecasting Evaluation

### Evaluation setup

- Input dataset: `data/analytical/daily_revenue_prophet.csv`
- Total historical observations: 696
- Train/test split: chronological, 80% training and 20% testing
- Training period ends: 2018-04-12
- Testing period: 2018-04-13 to 2018-08-29
- Test observations: 139
- Models evaluated: Random Forest, XGBoost, Prophet
- Metrics: MAE, RMSE, R² Score

### Results

| Model | MAE | RMSE | R² Score |
|---|---:|---:|---:|
| Random Forest | 5961.1877 | 7784.5598 | 0.5873 |
| XGBoost | 6644.2445 | 8252.8331 | 0.5361 |
| Prophet | 10054.2631 | 13127.8120 | -0.1738 |

### Interpretation

Random Forest achieved the lowest MAE and RMSE and the highest R² Score among the three evaluated models.

XGBoost was the second-best model according to these metrics.

Prophet had the highest forecast errors and a negative R² Score on the test period, indicating that it performed worse than a baseline predictor using the mean of the actual test values.

### Forecasting limitations

- Prophet issued a warning that yearly seasonality may be unstable because the training history contains fewer than approximately two years of observations.
- These results represent one chronological test period and do not establish performance on every future period.
- Forecasting errors are expressed in the revenue units of the input dataset.

## 3. Customer Segmentation Evaluation

### Features

The clustering features were:

- `purchase_frequency`
- `purchase_value`
- `customer_activity`

`customer_activity` represents recency in days: the difference between a customer's last delivered purchase date and the latest purchase date in the dataset.

The features were standardized using `StandardScaler`.

### Results

| Method | Clusters | Fitting sample | Silhouette Score evaluation sample | Silhouette Score |
|---|---:|---:|---:|---:|
| K-Means | 3 | 93,357 customers | 2,000 customers | 0.4569 |
| Hierarchical | 3 | 5,000 customers | 2,000 customers | 0.4330 |

### Interpretation

Both methods produced positive Silhouette Scores, suggesting some separation between clusters in the standardized feature space.

K-Means obtained the higher estimated score in this evaluation. However, the scores are sample-based estimates and should not be treated as proof that K-Means is categorically superior for business use.

The hierarchical model was fitted to a representative sample of 5,000 customers. The existing pipeline then assigned the remaining customers to the nearest cluster center.

### Segmentation limitations

- Silhouette Scores were estimated using samples of up to 2,000 customers.
- The hierarchical method clusters only a 5,000-customer sample directly.
- Cluster separation alone does not establish the commercial usefulness of the resulting segments.

## 4. Evaluation Summary

- Forecasting MAE and RMSE were calculated for all three forecasting models.
- R² Scores were calculated for all three forecasting models.
- Silhouette Scores were calculated for K-Means and hierarchical clustering.
- Random Forest was the strongest forecasting model in this test.
- K-Means had a slightly higher estimated Silhouette Score than hierarchical clustering.
- Results and limitations were documented for future reference.

## 5. Next Steps

Review the results, preserve the existing model outputs, and continue with the next milestone tasks only after confirming that these evaluation results meet the project requirements.
