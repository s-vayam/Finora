import React, { useState } from 'react';
import { 
  DollarSign, 
  TrendingUp, 
  AlertCircle, 
  Wallet, 
  ChevronRight, 
  Bot, 
  Calendar,
  ExternalLink,
  Eye
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  ComposedChart, 
  Bar, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend 
} from 'recharts';
import { Invoice, AlertItem, NavigationTab, CashFlowMonth, FXExposureRecord } from '../../types';
import { StatusBadge } from '../common/Badge';
import { AccessibleTooltip } from '../common/AccessibleTooltip';

interface OverviewScreenProps {
  invoices: Invoice[];
  alerts: AlertItem[];
  cashFlowData: CashFlowMonth[];
  fxRecords: FXExposureRecord[];
  onNavigate: (tab: NavigationTab, relatedId?: string) => void;
  onSelectInvoice: (invoice: Invoice) => void;
}

export const OverviewScreen: React.FC<OverviewScreenProps> = ({
  invoices,
  alerts,
  cashFlowData,
  fxRecords,
  onNavigate,
  onSelectInvoice,
}) => {
  const openInvoices = invoices.filter((inv) => inv.status !== 'Paid');
  const overdueInvoices = invoices.filter((inv) => inv.status === 'Overdue');
  const [reportingPeriod, setReportingPeriod] = useState<'3months' | '6months'>('6months');
  
  const displayedCashFlow = reportingPeriod === '3months' ? cashFlowData.slice(0, 3) : cashFlowData;
  const currentFinalBalance = displayedCashFlow[displayedCashFlow.length - 1]?.closingBalance || 24.8;

  const overdueTotalUSD = overdueInvoices.reduce((sum, inv) => {
    if (inv.currency === 'USD') return sum + inv.amount;
    if (inv.currency === 'EUR') return sum + Math.round(inv.amount * (99 / 85));
    if (inv.currency === 'GBP') return sum + Math.round(inv.amount * (113 / 85));
    return sum;
  }, 0);
  
  const totalReceivablesUSD = openInvoices.reduce((sum, inv) => {
    if (inv.currency === 'USD') return sum + inv.amount;
    if (inv.currency === 'EUR') return sum + Math.round(inv.amount * (99 / 85));
    if (inv.currency === 'GBP') return sum + Math.round(inv.amount * (113 / 85));
    return sum;
  }, 0);

  const overdueCount = overdueInvoices.length;

  const sortedAlerts = [...alerts].sort((a, b) => {
    const weights: Record<string, number> = { high: 3, medium: 2, low: 1 };
    return (weights[b.urgency] || 0) - (weights[a.urgency] || 0);
  });

  const previewInvoices = invoices.slice(0, 5);

  const hasOverdue = overdueInvoices.length > 0;
  const topOverdue = overdueInvoices[0];

  return (
    <div className="space-y-6">
      {/* Page Heading & Period Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E7E7E2]">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">Overview</h2>
            <span className="text-[11px] font-medium text-[#111111] bg-[#ECF9A8] px-2.5 py-0.5 rounded-full border border-[#D9F83F]">
              Reporting: 26 Oct 2026
            </span>
          </div>
          <p className="text-xs text-[#8B8D86] mt-1">
            A summary of your international receivables, currency exposure and expected cash position.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white border border-[#E7E7E2] rounded-lg text-xs font-semibold text-[#111111] shadow-xs">
            <Calendar className="w-3.5 h-3.5 text-[#111111]" />
            <span>{reportingPeriod === '3months' ? '3-Month Window (Nov 26 – Jan 27)' : '6-Month Cycle (Nov 26 – Apr 27)'}</span>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Outstanding Receivables */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-[#8B8D86]">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Outstanding Receivables</span>
              <div className="w-7 h-7 rounded-lg bg-[#F5F5F2] flex items-center justify-center text-[#111111]">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl lg:text-3xl font-extrabold text-[#111111] tracking-tight">
                ${totalReceivablesUSD.toLocaleString()}
              </span>
              <span className="text-xs font-medium text-[#8B8D86]">USD equiv.</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F5F2] flex items-center justify-between text-[11px] text-[#8B8D86]">
            <span>{openInvoices.length} active invoices</span>
            <button
              onClick={() => onNavigate('invoices')}
              className="text-[#111111] hover:underline font-bold inline-flex items-center gap-0.5"
            >
              <span>View all</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* KPI 2: Foreign Exchange Exposure */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-[#8B8D86]">
              <span className="font-semibold uppercase tracking-wider text-[11px]">FX Exposure</span>
              <div className="w-7 h-7 rounded-lg bg-[#F5F5F2] flex items-center justify-center text-[#111111]">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl lg:text-3xl font-extrabold text-[#111111] tracking-tight">
                $84,200
              </span>
              <span className="text-xs font-bold text-[#A87524] bg-[#FEF8EC] px-2 py-0.5 rounded-full border border-[#F5DCB2]">
                +8.4%
              </span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F5F2] flex items-center justify-between text-[11px] text-[#8B8D86]">
            <AccessibleTooltip content="Aggregate of unhedged receivables due within next 45 days exposed to foreign currency fluctuations">
              <span className="cursor-help underline decoration-dotted text-[#111111] font-medium">
                45-day forward basis
              </span>
            </AccessibleTooltip>
            <button
              onClick={() => onNavigate('fx-risk')}
              className="text-[#111111] hover:underline font-bold inline-flex items-center gap-0.5"
            >
              <span>FX Analysis</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* KPI 3: Overdue Invoices */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-[#8B8D86]">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Overdue Invoices</span>
              <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                overdueCount > 0 ? 'bg-[#FDF2F2] text-[#B94A48]' : 'bg-[#EDF7F2] text-[#39765A]'
              }`}>
                <AlertCircle className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className={`text-2xl lg:text-3xl font-extrabold tracking-tight ${
                overdueCount > 0 ? 'text-[#B94A48]' : 'text-[#39765A]'
              }`}>
                ${overdueTotalUSD.toLocaleString()}
              </span>
              <span className="text-xs font-medium text-[#8B8D86]">
                across {overdueCount} {overdueCount === 1 ? 'invoice' : 'invoices'}
              </span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F5F2] flex items-center justify-between text-[11px] text-[#8B8D86]">
            <span className={overdueCount > 0 ? 'text-[#B94A48] font-bold' : 'text-[#39765A]'}>
              {overdueCount > 0 ? 'Action required' : 'No overdue items'}
            </span>
            <button
              onClick={() => onNavigate('invoices')}
              className="text-[#111111] hover:underline font-bold inline-flex items-center gap-0.5"
            >
              <span>Follow up</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* KPI 4: Projected Available Cash Balance */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs text-[#8B8D86]">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Projected Cash</span>
              <div className="w-7 h-7 rounded-lg bg-[#ECF9A8] flex items-center justify-center text-[#111111]">
                <Wallet className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-2xl lg:text-3xl font-extrabold text-[#111111] tracking-tight">
                ₹24.8 lakh
              </span>
              <span className="text-xs font-bold text-[#111111] bg-[#D9F83F] px-2 py-0.5 rounded-full border border-[#D9F83F]">
                Liquid
              </span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F5F2] flex items-center justify-between text-[11px] text-[#8B8D86]">
            <AccessibleTooltip content="Liquid cash balance across operational and EEFC trade accounts ready for working capital deployment">
              <span className="cursor-help underline decoration-dotted text-[#111111] font-medium">
                Opening reserves
              </span>
            </AccessibleTooltip>
            <button
              onClick={() => onNavigate('cash-flow')}
              className="text-[#111111] hover:underline font-bold inline-flex items-center gap-0.5"
            >
              <span>View Forecast</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Dark Highlight Panel: Contextual Co-Pilot Insight Card (Pro Finance style) */}
      <div className="rounded-xl bg-[#111111] text-white p-5 shadow-sm border border-[#222222]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-lg bg-[#222222] border border-[#333333] text-[#D9F83F] flex items-center justify-center font-bold shrink-0 mt-0.5">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-xs text-[#D9F83F] uppercase tracking-wider">
                  Co-Pilot Operational Insight
                </span>
                <span className="text-[10px] text-[#8B8D86] font-medium bg-[#222222] px-2 py-0.5 rounded-full">
                  Sample Data Model
                </span>
              </div>
              <p className="text-xs text-[#E7E7E2] mt-1.5 leading-relaxed max-w-3xl">
                {hasOverdue && topOverdue ? (
                  <>
                    <strong className="text-white font-bold">{topOverdue.customer}&apos;s</strong> payment of{' '}
                    <strong className="text-[#D9F83F] font-bold">${topOverdue.amount.toLocaleString()} USD</strong> is overdue since {topOverdue.dueDate}. Reviewing the invoice and following up with the customer may help clarify the expected payment date and prevent cash flow delays.
                  </>
                ) : (
                  <>
                    All overdue items have been reconciled in the current prototype session. Upcoming receivables from Alpine Imports (€8,200) mature on 28 Oct 2026.
                  </>
                )}
              </p>
            </div>
          </div>

          <div className="shrink-0 self-end sm:self-center">
            {hasOverdue && topOverdue ? (
              <button
                onClick={() => onSelectInvoice(topOverdue)}
                className="px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg transition-colors shadow-sm"
              >
                Review Invoice
              </button>
            ) : (
              <button
                onClick={() => onNavigate('copilot')}
                className="px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg transition-colors shadow-sm"
              >
                Ask Co-Pilot
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Grid: Cash Flow Projections Chart + Priority Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cash Flow Chart (2 Columns on large screens) */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-[#F5F5F2] gap-2">
              <div>
                <h3 className="font-bold text-sm text-[#111111]">
                  Projected Monthly Cash Flow & Closing Liquidity
                </h3>
                <p className="text-xs text-[#8B8D86] mt-0.5">
                  Expected trade receivables vs payables in ₹ lakh (Cumulative closing balance plotted on line)
                </p>
              </div>

              {/* Working Reporting-Period Switcher */}
              <div className="flex items-center gap-2">
                <div className="flex items-center p-0.5 bg-[#F5F5F2] border border-[#E7E7E2] rounded-lg text-xs">
                  <button
                    onClick={() => setReportingPeriod('3months')}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                      reportingPeriod === '3months'
                        ? 'bg-[#111111] text-white shadow-xs'
                        : 'text-[#8B8D86] hover:text-[#111111]'
                    }`}
                  >
                    3 Months
                  </button>
                  <button
                    onClick={() => setReportingPeriod('6months')}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                      reportingPeriod === '6months'
                        ? 'bg-[#111111] text-white shadow-xs'
                        : 'text-[#8B8D86] hover:text-[#111111]'
                    }`}
                  >
                    6 Months
                  </button>
                </div>

                <button
                  onClick={() => onNavigate('cash-flow')}
                  className="text-xs font-bold text-[#111111] hover:underline inline-flex items-center gap-1"
                >
                  <span>Full Schedule</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="mt-4 h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={displayedCashFlow}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F0ED" vertical={false} />
                  <XAxis
                    dataKey="shortLabel"
                    tick={{ fill: '#8B8D86', fontSize: 11 }}
                    axisLine={{ stroke: '#E7E7E2' }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#8B8D86', fontSize: 11 }}
                    axisLine={{ stroke: '#E7E7E2' }}
                    tickLine={false}
                    unit="L"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E7E7E2',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: '#111111',
                      boxShadow: '0 2px 6px rgba(0, 0, 0, 0.05)',
                    }}
                    formatter={(value: any, name: any) => [`₹${value} Lakh`, name]}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                    iconType="circle"
                  />
                  <Bar dataKey="inflows" name="Export Inflows (₹L)" fill="#D9F83F" stroke="#B8D626" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="outflows" name="Trade Outflows (₹L)" fill="#111111" radius={[4, 4, 0, 0]} />
                  <Line
                    type="monotone"
                    dataKey="closingBalance"
                    name="Projected Balance (₹L)"
                    stroke="#111111"
                    strokeWidth={2.5}
                    strokeDasharray="4 4"
                    dot={{ fill: '#D9F83F', stroke: '#111111', strokeWidth: 2, r: 4 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-[#F5F5F2] flex flex-col sm:flex-row items-start sm:items-center justify-between text-[11px] text-[#8B8D86] gap-1">
            <span>Opening Balance: ₹24.8L • {reportingPeriod === '3months' ? '3-Month' : '6-Month'} Projected Closing: ₹{currentFinalBalance.toFixed(1)}L</span>
            <span className="font-bold text-[#A87524]">Month 3 (Jan 2027) net deficit of -₹1.0L</span>
          </div>
        </div>

        {/* Priority Alerts List (1 Column) */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#F5F5F2]">
              <div>
                <h3 className="font-bold text-sm text-[#111111]">Priority Alerts</h3>
                <p className="text-xs text-[#8B8D86] mt-0.5">
                  Ordered by operational urgency
                </p>
              </div>
              <span className="text-[11px] font-bold text-[#111111] bg-[#F5F5F2] px-2 py-0.5 rounded-full border border-[#E7E7E2]">
                {alerts.length} Items
              </span>
            </div>

            <div className="mt-3.5 space-y-3">
              {sortedAlerts.map((alert) => (
                <div
                  key={alert.id}
                  onClick={() => onNavigate(alert.targetTab, alert.relatedEntityId)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onNavigate(alert.targetTab, alert.relatedEntityId);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  className="p-3.5 rounded-xl border border-[#E7E7E2] bg-[#F5F5F2] hover:border-[#111111] hover:bg-white transition-all cursor-pointer group focus-visible:ring-2 focus-visible:ring-[#111111]"
                  title={`Click to open ${alert.title}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-xs text-[#111111] line-clamp-1 group-hover:text-black">
                      {alert.title}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        alert.urgency === 'high'
                          ? 'bg-[#FDF2F2] text-[#B94A48] border border-[#F6CECE]'
                          : 'bg-[#FEF8EC] text-[#A87524] border border-[#F5DCB2]'
                      }`}
                    >
                      {alert.urgency}
                    </span>
                  </div>

                  <p className="text-[11px] text-[#8B8D86] mt-1.5 line-clamp-2 leading-relaxed">
                    {alert.whatHappened}
                  </p>

                  <div className="mt-2.5 pt-2 border-t border-[#E7E7E2] flex items-center justify-between text-xs">
                    <span className="text-[10px] text-[#8B8D86]">
                      {alert.type === 'overdue' ? 'Receivables' : alert.type === 'fx' ? 'FX Exposure' : 'Shipping'}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onNavigate(alert.targetTab, alert.relatedEntityId);
                      }}
                      className="font-bold text-[#111111] hover:underline inline-flex items-center gap-1 text-[11px]"
                    >
                      <span>{alert.actionLabel}</span>
                      <ExternalLink className="w-3 h-3 text-[#111111]" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#F5F5F2] text-center">
            <span className="text-[11px] text-[#8B8D86]">
              Alerts update automatically as invoices & documents change
            </span>
          </div>
        </div>
      </div>

      {/* Lower Section: FX Exposure Summary & Upcoming Payments Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* FX Exposure Summary (1 Column) */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-[#F5F5F2]">
            <div>
              <h3 className="font-bold text-sm text-[#111111]">FX Exposure Breakdown</h3>
              <p className="text-xs text-[#8B8D86] mt-0.5">Open receivables across major currencies</p>
            </div>
            <button
              onClick={() => onNavigate('fx-risk')}
              className="text-xs font-bold text-[#111111] hover:underline"
            >
              Calculator
            </button>
          </div>

          <div className="mt-4 space-y-4">
            {fxRecords.map((item) => (
              <div key={item.currency} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-[#111111]">{item.currency}</span>
                    <span className="text-[#8B8D86] text-[11px]">(@ ₹{item.illustrativeRate})</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-[#111111]">
                      {item.symbol}{item.exposureAmount.toLocaleString()}
                    </span>
                    <span className="text-[#8B8D86] text-[11px] block">
                      ≈ ₹{item.inrLakh.toFixed(2)} Lakh
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2 bg-[#F5F5F2] rounded-full overflow-hidden border border-[#E7E7E2]">
                  <div
                    className="h-full bg-[#D9F83F] rounded-full"
                    style={{ width: `${item.sharePercent}%` }}
                    title={`${item.currency}: ${item.sharePercent}% of open trade exposure`}
                  />
                </div>

                <div className="flex items-center justify-between text-[10px] text-[#8B8D86]">
                  <span>Share: {item.sharePercent}%</span>
                  <span>Prev cycle: {item.symbol}{item.previousExposureAmount.toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 p-3 rounded-xl bg-[#F5F5F2] border border-[#E7E7E2] text-[11px] text-[#8B8D86]">
            <p className="font-bold text-[#111111] mb-0.5">Illustrative Measurement Notice</p>
            The $84,200 dashboard KPI is net 45-day unhedged forward volume normalized to USD, while this breakdown reflects total active trade invoices (₹81.25 L total equivalent).
          </div>
        </div>

        {/* Upcoming Payments Table (2 Columns) */}
        <div className="lg:col-span-2 bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-[#F5F5F2]">
              <div>
                <h3 className="font-bold text-sm text-[#111111]">Active & Upcoming Invoices</h3>
                <p className="text-xs text-[#8B8D86] mt-0.5">Current cycle receivables portfolio</p>
              </div>
              <button
                onClick={() => onNavigate('invoices')}
                className="text-xs font-bold text-[#111111] hover:underline inline-flex items-center gap-1"
              >
                <span>View All Invoices</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="mt-3.5 overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#E7E7E2] text-[#8B8D86] text-[11px] font-semibold bg-[#F5F5F2]">
                    <th className="py-2.5 px-3">Customer</th>
                    <th className="py-2.5 px-3">Invoice #</th>
                    <th className="py-2.5 px-3 text-right">Amount</th>
                    <th className="py-2.5 px-3">Due Date</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#F5F5F2]">
                  {previewInvoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-[#F5F5F2] transition-colors">
                      <td className="py-3 px-3 font-bold text-[#111111]">
                        {inv.customer}
                        <span className="block text-[10px] text-[#8B8D86] font-normal">{inv.country}</span>
                      </td>
                      <td className="py-3 px-3 text-[#8B8D86] font-mono text-[11px]">
                        {inv.invoiceNumber}
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-[#111111]">
                        {inv.currency === 'USD' ? '$' : inv.currency === 'EUR' ? '€' : '£'}
                        {inv.amount.toLocaleString()} {inv.currency}
                      </td>
                      <td className="py-3 px-3 text-[#8B8D86]">
                        {inv.dueDate}
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={inv.status} size="sm" />
                      </td>
                      <td className="py-3 px-3 text-center">
                        <button
                          onClick={() => onSelectInvoice(inv)}
                          className="px-2.5 py-1 text-[11px] font-bold text-[#111111] bg-white hover:bg-[#F5F5F2] rounded-lg border border-[#E7E7E2] transition-colors inline-flex items-center gap-1 shadow-2xs"
                          title="View Invoice Details"
                        >
                          <Eye className="w-3 h-3 text-[#111111]" />
                          <span>Details</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-[#F5F5F2] flex items-center justify-between text-[11px] text-[#8B8D86]">
            <span>Showing top 5 active records. Total recorded invoices: {invoices.length}</span>
            <span>Illustrative sample dataset</span>
          </div>
        </div>
      </div>
    </div>
  );
};
