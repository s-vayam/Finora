/**
 * Centralized API Configuration for Finora Frontend
 */

const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return 'http://127.0.0.1:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export const API_V1_PREFIX = '/api/v1';
export const DEFAULT_TIMEOUT_MS = 15000;
export const DEFAULT_COMPANY_ID = 'FINORA_DEMO';

export const API_ENDPOINTS = {
  health: `${API_V1_PREFIX}/health`,
  metaSummary: `${API_V1_PREFIX}/meta/data-summary`,
  customers: `${API_V1_PREFIX}/customers`,
  invoices: `${API_V1_PREFIX}/invoices`,
  payments: `${API_V1_PREFIX}/payments`,
  predictPaymentRisk: `${API_V1_PREFIX}/predict/payment-risk`,
  mlRiskStatus: `${API_V1_PREFIX}/ml/payment-risk/status`,
  mlRiskMetrics: `${API_V1_PREFIX}/ml/payment-risk/metrics`,
  cashflowHistory: `${API_V1_PREFIX}/cashflow/history`,
  cashflowPositionLatest: `${API_V1_PREFIX}/cashflow/position/latest`,
  cashflowPosition: `${API_V1_PREFIX}/cashflow/position`,
  cashflowForecast: `${API_V1_PREFIX}/cashflow/forecast`,
  cashflowAlerts: `${API_V1_PREFIX}/cashflow/alerts`,
  cashflowScenario: `${API_V1_PREFIX}/cashflow/scenario`,
  cashflowAssumptions: `${API_V1_PREFIX}/cashflow/expense-assumptions`,
  cashflowOverrides: `${API_V1_PREFIX}/cashflow/collection-overrides`,
  fxPairs: `${API_V1_PREFIX}/fx/pairs`,
  fxRatesCurrent: `${API_V1_PREFIX}/fx/rates/current`,
  fxRatesHistory: `${API_V1_PREFIX}/fx/rates/history`,
  fxModelsStatus: `${API_V1_PREFIX}/fx/models/status`,
  fxModelsMetrics: `${API_V1_PREFIX}/fx/models/metrics`,
  fxForecast: `${API_V1_PREFIX}/fx/forecast`,
  fxForecastHistory: `${API_V1_PREFIX}/fx/forecasts/history`,
  fxExposure: `${API_V1_PREFIX}/fx/exposure`,
  fxScenario: `${API_V1_PREFIX}/fx/scenario`,
  fxScenarioHistory: `${API_V1_PREFIX}/fx/scenarios/history`,
} as const;
