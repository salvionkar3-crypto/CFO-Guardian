"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  CreditCard,
  PlusCircle,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Search,
  Eye,
  Edit2,
  ThumbsUp,
  ThumbsDown,
  Building2,
  Mail,
  DollarSign,
  Fingerprint,
  ExternalLink,
} from "lucide-react";
import {
  PaymentDraft,
  Vendor,
  PaymentTransactionItem,
  PaymentStatus,
  PaymentDraftCreatePayload,
  PayPalConfig,
} from "@/types";
import { api } from "@/lib/api";

interface PaymentCenterProps {
  onRefreshParent?: () => void;
  currency?: string;
}

export function PaymentCenter({ onRefreshParent, currency = "USD" }: PaymentCenterProps) {
  // Navigation tabs within Payment Center
  const [activeSubTab, setActiveSubTab] = useState<"drafts" | "create" | "history">("drafts");

  // Data states
  const [drafts, setDrafts] = useState<PaymentDraft[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransactionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Selected draft for review/approval/execution modal
  const [selectedDraft, setSelectedDraft] = useState<PaymentDraft | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [showRejectModal, setShowRejectModal] = useState<boolean>(false);
  const [rejectionReasonInput, setRejectionReasonInput] = useState<string>("");

  // Edit draft modal state
  const [isEditingDraft, setIsEditingDraft] = useState<boolean>(false);
  const [editAmount, setEditAmount] = useState<string>("");
  const [editPurpose, setEditPurpose] = useState<string>("");
  const [editInvoiceNumber, setEditInvoiceNumber] = useState<string>("");

  // Create Draft Form state
  const [isNewVendor, setIsNewVendor] = useState<boolean>(false);
  const [selectedVendorId, setSelectedVendorId] = useState<string>("");
  const [newVendorName, setNewVendorName] = useState<string>("");
  const [newVendorEmail, setNewVendorEmail] = useState<string>("");
  const [newVendorWebsite, setNewVendorWebsite] = useState<string>("");
  const [newVendorDisburseEmail, setNewVendorDisburseEmail] = useState<string>("");

  const [formTitle, setFormTitle] = useState<string>("");
  const [formAmount, setFormAmount] = useState<string>("");
  const [formCurrency, setFormCurrency] = useState<string>(currency);
  const [formCategory, setFormCategory] = useState<string>("Software & SaaS");
  const [formPurpose, setFormPurpose] = useState<string>("");
  const [formInvoiceNumber, setFormInvoiceNumber] = useState<string>("");
  const [formInvoiceUrl, setFormInvoiceUrl] = useState<string>("");
  const [formIdempotencyKey, setFormIdempotencyKey] = useState<string>(
    `KEY-${Math.random().toString(36).substring(2, 10).toUpperCase()}`
  );
  const [formAutoRiskScan, setFormAutoRiskScan] = useState<boolean>(true);
  const [formError, setFormError] = useState<string | null>(null);

  // Payment Execution settings in Modal
  const [execPaymentMethod, setExecPaymentMethod] = useState<"SIMULATED_PROVIDER" | "PAYPAL_SANDBOX">(
    "SIMULATED_PROVIDER"
  );
  const [approvalNotes, setApprovalNotes] = useState<string>("");

  // PayPal Sandbox specific state
  const [paypalConfig, setPayPalConfig] = useState<PayPalConfig | null>(null);
  const [showPayPalHelpModal, setShowPayPalHelpModal] = useState<boolean>(false);
  const [livePayPalOrderStatus, setLivePayPalOrderStatus] = useState<string | null>(null);
  const [activeApprovalUrl, setActiveApprovalUrl] = useState<string | null>(null);

  // Generate fresh idempotency key
  const regenerateKey = () => {
    setFormIdempotencyKey(`KEY-${Math.random().toString(36).substring(2, 10).toUpperCase()}`);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [draftsRes, vendorsRes, txRes, ppCfg] = await Promise.all([
        api.getPaymentDrafts().catch(() => []),
        api.getVendors().catch(() => []),
        api.getPaymentTransactions().catch(() => []),
        api.getPayPalConfig().catch(() => null),
      ]);
      setDrafts(draftsRes);
      setVendors(vendorsRes);
      setTransactions(txRes);
      if (ppCfg) setPayPalConfig(ppCfg);
    } catch (err) {
      console.error("Error loading payment center data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Synchronize modal draft when drafts update
  useEffect(() => {
    if (selectedDraft) {
      const updated = drafts.find((d) => d.id === selectedDraft.id);
      if (updated) setSelectedDraft(updated);
    }
  }, [drafts, selectedDraft]);

  // Auto-capture when buyer returns from PayPal Sandbox with ?token=...
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      setActionLoading(true);
      api
        .capturePayPalOrderById(token)
        .then(() => {
          setActionSuccess(`PayPal Sandbox Order ${token} captured and settled successfully!`);
          loadData();
          if (onRefreshParent) onRefreshParent();
          // Clear query params in address bar without full page reload
          window.history.replaceState({}, document.title, window.location.pathname);
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : "Capture failed.";
          setActionError(`PayPal capture notice: ${msg}`);
        })
        .finally(() => setActionLoading(false));
    }
  }, [loadData, onRefreshParent]);

  // Handle Draft Creation Submission
  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const parsedAmount = parseFloat(formAmount);
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setFormError("Please enter a valid positive payment amount.");
      return;
    }

    if (!formPurpose.trim()) {
      setFormError("Commercial purpose is mandatory for compliance and audit trail.");
      return;
    }

    if (!isNewVendor && !selectedVendorId) {
      setFormError("Please select a vendor or toggle 'Add New Vendor'.");
      return;
    }

    if (isNewVendor && (!newVendorName.trim() || !newVendorEmail.trim())) {
      setFormError("Vendor name and email are required to register a new payee.");
      return;
    }

    const payload: PaymentDraftCreatePayload = {
      title: formTitle.trim() || `Payment to ${isNewVendor ? newVendorName : "Vendor"}`,
      amount: parsedAmount,
      currency: formCurrency,
      category: formCategory,
      purpose: formPurpose.trim(),
      invoice_number: formInvoiceNumber.trim() || undefined,
      invoice_url: formInvoiceUrl.trim() || undefined,
      idempotency_key: formIdempotencyKey,
      auto_run_risk_scan: formAutoRiskScan,
    };

    if (isNewVendor) {
      payload.new_vendor = {
        name: newVendorName.trim(),
        email: newVendorEmail.trim(),
        website: newVendorWebsite.trim() || undefined,
        bank_or_paypal_email: newVendorDisburseEmail.trim() || undefined,
      };
    } else {
      payload.vendor_id = parseInt(selectedVendorId, 10);
    }

    setActionLoading(true);
    try {
      const created = await api.createPaymentDraft(payload);
      await loadData();
      if (onRefreshParent) onRefreshParent();

      // Reset form
      setFormTitle("");
      setFormAmount("");
      setFormPurpose("");
      setFormInvoiceNumber("");
      setFormInvoiceUrl("");
      setIsNewVendor(false);
      setSelectedVendorId("");
      setNewVendorName("");
      setNewVendorEmail("");
      regenerateKey();

      // Select created draft for immediate review
      setSelectedDraft(created);
      setActiveSubTab("drafts");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create payment draft.";
      setFormError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Re-run Guardian AI Risk Assessment
  const handleRunRiskScan = async (draftId: number) => {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const updated = await api.assessDraftRisk(draftId);
      setSelectedDraft(updated);
      await loadData();
      if (onRefreshParent) onRefreshParent();
      setActionSuccess("Guardian AI risk scan completed successfully.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to run risk scan.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Explicit User Approval
  const handleApproveDraft = async (draft: PaymentDraft) => {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const updated = await api.approvePaymentDraft(
        draft.id,
        approvalNotes || undefined,
        draft.details_hash || undefined
      );
      setSelectedDraft(updated);
      await loadData();
      if (onRefreshParent) onRefreshParent();
      setActionSuccess(`Payment Draft #${draft.id} approved for settlement!`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Approval failed.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Open Rejection Modal Prompt
  const handleRejectDraft = () => {
    setShowRejectModal(true);
    setRejectionReasonInput("");
  };

  // Confirm Rejection with Reason
  const handleConfirmReject = async (draftId: number) => {
    if (!rejectionReasonInput.trim()) {
      setActionError("Please provide an executive reason for rejecting this payment draft.");
      return;
    }
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const updated = await api.rejectPaymentDraft(draftId, rejectionReasonInput.trim());
      setSelectedDraft(updated);
      setShowRejectModal(false);
      setRejectionReasonInput("");
      await loadData();
      if (onRefreshParent) onRefreshParent();
      setActionSuccess(`Draft #${draftId} has been REJECTED. Reason recorded in audit trail.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Rejection failed.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Execute Approved Payment
  const handleExecutePayment = async (draftId: number) => {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await api.executePayment({
        draft_id: draftId,
        idempotency_key: `EXEC-${Math.random().toString(36).substring(2, 12).toUpperCase()}`,
        payment_method: execPaymentMethod,
      });
      await loadData();
      if (onRefreshParent) onRefreshParent();

      if (res.status === "COMPLETED") {
        setActionSuccess(
          `Payment successfully settled! Provider Ref: ${res.provider_reference}. Corporate balances decremented.`
        );
      } else if (res.status === "PROVIDER_PENDING") {
        if (res.approval_url) {
          setActiveApprovalUrl(res.approval_url);
          window.open(res.approval_url, "_blank");
          setActionSuccess(
            `PayPal Order ${res.provider_reference} created! PayPal checkout window opened. After approving in PayPal Sandbox, click "Capture Approved Order".`
          );
        } else {
          setActionSuccess(
            `PayPal Order ${res.provider_reference} dispatched in Sandbox. Complete buyer checkout to authorize.`
          );
        }
      } else {
        setActionSuccess(
          `Payment order dispatched (${res.payment_method}). Status: ${res.status}. Provider Ref: ${res.provider_reference}`
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Payment execution failed.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Capture Approved PayPal Order on Backend
  const handleCapturePayPal = async (orderId: string, transactionId?: number) => {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await api.capturePayPalOrderById(orderId, transactionId);
      await loadData();
      if (onRefreshParent) onRefreshParent();
      setActionSuccess(
        `PayPal capture confirmed! Transaction marked COMPLETED. Capture ID: ${
          (res as Record<string, string>).paypal_capture_id || orderId
        }`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "PayPal capture failed.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Query live status directly from PayPal REST API
  const handleCheckPayPalStatus = async (orderId: string) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const details = (await api.getPayPalOrderDetails(orderId)) as Record<string, unknown>;
      const status = (details.status as string) || "UNKNOWN";
      setLivePayPalOrderStatus(status);
      setActionSuccess(`PayPal live status: ${status}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to query PayPal order status.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Cancel PayPal order checkout session
  const handleCancelPayPal = async (transactionId: number) => {
    if (!window.confirm("Cancel this PayPal checkout session? Draft will be reset to APPROVED.")) return;
    setActionLoading(true);
    setActionError(null);
    try {
      await api.cancelPayPalOrder(transactionId);
      await loadData();
      if (onRefreshParent) onRefreshParent();
      setActionSuccess("PayPal checkout session cancelled. Draft returned to APPROVED state.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Cancel failed.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Save edits to draft (invalidates prior approval if modified)
  const handleSaveDraftEdits = async (draftId: number) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.updatePaymentDraft(draftId, {
        amount: editAmount ? parseFloat(editAmount) : undefined,
        purpose: editPurpose.trim() || undefined,
        invoice_number: editInvoiceNumber.trim() || undefined,
      });
      setSelectedDraft(updated);
      setIsEditingDraft(false);
      await loadData();
      if (onRefreshParent) onRefreshParent();
      setActionSuccess("Draft parameters updated. Prior approval invalidated for compliance.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update draft.";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  };

  // Filtered drafts list
  const filteredDrafts = drafts.filter((d) => {
    const matchesStatus = statusFilter === "ALL" || d.status === statusFilter;
    const matchesSearch =
      searchQuery === "" ||
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.vendor_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.purpose && d.purpose.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (d.invoice_number && d.invoice_number.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  // Color helper for 10 payment states
  const getStatusBadge = (status: PaymentStatus | string) => {
    switch (status) {
      case "APPROVED":
        return {
          bg: "bg-emerald-950/60 border-emerald-500/40 text-emerald-300",
          dot: "bg-emerald-400",
          label: "APPROVED (READY TO PAY)",
        };
      case "COMPLETED":
        return {
          bg: "bg-teal-950/60 border-teal-500/40 text-teal-300",
          dot: "bg-teal-400",
          label: "COMPLETED & SETTLED",
        };
      case "AWAITING_APPROVAL":
        return {
          bg: "bg-amber-950/60 border-amber-500/40 text-amber-300",
          dot: "bg-amber-400",
          label: "AWAITING APPROVAL",
        };
      case "RISK_REVIEWED":
        return {
          bg: "bg-cyan-950/60 border-cyan-500/40 text-cyan-300",
          dot: "bg-cyan-400",
          label: "RISK REVIEWED",
        };
      case "REVIEW_REQUIRED":
        return {
          bg: "bg-orange-950/60 border-orange-500/40 text-orange-300",
          dot: "bg-orange-400",
          label: "REVIEW REQUIRED",
        };
      case "PROVIDER_PENDING":
        return {
          bg: "bg-blue-950/60 border-blue-500/40 text-blue-300",
          dot: "bg-blue-400 animate-pulse",
          label: "PROVIDER PENDING",
        };
      case "REJECTED":
        return {
          bg: "bg-rose-950/60 border-rose-500/40 text-rose-300",
          dot: "bg-rose-400",
          label: "REJECTED",
        };
      case "FAILED":
        return {
          bg: "bg-red-950/60 border-red-500/40 text-red-400",
          dot: "bg-red-500",
          label: "FAILED",
        };
      case "EXPIRED":
        return {
          bg: "bg-slate-900 border-slate-700 text-slate-400",
          dot: "bg-slate-500",
          label: "EXPIRED",
        };
      case "DRAFT":
      default:
        return {
          bg: "bg-slate-900/80 border-slate-700/80 text-slate-300",
          dot: "bg-slate-400",
          label: "DRAFT",
        };
    }
  };

  // Metrics overview
  const totalSettledAmount = transactions
    .filter((t) => t.status === "COMPLETED")
    .reduce((sum, t) => sum + t.amount, 0);

  const awaitingApprovalCount = drafts.filter(
    (d) => d.status === "AWAITING_APPROVAL" || d.status === "REVIEW_REQUIRED" || d.status === "RISK_REVIEWED"
  ).length;

  const approvedReadyCount = drafts.filter((d) => d.status === "APPROVED").length;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Awaiting Sign-off</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">{awaitingApprovalCount}</div>
          <p className="text-xs text-slate-500 mt-1">Pending risk review or user authorization</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Approved for Payout</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{approvedReadyCount}</div>
          <p className="text-xs text-slate-500 mt-1">Clear for instant execution / clearing</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Settled Volume</span>
            <DollarSign className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300">
            ${totalSettledAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-500 mt-1">Total settled payout disbursements</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Registered Payees</span>
            <Building2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">{vendors.length}</div>
          <p className="text-xs text-slate-500 mt-1">Active multi-tenant supplier directory</p>
        </div>
      </div>

      {/* Main Payment Center Card */}
      <div className="bg-slate-900/95 border border-slate-800/90 rounded-2xl shadow-xl overflow-hidden backdrop-blur">
        {/* Navigation Bar */}
        <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 bg-slate-900/40">
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <CreditCard className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex flex-wrap items-center gap-2">
                <span>Secure Payment Management Center</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 border border-blue-500/20 text-blue-300">
                  Dual-Guardrail
                </span>
                <button
                  type="button"
                  onClick={() => setShowPayPalHelpModal(true)}
                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center space-x-1 transition ${
                    paypalConfig?.configured
                      ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/40"
                      : "bg-amber-950/60 border-amber-500/40 text-amber-300 hover:bg-amber-900/40"
                  }`}
                  title="Click to view PayPal Sandbox configuration guide"
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${paypalConfig?.configured ? "bg-emerald-400" : "bg-amber-400"}`} />
                  <span>PayPal {paypalConfig?.mode?.toUpperCase() || "SANDBOX"}: {paypalConfig?.configured ? "Connected" : "Setup Required"}</span>
                </button>
              </h2>
              <p className="text-xs text-slate-400">
                Deterministic risk verification, tamper-locked details_hash & idempotency control
              </p>
            </div>
          </div>

          {/* Sub-tab Switcher */}
          <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveSubTab("drafts")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === "drafts"
                  ? "bg-slate-800 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Payment Drafts ({drafts.length})
            </button>
            <button
              onClick={() => setActiveSubTab("create")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1 transition ${
                activeSubTab === "create"
                  ? "bg-blue-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Create Draft</span>
            </button>
            <button
              onClick={() => setActiveSubTab("history")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeSubTab === "history"
                  ? "bg-slate-800 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Settlement History ({transactions.length})
            </button>
          </div>
        </div>

        {/* SUB-TAB 1: DRAFTS LIST & APPROVAL REGISTER */}
        {activeSubTab === "drafts" && (
          <div className="p-6 space-y-4">
            {/* Filter and Search Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search payee, invoice or purpose..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Status Filter Buttons */}
              <div className="flex items-center space-x-1.5 overflow-x-auto w-full sm:w-auto text-xs pb-1 sm:pb-0">
                {[
                  "ALL",
                  "DRAFT",
                  "RISK_REVIEWED",
                  "AWAITING_APPROVAL",
                  "APPROVED",
                  "PROVIDER_PENDING",
                  "COMPLETED",
                  "REJECTED",
                ].map((st) => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap transition ${
                      statusFilter === st
                        ? "bg-slate-800 text-blue-400 border border-slate-700 shadow"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {st.replace("_", " ")}
                  </button>
                ))}

                <button
                  onClick={loadData}
                  disabled={loading}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
                  title="Reload drafts"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                </button>
              </div>
            </div>

            {/* Drafts Table / Card Grid */}
            {loading ? (
              <div className="py-16 text-center text-slate-500 text-sm flex flex-col items-center justify-center space-y-2">
                <RefreshCw className="w-5 h-5 animate-spin text-blue-500" />
                <span>Loading secure payment drafts...</span>
              </div>
            ) : filteredDrafts.length === 0 ? (
              <div className="py-16 text-center text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
                No payment drafts found matching current filters.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800/80 text-slate-400 font-semibold bg-slate-950/40">
                      <th className="py-3 px-4">Payee & Purpose</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Guardian Risk</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Invoice / Fingerprint</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {filteredDrafts.map((draft) => {
                      const badge = getStatusBadge(draft.status);
                      const riskScore = draft.risk_assessment?.risk_score;

                      return (
                        <tr
                          key={draft.id}
                          className="hover:bg-slate-800/30 transition group cursor-pointer"
                          onClick={() => setSelectedDraft(draft)}
                        >
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-slate-200 flex items-center space-x-1.5">
                              <span>{draft.vendor_name}</span>
                              {draft.risk_assessment?.vendor_verified && (
                                <span title="Verified Payee Domain">
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                                </span>
                              )}
                            </div>
                            <div className="text-slate-400 text-[11px] truncate max-w-xs">{draft.purpose || draft.title}</div>
                          </td>

                          <td className="py-3.5 px-4 font-mono font-medium text-slate-100">
                            {draft.currency} {draft.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>

                          <td className="py-3.5 px-4">
                            {riskScore !== undefined ? (
                              <div className="flex items-center space-x-1.5">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    riskScore <= 24
                                      ? "bg-emerald-950/60 text-emerald-300 border border-emerald-500/40"
                                      : riskScore <= 49
                                      ? "bg-amber-950/60 text-amber-300 border border-amber-500/40"
                                      : "bg-rose-950/60 text-rose-300 border border-rose-500/40"
                                  }`}
                                >
                                  {riskScore.toFixed(0)}/100
                                </span>
                                <span className="text-[10px] text-slate-400 uppercase font-semibold">
                                  {draft.risk_assessment?.risk_level}
                                </span>
                              </div>
                            ) : (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRunRiskScan(draft.id);
                                }}
                                className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                              >
                                <ShieldAlert className="w-3 h-3" />
                                <span>Run Scan</span>
                              </button>
                            )}
                          </td>

                          <td className="py-3.5 px-4">
                            <span
                              className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badge.bg}`}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                              <span>{badge.label}</span>
                            </span>
                          </td>

                          <td className="py-3.5 px-4">
                            <div className="text-[11px] font-mono text-slate-400">
                              {draft.invoice_number || "No Inv Ref"}
                            </div>
                            <div className="text-[10px] font-mono text-slate-500 flex items-center space-x-1">
                              <Fingerprint className="w-3 h-3 text-slate-600" />
                              <span>{draft.details_hash ? draft.details_hash.substring(0, 10) + "..." : "Unhashed"}</span>
                            </div>
                          </td>

                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedDraft(draft);
                              }}
                              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center space-x-1 ml-auto"
                            >
                              <Eye className="w-3.5 h-3.5 text-blue-400" />
                              <span>Inspect</span>
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* SUB-TAB 2: CREATE PAYMENT DRAFT */}
        {activeSubTab === "create" && (
          <div className="p-6 max-w-3xl mx-auto space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-1.5">
                  <PlusCircle className="w-4 h-4 text-blue-400" />
                  <span>Draft a New Payment Request</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Every disbursement undergoes server-side validation and automated Guardian risk scoring
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-[11px] text-slate-400">Add New Payee?</span>
                <button
                  type="button"
                  onClick={() => setIsNewVendor(!isNewVendor)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition ${
                    isNewVendor ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-300"
                  }`}
                >
                  {isNewVendor ? "Inline Payee On" : "Select Existing"}
                </button>
              </div>
            </div>

            {formError && (
              <div className="p-3 bg-rose-950/80 border border-rose-500/50 rounded-xl text-rose-300 text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateDraft} className="space-y-4">
              {/* Payee Selection or Inline Payee Form */}
              {!isNewVendor ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Select Payee / Vendor *
                  </label>
                  <select
                    value={selectedVendorId}
                    onChange={(e) => setSelectedVendorId(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="">-- Choose Registered Vendor --</option>
                    {vendors.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} ({v.email}) — Trust: {v.trust_score}/100
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="p-4 bg-slate-950/60 border border-blue-500/20 rounded-xl space-y-3">
                  <div className="text-xs font-semibold text-blue-400 flex items-center space-x-1.5">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>Inline Payee Onboarding</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Company / Payee Name *</label>
                      <input
                        type="text"
                        placeholder="e.g. Datadog Inc"
                        value={newVendorName}
                        onChange={(e) => setNewVendorName(e.target.value)}
                        required
                        className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Billing Email *</label>
                      <input
                        type="email"
                        placeholder="billing@datadog.com"
                        value={newVendorEmail}
                        onChange={(e) => setNewVendorEmail(e.target.value)}
                        required
                        className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Website URL</label>
                      <input
                        type="url"
                        placeholder="https://datadog.com"
                        value={newVendorWebsite}
                        onChange={(e) => setNewVendorWebsite(e.target.value)}
                        className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">
                        Disbursement PayPal / Bank Coordinate
                      </label>
                      <input
                        type="email"
                        placeholder="pay@datadog.com"
                        value={newVendorDisburseEmail}
                        onChange={(e) => setNewVendorDisburseEmail(e.target.value)}
                        className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Title & Category */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Payment Title *</label>
                  <input
                    type="text"
                    placeholder="e.g. November Cloud Infrastructure Settlement"
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Expense Category *</label>
                  <select
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="Software & SaaS">Software & SaaS</option>
                    <option value="Infrastructure">Infrastructure</option>
                    <option value="Marketing & Growth">Marketing & Growth</option>
                    <option value="Legal & Professional">Legal & Professional</option>
                    <option value="Office & Facilities">Office & Facilities</option>
                    <option value="General">General Operating</option>
                  </select>
                </div>
              </div>

              {/* Amount & Currency */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Disbursement Amount *</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 font-mono">$</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder="0.00"
                      value={formAmount}
                      onChange={(e) => setFormAmount(e.target.value)}
                      required
                      className="w-full pl-8 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Currency *</label>
                  <select
                    value={formCurrency}
                    onChange={(e) => setFormCurrency(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
                  >
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                    <option value="INR">INR (₹)</option>
                    <option value="CAD">CAD ($)</option>
                    <option value="AUD">AUD ($)</option>
                  </select>
                </div>
              </div>

              {/* Commercial Purpose (Mandatory for Governance) */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Commercial Purpose & Justification *
                </label>
                <textarea
                  rows={2}
                  placeholder="Explain why this payment is required (e.g. Monthly server capacity billing per Q4 contractual schedule)..."
                  value={formPurpose}
                  onChange={(e) => setFormPurpose(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Invoice Number & Invoice URL */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Invoice Number (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. INV-2026-9042"
                    value={formInvoiceNumber}
                    onChange={(e) => setFormInvoiceNumber(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Invoice Link / Document URL</label>
                  <input
                    type="url"
                    placeholder="https://vendor.com/invoice/9042.pdf"
                    value={formInvoiceUrl}
                    onChange={(e) => setFormInvoiceUrl(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Idempotency & Guardian Checkbox */}
              <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center space-x-2">
                  <Fingerprint className="w-4 h-4 text-cyan-400" />
                  <div>
                    <span className="font-mono text-slate-300">{formIdempotencyKey}</span>
                    <span className="text-[10px] text-slate-500 block">Client Idempotency Key</span>
                  </div>
                  <button
                    type="button"
                    onClick={regenerateKey}
                    className="p-1 text-slate-400 hover:text-white"
                    title="Generate new idempotency key"
                  >
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </div>

                <label className="flex items-center space-x-2 cursor-pointer text-slate-300 font-medium">
                  <input
                    type="checkbox"
                    checked={formAutoRiskScan}
                    onChange={(e) => setFormAutoRiskScan(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                  />
                  <span>Run Guardian AI Risk Scan automatically</span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={actionLoading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold text-xs shadow-lg shadow-blue-600/20 flex items-center justify-center space-x-2 transition"
              >
                {actionLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Processing & Running Guardian Scan...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Create & Commit Payment Draft</span>
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* SUB-TAB 3: SETTLEMENT & TRANSACTION HISTORY */}
        {activeSubTab === "history" && (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <span>Settled Payouts & Transaction Ledger</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] bg-teal-500/10 border border-teal-500/20 text-teal-300 font-mono">
                    Provider Confirmed
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Confirmed clearing events that have decremented the business treasury balance
                </p>
              </div>

              <button
                onClick={loadData}
                disabled={loading}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center space-x-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
                <span>Refresh Ledger</span>
              </button>
            </div>

            {transactions.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs border border-dashed border-slate-800 rounded-xl">
                No settled transactions recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/40">
                      <th className="py-2.5 px-4">Tx ID & Ref</th>
                      <th className="py-2.5 px-4">Category / Description</th>
                      <th className="py-2.5 px-4">Amount</th>
                      <th className="py-2.5 px-4">Payment Method</th>
                      <th className="py-2.5 px-4">Status</th>
                      <th className="py-2.5 px-4 text-right">Settled At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40 font-mono">
                    {transactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-slate-800/20 transition">
                        <td className="py-3 px-4 font-sans">
                          <div className="font-semibold text-slate-200">Tx #{tx.id}</div>
                          <div className="text-[10px] text-slate-400 font-mono">
                            {tx.paypal_order_id || tx.idempotency_key || "N/A"}
                          </div>
                        </td>

                        <td className="py-3 px-4 font-sans">
                          <div className="text-slate-300">{tx.category}</div>
                          <div className="text-[11px] text-slate-500 truncate max-w-xs">{tx.description || "—"}</div>
                        </td>

                        <td className="py-3 px-4 text-emerald-400 font-bold">
                          {tx.currency} {tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>

                        <td className="py-3 px-4 font-sans">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 border border-slate-700 text-slate-300">
                            {tx.payment_method}
                          </span>
                        </td>

                        <td className="py-3 px-4 font-sans">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              tx.status === "COMPLETED"
                                ? "bg-teal-950 text-teal-300 border border-teal-500/30"
                                : "bg-blue-950 text-blue-300 border border-blue-500/30"
                            }`}
                          >
                            {tx.status}
                          </span>
                        </td>

                        <td className="py-3 px-4 text-right text-slate-400 text-[11px] font-sans">
                          {tx.settled_at
                            ? new Date(tx.settled_at).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : new Date(tx.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* INSPECT, APPROVE & EXECUTE MODAL DRAWER */}
      {selectedDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl p-6 space-y-5 text-slate-200">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono text-slate-400">Draft #{selectedDraft.id}</span>
                  {(() => {
                    const b = getStatusBadge(selectedDraft.status);
                    return (
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${b.bg}`}>
                        {b.label}
                      </span>
                    );
                  })()}
                </div>
                <h3 className="text-lg font-bold text-white mt-1">{selectedDraft.title}</h3>
                <p className="text-xs text-slate-400 flex items-center space-x-1.5 mt-0.5">
                  <Building2 className="w-3.5 h-3.5 text-blue-400" />
                  <span>{selectedDraft.vendor_name}</span>
                  <span className="text-slate-600">•</span>
                  <Mail className="w-3.5 h-3.5 text-slate-500" />
                  <span>{selectedDraft.vendor_email}</span>
                </p>
              </div>

              <button
                onClick={() => {
                  setSelectedDraft(null);
                  setIsEditingDraft(false);
                  setActionError(null);
                  setActionSuccess(null);
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            {/* Notification Banners */}
            {actionError && (
              <div className="p-3 bg-rose-950/80 border border-rose-500/50 rounded-xl text-rose-300 text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{actionError}</span>
              </div>
            )}
            {actionSuccess && (
              <div className="p-3 bg-emerald-950/80 border border-emerald-500/50 rounded-xl text-emerald-300 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>{actionSuccess}</span>
              </div>
            )}

            {/* Payment Details Card */}
            {!isEditingDraft ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-4 rounded-xl border border-slate-800/80 text-xs">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Amount</span>
                  <span className="text-base font-bold font-mono text-emerald-400">
                    {selectedDraft.currency} {selectedDraft.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Category</span>
                  <span className="text-slate-200 font-medium">{selectedDraft.category}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Budget Impact</span>
                  <span className="text-slate-200 font-medium">{selectedDraft.budget_impact_pct}% monthly</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">Runway Impact</span>
                  <span className="text-slate-200 font-medium">~{selectedDraft.runway_impact_days} days</span>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-slate-950 rounded-xl border border-amber-500/30 space-y-3">
                <div className="text-xs font-bold text-amber-400 flex items-center space-x-1.5">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Modifying Draft Parameters will Invalidate Prior Approvals</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 text-[11px] mb-1">New Amount ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={editAmount}
                      onChange={(e) => setEditAmount(e.target.value)}
                      className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 text-[11px] mb-1">Invoice Number</label>
                    <input
                      type="text"
                      value={editInvoiceNumber}
                      onChange={(e) => setEditInvoiceNumber(e.target.value)}
                      className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-slate-400 text-[11px] mb-1">Commercial Purpose</label>
                  <input
                    type="text"
                    value={editPurpose}
                    onChange={(e) => setEditPurpose(e.target.value)}
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white"
                  />
                </div>
                <div className="flex items-center space-x-2 pt-1">
                  <button
                    onClick={() => handleSaveDraftEdits(selectedDraft.id)}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs"
                  >
                    Save & Invalidate Prior Approval
                  </button>
                  <button
                    onClick={() => setIsEditingDraft(false)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Purpose & Commercial Rationale */}
            <div className="space-y-1">
              <span className="text-xs font-semibold text-slate-400">Commercial Purpose:</span>
              <p className="text-xs text-slate-200 bg-slate-950 p-3 rounded-xl border border-slate-800/80 leading-relaxed">
                {selectedDraft.purpose || "No explicit commercial purpose provided."}
              </p>
            </div>

            {/* Cryptographic SHA-256 Fingerprint */}
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-[11px]">
              <div className="flex items-center space-x-2 font-mono text-slate-400">
                <Fingerprint className="w-4 h-4 text-cyan-400" />
                <span className="text-slate-500">SHA-256 Fingerprint:</span>
                <span className="text-cyan-300 font-bold">{selectedDraft.details_hash || "Not Locked"}</span>
              </div>
              {selectedDraft.status !== "COMPLETED" && !isEditingDraft && (
                <button
                  onClick={() => {
                    setEditAmount(selectedDraft.amount.toString());
                    setEditPurpose(selectedDraft.purpose || "");
                    setEditInvoiceNumber(selectedDraft.invoice_number || "");
                    setIsEditingDraft(true);
                  }}
                  className="text-xs text-slate-400 hover:text-white flex items-center space-x-1"
                >
                  <Edit2 className="w-3 h-3" />
                  <span>Edit Draft</span>
                </button>
              )}
            </div>

            {/* Guardian AI Risk Assessment Section */}
            <div className="border border-slate-800 rounded-xl p-4 bg-slate-950/60 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Guardian AI Security Analysis
                  </span>
                </div>
                {selectedDraft.risk_assessment && (
                  <button
                    onClick={() => handleRunRiskScan(selectedDraft.id)}
                    disabled={actionLoading || selectedDraft.status === "COMPLETED"}
                    className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center space-x-1 font-semibold"
                  >
                    <RefreshCw className={`w-3 h-3 ${actionLoading ? "animate-spin" : ""}`} />
                    <span>Re-evaluate Risk</span>
                  </button>
                )}
              </div>

              {selectedDraft.risk_assessment ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-slate-900 rounded-xl border border-slate-800">
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Risk Score</span>
                      <span className="text-xl font-bold font-mono text-white">
                        {selectedDraft.risk_assessment.risk_score}/100
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Policy Level</span>
                      <span className="text-xs font-bold text-slate-200">
                        {selectedDraft.risk_assessment.risk_level}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Verdict</span>
                      <span className="text-xs font-bold font-mono text-cyan-300">
                        {selectedDraft.risk_assessment.verdict}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block uppercase font-semibold">Recommended Action</span>
                      <span className="text-xs font-bold text-slate-200">
                        {selectedDraft.risk_assessment.recommended_action}
                      </span>
                    </div>
                  </div>

                  {selectedDraft.risk_assessment.plain_explanation && (
                    <div className="text-xs text-slate-300 bg-slate-900/60 p-3 rounded-lg border border-slate-800 leading-relaxed">
                      {selectedDraft.risk_assessment.plain_explanation}
                    </div>
                  )}

                  {selectedDraft.risk_assessment.risk_signals && selectedDraft.risk_assessment.risk_signals.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-400">Detected Risk Signals:</span>
                      <div className="space-y-1">
                        {selectedDraft.risk_assessment.risk_signals.map((sig, idx) => (
                          <div
                            key={idx}
                            className="p-2 rounded-lg bg-rose-950/20 border border-rose-500/20 text-xs flex items-start space-x-2"
                          >
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-rose-900 text-rose-200 font-bold">
                              +{sig.score_impact}
                            </span>
                            <div>
                              <span className="font-semibold text-rose-300">{sig.name}:</span>{" "}
                              <span className="text-slate-300">{sig.evidence}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <p className="text-xs text-slate-400 mb-3">No risk evaluation recorded for this draft yet.</p>
                  <button
                    onClick={() => handleRunRiskScan(selectedDraft.id)}
                    disabled={actionLoading}
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs inline-flex items-center space-x-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Run Guardian 10-Signal Risk Scan</span>
                  </button>
                </div>
              )}
            </div>

            {/* ACTION SECTION: APPROVE OR EXECUTE */}
            <div className="border-t border-slate-800 pt-4 space-y-3">
              {/* If draft is REJECTED or BLOCKED */}
              {selectedDraft.status === "REJECTED" && (
                <div className="p-3 bg-rose-950/60 border border-rose-500/40 rounded-xl text-rose-300 text-xs space-y-1">
                  <div className="flex items-center space-x-2 font-bold">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>Payment Proposal REJECTED</span>
                  </div>
                  {selectedDraft.rejection_reason && (
                    <p className="text-[11px] text-rose-200/90 pl-6">
                      <strong className="text-rose-400">Executive Reason:</strong> {selectedDraft.rejection_reason}
                    </p>
                  )}
                  <p className="text-[10px] text-slate-400 pl-6">
                    Approval and settlement execution are strictly blocked under governance rules.
                  </p>
                </div>
              )}

              {/* Stale / Expired Approval Banner */}
              {selectedDraft.status === "EXPIRED" && (
                <div className="p-3 bg-amber-950/60 border border-amber-500/40 rounded-xl text-amber-300 text-xs space-y-2">
                  <div className="flex items-center space-x-2 font-bold">
                    <Clock className="w-4 h-4 text-amber-400 flex-shrink-0" />
                    <span>Approval Validity Window Expired</span>
                  </div>
                  <p className="text-[11px] text-amber-200/90 leading-relaxed">
                    Corporate governance mandates that approvals are valid for 24 hours. Because the execution window elapsed, prior authorization was automatically revoked to prevent stale fund disbursement.
                  </p>
                  <button
                    onClick={() => handleRunRiskScan(selectedDraft.id)}
                    disabled={actionLoading}
                    className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs inline-flex items-center space-x-1.5 transition"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Re-scan Risk & Re-evaluate Draft</span>
                  </button>
                </div>
              )}

              {/* Critical Risk Mandatory Block */}
              {selectedDraft.policy_eligibility?.mandatory_block && selectedDraft.status !== "REJECTED" && (
                <div className="p-3 bg-rose-950/70 border border-rose-500/50 rounded-xl text-rose-200 text-xs space-y-1.5">
                  <div className="flex items-center space-x-2 font-bold text-rose-300">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                    <span>MANDATORY GOVERNANCE BLOCK ENFORCED</span>
                  </div>
                  <p className="text-[11px] text-rose-200/90 leading-relaxed">
                    {selectedDraft.policy_eligibility.reason}
                  </p>
                  <p className="text-[10px] text-rose-400 font-semibold">
                    Policy Invariant: Critical-risk fraud and policy blocks cannot be overridden by user or AI chat instructions.
                  </p>
                </div>
              )}

              {/* If draft is in REVIEW_REQUIRED */}
              {selectedDraft.status === "REVIEW_REQUIRED" && (
                <div className="p-3 bg-orange-950/60 border border-orange-500/40 rounded-xl text-orange-300 text-xs flex items-center space-x-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  <span>
                    Parameters were altered or flagged. Re-review details thoroughly before approving.
                  </span>
                </div>
              )}

              {/* Dual-Control Governance Progress Tracker */}
              {selectedDraft.requires_dual_approval && (
                <div className="p-3 bg-slate-900/80 border border-cyan-500/30 rounded-xl space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-cyan-300 flex items-center space-x-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Dual-Control Governance (Four-Eyes Principle)</span>
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                      {selectedDraft.secondary_approved_at ? "Step 2 of 2 (Fully Approved)" : selectedDraft.approved_at ? "Step 2 of 2 (Pending Second Signer)" : "Step 1 of 2 (Pending Primary Signer)"}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className={`p-2.5 rounded-lg border ${
                      selectedDraft.approved_at ? "bg-emerald-950/30 border-emerald-500/30 text-emerald-300" : "bg-slate-950 border-slate-800 text-slate-400"
                    }`}>
                      <span className="text-[10px] block font-semibold text-slate-400">1. Primary Executive Sign-off</span>
                      <span className="font-semibold text-white block mt-0.5">
                        {selectedDraft.approved_by_name || (selectedDraft.approved_at ? "Authorized" : "Pending Sign-off")}
                      </span>
                      {selectedDraft.approved_at && (
                        <span className="text-[9px] text-slate-500 font-mono block">
                          {new Date(selectedDraft.approved_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>

                    <div className={`p-2.5 rounded-lg border ${
                      selectedDraft.secondary_approved_at ? "bg-emerald-950/30 border-emerald-500/30 text-emerald-300" : "bg-slate-950 border-slate-800 text-slate-400"
                    }`}>
                      <span className="text-[10px] block font-semibold text-slate-400">2. Secondary Executive Sign-off</span>
                      <span className="font-semibold text-white block mt-0.5">
                        {selectedDraft.secondary_approved_by_name || (selectedDraft.secondary_approved_at ? "Authorized" : "Pending Sign-off")}
                      </span>
                      {selectedDraft.secondary_approved_at && (
                        <span className="text-[9px] text-slate-500 font-mono block">
                          {new Date(selectedDraft.secondary_approved_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* If draft is NOT yet fully APPROVED */}
              {selectedDraft.status !== "APPROVED" &&
                selectedDraft.status !== "COMPLETED" &&
                selectedDraft.status !== "PROVIDER_PENDING" &&
                selectedDraft.status !== "REJECTED" &&
                selectedDraft.status !== "EXPIRED" &&
                !selectedDraft.policy_eligibility?.mandatory_block && (
                  <div className="space-y-3 pt-1">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1">
                        Executive Approval Notes / Auditor Justification
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Cleared by Controller after verifying purchase order & tax invoice"
                        value={approvalNotes}
                        onChange={(e) => setApprovalNotes(e.target.value)}
                        className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                      />
                    </div>

                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => handleApproveDraft(selectedDraft)}
                        disabled={actionLoading}
                        className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/20 flex items-center justify-center space-x-1.5 transition disabled:opacity-50"
                      >
                        <ThumbsUp className="w-4 h-4" />
                        <span>
                          {selectedDraft.requires_dual_approval && selectedDraft.approved_at && !selectedDraft.secondary_approved_at
                            ? "Grant Secondary Dual-Control Sign-off (Step 2 of 2)"
                            : selectedDraft.requires_dual_approval
                            ? "Grant Primary Authorization (Step 1 of 2)"
                            : "Explicitly Approve Payment Draft"}
                        </span>
                      </button>

                      <button
                        onClick={() => handleRejectDraft()}
                        disabled={actionLoading}
                        className="px-4 py-2.5 rounded-xl bg-rose-950 hover:bg-rose-900 border border-rose-800 text-rose-300 font-semibold text-xs flex items-center space-x-1.5 transition"
                      >
                        <ThumbsDown className="w-4 h-4" />
                        <span>Reject</span>
                      </button>
                    </div>
                  </div>
                )}

              {/* Immutable Authorization History */}
              {selectedDraft.approvals && selectedDraft.approvals.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Authorization & Audit History ({selectedDraft.approvals.length})
                  </span>
                  <div className="space-y-1.5">
                    {selectedDraft.approvals.map((ap) => (
                      <div
                        key={ap.id}
                        className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800/80 text-xs flex items-start justify-between"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center space-x-2">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                ap.status === "APPROVED"
                                  ? "bg-emerald-950 text-emerald-300 border border-emerald-500/30"
                                  : "bg-rose-950 text-rose-300 border border-rose-500/30"
                              }`}
                            >
                              {ap.approval_role.replace("_", " ")}
                            </span>
                            <span className="font-semibold text-white">
                              {ap.approved_by_name || `User #${ap.approved_by_id}`}
                            </span>
                          </div>
                          {ap.notes && (
                            <p className="text-slate-400 text-[11px] italic">&ldquo;{ap.notes}&rdquo;</p>
                          )}
                          {ap.details_hash && (
                            <p className="text-[10px] text-slate-500 font-mono">
                              Fingerprint: {ap.details_hash.substring(0, 16)}...
                            </p>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap">
                          {new Date(ap.approved_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* If draft is APPROVED -> Ready for Execution */}
              {selectedDraft.status === "APPROVED" && (
                <div className="p-4 bg-emerald-950/30 border border-emerald-500/30 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-emerald-400">
                      <CheckCircle2 className="w-5 h-5" />
                      <span className="text-xs font-bold uppercase tracking-wider">
                        Approved for Settlement & Clearing
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Approved At: {selectedDraft.approved_at ? new Date(selectedDraft.approved_at).toLocaleTimeString() : "N/A"}
                    </span>
                  </div>

                  {/* Execution Provider Selection */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <label
                      className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-2 ${
                        execPaymentMethod === "SIMULATED_PROVIDER"
                          ? "bg-slate-900 border-blue-500 text-white"
                          : "bg-slate-950 border-slate-800 text-slate-400"
                      }`}
                    >
                      <input
                        type="radio"
                        name="method"
                        checked={execPaymentMethod === "SIMULATED_PROVIDER"}
                        onChange={() => setExecPaymentMethod("SIMULATED_PROVIDER")}
                        className="mt-0.5 text-blue-600"
                      />
                      <div>
                        <span className="font-bold block">Simulated Clearing Provider</span>
                        <span className="text-[10px] text-slate-500">
                          Instant deterministic test clearing with verified balance debits.
                        </span>
                      </div>
                    </label>

                    <label
                      className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-2 ${
                        execPaymentMethod === "PAYPAL_SANDBOX"
                          ? "bg-slate-900 border-blue-500 text-white"
                          : "bg-slate-950 border-slate-800 text-slate-400"
                      }`}
                    >
                      <input
                        type="radio"
                        name="method"
                        checked={execPaymentMethod === "PAYPAL_SANDBOX"}
                        onChange={() => setExecPaymentMethod("PAYPAL_SANDBOX")}
                        className="mt-0.5 text-blue-600"
                      />
                      <div>
                        <div className="flex items-center space-x-1.5">
                          <span className="font-bold">PayPal Sandbox REST API</span>
                          {paypalConfig?.configured ? (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-emerald-950 text-emerald-300 border border-emerald-500/30">
                              Configured
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-amber-950 text-amber-300 border border-amber-500/30">
                              Unconfigured
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-500">
                          Live PayPal checkout order dispatch in sandbox testing mode.
                        </span>
                      </div>
                    </label>
                  </div>

                  {execPaymentMethod === "PAYPAL_SANDBOX" && !paypalConfig?.configured && (
                    <div className="p-3 bg-amber-950/60 border border-amber-500/40 rounded-xl text-amber-300 text-xs space-y-1.5">
                      <div className="flex items-center space-x-1.5 font-bold">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        <span>PayPal Sandbox Credentials Not Configured</span>
                      </div>
                      <p className="text-[11px] text-amber-200/90 leading-relaxed">
                        To execute live sandbox checkout orders, specify <code className="bg-slate-900 px-1 py-0.5 rounded text-amber-100 font-mono">PAYPAL_CLIENT_ID</code> and <code className="bg-slate-900 px-1 py-0.5 rounded text-amber-100 font-mono">PAYPAL_CLIENT_SECRET</code> in <code className="bg-slate-900 px-1 py-0.5 rounded text-amber-100 font-mono">backend/.env</code>.
                      </p>
                      <button
                        type="button"
                        onClick={() => setShowPayPalHelpModal(true)}
                        className="text-[11px] text-cyan-400 hover:text-cyan-300 underline font-semibold block"
                      >
                        Open PayPal Sandbox Setup Guide →
                      </button>
                    </div>
                  )}

                  {/* Execute Button */}
                  <button
                    onClick={() => handleExecutePayment(selectedDraft.id)}
                    disabled={actionLoading}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs shadow-xl shadow-emerald-600/30 flex items-center justify-center space-x-2 transition"
                  >
                    {actionLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        <span>Dispatching to Payment Provider...</span>
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4" />
                        <span>
                          Execute Payment of {selectedDraft.currency} {selectedDraft.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* If draft is PROVIDER_PENDING */}
              {selectedDraft.status === "PROVIDER_PENDING" && (() => {
                const matchedTx = transactions.find((t) => t.payment_draft_id === selectedDraft.id);
                const isPayPal = matchedTx?.payment_method === "PAYPAL_SANDBOX" || !!matchedTx?.paypal_order_id;
                const paypalOrderId = matchedTx?.paypal_order_id;

                return (
                  <div className="p-4 bg-blue-950/40 border border-blue-500/40 rounded-xl space-y-3 text-xs">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-blue-300">
                      <div className="flex items-center space-x-2">
                        <RefreshCw className="w-4 h-4 animate-spin text-blue-400" />
                        <span className="font-bold">
                          {isPayPal ? "PayPal Sandbox Order Created — Awaiting Buyer Authorization" : "Payment Dispatched to Provider"}
                        </span>
                      </div>
                      {paypalOrderId && (
                        <span className="font-mono text-[10px] text-blue-300 bg-blue-900/60 px-2 py-0.5 rounded border border-blue-500/30">
                          Order ID: {paypalOrderId}
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {isPayPal
                        ? "This order has been created via PayPal Orders v2. The buyer authorizes payment in PayPal Sandbox. After approval, click 'Capture Approved Order' to settle funds and update company treasury balances."
                        : "Awaiting provider settlement confirmation. Treasury ledger balances will be decremented upon verified settlement."}
                    </p>

                    {livePayPalOrderStatus && (
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] flex items-center justify-between">
                        <span className="text-slate-400">Live PayPal REST API Status:</span>
                        <span className="font-mono font-bold text-cyan-300">{livePayPalOrderStatus}</span>
                      </div>
                    )}

                    {isPayPal && paypalOrderId && (
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        {activeApprovalUrl && (
                          <button
                            type="button"
                            onClick={() => window.open(activeApprovalUrl, "_blank")}
                            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center space-x-1.5 transition"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>Re-open PayPal Sandbox Window</span>
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => handleCheckPayPalStatus(paypalOrderId)}
                          disabled={actionLoading}
                          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center space-x-1 transition"
                        >
                          <RefreshCw className={`w-3 h-3 ${actionLoading ? "animate-spin" : ""}`} />
                          <span>Check Live Status</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleCapturePayPal(paypalOrderId, matchedTx?.id)}
                          disabled={actionLoading}
                          className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/30 flex items-center space-x-1.5 transition"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Capture Approved Order</span>
                        </button>

                        {matchedTx && (
                          <button
                            type="button"
                            onClick={() => handleCancelPayPal(matchedTx.id)}
                            disabled={actionLoading}
                            className="px-2.5 py-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900/80 border border-rose-800 text-rose-300 text-xs ml-auto transition"
                          >
                            Cancel Order
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* If draft is COMPLETED */}
              {selectedDraft.status === "COMPLETED" && (
                <div className="p-4 bg-teal-950/40 border border-teal-500/40 rounded-xl text-teal-300 text-xs flex items-center space-x-3">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-teal-400" />
                  <div>
                    <span className="font-bold block">Payment Fully Settled & Confirmed</span>
                    <span className="text-[11px] text-slate-400">
                      Corporate treasury ledger updated. Transaction recorded in historical payment ledger.
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* REJECTION REASON PROMPT MODAL */}
      {showRejectModal && selectedDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-rose-500/40 rounded-2xl w-full max-w-md shadow-2xl p-6 space-y-4 text-slate-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-rose-400 font-bold text-sm">
                <ThumbsDown className="w-4 h-4 text-rose-400" />
                <span>Reject Payment Draft #{selectedDraft.id}</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectionReasonInput("");
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <p className="text-xs text-slate-300 leading-relaxed">
                Rejecting this disbursement will immediately halt clearing and record an immutable rejection event in the corporate audit trail.
              </p>
              <label className="block text-xs font-bold text-rose-300">
                Executive Rejection Reason *
              </label>
              <textarea
                rows={3}
                placeholder="State the formal governance reason (e.g., Unrecognized supplier charges, budget allocation ceiling reached, duplicate invoice flagged)..."
                value={rejectionReasonInput}
                onChange={(e) => setRejectionReasonInput(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 focus:border-rose-500 rounded-xl text-xs text-white placeholder-slate-600 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectionReasonInput("");
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleConfirmReject(selectedDraft.id)}
                disabled={actionLoading || !rejectionReasonInput.trim()}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/30 flex items-center space-x-1.5 transition disabled:opacity-50"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                <span>Confirm & Reject Proposal</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PAYPAL SANDBOX SETUP GUIDE MODAL */}
      {showPayPalHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl p-6 space-y-4 text-slate-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <CreditCard className="w-5 h-5 text-blue-400" />
                <h3 className="text-base font-bold text-white">PayPal Sandbox Setup Guide</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowPayPalHelpModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs leading-relaxed text-slate-300">
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                <span className="font-bold text-white block">Current Status:</span>
                <div className="flex items-center space-x-2">
                  <span className={`w-2 h-2 rounded-full ${paypalConfig?.configured ? "bg-emerald-400" : "bg-amber-400"}`} />
                  <span className="font-semibold text-slate-200">
                    {paypalConfig?.configured ? "Sandbox Credentials Configured & Ready" : "Unconfigured (Missing Client ID or Secret)"}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Target Endpoint: <span className="font-mono text-cyan-300">{paypalConfig?.base_url || "https://api-m.sandbox.paypal.com"}</span>
                </div>
              </div>

              <div className="space-y-2">
                <span className="font-bold text-white block">How to configure in 4 quick steps:</span>
                <ol className="list-decimal list-inside space-y-2 text-slate-300">
                  <li>
                    Log in to the <a href="https://developer.paypal.com/dashboard/applications/sandbox" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline font-semibold inline-flex items-center space-x-0.5"><span>PayPal Developer Dashboard</span><ExternalLink className="w-3 h-3 ml-0.5 inline" /></a>.
                  </li>
                  <li>
                    Under <strong>Apps & Credentials</strong> &gt; <strong>Sandbox</strong>, select or click <strong>Create App</strong>.
                  </li>
                  <li>
                    Copy your <strong>Client ID</strong> and <strong>Secret</strong>.
                  </li>
                  <li>
                    Paste them into <code className="bg-slate-950 px-1.5 py-0.5 rounded text-blue-300 font-mono">backend/.env</code>:
                    <pre className="mt-1 p-2 bg-slate-950 rounded border border-slate-800 text-[11px] font-mono text-cyan-300 overflow-x-auto">
PAYPAL_MODE=&quot;sandbox&quot;
PAYPAL_CLIENT_ID=&quot;your_sandbox_client_id_here&quot;
PAYPAL_CLIENT_SECRET=&quot;your_sandbox_client_secret_here&quot;
                    </pre>
                  </li>
                </ol>
              </div>

              <div className="p-3 bg-blue-950/30 border border-blue-500/30 rounded-xl text-[11px] text-blue-200">
                <strong>Sandbox Test Accounts:</strong> Under <em>Testing Tools &gt; Sandbox Accounts</em>, use your system-generated <strong>Personal (Buyer)</strong> account to log into the checkout popup to approve sample transactions.
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setShowPayPalHelpModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs"
              >
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
