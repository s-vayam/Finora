import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X, RotateCcw } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'warning' | 'info';
  title: string;
  message: string;
  onUndo?: () => void;
  undoLabel?: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  return (
    <div
      role="region"
      aria-label="Notifications"
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

const ToastItem: React.FC<{ toast: ToastMessage; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss,
}) => {
  useEffect(() => {
    // Give user more time (7.5s) if an undo action is available
    const timeoutDuration = toast.onUndo ? 7500 : 4500;
    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, timeoutDuration);
    return () => clearTimeout(timer);
  }, [toast.id, toast.onUndo, onDismiss]);

  const borderClass =
    toast.type === 'success'
      ? 'border-[#BDE3D1] bg-[#FFFFFF]'
      : toast.type === 'warning'
      ? 'border-[#F5DCB2] bg-[#FFFFFF]'
      : 'border-[#E7E7E2] bg-[#FFFFFF]';

  const icon =
    toast.type === 'success' ? (
      <CheckCircle2 className="w-4 h-4 text-[#39765A] shrink-0 mt-0.5" />
    ) : toast.type === 'warning' ? (
      <AlertCircle className="w-4 h-4 text-[#A87524] shrink-0 mt-0.5" />
    ) : (
      <Info className="w-4 h-4 text-[#111111] shrink-0 mt-0.5" />
    );

  return (
    <div
      className={`pointer-events-auto p-4 rounded-xl border shadow-lg flex items-start gap-3 transition-all ${borderClass}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {icon}
      <div className="flex-1 text-xs">
        <p className="font-bold text-[#111111]">{toast.title}</p>
        <p className="text-[#8B8D86] mt-0.5 leading-snug">{toast.message}</p>
        {toast.onUndo && (
          <div className="mt-2.5 flex items-center gap-2">
            <button
              onClick={() => {
                toast.onUndo?.();
                onDismiss(toast.id);
              }}
              className="text-xs font-bold px-2.5 py-1 rounded-md bg-[#111111] text-[#D9F83F] hover:bg-[#252525] transition-colors inline-flex items-center gap-1.5 shadow-xs focus-visible:ring-2 focus-visible:ring-[#111111]"
            >
              <RotateCcw className="w-3 h-3 text-[#D9F83F]" />
              <span>{toast.undoLabel || 'Undo'}</span>
            </button>
            <span className="text-[10px] text-[#8B8D86]">Restores previous status</span>
          </div>
        )}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-[#8B8D86] hover:text-[#111111] p-0.5 rounded transition-colors"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
