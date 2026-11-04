import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  AlertTriangle, 
  ArrowUpRight, 
  ArrowDownRight,
  RefreshCw,
  PlusCircle,
  Sliders,
  Calendar,
  CheckCircle2,
  TrendingDown,
  Info,
  Edit2,
  X
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
import { cashflowApi } from '../../services/api';
import { 
  CashPositionBackend, 
  CashflowForecastResponse, 
  CashflowAlertItem,
  MonthlyCashflowBackend,
  CashflowScenarioResponse
} from '../../services/api/types';
import { LoadingState, ErrorBanner } from '../common/ApiStateHelpers';

interface CashFlowScreenProps {
  cashFlowData?: CashFlowMonth[];
}

export const CashFlowScreen: React.FC<CashFlowScreenProps> = ({ cashFlowData: fallbackData = [] }) => {
  const [viewMode, setViewMode] = useState<'forecast' | 'historical'>('forecast');
  const [horizonDays, setHorizonDays] = useState<30 | 60 | 90>(30);
  
  // Data states
  const [position, setPosition] = useState<CashPositionBackend | null>(null);
  const [positionChecked, setPositionChecked] = useState(false);
  const [forecast, setForecast] = useState<CashflowForecastResponse | null>(null);
  const [historical, setHistorical] = useState<MonthlyCashflowBackend[]>([]);
  const [alerts, setAlerts] = useState<CashflowAlertItem[]>([]);
  
  // Scenario states
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const [delayDays, setDelayDays] = useState<number>(0);
  const [expenseIncreasePct, setExpenseIncreasePct] = useState<number>(0);
  const [scenarioResult, setScenarioResult] = useState<CashflowScenarioResponse | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  // New Opening Position Form state
  const [showCreatePosition, setShowCreatePosition] = useState(false);
  const [newBalance, setNewBalance] = useState('2500000');
  const [newThreshold, setNewThreshold] = useState('500000');
  const [newAsOfDate, setNewAsOfDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [createPositionLoading, setCreatePositionLoading] = useState(false);
  const [createPositionError, setCreatePositionError] = useState<string | null>(null);

  // Edit Opening Position Form state
  const [showEditPosition, setShowEditPosition] = useState(false);
  const [editBalance, setEditBalance] = useState('');
  const [editThreshold, setEditThreshold] = useState('');
  const [editAsOfDate, setEditAsOfDate] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [editPositionLoading, setEditPositionLoading] = useState(false);
  const [editPositionError, setEditPositionError] = useState<string | null>(null);
  const [editPositionSuccess, setEditPositionSuccess] = useState<string | null>(null);

  // Loading & error states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);

  // Load latest cash position
  const loadPositionAndForecast = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Check latest cash position
      let currentPos: CashPositionBackend | null = null;
      try {
        currentPos = await cashflowApi.getLatestPosition();
        setPosition(currentPos);
      } catch (err: any) {
        if (err?.status === 404 || err?.status === 409) {
          setPosition(null);
        }
      } finally {
        setPositionChecked(true);
      }

      // 2. Load alerts
      try {
        const alertList = await cashflowApi.getAlerts();
        setAlerts(alertList || []);
      } catch {
        // Alerts non-fatal
      }

      // 3. Load historical monthly records
      try {
        const hist = await cashflowApi.getHistory();
        setHistorical(hist || []);
      } catch {
        // Historical non-fatal
      }

      // 4. Load forecast if position exists
      if (currentPos) {
        try {
          const fc = await cashflowApi.getForecast({ horizon_days: horizonDays });
          setForecast(fc);
        } catch (fcErr: any) {
          // If 409 OPENING_BALANCE_REQUIRED
          if (fcErr?.status === 409) {
            setPosition(null);
          } else {
            setError(fcErr);
          }
        }
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [horizonDays]);

  useEffect(() => {
    loadPositionAndForecast();
  }, [loadPositionAndForecast]);

  // Create opening cash position
  const handleCreatePosition = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatePositionLoading(true);
    setCreatePositionError(null);
    try {
      const pos = await cashflowApi.createPosition({
        as_of_date: newAsOfDate,
        balance_amount: parseFloat(newBalance),
        currency: 'INR',
        minimum_cash_threshold: parseFloat(newThreshold),
        source: 'MANUAL',
        notes: 'Initial opening position established via Finora interface',
      });
      setPosition(pos);
      setShowCreatePosition(false);
      // Immediately trigger forecast load
      const fc = await cashflowApi.getForecast({ horizon_days: horizonDays });
      setForecast(fc);
    } catch (err: any) {
      setCreatePositionError(err?.message || 'Could not record opening balance.');
    } finally {
      setCreatePositionLoading(false);
    }
  };

  // Open edit position form
  const handleOpenEditPosition = () => {
    if (!position) return;
    setEditBalance(String(position.balance_amount));
    setEditThreshold(String(position.minimum_cash_threshold ?? '500000'));
    setEditAsOfDate(position.as_of_date);
    setEditNotes('');
    setEditPositionError(null);
    setEditPositionSuccess(null);
    setShowEditPosition(true);
  };

  // Update existing opening cash position
  const handleUpdatePosition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!position) return;
    setEditPositionLoading(true);
    setEditPositionError(null);
    setEditPositionSuccess(null);
    try {
      const updated = await cashflowApi.updatePosition(position.snapshot_id, {
        balance_amount: parseFloat(editBalance),
        minimum_cash_threshold: parseFloat(editThreshold),
        as_of_date: editAsOfDate,
        notes: editNotes.trim() ? editNotes.trim() : undefined,
      });
      setPosition(updated);
      setEditPositionSuccess('Opening cash position updated successfully.');
      setTimeout(() => {
        setShowEditPosition(false);
        setEditPositionSuccess(null);
      }, 1200);

      // Immediately refresh forecast with the updated position
      const fc = await cashflowApi.getForecast({ horizon_days: horizonDays });
      setForecast(fc);
    } catch (err: any) {
      setEditPositionError(err?.message || 'Could not update opening cash balance.');
    } finally {
      setEditPositionLoading(false);
    }
  };

  // Run scenario simulation
  const handleRunScenario = async () => {
    if (!position) return;
    setScenarioLoading(true);
    try {
      const res = await cashflowApi.runScenario({
        as_of_date: position.as_of_date,
        horizon_days: horizonDays,
        payment_delay_days: delayDays,
        expense_increase_percentage: expenseIncreasePct,
        customer_delay_days: delayDays,
        expense_increase_percent: expenseIncreasePct,
      });
      setScenarioResult(res);
    } catch (err: any) {
      setError(err);
    } finally {
      setScenarioLoading(false);
    }
  };

  // Format chart data based on forecast or historical
  const chartData = useMemo(() => {
    if (viewMode === 'historical') {
      // Last 12 months of historical data
      const last12 = historical.slice(-12);
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return last12.map((m) => ({
        label: `${months[m.month - 1]} ${m.year}`,
        shortLabel: `${months[m.month - 1]} '${String(m.year).slice(-2)}`,
        inflows: Number((Number(m.total_inflows) / 100000).toFixed(1)),
        outflows: Number((Number(m.total_outflows) / 100000).toFixed(1)),
        closingBalance: Number((Number(m.closing_balance) / 100000).toFixed(1)),
        netChange: Number((Number(m.net_cash_flow) / 100000).toFixed(1)),
        notes: 'Historical settled trade transactions',
      }));
    }

    const days = forecast?.daily_projection || forecast?.daily_projections;
    if (forecast && days && days.length > 0) {
      // Aggregate into 10-day buckets for clean Recharts display
      const bucketSize = horizonDays === 30 ? 6 : horizonDays === 60 ? 10 : 15;
      const buckets: any[] = [];

      for (let i = 0; i < days.length; i += bucketSize) {
        const slice = days.slice(i, i + bucketSize);
        const lastDay = slice[slice.length - 1];
        const sumIn = slice.reduce((sum, d) => {
          const val = Number(d.expected_inflows ?? d.inflow ?? 0);
          return sum + (isNaN(val) ? 0 : val);
        }, 0);
        const sumOut = slice.reduce((sum, d) => {
          const val = Number(d.expected_outflows ?? d.outflow ?? 0);
          return sum + (isNaN(val) ? 0 : val);
        }, 0);
        const startDayStr = slice[0].date.split('-').slice(1).join('/');
        const endDayStr = lastDay.date.split('-').slice(1).join('/');
        const closingNum = Number(lastDay.closing_balance ?? 0);

        buckets.push({
          label: `${slice[0].date} to ${lastDay.date}`,
          shortLabel: `${startDayStr}–${endDayStr}`,
          inflows: Number((sumIn / 100000).toFixed(1)),
          outflows: Number((sumOut / 100000).toFixed(1)),
          closingBalance: Number((closingNum / 100000).toFixed(1)),
          netChange: Number(((sumIn - sumOut) / 100000).toFixed(1)),
          notes: `Projected receipts and payables for ${slice.length} sessions`,
        });
      }
      return buckets;
    }

    // Fallback to static props if backend position not initialized
    return fallbackData.slice(0, horizonDays === 30 ? 3 : 6);
  }, [viewMode, historical, forecast, horizonDays, fallbackData]);

  // KPI Calculations (Safely handling both nested summary and top-level fields to prevent NaN)
  const openingLakh = position
    ? Number((Number(position.balance_amount) / 100000).toFixed(1))
    : forecast?.summary?.opening_balance != null
    ? Number((Number(forecast.summary.opening_balance) / 100000).toFixed(1))
    : forecast?.opening_balance != null
    ? Number((Number(forecast.opening_balance) / 100000).toFixed(1))
    : 25.0;

  const rawInflow = forecast?.summary?.expected_inflows ?? forecast?.total_inflow;
  const totalInflowsLakh = rawInflow != null
    ? Number((Number(rawInflow) / 100000).toFixed(1))
    : chartData.reduce((acc, d) => acc + (d.inflows || 0), 0);

  const rawOutflow = forecast?.summary?.expected_outflows ?? forecast?.total_outflow;
  const totalOutflowsLakh = rawOutflow != null
    ? Number((Number(rawOutflow) / 100000).toFixed(1))
    : chartData.reduce((acc, d) => acc + (d.outflows || 0), 0);

  const rawClosing = forecast?.summary?.closing_balance ?? forecast?.closing_balance;
  const closingBalanceLakh = rawClosing != null
    ? Number((Number(rawClosing) / 100000).toFixed(1))
    : (chartData[chartData.length - 1]?.closingBalance || openingLakh);

  const totalNetLakh = Number((totalInflowsLakh - totalOutflowsLakh).toFixed(1));

  return (
    <div className="space-y-6">
      {/* Header & View Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E7E7E2]">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">Cash Flow Forecast</h2>
            <button
              type="button"
              onClick={loadPositionAndForecast}
              disabled={loading}
              className="p-1 text-[#8B8D86] hover:text-[#111111] rounded hover:bg-[#EBEBE6] transition-colors cursor-pointer"
              title="Refresh cash flow from backend"
              aria-label="Refresh forecast"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="text-xs text-[#8B8D86] mt-1">
            Predictive liquidity engine • Probability-weighted collections, rolling payables, and working capital cushion.
          </p>
        </div>

        {/* Controls: Horizon Tabs & Scenario Button */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 p-1 bg-white border border-[#E7E7E2] rounded-xl">
            <button
              onClick={() => { setViewMode('forecast'); setHorizonDays(30); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                viewMode === 'forecast' && horizonDays === 30
                  ? 'bg-[#111111] text-white shadow-xs'
                  : 'text-[#8B8D86] hover:text-[#111111]'
              }`}
            >
              30-Day
            </button>
            <button
              onClick={() => { setViewMode('forecast'); setHorizonDays(60); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                viewMode === 'forecast' && horizonDays === 60
                  ? 'bg-[#111111] text-white shadow-xs'
                  : 'text-[#8B8D86] hover:text-[#111111]'
              }`}
            >
              60-Day
            </button>
            <button
              onClick={() => { setViewMode('forecast'); setHorizonDays(90); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                viewMode === 'forecast' && horizonDays === 90
                  ? 'bg-[#111111] text-white shadow-xs'
                  : 'text-[#8B8D86] hover:text-[#111111]'
              }`}
            >
              90-Day
            </button>
            <button
              onClick={() => setViewMode('historical')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer ${
                viewMode === 'historical'
                  ? 'bg-[#111111] text-white shadow-xs'
                  : 'text-[#8B8D86] hover:text-[#111111]'
              }`}
            >
              Historical (3Y)
            </button>
          </div>

          {viewMode === 'forecast' && (
            <button
              type="button"
              onClick={() => setScenarioOpen(!scenarioOpen)}
              className={`px-3 py-2 text-xs font-semibold border rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs ${
                scenarioOpen
                  ? 'bg-[#111111] text-white border-[#111111]'
                  : 'bg-white text-[#111111] border-[#E7E7E2] hover:bg-[#F5F5F2]'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>What-If Simulator</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && <ErrorBanner error={error} onRetry={loadPositionAndForecast} />}

      {/* Missing Opening Balance Alert & Form */}
      {positionChecked && !position && (
        <div className="p-5 rounded-xl bg-[#FEF8EC] border border-[#F5DCB2] text-xs">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-5 h-5 text-[#A87524] shrink-0 mt-0.5" />
              <div>
                <h4 className="font-bold text-sm text-[#A87524]">Opening Cash Position Required</h4>
                <p className="text-[11px] text-[#8B8D86] mt-0.5 max-w-xl leading-relaxed">
                  Finora&apos;s Phase 4 predictive liquidity engine requires a verified cash position snapshot to roll forward daily projections. Historical December 2025 closing balances are not assumed as current liquidity.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowCreatePosition(!showCreatePosition)}
              className="px-3.5 py-1.5 bg-[#244E3D] hover:bg-[#1C3E30] text-white font-semibold text-xs rounded-lg transition-colors cursor-pointer shadow-xs shrink-0 flex items-center gap-1"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>{showCreatePosition ? 'Close Form' : 'Establish Position'}</span>
            </button>
          </div>

          {showCreatePosition && (
            <form onSubmit={handleCreatePosition} className="mt-4 pt-4 border-t border-[#F5DCB2] grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
              <div>
                <label className="text-[10px] font-bold text-neutral-700 block mb-1">Opening Balance (₹ INR)</label>
                <input
                  type="number"
                  value={newBalance}
                  onChange={(e) => setNewBalance(e.target.value)}
                  className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs font-mono"
                  placeholder="e.g. 2500000"
                  required
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-neutral-700 block mb-1">Min Threshold (₹ INR)</label>
                <input
                  type="number"
                  value={newThreshold}
                  onChange={(e) => setNewThreshold(e.target.value)}
                  className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs font-mono"
                  placeholder="e.g. 500000"
                  required
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-neutral-700 block mb-1">As Of Date</label>
                <input
                  type="date"
                  value={newAsOfDate}
                  onChange={(e) => setNewAsOfDate(e.target.value)}
                  className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs"
                  required
                />
              </div>
              <div>
                <button
                  type="submit"
                  disabled={createPositionLoading}
                  className="w-full p-2 bg-[#244E3D] hover:bg-[#1C3E30] text-white font-bold text-xs rounded-lg transition-colors cursor-pointer shadow-xs flex items-center justify-center gap-1"
                >
                  {createPositionLoading ? 'Saving...' : 'Confirm Position'}
                </button>
              </div>
              {createPositionError && (
                <p className="col-span-full text-xs text-[#B94A48] mt-1">{createPositionError}</p>
              )}
            </form>
          )}
        </div>
      )}

      {/* What-If Simulator Panel */}
      {scenarioOpen && (
        <div className="p-5 bg-white border border-[#E7E7E2] rounded-xl shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#F5F5F2] pb-2">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[#244E3D]" />
              <h3 className="font-bold text-sm text-[#111111]">What-If Liquidity Stress Simulator</h3>
            </div>
            <span className="text-[11px] text-[#8B8D86]">Server-authoritative calculation via Phase 4 scenario engine</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-[#111111]">Customer Payment Delay:</span>
                <span className="font-bold text-[#244E3D]">+{delayDays} days</span>
              </div>
              <input
                type="range"
                min="0"
                max="60"
                step="5"
                value={delayDays}
                onChange={(e) => setDelayDays(parseInt(e.target.value, 10))}
                className="w-full accent-[#244E3D] cursor-pointer"
              />
              <span className="text-[10px] text-[#8B8D86] block mt-1">Pushes expected invoice collections forward</span>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-[#111111]">Vendor Expense Surge:</span>
                <span className="font-bold text-[#B94A48]">+{expenseIncreasePct}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="50"
                step="5"
                value={expenseIncreasePct}
                onChange={(e) => setExpenseIncreasePct(parseInt(e.target.value, 10))}
                className="w-full accent-[#B94A48] cursor-pointer"
              />
              <span className="text-[10px] text-[#8B8D86] block mt-1">Inflationary pressure on trade payables</span>
            </div>

            <div className="flex items-end">
              <button
                type="button"
                onClick={handleRunScenario}
                disabled={scenarioLoading || !position}
                className="w-full py-2 bg-[#111111] hover:bg-[#222222] text-white text-xs font-bold rounded-lg transition-colors cursor-pointer shadow-xs disabled:opacity-50"
              >
                {scenarioLoading ? 'Simulating Stress...' : 'Execute Stress Test'}
              </button>
            </div>
          </div>

          {scenarioResult && (() => {
            const baselineEnding = Number(scenarioResult.baseline_ending_cash ?? scenarioResult.baseline?.closing_balance ?? 0);
            const scenarioEnding = Number(scenarioResult.scenario_ending_cash ?? scenarioResult.scenario?.closing_balance ?? 0);
            const netDiff = Number(scenarioResult.net_cash_difference ?? scenarioResult.difference_in_closing_balance ?? (scenarioEnding - baselineEnding));
            const pressureText = scenarioResult.explanation ?? scenarioResult.liquidity_pressure ?? (netDiff < 0 ? `-${(Math.abs(netDiff) / 100000).toFixed(2)} L` : 'Neutral');

            return (
              <div className="mt-4 p-4 rounded-xl bg-[#F5F5F2] border border-[#E7E7E2] grid grid-cols-1 sm:grid-cols-4 gap-3 text-center">
                <div>
                  <span className="text-[10px] text-[#8B8D86] block">Baseline Closing</span>
                  <span className="text-base font-bold text-[#111111]">
                    ₹{(baselineEnding / 100000).toFixed(2)} L
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#8B8D86] block">Stressed Closing</span>
                  <span className="text-base font-bold text-[#B94A48]">
                    ₹{(scenarioEnding / 100000).toFixed(2)} L
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#8B8D86] block">Liquidity Variance</span>
                  <span className="text-base font-bold text-[#B94A48]">
                    {netDiff < 0 ? '-' : '+'}₹{(Math.abs(netDiff) / 100000).toFixed(2)} L
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-[#8B8D86] block">Liquidity Pressure</span>
                  <span className="text-xs font-bold px-2 py-0.5 rounded-full inline-block mt-1 bg-white border border-[#E7E7E2] text-[#111111] truncate max-w-full" title={String(pressureText)}>
                    {scenarioResult.liquidity_pressure || (netDiff < 0 ? `Stress: -₹${(Math.abs(netDiff) / 100000).toFixed(1)}L` : 'Stable')}
                  </span>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Edit Opening Position Form Modal / Panel */}
      {showEditPosition && position && (
        <div className="p-5 rounded-xl bg-white border border-[#244E3D] shadow-sm text-xs space-y-3">
          <div className="flex items-start justify-between pb-3 border-b border-[#E7E7E2]">
            <div>
              <div className="flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-[#244E3D]" />
                <h4 className="font-bold text-sm text-[#111111]">Edit Opening Cash Position</h4>
              </div>
              <p className="text-[11px] text-[#8B8D86] mt-0.5">
                Snapshot ID: <span className="font-mono text-neutral-700">{position.snapshot_id}</span> • Modifying this position recalculates downstream rolling forecasts.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setShowEditPosition(false);
                setEditPositionError(null);
                setEditPositionSuccess(null);
              }}
              className="p-1 text-[#8B8D86] hover:text-[#111111] rounded hover:bg-[#F5F5F2] cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <form onSubmit={handleUpdatePosition} className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end">
            <div>
              <label className="text-[10px] font-bold text-neutral-700 block mb-1">Opening Balance (₹ INR)</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={editBalance}
                onChange={(e) => setEditBalance(e.target.value)}
                className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs font-mono"
                required
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-neutral-700 block mb-1">Min Threshold (₹ INR)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={editThreshold}
                onChange={(e) => setEditThreshold(e.target.value)}
                className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs font-mono"
                required
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-neutral-700 block mb-1">As Of Date</label>
              <input
                type="date"
                value={editAsOfDate}
                onChange={(e) => setEditAsOfDate(e.target.value)}
                className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs"
                required
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={editPositionLoading}
                  className="flex-1 p-2 bg-[#244E3D] hover:bg-[#1C3E30] text-white font-bold text-xs rounded-lg transition-colors cursor-pointer shadow-xs flex items-center justify-center gap-1"
                >
                  {editPositionLoading ? 'Updating...' : 'Save Changes'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowEditPosition(false)}
                  className="px-3 py-2 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 font-semibold text-xs rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>

            <div className="col-span-full">
              <label className="text-[10px] font-bold text-neutral-700 block mb-1">Audit Note / Reason for Change (Optional)</label>
              <input
                type="text"
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="e.g. Bank statement reconciliation adjustment"
                className="w-full p-2 bg-white border border-[#E7E7E2] rounded-lg text-xs"
                maxLength={500}
              />
            </div>

            {editPositionError && (
              <p className="col-span-full text-xs text-[#B94A48] mt-1 font-medium">{editPositionError}</p>
            )}
            {editPositionSuccess && (
              <p className="col-span-full text-xs text-[#244E3D] mt-1 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {editPositionSuccess}
              </p>
            )}
          </form>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Opening Balance */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs relative">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">Opening Liquidity</span>
            {position && (
              <button
                type="button"
                onClick={handleOpenEditPosition}
                className="text-[11px] font-semibold text-[#244E3D] hover:text-[#1C3E30] flex items-center gap-1 cursor-pointer bg-[#F5F5F2] hover:bg-[#EBEBE6] px-2 py-0.5 rounded transition-colors"
                title="Edit verified cash position"
              >
                <Edit2 className="w-3 h-3" />
                <span>Edit</span>
              </button>
            )}
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{openingLakh.toFixed(1)} L
            </span>
            <span className="text-xs text-[#8B8D86]">INR</span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            {position ? `Snapshot as of ${position.as_of_date}` : 'Baseline bank & EEFC balances'}
          </span>
        </div>

        {/* Period Inflows */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">
            {viewMode === 'historical' ? 'Historical Inflows' : 'Projected Inflows'}
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{totalInflowsLakh.toFixed(1)} L
            </span>
            <span className="text-xs text-[#39765A] font-semibold flex items-center">
              <ArrowUpRight className="w-3.5 h-3.5" />
              Receipts
            </span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            {viewMode === 'historical' ? 'Last 12 calendar months' : `Probability-weighted for ${horizonDays} days`}
          </span>
        </div>

        {/* Period Outflows */}
        <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">
            {viewMode === 'historical' ? 'Historical Outflows' : 'Projected Outflows'}
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{totalOutflowsLakh.toFixed(1)} L
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
          <span className="text-xs text-[#8B8D86] font-semibold uppercase tracking-wider block">
            {viewMode === 'historical' ? 'Settled Position' : 'Closing Liquidity'}
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-extrabold text-[#111111]">
              ₹{closingBalanceLakh.toFixed(1)} L
            </span>
            <span className={`text-xs font-bold ${totalNetLakh >= 0 ? 'text-[#39765A]' : 'text-[#B94A48]'}`}>
              {totalNetLakh >= 0 ? `+₹${totalNetLakh}L` : `-₹${Math.abs(totalNetLakh)}L`} Net
            </span>
          </div>
          <span className="text-[11px] text-[#8B8D86] block mt-3 pt-2.5 border-t border-[#F5F5F2]">
            {viewMode === 'historical' ? 'Authoritative historical closing' : `Projected at day ${horizonDays}`}
          </span>
        </div>
      </div>

      {/* Liquidity Alerts Banner */}
      {alerts && alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((al) => (
            <div
              key={al.alert_id}
              className={`p-4 rounded-xl text-xs flex items-start gap-3 border ${
                al.severity === 'HIGH'
                  ? 'bg-[#FDF2F2] border-[#F6CECE] text-[#B94A48]'
                  : 'bg-[#FEF8EC] border-[#F5DCB2] text-[#A87524]'
              }`}
            >
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="font-bold text-xs">{al.title}</h4>
                <p className="text-[11px] leading-relaxed opacity-90">{al.description}</p>
                {al.action_needed && (
                  <p className="text-[11px] font-semibold underline">{al.action_needed}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Chart Section */}
      <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs">
        <div className="flex items-center justify-between pb-3 border-b border-[#F5F5F2]">
          <div>
            <h3 className="font-bold text-sm text-[#111111]">
              {viewMode === 'historical'
                ? 'Historical Settled Monthly Cash Flow (2023–2025)'
                : `Projected Cash Flow Roll-Forward (${horizonDays}-Day Horizon)`}
            </h3>
            <p className="text-xs text-[#8B8D86] mt-0.5">
              Unit: ₹ Lakh • Receipts in Lime, Payables in Charcoal, dashed line indicates closing working capital balance
            </p>
          </div>
          <span className="text-[11px] font-semibold text-[#111111] bg-[#F5F5F2] px-2.5 py-0.5 rounded-full border border-[#E7E7E2]">
            {viewMode === 'historical' ? 'Historical Archive' : `${horizonDays}-Day Horizon`}
          </span>
        </div>

        <div className="mt-4 h-72 w-full">
          {loading && chartData.length === 0 ? (
            <LoadingState label="Computing liquidity roll-forward..." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={chartData}
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
                <Bar dataKey="inflows" name="Export Receipts (₹L)" fill="#D9F83F" stroke="#B8D626" radius={[4, 4, 0, 0]} />
                <Bar dataKey="outflows" name="Vendor Disbursements (₹L)" fill="#111111" radius={[4, 4, 0, 0]} />
                <Line
                  type="monotone"
                  dataKey="closingBalance"
                  name="Closing Liquidity (₹L)"
                  stroke="#111111"
                  strokeWidth={2.5}
                  strokeDasharray="4 4"
                  dot={{ fill: '#D9F83F', stroke: '#111111', strokeWidth: 2, r: 4 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Breakdown Schedule Table */}
      <div className="bg-white rounded-xl border border-[#E7E7E2] shadow-xs overflow-hidden">
        <div className="p-4 border-b border-[#E7E7E2] bg-[#F5F5F2] flex items-center justify-between">
          <div>
            <h3 className="font-bold text-sm text-[#111111]">
              {viewMode === 'historical' ? 'Historical Cash Transaction Reconciliation' : 'Rolling Liquidity Schedule'}
            </h3>
            <p className="text-xs text-[#8B8D86] mt-0.5">
              Authoritative values synchronized with backend database records
            </p>
          </div>
          <span className="text-[11px] font-mono text-[#8B8D86]">
            {viewMode === 'historical' ? 'Status: Settled' : 'Status: Model Projected'}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#E7E7E2] text-[#8B8D86] text-[11px] font-semibold bg-[#F5F5F2]">
                <th className="py-2.5 px-4">Period / Window</th>
                <th className="py-2.5 px-4 text-right">Inflows (₹L)</th>
                <th className="py-2.5 px-4 text-right">Outflows (₹L)</th>
                <th className="py-2.5 px-4 text-right">Net Change (₹L)</th>
                <th className="py-2.5 px-4 text-right">Closing Balance (₹L)</th>
                <th className="py-2.5 px-4">Operational Intelligence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F5F5F2]">
              {chartData.map((item, idx) => (
                <tr key={idx} className="hover:bg-[#F5F5F2] transition-colors">
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

        <div className="px-4 py-3 bg-[#F5F5F2] border-t border-[#E7E7E2] text-[11px] text-[#8B8D86] flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Formula: Closing Balance = Opening Position + Cumulative (Inflows − Outflows)</span>
          <span>Verified against Finora Phase 4 Predictive Cash Flow Engine</span>
        </div>
      </div>
    </div>
  );
};
