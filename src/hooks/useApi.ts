/**
 * Reusable React Hook for Async Backend API Calls
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { ApiError, parseApiError } from '../services/api/errors';

export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  refetch: () => Promise<T | null>;
}

export interface UseApiOptions<T> {
  immediate?: boolean;
  initialData?: T | null;
  onSuccess?: (data: T) => void;
  onError?: (error: ApiError) => void;
}

export function useApi<T>(
  apiFn: (signal?: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
  options: UseApiOptions<T> = {}
): UseApiState<T> {
  const { immediate = true, initialData = null, onSuccess, onError } = options;

  const [data, setData] = useState<T | null>(initialData);
  const [loading, setLoading] = useState<boolean>(immediate);
  const [error, setError] = useState<ApiError | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef<boolean>(true);

  const execute = useCallback(async (): Promise<T | null> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const result = await apiFn(controller.signal);
      if (mountedRef.current) {
        setData(result);
        setLoading(false);
        if (onSuccess) onSuccess(result);
      }
      return result;
    } catch (err: unknown) {
      const parsed = parseApiError(err);
      // Ignore if user cancelled
      if (err instanceof DOMException && err.name === 'AbortError') {
        return null;
      }

      if (mountedRef.current) {
        setError(parsed);
        setLoading(false);
        if (onError) onError(parsed);
      }
      return null;
    }
  }, [apiFn, onSuccess, onError]);

  useEffect(() => {
    mountedRef.current = true;
    if (immediate) {
      execute();
    }
    return () => {
      mountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [execute, ...deps]);

  return {
    data,
    loading,
    error,
    refetch: execute,
  };
}
