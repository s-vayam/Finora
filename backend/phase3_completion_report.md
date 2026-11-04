# FINORA — PHASE 3 COMPLETION REPORT
## Machine Learning Payment Risk Engine

**Phase**: Phase 3  
**Status**: Completed & Verified  
**Date**: November 4, 2026  
**Scope**: Machine Learning Dataset Preprocessing, Leakage-Safe Feature Engineering, Supervised Model Training & Evaluation, Serialization, Database Migration, and FastAPI Inference Integration.

---

## 1. Executive Summary

Phase 3 introduces an intelligent, machine-learning-driven payment risk prediction engine to Finora. The engine predicts whether an unpaid invoice is likely to experience delayed settlement, quantifies the conditional delay in days, calculates the probability-weighted expected delay, and estimates the realistic nominal payment date.

All development has been strictly isolated to the `backend/` directory. Zero changes were made to the frontend code (`src/`), ensuring 100% preservation of existing UI screens, navigation, and mock data. All 35 pre-existing automated tests continue to pass without regression, and 18 new automated tests covering all ML stages were implemented and verified (total: 53 passing tests).

---

## 2. Stage 3A: Dataset Profiling, Cleaning & Preprocessing

The model is trained on the Kaggle Payment Date Dataset (`dataset.csv`), containing 50,000 corporate invoice records.

### Key Data Findings & Quality Assessment
- **Raw File**: `backend/data/raw/payment_date_dataset/dataset.csv` (SHA-256: `139482bdc3325a734474d08f48ceee71ab67c84b106f2a0c0fe9479d71be8431`).
- **Exact Duplicates Dropped**: 1,161 duplicate rows identified and removed (leaving 48,839 unique records).
- **Target Formulation & Segregation**:
  - **Closed/Cleared Invoices (`isOpen == 0`)**: 39,158 records with valid `clear_date`. Used for supervised training and validation.
  - **Open Invoices (`isOpen == 1`)**: 9,681 records with null `clear_date`. Segregated for batch testing and future inference.
  - **Payment Delay Calculation**: `payment_delay_days = (clear_date - due_date).days`.
  - **Binary Classification Target**: `is_late = 1` if `payment_delay_days > 0` else `0`. Late rate across cleared dataset is 41.93% (16,418 late invoices vs 22,740 on-time/early invoices).
  - **Regression Target**: `late_delay_days = payment_delay_days` conditional strictly on `is_late == 1` (mean late delay: 6.46 days, median: 2.0 days, max: 204 days).
- **Processed Deliverables**:
  - `backend/ml/preprocessing.py`
  - `backend/ml/processed/cleared_invoices.csv` (39,158 records)
  - `backend/ml/processed/open_invoices.csv` (9,681 records)
  - `backend/ml/metadata/dataset_provenance.json`
  - Automated tests: `backend/tests/test_ml_preprocessing.py` (3 tests passed).

---

## 3. Stage 3B: Leakage-Safe Feature Engineering

To guarantee zero data leakage between past and future events, a strict chronological constraint was enforced for all feature extraction.

### Feature Architecture
1. **Invoice-Level Features**:
   - `invoice_amount` (`total_open_amount`)
   - `log_invoice_amount` (`np.log1p(invoice_amount)`)
   - `terms_days` (`due_date - posting_date`)
   - `baseline_to_due_days` (`due_date - baseline_create_date`)
   - `invoice_month`, `invoice_quarter`, `invoice_dayofweek`
   - `due_month`, `due_dayofweek`
   - Categorical: `currency`, `business_code`, `cust_payment_terms`
2. **Customer Historical Features (Zero-Leakage Constraint)**:
   - For an invoice posted on date $T$, historical behavior is derived **strictly** from earlier cleared invoices for that customer where `clear_date <= T`.
   - The invoice itself is explicitly excluded from its own history ($O(1)$ exclusion).
   - High-performance prefix-sum and binary search (`bisect_right`) architecture processes all 39,158 records in ~3.4 seconds.
   - Extracted customer signals:
     - `cust_prev_invoice_count`: number of prior cleared payments
     - `cust_prev_late_rate`: proportion of prior payments that were late
     - `cust_prev_ontime_rate`: `1.0 - cust_prev_late_rate`
     - `cust_prev_avg_delay`: historical average payment delay in days
     - `cust_prev_max_delay`: historical maximum delay in days
     - `is_cold_start`: binary indicator for new customers with zero prior payment history
3. **Dual Offline & Online Implementation**:
   - `compute_offline_customer_history`: fast prefix-sum algorithm for training datasets.
   - `compute_live_customer_history`: queries Finora SQLite database (`invoices` and `payments` tables) with `payment_date <= invoice.invoice_date` filter, ensuring identical feature representations between training and production.
4. **Deliverables**:
   - `backend/ml/feature_schema.py`
   - `backend/ml/customer_history_features.py`
   - `backend/ml/features.py`
   - Automated tests: `backend/tests/test_ml_features.py` (4 tests passed).

---

## 4. Stage 3C & 3D: Model Training, Evaluation & Serialization

### Chronological Partitioning
The dataset was split chronologically by `posting_date` to prevent look-ahead bias:
- **Training Set (70%)**: 27,410 invoices (11,709 late invoices)
- **Validation Set (15%)**: 5,874 invoices (2,394 late invoices)
- **Test Set (15%)**: 5,874 invoices (2,315 late invoices)

### Classification Model Comparison
| Model | Val ROC-AUC | Val PR-AUC | Test ROC-AUC | Test PR-AUC | Test F1 (Opt Thresh) |
|---|---|---|---|---|---|
| **Dummy (Prior)** | 0.5000 | 0.4076 | 0.5000 | 0.3941 | 0.5654 |
| **Logistic Regression** | 0.7712 | 0.7105 | 0.7811 | 0.7289 | 0.6512 |
| **Random Forest (Champion)** | **0.8014** | **0.7512** | **0.8100** | **0.7685** | **0.6794** |

- **Optimal Classification Threshold**: Tuned on validation split to **0.38** (balanced precision 0.595, recall 0.792, F1 0.679).
- **Test Brier Score**: 0.1721.

### Regression Model Comparison (Trained on Late Subset Only)
| Model | Val MAE (Days) | Val RMSE (Days) | Test MAE (Days) | Test RMSE (Days) |
|---|---|---|---|---|
| **Dummy (Mean)** | 5.21 | 11.45 | 5.12 | 11.02 |
| **Random Forest** | 5.14 | 11.02 | 5.08 | 10.74 |
| **Ridge (Champion)** | **4.98** | **10.42** | **4.895** | **10.087** |

- Non-negative post-processing constraint: `max(0.0, y_pred)` enforced.
- Test Median Absolute Error: 3.05 days.

### Top Feature Importances (Random Forest Classifier)
1. `num__cust_prev_ontime_rate`: 22.50%
2. `num__cust_prev_late_rate`: 14.80%
3. `num__cust_prev_avg_delay`: 12.85%
4. `num__due_dayofweek`: 8.38%
5. `num__invoice_dayofweek`: 6.18%
6. `num__cust_prev_invoice_count`: 4.68%
7. `num__baseline_to_due_days`: 3.65%
8. `num__terms_days`: 3.15%

Customer historical behavior accounts for > 54% of total predictive weight.

### Serialized Artifacts (`backend/ml/artifacts/`)
- `feature_pipeline.joblib`: fitted scikit-learn `ColumnTransformer`.
- `payment_classifier.joblib`: trained champion `RandomForestClassifier`.
- `payment_delay_regressor.joblib`: trained champion `Ridge` regressor.
- `model_metadata.json`: hyperparameters, versioning, split metadata.
- `evaluation_metrics.json`: comprehensive evaluation metrics across models and splits.
- `feature_importance.json`: feature ranking summaries.
- `test_evaluation_report.json`: open invoices inference and test performance report.

---

## 5. Stage 3E: Database Migration & FastAPI Inference Integration

### Database Architecture (`ml_predictions` Table)
Alembic migration `002_create_ml_predictions_table.py` was authored and applied cleanly to `backend/data/database/finora.db`.

```sql
CREATE TABLE ml_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id VARCHAR(50) NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    prediction_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50) NOT NULL,
    predicted_late_probability FLOAT NOT NULL,
    risk_category VARCHAR(20) NOT NULL,
    predicted_delay_days FLOAT NOT NULL,
    expected_delay_days FLOAT NOT NULL,
    estimated_payment_date DATE NOT NULL,
    features_snapshot TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_ml_predictions_invoice_id ON ml_predictions(invoice_id);
CREATE INDEX ix_ml_predictions_prediction_timestamp ON ml_predictions(prediction_timestamp);
```

### Business Eligibility Rules
- Predictions are strictly allowed on **UNPAID open invoices** only.
- Inactive/ineligible invoices return **HTTP 409 Conflict**:
  - `PAID` invoice: rejected with clear explanation that invoice is already settled.
  - `CANCELLED` invoice: rejected as cancelled invoices do not carry payment risk.
  - `PARTIALLY_PAID` invoice: rejected as partial payment has already occurred.
- Non-existent invoice returns **HTTP 404 Not Found**.

### Risk Categorization & Outputs
- **Risk Categories**:
  - `LOW`: `predicted_late_probability < 0.35`
  - `MEDIUM`: `0.35 <= predicted_late_probability <= 0.65`
  - `HIGH`: `predicted_late_probability > 0.65`
- **Expected Delay**: `prob * predicted_delay_days`
- **Estimated Payment Date**: `due_date + round(expected_delay_days)`

### API Endpoints Implemented
1. `GET /api/v1/ml/payment-risk/status`: Returns model readiness, version (`v1.0.0`), model types, and optimal threshold.
2. `GET /api/v1/ml/payment-risk/metrics`: Returns test metrics (ROC-AUC, PR-AUC, F1, MAE) and top feature importances.
3. `POST /api/v1/predict/payment-risk`: Accepts `{"invoice_id": "..."}`, extracts customer history, runs inference, persists `MLPrediction`, and returns 201 Created.
4. `GET /api/v1/invoices/{invoice_id}/payment-risk/latest`: Retrieves the most recent prediction for an invoice (404 if none).
5. `GET /api/v1/invoices/{invoice_id}/payment-risk/history`: Retrieves the complete chronological audit log of predictions for that invoice.

---

## 6. Verification and Quality Assurance

### 1. Automated Test Suite
- Ran `pytest backend/tests -v`:
  - **Total Tests**: 53 passed (0 failed, 0 skipped).
  - **Phase 1 & 2 Existing Tests**: 35 passed.
  - **Phase 3 New Tests**: 18 passed:
    - `test_ml_preprocessing.py`: 3 passed.
    - `test_ml_features.py`: 4 passed.
    - `test_ml_training.py`: 3 passed.
    - `test_ml_artifacts.py`: 3 passed.
    - `test_ml_prediction_apis.py`: 5 passed.

### 2. Phase 2 Database Integrity Audit
- Ran `python backend/scripts/audit_phase2_integrity.py`:
  - **Result**: PASSED with 100% integrity across all 5 checks.
  - 873 paid invoices match payments sum (INR 122,169,067.90).
  - 873 payments link 1:1 with valid cash transactions.
  - 0 duplicate payments.
  - 26 open invoices have 0 payments.
  - 36 monthly cash flows identical to baseline CSVs.

### 3. Frontend Preservation Check
- Ran `npm run build`:
  - Built cleanly in 6.41 seconds with zero errors.
  - Directory `src/` and all frontend files are completely untouched.

### 4. Git Security Check
- Raw Kaggle dataset (`backend/data/raw/payment_date_dataset/`) is strictly ignored via `.gitignore` and not tracked in git.

---

## 7. Deliverables Checklist

| Deliverable | Location | Status |
|---|---|---|
| Raw Data Inspection Script | `backend/ml/data_inspection.py` | Completed |
| Data Quality Report | `backend/ml/data_quality_report.md` | Completed |
| Dataset Profile JSON | `backend/ml/dataset_profile.json` | Completed |
| Preprocessing Pipeline | `backend/ml/preprocessing.py` | Completed |
| Processed Cleared Invoices | `backend/ml/processed/cleared_invoices.csv` | Completed |
| Processed Open Invoices | `backend/ml/processed/open_invoices.csv` | Completed |
| Dataset Provenance JSON | `backend/ml/metadata/dataset_provenance.json` | Completed |
| Feature Schema | `backend/ml/feature_schema.py` | Completed |
| Customer History Features | `backend/ml/customer_history_features.py` | Completed |
| Feature Transformation Pipeline | `backend/ml/features.py` | Completed |
| Training Configuration | `backend/ml/training/training_config.py` | Completed |
| Classifier Training & Selection | `backend/ml/training/train_classifier.py` | Completed |
| Regressor Training & Selection | `backend/ml/training/train_regressor.py` | Completed |
| Master Training Script | `backend/scripts/train_payment_models.py` | Completed |
| Master Evaluation Script | `backend/scripts/evaluate_payment_models.py` | Completed |
| Serialized Classifier | `backend/ml/artifacts/payment_classifier.joblib` | Completed |
| Serialized Regressor | `backend/ml/artifacts/payment_delay_regressor.joblib` | Completed |
| Serialized Feature Pipeline | `backend/ml/artifacts/feature_pipeline.joblib` | Completed |
| Model Metadata JSON | `backend/ml/artifacts/model_metadata.json` | Completed |
| Evaluation Metrics JSON | `backend/ml/artifacts/evaluation_metrics.json` | Completed |
| Feature Importance JSON | `backend/ml/artifacts/feature_importance.json` | Completed |
| Alembic Migration (002) | `backend/alembic/versions/002_create_ml_predictions_table.py` | Applied |
| MLPrediction SQLAlchemy Model | `backend/app/models/ml_prediction.py` | Completed |
| Prediction Pydantic Schemas | `backend/app/schemas/prediction.py` | Completed |
| Prediction Service Layer | `backend/app/services/payment_prediction_service.py` | Completed |
| Prediction FastAPI Router | `backend/app/routers/predictions.py` | Completed |
| 18 New Unit & Integration Tests | `backend/tests/test_ml_*.py` | 18 Passed |

---

## 8. Transition to Phase 4

Phase 3 is complete and verified. Per strict project guidelines, Phase 4 (Cash Flow Forecasting Engine) will only begin upon explicit user request.
