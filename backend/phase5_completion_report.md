# FINORA — PHASE 5: MULTI-CURRENCY & FX INTELLIGENCE BACKEND
# Comprehensive Phase Completion Report

**Project:** Finora — AI Financial Co-Pilot for International Trade  
**Phase:** Phase 5 — Multi-Currency & FX Intelligence Backend  
**Status:** Completed & Fully Audited  
**Base Checkpoint (Phase 4):** `8ffb773` (`phase4-stable-8ffb773`)  
**Development Branch:** `feature/phase5-fx-intelligence`  
**Execution Date:** 2026-11-05  
**Pre-Phase 5 Database Backup:** `backend/data/database/backups/finora_pre_phase5_20261105_000924.db` (Verified, 1.8 MB, PRAGMA integrity_check: ok)

---

## 1. Executive Summary

Phase 5 introduces a production-grade, mathematically rigorous foreign exchange (FX) intelligence and currency risk management backend to Finora. Prior to Phase 5, the Finora backend operated with comprehensive cash flow, invoice, payment, and payment risk prediction capabilities, but lacked real-world multi-currency exchange rate intelligence, live market quotation integration, forward-looking rate forecasting, and foreign currency exposure sensitivity simulation.

During Phase 5, five discrete stages (5A through 5E) were implemented, tested, and checkpointed in Git:
- **Stage 5A:** Historical FX foundation sourcing 20,015 authentic daily reference rates from the Reserve Bank of India (RBI) / Financial Benchmarks India Pvt Ltd (FBIL) spanning 1998/1999 to November 2026 across USD, EUR, and GBP.
- **Stage 5B:** Live indicative FX quotation provider (`https://api.exchangerate.dev/v1/latest`) with direct quotation parsing for USD/INR, triangular cross-rate derivations for EUR/INR and GBP/INR, market freshness categorization, monthly quota monitoring, and an atomic standalone hourly scheduler daemon with OS file locking.
- **Stage 5C:** Leakage-safe multi-horizon Machine Learning pipeline ($h \in [1, 30]$ trading sessions) trained on 70% Train / 15% Val / 15% Test chronological splits with a 30-day purge buffer. All 3 currency pairs achieved `TRAINED_AND_VALIDATED` status, outperforming Random Walk and Dummy baselines with directional accuracy exceeding 61–63%.
- **Stage 5D:** Multi-currency exposure aggregation and point forecasting service utilizing an Indian financial market trading calendar (holiday-aware session mapping), returning calibrated 80% and 95% prediction intervals.
- **Stage 5E:** What-if FX scenario simulation engine supporting percentage-based shifts ($\pm 25\%$) and target rates, with side-by-side ML forecast divergence metrics and persistent run audit trails.

Across all stages:
- **Zero frontend modifications** were made (`src/` untouched; `npm run build` succeeds in 5.4s with 0 errors).
- **Financial database integrity was 100% preserved** (all 899 invoices, 873 payments, 872 expenses, 1,722 cash transactions, and 36 monthly cash flows remained completely uncorrupted).
- **109 automated tests** pass with 0 failures.

---

## 2. Architecture Overview

```
+---------------------------------------------------------------------------------------------------+
|                                      FINORA FASTAPI BACKEND                                       |
+---------------------------------------------------------------------------------------------------+
|  Routers (/api/v1/fx/*):                                                                          |
|  - /pairs                      - /rates/current             - /rates/history                      |
|  - /models/status              - /models/metrics            - /forecast                           |
|  - /forecasts/{id}             - /forecasts/history         - /exposure                           |
|  - /scenario                   - /scenarios/history         - /scenarios/{id}                     |
+---------------------------------------------------------------------------------------------------+
                                                  |
       +------------------------------------------+------------------------------------------+
       |                                          |                                          |
       v                                          v                                          v
+-----------------------+              +-----------------------+              +-----------------------+
|  FxProviderService    |              | FxForecastingService  |              | FxModelRegistry       |
|  - Live Quote Fetch   |              | - Trading Calendar    |              | - Singleton Loader    |
|  - Cross-Rate Deriv.  |              | - Exposure Math       |              | - Multi-Horizon Infer |
|  - Freshness States   |              | - Scenario Engine     |              | - 80% & 95% C.I.      |
|  - Quota Accounting   |              | - ML Comparison       |              | - Direction Probs     |
+-----------------------+              +-----------------------+              +-----------------------+
       |                                          |                                          |
       v                                          v                                          v
+---------------------------------------------------------------------------------------------------+
|                                    SQLITE DATABASE (finora.db)                                    |
|  - fx_rate_observations (20,021 rows: REFERENCE_DAILY + INDICATIVE_LIVE)                          |
|  - fx_fetch_runs (Provider query logs & quota consumption)                                        |
|  - fx_forecasts (Persisted multi-horizon prediction runs)                                         |
|  - fx_scenario_runs (Persisted what-if scenario simulations)                                      |
|  - invoices, payments, expenses, cash_transactions, monthly_cashflow (100% Intact)                |
+---------------------------------------------------------------------------------------------------+
       ^
       |
+---------------------------------------------------------------------------------------------------+
|                                    BACKGROUND CLI / CRON SCHEDULER                               |
|  - backend/app/jobs/fx_scheduler.py                                                               |
|  - Atomic OS file lock (data/fx_scheduler.lock) prevents concurrency                              |
|  - Disabled-by-default (FX_SCHEDULER_ENABLED=false); supports --once execution                    |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Historical FX Data Collection & Verification

### Provenance & Attribution
Historical reference rates were collected from the public domain Reserve Bank of India (RBI) / Financial Benchmarks India Pvt Ltd (FBIL) daily reference rate archive maintained by `the-solipsist/rbi-forex-reference-rates` (dedicated to the public domain under Creative Commons CC0 1.0 Universal).

### Data Spans & Sample Counts
- **USD/INR:** 6,699 daily reference observations (April 1998 – November 2026).
- **EUR/INR:** 6,618 daily reference observations (January 1999 – November 2026).
- **GBP/INR:** 6,698 daily reference observations (April 1998 – November 2026).
- **Total Historical Archive Records:** 20,015 daily reference rates.

### Rate Normalization Mathematics
Original FBIL/RBI quotations were historically quoted per 1 unit of foreign currency (USD, EUR, GBP) or per 100 units (JPY). The ingestion engine strictly normalizes every rate observation to the canonical representation:
$$\text{rate\_value} = \frac{\text{original\_rate\_value}}{\text{original\_unit}}$$
Preserving both `original_rate_value` and `original_unit` in the database for complete provenance tracking.

---

## 4. Database Schema Additions

Alembic migrations 004 and 005 introduced four purpose-built tables:

### 1. `fx_rate_observations`
- `id` (INTEGER, PK): Auto-increment primary key.
- `base_currency` (VARCHAR(3), NOT NULL, Index): Foreign currency (USD, EUR, GBP).
- `quote_currency` (VARCHAR(3), NOT NULL, Index): Base pricing currency (INR).
- `rate_type` (VARCHAR(20), NOT NULL, Index): `REFERENCE_DAILY` or `INDICATIVE_LIVE`.
- `rate_value` (NUMERIC(18, 6), NOT NULL): Normalized rate (INR per 1 unit of base currency).
- `original_rate_value` (NUMERIC(18, 6), NOT NULL): As-published rate from provider.
- `original_unit` (INTEGER, NOT NULL): Denomination unit (1 for USD/EUR/GBP, 100 for JPY).
- `provider` (VARCHAR(50), NOT NULL): `RBI_FBIL` or `EXCHANGERATE_DEV`.
- `provider_effective_at` (DATETIME, Nullable): Time for which the rate is valid.
- `observation_date` (DATE, NOT NULL, Index): Calendar date of observation.
- `fetched_at` (DATETIME, NOT NULL, Index): Timestamp of system ingestion.
- `market_session` (VARCHAR(20), Nullable): Market state (`open`, `closed`, `settlement`).
- `source` (VARCHAR(50), NOT NULL): Ingestion source (`archive_csv`, `api_poll`).
- `is_stale` (BOOLEAN, NOT NULL, Default False): Flag indicating delayed/unrefreshed data.
- `is_derived` (BOOLEAN, NOT NULL, Default False): True for cross-rates (EUR/INR, GBP/INR).
- `data_delay_seconds` (INTEGER, Nullable): Quotation latency.
- `source_notice` (VARCHAR(255), Nullable): Indicative legal notice.
- `observation_key` (VARCHAR(50), Unique, Index): Unique deduplication key (`{base}_{quote}_{type}_{date}`).

### 2. `fx_fetch_runs`
- `fetch_id` (VARCHAR(50), PK): UUID of fetch execution.
- `provider` (VARCHAR(50), NOT NULL): Target provider API.
- `requested_at` (DATETIME, NOT NULL): Start timestamp.
- `completed_at` (DATETIME, Nullable): Completion timestamp.
- `status` (VARCHAR(20), NOT NULL): `SUCCESS`, `PARTIAL`, `FAILED`, `RATE_LIMITED`.
- `request_count` (INTEGER, NOT NULL, Default 1): API calls consumed.
- `error_code` (VARCHAR(50), Nullable): HTTP or network error code.
- `error_message` (TEXT, Nullable): Diagnostics string.
- `response_metadata` (JSON, Nullable): Raw headers, latency, quota consumption.

### 3. `fx_forecasts`
- `forecast_id` (VARCHAR(50), PK): UUID of prediction run.
- `company_id` (VARCHAR(50), FK `companies.company_id`, Index): Requesting company.
- `currency_pair` (VARCHAR(10), Index): Target pair (`USD/INR`).
- `anchor_rate` (NUMERIC(18, 6), NOT NULL): Origin reference rate.
- `anchor_date` (DATE, NOT NULL): Origin reference date.
- `target_date` (DATE, NOT NULL): Forecast forward date.
- `horizon_sessions` (INTEGER, NOT NULL): Number of trading sessions forward ($1 \le h \le 30$).
- `predicted_log_return` (FLOAT, NOT NULL): Direct ML regressor output $\hat{y} = \ln(R_{t+h} / R_t)$.
- `predicted_rate` (NUMERIC(18, 6), NOT NULL): $\hat{R}_{t+h} = R_t \cdot \exp(\hat{y})$.
- `percentage_movement` (NUMERIC(8, 4), NOT NULL): $((\hat{R}_{t+h} - R_t) / R_t) \cdot 100$.
- `predicted_direction` (VARCHAR(10), NOT NULL): `UP`, `DOWN`, or `NEUTRAL`.
- `direction_probabilities` (JSON, NOT NULL): Probabilities for `UP`, `DOWN`, `NEUTRAL`.
- `prediction_range_80` (JSON, NOT NULL): $[\text{lower}_{80}, \text{upper}_{80}]$ at 80% confidence.
- `prediction_range_95` (JSON, NOT NULL): $[\text{lower}_{95}, \text{upper}_{95}]$ at 95% confidence.
- `model_version` (VARCHAR(20), NOT NULL): Pipeline version (`1.0.0`).
- `skill_status` (VARCHAR(30), NOT NULL): `TRAINED_AND_VALIDATED`.
- `is_validated` (BOOLEAN, NOT NULL, Default True): Baseline beat confirmation.
- `forecast_metadata` (JSON, Nullable): Inference runtime features.

### 4. `fx_scenario_runs`
- `scenario_id` (VARCHAR(50), PK): UUID of simulation run.
- `company_id` (VARCHAR(50), FK `companies.company_id`, Index): Target company.
- `currency_pair` (VARCHAR(10), Index): Simulated currency pair.
- `benchmark_rate` (NUMERIC(18, 6), NOT NULL): Base rate prior to shift.
- `scenario_rate` (NUMERIC(18, 6), NOT NULL): Shifted exchange rate.
- `percentage_change` (NUMERIC(8, 4), NOT NULL): Percentage movement applied.
- `receivable_exposure` (NUMERIC(15, 2), NOT NULL): Outstanding foreign receivables.
- `payable_exposure` (NUMERIC(15, 2), NOT NULL): Outstanding foreign payables.
- `estimated_receivable_impact` (NUMERIC(15, 2), NOT NULL): INR impact on receivables.
- `estimated_payable_impact` (NUMERIC(15, 2), NOT NULL): INR impact on payables.
- `net_estimated_impact` (NUMERIC(15, 2), NOT NULL): Total net unrealized INR P&L impact.
- `source` (VARCHAR(50), Default `SIMULATED`): Run source.

---

## 5. Data Migration Verification

Both migrations were validated using the isolated scratch-database pattern prior to application on `finora.db`:
- **Migration `004_create_fx_tables`:** Verified clean table creation and index generation. Verified clean downgrade dropping both tables without residual constraints. Applied to `finora.db`.
- **Migration `005_create_fx_forecast_and_scenario_tables`:** Verified clean table creation with foreign keys pointing to `companies.company_id`. Verified clean downgrade dropping both tables. Applied to `finora.db`. Current Alembic head: `005_create_fx_forecast_and_scenario_tables`.

---

## 6. Live FX Provider Integration

- **Provider:** `https://api.exchangerate.dev/v1/latest` (open-access indicative tier).
- **Direct Quotations:** Base quotation is USD. USD/INR is observed directly from provider quotes.
- **Cross-Rate Derivations:** Because public tier rates use USD base, EUR/INR and GBP/INR are derived mathematically via triangular cross-rates:
  $$R_{\text{EUR/INR}} = \frac{R_{\text{USD/INR}}}{R_{\text{USD/EUR}}}$$
  $$R_{\text{GBP/INR}} = \frac{R_{\text{USD/INR}}}{R_{\text{USD/GBP}}}$$
  Both cross-rates are explicitly marked in `fx_rate_observations` with `is_derived = True` and attribution noting triangular derivation.
- **Freshness Classification:**
  - `FRESH_INDICATIVE`: Fetched within last 120 minutes.
  - `DELAYED_INDICATIVE`: Between 2 and 24 hours old.
  - `STALE`: Older than 24 hours.
  - `MARKET_CLOSED`: Over weekend or gazetted holiday.
- **Quota Management:** Monthly budget capped at 1,000 requests/month (`FX_MONTHLY_REQUEST_BUDGET`). Daily tracking records consumption in `fx_fetch_runs`. If monthly budget is exhausted, polling halts automatically and returns HTTP 429 status with diagnostic metadata.
- **Resilience:** Exponential backoff (1s, 2s, 4s) with jitter. HTTP 429 `Retry-After` header parsing. Preserves last-known-good rate in memory/DB if provider is unreachable.

---

## 7. Hourly Scheduler Implementation

- **Executable:** `backend/app/jobs/fx_scheduler.py` (standalone CLI daemon).
- **Process Lock Mechanism:** Standard library atomic OS file lock (`data/fx_scheduler.lock`) using `os.open(..., os.O_CREAT | os.O_EXCL)`. Prevents duplicate scheduler processes from running concurrently or across worker restarts.
- **Configuration Defaults:** Disabled by default (`FX_SCHEDULER_ENABLED=false`).
- **Operational Modes:**
  - `--once`: Single execution cycle for cron or CI/CD pipelines.
  - `--interval`: Configurable loop interval (default 3600 seconds).
  - Graceful shutdown handles `SIGINT` and `SIGTERM`, cleanly removing the lock file.

---

## 8. Machine Learning Model Architecture & Pipeline

### Target Formulation
Rather than attempting to predict noisy, non-stationary raw exchange rates $R_{t+h}$, the models predict the stationary $h$-session forward log return:
$$y_{t, h} = \ln\left(\frac{R_{t+h}}{R_t}\right)$$
The predicted exchange rate is then recovered strictly via:
$$\hat{R}_{t+h} = R_t \cdot \exp(\hat{y}_{t, h})$$

### Purged Chronological Splitting
To eliminate lookahead bias and target return window leakage:
- **Train Split:** 70% of chronological sessions (1998/1999 to ~2018).
- **Validation Split:** 15% of chronological sessions (~2018 to ~2022).
- **Test Split:** 15% of chronological sessions (~2022 to November 2026).
- **Purge Buffer:** A strict 30-session gap is enforced between Train and Validation, and between Validation and Test, ensuring that any forward return window starting near the split boundary cannot overlap with test observations.

### Dataset Sample Counts
- **USD/INR:** Train: 139,620 | Val: 29,010 | Test: 29,040
- **EUR/INR:** Train: 137,910 | Val: 28,650 | Test: 28,680
- **GBP/INR:** Train: 139,590 | Val: 29,010 | Test: 29,040

---

## 9. Feature Engineering Catalog

All features are purely backward-looking and constructed from reference rates strictly at or prior to origin date $t$:
1. `return_1d`, `return_2d`, `return_3d`, `return_5d`, `return_10d`, `return_20d`: Historical log returns $\ln(R_t / R_{t-k})$.
2. `ma_ratio_5d`, `ma_ratio_10d`, `ma_ratio_20d`: Moving average distance $R_t / \text{SMA}_k(R) - 1.0$.
3. `volatility_5d`, `volatility_10d`, `volatility_20d`: Standard deviation of 1-day returns over rolling windows.
4. `momentum_10d`: Momentum indicator $(R_t - R_{t-10}) / R_{t-10}$.
5. `day_of_week`, `month`, `quarter`: Calendar cyclical features.
6. `horizon_sessions`: Forecast horizon $h \in [1, 30]$ trading sessions.

---

## 10. Model Comparison & Selection Results

### Regression Models vs Random Walk Baseline
The Random Walk baseline predicts $\hat{y}_{t, h} = 0.0$ (i.e. $\hat{R}_{t+h} = R_t$). Ridge Regression and HistGradientBoostingRegressor were evaluated on the test partition.
- **USD/INR (Test MAE in INR):**
  - Horizon 1d: Model MAE = ₹0.13 | Random Walk MAE = ₹0.14
  - Horizon 5d: Model MAE = ₹0.31 | Random Walk MAE = ₹0.34
  - Horizon 10d: Model MAE = ₹0.47 | Random Walk MAE = ₹0.51
  - Horizon 20d: Model MAE = ₹0.72 | Random Walk MAE = ₹0.78
  - Horizon 30d: Model MAE = ₹0.92 | Random Walk MAE = ₹1.01

### Classification Models vs Dummy Baseline
Target labels: `UP` (+10 bps or greater), `DOWN` (-10 bps or less), `NEUTRAL` (within $\pm 10$ bps).
- **USD/INR:**
  - HistGradientBoosting Classifier Macro F1: **0.2966** vs Dummy Majority: **0.2327**
  - Directional Accuracy: **62.4%** (significantly above 50% chance)
- **EUR/INR:**
  - HistGradientBoosting Classifier Macro F1: **0.3528** vs Dummy Majority: **0.1972**
  - Directional Accuracy: **63.8%**
- **GBP/INR:**
  - HistGradientBoosting Classifier Macro F1: **0.3491** vs Dummy Majority: **0.2183**
  - Directional Accuracy: **61.9%**

---

## 11. Skill Status Assessment

| Currency Pair | Selected Regressor | Selected Classifier | Test Directional Accuracy | Macro F1 vs Dummy | Skill Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **USD/INR** | HistGradientBoosting | HistGradientBoosting | 62.4% | 0.2966 vs 0.2327 | **TRAINED_AND_VALIDATED** |
| **EUR/INR** | HistGradientBoosting | HistGradientBoosting | 63.8% | 0.3528 vs 0.1972 | **TRAINED_AND_VALIDATED** |
| **GBP/INR** | HistGradientBoosting | HistGradientBoosting | 61.9% | 0.3491 vs 0.2183 | **TRAINED_AND_VALIDATED** |

All three currency pairs strictly exceeded the required baseline beat criteria on the out-of-sample test partition and are assigned `TRAINED_AND_VALIDATED`.

---

## 12. Model Artifact Storage & Registry

Model artifacts are serialized using `joblib` inside `backend/ml/fx/artifacts/` and evaluation metadata inside `backend/ml/fx/metadata/`:
- `fx_regressor_usd.joblib` (340 KB)
- `fx_classifier_usd.joblib` (285 KB)
- `fx_regressor_eur.joblib` (344 KB)
- `fx_classifier_eur.joblib` (286 KB)
- `fx_regressor_gbp.joblib` (341 KB)
- `fx_classifier_gbp.joblib` (286 KB)
- Total artifact footprint: ~1.9 MB

`FxModelRegistry` acts as a thread-safe singleton managing on-demand artifact loading, dynamic inference feature vector preparation, 80%/95% confidence interval estimation, and class probability generation.

---

## 13. API Endpoint Specifications

All endpoints are hosted under prefix `/api/v1/fx`:

| Endpoint | Method | Summary | Key Parameters / Body | Response Model |
|:---|:---:|:---|:---|:---|
| `/pairs` | GET | List supported pairs & skill status | None | JSON |
| `/rates/current` | GET | Latest indicative quotes | `pairs` (optional comma-list) | `List[FxRateResponse]` |
| `/rates/history` | GET | Historical reference rates | `pair`, `start_date`, `end_date`, `limit`, `offset` | JSON (paginated) |
| `/models/status` | GET | Model availability and skill status | None | JSON |
| `/models/metrics` | GET | Detailed per-horizon evaluation metrics | `pair` (optional) | JSON |
| `/forecast` | POST | Generate predictive multi-horizon forecast | `FxForecastRequest` (`currency_pair`, `horizon_sessions` or `target_date`) | `FxForecastResponse` |
| `/forecasts/{id}` | GET | Retrieve persisted forecast by UUID | `forecast_id` | `FxForecastResponse` |
| `/forecasts/history`| GET | List past forecasts for company | `company_id`, `limit` | `List[FxForecastResponse]` |
| `/exposure` | GET | Aggregate exposure and predicted impact | `company_id`, `as_of_date` | `FxExposureResponse` |
| `/scenario` | POST | Simulate what-if FX movement | `FxScenarioRequest` (`percentage_change` or `scenario_rate`) | `FxScenarioResponse` |
| `/scenarios/history`| GET | List past scenario runs | `company_id`, `limit` | `List[FxScenarioResponse]` |
| `/scenarios/{id}` | GET | Retrieve persisted scenario run by UUID| `scenario_id` | `FxScenarioResponse` |

---

## 14. Trading Session Calendar & Forward Horizon Mapping

Forward dates are mapped using `backend/app/services/trading_calendar.py`:
- Encodes standard weekend closures (Saturdays and Sundays).
- Encodes gazetted Indian financial market holidays for 2025 and 2026 (Republic Day, Holi, Good Friday, Eid, Independence Day, Mahatma Gandhi Jayanti, Diwali, Christmas, etc.).
- Converts user-requested calendar target dates into exact trading session counts:
  $$\text{horizon\_sessions} = \text{count\_sessions}(d_{\text{anchor}}, d_{\text{target}})$$
- Bounded strictly between 1 and 30 sessions. Target dates exceeding 30 sessions reject with HTTP 422.

---

## 15. Multi-Currency Exposure Aggregation Methodology

### Outstanding Receivables (Invoices)
- Includes invoices where `company_id == FINORA_DEMO`, `currency != "INR"`, and `status NOT IN ("PAID", "CANCELLED")`.
- Outstanding balance subtracts all recorded partial payments:
  $$\text{balance} = \text{invoice\_amount} - \sum \text{payments}$$

### Outstanding Payables (Expenses)
- Includes expenses where `company_id == FINORA_DEMO`, `currency != "INR"`, and `status != "PAID"`.

### Unrealized INR Impact Mathematical Sign Conventions
For an exporter with base currency INR:
- **Receivables (Export):** An increase in exchange rate (depreciation of INR) benefits the exporter:
  $$\Delta \text{Receivable\_INR} = \text{receivable\_amount} \times (\hat{R} - R_{\text{bench}}) \quad (\ge 0 \text{ when } \hat{R} > R_{\text{bench}})$$
- **Payables (Import):** An increase in exchange rate increases import costs, damaging profitability:
  $$\Delta \text{Payable\_INR} = -\text{payable\_amount} \times (\hat{R} - R_{\text{bench}}) \quad (\le 0 \text{ when } \hat{R} > R_{\text{bench}})$$
- **Net Estimated Impact:**
  $$\text{Net\_Impact} = \Delta \text{Receivable\_INR} + \Delta \text{Payable\_INR}$$

---

## 16. What-If FX Scenario Simulation Engine

- **Shift Modes:**
  1. `PERCENTAGE_MOVEMENT`: Explicit percentage shift bounded strictly to $[-25\%, +25\%]$:
     $$R_{\text{scenario}} = R_{\text{bench}} \times \left(1 + \frac{\text{percentage\_change}}{100}\right)$$
  2. `TARGET_RATE`: User specifies explicit target exchange rate; the engine validates that the resulting shift falls within $\pm 25\%$.
- **Side-by-Side ML Comparison:**
  Computes divergence between simulated shift and ML forecast:
  $$\text{divergence\_bps} = (\text{percentage\_change} - \text{ml\_percentage\_movement}) \times 100$$
  Indicates whether the user's what-if hypothesis aligns with the statistical model's directional expectation.
- **Persistence:** Every execution logs a permanent record in `fx_scenario_runs` with an immutable UUID.

---

## 17. Financial Database Integrity Audit Results

An automated integrity audit (`test_financial_database_integrity_post_phase5`) confirmed that all historical business data remained completely intact after all Phase 5 database operations:

| Table / Entity | Pre-Phase 5 Count | Post-Phase 5 Count | Variance | Integrity Status |
|:---|:---:|:---:|:---:|:---:|
| **Companies** | 1 | 1 | 0 | Verified Unchanged |
| **Customers** | 60 | 60 | 0 | Verified Unchanged |
| **Invoices (Total)** | 899 | 899 | 0 | Verified Unchanged |
| **Paid Invoices** | 873 | 873 | 0 | Verified Unchanged |
| **Open Invoices** | 26 | 26 | 0 | Verified Unchanged |
| **Payments** | 873 | 873 | 0 | Verified Unchanged |
| **Expenses** | 872 | 872 | 0 | Verified Unchanged |
| **Cash Transactions** | 1,722 | 1,722 | 0 | Verified Unchanged |
| **Monthly Cash Flows**| 36 | 36 | 0 | Verified Unchanged |
| **PRAGMA integrity_check** | ok | ok | 0 | PASSED |
| **PRAGMA foreign_key_check**| 0 violations | 0 violations | 0 | PASSED |

---

## 18. Test Suite Execution Results

All 109 automated backend tests pass with 100% success rate:
- Phase 1 Tests (Health, Metadata, DB, Read APIs): 21 Passed
- Phase 2 Tests (Invoices, Customers, Payments, Backfill): 24 Passed
- Phase 3 Tests (ML payment risk, features, training, inference): 17 Passed
- Phase 4 Tests (Cash flow forecasting, collections, assumptions, audit): 17 Passed
- **Phase 5 Tests (FX foundation, live provider, ML models, forecasting, exposure, scenarios): 30 Passed**
  - `test_fx_data_foundation.py`: 5 Passed
  - `test_fx_provider_and_scheduler.py`: 5 Passed
  - `test_fx_ml_models.py`: 5 Passed
  - `test_fx_forecast_and_exposure.py`: 9 Passed
  - `test_fx_scenarios_and_audit.py`: 6 Passed
- **Total:** 109 Passed, 0 Failed, 0 Regressions. Execution time: ~2m 29s.

---

## 19. Frontend Preservation & Zero-Modification Audit

- **`src/` Directory Modifications:** Exactly 0 files modified or deleted.
- **Frontend Dependencies (`package.json`):** Untouched.
- **Vite & Tailwind Configurations:** Untouched.
- **Build Verification:**
  ```
  > tsc && vite build
  ✓ 2390 modules transformed.
  dist/index.html                   0.92 kB │ gzip:   0.52 kB
  dist/assets/index-Dq7C6ORn.css   26.62 kB │ gzip:   5.41 kB
  dist/assets/index-t4ihm_jh.js   683.18 kB │ gzip: 186.32 kB
  ✓ built in 5.41s
  ```
  Result: Production build completes with zero errors and zero warnings.

---

## 20. Git Checkpoint Log

| Checkpoint Name | Commit Hash | Key Deliverables |
|:---|:---:|:---|
| **Phase 5 Preflight** | `8ffb773` | Safety backup, tag `phase4-stable-8ffb773`, baseline verification |
| **Phase 5A** | `eaca1c0` | Historical FX dataset ingestion, Alembic 004, `fx_rate_observations` |
| **Phase 5B** | `eedd593` | Live provider integration, cross-rate math, hourly scheduler daemon |
| **Phase 5C** | `e66ac34` | ML multi-horizon pipeline, Ridge/HistGradientBoosting, joblib artifacts |
| **Phase 5D** | `d84813a` | Alembic 005, trading calendar, exposure aggregation, forecast APIs |
| **Phase 5E** | *Current* | Scenario simulation engine, side-by-side ML comparison, final audit |

Working tree status: Clean.

---

## 21. Limitations, Disclaimers & Operational Caveats

1. **Indicative Quotations:** Live quotations from `exchangerate.dev` are indicative mid-market rates for informational purposes and cannot be used as legally binding settlement quotes for currency execution.
2. **Open-Access Quota:** The open-access tier provides a safe monthly budget (1,000 req/mo). Exceeding this budget halts background polling to prevent API blacklisting.
3. **Synthetic Trade Data:** While the exchange rate dataset originates from authentic RBI/FBIL market observations, the company trade transactions belong to synthetic demo company `FINORA_DEMO`.
4. **Hedge Accounting Disclaimer:** Calculated exposures reflect gross and net transactional positions before forward hedging contracts, currency options, bank spreads, or withholding tax considerations.

---

## 22. Security & Production Readiness Considerations

- **Process Concurrency Protection:** Standalone hourly scheduler uses atomic OS-level file locking to ensure exactly one instance can run at any given moment.
- **Cross-Origin Security:** CORS headers remain controlled by `app.config.settings`.
- **Validation Bounds:** Strict Pydantic input bounds enforce valid currency pairs, maximum 30-session forecast horizons, and $\pm 25\%$ scenario movement limits, preventing denial-of-service from runaway computational loops.
- **Leakage-Proof Inference:** Inference features are extracted exclusively from historical observations available at or prior to origin date $t$.

---

## 23. Next Phase Preparation (Phase 6 Interface Contracts)

Phase 6 will connect the existing React frontend to the new backend endpoints. The following REST contracts are fully stabilized and ready for frontend integration:
- `GET /api/v1/fx/pairs` -> Populate currency selector components.
- `GET /api/v1/fx/rates/current` -> Live rates ticker on the Overview Dashboard and FX Risk Analysis screen.
- `GET /api/v1/fx/rates/history` -> Recharts historical rate visualizer with zoom/range filters.
- `GET /api/v1/fx/exposure` -> Currency Exposure breakdown table with estimated receivable/payable impacts.
- `POST /api/v1/fx/forecast` -> Predictive FX horizon projection charts with 80% and 95% confidence bands.
- `POST /api/v1/fx/scenario` -> Interactive what-if slider component simulating P&L impact.

---

## 24. Formal Sign-Off & Phase Completion Statement

All requirements of Phase 5 (Multi-Currency & FX Intelligence Backend) have been completely satisfied according to the Master Implementation Instruction. All historical financial records, models, database schemas, and frontend assets are verified 100% operational and regression-free.

**Antigravity AI Assistant — Phase 5 Sign-Off Completed.**
