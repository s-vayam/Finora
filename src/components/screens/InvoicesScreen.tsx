import React, { useState, useMemo } from 'react';
import { 
  Search, 
  X, 
  Eye, 
  CheckCircle2,
  ArrowUpDown
} from 'lucide-react';
import { Invoice } from '../../types';
import { StatusBadge } from '../common/Badge';
import { EXCHANGE_RATES } from '../../data/mockData';

interface InvoicesScreenProps {
  invoices: Invoice[];
  onSelectInvoice: (invoice: Invoice) => void;
  onRequestMarkAsPaid: (invoice: Invoice) => void;
}

export const InvoicesScreen: React.FC<InvoicesScreenProps> = ({
  invoices,
  onSelectInvoice,
  onRequestMarkAsPaid,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [currencyFilter, setCurrencyFilter] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'dueDate' | 'amount' | 'customer'>('dueDate');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  const filteredInvoices = useMemo(() => {
    return invoices.filter((inv) => {
      const matchesSearch =
        inv.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inv.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inv.shippingReference.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus =
        statusFilter === 'All' ? true : inv.status === statusFilter;

      const matchesCurrency =
        currencyFilter === 'All' ? true : inv.currency === currencyFilter;

      return matchesSearch && matchesStatus && matchesCurrency;
    }).sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'dueDate') {
        comparison = a.dueDate.localeCompare(b.dueDate);
      } else if (sortBy === 'amount') {
        comparison = a.amount - b.amount;
      } else if (sortBy === 'customer') {
        comparison = a.customer.localeCompare(b.customer);
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [invoices, searchTerm, statusFilter, currencyFilter, sortBy, sortOrder]);

  const totalCount = invoices.length;
  const overdueCount = invoices.filter((i) => i.status === 'Overdue').length;
  const paidCount = invoices.filter((i) => i.status === 'Paid').length;

  const handleClearFilters = () => {
    setSearchTerm('');
    setStatusFilter('All');
    setCurrencyFilter('All');
  };

  const getCurrencySymbol = (curr: string) => {
    switch (curr) {
      case 'USD': return '$';
      case 'EUR': return '€';
      case 'GBP': return '£';
      default: return '₹';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Status Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E7E7E2]">
        <div>
          <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">Invoices & Payments</h2>
          <p className="text-xs text-[#8B8D86] mt-1">
            Manage international export trade invoices, track payment status, and record settlement.
          </p>
        </div>

        {/* Status Count Badges */}
        <div className="flex items-center gap-2 text-xs flex-wrap">
          <button
            onClick={() => setStatusFilter('All')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'All'
                ? 'bg-[#111111] text-white border-[#111111]'
                : 'bg-white text-[#8B8D86] border-[#E7E7E2] hover:bg-[#F5F5F2] hover:text-[#111111]'
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setStatusFilter('Overdue')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Overdue'
                ? 'bg-[#B94A48] text-white border-[#B94A48]'
                : 'bg-[#FDF2F2] text-[#B94A48] border-[#F6CECE] hover:bg-[#FBE4E4]'
            }`}
          >
            Overdue ({overdueCount})
          </button>
          <button
            onClick={() => setStatusFilter('Due soon')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Due soon'
                ? 'bg-[#A87524] text-white border-[#A87524]'
                : 'bg-[#FEF8EC] text-[#A87524] border-[#F5DCB2] hover:bg-[#FDF0D5]'
            }`}
          >
            Due Soon ({invoices.filter((i) => i.status === 'Due soon').length})
          </button>
          <button
            onClick={() => setStatusFilter('Upcoming')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Upcoming'
                ? 'bg-[#111111] text-white border-[#111111]'
                : 'bg-white text-[#8B8D86] border-[#E7E7E2] hover:bg-[#F5F5F2]'
            }`}
          >
            Upcoming ({invoices.filter((i) => i.status === 'Upcoming').length})
          </button>
          <button
            onClick={() => setStatusFilter('Paid')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Paid'
                ? 'bg-[#39765A] text-white border-[#39765A]'
                : 'bg-[#EDF7F2] text-[#39765A] border-[#BDE3D1] hover:bg-[#DCF1E6]'
            }`}
          >
            Paid ({paidCount})
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-[#E7E7E2] shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
          {/* Search Box */}
          <div className="sm:col-span-5 relative">
            <Search className="w-4 h-4 text-[#8B8D86] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by customer, invoice ID, or shipment..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-xs bg-[#F5F5F2] border border-[#E7E7E2] rounded-lg text-[#111111] focus:bg-white focus:border-[#111111] transition-colors"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8B8D86] hover:text-[#111111]"
                aria-label="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Status Dropdown */}
          <div className="sm:col-span-3 flex items-center gap-2">
            <span className="text-xs text-[#8B8D86] shrink-0 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full py-2 px-2.5 text-xs bg-[#F5F5F2] border border-[#E7E7E2] rounded-lg text-[#111111] focus:bg-white focus:border-[#111111] transition-colors"
            >
              <option value="All">All Statuses</option>
              <option value="Overdue">Overdue</option>
              <option value="Due soon">Due soon</option>
              <option value="Upcoming">Upcoming</option>
              <option value="Paid">Paid</option>
            </select>
          </div>

          {/* Currency Dropdown */}
          <div className="sm:col-span-2 flex items-center gap-2">
            <span className="text-xs text-[#8B8D86] shrink-0 font-medium">Currency:</span>
            <select
              value={currencyFilter}
              onChange={(e) => setCurrencyFilter(e.target.value)}
              className="w-full py-2 px-2.5 text-xs bg-[#F5F5F2] border border-[#E7E7E2] rounded-lg text-[#111111] focus:bg-white focus:border-[#111111] transition-colors"
            >
              <option value="All">All Currencies</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
            </select>
          </div>

          {/* Reset Filters / Result count */}
          <div className="sm:col-span-2 flex items-center justify-end gap-2 text-xs">
            {(searchTerm || statusFilter !== 'All' || currencyFilter !== 'All') ? (
              <button
                onClick={handleClearFilters}
                className="text-xs text-[#B94A48] hover:underline font-semibold flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" />
                Reset filters
              </button>
            ) : (
              <span className="text-[11px] text-[#8B8D86]">
                {filteredInvoices.length} results
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-[#E7E7E2] shadow-xs overflow-hidden">
        {filteredInvoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#E7E7E2] text-[#8B8D86] text-[11px] font-semibold bg-[#F5F5F2]">
                  <th
                    className="py-3 px-4 cursor-pointer hover:text-[#111111] transition-colors"
                    onClick={() => {
                      if (sortBy === 'customer') {
                        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                      } else {
                        setSortBy('customer');
                        setSortOrder('asc');
                      }
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Customer / Destination</span>
                      <ArrowUpDown className="w-3 h-3 text-[#111111]" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Invoice #</th>
                  <th
                    className="py-3 px-4 text-right cursor-pointer hover:text-[#111111] transition-colors"
                    onClick={() => {
                      if (sortBy === 'amount') {
                        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                      } else {
                        setSortBy('amount');
                        setSortOrder('desc');
                      }
                    }}
                  >
                    <div className="flex items-center justify-end gap-1.5">
                      <span>Amount</span>
                      <ArrowUpDown className="w-3 h-3 text-[#111111]" />
                    </div>
                  </th>
                  <th className="py-3 px-4 text-right">Base INR (₹)</th>
                  <th className="py-3 px-4">Issue Date</th>
                  <th
                    className="py-3 px-4 cursor-pointer hover:text-[#111111] transition-colors"
                    onClick={() => {
                      if (sortBy === 'dueDate') {
                        setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                      } else {
                        setSortBy('dueDate');
                        setSortOrder('asc');
                      }
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Due Date</span>
                      <ArrowUpDown className="w-3 h-3 text-[#111111]" />
                    </div>
                  </th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F5F5F2]">
                {filteredInvoices.map((inv) => {
                  const rate = EXCHANGE_RATES[inv.currency] || 85;
                  const inrValueLakh = ((inv.amount * rate) / 100000).toFixed(2);
                  return (
                    <tr
                      key={inv.id}
                      className="hover:bg-[#F5F5F2] transition-colors group"
                    >
                      <td className="py-3.5 px-4">
                        <span className="font-bold text-[#111111] block">
                          {inv.customer}
                        </span>
                        <span className="text-[11px] text-[#8B8D86]">
                          {inv.country} • {inv.paymentTerms}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-[11px] text-[#8B8D86]">
                        {inv.invoiceNumber}
                      </td>

                      <td className="py-3.5 px-4 text-right font-bold text-[#111111]">
                        {getCurrencySymbol(inv.currency)}
                        {inv.amount.toLocaleString()} {inv.currency}
                      </td>

                      <td className="py-3.5 px-4 text-right text-[#111111] font-semibold">
                        ₹{inrValueLakh} L
                      </td>

                      <td className="py-3.5 px-4 text-[#8B8D86]">
                        {inv.issueDate}
                      </td>

                      <td className="py-3.5 px-4">
                        <span
                          className={`font-semibold ${
                            inv.status === 'Overdue'
                              ? 'text-[#B94A48] font-bold'
                              : inv.status === 'Due soon'
                              ? 'text-[#A87524]'
                              : 'text-[#111111]'
                          }`}
                        >
                          {inv.dueDate}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <StatusBadge status={inv.status} size="sm" />
                      </td>

                      <td className="py-3.5 px-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => onSelectInvoice(inv)}
                            className="px-2.5 py-1 text-[11px] font-bold text-[#111111] bg-white hover:bg-[#F5F5F2] rounded-lg border border-[#E7E7E2] transition-colors inline-flex items-center gap-1"
                            title="View Invoice Details"
                          >
                            <Eye className="w-3 h-3 text-[#111111]" />
                            <span>Details</span>
                          </button>
                          {inv.status !== 'Paid' && (
                            <button
                              onClick={() => onRequestMarkAsPaid(inv)}
                              className="px-2.5 py-1 text-[11px] font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg border border-[#D9F83F] transition-colors inline-flex items-center gap-1 shadow-xs"
                              title="Mark as Paid"
                            >
                              <CheckCircle2 className="w-3 h-3 text-[#111111]" />
                              <span>Pay</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-[#F5F5F2] text-[#8B8D86] flex items-center justify-center mx-auto mb-3">
              <Search className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-[#111111]">No invoices found</h3>
            <p className="text-xs text-[#8B8D86] max-w-sm mx-auto mt-1">
              No invoice records matched &apos;{searchTerm}&apos; with current filters.
            </p>
            <button
              onClick={handleClearFilters}
              className="mt-4 px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg transition-colors"
            >
              Reset Filters
            </button>
          </div>
        )}

        <div className="px-4 py-3 bg-[#F5F5F2] border-t border-[#E7E7E2] flex flex-col sm:flex-row items-center justify-between text-[11px] text-[#8B8D86] gap-2">
          <span>
            Showing {filteredInvoices.length} of {invoices.length} recorded invoices • Fixed prototype rates (USD: ₹85, EUR: ₹99, GBP: ₹113)
          </span>
          <span className="text-[#111111] font-semibold">
            Status updates take immediate effect across dashboard widgets
          </span>
        </div>
      </div>
    </div>
  );
};
