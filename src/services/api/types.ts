/**
 * Authoritative TypeScript API types matching Finora backend Pydantic models
 */

// Generic Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages?: number;
}

// Company & Customer
export interface CompanyBackend {
  company_id: string;
  name: string;
  currency: string;
  created_at: string;
}

export interface CustomerBackend {
  customer_id: string;
  company_id: string;
  name: string;
  country: string;
  currency: string;
  payment_terms_days: number;
  credit_limit: string | number;
  created_at: string;
  contact_email?: string;
}

// Invoices
export type InvoiceStatusBackend = 'DRAFT' | 'ISSUED' | 'SENT' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';
export type InvoiceDueStatus = 'UPCOMING' | 'DUE_SOON' | 'OVERDUE' | 'SETTLED';

export interface InvoiceBackend {
  invoice_id: string;
  invoice_number: string;
  company_id: string;
  customer_id: string;
  customer_name?: string;
  customer_country?: string;
  currency: 'USD' | 'EUR' | 'GBP' | 'INR';
  invoice_amount: string | number;
  amount_paid?: string | number;
  outstanding_balance?: string | number;
  inr_equivalent?: string | number;
  issue_date: string;
  due_date: string;
  payment_terms_days: number;
  status: InvoiceStatusBackend;
  due_status?: InvoiceDueStatus;
  description?: string;
  shipping_reference?: string;
  contact_email?: string;
  created_at: string;
  updated_at?: string;
}

export interface InvoiceCreateRequest {
  company_id?: string;
  customer_id: string;
  invoice_number: string;
  currency: 'USD' | 'EUR' | 'GBP' | 'INR';
  invoice_amount: number | string;
  issue_date: string;
  due_date: string;
  description?: string;
  shipping_reference?: string;
  payment_terms_days?: number;
}

export interface InvoiceUpdateRequest {
  description?: string;
  due_date?: string;
  shipping_reference?: string;
}

// Payments
export interface PaymentBackend {
  payment_id: string;
  invoice_id: string;
  company_id: string;
  payment_date: string;
  amount: string | number;
  currency: string;
  payment_method: string;
  reference_number?: string;
  notes?: string;
  created_at: string;
}

export interface PaymentCreateRequest {
  payment_date: string;
  amount: number | string;
  currency?: string;
  payment_method?: string;
  reference_number?: string;
  notes?: string;
}

export interface PaymentHistoryResponse {
  invoice_id: string;
  invoice_amount: string | number;
  amount_paid: string | number;
  outstanding_balance: string | number;
  status: InvoiceStatusBackend;
  payments: PaymentBackend[];
}

// ML Payment Risk
export type PaymentRiskCategory = 'LOW' | 'MEDIUM' | 'HIGH';

export interface PaymentRiskPrediction {
  prediction_id: string;
  invoice_id: string;
  late_probability: number;
  risk_category: PaymentRiskCategory;
  predicted_delay_days: number;
  expected_delay_days: number;
  estimated_payment_date: string;
  model_version: string;
  created_at: string;
  cold_start?: boolean;
}

export interface PaymentRiskStatusResponse {
  is_loaded: boolean;
  model_version: string;
  classifier_type: string;
  regressor_type: string;
  optimal_threshold: number;
}

// Cash Flow & Liquidity
export interface CashPositionBackend {
  snapshot_id: string;
  company_id: string;
  as_of_date: string;
  balance_amount: string | number;
  currency: string;
  minimum_cash_threshold: string | number;
  source: string;
  notes?: string;
  created_at: string;
}

export interface CashPositionCreateRequest {
  company_id?: string;
  as_of_date: string;
  balance_amount: number | string;
  currency?: string;
  minimum_cash_threshold?: number | string;
  source?: string;
  notes?: string;
}

export interface MonthlyCashflowBackend {
  id: number;
  company_id: string;
  year: number;
  month: number;
  opening_balance: string | number;
  total_inflows: string | number;
  total_outflows: string | number;
  net_cash_flow: string | number;
  closing_balance: string | number;
  is_historical: boolean;
}

export interface DailyProjectionItem {
  date: string;
  inflow: number;
  outflow: number;
  net: number;
  closing_balance: number;
  minimum_threshold: number;
  is_breach: boolean;
}

export interface CashflowForecastResponse {
  forecast_run_id: string;
  company_id: string;
  as_of_date: string;
  horizon_days: number;
  opening_balance: number;
  total_inflow: number;
  total_outflow: number;
  net_cash_flow: number;
  closing_balance: number;
  minimum_projected_balance: number;
  minimum_projected_date: string;
  has_liquidity_breach: boolean;
  daily_projections: DailyProjectionItem[];
  model_version?: string;
  generated_at?: string;
}

export interface CashflowAlertItem {
  alert_id: string;
  alert_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  action_needed?: string;
  projected_date?: string;
  shortfall_amount?: number;
}

export interface CashflowScenarioRequest {
  company_id?: string;
  as_of_date?: string;
  horizon_days?: number;
  customer_delay_days?: number;
  expense_increase_percent?: number;
  collection_haircut_percent?: number;
}

export interface CashflowScenarioResponse {
  baseline: CashflowForecastResponse;
  scenario: CashflowForecastResponse;
  difference_in_closing_balance: number;
  liquidity_pressure: string;
}

export interface ExpenseAssumptionBackend {
  assumption_id: string;
  company_id: string;
  category: string;
  monthly_amount: string | number;
  currency: string;
  growth_rate_pct: string | number;
  is_active: boolean;
}

export interface CollectionOverrideBackend {
  override_id: string;
  invoice_id: string;
  company_id: string;
  expected_collection_date: string;
  notes?: string;
}

// FX Intelligence
export interface FxPairItem {
  pair: string;
  base: string;
  quote: string;
  unit: number;
  description: string;
  models_available: boolean;
  skill_status: string;
}

export interface FxPairsResponse {
  base_currency: string;
  supported_pairs: FxPairItem[];
  other_known_currencies: string[];
  attribution_notice: string;
}

export type FxFreshnessStatus = 'FRESH_INDICATIVE' | 'DELAYED_INDICATIVE' | 'STALE' | 'MARKET_CLOSED';

export interface FxRateBackend {
  currency_pair: string;
  base_currency: string;
  quote_currency: string;
  rate_value: number;
  provider: string;
  provider_effective_at?: string;
  fetched_at: string;
  market_session?: string;
  freshness_status: FxFreshnessStatus;
  is_stale: boolean;
  is_derived: boolean;
  source_notice?: string;
}

export interface FxForecastRequestBackend {
  company_id?: string;
  currency_pair: string;
  horizon_sessions?: number;
  target_date?: string;
  as_of_date?: string;
}

export interface FxForecastBackend {
  forecast_id: string;
  company_id: string;
  currency_pair: string;
  anchor_rate: string | number;
  anchor_date: string;
  target_date: string;
  horizon_sessions: number;
  predicted_rate: string | number;
  percentage_movement: string | number;
  predicted_direction: 'UP' | 'DOWN' | 'NEUTRAL';
  direction_probabilities: {
    UP: number;
    DOWN: number;
    NEUTRAL: number;
  };
  prediction_range_80?: [string | number, string | number];
  prediction_range_95?: [string | number, string | number];
  latest_indicative_rate?: string | number;
  latest_indicative_timestamp?: string;
  model_version: string;
  skill_status: string;
  is_validated: boolean;
  freshness_warning?: string;
  attribution: string;
}

export interface FxExposureItemBackend {
  currency: string;
  receivable_amount: string | number;
  payable_amount: string | number;
  net_exposure: string | number;
  benchmark_rate: string | number;
  predicted_rate?: string | number;
  estimated_receivable_impact: string | number;
  estimated_payable_impact: string | number;
  net_estimated_impact: string | number;
  status: string;
}

export interface FxExposureResponseBackend {
  company_id: string;
  as_of_date: string;
  base_currency: string;
  supported_exposures: FxExposureItemBackend[];
  unsupported_exposures: FxExposureItemBackend[];
  total_net_estimated_impact: string | number;
  disclaimer: string;
}

export interface FxScenarioRequestBackend {
  company_id?: string;
  currency_pair: string;
  benchmark_rate?: number | string;
  scenario_type?: 'PERCENTAGE_MOVEMENT' | 'TARGET_RATE';
  percentage_change?: number | string;
  scenario_rate?: number | string;
}

export interface FxScenarioResponseBackend {
  scenario_id: string;
  company_id: string;
  currency_pair: string;
  benchmark_rate: string | number;
  scenario_rate: string | number;
  percentage_change: string | number;
  receivable_exposure: string | number;
  payable_exposure: string | number;
  estimated_receivable_impact: string | number;
  estimated_payable_impact: string | number;
  net_estimated_impact: string | number;
  source: string;
  comparison_with_ml?: {
    forecast_id: string;
    ml_horizon_sessions: number;
    ml_predicted_rate: number;
    ml_percentage_movement: number;
    ml_predicted_direction: string;
    scenario_percentage_change: number;
    divergence_bps: number;
    aligned_direction: boolean;
  };
  created_at?: string;
  disclaimer?: string;
}

// Data Summary
export interface DataSummaryResponse {
  company_id: string;
  company_name: string;
  currency: string;
  counts: {
    customers: number;
    invoices: number;
    paid_invoices: number;
    open_invoices: number;
    expenses: number;
    payments: number;
    cash_transactions: number;
    monthly_cashflows: number;
  };
  aggregates: {
    total_invoiced: number;
    total_paid: number;
    total_outstanding: number;
    total_expenses: number;
  };
}

export interface HealthResponse {
  status: string;
  database: string;
  app: string;
  version: string;
  environment: string;
}

