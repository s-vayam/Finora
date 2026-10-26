import React from 'react';
import { CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { InvoiceStatus, DocumentStatus } from '../../types';

interface BadgeProps {
  status: InvoiceStatus | DocumentStatus | 'High' | 'Medium' | 'Low' | string;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<BadgeProps> = ({ status, className = '', size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  switch (status) {
    case 'Paid':
    case 'Complete':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#EDF7F2] text-[#39765A] border border-[#BDE3D1] ${sizeClasses} ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-[#39765A]" aria-hidden="true" />
          <span>{status}</span>
        </span>
      );

    case 'Due soon':
    case 'Pending':
    case 'Medium':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#FEF8EC] text-[#A87524] border border-[#F5DCB2] ${sizeClasses} ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-[#A87524]" aria-hidden="true" />
          <span>{status}</span>
        </span>
      );

    case 'Overdue':
    case 'Missing':
    case 'High':
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-semibold rounded-full bg-[#FDF2F2] text-[#B94A48] border border-[#F6CECE] ${sizeClasses} ${className}`}
        >
          <AlertCircle className="w-3.5 h-3.5 text-[#B94A48]" aria-hidden="true" />
          <span>{status}</span>
        </span>
      );

    case 'Upcoming':
    case 'Low':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#F5F5F2] text-[#8B8D86] border border-[#E7E7E2] ${sizeClasses} ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-[#8B8D86]" aria-hidden="true" />
          <span>{status}</span>
        </span>
      );
  }
};
