import React, { useState, useMemo } from 'react';
import { 
  FolderLock, 
  Search, 
  X, 
  AlertCircle, 
  Eye, 
  CheckCircle2,
  FileText
} from 'lucide-react';
import { TradeDocument } from '../../types';
import { StatusBadge } from '../common/Badge';

interface DocumentsScreenProps {
  documents: TradeDocument[];
  onSelectDocument: (doc: TradeDocument) => void;
  onUpdateStatus: (docId: string, newStatus: 'Complete' | 'Pending') => void;
}

export const DocumentsScreen: React.FC<DocumentsScreenProps> = ({
  documents,
  onSelectDocument,
  onUpdateStatus,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('All');

  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch =
        doc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.customer.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.shipmentRef.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.issuingAuthority.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus =
        statusFilter === 'All' ? true : doc.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [documents, searchTerm, statusFilter]);

  const totalCount = documents.length;
  const missingCount = documents.filter((d) => d.status === 'Missing').length;
  const pendingCount = documents.filter((d) => d.status === 'Pending').length;
  const completeCount = documents.filter((d) => d.status === 'Complete').length;

  const handleClearFilters = () => {
    setSearchTerm('');
    setStatusFilter('All');
  };

  return (
    <div className="space-y-6">
      {/* Header & Status Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E7E7E2]">
        <div>
          <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">Trade Documents</h2>
          <p className="text-xs text-[#8B8D86] mt-1">
            Track statutory customs clearance, bills of lading, and export compliance documents.
          </p>
        </div>

        {/* Status Count Filters */}
        <div className="flex items-center gap-2 text-xs flex-wrap">
          <button
            onClick={() => setStatusFilter('All')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'All'
                ? 'bg-[#111111] text-white border-[#111111]'
                : 'bg-white text-[#8B8D86] border-[#E7E7E2] hover:bg-[#F5F5F2]'
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setStatusFilter('Missing')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Missing'
                ? 'bg-[#B94A48] text-white border-[#B94A48]'
                : 'bg-[#FDF2F2] text-[#B94A48] border-[#F6CECE] hover:bg-[#FBE4E4]'
            }`}
          >
            Missing ({missingCount})
          </button>
          <button
            onClick={() => setStatusFilter('Pending')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Pending'
                ? 'bg-[#A87524] text-white border-[#A87524]'
                : 'bg-[#FEF8EC] text-[#A87524] border-[#F5DCB2] hover:bg-[#FDF0D5]'
            }`}
          >
            Pending ({pendingCount})
          </button>
          <button
            onClick={() => setStatusFilter('Complete')}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
              statusFilter === 'Complete'
                ? 'bg-[#39765A] text-white border-[#39765A]'
                : 'bg-[#EDF7F2] text-[#39765A] border-[#BDE3D1] hover:bg-[#DCF1E6]'
            }`}
          >
            Complete ({completeCount})
          </button>
        </div>
      </div>

      {/* Missing Doc Alert Notice */}
      {missingCount > 0 && (
        <div className="p-4 rounded-xl bg-[#FDF2F2] border border-[#F6CECE] text-xs flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-[#B94A48] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-[#B94A48]">
              Immediate Clearance Risk: {missingCount} Required Document Awaiting Submission
            </h4>
            <p className="text-[#8C3432] text-[11px] leading-relaxed">
              Consignment #EXP-2026-441 to Alpine Imports is scheduled to dock in Hamburg. The original Certificate of Origin has not been endorsed by the Export Inspection Council. Without this, standard third-country customs duty applies and cargo detention charges may accrue.
            </p>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-[#E7E7E2] shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
          {/* Search Input */}
          <div className="sm:col-span-7 relative">
            <Search className="w-4 h-4 text-[#8B8D86] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search document name, shipment ref, customer, or authority..."
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
            <span className="text-xs text-[#8B8D86] shrink-0 font-medium">Filter Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full py-2 px-2.5 text-xs bg-[#F5F5F2] border border-[#E7E7E2] rounded-lg text-[#111111] focus:bg-white focus:border-[#111111] transition-colors"
            >
              <option value="All">All Documents</option>
              <option value="Missing">Missing</option>
              <option value="Pending">Pending</option>
              <option value="Complete">Complete</option>
            </select>
          </div>

          {/* Reset Filters / Count */}
          <div className="sm:col-span-2 flex items-center justify-end text-xs">
            {searchTerm || statusFilter !== 'All' ? (
              <button
                onClick={handleClearFilters}
                className="text-xs text-[#B94A48] hover:underline font-semibold flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5" />
                Reset
              </button>
            ) : (
              <span className="text-[11px] text-[#8B8D86]">
                {filteredDocs.length} documents
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-xl border border-[#E7E7E2] shadow-xs overflow-hidden">
        {filteredDocs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#E7E7E2] text-[#8B8D86] text-[11px] font-semibold bg-[#F5F5F2]">
                  <th className="py-3 px-4">Document Name</th>
                  <th className="py-3 px-4">Related Customer / Shipment</th>
                  <th className="py-3 px-4">Transit Route</th>
                  <th className="py-3 px-4">Issuing Authority</th>
                  <th className="py-3 px-4">Deadline</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F5F5F2]">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-[#F5F5F2] transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="p-1.5 rounded-lg bg-[#F5F5F2] text-[#111111]">
                          <FileText className="w-4 h-4 shrink-0" />
                        </div>
                        <div>
                          <span className="font-bold text-[#111111] block">
                            {doc.name}
                          </span>
                          <span className="text-[10px] text-[#8B8D86]">
                            {doc.type}
                          </span>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="font-bold text-[#111111] block">
                        {doc.customer}
                      </span>
                      <span className="font-mono text-[11px] text-[#8B8D86]">
                        {doc.shipmentRef}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-[#8B8D86] text-[11px]">
                      {doc.originPort} → {doc.destinationPort}
                    </td>

                    <td className="py-3.5 px-4 text-[#111111]">
                      {doc.issuingAuthority}
                    </td>

                    <td className="py-3.5 px-4 text-[#8B8D86]">
                      {doc.deadlineDate}
                    </td>

                    <td className="py-3.5 px-4">
                      <StatusBadge status={doc.status} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => onSelectDocument(doc)}
                          className="px-2.5 py-1 text-[11px] font-bold text-[#111111] bg-white hover:bg-[#F5F5F2] rounded-lg border border-[#E7E7E2] transition-colors inline-flex items-center gap-1"
                        >
                          <Eye className="w-3 h-3 text-[#111111]" />
                          <span>Review</span>
                        </button>
                        {doc.status !== 'Complete' && (
                          <button
                            onClick={() => onUpdateStatus(doc.id, 'Complete')}
                            className="px-2.5 py-1 text-[11px] font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg border border-[#D9F83F] transition-colors inline-flex items-center gap-1 shadow-xs"
                            title="Mark as Received & Verified"
                          >
                            <CheckCircle2 className="w-3 h-3 text-[#111111]" />
                            <span>Verify</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-full bg-[#F5F5F2] text-[#8B8D86] flex items-center justify-center mx-auto mb-3">
              <FolderLock className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-[#111111]">No trade documents found</h3>
            <p className="text-xs text-[#8B8D86] max-w-sm mx-auto mt-1">
              No records matched &apos;{searchTerm}&apos; with current status filters.
            </p>
            <button
              onClick={handleClearFilters}
              className="mt-4 px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] rounded-lg transition-colors"
            >
              Clear Filters
            </button>
          </div>
        )}

        <div className="px-4 py-3 bg-[#F5F5F2] border-t border-[#E7E7E2] flex flex-col sm:flex-row items-center justify-between text-[11px] text-[#8B8D86] gap-2">
          <span>Demonstration purposes: tracks documentation status to prevent trade compliance bottlenecks.</span>
          <span className="text-[#111111] font-semibold">Changes update immediately in memory</span>
        </div>
      </div>
    </div>
  );
};
