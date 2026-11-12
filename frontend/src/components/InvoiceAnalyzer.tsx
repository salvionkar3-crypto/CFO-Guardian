"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, AlertTriangle, ShieldCheck, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { InvoiceSubmission } from "@/types";

interface InvoiceAnalyzerProps {
  onSuccess: () => void;
  onStageChange: (stage: string) => void;
}

const PRESETS: InvoiceSubmission[] = [
  {
    title: "AWS Cloud Infrastructure - Monthly",
    vendor: "Amazon Web Services",
    vendor_email: "billing@aws.amazon.com",
    category: "Infrastructure",
    amount: 320.0,
    currency: "USD",
    notes: "Production EC2 instances and Postgres RDS cluster",
  },
  {
    title: "Q4 Growth Marketing Campaign",
    vendor: "HyperScale Media",
    vendor_email: "accounts@hyperscalemedia.io",
    category: "Marketing",
    amount: 1450.0,
    currency: "USD",
    notes: "Targeted LinkedIn Ads and conversion funnel optimization",
  },
  {
    title: "Suspicious Urgent Consultant Fee",
    vendor: "FastPay International Ltd",
    vendor_email: "wire-transfer@fastpay-offshore99.xyz",
    category: "Consulting",
    amount: 6200.0,
    currency: "USD",
    notes: "Urgent wire required before contract countersignature",
  },
];

export const InvoiceAnalyzer: React.FC<InvoiceAnalyzerProps> = ({ onSuccess, onStageChange }) => {
  const [formData, setFormData] = useState<InvoiceSubmission>(PRESETS[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resultMessage, setResultMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setResultMessage(null);

    try {
      onStageChange("UNDERSTAND");

      // 1. Ingest & Analyze via AI CFO
      const analysis = await api.analyzeInvoice(formData);
      onStageChange("ANALYZE");

      // 2. Investigate & Decide via Guardian AI
      const risk = await api.assessRisk(analysis.decision_id);
      onStageChange("DECIDE");

      setResultMessage({
        type: "success",
        text: `Analysis complete! CFO: ${analysis.recommendation} | Guardian AI Verdict: ${risk.verdict} (Risk Score: ${risk.risk_score}/100)`,
      });

      onSuccess();
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Failed to process invoice through the Guardian CFO pipeline.";
      setResultMessage({
        type: "error",
        text: errorMsg,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Invoice Evaluation Engine</h3>
            <p className="text-xs text-slate-400">
              Submit an invoice to initiate the 8-stage verification pipeline
            </p>
          </div>
        </div>

        {/* Preset Selector */}
        <div className="hidden sm:flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-slate-400">Quick Test:</span>
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setFormData(preset)}
              className="text-[11px] font-semibold px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
            >
              Preset {idx + 1}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Invoice Title</label>
            <input
              type="text"
              required
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="e.g. Server Renewal"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Vendor / Payee</label>
            <input
              type="text"
              required
              value={formData.vendor}
              onChange={(e) => setFormData({ ...formData, vendor: e.target.value })}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="e.g. AWS"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Payee Email</label>
            <input
              type="email"
              required
              value={formData.vendor_email}
              onChange={(e) => setFormData({ ...formData, vendor_email: e.target.value })}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-cyan-500 transition"
              placeholder="billing@vendor.com"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Amount ($ USD)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white font-mono focus:outline-none focus:border-cyan-500 transition"
              placeholder="0.00"
            />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-amber-400" />
            <span>Checks runway depletion, duplicate invoices, and vendor domain threat level</span>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs tracking-wide shadow-lg shadow-cyan-500/25 flex items-center justify-center gap-2 transition disabled:opacity-50"
          >
            {isSubmitting ? (
              <span>Executing Pipeline...</span>
            ) : (
              <>
                <span>Run CFO & Guardian Analysis</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>

        {resultMessage && (
          <div
            className={`p-3 rounded-xl text-xs font-medium border flex items-center gap-2 ${
              resultMessage.type === "success"
                ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-300"
                : "bg-rose-950/40 border-rose-800/80 text-rose-300"
            }`}
          >
            {resultMessage.type === "success" ? (
              <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            )}
            <span>{resultMessage.text}</span>
          </div>
        )}
      </form>
    </div>
  );
};
