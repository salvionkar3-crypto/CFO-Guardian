"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  AlertTriangle,
  Lock,
  Search,
  CheckCircle2,
  Hash,
  RefreshCw,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  GuardianRiskAssessment,
  SecurityAlert,
  FinancialDecision,
  RiskPolicyThresholds,
} from "@/types";

interface GuardianSecurityCenterProps {
  decisions: FinancialDecision[];
  onRefresh: () => void;
  currency?: string;
}

export const GuardianSecurityCenter: React.FC<GuardianSecurityCenterProps> = ({
  decisions,
  onRefresh,
}) => {
  const [assessments, setAssessments] = useState<GuardianRiskAssessment[]>([]);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [policy, setPolicy] = useState<RiskPolicyThresholds | null>(null);
  const [selectedAssessment, setSelectedAssessment] = useState<GuardianRiskAssessment | null>(null);
  const [selectedDecisionId, setSelectedDecisionId] = useState<number | null>(null);
  const [scanningId, setScanningId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");

  useEffect(() => {
    loadGuardianData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadGuardianData = async () => {
    setLoading(true);
    try {
      const [assRes, alertRes, polRes] = await Promise.all([
        api.getAssessments().catch(() => []),
        api.getSecurityAlerts().catch(() => []),
        api.getRiskPolicy().catch(() => null),
      ]);
      setAssessments(assRes);
      setAlerts(alertRes);
      if (polRes) setPolicy(polRes);

      if (assRes.length > 0 && !selectedAssessment) {
        setSelectedAssessment(assRes[0]);
        setSelectedDecisionId(assRes[0].decision_id);
      }
    } catch (err) {
      console.error("Failed to load Guardian AI data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleScanDraft = async (decisionId: number) => {
    setScanningId(decisionId);
    try {
      const result = await api.assessRisk(decisionId, true);
      setSelectedAssessment(result);
      setSelectedDecisionId(decisionId);
      await loadGuardianData();
      onRefresh();
    } catch (err) {
      console.error("Risk assessment failed:", err);
    } finally {
      setScanningId(null);
    }
  };

  const handleResolveAlert = async (alertId: number) => {
    try {
      await api.resolveSecurityAlert(alertId);
      await loadGuardianData();
    } catch (err) {
      console.error("Failed to resolve alert:", err);
    }
  };

  // Metrics
  const totalScanned = assessments.length;
  const safeCount = assessments.filter((a) => a.risk_level === "LOW").length;
  const reviewCount = assessments.filter((a) => a.risk_level === "MEDIUM" || a.risk_level === "HIGH").length;
  const blockedCount = assessments.filter((a) => a.risk_level === "CRITICAL").length;
  const openAlerts = alerts.filter((a) => a.status === "OPEN");

  const filteredAssessments = assessments.filter((a) => {
    if (filterSeverity === "ALL") return true;
    return a.risk_level === filterSeverity;
  });

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Policy Thresholds */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3.5">
            <div className="p-3 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-600 text-white shadow-lg shadow-indigo-500/20 flex-shrink-0">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-white tracking-tight">
                  Guardian AI Security Center
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-950 text-indigo-400 border border-indigo-800 flex items-center space-x-1">
                  <Lock className="w-2.5 h-2.5" />
                  <span>Deterministic 10-Signal Engine</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 max-w-2xl">
                Zero-trust pre-payment investigation. Every payment draft is audited for first-time vendors,
                unusual amounts, duplicate invoices, velocity bursts, and brand spoofing before authorization.
              </p>
            </div>
          </div>

          <button
            onClick={loadGuardianData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center space-x-2 text-xs font-medium self-start md:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
            <span>Sync Security Telemetry</span>
          </button>
        </div>

        {/* Policy Threshold Chips */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
            Risk Policy:
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 font-mono text-[11px] flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>LOW: 0–{policy?.low_max ?? 24} (Safe to Pay)</span>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-amber-950/60 text-amber-400 border border-amber-800/60 font-mono text-[11px] flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>MEDIUM: {policy?.medium_min ?? 25}–{policy?.medium_max ?? 49} (Manual Review)</span>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-orange-950/60 text-orange-400 border border-orange-800/60 font-mono text-[11px] flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
            <span>HIGH: {policy?.high_min ?? 50}–{policy?.high_max ?? 74} (Dual Executive Approval)</span>
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-rose-950/60 text-rose-400 border border-rose-800/60 font-mono text-[11px] flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            <span>CRITICAL: {policy?.critical_min ?? 75}–100 (Blocked)</span>
          </span>
        </div>
      </div>

      {/* 2. Security Telemetry Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-slate-400 font-medium">Total Audited Payments</div>
          <div className="text-2xl font-bold text-white mt-1">{totalScanned}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Pre-disbursement scans</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-emerald-400 font-medium">Safe to Pay (Low Risk)</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{safeCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Cleared for automated flow</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-amber-400 font-medium">Review Required</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{reviewCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Medium & High risk flagged</div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
          <div className="text-xs text-rose-400 font-medium">Threats Blocked</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{blockedCount}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Critical anomalies intercepted</div>
        </div>
      </div>

      {/* 3. Open Security Alerts (if any exist) */}
      {openAlerts.length > 0 && (
        <div className="p-4 rounded-2xl bg-rose-950/20 border border-rose-800/60 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs tracking-wider uppercase">
              <AlertTriangle className="w-4 h-4" />
              <span>Active Security Alerts ({openAlerts.length})</span>
            </div>
            <span className="text-[11px] text-rose-300">Action Required</span>
          </div>
          <div className="space-y-2">
            {openAlerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3 rounded-xl bg-slate-900/90 border border-rose-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-800">
                      {alert.severity}
                    </span>
                    <span className="text-sm font-semibold text-white">{alert.title}</span>
                  </div>
                  <p className="text-xs text-slate-400">{alert.description}</p>
                </div>
                <button
                  onClick={() => handleResolveAlert(alert.id)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-medium transition self-start sm:self-auto flex items-center space-x-1"
                >
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Mark Resolved</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Main Two-Column Layout: Drafts List + Deep Investigation Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Assessed Drafts & Pending Invoices */}
        <div className="lg:col-span-5 rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white text-sm">Payment Risk Register</h3>
            {/* Filter buttons */}
            <div className="flex items-center space-x-1 text-[10px]">
              {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((level) => (
                <button
                  key={level}
                  onClick={() => setFilterSeverity(level)}
                  className={`px-2 py-0.5 rounded-md font-semibold transition ${
                    filterSeverity === level
                      ? "bg-slate-700 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2.5 max-h-[560px] overflow-y-auto pr-1">
            {filteredAssessments.length === 0 ? (
              <div className="text-center py-10 text-slate-500 text-xs">
                No risk assessments match the selected filter.
              </div>
            ) : (
              filteredAssessments.map((a) => {
                const isSelected = selectedDecisionId === a.decision_id;
                const matchedDecision = decisions.find((d) => d.id === a.decision_id);

                return (
                  <div
                    key={a.id}
                    onClick={() => {
                      setSelectedAssessment(a);
                      setSelectedDecisionId(a.decision_id);
                    }}
                    className={`p-3.5 rounded-xl border transition cursor-pointer space-y-2 ${
                      isSelected
                        ? "bg-indigo-950/30 border-indigo-500/60 shadow-md"
                        : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white truncate max-w-[180px]">
                        {matchedDecision?.title || `Draft #${a.decision_id}`}
                      </span>
                      <RiskLevelBadge level={a.risk_level} score={a.risk_score} />
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>{matchedDecision?.vendor || "Vendor"}</span>
                      <span className="font-semibold text-slate-200">
                        ${Number(matchedDecision?.amount || 0).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px]">
                      <span className="text-slate-500">
                        {a.detected_signals?.length || a.flags?.length || 0} signal(s) detected
                      </span>
                      <span
                        className={`font-semibold ${
                          a.verdict === "SAFE_TO_PAY"
                            ? "text-emerald-400"
                            : a.verdict === "BLOCKED"
                            ? "text-rose-400"
                            : "text-amber-400"
                        }`}
                      >
                        {a.verdict}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Deep Investigation Inspector */}
        <div className="lg:col-span-7 rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-6">
          {selectedAssessment ? (
            <div className="space-y-6">
              {/* Top Inspector Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Investigation Report: Draft #{selectedAssessment.decision_id}
                    </span>
                    <RiskLevelBadge
                      level={selectedAssessment.risk_level}
                      score={selectedAssessment.risk_score}
                    />
                  </div>
                  <h3 className="text-base font-bold text-white">
                    {decisions.find((d) => d.id === selectedAssessment.decision_id)?.title ||
                      `Financial Decision #${selectedAssessment.decision_id}`}
                  </h3>
                </div>

                <button
                  onClick={() => handleScanDraft(selectedAssessment.decision_id)}
                  disabled={scanningId === selectedAssessment.decision_id}
                  className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center space-x-1.5 transition disabled:opacity-50 shadow-md self-start sm:self-auto"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${
                      scanningId === selectedAssessment.decision_id ? "animate-spin" : ""
                    }`}
                  />
                  <span>Re-audit Risk Signals</span>
                </button>
              </div>

              {/* Score Gauge & Verdict Matrix */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Score Gauge */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center text-center">
                  <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Threat Score
                  </div>
                  <div
                    className={`text-4xl font-extrabold tracking-tight ${
                      selectedAssessment.risk_score >= 75
                        ? "text-rose-400"
                        : selectedAssessment.risk_score >= 50
                        ? "text-orange-400"
                        : selectedAssessment.risk_score >= 25
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {selectedAssessment.risk_score}
                    <span className="text-sm font-normal text-slate-500">/100</span>
                  </div>
                  <div className="mt-1 text-xs font-semibold text-slate-300">
                    Category: {selectedAssessment.risk_level}
                  </div>
                </div>

                {/* Verdict & Recommended Action */}
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 md:col-span-2">
                  <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    Executive Decision & Action
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold ${
                        selectedAssessment.verdict === "SAFE_TO_PAY"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : selectedAssessment.verdict === "BLOCKED"
                          ? "bg-rose-950 text-rose-400 border border-rose-800"
                          : "bg-amber-950 text-amber-400 border border-amber-800"
                      }`}
                    >
                      Verdict: {selectedAssessment.verdict}
                    </span>
                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-200 border border-slate-700 font-mono">
                      Action: {selectedAssessment.recommended_action || "REVIEW"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 pt-1 leading-relaxed">
                    {selectedAssessment.plain_explanation ||
                      "Detailed explanation generated directly by Guardian AI deterministic rules."}
                  </p>
                </div>
              </div>

              {/* 10 Signals Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Detected Risk Signals ({selectedAssessment.detected_signals?.length || 0})
                  </h4>
                  <span className="text-[11px] text-slate-500">
                    Evaluated across 10 deterministic checks
                  </span>
                </div>

                {(!selectedAssessment.detected_signals ||
                  selectedAssessment.detected_signals.length === 0) ? (
                  <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/40 flex items-center space-x-3 text-emerald-400 text-xs">
                    <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                    <span>
                      Clean Scan: None of the 10 risk signals fired. Payee domain verified, no
                      invoice duplicates, and amount is within operational norms.
                    </span>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {selectedAssessment.detected_signals.map((sig, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                sig.severity === "CRITICAL"
                                  ? "bg-rose-950 text-rose-400 border border-rose-800"
                                  : sig.severity === "HIGH"
                                  ? "bg-orange-950 text-orange-400 border border-orange-800"
                                  : "bg-amber-950 text-amber-400 border border-amber-800"
                              }`}
                            >
                              {sig.severity}
                            </span>
                            <span className="text-xs font-bold text-white">{sig.name}</span>
                          </div>
                          <span className="text-xs font-mono font-bold text-rose-400">
                            +{sig.score_impact} pts
                          </span>
                        </div>
                        <p className="text-xs text-slate-400">{sig.description}</p>
                        <div className="text-xs text-slate-300 bg-slate-900/80 p-2 rounded-lg border border-slate-800/60 font-mono text-[11px]">
                          <strong>Evidence:</strong> {sig.evidence}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Missing Information Checklist */}
              {selectedAssessment.missing_information &&
                selectedAssessment.missing_information.length > 0 && (
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <Search className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Missing Compliance Information</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-slate-400 list-disc list-inside">
                      {selectedAssessment.missing_information.map((item, i) => (
                        <li key={i} className="text-slate-300">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

              {/* Cryptographic SHA-256 Digest */}
              {selectedAssessment.verification_hash && (
                <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
                  <div className="flex items-center space-x-2">
                    <Hash className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Integrity Digest (SHA-256):</span>
                  </div>
                  <span className="text-slate-200 select-all font-mono text-[11px]">
                    {selectedAssessment.verification_hash.substring(0, 24)}...
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="py-20 text-center space-y-3">
              <ShieldAlert className="w-12 h-12 text-slate-600 mx-auto" />
              <h4 className="text-sm font-semibold text-slate-300">
                Select a payment draft to inspect its risk profile
              </h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Guardian AI analyzes vendor legitimacy, invoice duplication, amount variance,
                and business policy limits in real time.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Small Badge Component
const RiskLevelBadge: React.FC<{ level: string; score: number }> = ({ level, score }) => {
  if (level === "CRITICAL") {
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-950 text-rose-400 border border-rose-800 flex items-center space-x-1">
        <ShieldX className="w-3 h-3" />
        <span>CRITICAL ({score})</span>
      </span>
    );
  }
  if (level === "HIGH") {
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-950 text-orange-400 border border-orange-800 flex items-center space-x-1">
        <AlertTriangle className="w-3 h-3" />
        <span>HIGH ({score})</span>
      </span>
    );
  }
  if (level === "MEDIUM") {
    return (
      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-950 text-amber-400 border border-amber-800 flex items-center space-x-1">
        <AlertTriangle className="w-3 h-3" />
        <span>MEDIUM ({score})</span>
      </span>
    );
  }
  return (
    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center space-x-1">
      <ShieldCheck className="w-3 h-3" />
      <span>LOW ({score})</span>
    </span>
  );
};

