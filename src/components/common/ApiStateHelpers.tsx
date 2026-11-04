import React from 'react';
import { AlertCircle, RefreshCw, Loader2, Inbox } from 'lucide-react';
import { ApiError } from '../../services/api/errors';

export interface ErrorBannerProps {
  error: ApiError | Error | string | null;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  error,
  onRetry,
  className = '',
  compact = false,
}) => {
  if (!error) return null;

  const message =
    error instanceof ApiError
      ? error.getUserFriendlyMessage()
      : error instanceof Error
      ? error.message
      : String(error);

  if (compact) {
    return (
      <div
        className={`flex items-center justify-between gap-2 p-2.5 bg-[#FDF2F2] border border-[#F6CECE] rounded-lg text-xs text-[#B94A48] ${className}`}
        role="alert"
      >
        <div className="flex items-center gap-1.5 min-w-0">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 text-[#B94A48]" />
          <span className="truncate">{message}</span>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="flex items-center gap-1 font-medium hover:underline text-[#B94A48] flex-shrink-0 cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Retry</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={`p-4 bg-[#FDF2F2] border border-[#F6CECE] rounded-xl text-[#B94A48] ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-[#B94A48]" />
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-sm">Failed to load data</h4>
          <p className="text-xs mt-1 text-[#8C3432] leading-relaxed">{message}</p>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#F6CECE] hover:bg-[#FDF2F2] text-xs font-medium text-[#B94A48] rounded-lg transition-colors cursor-pointer shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        )}
      </div>
    </div>
  );
};

export interface LoadingStateProps {
  label?: string;
  className?: string;
  minHeight?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  label = 'Loading data...',
  className = '',
  minHeight = 'min-h-[160px]',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-6 ${minHeight} ${className}`}>
      <Loader2 className="w-6 h-6 animate-spin text-[#244E3D] mb-2" />
      <span className="text-xs text-neutral-500 font-medium">{label}</span>
    </div>
  );
};

export interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No records found',
  description = 'There are no items matching the current criteria.',
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center bg-white border border-[#E5E5E0] rounded-xl ${className}`}>
      <div className="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-400 mb-3">
        <Inbox className="w-5 h-5" />
      </div>
      <h4 className="text-sm font-semibold text-[#111111]">{title}</h4>
      <p className="text-xs text-neutral-500 mt-1 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 px-3.5 py-1.5 bg-[#244E3D] hover:bg-[#1C3E30] text-white text-xs font-medium rounded-lg transition-colors cursor-pointer shadow-sm"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};
