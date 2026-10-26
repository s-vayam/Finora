import React, { useState, useRef, useEffect } from 'react';
import { 
  Building2, 
  Bell, 
  ChevronDown, 
  Info, 
  ExternalLink, 
  Check, 
  Menu, 
  Sparkles 
} from 'lucide-react';
import { COMPANY_INFO } from '../../data/mockData';
import { NavigationTab, AlertItem } from '../../types';

interface HeaderProps {
  currentTab: NavigationTab;
  alerts: AlertItem[];
  onNavigate: (tab: NavigationTab, relatedId?: string) => void;
  onToggleMobileMenu?: () => void;
}

const TAB_TITLES: Record<NavigationTab, { title: string; subtitle: string }> = {
  overview: {
    title: 'Financial Overview',
    subtitle: 'Summary of international receivables, currency exposure, and cash runway',
  },
  invoices: {
    title: 'Invoices & Payments',
    subtitle: 'Cross-border trade invoice ledger, payment reconciliation & settlement',
  },
  'fx-risk': {
    title: 'FX Risk & Exposure Analytics',
    subtitle: 'Currency portfolio sensitivity, unhedged forward volume & margin impact',
  },
  'cash-flow': {
    title: 'Cash Flow Forecast',
    subtitle: 'Projected monthly export inflows, supplier disbursements & working capital',
  },
  documents: {
    title: 'Trade & Customs Documents',
    subtitle: 'Statutory compliance tracking for bills of lading, origin certificates & shipping bills',
  },
  copilot: {
    title: 'AI Financial Co-Pilot',
    subtitle: 'Simulated operational co-pilot answering inquiries using active trade telemetry',
  },
};

export const Header: React.FC<HeaderProps> = ({ currentTab, alerts, onNavigate, onToggleMobileMenu }) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showCompanyMenu, setShowCompanyMenu] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const companyRef = useRef<HTMLDivElement>(null);

  const notifBtnRef = useRef<HTMLButtonElement>(null);
  const companyBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (companyRef.current && !companyRef.current.contains(e.target as Node)) {
        setShowCompanyMenu(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showNotifications) {
          setShowNotifications(false);
          notifBtnRef.current?.focus();
        }
        if (showCompanyMenu) {
          setShowCompanyMenu(false);
          companyBtnRef.current?.focus();
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [showNotifications, showCompanyMenu]);

  const pageInfo = TAB_TITLES[currentTab] || { title: 'Dashboard', subtitle: '' };

  return (
    <header className="sticky top-0 z-30 bg-[#FFFFFF] border-b border-[#E7E7E2] px-4 lg:px-8 py-3.5 flex items-center justify-between shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
      {/* Left: Mobile Toggle + Breadcrumb & Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobileMenu}
          className="lg:hidden p-1.5 rounded-lg border border-[#E7E7E2] text-[#8B8D86] hover:text-[#111111] hover:bg-[#F5F5F2] transition-colors"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-[11px] text-[#8B8D86] font-medium">
            <span className="text-[#111111] font-semibold">BorderPilot</span>
            <span>/</span>
            <span className="capitalize">{currentTab.replace('-', ' ')}</span>
          </div>
          <div className="flex items-center gap-2.5 mt-0.5">
            <h1 className="text-base sm:text-lg lg:text-xl font-bold text-[#111111] tracking-tight">
              {pageInfo.title}
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#ECF9A8] text-[#111111] border border-[#D9F83F]">
              <Sparkles className="w-3 h-3 text-[#111111]" />
              Pro Prototype
            </span>
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Company Selector */}
        <div className="relative" ref={companyRef}>
          <button
            ref={companyBtnRef}
            onClick={() => setShowCompanyMenu(!showCompanyMenu)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-[#111111] bg-[#F5F5F2] hover:bg-[#EBEBE6] border border-[#E7E7E2] rounded-lg transition-colors"
            aria-label="Select Company"
            aria-expanded={showCompanyMenu}
          >
            <div className="w-5 h-5 rounded bg-[#111111] text-[#D9F83F] flex items-center justify-center font-bold text-[10px]">
              M
            </div>
            <span className="max-w-[110px] sm:max-w-[190px] truncate">
              {COMPANY_INFO.name}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-[#8B8D86]" />
          </button>

          {showCompanyMenu && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl border border-[#E7E7E2] shadow-xl py-2 z-50 text-xs animate-in fade-in zoom-in-95 duration-100">
              <div className="px-4 py-3 border-b border-[#E7E7E2] bg-[#F5F5F2]">
                <p className="font-bold text-[#111111] text-sm">{COMPANY_INFO.name}</p>
                <p className="text-[#8B8D86] text-[11px] mt-0.5">{COMPANY_INFO.division}</p>
                <p className="text-[#8B8D86] text-[11px] mt-1 font-mono">HQ: {COMPANY_INFO.headquarters}</p>
              </div>
              <div className="p-2">
                <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#ECF9A8] text-[#111111] font-semibold border border-[#D9F83F]/60">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#111111]" />
                    <span>{COMPANY_INFO.name}</span>
                  </div>
                  <Check className="w-4 h-4 text-[#111111]" />
                </div>
              </div>
              <div className="px-4 py-2 text-[11px] text-[#8B8D86] border-t border-[#E7E7E2] flex items-center gap-2">
                <Info className="w-3.5 h-3.5 text-[#111111]" />
                Base currency: INR (₹)
              </div>
            </div>
          )}
        </div>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            ref={notifBtnRef}
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-[#8B8D86] hover:text-[#111111] hover:bg-[#F5F5F2] rounded-lg border border-[#E7E7E2] transition-colors"
            aria-label={`Notifications: ${alerts.length} unread alerts`}
            aria-expanded={showNotifications}
          >
            <Bell className="w-4 h-4" />
            {alerts.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-[#B94A48] text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                {alerts.length}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl border border-[#E7E7E2] shadow-xl py-2 z-50">
              <div className="px-4 py-3 border-b border-[#E7E7E2] flex items-center justify-between bg-[#F5F5F2]">
                <span className="font-bold text-xs text-[#111111] uppercase tracking-wider">
                  Priority Risk Alerts
                </span>
                <span className="text-[11px] font-bold text-[#B94A48] bg-[#FDF2F2] px-2 py-0.5 rounded-full border border-[#F6CECE]">
                  {alerts.length} Items
                </span>
              </div>
              <div className="max-h-80 overflow-y-auto divide-y divide-[#E7E7E2]">
                {alerts.map((alert) => (
                  <div key={alert.id} className="p-3.5 hover:bg-[#F5F5F2] transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-xs text-[#111111]">{alert.title}</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          alert.urgency === 'high'
                            ? 'bg-[#FDF2F2] text-[#B94A48] border border-[#F6CECE]'
                            : 'bg-[#FEF8EC] text-[#A87524] border border-[#F5DCB2]'
                        }`}
                      >
                        {alert.urgency.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#8B8D86] mt-1 leading-relaxed">
                      {alert.whatHappened}
                    </p>
                    <button
                      onClick={() => {
                        setShowNotifications(false);
                        onNavigate(alert.targetTab, alert.relatedEntityId);
                      }}
                      className="mt-2 text-xs font-bold text-[#111111] hover:underline inline-flex items-center gap-1 transition-colors"
                    >
                      <span>{alert.actionLabel}</span>
                      <ExternalLink className="w-3 h-3 text-[#111111]" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-[#E7E7E2]">
          <div className="w-8 h-8 rounded-lg bg-[#111111] text-[#D9F83F] font-bold text-xs flex items-center justify-center">
            AM
          </div>
          <div className="hidden md:flex flex-col text-left">
            <span className="text-xs font-bold text-[#111111]">
              {COMPANY_INFO.primaryUser.name}
            </span>
            <span className="text-[11px] text-[#8B8D86]">
              {COMPANY_INFO.primaryUser.role}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
