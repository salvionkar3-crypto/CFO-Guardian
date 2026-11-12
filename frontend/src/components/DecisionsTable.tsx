"use client";

import React, { useState } from "react";
import { CheckCircle2, AlertOctagon, HelpCircle, ExternalLink, ShieldCheck, Loader2 } from "lucide-react";
import { FinancialDecision } from "@/types";
import { api } from "@/lib/api";

interface DecisionsTableProps {
  decisions: FinancialDecision[];
  onRefresh: () => void;
  onSelectDecision: (id: number) => void;
}

export const DecisionsTable: React.FC<DecisionsTableProps> = ({ decisions, onRefresh, onSelectDecision }) => {
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [paymentNotice, setPaymentNotice] = useState<{ decisionId: number; text: string; error?: boolean } | null>(null);

  const handleInitiatePayment = async (decision: FinancialDecision) => {
    setProcessingId(decision.id);
    setPaymentNotice(null);

    try {
      const order = await api.createPaymentOrder(decision.id);
      if (order.approval_url) {
        setPaymentNotice({
          decisionId: decision.id,
          text: `PayPal Order created (${order.paypal_order_id}). Redirecting to PayPal Sandbox...`,
        });
        window.open(order.approval_url, "_blank");
      } else {
        setPaymentNotice({
          decisionId: decision.id,
          text: `PayPal Order created (${order.paypal_order_id}). Awaiting customer approval in Sandbox.`,
        });
      }
      onRefresh();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Payment initiation failed. Verify PayPal Sandbox credentials in backend/.env.";
      setPaymentNotice({
        decisionId: decision.id,
        text: errorMessage,
        error: true,
      });
    } finally {
      setProcessingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">Approved</span>;
      case "PAID":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800">Paid (PayPal)</span>;
      case "REJECTED":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-950 text-rose-400 border border-rose-800">Blocked / Rejected</span>;
      case "AWAITING_APPROVAL":
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-950 text-amber-400 border border-amber-800">Review Required</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-300">{status}</span>;
    }
  };

  const getRecommendationIcon = (rec: string) => {
    if (rec === "APPROVE")
      return (
        <span title="CFO Recommends Approval">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        </span>
      );
    if (rec === "REJECT")
      return (
        <span title="CFO Recommends Rejection">
          <AlertOctagon className="h-4 w-4 text-rose-400" />
        </span>
      );
    return (
      <span title="Flagged for Executive Review">
        <HelpCircle className="h-4 w-4 text-amber-400" />
      </span>
    );
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white">Financial Decision Register</h3>
          <p className="text-xs text-slate-400">
            Audit-tracked invoices and their automated CFO & Guardian verification states
          </p>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          {decisions.length} Record{decisions.length === 1 ? "" : "s"}
        </span>
      </div>

      {decisions.length === 0 ? (
        <div className="py-12 text-center border border-dashed border-slate-800 rounded-xl">
          <ShieldCheck className="h-10 w-10 text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-400 font-medium">No financial decisions logged yet.</p>
          <p className="text-xs text-slate-500 mt-1">Use the Invoice Evaluation Engine above to submit a test invoice.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-3 px-3">ID & Title</th>
                <th className="py-3 px-3">Vendor</th>
                <th className="py-3 px-3">Amount</th>
                <th className="py-3 px-3">CFO Rationale</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {decisions.map((decision) => (
                <tr key={decision.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-3">
                    <div className="flex items-center gap-2">
                      {getRecommendationIcon(decision.cfo_recommendation)}
                      <div>
                        <div className="font-semibold text-white">{decision.title}</div>
                        <div className="text-[10px] text-slate-400 font-mono">#{decision.id} • {decision.category}</div>
                      </div>
                    </div>
                  </td>

                  <td className="py-3.5 px-3">
                    <div className="font-medium text-slate-200">{decision.vendor}</div>
                    <div className="text-[10px] text-slate-400 font-mono truncate max-w-[140px]">{decision.vendor_email}</div>
                  </td>

                  <td className="py-3.5 px-3 font-mono font-bold text-white text-sm">
                    ${decision.amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </td>

                  <td className="py-3.5 px-3 max-w-xs">
                    <p className="text-[11px] text-slate-400 truncate" title={decision.cfo_rationale || ""}>
                      {decision.cfo_rationale || "Analysis pending"}
                    </p>
                    <button
                      onClick={() => onSelectDecision(decision.id)}
                      className="text-[10px] text-cyan-400 hover:text-cyan-300 underline mt-0.5"
                    >
                      View Full Explainability Trail
                    </button>
                  </td>

                  <td className="py-3.5 px-3">
                    {getStatusBadge(decision.status)}
                  </td>

                  <td className="py-3.5 px-3">
                    {decision.status === "APPROVED" ? (
                      <button
                        onClick={() => handleInitiatePayment(decision)}
                        disabled={processingId === decision.id}
                        className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center gap-1.5 transition disabled:opacity-50"
                      >
                        {processingId === decision.id ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin" />
                            <span>PayPal...</span>
                          </>
                        ) : (
                          <>
                            <span>Pay via PayPal</span>
                            <ExternalLink className="h-3 w-3" />
                          </>
                        )}
                      </button>
                    ) : decision.status === "PAID" ? (
                      <span className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Settled
                      </span>
                    ) : decision.status === "REJECTED" ? (
                      <span className="text-[11px] font-semibold text-rose-400">
                        Payment Blocked
                      </span>
                    ) : (
                      <button
                        onClick={() => onSelectDecision(decision.id)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition"
                      >
                        Review
                      </button>
                    )}

                    {paymentNotice && paymentNotice.decisionId === decision.id && (
                      <div className={`mt-1.5 text-[10px] ${paymentNotice.error ? "text-rose-400" : "text-cyan-300"}`}>
                        {paymentNotice.text}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
