/**
 * Centralized API Error Handling for Finora
 */

export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export class ApiError extends Error {
  public readonly status: number;
  public readonly statusText: string;
  public readonly endpoint: string;
  public readonly detail: string | Record<string, unknown>;
  public readonly validationErrors?: ValidationErrorItem[];
  public readonly isNetworkError: boolean;
  public readonly isBackendUnavailable: boolean;

  constructor(params: {
    message: string;
    status: number;
    statusText: string;
    endpoint: string;
    detail?: string | Record<string, unknown>;
    validationErrors?: ValidationErrorItem[];
    isNetworkError?: boolean;
    isBackendUnavailable?: boolean;
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.status = params.status;
    this.statusText = params.statusText;
    this.endpoint = params.endpoint;
    this.detail = params.detail || params.message;
    this.validationErrors = params.validationErrors;
    this.isNetworkError = !!params.isNetworkError;
    this.isBackendUnavailable = !!params.isBackendUnavailable || params.status === 0 || params.status === 502 || params.status === 503 || params.status === 504;

    // Maintains proper stack trace if supported
    const errObj = Error as unknown as { captureStackTrace?: (target: object, constructorOpt?: Function) => void };
    if (typeof errObj.captureStackTrace === 'function') {
      errObj.captureStackTrace(this, ApiError);
    }
  }

  /**
   * Returns a user-friendly error message suitable for displaying in UI/Toasts.
   */
  public getUserFriendlyMessage(): string {
    if (this.isNetworkError || this.isBackendUnavailable) {
      return 'Unable to connect to Finora backend service. Please ensure the server is running on http://127.0.0.1:8000.';
    }

    if (this.status === 404) {
      if (typeof this.detail === 'string') return this.detail;
      return 'The requested resource was not found.';
    }

    if (this.status === 409) {
      if (typeof this.detail === 'object' && this.detail !== null && 'message' in this.detail) {
        return String(this.detail.message);
      }
      if (typeof this.detail === 'string') return this.detail;
      return 'A conflict occurred with the current state of the resource.';
    }

    if (this.status === 422) {
      if (this.validationErrors && this.validationErrors.length > 0) {
        const first = this.validationErrors[0];
        const field = first.loc.slice(1).join('.');
        return field ? `Validation failed for ${field}: ${first.msg}` : first.msg;
      }
      if (typeof this.detail === 'string') return this.detail;
      return 'Request validation failed. Please check your inputs.';
    }

    if (typeof this.detail === 'string' && this.detail.trim().length > 0) {
      return this.detail;
    }

    return this.message || 'An unexpected error occurred while communicating with the server.';
  }
}

export function parseApiError(error: unknown, endpoint = ''): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof DOMException && error.name === 'AbortError') {
    return new ApiError({
      message: 'Request was cancelled or timed out',
      status: 408,
      statusText: 'Request Timeout',
      endpoint,
      detail: 'Request was aborted or exceeded the maximum timeout limit.',
      isNetworkError: true,
    });
  }

  if (error instanceof TypeError && error.message.includes('fetch')) {
    return new ApiError({
      message: 'Network request failed: Could not connect to API server',
      status: 0,
      statusText: 'Network Error',
      endpoint,
      detail: 'Backend server is unreachable. Check connection and CORS settings.',
      isNetworkError: true,
      isBackendUnavailable: true,
    });
  }

  const msg = error instanceof Error ? error.message : String(error);
  return new ApiError({
    message: msg || 'Unknown API Error',
    status: 500,
    statusText: 'Internal Error',
    endpoint,
    detail: msg,
  });
}
