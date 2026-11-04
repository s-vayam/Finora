/**
 * Finora API Service Hub
 */

import { apiClient } from './client';
import { API_ENDPOINTS, DEFAULT_COMPANY_ID } from './config';
import {
  HealthResponse,
  DataSummaryResponse,
  CustomerBackend,
  InvoiceBackend,
  InvoiceCreateRequest,
  InvoiceUpdateRequest,
  PaymentBackend,
  PaymentCreateRequest,
  PaymentHistoryResponse,
  PaymentRiskPrediction,
  PaymentRiskStatusResponse,
  CashPositionBackend,
  CashPositionCreateRequest,
  CashPositionUpdateRequest,
  MonthlyCashflowBackend,
  CashflowForecastResponse,
  CashflowAlertItem,
  CashflowScenarioRequest,
  CashflowScenarioResponse,
  ExpenseAssumptionBackend,
  CollectionOverrideBackend,
  FxPairsResponse,
  FxRateBackend,
  FxForecastRequestBackend,
  FxForecastBackend,
  FxExposureResponseBackend,
  FxScenarioRequestBackend,
  FxScenarioResponseBackend,
  PaginatedResponse,
} from './types';

// Health & Metadata API
export const healthApi = {
  checkHealth: (signal?: AbortSignal) =>
    apiClient.get<HealthResponse>(API_ENDPOINTS.health, { signal }),

  getDataSummary: (companyId = DEFAULT_COMPANY_ID, signal?: AbortSignal) =>
    apiClient.get<DataSummaryResponse>(API_ENDPOINTS.metaSummary, {
      params: { company_id: companyId },
      signal,
    }),
};

// Customers API
export const customersApi = {
  listCustomers: (companyId = DEFAULT_COMPANY_ID, signal?: AbortSignal) =>
    apiClient.get<PaginatedResponse<CustomerBackend>>(API_ENDPOINTS.customers, {
      params: { company_id: companyId, page_size: 100 },
      signal,
    }),

  getCustomer: (customerId: string, signal?: AbortSignal) =>
    apiClient.get<CustomerBackend>(`${API_ENDPOINTS.customers}/${customerId}`, { signal }),
};

// Invoices API
export const invoicesApi = {
  listInvoices: (
    params?: {
      company_id?: string;
      customer_id?: string;
      status?: string;
      currency?: string;
      page?: number;
      page_size?: number;
    },
    signal?: AbortSignal
  ) =>
    apiClient.get<PaginatedResponse<InvoiceBackend>>(API_ENDPOINTS.invoices, {
      params: {
        company_id: DEFAULT_COMPANY_ID,
        page_size: 100,
        ...params,
      },
      signal,
    }),

  getInvoice: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.get<InvoiceBackend>(`${API_ENDPOINTS.invoices}/${invoiceId}`, { signal }),

  createInvoice: (data: InvoiceCreateRequest, signal?: AbortSignal) =>
    apiClient.post<InvoiceBackend>(API_ENDPOINTS.invoices, {
      company_id: DEFAULT_COMPANY_ID,
      ...data,
    }, { signal }),

  updateInvoice: (invoiceId: string, data: InvoiceUpdateRequest, signal?: AbortSignal) =>
    apiClient.patch<InvoiceBackend>(`${API_ENDPOINTS.invoices}/${invoiceId}`, data, { signal }),

  cancelInvoice: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.post<InvoiceBackend>(`${API_ENDPOINTS.invoices}/${invoiceId}/cancel`, undefined, { signal }),
};

// Payments API
export const paymentsApi = {
  recordPayment: (
    invoiceId: string,
    data: PaymentCreateRequest,
    idempotencyKey?: string,
    signal?: AbortSignal
  ) => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    return apiClient.post<PaymentBackend>(
      `${API_ENDPOINTS.invoices}/${invoiceId}/payments`,
      data,
      { headers, signal }
    );
  },

  getInvoicePayments: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.get<PaymentHistoryResponse>(`${API_ENDPOINTS.invoices}/${invoiceId}/payments`, { signal }),

  listPayments: (companyId = DEFAULT_COMPANY_ID, limit = 50, signal?: AbortSignal) =>
    apiClient.get<PaginatedResponse<PaymentBackend>>(API_ENDPOINTS.payments, {
      params: { company_id: companyId, page_size: limit },
      signal,
    }),
};

// Payment Risk ML API
export const predictionApi = {
  predictPaymentRisk: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.post<PaymentRiskPrediction>(
      API_ENDPOINTS.predictPaymentRisk,
      { invoice_id: invoiceId },
      { signal }
    ),

  getLatestPrediction: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.get<PaymentRiskPrediction>(
      `${API_ENDPOINTS.invoices}/${invoiceId}/payment-risk/latest`,
      { signal }
    ),

  getPredictionHistory: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.get<PaymentRiskPrediction[]>(
      `${API_ENDPOINTS.invoices}/${invoiceId}/payment-risk/history`,
      { signal }
    ),

  getMLStatus: (signal?: AbortSignal) =>
    apiClient.get<PaymentRiskStatusResponse>(API_ENDPOINTS.mlRiskStatus, { signal }),

  getMLMetrics: (signal?: AbortSignal) =>
    apiClient.get<Record<string, unknown>>(API_ENDPOINTS.mlRiskMetrics, { signal }),
};

// Cash Flow & Liquidity Intelligence API
export const cashflowApi = {
  getHistory: (companyId = DEFAULT_COMPANY_ID, signal?: AbortSignal) =>
    apiClient.get<MonthlyCashflowBackend[]>(API_ENDPOINTS.cashflowHistory, {
      params: { company_id: companyId },
      signal,
    }),

  getLatestPosition: (companyId = DEFAULT_COMPANY_ID, signal?: AbortSignal) =>
    apiClient.get<CashPositionBackend>(API_ENDPOINTS.cashflowPositionLatest, {
      params: { company_id: companyId },
      signal,
    }),

  createPosition: (data: CashPositionCreateRequest, signal?: AbortSignal) =>
    apiClient.post<CashPositionBackend>(
      API_ENDPOINTS.cashflowPosition,
      { company_id: DEFAULT_COMPANY_ID, ...data },
      { signal }
    ),

  updatePosition: (
    snapshotId: string,
    data: CashPositionUpdateRequest,
    signal?: AbortSignal
  ) =>
    apiClient.patch<CashPositionBackend>(
      `${API_ENDPOINTS.cashflowPosition}/${snapshotId}`,
      data,
      { signal }
    ),

  getForecast: (
    options?: { horizon_days?: number; as_of_date?: string; company_id?: string },
    signal?: AbortSignal
  ) =>
    apiClient.get<CashflowForecastResponse>(API_ENDPOINTS.cashflowForecast, {
      params: {
        company_id: DEFAULT_COMPANY_ID,
        horizon_days: options?.horizon_days || 30,
        as_of_date: options?.as_of_date,
      },
      signal,
    }),

  getAlerts: (
    options?: { company_id?: string; as_of_date?: string },
    signal?: AbortSignal
  ) =>
    apiClient.get<CashflowAlertItem[]>(API_ENDPOINTS.cashflowAlerts, {
      params: {
        company_id: DEFAULT_COMPANY_ID,
        as_of_date: options?.as_of_date,
      },
      signal,
    }),

  runScenario: (data: CashflowScenarioRequest, signal?: AbortSignal) => {
    const delay = data.payment_delay_days ?? data.customer_delay_days ?? 0;
    const expensePct = data.expense_increase_percentage ?? data.expense_increase_percent ?? 0;
    return apiClient.post<CashflowScenarioResponse>(
      API_ENDPOINTS.cashflowScenario,
      {
        company_id: data.company_id || DEFAULT_COMPANY_ID,
        as_of_date: data.as_of_date,
        horizon_days: data.horizon_days || 30,
        payment_delay_days: delay,
        expense_increase_percentage: expensePct,
        customer_delay_days: delay,
        expense_increase_percent: expensePct,
      },
      { signal }
    );
  },

  getExpenseAssumptions: (companyId = DEFAULT_COMPANY_ID, signal?: AbortSignal) =>
    apiClient.get<ExpenseAssumptionBackend[]>(API_ENDPOINTS.cashflowAssumptions, {
      params: { company_id: companyId },
      signal,
    }),

  createExpenseAssumption: (data: Partial<ExpenseAssumptionBackend>, signal?: AbortSignal) =>
    apiClient.post<ExpenseAssumptionBackend>(
      API_ENDPOINTS.cashflowAssumptions,
      { company_id: DEFAULT_COMPANY_ID, ...data },
      { signal }
    ),

  updateExpenseAssumption: (
    assumptionId: string,
    data: Partial<ExpenseAssumptionBackend>,
    signal?: AbortSignal
  ) =>
    apiClient.patch<ExpenseAssumptionBackend>(
      `${API_ENDPOINTS.cashflowAssumptions}/${assumptionId}`,
      data,
      { signal }
    ),

  deleteExpenseAssumption: (assumptionId: string, signal?: AbortSignal) =>
    apiClient.delete(`${API_ENDPOINTS.cashflowAssumptions}/${assumptionId}`, { signal }),

  getCollectionOverrides: (companyId = DEFAULT_COMPANY_ID, signal?: AbortSignal) =>
    apiClient.get<CollectionOverrideBackend[]>(API_ENDPOINTS.cashflowOverrides, {
      params: { company_id: companyId },
      signal,
    }),

  getInvoiceOverrides: (invoiceId: string, signal?: AbortSignal) =>
    apiClient.get<CollectionOverrideBackend[]>(API_ENDPOINTS.cashflowOverrides, {
      params: { company_id: DEFAULT_COMPANY_ID, invoice_id: invoiceId, is_active: true },
      signal,
    }),

  createCollectionOverride: (
    data: {
      invoice_id: string;
      expected_collection_date: string;
      expected_amount?: number;
      recovery_probability?: number;
      commitment_source?: string;
      notes?: string;
      company_id?: string;
    },
    signal?: AbortSignal
  ) =>
    apiClient.post<CollectionOverrideBackend>(
      API_ENDPOINTS.cashflowOverrides,
      { company_id: data.company_id || DEFAULT_COMPANY_ID, ...data },
      { signal }
    ),

  deleteCollectionOverride: (overrideId: string, signal?: AbortSignal) =>
    apiClient.delete(`${API_ENDPOINTS.cashflowOverrides}/${overrideId}`, { signal }),
};

// FX Intelligence API
export const fxApi = {
  getPairs: (signal?: AbortSignal) =>
    apiClient.get<FxPairsResponse>(API_ENDPOINTS.fxPairs, { signal }),

  getCurrentRates: (pairs?: string[], signal?: AbortSignal) =>
    apiClient.get<FxRateBackend[]>(API_ENDPOINTS.fxRatesCurrent, {
      params: pairs && pairs.length > 0 ? { pairs: pairs.join(',') } : undefined,
      signal,
    }),

  getRateHistory: (
    pair = 'USD/INR',
    options?: { start_date?: string; end_date?: string; limit?: number },
    signal?: AbortSignal
  ) =>
    apiClient.get<{
      currency_pair: string;
      total: number;
      limit: number;
      offset: number;
      items: Array<{
        id: number;
        currency_pair: string;
        observation_date: string;
        rate_value: number;
        original_rate_value: number;
        original_unit: number;
        provider: string;
        rate_type: string;
        source: string;
      }>;
    }>(API_ENDPOINTS.fxRatesHistory, {
      params: {
        pair,
        limit: options?.limit || 100,
        start_date: options?.start_date,
        end_date: options?.end_date,
      },
      signal,
    }),

  getModelsStatus: (signal?: AbortSignal) =>
    apiClient.get<Record<string, unknown>>(API_ENDPOINTS.fxModelsStatus, { signal }),

  getModelsMetrics: (pair?: string, signal?: AbortSignal) =>
    apiClient.get<Record<string, unknown>>(API_ENDPOINTS.fxModelsMetrics, {
      params: pair ? { pair } : undefined,
      signal,
    }),

  generateForecast: (data: FxForecastRequestBackend, signal?: AbortSignal) =>
    apiClient.post<FxForecastBackend>(
      API_ENDPOINTS.fxForecast,
      { company_id: DEFAULT_COMPANY_ID, ...data },
      { signal }
    ),

  getForecastById: (forecastId: string, signal?: AbortSignal) =>
    apiClient.get<FxForecastBackend>(`${API_ENDPOINTS.fxForecast}/${forecastId}`, { signal }),

  getForecastHistory: (companyId = DEFAULT_COMPANY_ID, limit = 50, signal?: AbortSignal) =>
    apiClient.get<FxForecastBackend[]>(API_ENDPOINTS.fxForecastHistory, {
      params: { company_id: companyId, limit },
      signal,
    }),

  getExposure: (
    companyId = DEFAULT_COMPANY_ID,
    asOfDate?: string,
    signal?: AbortSignal
  ) =>
    apiClient.get<FxExposureResponseBackend>(API_ENDPOINTS.fxExposure, {
      params: {
        company_id: companyId,
        as_of_date: asOfDate,
      },
      signal,
    }),

  runScenario: (data: FxScenarioRequestBackend, signal?: AbortSignal) =>
    apiClient.post<FxScenarioResponseBackend>(
      API_ENDPOINTS.fxScenario,
      { company_id: DEFAULT_COMPANY_ID, ...data },
      { signal }
    ),

  getScenarioById: (scenarioId: string, signal?: AbortSignal) =>
    apiClient.get<FxScenarioResponseBackend>(`${API_ENDPOINTS.fxScenario}/${scenarioId}`, { signal }),

  getScenarioHistory: (companyId = DEFAULT_COMPANY_ID, limit = 50, signal?: AbortSignal) =>
    apiClient.get<FxScenarioResponseBackend[]>(API_ENDPOINTS.fxScenarioHistory, {
      params: { company_id: companyId, limit },
      signal,
    }),
};

// Re-exports
export * from './client';
export * from './config';
export * from './errors';
export * from './types';
export * from './formatters';

