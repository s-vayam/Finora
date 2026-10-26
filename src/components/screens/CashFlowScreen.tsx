import React, { useState } from 'react';
import { 
  AlertTriangle, 
  ArrowUpRight, 
  ArrowDownRight,
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
import { CashFlowMonth } from '../../types';
import { OPENING_CASH_BALANCE } from '../../data/mockData';

interface CashFlowScreenProps {
  cashFlowData: CashFlowMonth[];
}

export const CashFlowScreen: React.FC<CashFlowScreenProps> = ({ cashFlowData }) => {
  const [period, setPeriod] = useState<'3months' | '6months'>('6months');

  const displayedData = period === '3months' ? cashFlowData.slice(0, 3) : cashFlowData;

  const finalMonth = displayedData[displayedData.length - 1];
  const finalBalance = finalMonth ? finalMonth.closingBalance : OPENING_CASH_BALANCE;

  const deficitMonths = displayedData.filter((m) => m.inflows < m.outflows);

  const totalInflows = displayedData.reduce((sum, m) => sum + m.inflows, 0);
  const totalOutflows = displayedData.reduce((sum, m) => sum + m.outflows, 0);
  const totalNet = totalInflows - totalOutflows;

  return (
    <div className="space-y-6">
      {/* Header & Period Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E7E7E2]">
        <div>
          <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">Cash Flow Forecast</h2>
          <p className="text-xs text-[#8B8D86] mt-1">
            Projected trade receipts, operational vendor disbursements, and cumulative working capital.
          </p>
        </div>

        {/* Period Selector Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-white border border-[#E7E7E2] rounded-xl">
          <button
            onClick={() => setPeriod('3months')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              period === '3months'
                ? 'bg-[#111111] text-white shadow-xs'
                : 'text-[#8B8D86] hover:text-[#111111]'
            }`}
          >
            3-Month View (Q4 26 – Jan 27)
          </button>
          <button
            onClick={() => setPeriod('6months')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              period === '6months'
                ? 'bg-[#111111] text-white shadow-xs'
                : 'text-[#8B8D86] hover:text-[#111111]'
            }`}
          >
            6-Month Forecast (Full Cycle)
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Opening Balance */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">Opening Liquidity</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{OPENING_CASH_BALANCE.toFixed(1)} L
            </span>
            <span className="text-xs text-[#8B8D86]">INR</span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            Baseline bank & EEFC balances
          </span>
        </div>

        {/* Period Inflows */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">Projected Inflows</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{totalInflows.toFixed(1)} L
            </span>
            <span className="text-xs text-[#39765A] font-semibold flex items-center">
              <ArrowUpRight className="w-3.5 h-3.5" />
              Receipts
            </span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            Across {displayedData.length} forecast months
          </span>
        </div>

        {/* Period Outflows */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">Projected Outflows</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{totalOutflows.toFixed(1)} L
            </span>
            <span className="text-xs text-[#B94A48] font-semibold flex items-center">
              <ArrowDownRight className="w-3.5 h-3.5" />
              Payables
            </span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            Raw materials & shipping expenses
          </span>
        </div>

        {/* Closing Balance */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">Closing Liquidity</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{finalBalance.toFixed(1)} L
            </span>
            <span className="text-xs text-[#39765A] font-bold">
              +{totalNet.toFixed(1)}L Net
            </span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            Cumulative data-calculated balance
          </span>
        </div>
      </div>

      {/* Shortfall Alert Banner */}
      {deficitMonths.length > 0 && (
        <div className="p-4 rounded-xl bg-[#FEF8EC] border border-[#F5DCB2] text-xs flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-[#A87524] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-xs text-[#A87524]">
              Working Capital Attention: {deficitMonths.map((m) => m.shortLabel).join(', ')} Inflow Deficit
            </h4>
            <p className="text-[#8B8D86] leading-relaxed text-[11px]">
              In <strong>{deficitMonths[0].label}</strong>, projected vendor outflows (<strong>₹{deficitMonths[0].outflows}L</strong>) exceed export receipts (<strong>₹{deficitMonths[0].inflows}L</strong>) by <strong>₹{Math.abs(deficitMonths[0].netChange).toFixed(1)} Lakh</strong> due to scheduled raw cotton purchase cycles and plant upkeep. 
              The overall liquidity cushion remains positive (projected closing balance: <strong>₹{deficitMonths[0].closingBalance}L</strong>).
            </p>
          </div>
        </div>
      )}

      {/* Chart Section */}
      <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-[#F5F5F2]">
          <div>
            <h3 className="font-bold text-sm text-[#111111]">
              Projected Monthly Inflows, Outflows, and Liquidity Balance
            </h3>
            <p className="text-xs text-[#8B8D86] mt-0.5">
              Unit: ₹ Lakh • Inflows (Neon Lime) and Outflows (Near-black) depicted as bars; line tracks cumulative closing balance
            </p>
          </div>
          <span className="text-[11px] font-semibold text-[#111111] bg-[#F5F5F2] px-2.5 py-0.5 rounded-full border border-[#E7E7E2]">
            {period === '3months' ? '3 Months' : '6 Months'}
          </span>
        </div>

        <div className="mt-4 h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={displayedData}
              margin={{ top: 15, right: 15, left: -5, bottom: 0 }}
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
                  boxShadow: '0 2px 6px rgba(0, 0, 0, 0.05)',
                }}
                formatter={(val: any, name: any) => [`₹${val} Lakh`, name]}
              />
              <Legend
                wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                iconType="circle"
              />
              <Bar dataKey="inflows" name="Export Inflows (₹L)" fill="#D9F83F" stroke="#B8D626" radius={[4, 4, 0, 0]} />
              <Bar dataKey="outflows" name="Vendor Outflows (₹L)" fill="#111111" radius={[4, 4, 0, 0]} />
              <Line
                type="monotone"
                dataKey="closingBalance"
                name="Projected Closing Balance (₹L)"
                stroke="#111111"
                strokeWidth={2.5}
                strokeDasharray="4 4"
                dot={{ fill: '#D9F83F', stroke: '#111111', strokeWidth: 2, r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monthly Breakdown Table */}
      <div className="bg-white rounded-xl border border-[#E7E7E2] shadow-xs overflow-hidden">
        <div className="p-4 border-b border-[#E7E7E2] bg-[#F5F5F2]">
          <h3 className="font-bold text-sm text-[#111111]">Detailed Monthly Breakdown Schedule</h3>
          <p className="text-xs text-[#8B8D86] mt-0.5">
            Single source of truth feeding both table and graphical model
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#E7E7E2] text-[#8B8D86] text-[11px] font-semibold bg-[#F5F5F2]">
                <th className="py-2.5 px-4">Period</th>
                <th className="py-2.5 px-4 text-right">Inflows (₹L)</th>
                <th className="py-2.5 px-4 text-right">Outflows (₹L)</th>
                <th className="py-2.5 px-4 text-right">Net Change (₹L)</th>
                <th className="py-2.5 px-4 text-right">Projected Balance (₹L)</th>
                <th className="py-2.5 px-4">Operational Assumptions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F5F5F2]">
              {displayedData.map((item) => (
                <tr key={item.monthId} className="hover:bg-[#F5F5F2] transition-colors">
                  <td className="py-3 px-4 font-bold text-[#111111]">
                    {item.label}
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-[#111111]">
                    ₹{item.inflows.toFixed(1)} L
                  </td>
                  <td className="py-3 px-4 text-right font-medium text-[#8B8D86]">
                    ₹{item.outflows.toFixed(1)} L
                  </td>
                  <td
                    className={`py-3 px-4 text-right font-bold ${
                      item.netChange >= 0 ? 'text-[#39765A]' : 'text-[#B94A48]'
                    }`}
                  >
                    {item.netChange >= 0 ? `+₹${item.netChange.toFixed(1)}` : `-₹${Math.abs(item.netChange).toFixed(1)}`} L
                  </td>
                  <td className="py-3 px-4 text-right font-bold text-[#111111]">
                    ₹{item.closingBalance.toFixed(1)} L
                  </td>
                  <td className="py-3 px-4 text-[#8B8D86] text-[11px]">
                    {item.notes}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 bg-[#F5F5F2] border-t border-[#E7E7E2] text-[11px] text-[#8B8D86] flex items-center justify-between">
          <span>Formula: Closing Balance = Previous Balance + (Inflows − Outflows)</span>
          <span>Opening Balance: ₹{OPENING_CASH_BALANCE} Lakh</span>
        </div>
      </div>
    </div>
  );
};
