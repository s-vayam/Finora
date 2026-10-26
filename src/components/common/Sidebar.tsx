import React from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  TrendingUp, 
  Wallet, 
  FolderLock, 
  Bot, 
  X, 
  ShieldCheck,
  Zap 
} from 'lucide-react';
import { NavigationTab } from '../../types';

interface SidebarProps {
  currentTab: NavigationTab;
  onNavigate: (tab: NavigationTab) => void;
  overdueCount: number;
  missingDocsCount: number;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  id: NavigationTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
  badgeType?: 'danger' | 'warning' | 'info';
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onNavigate,
  overdueCount,
  missingDocsCount,
  mobileOpen = false,
  onCloseMobile,
}) => {
  const navItems: NavItem[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'invoices',
      label: 'Invoices & Payments',
      icon: FileText,
      badge: overdueCount > 0 ? overdueCount : undefined,
      badgeType: 'danger',
    },
    {
      id: 'fx-risk',
      label: 'FX Risk',
      icon: TrendingUp,
    },
    {
      id: 'cash-flow',
      label: 'Cash Flow',
      icon: Wallet,
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: FolderLock,
      badge: missingDocsCount > 0 ? missingDocsCount : undefined,
      badgeType: 'warning',
    },
    {
      id: 'copilot',
      label: 'AI Co-Pilot',
      icon: Bot,
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden backdrop-blur-xs"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 w-64 bg-[#FFFFFF] border-r border-[#E7E7E2] flex flex-col shrink-0 min-h-screen transition-transform duration-200 ease-in-out ${
          mobileOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-[#E7E7E2] bg-[#FFFFFF]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#111111] flex items-center justify-center text-[#D9F83F] font-bold text-sm tracking-wider shadow-sm">
              BP
            </div>
            <div>
              <span className="font-bold text-base text-[#111111] tracking-tight block">
                BorderPilot
              </span>
              <span className="text-[10px] text-[#8B8D86] font-semibold tracking-wider block uppercase">
                Trade Financial Co-Pilot
              </span>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="lg:hidden p-1 text-[#8B8D86] hover:text-[#111111] rounded-lg hover:bg-[#F5F5F2]"
            aria-label="Close navigation"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-3.5 space-y-1.5" aria-label="Main Navigation">
          <div className="px-3 py-1.5 text-[10px] font-bold text-[#8B8D86] uppercase tracking-wider">
            Workspace
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onNavigate(item.id);
                  onCloseMobile?.();
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition-all group focus-visible:ring-2 focus-visible:ring-[#111111] ${
                  isActive
                    ? 'bg-[#111111] text-white shadow-sm'
                    : 'text-[#8B8D86] hover:bg-[#F5F5F2] hover:text-[#111111]'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-[#D9F83F]' : 'text-[#8B8D86] group-hover:text-[#111111]'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && item.badge > 0 && (
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      item.badgeType === 'danger'
                        ? 'bg-[#FDF2F2] text-[#B94A48] border-[#F6CECE]'
                        : 'bg-[#FEF8EC] text-[#A87524] border-[#F5DCB2]'
                    }`}
                    title={`${item.badge} item(s) require attention`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Dark Highlight Panel (Pro Finance Style) */}
        <div className="p-3.5 border-t border-[#E7E7E2]">
          <div className="p-3.5 rounded-xl bg-[#111111] text-white text-[11px] space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 font-bold text-[#D9F83F]">
                <Zap className="w-3.5 h-3.5 text-[#D9F83F]" />
                <span>Trade Engine v2.4</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-[#D9F83F]" />
            </div>
            <p className="text-[#8B8D86] leading-relaxed text-[11px]">
              Continuous telemetry across cross-border receivables, FX exposure & liquidity.
            </p>
            <div className="pt-2 text-[10px] text-[#8B8D86] flex items-center justify-between border-t border-[#222222]">
              <span>Base: INR (₹)</span>
              <span className="text-[#D9F83F] font-semibold">Active Cycle</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
