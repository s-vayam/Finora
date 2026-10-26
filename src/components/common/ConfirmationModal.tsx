import React, { useRef } from 'react';
import { ShieldAlert, X } from 'lucide-react';
import { useModalFocus } from '../../hooks/useModalFocus';

interface ConfirmationModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  title,
  description,
  confirmLabel = 'Confirm Action',
  cancelLabel = 'Cancel',
  isDestructive = false,
  onConfirm,
  onCancel,
}) => {
  const cancelBtnRef = useRef<HTMLButtonElement>(null);

  // Hook manages focus trap, initial focus on Cancel, Escape dismissal, and restoring focus to caller
  const modalContainerRef = useModalFocus({
    isOpen,
    onClose: onCancel,
    initialFocusRef: cancelBtnRef,
  });

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
      aria-describedby="confirm-modal-desc"
      onClick={onCancel}
    >
      <div 
        ref={modalContainerRef}
        className="bg-white border border-[#E7E7E2] rounded-xl max-w-md w-full shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-100"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-[#E7E7E2] flex items-center justify-between bg-[#F5F5F2]">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#111111] flex items-center justify-center text-[#D9F83F]">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <h3 id="confirm-modal-title" className="text-sm font-bold text-[#111111]">
              {title}
            </h3>
          </div>
          <button
            onClick={onCancel}
            className="text-[#8B8D86] hover:text-[#111111] p-1 rounded-md hover:bg-[#EBEBE6] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111]"
            aria-label="Cancel and close dialog (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 text-xs text-[#8B8D86] leading-relaxed space-y-3">
          <p id="confirm-modal-desc" className="text-[#111111] text-xs leading-relaxed">{description}</p>
          <div className="p-3 rounded-lg bg-[#F5F5F2] border border-[#E7E7E2] text-[11px] text-[#8B8D86]">
            <span className="font-bold text-[#111111]">Prototype Notice:</span> This action updates the local prototype state and recalculates dashboard summaries. No live banking transaction will be initiated. Reversible via Undo.
          </div>
        </div>

        <div className="px-5 py-3.5 bg-[#F5F5F2] border-t border-[#E7E7E2] flex items-center justify-end gap-2.5">
          <button
            ref={cancelBtnRef}
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-xs font-semibold text-[#111111] bg-white border border-[#E7E7E2] hover:bg-[#EBEBE6] rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-[#111111]"
          >
            {cancelLabel} (Esc)
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] ${
              isDestructive
                ? 'bg-[#B94A48] hover:bg-[#963735] text-white'
                : 'bg-[#D9F83F] hover:bg-[#c8ea2e] text-[#111111]'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
