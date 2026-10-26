import { Invoice, TradeDocument, AlertItem, CashFlowMonth, FXExposureRecord } from '../types';

export const COMPANY_INFO = {
  name: 'Meridian Textiles Pvt Ltd',
  division: 'Export Division — Cotton & Linen Weaves',
  industry: 'Textile Manufacturing & Global Exports',
  headquarters: 'Ahmedabad, Gujarat, India',
  primaryUser: {
    name: 'Arjun Mehta',
    role: 'Finance Manager',
    email: 'arjun.mehta@meridiantextiles.in',
  },
  baseCurrency: 'INR',
  baseCurrencySymbol: '₹',
};

// Illustrative Conversion Rates against INR (Fixed for prototype)
export const EXCHANGE_RATES: Record<string, number> = {
  USD: 85,
  EUR: 99,
  GBP: 113,
  INR: 1,
};

export const EXCHANGE_RATES_LABEL = 'Illustrative rates — not live market data';

export const INITIAL_INVOICES: Invoice[] = [
  {
    id: 'inv-1',
    invoiceNumber: 'INV-2026-089',
    customer: 'Northstar Retail',
    country: 'United States',
    currency: 'USD',
    amount: 12400,
    inrEquivalent: 12400 * 85, // ₹10,54,000
    issueDate: '2026-09-18',
    dueDate: '2026-10-18',
    status: 'Overdue',
    paymentTerms: 'Net 30',
    description: '1,200 Organic Linen Bedspread sets — Batch #B-409',
    shippingReference: 'EXP-2026-388 / Hanjin 4120',
    contactEmail: 'ap@northstar-retail.com',
  },
  {
    id: 'inv-2',
    invoiceNumber: 'INV-2026-082',
    customer: 'Horizon Apparel LLC',
    country: 'United States',
    currency: 'USD',
    amount: 3800,
    inrEquivalent: 3800 * 85, // ₹3,23,000
    issueDate: '2026-09-12',
    dueDate: '2026-10-12',
    status: 'Overdue',
    paymentTerms: 'Net 30',
    description: '450 Premium Cotton Twill fabrics (Navy & Sand)',
    shippingReference: 'EXP-2026-372 / Maersk Line',
    contactEmail: 'finance@horizonapparel.com',
  },
  {
    id: 'inv-3',
    invoiceNumber: 'INV-2026-085',
    customer: 'Baltic Fashion Ltd',
    country: 'United States',
    currency: 'USD',
    amount: 2400,
    inrEquivalent: 2400 * 85, // ₹2,04,000
    issueDate: '2026-09-15',
    dueDate: '2026-10-15',
    status: 'Overdue',
    paymentTerms: 'Net 30',
    description: '300 Spun-dyed Jacquard weave samples',
    shippingReference: 'EXP-2026-379 / MSC Cargo',
    contactEmail: 'accounts@balticfashion.com',
  },
  {
    id: 'inv-4',
    invoiceNumber: 'INV-2026-091',
    customer: 'Alpine Imports',
    country: 'Germany',
    currency: 'EUR',
    amount: 8200,
    inrEquivalent: 8200 * 99, // ₹8,11,800
    issueDate: '2026-09-28',
    dueDate: '2026-10-28',
    status: 'Due soon',
    paymentTerms: 'Net 30',
    description: '800 Pure Khadi Tablecloth and Napkin sets',
    shippingReference: 'EXP-2026-441 / CMA CGM',
    contactEmail: 'buchhaltung@alpine-imports.de',
  },
  {
    id: 'inv-5',
    invoiceNumber: 'INV-2026-094',
    customer: 'Pacific Home Co',
    country: 'United States',
    currency: 'USD',
    amount: 19500,
    inrEquivalent: 19500 * 85, // ₹16,57,500
    issueDate: '2026-10-02',
    dueDate: '2026-11-02',
    status: 'Upcoming',
    paymentTerms: 'Net 30',
    description: '2,000 Woven Cotton Drapes — Natural Ecru',
    shippingReference: 'EXP-2026-452 / ONE Line',
    contactEmail: 'procurement@pacifichome.co',
  },
  {
    id: 'inv-6',
    invoiceNumber: 'INV-2026-096',
    customer: 'Greenfield Trading',
    country: 'United Kingdom',
    currency: 'GBP',
    amount: 4800,
    inrEquivalent: 4800 * 113, // ₹5,42,400
    issueDate: '2026-10-05',
    dueDate: '2026-11-05',
    status: 'Upcoming',
    paymentTerms: 'Net 30',
    description: '600 Luxury Combed Cotton Towel Bales',
    shippingReference: 'EXP-2026-460 / Hapag-Lloyd',
    contactEmail: 'invoices@greenfieldtrading.co.uk',
  },
  {
    id: 'inv-7',
    invoiceNumber: 'INV-2026-098',
    customer: 'Nova Living',
    country: 'France',
    currency: 'EUR',
    amount: 6700,
    inrEquivalent: 6700 * 99, // ₹6,63,300
    issueDate: '2026-10-09',
    dueDate: '2026-11-09',
    status: 'Upcoming',
    paymentTerms: 'Net 30',
    description: '950 Embroidered Cushion Covers & Throws',
    shippingReference: 'EXP-2026-465 / Cosco',
    contactEmail: 'comptabilite@novaliving.fr',
  },
  {
    id: 'inv-8',
    invoiceNumber: 'INV-2026-101',
    customer: 'Solstice Department Stores',
    country: 'United States',
    currency: 'USD',
    amount: 34000,
    inrEquivalent: 34000 * 85, // ₹28,90,000
    issueDate: '2026-10-22',
    dueDate: '2026-11-22',
    status: 'Upcoming',
    paymentTerms: 'Net 30',
    description: 'Bulk Holiday Bedding Collection — 3,500 units',
    shippingReference: 'EXP-2026-480 / Maersk Line',
    contactEmail: 'vendorinvoices@solsticestores.com',
  },
  {
    id: 'inv-9',
    invoiceNumber: 'INV-2026-104',
    customer: 'Kyoto Home Goods',
    country: 'United States', // Billed in USD
    currency: 'USD',
    amount: 22500,
    inrEquivalent: 22500 * 85, // ₹19,12,500
    issueDate: '2026-10-25',
    dueDate: '2026-11-30',
    status: 'Upcoming',
    paymentTerms: 'Net 35',
    description: 'Indigo Artisan Weave Panels — Export Consignment',
    shippingReference: 'EXP-2026-489 / Evergreen Marine',
    contactEmail: 'payables@kyotohome.com',
  },
  {
    id: 'inv-10',
    invoiceNumber: 'INV-2026-074',
    customer: 'Lyon Deco SA',
    country: 'France',
    currency: 'EUR',
    amount: 5400,
    inrEquivalent: 5400 * 99, // ₹5,34,600
    issueDate: '2026-09-05',
    dueDate: '2026-10-05',
    status: 'Paid',
    paymentTerms: 'Net 30',
    description: '500 Linen Table Runners (Bespoke Pattern)',
    shippingReference: 'EXP-2026-350 / CMA CGM',
    contactEmail: 'finance@lyondeco.fr',
  },
  {
    id: 'inv-11',
    invoiceNumber: 'INV-2026-071',
    customer: 'Cambridge Mills',
    country: 'United Kingdom',
    currency: 'GBP',
    amount: 3200,
    inrEquivalent: 3200 * 113, // ₹3,61,600
    issueDate: '2026-09-02',
    dueDate: '2026-10-02',
    status: 'Paid',
    paymentTerms: 'Net 30',
    description: 'Woven Cotton Yarn Sample Cones (Grade A)',
    shippingReference: 'EXP-2026-342 / Hapag-Lloyd',
    contactEmail: 'accounts@cambridgemills.co.uk',
  },
];

export const INITIAL_DOCUMENTS: TradeDocument[] = [
  {
    id: 'doc-1',
    name: 'Certificate of Origin',
    type: 'Regulatory / Trade Preference',
    customer: 'Alpine Imports',
    shipmentRef: 'EXP-2026-441',
    originPort: 'Mundra Port (INMUN)',
    destinationPort: 'Hamburg (DEHAM)',
    status: 'Missing',
    lastUpdated: '2026-10-24',
    deadlineDate: '2026-10-29',
    issuingAuthority: 'Export Inspection Council of India (EIC)',
    notes: 'Awaiting Chamber of Commerce seal. Consignment arrives in Hamburg in 3 days; customs clearance will stall without original document.',
  },
  {
    id: 'doc-2',
    name: 'Export Declaration Form (Shipping Bill)',
    type: 'Customs Clearance',
    customer: 'Greenfield Trading',
    shipmentRef: 'EXP-2026-460',
    originPort: 'Nhava Sheva (INNSA)',
    destinationPort: 'Felixstowe (GBFXT)',
    status: 'Pending',
    lastUpdated: '2026-10-25',
    deadlineDate: '2026-11-02',
    issuingAuthority: 'Indian Customs ICEGATE',
    notes: 'Draft bill uploaded by customs clearing agent. Pending electronic verification of HS code 5208.52.',
  },
  {
    id: 'doc-3',
    name: 'Inspection Certificate',
    type: 'Quality Assurance',
    customer: 'Nova Living',
    shipmentRef: 'EXP-2026-465',
    originPort: 'Mundra Port (INMUN)',
    destinationPort: 'Le Havre (FRLEH)',
    status: 'Pending',
    lastUpdated: '2026-10-23',
    deadlineDate: '2026-11-04',
    issuingAuthority: 'SGS India Pvt Ltd',
    notes: 'Final tensile strength test complete; awaiting signed quality conformity certificate from laboratory.',
  },
  {
    id: 'doc-4',
    name: 'Commercial Invoice #INV-2026-089',
    type: 'Financial / Commercial',
    customer: 'Northstar Retail',
    shipmentRef: 'EXP-2026-388',
    originPort: 'Mundra Port (INMUN)',
    destinationPort: 'Long Beach (USLGB)',
    status: 'Complete',
    lastUpdated: '2026-09-18',
    deadlineDate: '2026-10-18',
    issuingAuthority: 'Meridian Textiles Pvt Ltd',
    notes: 'Stamped and signed. Delivered to buyer bank via documentary collection.',
  },
  {
    id: 'doc-5',
    name: 'Ocean Bill of Lading (B/L)',
    type: 'Title / Transport',
    customer: 'Northstar Retail',
    shipmentRef: 'EXP-2026-388',
    originPort: 'Mundra Port (INMUN)',
    destinationPort: 'Long Beach (USLGB)',
    status: 'Complete',
    lastUpdated: '2026-09-22',
    deadlineDate: '2026-10-18',
    issuingAuthority: 'Hanjin Shipping / Agent',
    notes: 'Clean on board original bill released to consignee bank.',
  },
  {
    id: 'doc-6',
    name: 'Marine Cargo Insurance Policy',
    type: 'Insurance',
    customer: 'Pacific Home Co',
    shipmentRef: 'EXP-2026-452',
    originPort: 'Nhava Sheva (INNSA)',
    destinationPort: 'Los Angeles (USLAX)',
    status: 'Complete',
    lastUpdated: '2026-10-02',
    deadlineDate: '2026-11-02',
    issuingAuthority: 'New India Assurance Co',
    notes: 'Institute Cargo Clauses (A) cover all risks up to 110% of CIF invoice value.',
  },
  {
    id: 'doc-7',
    name: 'Packing List & Weight Slip',
    type: 'Logistics',
    customer: 'Alpine Imports',
    shipmentRef: 'EXP-2026-441',
    originPort: 'Mundra Port (INMUN)',
    destinationPort: 'Hamburg (DEHAM)',
    status: 'Complete',
    lastUpdated: '2026-09-28',
    deadlineDate: '2026-10-28',
    issuingAuthority: 'Meridian Dispatch Warehouse',
    notes: 'Gross weight 4,210 kg, tare 320 kg across 24 palletized cartons.',
  },
];

export const INITIAL_ALERTS: AlertItem[] = [
  {
    id: 'alert-1',
    type: 'overdue',
    urgency: 'high',
    title: 'Overdue payment from Northstar Retail',
    whatHappened: 'Invoice #INV-2026-089 ($12,400 USD) was due on 18 Oct 2026 and is now 8 days overdue.',
    whyItMatters: 'Delayed international receipts compress working capital and increase receivables aging risk across open export orders.',
    whatToDoNext: 'Review invoice details, confirm arrival of goods in Long Beach, and issue a structured payment follow-up notice.',
    actionLabel: 'View invoice',
    targetTab: 'invoices',
    relatedEntityId: 'inv-1',
  },
  {
    id: 'alert-2',
    type: 'fx',
    urgency: 'medium',
    title: 'Increased foreign currency exposure',
    whatHappened: "The company's recorded foreign-currency exposure increased by +8.4% compared with the previous month's review to $84,200 USD equivalent.",
    whyItMatters: 'Recent volatility in USD/INR and EUR/INR rates exposes open receivables to unexpected margin compression upon conversion.',
    whatToDoNext: 'Review currency breakdown by currency pair and assess forward hedge coverage in the FX Risk module.',
    actionLabel: 'Review exposure',
    targetTab: 'fx-risk',
  },
  {
    id: 'alert-3',
    type: 'document',
    urgency: 'high',
    title: 'Missing trade document: Certificate of Origin',
    whatHappened: 'Export shipment #EXP-2026-441 to Alpine Imports is awaiting an endorsed Certificate of Origin.',
    whyItMatters: 'Without the preferential tariff certificate, the German buyer faces standard third-country duties and Hamburg port clearance will be held up.',
    whatToDoNext: 'Review the document record and request expedited endorsement from the regional Export Inspection Council.',
    actionLabel: 'View documents',
    targetTab: 'documents',
    relatedEntityId: 'doc-1',
  },
];

export const FX_EXPOSURE_RECORDS: FXExposureRecord[] = [
  {
    currency: 'USD',
    symbol: '$',
    exposureAmount: 58000,
    illustrativeRate: 85,
    inrEquivalent: 58000 * 85, // ₹49,30,000
    inrLakh: 49.30,
    previousExposureAmount: 52000,
    sharePercent: 60.7,
  },
  {
    currency: 'EUR',
    symbol: '€',
    exposureAmount: 22000,
    illustrativeRate: 99,
    inrEquivalent: 22000 * 99, // ₹21,78,000
    inrLakh: 21.78,
    previousExposureAmount: 24000,
    sharePercent: 26.8,
  },
  {
    currency: 'GBP',
    symbol: '£',
    exposureAmount: 9000,
    illustrativeRate: 113,
    inrEquivalent: 9000 * 113, // ₹10,17,000
    inrLakh: 10.17,
    previousExposureAmount: 7500,
    sharePercent: 12.5,
  },
];

// Base cash balance: ₹24.8 lakh
export const OPENING_CASH_BALANCE = 24.8; // in ₹ lakh

// Monthly values in ₹ lakh
// Month 1: 18, 15
// Month 2: 22, 17
// Month 3: 19, 20 (Outflow exceeds inflow by 1 lakh)
// Month 4: 25, 18
// Month 5: 27, 21
// Month 6: 24, 19
export const MONTHLY_CASH_FLOW_DATA_RAW = [
  { monthId: 'm1', label: 'Month 1 (Nov 2026)', shortLabel: 'Nov 2026', inflows: 18, outflows: 15, notes: 'Steady shipments; Northstar & Alpine settlements anticipated' },
  { monthId: 'm2', label: 'Month 2 (Dec 2026)', shortLabel: 'Dec 2026', inflows: 22, outflows: 17, notes: 'Q4 holiday retail deliveries; strong collection cycle' },
  { monthId: 'm3', label: 'Month 3 (Jan 2027)', shortLabel: 'Jan 2027', inflows: 19, outflows: 20, notes: 'Raw cotton procurement & annual factory maintenance payments exceed collections by ₹1.0L' },
  { monthId: 'm4', label: 'Month 4 (Feb 2027)', shortLabel: 'Feb 2027', inflows: 25, outflows: 18, notes: 'Spring season export order dispatches begin' },
  { monthId: 'm5', label: 'Month 5 (Mar 2027)', shortLabel: 'Mar 2027', inflows: 27, outflows: 21, notes: 'Fiscal year-end receivables realization peak' },
  { monthId: 'm6', label: 'Month 6 (Apr 2027)', shortLabel: 'Apr 2027', inflows: 24, outflows: 19, notes: 'New fiscal cycle opening purchase orders' },
];

export function calculateCashFlow(openingBalance: number = OPENING_CASH_BALANCE): CashFlowMonth[] {
  let runningBalance = openingBalance;
  return MONTHLY_CASH_FLOW_DATA_RAW.map((item) => {
    const netChange = item.inflows - item.outflows;
    runningBalance = Math.round((runningBalance + netChange) * 10) / 10;
    return {
      ...item,
      netChange,
      closingBalance: runningBalance,
    };
  });
}
