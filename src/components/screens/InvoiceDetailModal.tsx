import React, { useRef, useState, useEffect } from 'react';
import { 
  X, 
  Calendar, 
  DollarSign, 
  Building, 
  Truck, 
  Mail, 
  CheckCircle2, 
  AlertCircle, 
  Info, 
  RotateCcw,
  Sparkles,
  TrendingDown,
  Clock,
  CreditCard,
  Loader2
} from 'lucide-react';
import { Invoice } from '../../types';
import { StatusBadge } from '../common/Badge';
import { EXCHANGE_RATES } from '../../data/mockData';
import { useModalFocus } from '../../hooks/useModalFocus';
import { AccessibleTooltip } from '../common/AccessibleTooltip';
import { paymentsApi, predictionApi } from '../../services/api';
import { PaymentBackend, PaymentRiskPrediction } from '../../services/api/types';

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

  // State for Payment History
  const [payments, setPayments] = useState<PaymentBackend[]>([]);
  const [paymentsLoading, setPaymentsLoading] = useState(false);

  // State for ML Payment Risk
  const [prediction, setPrediction] = useState<PaymentRiskPrediction | null>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);

  useEffect(() => {
    if (!invoice) {
      setPayments([]);
      setPrediction(null);
      setPredictionError(null);
      return;
    }

    // Fetch payments history
    let isSubscribed = true;
    setPaymentsLoading(true);
    paymentsApi.getInvoicePayments(invoice.id)
      .then((res) => {
        if (isSubscribed && res?.payments) {
          setPayments(res.payments);
        }
      })
      .catch(() => {
        // Silently handle if payments endpoint not seeded for mock id
      })
      .finally(() => {
        if (isSubscribed) setPaymentsLoading(false);
      });

    // Check ML Risk prediction eligibility
    const isPaid = invoice.status === 'Paid' || invoice.backendStatus === 'PAID';
    const isPartiallyPaid = invoice.backendStatus === 'PARTIALLY_PAID';
    const isCancelled = invoice.backendStatus === 'CANCELLED';

    if (isPaid || isPartiallyPaid || isCancelled) {
      setPrediction(null);
      setPredictionLoading(false);
      return;
    }

    // Attempt to load latest prediction for unpaid invoice
    setPredictionLoading(true);
    setPredictionError(null);
    predictionApi.getLatestPrediction(invoice.id)
      .then((pred) => {
        if (isSubscribed && pred) {
          setPrediction(pred);
        }
      })
      .catch(() => {
        // If not generated yet, it will remain null and user can click Predict
      })
      .finally(() => {
        if (isSubscribed) setPredictionLoading(false);
      });

    return () => {
      isSubscribed = false;
    };
  }, [invoice]);

  const handleRunPrediction = async () => {
    if (!invoice) return;
    setPredictionLoading(true);
    setPredictionError(null);
    try {
      const result = await predictionApi.predictPaymentRisk(invoice.id);
      setPrediction(result);
    } catch (err: any) {
      setPredictionError(err?.message || 'Could not compute payment risk prediction.');
    } finally {
      setPredictionLoading(false);
    }
  };

  if (!invoice) return null;

  const rate = EXCHANGE_RATES[invoice.currency] || 85;
  const inrAmount = invoice.amount * rate;
  const inrLakh = (inrAmount / 100000).toFixed(2);
  const amountPaid = invoice.amountPaid || 0;
  const outstanding = invoice.outstandingBalance !== undefined ? invoice.outstandingBalance : Math.max(0, invoice.amount - amountPaid);

  const getCurrencySymbol = (curr: string) => {
    switch (curr) {
      case 'USD': return '$';
      case 'EUR': return '€';
      case 'GBP': return '£';
      default: return '₹';
    }
  };

  const isPaid = invoice.status === 'Paid' || invoice.backendStatus === 'PAID';
  const isPartiallyPaid = invoice.backendStatus === 'PARTIALLY_PAID';

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
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto text-xs">
          {/* Financial Highlights */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-[#F5F5F2] border border-[#E7E7E2]">
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Total Amount</span>
              <span className="text-base sm:text-lg font-bold text-[#111111] block">
                {getCurrencySymbol(invoice.currency)}{invoice.amount.toLocaleString()}
              </span>
              <span className="text-[10px] text-[#8B8D86] block">₹{inrLakh} L approx</span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Amount Received</span>
              <span className="text-base sm:text-lg font-bold text-[#39765A] block">
                {getCurrencySymbol(invoice.currency)}{amountPaid.toLocaleString()}
              </span>
              <span className="text-[10px] text-[#39765A] block">{((amountPaid / (invoice.amount || 1)) * 100).toFixed(0)}% paid</span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Outstanding</span>
              <span className={`text-base sm:text-lg font-bold block ${outstanding > 0 ? 'text-[#B94A48]' : 'text-neutral-500'}`}>
                {getCurrencySymbol(invoice.currency)}{outstanding.toLocaleString()}
              </span>
              <span className="text-[10px] text-[#8B8D86] block">Due: {invoice.dueDate}</span>
            </div>
            <div>
              <span className="text-[11px] font-medium text-[#8B8D86] block">Payment Terms</span>
              <span className="text-sm font-semibold text-[#111111] block mt-0.5">
                {invoice.paymentTerms}
              </span>
              <span className="text-[10px] text-[#8B8D86] block">Issue: {invoice.issueDate}</span>
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

          {/* ML Payment Risk Intelligence Section */}
          <div className="p-4 rounded-xl border border-[#E7E7E2] bg-[#FDFDFD]">
            <div className="flex items-center justify-between border-b border-[#E7E7E2] pb-2 mb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#244E3D]" />
                <h3 className="font-bold text-xs text-[#111111] uppercase tracking-wider">
                  Payment Risk Intelligence
                </h3>
              </div>
              {prediction && (
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                  prediction.risk_category === 'HIGH'
                    ? 'bg-[#FDF2F2] text-[#B94A48] border border-[#F6CECE]'
                    : prediction.risk_category === 'MEDIUM'
                    ? 'bg-[#FEF8EC] text-[#A87524] border border-[#F5DCB2]'
                    : 'bg-[#EDF7F2] text-[#39765A] border border-[#BDE3D1]'
                }`}>
                  {prediction.risk_category} Risk
                </span>
              )}
            </div>

            {isPaid ? (
              <div className="p-3 bg-[#EDF7F2] border border-[#BDE3D1] rounded-lg text-[#39765A] flex items-center gap-2 text-xs">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>Invoice settled in full. Risk prediction is inactive for paid invoices.</span>
              </div>
            ) : isPartiallyPaid ? (
              <div className="p-3 bg-[#FEF8EC] border border-[#F5DCB2] rounded-lg text-[#A87524] flex items-center gap-2 text-xs">
                <Info className="w-4 h-4 shrink-0" />
                <span>This invoice has partial settlement recorded. ML model v1.0.0 evaluates initial unpaid invoices.</span>
              </div>
            ) : predictionLoading ? (
              <div className="flex items-center justify-center p-4 text-neutral-500 gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-[#244E3D]" />
                <span>Evaluating customer payment history with ML models...</span>
              </div>
            ) : prediction ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[#F5F5F2] p-3 rounded-lg text-center">
                  <div>
                    <span className="text-[10px] text-[#8B8D86] block">Late Probability</span>
                    <span className="text-sm font-bold text-[#111111]">
                      {(prediction.late_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#8B8D86] block">Expected Delay</span>
                    <span className="text-sm font-bold text-[#111111]">
                      +{prediction.expected_delay_days.toFixed(1)} days
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#8B8D86] block">Conditional Delay</span>
                    <span className="text-sm font-bold text-[#111111]">
                      +{prediction.predicted_delay_days.toFixed(1)} days
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-[#8B8D86] block">Est. Collection Date</span>
                    <span className="text-sm font-bold text-[#111111]">
                      {prediction.estimated_payment_date}
                    </span>
                  </div>
                </div>
                <p className="text-[10px] text-[#8B8D86] leading-relaxed">
                  * ML payment risk estimation powered by Random Forest & Ridge Regression models ({prediction.model_version}). Delay is conditional on late payment. Not a credit default guarantee.
                </p>
              </div>
            ) : (
              <div className="flex items-center justify-between bg-[#F5F5F2] p-3 rounded-lg">
                <div className="text-[11px] text-[#8B8D86]">
                  No prediction run yet. Evaluate this invoice with the ML risk model.
                </div>
                <button
                  type="button"
                  onClick={handleRunPrediction}
                  className="px-3 py-1.5 bg-[#244E3D] hover:bg-[#1C3E30] text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Analyze Risk</span>
                </button>
              </div>
            )}
            {predictionError && (
              <p className="text-xs text-[#B94A48] mt-2">{predictionError}</p>
            )}
          </div>

          {/* Payment History Section */}
          <div className="p-4 rounded-xl border border-[#E7E7E2] bg-white">
            <div className="flex items-center justify-between border-b border-[#E7E7E2] pb-2 mb-3">
              <div className="flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-[#111111]" />
                <h3 className="font-bold text-[11px] text-[#111111] uppercase tracking-wider">
                  Payment History & Settlements ({payments.length})
                </h3>
              </div>
              {paymentsLoading && <Loader2 className="w-3.5 h-3.5 animate-spin text-neutral-400" />}
            </div>

            {payments.length === 0 ? (
              <p className="text-neutral-500 text-xs italic">
                {isPaid ? 'Payment marked settled in demonstration state.' : 'No payments recorded against this invoice yet.'}
              </p>
            ) : (
              <div className="space-y-2">
                {payments.map((pmt, idx) => (
                  <div key={pmt.payment_id || idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#F5F5F2] text-xs">
                    <div className="flex items-center gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-[#39765A]" />
                      <div>
                        <span className="font-bold text-[#111111]">{pmt.payment_method || 'WIRE'}</span>
                        <span className="text-neutral-500 text-[10px] block">Ref: {pmt.reference_number || pmt.payment_id.substring(0, 12)} • {pmt.payment_date}</span>
                      </div>
                    </div>
                    <span className="font-bold text-[#39765A]">
                      +{getCurrencySymbol(pmt.currency || invoice.currency)}{Number(pmt.amount).toLocaleString()} {pmt.currency || invoice.currency}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Goods Description */}
          <div className="p-4 bg-[#F5F5F2] rounded-xl border border-[#E7E7E2]">
            <span className="font-bold text-[#111111] block mb-1">Export Consignment Description</span>
            <p className="text-[#8B8D86] leading-relaxed">{invoice.description}</p>
          </div>

          {/* Unfamiliar Terms Explanation Card */}
          <div className="p-3.5 bg-white border border-[#E7E7E2] rounded-xl text-[11px] text-[#8B8D86] space-y-1">
            <div className="flex items-center gap-1.5 font-bold text-[#111111]">
              <Info className="w-3.5 h-3.5" />
              <span>Trade Terms Reference</span>
            </div>
            <p className="leading-relaxed">
              <strong>EEFC Account:</strong> Foreign currency held by exporters in India without mandatory rupee conversion. <strong>Net 30:</strong> Settlement due 30 days post-issuance.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-[#F5F5F2] border-t border-[#E7E7E2] flex items-center justify-between">
          <div className="text-[11px] text-[#8B8D86]">
            Press <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#E7E7E2] font-mono text-[10px]">Esc</kbd> to close
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
