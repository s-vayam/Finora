export type NavigationTab = 
  | 'overview' 
  | 'invoices' 
  | 'fx-risk' 
  | 'cash-flow' 
  | 'documents' 
  | 'copilot';

export type Currency = 'USD' | 'EUR' | 'GBP' | 'INR';

export type InvoiceStatus = 'Paid' | 'Upcoming' | 'Due soon' | 'Overdue';

export interface Invoice {
  id: string;
  invoiceNumber: string;
  customer: string;
  country: string;
  currency: 'USD' | 'EUR' | 'GBP';
  amount: number;
  inrEquivalent: number;
  issueDate: string;
  dueDate: string;
  status: InvoiceStatus;
  paymentTerms: string;
  description: string;
  shippingReference: string;
  contactEmail: string;
}

export type DocumentStatus = 'Complete' | 'Pending' | 'Missing';

export interface TradeDocument {
  id: string;
  name: string;
  type: string;
  customer: string;
  shipmentRef: string;
  destinationPort: string;
  originPort: string;
  status: DocumentStatus;
  lastUpdated: string;
  deadlineDate: string;
  issuingAuthority: string;
  notes: string;
}

export interface AlertItem {
  id: string;
  type: 'overdue' | 'fx' | 'document';
  urgency: 'high' | 'medium' | 'low';
  title: string;
  whatHappened: string;
  whyItMatters: string;
  whatToDoNext: string;
  actionLabel: string;
  targetTab: NavigationTab;
  relatedEntityId?: string;
}

export interface CashFlowMonth {
  monthId: string;
  label: string; // e.g. "Month 1 (Nov 2026)"
  shortLabel: string; // e.g. "Nov 2026"
  inflows: number; // in ₹ lakh
  outflows: number; // in ₹ lakh
  netChange: number; // inflows - outflows
  closingBalance: number; // opening + cumulative netChange
  notes?: string;
}

export interface FXExposureRecord {
  currency: 'USD' | 'EUR' | 'GBP';
  symbol: string;
  exposureAmount: number;
  illustrativeRate: number; // INR per unit
  inrEquivalent: number; // in ₹
  inrLakh: number;
  previousExposureAmount: number;
  sharePercent: number;
}

export interface ChatAction {
  label: string;
  targetTab: NavigationTab;
  relatedEntityId?: string;
  invoiceToOpen?: Invoice;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  suggestedAction?: ChatAction;
}
