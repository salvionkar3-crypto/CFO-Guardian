"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { WorkflowBar } from "@/components/WorkflowBar";
import { FinancialSummaryCards } from "@/components/FinancialSummaryCards";
import { CashFlowTrendChart } from "@/components/CashFlowTrendChart";
import { CategoryDistribution } from "@/components/CategoryDistribution";
import { ExpenseAnomaliesBanner } from "@/components/ExpenseAnomaliesBanner";
import { RecurringExpensesCard } from "@/components/RecurringExpensesCard";
import { InvoiceAnalyzer } from "@/components/InvoiceAnalyzer";
import { DecisionsTable } from "@/components/DecisionsTable";
import { AuditTimeline } from "@/components/AuditTimeline";
import { AuthModal } from "@/components/AuthModal";
import { AiCfoBanner } from "@/components/AiCfoBanner";
import { AiCfoChatDrawer } from "@/components/AiCfoChatDrawer";
import { GuardianSecurityCenter } from "@/components/GuardianSecurityCenter";
import { PaymentCenter } from "@/components/PaymentCenter";
import { SecurityActivity } from "@/components/SecurityActivity";
import { PaymentDecisionRoom } from "@/components/PaymentDecisionRoom";
import { Bot, Sparkles, TrendingUp, ShieldAlert, CreditCard, LayoutDashboard, WalletCards, ShieldCheck, Scale } from "lucide-react";
import { api, authStorage } from "@/lib/api";
import {
  SystemHealth,
  TokenResponse,
  FinancialSummary,
  TrendItem,
  CategoryBreakdownItem,
  ExpenseAnomaly,
  RecurringExpensesResponse,
  FinancialDecision,
  AuditLogItem,
} from "@/types";

export default function DashboardPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [authData, setAuthData] = useState<TokenResponse | null>(null);
  const [isAuthOpen, setIsAuthOpen] = useState<boolean>(false);

  // Financial Analytics State
  const [period, setPeriod] = useState<string>("current_month");
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [categories, setCategories] = useState<CategoryBreakdownItem[]>([]);
  const [totalExpenses, setTotalExpenses] = useState<number>(0);
  const [anomalies, setAnomalies] = useState<ExpenseAnomaly[]>([]);
  const [recurring, setRecurring] = useState<RecurringExpensesResponse | null>(null);

  // Workflow & Decision Register State
  const [decisions, setDecisions] = useState<FinancialDecision[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [currentStage, setCurrentStage] = useState<string>("UNDERSTAND");
  const [selectedDecisionId, setSelectedDecisionId] = useState<number | null>(null);

  // Active Dashboard Section Tab
  const [activeTab, setActiveTab] = useState<"all" | "decision-room" | "security" | "payments" | "activity" | "analytics" | "decisions">("decision-room");

  // AI CFO Consultation State
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);
  const [initialChatPrompt, setInitialChatPrompt] = useState<string | undefined>(undefined);

  const handleOpenChat = (prompt?: string) => {
    setInitialChatPrompt(prompt);
    setIsChatOpen(true);
  };

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      // 1. System Health
      const h = await api.getHealth().catch(() => null);
      if (h) setHealth(h);

      // 2. Financial Analytics Engine Calls
      const [sumRes, trendRes, catRes, anomRes, recRes, decRes, logRes] = await Promise.all([
        api.getFinancialSummary(period).catch(() => null),
        api.getFinancialTrends(6).catch(() => []),
        api.getCategoryBreakdown().catch(() => null),
        api.getExpenseAnomalies().catch(() => []),
        api.getRecurringExpenses().catch(() => null),
        api.getDecisions().catch(() => []),
        api.getAuditLogs().catch(() => []),
      ]);

      if (sumRes) setSummary(sumRes);
      setTrends(trendRes);
      if (catRes) {
        setCategories(catRes.expenses_by_category);
        setTotalExpenses(catRes.total_expenses);
      }
      setAnomalies(anomRes);
      if (recRes) setRecurring(recRes);
      setDecisions(decRes);
      setAuditLogs(logRes);
    } catch (err) {
      console.error("Dashboard data fetching error:", err);
    } finally {
      setLoading(false);
    }
  }, [period]);

  // Initial Auth Check & Auto Demo Initialization
  useEffect(() => {
    const initAuth = async () => {
      const existingToken = authStorage.getToken();
      if (existingToken) {
        try {
          const profile = await api.getMe();
          setAuthData({
            access_token: existingToken,
            token_type: "bearer",
            user: profile.user,
            business: profile.business,
          });
          fetchDashboardData();
          return;
        } catch {
          authStorage.clearToken();
        }
      }

      // If no session exists, perform instant demo login for zero-friction evaluation
      try {
        const demoAuth = await api.demoLogin();
        setAuthData(demoAuth);
        fetchDashboardData();
      } catch (err) {
        console.error("Auto demo authentication error:", err);
        fetchDashboardData();
      }
    };

    initAuth();
  }, [fetchDashboardData]);

  // Periodic Telemetry Refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const handleLogout = async () => {
    await api.logout();
    setAuthData(null);
    fetchDashboardData();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-white">
      {/* Top Telemetry Header */}
      <Header
        health={health}
        loading={loading}
        onRefresh={fetchDashboardData}
        authData={authData}
        onOpenAuth={() => setIsAuthOpen(true)}
        onLogout={handleLogout}
        onOpenChat={() => handleOpenChat()}
        onSelectDecision={(id) => {
          setSelectedDecisionId(id);
          setActiveTab("activity");
        }}
        onNavigateToSecurity={() => setActiveTab("activity")}
      />

      {/* Main Command Center */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Core Autonomous Workflow Pipeline Bar */}
        <WorkflowBar currentStage={currentStage} />

        {/* AI CFO Natural Language Consultation Banner */}
        <AiCfoBanner
          onOpenChat={handleOpenChat}
          currency={summary?.currency || "USD"}
        />

        {/* Dashboard Navigation Tabs */}
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-3 overflow-x-auto text-xs">
          <button
            onClick={() => setActiveTab("decision-room")}
            className={`px-3.5 py-2 rounded-xl font-bold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "decision-room"
                ? "bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-600/30 ring-1 ring-cyan-400/50"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-cyan-300" />
            <span>Payment Decision Room</span>
            <span className="text-[9px] uppercase px-1.5 py-0.2 bg-cyan-950 text-cyan-300 rounded font-mono border border-cyan-500/40">Live</span>
          </button>

          <button
            onClick={() => setActiveTab("all")}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "all"
                ? "bg-slate-800 text-white border border-slate-700 shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Full Command Center</span>
          </button>

          <button
            onClick={() => setActiveTab("security")}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "security"
                ? "bg-gradient-to-r from-indigo-600 to-cyan-600 text-white shadow-md shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Guardian AI Security Center</span>
          </button>

          <button
            onClick={() => setActiveTab("analytics")}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "analytics"
                ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Financial Analytics</span>
          </button>

          <button
            onClick={() => setActiveTab("payments")}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "payments"
                ? "bg-gradient-to-r from-blue-600 to-teal-600 text-white shadow-md shadow-blue-600/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <WalletCards className="w-3.5 h-3.5" />
            <span>Secure Payment Center</span>
          </button>

          <button
            onClick={() => setActiveTab("activity")}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "activity"
                ? "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-indigo-600/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Security Activity & Audit</span>
          </button>

          <button
            onClick={() => setActiveTab("decisions")}
            className={`px-3.5 py-2 rounded-xl font-semibold flex items-center space-x-1.5 transition whitespace-nowrap ${
              activeTab === "decisions"
                ? "bg-blue-600 text-white shadow-md shadow-blue-600/20"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>Decisions & PayPal Disbursements</span>
          </button>
        </div>

        {/* PRIMARY HERO: PAYMENT DECISION ROOM */}
        {(activeTab === "all" || activeTab === "decision-room") && (
          <PaymentDecisionRoom
            initialDraftId={selectedDecisionId}
            onRefreshParent={fetchDashboardData}
            currency={summary?.currency || "USD"}
          />
        )}

        {/* SECTION 1: GUARDIAN AI SECURITY CENTER */}
        {(activeTab === "all" || activeTab === "security") && (
          <GuardianSecurityCenter
            decisions={decisions}
            onRefresh={fetchDashboardData}
            currency={summary?.currency || "USD"}
          />
        )}

        {/* SECTION 2: SECURE PAYMENT MANAGEMENT CENTER */}
        {(activeTab === "all" || activeTab === "payments") && (
          <PaymentCenter
            onRefreshParent={fetchDashboardData}
            currency={summary?.currency || "USD"}
          />
        )}

        {/* SECTION: SECURITY ACTIVITY, 6-QUESTION EXPLAINABILITY & WEBHOOKS */}
        {(activeTab === "all" || activeTab === "activity") && (
          <SecurityActivity
            initialDecisionId={selectedDecisionId}
            onSelectDraft={(id) => {
              setSelectedDecisionId(id);
              setActiveTab("decision-room");
            }}
          />
        )}

        {/* SECTION 3: FINANCIAL ANALYTICS */}
        {(activeTab === "all" || activeTab === "analytics") && (
          <>
            <FinancialSummaryCards
              summary={summary}
              period={period}
              onPeriodChange={(newPeriod) => setPeriod(newPeriod)}
            />

            <ExpenseAnomaliesBanner anomalies={anomalies} />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <div className="lg:col-span-7">
                <CashFlowTrendChart trends={trends} />
              </div>
              <div className="lg:col-span-5">
                <CategoryDistribution
                  categories={categories}
                  totalExpenses={totalExpenses}
                />
              </div>
            </div>
          </>
        )}

        {/* SECTION 3: INVOICE EVALUATION, RECURRING EXPENSES & DECISIONS */}
        {(activeTab === "all" || activeTab === "decisions") && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <div className="lg:col-span-7">
                <InvoiceAnalyzer
                  onSuccess={fetchDashboardData}
                  onStageChange={setCurrentStage}
                />
              </div>
              <div className="lg:col-span-5">
                <RecurringExpensesCard recurring={recurring} />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              <div className="lg:col-span-7">
                <DecisionsTable
                  decisions={decisions}
                  onRefresh={fetchDashboardData}
                  onSelectDecision={(id) => {
                    setSelectedDecisionId(id);
                    setActiveTab("decision-room");
                  }}
                />
              </div>
              <div className="lg:col-span-5">
                <AuditTimeline
                  logs={auditLogs}
                  selectedDecisionId={selectedDecisionId}
                  onClearFilter={() => setSelectedDecisionId(null)}
                />
              </div>
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Guardian CFO • Autonomous Financial Intelligence & Payment Security</span>
          <span className="font-mono text-slate-400">Deterministic Calculations • PayPal REST Sandbox</span>
        </div>
      </footer>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={(res) => {
          setAuthData(res);
          fetchDashboardData();
        }}
      />

      {/* AI CFO Conversational Drawer */}
      <AiCfoChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        currency={summary?.currency || "USD"}
        initialPrompt={initialChatPrompt}
      />

      {/* Floating AI CFO Chat Trigger */}
      <button
        onClick={() => handleOpenChat()}
        className="fixed bottom-6 right-6 z-30 px-4 py-3 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm shadow-2xl shadow-cyan-600/40 flex items-center space-x-2 border border-cyan-400/30 hover:scale-105 active:scale-95 transition-all group"
        title="Consult AI CFO in natural language"
      >
        <div className="relative">
          <Bot className="w-5 h-5" />
          <span className="absolute -top-1 -right-1 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-300 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400"></span>
          </span>
        </div>
        <span>Ask AI CFO</span>
        <Sparkles className="w-4 h-4 text-cyan-200 group-hover:rotate-12 transition-transform" />
      </button>
    </div>
  );
}
