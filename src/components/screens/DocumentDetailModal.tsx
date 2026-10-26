import React, { useRef } from 'react';
import { X, FileText, CheckCircle2, Clock, Building, Anchor, Info } from 'lucide-react';
import { TradeDocument } from '../../types';
import { StatusBadge } from '../common/Badge';
import { useModalFocus } from '../../hooks/useModalFocus';

interface DocumentDetailModalProps {
  document: TradeDocument | null;
  onClose: () => void;
  onUpdateStatus: (docId: string, newStatus: 'Complete' | 'Pending') => void;
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({
  document,
  onClose,
  onUpdateStatus,
}) => {
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // Hook manages focus trap, Escape dismissal, and returns focus to triggering element
  const modalContainerRef = useModalFocus({
    isOpen: !!document,
    onClose,
    initialFocusRef: closeBtnRef,
  });

  if (!document) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="doc-modal-title"
      onClick={onClose}
    >
      <div 
        ref={modalContainerRef}
        className="bg-white border border-[#E7E7E2] rounded-xl max-w-xl w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E7E7E2] flex items-center justify-between bg-[#F5F5F2]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#111111] text-[#D9F83F]">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 id="doc-modal-title" className="text-base font-bold text-[#111111]">
                  {document.name}
                </h2>
                <StatusBadge status={document.status} />
              </div>
              <p className="text-xs text-[#8B8D86] mt-0.5">
                Type: {document.type} • Shipment Ref: {document.shipmentRef}
              </p>
            </div>
          </div>
          <button
            ref={closeBtnRef}
            onClick={onClose}
            className="text-[#8B8D86] hover:text-[#111111] p-1.5 rounded-lg hover:bg-[#EBEBE6] transition-colors focus-visible:ring-2 focus-visible:ring-[#111111]"
            aria-label="Close modal (Esc)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-xs">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 rounded-xl bg-[#F5F5F2] border border-[#E7E7E2]">
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Related Customer</span>
              <span className="font-bold text-sm text-[#111111] flex items-center gap-1.5 mt-0.5">
                <Building className="w-3.5 h-3.5 text-[#111111]" />
                {document.customer}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Issuing Authority</span>
              <span className="font-bold text-sm text-[#111111] block mt-0.5">
                {document.issuingAuthority}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Trade Transit Route</span>
              <span className="text-xs text-[#111111] flex items-center gap-1.5 mt-0.5">
                <Anchor className="w-3.5 h-3.5 text-[#111111]" />
                {document.originPort} → {document.destinationPort}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Required Deadline</span>
              <span className="font-bold text-xs text-[#111111] block mt-0.5">
                {document.deadlineDate} <span className="text-[#8B8D86] font-normal">(Updated: {document.lastUpdated})</span>
              </span>
            </div>
          </div>

          {/* Operational Notes */}
          <div className="p-4 rounded-xl bg-white border border-[#E7E7E2] space-y-1">
            <span className="font-bold text-xs text-[#111111] block">Shipment Compliance Context</span>
            <p className="text-[#8B8D86] leading-relaxed">{document.notes}</p>
          </div>

          {/* Explanatory Notice */}
          <div className="p-3 bg-[#ECF9A8] border border-[#D9F83F] rounded-xl text-[11px] text-[#111111] flex items-start gap-2">
            <Info className="w-4 h-4 text-[#111111] shrink-0 mt-0.5" />
            <div>
              <strong>Compliance Workflow:</strong> Tracks customs paperwork to avoid port demurrage, customs detention, and clearance delays. Status can be changed or reverted at any time.
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#F5F5F2] border-t border-[#E7E7E2] flex items-center justify-between">
          <div className="text-[11px] text-[#8B8D86]">
            Press <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#E7E7E2] font-mono text-[10px]">Esc</kbd> to dismiss
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#111111] bg-white border border-[#E7E7E2] hover:bg-[#EBEBE6] rounded-lg transition-colors"
            >
              Close
            </button>
            {document.status !== 'Complete' ? (
              <button
                onClick={() => {
                  onUpdateStatus(document.id, 'Complete');
                  onClose();
                }}
                className="px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4 text-[#111111]" />
                <span>Mark Received & Verified</span>
              </button>
            ) : (
              <button
                onClick={() => {
                  onUpdateStatus(document.id, 'Pending');
                  onClose();
                }}
                className="px-4 py-2 text-xs font-semibold text-[#A87524] bg-[#FEF8EC] border border-[#F5DCB2] hover:bg-[#fdedcb] rounded-lg transition-colors flex items-center gap-1.5"
              >
                <Clock className="w-4 h-4" />
                <span>Revert to Pending</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
