/**
 * Centralized Native Fetch API Client for Finora
 */

import { API_BASE_URL, DEFAULT_TIMEOUT_MS } from './config';
import { ApiError, parseApiError } from './errors';

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
  timeoutMs?: number;
}

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  /**
   * Core request dispatcher with timeout, abort handling, and standardized error parsing.
   */
  public async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { params, body, headers: customHeaders, timeoutMs = DEFAULT_TIMEOUT_MS, signal: userSignal, ...rest } = options;

    // Build URL with query parameters
    const url = new URL(`${this.baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null) {
          url.searchParams.append(key, String(val));
        }
      });
    }

    // Set up AbortController timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    // Chain with user's signal if provided
    if (userSignal) {
      userSignal.addEventListener('abort', () => controller.abort());
    }

    // Prepare headers
    const headers = new Headers(customHeaders);
    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }

    let requestBody: BodyInit | undefined;
    if (body !== undefined && body !== null) {
      if (body instanceof FormData || body instanceof URLSearchParams || typeof body === 'string') {
        requestBody = body as BodyInit;
      } else {
        requestBody = JSON.stringify(body);
        if (!headers.has('Content-Type')) {
          headers.set('Content-Type', 'application/json');
        }
      }
    }

    try {
      const response = await fetch(url.toString(), {
        ...rest,
        headers,
        body: requestBody,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle non-2xx HTTP responses
      if (!response.ok) {
        let errorData: any = null;
        try {
          errorData = await response.json();
        } catch {
          errorData = await response.text();
        }

        throw new ApiError({
          message: typeof errorData === 'object' && errorData?.detail
            ? (typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail))
            : `HTTP ${response.status}: ${response.statusText}`,
          status: response.status,
          statusText: response.statusText,
          endpoint,
          detail: errorData?.detail || errorData,
          validationErrors: errorData?.errors,
        });
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return (await response.json()) as T;
      }

      return (await response.text()) as unknown as T;
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      throw parseApiError(err, endpoint);
    }
  }

  public get<T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  public post<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'POST', body });
  }

  public patch<T>(endpoint: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'PATCH', body });
  }

  public delete<T>(endpoint: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
