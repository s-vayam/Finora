/**
 * Safe formatting utilities for dates and financial monetary values
 */

/**
 * Parses a YYYY-MM-DD date string safely without timezone conversion bugs.
 * Avoids converting UTC midnight into the previous calendar date in Western hemispheres.
 */
export function parseDateOnly(dateStr: string | null | undefined): { year: number; month: number; day: number } | null {
  if (!dateStr || typeof dateStr !== 'string') return null;
  const parts = dateStr.trim().split('T')[0].split('-');
  if (parts.length < 3) return null;
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10);
  const day = parseInt(parts[2], 10);
  if (isNaN(year) || isNaN(month) || isNaN(day)) return null;
  return { year, month, day };
}

/**
 * Formats a date-only string into a user-friendly display date (e.g. "26 Oct 2026")
 */
export function formatDateDisplay(dateStr: string | null | undefined, fallback = '—'): string {
  const parsed = parseDateOnly(dateStr);
  if (!parsed) return fallback;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthName = months[parsed.month - 1] || '';
  return `${parsed.day.toString().padStart(2, '0')} ${monthName} ${parsed.year}`;
}

/**
 * Formats a monetary number with proper currency symbols and thousands separators.
 */
export function formatCurrency(
  amount: number | string | null | undefined,
  currency = 'INR',
  options: { maximumFractionDigits?: number; minimumFractionDigits?: number } = {}
): string {
  if (amount === null || amount === undefined || amount === '') return '—';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '—';

  const symbols: Record<string, string> = {
    INR: '₹',
    USD: '$',
    EUR: '€',
    GBP: '£',
  };

  const symbol = symbols[currency.toUpperCase()] || `${currency} `;
  const formatted = Math.abs(num).toLocaleString('en-IN', {
    maximumFractionDigits: options.maximumFractionDigits ?? 2,
    minimumFractionDigits: options.minimumFractionDigits ?? (options.maximumFractionDigits === 0 ? 0 : 2),
  });

  const sign = num < 0 ? '-' : '';
  return `${sign}${symbol}${formatted}`;
}

/**
 * Formats large INR amounts in Indian numerical system (Lakhs / Crores)
 */
export function formatInrLakhs(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '—';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '—';

  const abs = Math.abs(num);
  const sign = num < 0 ? '-' : '';

  if (abs >= 10000000) {
    const cr = (abs / 10000000).toFixed(2);
    return `${sign}₹${cr} Cr`;
  }
  const l = (abs / 100000).toFixed(2);
  return `${sign}₹${l} L`;
}
