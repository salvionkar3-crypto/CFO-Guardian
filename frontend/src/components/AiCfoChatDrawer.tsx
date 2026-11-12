"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  MessageSquare,
  X,
  Send,
  Sparkles,
  Bot,
  User,
  PlusCircle,
  History,
  TrendingUp,
  DollarSign,
  PieChart,
  Scale,
  AlertTriangle,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api";
import { ChatMessage, ChatSession, ChatQueryResponse } from "@/types";

interface AiCfoChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currency?: string;
  initialPrompt?: string;
}

const PRESET_PROMPTS = [
  {
    label: "Monthly Performance",
    prompt: "How is my business performing this month?",
    icon: TrendingUp,
  },
  {
    label: "Biggest Expenses",
    prompt: "What are my biggest expenses?",
    icon: PieChart,
  },
  {
    label: "Top Vendor",
    prompt: "Which vendor costs me the most?",
    icon: DollarSign,
  },
  {
    label: "Month vs Last Month",
    prompt: "Compare this month with last month.",
    icon: Scale,
  },
  {
    label: "Can I afford $15,000?",
    prompt: "Can I afford a $15,000 payment?",
    icon: DollarSign,
  },
  {
    label: "Unusual Spending",
    prompt: "Identify unusual spending patterns.",
    icon: AlertTriangle,
  },
];

export const AiCfoChatDrawer: React.FC<AiCfoChatDrawerProps> = ({
  isOpen,
  onClose,
  currency = "USD",
  initialPrompt,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load available sessions when opened
  useEffect(() => {
    if (isOpen) {
      loadSessions(Boolean(initialPrompt));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // Auto scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadSessions = async (skipSelect?: boolean) => {
    try {
      const data = await api.getChatSessions();
      setSessions(data);
      if (data.length > 0 && !currentSessionId && !skipSelect && !initialPrompt) {
        // Load the most recent session
        selectSession(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load chat sessions:", err);
    }
  };

  const selectSession = async (sessionId: number) => {
    try {
      setLoading(true);
      setCurrentSessionId(sessionId);
      setShowHistory(false);
      const detail = await api.getChatSessionDetail(sessionId);
      setMessages(detail.messages);
    } catch (err) {
      console.error("Failed to load session detail:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartNewSession = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setShowHistory(false);
  };

  const handleSend = async (customPrompt?: string) => {
    const textToSend = (customPrompt || inputPrompt).trim();
    if (!textToSend || loading) return;

    setInputPrompt("");
    setLoading(true);

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      session_id: currentSessionId || 0,
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const resp: ChatQueryResponse = await api.askCfo(textToSend, currentSessionId);
      setCurrentSessionId(resp.session_id);

      const assistantMsg: ChatMessage = {
        id: resp.message_id,
        session_id: resp.session_id,
        role: "assistant",
        content: resp.reply,
        reasoning_meta: JSON.stringify({
          tools_executed: resp.tools_executed,
          insight_card: resp.insight_card,
        }),
        created_at: resp.timestamp,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh sessions list in background without resetting current view
      loadSessions(true);
    } catch (err: unknown) {
      console.error("[AiCfoChatDrawer] Consultation error:", err);
      const errObj = err as { message?: string; status?: number } | null;
      let errorContent =
        "⚠️ **Connection Error:** Unable to reach Guardian CFO backend. Please verify that your local backend server is running and try again.";

      if (errObj?.message) {
        if (errObj.message.includes("401") || errObj.message.toLowerCase().includes("credential")) {
          errorContent =
            "🔒 **Authentication Required:** Session expired or unauthenticated. Please click **Sign In / Demo** in the top header.";
        } else if (errObj.status === 0 || errObj.message.includes("Unable to connect")) {
          errorContent = `⚠️ **Connection Error:** ${errObj.message}`;
        } else {
          errorContent = `⚠️ **AI CFO Advisory Notice:** ${errObj.message}`;
        }
      }

      const errorMsg: ChatMessage = {
        id: Date.now() + 1,
        session_id: currentSessionId || 0,
        role: "assistant",
        content: errorContent,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  // If opened with an initial prompt from quick-action pills, send immediately
  useEffect(() => {
    if (isOpen && initialPrompt) {
      handleSend(initialPrompt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialPrompt]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm animate-fade-in flex justify-end">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-slide-left">
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 shadow-md">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-white tracking-wide text-base">
                  Guardian AI CFO
                </h3>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800">
                  Read-Only Advisory
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Live ledger intelligence &bull; Multi-turn tool reasoning
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              title="Chat History"
              className={`p-2 rounded-lg transition-colors ${
                showHistory
                  ? "bg-cyan-500/20 text-cyan-400"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <History className="w-5 h-5" />
            </button>
            <button
              onClick={handleStartNewSession}
              title="New Consultation"
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <PlusCircle className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              title="Close Drawer"
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Security Guardrail Banner */}
        <div className="px-4 py-2 bg-slate-950 border-b border-slate-800/80 flex items-center space-x-2 text-xs text-slate-400">
          <Lock className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
          <span>
            Strictly advisory: AI CFO cannot authorize payouts or alter account balances.
          </span>
        </div>

        {/* Sessions History View (Toggleable) */}
        {showHistory ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-950/60">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Prior Consultations ({sessions.length})
              </span>
              <button
                onClick={handleStartNewSession}
                className="text-xs text-cyan-400 hover:underline flex items-center space-x-1"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>Start Fresh</span>
              </button>
            </div>

            {sessions.length === 0 ? (
              <div className="text-center py-10 text-slate-500 text-sm">
                No past consultations found.
              </div>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => selectSession(s.id)}
                  className={`p-3 rounded-xl border transition cursor-pointer ${
                    currentSessionId === s.id
                      ? "bg-cyan-950/30 border-cyan-500/50 text-white"
                      : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium line-clamp-1">{s.title}</span>
                    <span className="text-xs text-slate-500">
                      {new Date(s.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center space-x-2 text-xs text-slate-400">
                    <MessageSquare className="w-3 h-3" />
                    <span>{s.message_count} messages</span>
                  </div>
                </div>
              ))
            )}
          </div>
        ) : (
          /* Main Chat Area */
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="py-8 text-center space-y-4">
                <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mx-auto shadow-inner">
                  <Bot className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-lg font-semibold text-white">
                    What would you like to analyze today?
                  </h4>
                  <p className="text-xs text-slate-400 max-w-sm mx-auto">
                    Guardian CFO executes real-time database queries to explain your
                    cash flow, cost drivers, affordability, and runway.
                  </p>
                </div>

                {/* Quick Prompts */}
                <div className="pt-4 grid grid-cols-2 gap-2 text-left">
                  {PRESET_PROMPTS.map((p, idx) => {
                    const Icon = p.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleSend(p.prompt)}
                        className="p-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 hover:border-cyan-500/40 transition group flex flex-col justify-between"
                      >
                        <div className="flex items-center space-x-2 text-cyan-400 mb-1">
                          <Icon className="w-4 h-4" />
                          <span className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300">
                            {p.label}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400 line-clamp-1">
                          {p.prompt}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Conversation Messages */}
            {messages.map((m) => {
              const isAssistant = m.role === "assistant";
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              let reasoningMeta: { tools_executed?: string[]; insight_card?: any } | null = null;
              if (m.reasoning_meta) {
                try {
                  reasoningMeta = JSON.parse(m.reasoning_meta);
                } catch {
                  // Ignore parse error
                }
              }

              return (
                <div
                  key={m.id}
                  className={`flex items-start space-x-3 ${
                    isAssistant ? "" : "flex-row-reverse space-x-reverse"
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold ${
                      isAssistant
                        ? "bg-gradient-to-tr from-cyan-600 to-blue-600 text-white shadow-sm"
                        : "bg-slate-700 text-slate-200"
                    }`}
                  >
                    {isAssistant ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                  </div>

                  <div className={`max-w-[85%] space-y-2 ${isAssistant ? "" : "text-right"}`}>
                    {/* Tool Badges */}
                    {isAssistant && reasoningMeta?.tools_executed && reasoningMeta.tools_executed.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pb-1">
                        {reasoningMeta.tools_executed.map((tool, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-cyan-950/70 border border-cyan-800 text-cyan-300 text-[10px] font-mono"
                          >
                            <Sparkles className="w-2.5 h-2.5" />
                            <span>Executed: {tool}</span>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Message Bubble */}
                    <div
                      className={`p-3.5 rounded-2xl text-sm leading-relaxed ${
                        isAssistant
                          ? "bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-tl-sm text-left"
                          : "bg-cyan-600 text-white rounded-tr-sm text-left"
                      }`}
                    >
                      <div
                        className="prose prose-invert prose-sm max-w-none space-y-2"
                        dangerouslySetInnerHTML={{
                          __html: formatMarkdownToHtml(m.content),
                        }}
                      />
                    </div>

                    {/* Structured Insight Card (if attached to message) */}
                    {isAssistant && reasoningMeta?.insight_card && (
                      <InsightCardRenderer card={reasoningMeta.insight_card} currency={currency} />
                    )}

                    <div className="text-[10px] text-slate-500 px-1">
                      {new Date(m.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Thinking / Loading indicator */}
            {loading && (
              <div className="flex items-start space-x-3 animate-fade-in">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white flex-shrink-0 animate-pulse">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-3.5 rounded-2xl bg-slate-800/80 border border-slate-700/60 rounded-tl-sm space-y-2">
                  <div className="flex items-center space-x-2 text-xs text-cyan-400">
                    <Sparkles className="w-3.5 h-3.5 animate-spin" />
                    <span>Guardian CFO is analyzing ledger transactions...</span>
                  </div>
                  <div className="flex space-x-1.5 py-1">
                    <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" />
                    <div
                      className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    />
                    <div
                      className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input Box */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/90 space-y-2">
          {/* Quick chip bar when in conversation */}
          {messages.length > 0 && !showHistory && (
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-xs">
              <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider flex-shrink-0">
                Ask:
              </span>
              {PRESET_PROMPTS.slice(0, 4).map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(p.prompt)}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs whitespace-nowrap transition disabled:opacity-50"
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center space-x-2"
          >
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              placeholder="Ask Guardian CFO anything about your business finances..."
              disabled={loading}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputPrompt.trim() || loading}
              className="p-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

// ==========================================
// Insight Card Visual Renderer
// ==========================================

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const InsightCardRenderer: React.FC<{ card: any; currency: string }> = ({
  card,
  currency,
}) => {
  if (!card || !card.type) return null;

  const { type, data } = card;

  if (type === "affordability") {
    const isAffordable = data.verdict === "AFFORDABLE";
    const requiresDual = data.verdict === "REQUIRES_DUAL_EXECUTIVE_APPROVAL";
    return (
      <div className="p-3 rounded-xl bg-slate-900 border border-cyan-800/50 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">
            Affordability Matrix
          </span>
          <span
            className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
              isAffordable
                ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                : requiresDual
                ? "bg-amber-950 text-amber-400 border border-amber-800"
                : "bg-rose-950 text-rose-400 border border-rose-800"
            }`}
          >
            {data.verdict}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-800">
          <div>
            <div className="text-slate-500">Proposed Amount</div>
            <div className="font-semibold text-white">
              ${Number(data.requested_amount || 0).toLocaleString()} {currency}
            </div>
          </div>
          <div>
            <div className="text-slate-500">Runway Impact</div>
            <div className="font-semibold text-amber-400">
              -{data.runway_impact_days} Days
            </div>
          </div>
          <div>
            <div className="text-slate-500">Post-Purchase Runway</div>
            <div className="font-semibold text-cyan-400">
              {data.projected_runway_months} Months
            </div>
          </div>
          <div>
            <div className="text-slate-500">Treasury Buffer</div>
            <div className="font-semibold text-emerald-400">
              ${Number(data.post_purchase_balance || 0).toLocaleString()}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === "category_breakdown" && data.top_expense_categories) {
    return (
      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">
            Top Cost Drivers
          </span>
          <span className="text-[10px] text-slate-400">
            Total: ${Number(data.total_expenses || 0).toLocaleString()}
          </span>
        </div>
        <div className="space-y-1.5 pt-1">
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          {data.top_expense_categories.slice(0, 3).map((c: any, i: number) => (
            <div key={i} className="space-y-0.5">
              <div className="flex justify-between text-[11px]">
                <span className="text-slate-300">{c.category}</span>
                <span className="font-semibold text-white">
                  ${Number(c.amount).toLocaleString()} ({c.percentage_share}%)
                </span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-cyan-500 rounded-full"
                  style={{ width: `${Math.min(100, c.percentage_share)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "comparison") {
    return (
      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2 text-xs">
        <span className="font-semibold text-slate-300 uppercase tracking-wider text-[10px]">
          Month-over-Month Delta
        </span>
        <div className="grid grid-cols-3 gap-2 pt-1 border-t border-slate-800 text-center">
          <div>
            <div className="text-[10px] text-slate-500">Revenue Growth</div>
            <div
              className={`font-bold ${
                data.revenue_growth_pct >= 0 ? "text-emerald-400" : "text-rose-400"
              }`}
            >
              {data.revenue_growth_pct > 0 ? "+" : ""}
              {data.revenue_growth_pct}%
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500">Expense Delta</div>
            <div
              className={`font-bold ${
                data.expense_change_pct <= 0 ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {data.expense_change_pct > 0 ? "+" : ""}
              {data.expense_change_pct}%
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-500">Net Flow</div>
            <div className="font-bold text-cyan-400">
              ${Number(data.net_cash_flow_current || 0).toLocaleString()}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

// ==========================================
// Simple Markdown Formatter Helper
// ==========================================

function formatMarkdownToHtml(text: string): string {
  if (!text) return "";

  let html = text
    // Replace markdown bold **text** with <strong>text</strong>
    .replace(/\*\*(.*?)\*\*/g, "<strong class='text-white font-semibold'>$1</strong>")
    // Replace markdown inline code `code`
    .replace(/`(.*?)`/g, "<code class='px-1.5 py-0.5 rounded bg-slate-950 text-cyan-300 font-mono text-xs border border-slate-800'>$1</code>")
    // Headings
    .replace(/^### (.*$)/gim, "<h4 class='text-sm font-bold text-cyan-300 mt-2 mb-1'>$1</h4>")
    .replace(/^## (.*$)/gim, "<h3 class='text-base font-bold text-white mt-3 mb-1'>$1</h3>")
    // Blockquotes
    .replace(/^\> (.*$)/gim, "<blockquote class='border-l-2 border-cyan-500 pl-2 py-0.5 my-1 text-slate-400 italic text-xs'>$1</blockquote>")
    // Bullet lists
    .replace(/^\- (.*$)/gim, "<li class='ml-4 list-disc text-slate-300'>$1</li>");

  // Wrap newlines
  html = html.replace(/\n\n/g, "<div class='h-2'></div>");

  return html;
}
