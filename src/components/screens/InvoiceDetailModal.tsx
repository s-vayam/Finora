import React, { useRef } from 'react';
import { X, Calendar, DollarSign, Building, Truck, Mail, CheckCircle2, AlertCircle, Info, RotateCcw } from 'lucide-react';
import { Invoice } from '../../types';
import { StatusBadge } from '../common/Badge';
import { EXCHANGE_RATES } from '../../data/mockData';
import { useModalFocus } from '../../hooks/useModalFocus';
import { AccessibleTooltip } from '../common/AccessibleTooltip';

interface InvoiceDetailModalProps {
  invoice: Invoice | null;
  onClose: () => void;
  onRequestMarkAsPaid: (invoice: Invoice) => void;
  onRequestRevertStatus?: (invoice: Invoice) => void;
}

export const InvoiceDetailModal: React.FC<InvoiceDetailModalProps> = ({
  invoice,
  onClose,
  onRequestMarkAsPaid,
  onRequestRevertStatus,
}) => {
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  // Focus trap, Escape dismissal, and return focus to triggering control
  const modalContainerRef = useModalFocus({
    isOpen: !!invoice,
    onClose,
    initialFocusRef: closeBtnRef,
  });

  if (!invoice) return null;

  const rate = EXCHANGE_RATES[invoice.currency] || 85;
  const inrAmount = invoice.amount * rate;
  const inrLakh = (inrAmount / 100000).toFixed(2);

  const getCurrencySymbol = (curr: string) => {
    switch (curr) {
      case 'USD': return '$';
      case 'EUR': return '€';
      case 'GBP': return '£';
      default: return '₹';
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="invoice-modal-title"
      onClick={onClose}
    >
      <div 
        ref={modalContainerRef}
        className="bg-white border border-[#E7E7E2] rounded-xl max-w-2xl w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#E7E7E2] flex items-center justify-between bg-[#F5F5F2]">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2.5">
                <h2 id="invoice-modal-title" className="text-base font-bold text-[#111111]">
                  {invoice.invoiceNumber}
                </h2>
                <StatusBadge status={invoice.status} />
              </div>
              <p className="text-xs text-[#8B8D86] mt-0.5">
                Export Receivables Record • {invoice.customer} ({invoice.country})
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

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto text-xs">
          {/* Financial Highlights */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-[#F5F5F2] border border-[#E7E7E2]">
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Invoice Amount</span>
              <span className="text-xl font-bold text-[#111111]">
                {getCurrencySymbol(invoice.currency)}
                {invoice.amount.toLocaleString()} {invoice.currency}
              </span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Base INR Value</span>
              <span className="text-xl font-bold text-[#111111]">
                ₹{inrLakh} Lakh
              </span>
              <span className="text-[10px] text-[#8B8D86] block">Benchmark: ₹{rate} / 1 {invoice.currency}</span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Payment Terms</span>
              <span className="text-sm font-semibold text-[#111111] block mt-0.5">
                {invoice.paymentTerms}
              </span>
              <span className="text-[10px] text-[#A87524]">Due: {invoice.dueDate}</span>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-3 p-4 rounded-xl border border-[#E7E7E2] bg-white">
              <h3 className="font-bold text-[11px] text-[#111111] uppercase tracking-wider border-b border-[#E7E7E2] pb-1.5">
                Commercial Details
              </h3>
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-[#8B8D86]">
                  <Building className="w-4 h-4 text-[#111111] shrink-0" />
                  <span>Buyer:</span>
                  <strong className="text-[#111111]">{invoice.customer}</strong>
                </div>
                <div className="flex items-center gap-2 text-[#8B8D86]">
                  <Mail className="w-4 h-4 text-[#111111] shrink-0" />
                  <span>Contact:</span>
                  <span className="text-[#111111] underline">{invoice.contactEmail}</span>
                </div>
                <div className="flex items-center gap-2 text-[#8B8D86]">
                  <Truck className="w-4 h-4 text-[#111111] shrink-0" />
                  <span>Shipping Ref:</span>
                  <AccessibleTooltip content="Ocean freight consignment identifier and vessel customs bill reference">
                    <span className="text-[#111111] font-mono text-[11px] underline decoration-dotted cursor-help">
                      {invoice.shippingReference}
                    </span>
                  </AccessibleTooltip>
                </div>
              </div>
            </div>

            <div className="space-y-3 p-4 rounded-xl border border-[#E7E7E2] bg-white">
              <h3 className="font-bold text-[11px] text-[#111111] uppercase tracking-wider border-b border-[#E7E7E2] pb-1.5">
                Timeline & Banking Route
              </h3>
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-[#8B8D86]">
                  <Calendar className="w-4 h-4 text-[#111111] shrink-0" />
                  <span>Issue Date:</span>
                  <span className="text-[#111111]">{invoice.issueDate}</span>
                </div>
                <div className="flex items-center gap-2 text-[#8B8D86]">
                  <Calendar className="w-4 h-4 text-[#111111] shrink-0" />
                  <span>Due Date:</span>
                  <span className="text-[#111111] font-bold">{invoice.dueDate}</span>
                </div>
                <div className="flex items-center gap-2 text-[#8B8D86]">
                  <DollarSign className="w-4 h-4 text-[#111111] shrink-0" />
                  <span>Settlement Route:</span>
                  <AccessibleTooltip content="Exchange Earners' Foreign Currency (EEFC) account held in India for receiving cross-border export receipts without rupee conversion">
                    <span className="text-[#111111] underline decoration-dotted cursor-help">
                      Wire SWIFT / EEFC Account
                    </span>
                  </AccessibleTooltip>
                </div>
              </div>
            </div>
          </div>

          {/* Goods Description */}
          <div className="p-4 bg-[#F5F5F2] rounded-xl border border-[#E7E7E2]">
            <span className="font-bold text-[#111111] block mb-1">Export Consignment Description</span>
            <p className="text-[#8B8D86] leading-relaxed">{invoice.description}</p>
          </div>

          {/* Unfamiliar Terms Explanation Card (Universal Usability & Memory Load) */}
          <div className="p-3.5 bg-white border border-[#E7E7E2] rounded-xl text-[11px] text-[#8B8D86] space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-[#111111]">
              <Info className="w-3.5 h-3.5" />
              <span>Trade Terms Reference</span>
            </div>
            <p className="leading-relaxed">
              <strong>EEFC Account:</strong> Foreign currency held by exporters in India without mandatory rupee conversion. <strong>Net 30:</strong> Settlement due 30 days post-issuance.
            </p>
          </div>

          {/* Contextual Status Guidance */}
          {invoice.status === 'Overdue' && (
            <div className="p-4 bg-[#FDF2F2] border border-[#F6CECE] rounded-xl text-[#B94A48] flex items-start gap-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Payment Overdue Notice</strong>
                <p className="text-[11px] text-[#8C3432] mt-0.5 leading-relaxed">
                  Maturity date was {invoice.dueDate}. An automated reminder was dispatched. Recommend checking container release status and following up with foreign buyer accounts team.
                </p>
              </div>
            </div>
          )}

          {invoice.status === 'Paid' && (
            <div className="p-4 bg-[#EDF7F2] border border-[#BDE3D1] rounded-xl text-[#39765A] flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Settled / Closed</strong>
                <p className="text-[11px] text-[#295641] mt-0.5">
                  Funds recorded as received in full in local prototype state.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-[#F5F5F2] border-t border-[#E7E7E2] flex items-center justify-between">
          <div className="text-[11px] text-[#8B8D86]">
            Illustrative sample record • Press <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#E7E7E2] font-mono text-[10px]">Esc</kbd> to close
          </div>
          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#111111] bg-white border border-[#E7E7E2] hover:bg-[#EBEBE6] rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-[#111111]"
            >
              Close
            </button>
            {invoice.status !== 'Paid' ? (
              <button
                onClick={() => onRequestMarkAsPaid(invoice)}
                className="px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg transition-colors flex items-center gap-1.5 shadow-xs focus-visible:ring-2 focus-visible:ring-[#111111]"
              >
                <CheckCircle2 className="w-4 h-4 text-[#111111]" />
                <span>Mark as Paid</span>
              </button>
            ) : (
              onRequestRevertStatus && (
                <button
                  onClick={() => onRequestRevertStatus(invoice)}
                  className="px-3 py-2 text-xs font-semibold text-[#111111] bg-white border border-[#E7E7E2] hover:bg-[#F5F5F2] rounded-lg transition-colors flex items-center gap-1.5"
                  title="Revert status to Unpaid / Overdue"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Revert to Unpaid</span>
                </button>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
