/**
 * Data mappers converting between Backend API schemas and Frontend UI types
 */

import { Invoice, InvoiceStatus } from '../../types';
import { InvoiceBackend, PaymentBackend } from './types';

const FX_BENCHMARKS: Record<string, number> = {
  USD: 94.5,
  EUR: 106.1,
  GBP: 127.3,
  INR: 1.0,
};

export function mapBackendInvoiceToUi(inv: InvoiceBackend): Invoice {
  const currency = (inv.currency as 'USD' | 'EUR' | 'GBP') || 'USD';
  const amount = Number(inv.invoice_amount || 0);
  const rate = FX_BENCHMARKS[currency] || 85.0;
  const inrEquivalent = inv.inr_equivalent ? Number(inv.inr_equivalent) : Math.round(amount * rate);

  const amountPaid = Number(inv.amount_paid || 0);
  const outstandingBalance = inv.outstanding_balance !== undefined
    ? Number(inv.outstanding_balance)
    : Math.max(0, amount - amountPaid);

  // Map status
  let uiStatus: InvoiceStatus = 'Upcoming';
  if (inv.status === 'PAID') {
    uiStatus = 'Paid';
  } else if (inv.status === 'CANCELLED') {
    uiStatus = 'Upcoming';
  } else {
    // Determine based on due_date or due_status
    if (inv.due_status === 'OVERDUE') {
      uiStatus = 'Overdue';
    } else if (inv.due_status === 'DUE_SOON') {
      uiStatus = 'Due soon';
    } else if (inv.due_status === 'UPCOMING') {
      uiStatus = 'Upcoming';
    } else if (inv.due_date) {
      const today = new Date().toISOString().split('T')[0];
      if (inv.due_date < today) {
        uiStatus = 'Overdue';
      } else {
        const dueDateObj = new Date(inv.due_date);
        const todayObj = new Date(today);
        const diffDays = Math.ceil((dueDateObj.getTime() - todayObj.getTime()) / (1000 * 60 * 60 * 24));
        if (diffDays <= 7) {
          uiStatus = 'Due soon';
        } else {
          uiStatus = 'Upcoming';
        }
      }
    }
  }

  const terms = inv.payment_terms_days ? `Net ${inv.payment_terms_days}` : 'Net 30';

  return {
    id: inv.invoice_id,
    invoiceNumber: inv.invoice_number,
    customer: inv.customer_name || `Customer ${inv.customer_id.substring(0, 8)}`,
    country: inv.customer_country || 'United States',
    currency,
    amount,
    inrEquivalent,
    issueDate: inv.issue_date,
    dueDate: inv.due_date,
    status: uiStatus,
    paymentTerms: terms,
    description: inv.description || 'Export commercial shipment',
    shippingReference: inv.shipping_reference || `EXP-${inv.invoice_number}`,
    contactEmail: inv.contact_email || 'finance@buyer-intl.com',
    amountPaid,
    outstandingBalance,
    backendStatus: inv.status,
  };
}

export function mapBackendPaymentList(payments: PaymentBackend[]): Array<{
  id: string;
  date: string;
  amount: number;
  currency: string;
  method: string;
  referenceNumber: string;
  notes?: string;
}> {
  return payments.map((p) => ({
    id: p.payment_id,
    date: p.payment_date,
    amount: Number(p.amount),
    currency: p.currency,
    method: p.payment_method,
    referenceNumber: p.reference_number || p.payment_id,
    notes: p.notes,
  }));
}
