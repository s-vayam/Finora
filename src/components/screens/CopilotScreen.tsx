import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  Clock, 
  RotateCcw,
  ArrowRight,
  Info
} from 'lucide-react';
import { Invoice, TradeDocument, CashFlowMonth, FXExposureRecord, NavigationTab, ChatMessage, ChatAction } from '../../types';

interface CopilotScreenProps {
  invoices: Invoice[];
  documents: TradeDocument[];
  cashFlowData: CashFlowMonth[];
  fxRecords: FXExposureRecord[];
  onNavigate: (tab: NavigationTab, relatedId?: string) => void;
  onSelectInvoice: (invoice: Invoice) => void;
}

export const CopilotScreen: React.FC<CopilotScreenProps> = ({
  invoices,
  documents,
  cashFlowData,
  fxRecords,
  onNavigate,
  onSelectInvoice,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      sender: 'assistant',
      timestamp: '09:00 AM',
      text: "Hello Arjun. I am your BorderPilot financial co-pilot. I analyze Meridian Textiles' current receivables, foreign exchange exposure, cash flow projections, and trade documents. What would you like to check today?",
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const suggestedQuestions = [
    'Which invoices need attention first?',
    'What is our largest currency exposure?',
    'How is our projected cash balance changing?',
    'Which trade documents are pending?',
    'What happens if USD exchange rate drops 5%?',
  ];

  const generateContextualAnswer = (query: string): { text: string; action?: ChatAction } => {
    const q = query.toLowerCase().trim();

    if (q.includes('invoice') || q.includes('overdue') || q.includes('attention') || q.includes('payment') || q.includes('first')) {
      const overdue = invoices.filter((i) => i.status === 'Overdue');
      const dueSoon = invoices.filter((i) => i.status === 'Due soon');

      if (overdue.length > 0) {
        const top = overdue[0];
        const overdueTotal = overdue.reduce((sum, i) => sum + i.amount, 0);
        return {
          text: `${top.customer}'s invoice (${top.invoiceNumber}) for $${top.amount.toLocaleString()} USD is currently ${top.status.toLowerCase()} (due on ${top.dueDate}). In total, there are ${overdue.length} overdue invoices totaling $${overdueTotal.toLocaleString()} USD that require immediate follow-up. ${dueSoon.length > 0 ? `Additionally, ${dueSoon[0].customer} has an invoice of €${dueSoon[0].amount.toLocaleString()} EUR due soon on ${dueSoon[0].dueDate}.` : ''}`,
          action: {
            label: `Inspect ${top.customer} Invoice (${top.invoiceNumber})`,
            targetTab: 'invoices',
            relatedEntityId: top.id,
            invoiceToOpen: top,
          },
        };
      } else if (dueSoon.length > 0) {
        return {
          text: `Good news: There are no overdue invoices in the current record. However, ${dueSoon[0].customer}'s invoice of €${dueSoon[0].amount.toLocaleString()} EUR is due soon on ${dueSoon[0].dueDate}.`,
          action: {
            label: 'Open Invoices List',
            targetTab: 'invoices',
          },
        };
      } else {
        return {
          text: 'All recorded invoices are currently up to date or marked as paid. No immediate payment overdue risk detected in the local dataset.',
          action: {
            label: 'View Invoices Schedule',
            targetTab: 'invoices',
          },
        };
      }
    }

    if (q.includes('currency') || q.includes('largest') || q.includes('fx') || q.includes('exposure')) {
      const sortedFx = [...fxRecords].sort((a, b) => b.inrEquivalent - a.inrEquivalent);
      const largest = sortedFx[0];
      return {
        text: `Your largest foreign currency exposure is in ${largest.currency}, with an open trade balance of ${largest.symbol}${largest.exposureAmount.toLocaleString()} (approx. ₹${largest.inrLakh.toFixed(2)} Lakh INR at the illustrative rate of ₹${largest.illustrativeRate}/USD). This accounts for ${largest.sharePercent}% of your total foreign currency trade portfolio. Note that the dashboard overall FX risk metric is $84,200 USD equivalent on a 45-day forward basis.`,
        action: {
          label: 'Open FX Risk Module',
          targetTab: 'fx-risk',
        },
      };
    }

    if (q.includes('cash') || q.includes('position') || q.includes('change') || q.includes('changing') || q.includes('projected') || q.includes('liquidity') || q.includes('deficit')) {
      const deficitMonth = cashFlowData.find((m) => m.inflows < m.outflows);
      const endMonth = cashFlowData[cashFlowData.length - 1];
      return {
        text: `Based on your cash flow projections, opening balance is ₹24.8 Lakh and is projected to rise to ₹${endMonth.closingBalance.toFixed(1)} Lakh by Month 6. However, ${deficitMonth ? `attention is required in ${deficitMonth.label}: outflows (₹${deficitMonth.outflows}L) will exceed inflows (₹${deficitMonth.inflows}L) by ₹${Math.abs(deficitMonth.netChange).toFixed(1)} Lakh due to raw cotton procurement.` : 'all months currently project positive net cash additions.'}`,
        action: {
          label: 'Open Cash Flow Schedule',
          targetTab: 'cash-flow',
        },
      };
    }

    if (q.includes('document') || q.includes('pending') || q.includes('missing') || q.includes('compliance') || q.includes('trade')) {
      const missing = documents.filter((d) => d.status === 'Missing');
      const pending = documents.filter((d) => d.status === 'Pending');

      if (missing.length > 0) {
        return {
          text: `You have ${missing.length} missing document: "${missing[0].name}" for shipment ${missing[0].shipmentRef} to ${missing[0].customer}. Without it, clearance at ${missing[0].destinationPort} will stall. There are also ${pending.length} pending documents under review by issuing authorities.`,
          action: {
            label: `Track Missing ${missing[0].name}`,
            targetTab: 'documents',
            relatedEntityId: missing[0].id,
          },
        };
      } else if (pending.length > 0) {
        return {
          text: `There are no missing documents, but ${pending.length} documents remain pending: ${pending.map((d) => `"${d.name}" (${d.customer})`).join(', ')}.`,
          action: {
            label: 'Track Pending Documents',
            targetTab: 'documents',
          },
        };
      } else {
        return {
          text: 'All trade compliance documents are marked as complete and verified for current shipments.',
          action: {
            label: 'View Documents',
            targetTab: 'documents',
          },
        };
      }
    }

    if (q.includes('drop') || q.includes('rate') || q.includes('usd') || q.includes('rupee') || q.includes('sensitivity')) {
      const usdRecord = fxRecords.find((r) => r.currency === 'USD') || fxRecords[0];
      const baseInr = usdRecord.inrEquivalent;
      const drop5Val = Math.round(baseInr * 0.95);
      const diffLakh = ((baseInr - drop5Val) / 100000).toFixed(2);
      return {
        text: `If the USD/INR conversion rate drops by 5% (i.e. INR strengthens from ₹85 to ₹80.75), your $58,000 USD open receivables will convert to approx ₹${(drop5Val / 100000).toFixed(2)} Lakh instead of ₹${(baseInr / 100000).toFixed(2)} Lakh—a realization contraction of ₹${diffLakh} Lakh. You can test interactive scenarios in the FX Sensitivity Calculator.`,
        action: {
          label: 'Open Sensitivity Calculator',
          targetTab: 'fx-risk',
        },
      };
    }

    return {
      text: "I do not have sufficient illustrative mock data in the prototype to answer that inquiry with certainty. As a prototype co-pilot, I only access recorded invoices, exchange rates (USD ₹85, EUR ₹99, GBP ₹113), cash flow schedules, and trade document statuses for Meridian Textiles.",
    };
  };

  const handleSendMessage = (textToSend?: string) => {
    const text = (textToSend || inputQuery).trim();
    if (!text) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsTyping(true);

    setTimeout(() => {
      const response = generateContextualAnswer(text);
      const botMsg: ChatMessage = {
        id: `bot-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: response.text,
        suggestedAction: response.action,
      };
      setMessages((prev) => [...prev, botMsg]);
      setIsTyping(false);
    }, 450);
  };

  const handleResetChat = () => {
    setMessages([
      {
        id: 'welcome-reset',
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: "Chat history cleared. What questions do you have regarding Meridian Textiles' international trade finances?",
      },
    ]);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-[#E7E7E2]">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-xl lg:text-2xl font-bold text-[#111111] tracking-tight">AI Financial Co-Pilot</h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#ECF9A8] text-[#111111] border border-[#D9F83F]">
              Prototype Assistant — Uses Sample Data
            </span>
          </div>
          <p className="text-xs text-[#8B8D86] mt-1">
            Query your cross-border trade invoices, foreign exchange exposure, cash flow models, and export paperwork.
          </p>
        </div>

        <button
          onClick={handleResetChat}
          className="self-start sm:self-center px-3 py-1.5 text-xs text-[#8B8D86] hover:text-[#111111] hover:bg-white border border-[#E7E7E2] rounded-lg transition-colors flex items-center gap-1.5"
          title="Reset conversation"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Session</span>
        </button>
      </div>

      {/* Notice Banner */}
      <div className="p-3.5 bg-white border border-[#E7E7E2] rounded-xl text-[11px] text-[#8B8D86] flex items-center gap-2.5 shadow-xs">
        <Info className="w-4 h-4 text-[#111111] shrink-0" />
        <span>
          <strong className="text-[#111111]">Simulated Assistant:</strong> Answers are dynamically derived from current prototype memory. Does not connect to live banking networks, SWIFT servers, or external AI APIs.
        </span>
      </div>

      {/* Main Chat Container */}
      <div className="bg-white rounded-xl border border-[#E7E7E2] shadow-xs flex flex-col h-[520px] overflow-hidden">
        {/* Messages Stream */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4">
          {messages.map((msg) => {
            const isBot = msg.sender === 'assistant';
            return (
              <div
                key={msg.id}
                className={`flex items-start gap-3 ${isBot ? 'justify-start' : 'justify-end'}`}
              >
                {isBot && (
                  <div className="w-8 h-8 rounded-lg bg-[#111111] text-[#D9F83F] font-bold flex items-center justify-center shrink-0 shadow-xs mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-xl p-4 text-xs shadow-xs ${
                    isBot
                      ? 'bg-[#F5F5F2] border border-[#E7E7E2] text-[#111111]'
                      : 'bg-[#111111] text-white font-medium'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 mb-1.5">
                    <span className={`font-bold text-[11px] ${isBot ? 'text-[#111111]' : 'text-[#D9F83F]'}`}>
                      {isBot ? 'BorderPilot Assistant' : 'Arjun Mehta'}
                    </span>
                    <span className={`text-[10px] flex items-center gap-1 ${isBot ? 'text-[#8B8D86]' : 'text-zinc-400'}`}>
                      <Clock className="w-2.5 h-2.5" />
                      {msg.timestamp}
                    </span>
                  </div>

                  <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>

                  {/* Contextual Action Button */}
                  {isBot && msg.suggestedAction && (
                    <div className="mt-3.5 pt-3 border-t border-[#E7E7E2]">
                      <button
                        onClick={() => {
                          if (msg.suggestedAction?.invoiceToOpen) {
                            onSelectInvoice(msg.suggestedAction.invoiceToOpen);
                          } else if (msg.suggestedAction?.targetTab) {
                            onNavigate(msg.suggestedAction.targetTab, msg.suggestedAction.relatedEntityId);
                          }
                        }}
                        className="px-3.5 py-1.5 text-xs font-bold text-[#111111] bg-white hover:bg-[#D9F83F] border border-[#E7E7E2] rounded-lg transition-colors inline-flex items-center gap-1.5 shadow-xs"
                      >
                        <span>{msg.suggestedAction.label}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                {!isBot && (
                  <div className="w-8 h-8 rounded-lg bg-[#F5F5F2] border border-[#E7E7E2] text-[#111111] font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                    AM
                  </div>
                )}
              </div>
            );
          })}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#111111] text-[#D9F83F] font-bold flex items-center justify-center shrink-0 shadow-xs">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-[#F5F5F2] border border-[#E7E7E2] rounded-xl px-4 py-3 text-xs text-[#111111] flex items-center gap-2">
                <span className="inline-block w-2 h-2 bg-[#D9F83F] rounded-full animate-ping" />
                <span className="text-[11px] font-medium text-[#8B8D86] ml-1">Analyzing financial state...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Quick Questions */}
        <div className="p-3.5 bg-[#F5F5F2] border-t border-[#E7E7E2]">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#8B8D86] block mb-2">
            Suggested Prompts (Click to inquire)
          </span>
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
            {suggestedQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSendMessage(q)}
                disabled={isTyping}
                className="shrink-0 px-3 py-1.5 text-[11px] font-semibold text-[#111111] bg-white hover:bg-[#D9F83F] border border-[#E7E7E2] rounded-full transition-colors disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="p-3.5 bg-white border-t border-[#E7E7E2]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2.5"
          >
            <input
              type="text"
              placeholder="Ask questions about invoices, FX exposure, cash flow, or documentation..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isTyping}
              className="flex-1 py-2 px-3 text-xs bg-[#F5F5F2] text-[#111111] border border-[#E7E7E2] rounded-lg focus:bg-white focus:border-[#111111] transition-colors disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || isTyping}
              className="px-4 py-2 text-xs font-bold text-[#111111] bg-[#D9F83F] hover:bg-[#c8ea2e] disabled:bg-[#F5F5F2] disabled:text-[#8B8D86] rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
              aria-label="Send message to co-pilot"
            >
              <span>Send</span>
              <Send className="w-3.5 h-3.5 text-[#111111]" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
