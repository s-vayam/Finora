import React, { useState } from 'react';
import { 
  Calculator, 
  Info, 
  ArrowUpRight, 
  ArrowDownRight,
  AlertCircle,
  RotateCcw
} from 'lucide-react';
import { FXExposureRecord } from '../../types';
import { EXCHANGE_RATES_LABEL } from '../../data/mockData';

interface FXRiskScreenProps {
  fxRecords: FXExposureRecord[];
}

export const FXRiskScreen: React.FC<FXRiskScreenProps> = ({ fxRecords }) => {
  const [selectedCurrency, setSelectedCurrency] = useState<'USD' | 'EUR' | 'GBP' | 'ALL'>('USD');
  const [inputString, setInputString] = useState<string>('5');
  const [rateShiftPercent, setRateShiftPercent] = useState<number>(5);
  const [validationError, setValidationError] = useState<string | null>(null);

  const totalInrEquivalent = fxRecords.reduce((sum, r) => sum + r.inrEquivalent, 0);

  let targetExposureAmount = 0;
  let targetCurrencyCode = 'USD';
  let targetBaseRate = 85;
  let targetSymbol = '$';
  let targetBaseInr = 0;

  if (selectedCurrency === 'ALL') {
    targetExposureAmount = 0;
    targetBaseInr = totalInrEquivalent;
  } else {
    const record = fxRecords.find((r) => r.currency === selectedCurrency) || fxRecords[0];
    targetExposureAmount = record.exposureAmount;
    targetCurrencyCode = record.currency;
    targetBaseRate = record.illustrativeRate;
    targetSymbol = record.symbol;
    targetBaseInr = record.inrEquivalent;
  }

  // Safe validation logic (Rule 5: Prevent Errors)
  const handleInputChange = (rawVal: string) => {
    setInputString(rawVal);

    if (rawVal.trim() === '') {
      setValidationError('Percentage shift cannot be empty. Enter a value between -25% and +25%.');
      return;
    }

    const num = Number(rawVal);
    if (isNaN(num)) {
      setValidationError('Invalid input. Please enter a numeric percentage (e.g. -5, 2.5, 10).');
      return;
    }

    if (!isFinite(num)) {
      setValidationError('Please enter a finite number.');
      return;
    }

    if (num < -25 || num > 25) {
      setValidationError('Simulation percentage must be between -25% and +25% for realistic stress testing.');
      return;
    }

    // Input is valid
    setValidationError(null);
    setRateShiftPercent(num);
  };

  const handleSelectPreset = (preset: number) => {
    setInputString(String(preset));
    setRateShiftPercent(preset);
    setValidationError(null);
  };

  const handleResetToZero = () => {
    handleSelectPreset(0);
  };

  // Recalculations using valid rateShiftPercent
  const effectiveShift = validationError ? 0 : rateShiftPercent;
  const multiplier = 1 + effectiveShift / 100;
  const recalculatedInr = Math.round(targetBaseInr * multiplier);
  const deltaInr = recalculatedInr - targetBaseInr;
  const deltaLakh = (Math.abs(deltaInr) / 100000).toFixed(2);
  const recalculatedLakh = (recalculatedInr / 100000).toFixed(2);
  const baseLakh = (targetBaseInr / 100000).toFixed(2);
  const simulatedRate = (targetBaseRate * (1 + effectiveShift / 100)).toFixed(2);

  const shiftPresets = [-5, -2, 0, 2, 5];
  const topCurrency = [...fxRecords].sort((a, b) => b.inrEquivalent - a.inrEquivalent)[0];

  return (
    <div className="space-y-6">
      {/* Page Title & Exchange Rate Disclaimer */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E7E7E2]">
        <div>
          <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">Foreign Exchange (FX) Risk</h2>
          <p className="text-xs text-[#8B8D86] mt-1">
            Monitor unhedged foreign receivables, evaluate currency sensitivity, and assess margin exposure.
          </p>
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#FEF8EC] border border-[#F5DCB2] text-xs font-semibold text-[#A87524]">
          <Info className="w-4 h-4 shrink-0 text-[#A87524]" />
          <span>{EXCHANGE_RATES_LABEL}</span>
        </div>
      </div>

      {/* FX Rates Reference Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {fxRecords.map((item) => (
          <div
            key={item.currency}
            className="p-5 rounded-xl bg-white border border-[#E7E7E2] shadow-xs flex items-center justify-between"
          >
            <div>
              <span className="text-[11px] font-semibold text-[#8B8D86] block uppercase tracking-wider">
                {item.currency} / INR Conversion Rate
              </span>
              <div className="mt-1.5 flex items-baseline gap-2">
                <span className="text-2xl font-extrabold text-[#111111]">
                  ₹{item.illustrativeRate}.00
                </span>
                <span className="text-xs text-[#8B8D86]">per 1 {item.currency}</span>
              </div>
            </div>
            <div className="w-9 h-9 rounded-lg bg-[#F5F5F2] text-[#111111] font-bold text-sm flex items-center justify-center border border-[#E7E7E2]">
              {item.symbol}
            </div>
          </div>
        ))}
      </div>

      {/* Exposure Breakdown Cards */}
      <div className="bg-white p-5 rounded-xl border border-[#E7E7E2] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-[#F5F5F2] gap-2">
          <div>
            <h3 className="font-bold text-sm text-[#111111]">
              Foreign Currency Open Exposure & Historical Review
            </h3>
            <p className="text-xs text-[#8B8D86] mt-0.5">
              Comparison against previous review cycle (₹{(totalInrEquivalent / 100000).toFixed(2)} Lakh total portfolio)
            </p>
          </div>
          <div className="px-3 py-1 rounded-full bg-[#ECF9A8] text-[#111111] text-xs font-bold border border-[#D9F83F]">
            Dominant Risk: {topCurrency.currency} ({topCurrency.sharePercent}% of total)
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {fxRecords.map((record) => {
            const diffAmount = record.exposureAmount - record.previousExposureAmount;
            const diffPercent = ((diffAmount / record.previousExposureAmount) * 100).toFixed(1);
            const isIncrease = diffAmount > 0;

            return (
              <div
                key={record.currency}
                className="p-4 rounded-xl border border-[#E7E7E2] bg-[#F5F5F2] space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-[#111111]">
                    {record.currency} Exposure
                  </span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-white border border-[#E7E7E2] text-[#111111]">
                    {record.sharePercent}% Share
                  </span>
                </div>

                <div>
                  <div className="text-2xl font-extrabold text-[#111111]">
                    {record.symbol}{record.exposureAmount.toLocaleString()}
                  </div>
                  <div className="text-xs text-[#111111] font-semibold mt-0.5">
                    ≈ ₹{record.inrLakh.toFixed(2)} Lakh INR
                  </div>
                </div>

                <div className="pt-2 border-t border-[#E7E7E2] flex items-center justify-between text-xs">
                  <span className="text-[#8B8D86]">Vs Prev Period:</span>
                  <div
                    className={`inline-flex items-center gap-1 font-bold ${
                      isIncrease ? 'text-[#B94A48]' : 'text-[#39765A]'
                    }`}
                  >
                    {isIncrease ? (
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    ) : (
                      <ArrowDownRight className="w-3.5 h-3.5" />
                    )}
                    <span>
                      {isIncrease ? '+' : ''}
                      {diffPercent}% ({record.symbol}{Math.abs(diffAmount).toLocaleString()})
                    </span>
                  </div>
                </div>

                <p className="text-[11px] text-[#8B8D86] leading-relaxed pt-1">
                  Previous: {record.symbol}{record.previousExposureAmount.toLocaleString()} • Settlement via Mumbai branch nostro.
                </p>
              </div>
            );
          })}
        </div>

        {/* Analytical Note on Discrepancy */}
        <div className="p-4 rounded-xl bg-[#F5F5F2] border border-[#E7E7E2] text-xs text-[#111111] space-y-1">
          <p className="font-bold text-xs text-[#111111] flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-[#111111]" />
            Portfolio Metric Explanation
          </p>
          <p className="text-[#8B8D86] text-[11px] leading-relaxed">
            The dashboard displays an aggregate FX exposure metric of <strong>$84,200 USD equivalent</strong> representing net unhedged forward risk for the next 45 days. The open receivables schedule detailed above sums to <strong>$58,000 USD</strong>, <strong>€22,000 EUR</strong>, and <strong>£9,000 GBP</strong> (totaling <strong>₹81.25 Lakh</strong> converted at prototype rates). The difference arises because the dashboard figure specifically reflects forward commitments and pipeline dispatches.
          </p>
        </div>
      </div>

      {/* Sensitivity Calculator Section */}
      <div className="bg-white p-6 rounded-xl border border-[#E7E7E2] shadow-xs space-y-6">
        <div className="flex items-center justify-between pb-3 border-b border-[#F5F5F2]">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-[#F5F5F2] text-[#111111]">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-[#111111]">
                Exchange Rate Sensitivity Calculator
              </h3>
              <p className="text-xs text-[#8B8D86] mt-0.5">
                Simulate percentage movements in INR conversion rates against your trade receivables
              </p>
            </div>
          </div>
        </div>

        {/* Calculator Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
          <div className="space-y-4">
            {/* Currency Selector */}
            <div>
              <label className="block text-xs font-semibold text-[#111111] mb-1.5">
                Target Portfolio / Currency
              </label>
              <div className="grid grid-cols-4 gap-2">
                {(['USD', 'EUR', 'GBP', 'ALL'] as const).map((curr) => (
                  <button
                    key={curr}
                    onClick={() => setSelectedCurrency(curr)}
                    className={`py-2 text-xs font-bold rounded-lg border transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] ${
                      selectedCurrency === curr
                        ? 'bg-[#111111] text-white border-[#111111]'
                        : 'bg-[#F5F5F2] text-[#111111] border-[#E7E7E2] hover:bg-[#EBEBE6]'
                    }`}
                  >
                    {curr === 'ALL' ? 'Total (All)' : curr}
                  </button>
                ))}
              </div>
            </div>

            {/* Percentage Shift Selector */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="fx-shift-input" className="text-xs font-semibold text-[#111111]">
                  Simulated Exchange Rate Shift (% change in INR per unit)
                </label>
                <span className="text-[11px] text-[#8B8D86]">Range: -25% to +25%</span>
              </div>
              <div className="grid grid-cols-5 gap-1.5">
                {shiftPresets.map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => handleSelectPreset(pct)}
                    className={`py-2 text-xs font-bold rounded-lg border transition-colors focus-visible:ring-2 focus-visible:ring-[#111111] ${
                      !validationError && rateShiftPercent === pct
                        ? 'bg-[#D9F83F] text-[#111111] border-[#D9F83F] shadow-xs'
                        : 'bg-[#F5F5F2] text-[#111111] border-[#E7E7E2] hover:bg-[#EBEBE6]'
                    }`}
                  >
                    {pct > 0 ? `+${pct}%` : `${pct}%`}
                  </button>
                ))}
              </div>

              {/* Slider and Safe Validated Input */}
              <div className="mt-3.5 space-y-2">
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="-25"
                    max="25"
                    step="1"
                    value={validationError ? 0 : rateShiftPercent}
                    onChange={(e) => handleInputChange(e.target.value)}
                    className="flex-1 accent-[#111111] cursor-pointer"
                    aria-label="Percentage shift slider"
                  />
                  <div className="flex items-center gap-1.5">
                    <input
                      id="fx-shift-input"
                      type="text"
                      value={inputString}
                      onChange={(e) => handleInputChange(e.target.value)}
                      className={`w-20 py-1.5 px-2 text-xs font-bold text-center border rounded-lg bg-[#F5F5F2] text-[#111111] focus:bg-white focus-visible:ring-2 ${
                        validationError
                          ? 'border-[#B94A48] focus-visible:ring-[#B94A48] bg-[#FDF2F2]'
                          : 'border-[#E7E7E2] focus-visible:ring-[#111111]'
                      }`}
                      placeholder="0"
                      aria-invalid={!!validationError}
                      aria-describedby={validationError ? "fx-validation-error" : undefined}
                    />
                    <span className="text-xs text-[#8B8D86] font-semibold">%</span>
                  </div>
                </div>

                {/* Inline Error Message & Quick Fix (Rule 5: Prevent Errors) */}
                {validationError && (
                  <div 
                    id="fx-validation-error" 
                    className="p-2.5 rounded-lg bg-[#FDF2F2] border border-[#F6CECE] text-xs text-[#B94A48] flex items-center justify-between gap-2"
                  >
                    <div className="flex items-center gap-1.5">
                      <AlertCircle className="w-4 h-4 shrink-0 text-[#B94A48]" />
                      <span>{validationError}</span>
                    </div>
                    <button
                      type="button"
                      onClick={handleResetToZero}
                      className="px-2 py-0.5 rounded bg-white text-[11px] font-bold text-[#111111] border border-[#E7E7E2] hover:bg-[#F5F5F2] shrink-0"
                    >
                      Reset to 0%
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Base Exposure Reference with Complete Context (Rule 8: Memory Load) */}
            <div className="p-3.5 bg-[#F5F5F2] border border-[#E7E7E2] rounded-xl text-xs space-y-1.5">
              <span className="text-[#8B8D86] block text-[11px] font-medium">Calculation Assumptions & Baseline:</span>
              <div className="font-bold text-[#111111] text-xs">
                {selectedCurrency === 'ALL'
                  ? `Full Open Portfolio: USD $58k + EUR €22k + GBP £9k`
                  : `Target: ${targetSymbol}${targetExposureAmount.toLocaleString()} ${targetCurrencyCode} (Benchmark: ₹${targetBaseRate}.00 / ${targetCurrencyCode})`}
              </div>
              <div className="flex items-center justify-between text-xs pt-1 border-t border-[#E7E7E2]">
                <span className="text-[#8B8D86]">Base Value:</span>
                <span className="font-bold text-[#111111]">₹{baseLakh} Lakh INR</span>
              </div>
              {selectedCurrency !== 'ALL' && (
                <div className="flex items-center justify-between text-[11px] text-[#8B8D86]">
                  <span>Stress Rate:</span>
                  <span className="font-mono text-[#111111]">₹{simulatedRate} / {targetCurrencyCode} ({effectiveShift >= 0 ? `+${effectiveShift}%` : `${effectiveShift}%`})</span>
                </div>
              )}
            </div>
          </div>

          {/* Calculator Output Card (Pro Finance Dark Panel style) */}
          <div className="p-5 rounded-xl bg-[#111111] text-white space-y-4 shadow-sm border border-[#222222]">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-xs uppercase tracking-wider text-[#D9F83F]">
                Sensitivity Projection Results
              </h4>
              {validationError && (
                <span className="text-[10px] text-[#FF8585] font-semibold bg-[#222] px-2 py-0.5 rounded">
                  Calculations Paused
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 bg-[#1C1C1C] rounded-lg border border-[#333333]">
                <span className="text-[11px] text-[#8B8D86] block">Recalculated INR Value</span>
                <span className="text-xl font-bold text-[#D9F83F] mt-0.5 block font-mono">
                  ₹{recalculatedLakh} Lakh
                </span>
                <span className="text-[10px] text-[#8B8D86]">
                  After {effectiveShift >= 0 ? `+${effectiveShift}%` : `${effectiveShift}%`} shift
                </span>
              </div>

              <div className="p-3.5 bg-[#1C1C1C] rounded-lg border border-[#333333]">
                <span className="text-[11px] text-[#8B8D86] block">Net Realization Variance</span>
                <span
                  className={`text-xl font-bold mt-0.5 block font-mono ${
                    deltaInr > 0
                      ? 'text-[#39765A]'
                      : deltaInr < 0
                      ? 'text-[#B94A48]'
                      : 'text-white'
                  }`}
                >
                  {deltaInr > 0 ? '+' : deltaInr < 0 ? '-' : ''}₹{deltaLakh} Lakh
                </span>
                <span className="text-[10px] text-[#8B8D86]">
                  {deltaInr >= 0 ? 'Export gain' : 'Export contraction'}
                </span>
              </div>
            </div>

            {/* Directional Explanation */}
            <div className="p-3.5 bg-[#1C1C1C] rounded-lg border border-[#333333] space-y-1.5 text-xs">
              <span className="font-semibold text-white block">
                Directional Explanation
              </span>
              <p className="text-[#E7E7E2] text-[11px] leading-relaxed">
                {effectiveShift > 0 ? (
                  <>
                    A <strong>+{effectiveShift}% depreciation of INR</strong> (meaning the rupee rate per foreign currency increases from benchmark) increases your converted export receipts by <strong className="text-[#D9F83F]">₹{deltaLakh} Lakh</strong> on existing trade receivables upon settlement.
                  </>
                ) : effectiveShift < 0 ? (
                  <>
                    A <strong>{effectiveShift}% appreciation of INR</strong> (meaning fewer rupees per foreign currency) decreases your expected rupee realization by <strong className="text-[#FF8585]">₹{deltaLakh} Lakh</strong>, reducing export gross margins unless hedged with forward contracts.
                  </>
                ) : (
                  <>
                    At 0% change, realization matches baseline conversions exactly (₹{baseLakh} Lakh).
                  </>
                )}
              </p>
              <p className="text-[10px] text-[#8B8D86] italic pt-1 border-t border-[#333333]">
                Non-prescriptive scenario simulation. Actual settlement depends on spot rate on value date.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
