import React, { useState, useEffect, useCallback } from 'react';
import { 
  NavigationTab, 
  Invoice, 
  InvoiceStatus,
  TradeDocument, 
  AlertItem, 
  CashFlowMonth 
} from './types';
import { 
  INITIAL_INVOICES, 
  INITIAL_DOCUMENTS, 
  INITIAL_ALERTS, 
  FX_EXPOSURE_RECORDS, 
  calculateCashFlow, 
  OPENING_CASH_BALANCE 
} from './data/mockData';
import { Sidebar } from './components/common/Sidebar';
import { Header } from './components/common/Header';
import { ToastContainer, ToastMessage } from './components/common/Toast';
import { ConfirmationModal } from './components/common/ConfirmationModal';
import { InvoiceDetailModal } from './components/screens/InvoiceDetailModal';
import { DocumentDetailModal } from './components/screens/DocumentDetailModal';

// Screens
import { OverviewScreen } from './components/screens/OverviewScreen';
import { InvoicesScreen } from './components/screens/InvoicesScreen';
import { FXRiskScreen } from './components/screens/FXRiskScreen';
import { CashFlowScreen } from './components/screens/CashFlowScreen';
import { DocumentsScreen } from './components/screens/DocumentsScreen';
import { CopilotScreen } from './components/screens/CopilotScreen';

// Backend Services & Mappers
import { invoicesApi, paymentsApi } from './services/api';
import { mapBackendInvoiceToUi } from './services/api/mappers';

export function App() {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('overview');
  const [invoices, setInvoices] = useState<Invoice[]>(INITIAL_INVOICES);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [invoicesError, setInvoicesError] = useState<any>(null);

  const [documents, setDocuments] = useState<TradeDocument[]>(INITIAL_DOCUMENTS);
  const [alerts, setAlerts] = useState<AlertItem[]>(INITIAL_ALERTS);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Modal states
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<TradeDocument | null>(null);
  const [invoiceToConfirmPay, setInvoiceToConfirmPay] = useState<Invoice | null>(null);

  // Cash flow schedule calculated from single source of truth
  const cashFlowData: CashFlowMonth[] = calculateCashFlow(OPENING_CASH_BALANCE);

  // Overdue and missing counts for badges
  const overdueCount = invoices.filter((i) => i.status === 'Overdue').length;
  const missingDocsCount = documents.filter((d) => d.status === 'Missing').length;

  const fetchInvoices = useCallback(async () => {
    setInvoicesLoading(true);
    setInvoicesError(null);
    try {
      const res = await invoicesApi.listInvoices();
      if (res?.items && res.items.length > 0) {
        const mapped = res.items.map(mapBackendInvoiceToUi);
        setInvoices(mapped);
      }
    } catch (err: any) {
      setInvoicesError(err);
    } finally {
      setInvoicesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  const addToast = (
    type: 'success' | 'warning' | 'info',
    title: string,
    message: string,
    onUndo?: () => void,
    undoLabel?: string
  ) => {
    const newToast: ToastMessage = {
      id: `toast-${Date.now()}-${Math.random()}`,
      type,
      title,
      message,
      onUndo,
      undoLabel,
    };
    setToasts((prev) => [...prev, newToast]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleNavigate = (tab: NavigationTab, relatedId?: string) => {
    setCurrentTab(tab);
    setMobileMenuOpen(false);
    if (tab === 'invoices' && relatedId) {
      const targetInvoice = invoices.find((inv) => inv.id === relatedId);
      if (targetInvoice) {
        setSelectedInvoice(targetInvoice);
      }
    } else if (tab === 'documents' && relatedId) {
      const targetDoc = documents.find((doc) => doc.id === relatedId);
      if (targetDoc) {
        setSelectedDocument(targetDoc);
      }
    }
  };

  // Mark as Paid Workflow with Confirmation & Undo (Rules 4, 5, 6)
  const handleRequestMarkAsPaid = (invoice: Invoice) => {
    setInvoiceToConfirmPay(invoice);
  };

  const handleConfirmMarkAsPaid = async () => {
    if (!invoiceToConfirmPay) return;

    const targetInvoice = invoiceToConfirmPay;
    const targetId = targetInvoice.id;
    const invNumber = targetInvoice.invoiceNumber;
    const customer = targetInvoice.customer;
    const originalStatus = targetInvoice.status;
    setInvoiceToConfirmPay(null);

    const isBackendInvoice = targetId && !targetId.startsWith('inv-');

    if (isBackendInvoice) {
      try {
        const idempotencyKey = `pmt-${targetId}-${Date.now()}`;
        const outstandingAmt = targetInvoice.outstandingBalance !== undefined
          ? targetInvoice.outstandingBalance
          : targetInvoice.amount;

        await paymentsApi.recordPayment(
          targetId,
          {
            payment_date: new Date().toISOString().split('T')[0],
            amount: outstandingAmt,
            currency: targetInvoice.currency,
            payment_method: 'WIRE_TRANSFER',
            reference_number: `WIRE-${Date.now().toString().slice(-6)}`,
            notes: 'Settled via Finora web interface',
          },
          idempotencyKey
        );

        // Fetch refreshed invoice from backend
        try {
          const fresh = await invoicesApi.getInvoice(targetId);
          const mapped = mapBackendInvoiceToUi(fresh);
          setInvoices((prev) => prev.map((inv) => (inv.id === targetId ? mapped : inv)));
          if (selectedInvoice && selectedInvoice.id === targetId) {
            setSelectedInvoice(mapped);
          }
        } catch {
          // Optimistic local update
          setInvoices((prev) =>
            prev.map((inv) =>
              inv.id === targetId
                ? { ...inv, status: 'Paid' as const, amountPaid: inv.amount, outstandingBalance: 0 }
                : inv
            )
          );
          if (selectedInvoice && selectedInvoice.id === targetId) {
            setSelectedInvoice((prev) =>
              prev ? { ...prev, status: 'Paid' as const, amountPaid: prev.amount, outstandingBalance: 0 } : null
            );
          }
        }

        addToast(
          'success',
          'Payment Recorded Successfully',
          `Full settlement of ${targetInvoice.currency} ${outstandingAmt.toLocaleString()} recorded for Invoice ${invNumber} (${customer}).`
        );
      } catch (err: any) {
        addToast(
          'warning',
          'Payment Recording Failed',
          err?.message || 'Server rejected payment operation. Please check connectivity.'
        );
      }
    } else {
      // Prototype mock records (e.g. inv-1)
      setInvoices((prev) =>
        prev.map((inv) =>
          inv.id === targetId ? { ...inv, status: 'Paid' as const } : inv
        )
      );

      if (selectedInvoice && selectedInvoice.id === targetId) {
        setSelectedInvoice((prev) => (prev ? { ...prev, status: 'Paid' as const } : null));
      }

      if (targetId === 'inv-1') {
        setAlerts((prev) => prev.filter((a) => a.id !== 'alert-1'));
      }

      addToast(
        'success',
        'Invoice Reconciled as Paid',
        `Invoice ${invNumber} for ${customer} has been updated to Paid in the prototype state.`,
        () => handleUndoMarkAsPaid(targetId, originalStatus, invNumber, customer),
        'Undo Settlement'
      );
    }
  };

  const handleUndoMarkAsPaid = (
    invoiceId: string,
    revertToStatus: InvoiceStatus,
    invNumber: string,
    customer: string
  ) => {
    setInvoices((prev) =>
      prev.map((inv) =>
        inv.id === invoiceId ? { ...inv, status: revertToStatus } : inv
      )
    );

    if (selectedInvoice && selectedInvoice.id === invoiceId) {
      setSelectedInvoice((prev) =>
        prev ? { ...prev, status: revertToStatus } : null
      );
    }

    if (invoiceId === 'inv-1') {
      const originalAlert = INITIAL_ALERTS.find((a) => a.id === 'alert-1');
      if (originalAlert) {
        setAlerts((prev) => {
          if (prev.some((a) => a.id === 'alert-1')) return prev;
          return [originalAlert, ...prev];
        });
      }
    }

    addToast(
      'info',
      'Action Undone',
      `Invoice ${invNumber} status reverted back to ${revertToStatus}.`
    );
  };

  const handleRevertInvoiceStatus = (invoice: Invoice) => {
    handleUndoMarkAsPaid(invoice.id, 'Overdue', invoice.invoiceNumber, invoice.customer);
  };

  // Update Document Status Workflow with Undo (Rule 6)
  const handleUpdateDocumentStatus = (docId: string, newStatus: 'Complete' | 'Pending' | 'Missing') => {
    const targetDoc = documents.find((d) => d.id === docId);
    if (!targetDoc) return;
    const previousStatus = targetDoc.status;

    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === docId ? { ...doc, status: newStatus, lastUpdated: '2026-10-26' } : doc
      )
    );

    if (docId === 'doc-1') {
      if (newStatus === 'Complete') {
        setAlerts((prev) => prev.filter((a) => a.id !== 'alert-3'));
      } else {
        const originalAlert = INITIAL_ALERTS.find((a) => a.id === 'alert-3');
        if (originalAlert) {
          setAlerts((prev) => {
            if (prev.some((a) => a.id === 'alert-3')) return prev;
            return [...prev, originalAlert];
          });
        }
      }
    }

    if (selectedDocument && selectedDocument.id === docId) {
      setSelectedDocument((prev) =>
        prev ? { ...prev, status: newStatus, lastUpdated: '2026-10-26' } : null
      );
    }

    addToast(
      'info',
      'Document Status Updated',
      `"${targetDoc.name}" status updated to ${newStatus}.`,
      () => handleUpdateDocumentStatus(docId, previousStatus),
      'Undo Status Change'
    );
  };

  return (
    <div className="min-h-screen bg-[#F5F5F2] flex text-[#111111]">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onNavigate={handleNavigate}
        overdueCount={overdueCount}
        missingDocsCount={missingDocsCount}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          currentTab={currentTab}
          alerts={alerts}
          onNavigate={handleNavigate}
          onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {currentTab === 'overview' && (
            <OverviewScreen
              invoices={invoices}
              alerts={alerts}
              cashFlowData={cashFlowData}
              fxRecords={FX_EXPOSURE_RECORDS}
              onNavigate={handleNavigate}
              onSelectInvoice={(inv) => setSelectedInvoice(inv)}
            />
          )}

          {currentTab === 'invoices' && (
            <InvoicesScreen
              invoices={invoices}
              onSelectInvoice={(inv) => setSelectedInvoice(inv)}
              onRequestMarkAsPaid={handleRequestMarkAsPaid}
              loading={invoicesLoading}
              error={invoicesError}
              onRefresh={fetchInvoices}
            />
          )}

          {currentTab === 'fx-risk' && (
            <FXRiskScreen fxRecords={FX_EXPOSURE_RECORDS} />
          )}

          {currentTab === 'cash-flow' && (
            <CashFlowScreen cashFlowData={cashFlowData} />
          )}

          {currentTab === 'documents' && (
            <DocumentsScreen
              documents={documents}
              onSelectDocument={(doc) => setSelectedDocument(doc)}
              onUpdateStatus={handleUpdateDocumentStatus}
            />
          )}

          {currentTab === 'copilot' && (
            <CopilotScreen
              invoices={invoices}
              documents={documents}
              cashFlowData={cashFlowData}
              fxRecords={FX_EXPOSURE_RECORDS}
              onNavigate={handleNavigate}
              onSelectInvoice={(inv) => setSelectedInvoice(inv)}
            />
          )}
        </main>
      </div>

      {/* Invoice Detail Modal */}
      <InvoiceDetailModal
        invoice={selectedInvoice}
        onClose={() => setSelectedInvoice(null)}
        onRequestMarkAsPaid={handleRequestMarkAsPaid}
        onRequestRevertStatus={handleRevertInvoiceStatus}
      />

      {/* Document Detail Modal */}
      <DocumentDetailModal
        document={selectedDocument}
        onClose={() => setSelectedDocument(null)}
        onUpdateStatus={handleUpdateDocumentStatus}
      />

      {/* Confirmation Modal for Error Prevention */}
      <ConfirmationModal
        isOpen={!!invoiceToConfirmPay}
        title="Confirm Invoice Settlement"
        description={
          invoiceToConfirmPay
            ? `Are you sure you want to mark Invoice ${invoiceToConfirmPay.invoiceNumber} (${invoiceToConfirmPay.customer} - ${invoiceToConfirmPay.currency} ${invoiceToConfirmPay.amount.toLocaleString()}) as Paid? This will record payment and recalculate overdue metrics and outstanding receivables.`
            : ''
        }
        confirmLabel="Mark as Paid"
        cancelLabel="Cancel"
        onConfirm={handleConfirmMarkAsPaid}
        onCancel={() => setInvoiceToConfirmPay(null)}
      />

      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}

export default App;
