/**
 * Guardian CFO API Client
 *
 * Provides typed, resilient HTTP access to the FastAPI backend,
 * supporting JWT bearer authentication and multi-tenant scoping.
 */

import {
  SystemHealth,
  CompanyMetrics,
  InvoiceSubmission,
  FinancialDecision,
  GuardianRiskAssessment,
  PayPalOrderResponse,
  AuditLogItem,
  ExplainabilityReport,
  TokenResponse,
  FinancialSummary,
  TrendItem,
  CategoryAnalysisResponse,
  ExpenseAnomaly,
  RecurringExpensesResponse,
  ChatQueryResponse,
  ChatSession,
  ChatSessionDetail,
  RiskPolicyThresholds,
  SecurityAlert,
  Vendor,
  VendorCreatePayload,
  PaymentDraft,
  PaymentDraftCreatePayload,
  PaymentDraftUpdatePayload,
  ExecutePaymentPayload,
  ExecutePaymentResponse,
  PaymentTransactionItem,
  PayPalConfig,
  PayPalOrderDraftResponse,
  NotificationItem,
  UnreadCountResponse,
  WebhookEventItem,
  BusinessSettingsSummary,
  PaymentDecisionRoomResponse,
} from "@/types";

export const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    if (typeof window !== "undefined") {
      const currentHost = window.location.hostname;
      if (currentHost === "127.0.0.1" && process.env.NEXT_PUBLIC_API_URL.includes("localhost")) {
        return process.env.NEXT_PUBLIC_API_URL.replace("localhost", "127.0.0.1");
      }
      if (currentHost === "localhost" && process.env.NEXT_PUBLIC_API_URL.includes("127.0.0.1")) {
        return process.env.NEXT_PUBLIC_API_URL.replace("127.0.0.1", "localhost");
      }
    }
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
};

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

// Token helper
export const authStorage = {
  getToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("guardian_cfo_token");
  },
  setToken: (token: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("guardian_cfo_token", token);
    }
  },
  clearToken: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("guardian_cfo_token");
      localStorage.removeItem("guardian_cfo_user");
    }
  },
};

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  const token = authStorage.getToken();

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
      cache: "no-store",
    });
  } catch (netErr: unknown) {
    const errObj = netErr as Error | undefined;
    const errorMsg = `Unable to connect to Guardian CFO backend at ${baseUrl}. Ensure local backend server is running. (${errObj?.message || "Network Error"})`;
    console.error(`[Guardian CFO API Connection Error] ${options.method || "GET"} ${url}:`, netErr);
    throw new ApiError(errorMsg, 0, { originalError: errObj?.message, url, baseUrl });
  }

  // Handle 401 Unauthorized: Attempt automatic demo session recovery
  if (response.status === 401 && !endpoint.includes("/auth/")) {
    console.warn(`[Guardian CFO API] Unauthorized (401) on ${endpoint}. Attempting automatic demo session recovery...`);
    try {
      const demoRes = await fetch(`${baseUrl}/api/v1/auth/demo-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (demoRes.ok) {
        const demoData = await demoRes.json();
        authStorage.setToken(demoData.access_token);
        const retryHeaders = {
          ...defaultHeaders,
          ...options.headers,
          Authorization: `Bearer ${demoData.access_token}`,
        };
        const retryResponse = await fetch(url, {
          ...options,
          headers: retryHeaders,
          cache: "no-store",
        });
        if (retryResponse.ok) {
          return retryResponse.json();
        }
      }
    } catch {
      // Recovery failed, proceed to error parsing
    }
  }

  if (!response.ok) {
    let errorData: Record<string, unknown> | null = null;
    try {
      errorData = await response.json();
    } catch {
      // response wasn't JSON
    }
    let message = `API request failed: ${response.status} ${response.statusText}`;
    if (errorData?.detail) {
      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (typeof errorData.detail === "object" && (errorData.detail as { message?: string }).message) {
        message = (errorData.detail as { message: string }).message;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
      } else {
        message = JSON.stringify(errorData.detail);
      }
    }
    throw new ApiError(message, response.status, errorData);
  }

  return response.json();
}

export const api = {
  // System Health
  getHealth: () => request<SystemHealth>("/api/v1/health"),

  // Authentication & Tenant Context
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const res = await request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    authStorage.setToken(res.access_token);
    return res;
  },

  demoLogin: async (): Promise<TokenResponse> => {
    const res = await request<TokenResponse>("/api/v1/auth/demo-login", {
      method: "POST",
    });
    authStorage.setToken(res.access_token);
    return res;
  },

  register: async (data: {
    email: string;
    password: string;
    full_name: string;
    business_name: string;
    currency?: string;
  }): Promise<TokenResponse> => {
    const res = await request<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    authStorage.setToken(res.access_token);
    return res;
  },

  logout: async () => {
    try {
      await request<{ message: string }>("/api/v1/auth/logout", {
        method: "POST",
      });
    } finally {
      authStorage.clearToken();
    }
  },

  getMe: () =>
    request<{
      user: TokenResponse["user"];
      business: TokenResponse["business"];
      settings: Record<string, unknown> | null;
    }>("/api/v1/auth/me"),

  // Financial Analytics Engine
  getFinancialSummary: (period?: string, startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (period) params.append("period", period);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<FinancialSummary>(`/api/v1/analytics/summary${qs}`);
  },

  getFinancialTrends: (months: number = 6) =>
    request<TrendItem[]>(`/api/v1/analytics/trends?months=${months}`),

  getCategoryBreakdown: (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams();
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<CategoryAnalysisResponse>(`/api/v1/analytics/categories${qs}`);
  },

  getExpenseAnomalies: () => request<ExpenseAnomaly[]>("/api/v1/analytics/anomalies"),

  getRecurringExpenses: () => request<RecurringExpensesResponse>("/api/v1/analytics/recurring"),

  // CFO Financial Intelligence
  getMetrics: () => request<CompanyMetrics>("/api/v1/cfo/metrics"),
  analyzeInvoice: (data: InvoiceSubmission) =>
    request<{
      decision_id: number;
      recommendation: string;
      rationale: string;
      budget_impact_pct: number;
      runway_impact_days: number;
      current_stage: string;
    }>("/api/v1/cfo/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getDecisions: (status?: string) =>
    request<FinancialDecision[]>(
      `/api/v1/cfo/decisions${status ? `?status=${encodeURIComponent(status)}` : ""}`
    ),

  // Guardian AI Risk & Fraud
  assessRisk: (decisionId: number, forceDeepScan: boolean = false) =>
    request<GuardianRiskAssessment>("/api/v1/guardian/assess-risk", {
      method: "POST",
      body: JSON.stringify({ decision_id: decisionId, force_deep_scan: forceDeepScan }),
    }),
  getAssessments: () => request<GuardianRiskAssessment[]>("/api/v1/guardian/assessments"),
  getAssessmentForDecision: (decisionId: number) =>
    request<GuardianRiskAssessment>(`/api/v1/guardian/assessments/${decisionId}`),
  getRiskPolicy: () => request<RiskPolicyThresholds>("/api/v1/guardian/policy"),
  getSecurityAlerts: (status?: string) =>
    request<SecurityAlert[]>(
      `/api/v1/guardian/alerts${status ? `?status_filter=${encodeURIComponent(status)}` : ""}`
    ),
  resolveSecurityAlert: (alertId: number) =>
    request<SecurityAlert>(`/api/v1/guardian/alerts/${alertId}/resolve`, {
      method: "POST",
    }),

  // Secure Payment Management Lifecycle
  getVendors: (search?: string) =>
    request<Vendor[]>(`/api/v1/payments/vendors${search ? `?search=${encodeURIComponent(search)}` : ""}`),

  createVendor: (payload: VendorCreatePayload) =>
    request<Vendor>("/api/v1/payments/vendors", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createPaymentDraft: (payload: PaymentDraftCreatePayload) =>
    request<PaymentDraft>("/api/v1/payments/drafts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getPaymentDrafts: (status?: string) =>
    request<PaymentDraft[]>(
      `/api/v1/payments/drafts${status ? `?status=${encodeURIComponent(status)}` : ""}`
    ),

  getPaymentDraft: (id: number) =>
    request<PaymentDraft>(`/api/v1/payments/drafts/${id}`),

  updatePaymentDraft: (id: number, payload: PaymentDraftUpdatePayload) =>
    request<PaymentDraft>(`/api/v1/payments/drafts/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  assessDraftRisk: (id: number) =>
    request<PaymentDraft>(`/api/v1/payments/drafts/${id}/assess-risk`, {
      method: "POST",
    }),

  approvePaymentDraft: (id: number, notes?: string, expectedDetailsHash?: string, dualApprovalOverride?: boolean) =>
    request<PaymentDraft>(`/api/v1/payments/drafts/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({
        notes: notes || undefined,
        expected_details_hash: expectedDetailsHash || undefined,
        dual_approval_override: dualApprovalOverride || false,
      }),
    }),

  rejectPaymentDraft: (id: number, reason?: string) =>
    request<PaymentDraft>(
      `/api/v1/payments/drafts/${id}/reject`,
      {
        method: "POST",
        body: JSON.stringify({
          reason: reason || "Declined by executive authority.",
        }),
      }
    ),

  executePayment: (payload: ExecutePaymentPayload) =>
    request<ExecutePaymentResponse>("/api/v1/payments/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getPaymentTransactions: () =>
    request<PaymentTransactionItem[]>("/api/v1/payments/transactions"),

  // Payment Decision Room
  getDecisionRoom: (draftId: number, forceRecalculate: boolean = false) =>
    request<PaymentDecisionRoomResponse>(
      `/api/v1/payments/decision-room/${draftId}?force_recalculate=${forceRecalculate}`
    ),

  loadDemoScenario: (scenarioKey: "normal" | "suspicious") =>
    request<PaymentDecisionRoomResponse>(
      `/api/v1/payments/decision-room/demo-scenario/${scenarioKey}`,
      { method: "POST" }
    ),

  holdPaymentDraft: (draftId: number, notes?: string) =>
    request<PaymentDraft>(`/api/v1/payments/drafts/${draftId}/hold`, {
      method: "POST",
      body: JSON.stringify({ notes: notes || undefined }),
    }),

  requestReviewDraft: (draftId: number, notes?: string) =>
    request<PaymentDraft>(`/api/v1/payments/drafts/${draftId}/request-review`, {
      method: "POST",
      body: JSON.stringify({ notes: notes || undefined }),
    }),

  // PayPal REST API Payment Management (Legacy)
  createPaymentOrder: (decisionId: number) =>
    request<PayPalOrderResponse>("/api/v1/payments/create-order", {
      method: "POST",
      body: JSON.stringify({ decision_id: decisionId }),
    }),

  capturePaymentOrder: (transactionId: number, orderId: string) =>
    request<Record<string, unknown>>("/api/v1/payments/capture-order", {
      method: "POST",
      body: JSON.stringify({
        transaction_id: transactionId,
        paypal_order_id: orderId,
      }),
    }),
  getTransactions: () => request<Record<string, unknown>[]>("/api/v1/payments/transactions"),

  // PayPal Orders v2 & Sandbox Direct Endpoints
  getPayPalConfig: () =>
    request<PayPalConfig>("/api/v1/payments/paypal/config"),

  createPayPalOrderForDraft: (draftId: number, returnUrl?: string, cancelUrl?: string, idempotencyKey?: string) =>
    request<PayPalOrderDraftResponse>("/api/v1/payments/paypal/orders", {
      method: "POST",
      body: JSON.stringify({
        draft_id: draftId,
        return_url: returnUrl || undefined,
        cancel_url: cancelUrl || undefined,
        idempotency_key: idempotencyKey || undefined,
      }),
    }),

  getPayPalOrderDetails: (orderId: string) =>
    request<Record<string, unknown>>(`/api/v1/payments/paypal/orders/${orderId}`),

  capturePayPalOrderById: (orderId: string, transactionId?: number) =>
    request<Record<string, unknown>>(
      `/api/v1/payments/paypal/orders/${orderId}/capture${transactionId ? `?transaction_id=${transactionId}` : ""}`,
      { method: "POST" }
    ),

  cancelPayPalOrder: (transactionId: number) =>
    request<Record<string, unknown>>(`/api/v1/payments/paypal/orders/${transactionId}/cancel`, {
      method: "POST",
    }),

  // AI CFO Natural Language Assistant
  askCfo: (prompt: string, sessionId?: number | null) =>
    request<ChatQueryResponse>("/api/v1/cfo/chat", {
      method: "POST",
      body: JSON.stringify({ prompt, session_id: sessionId ?? null }),
    }),

  getChatSessions: () => request<ChatSession[]>("/api/v1/cfo/chat/sessions"),

  getChatSessionDetail: (sessionId: number) =>
    request<ChatSessionDetail>(`/api/v1/cfo/chat/sessions/${sessionId}`),

  deleteChatSession: (sessionId: number) =>
    request<void>(`/api/v1/cfo/chat/sessions/${sessionId}`, {
      method: "DELETE",
    }),

  // Explainability & Audit
  getAuditLogs: (params?: {
    search?: string;
    stage?: string;
    actor?: string;
    action?: string;
    decision_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.search) query.append("search", params.search);
    if (params?.stage) query.append("stage", params.stage);
    if (params?.actor) query.append("actor", params.actor);
    if (params?.action) query.append("action", params.action);
    if (params?.decision_id !== undefined) query.append("decision_id", String(params.decision_id));
    if (params?.limit !== undefined) query.append("limit", String(params.limit));
    if (params?.offset !== undefined) query.append("offset", String(params.offset));
    const qs = query.toString();
    return request<AuditLogItem[]>(`/api/v1/audit/logs${qs ? `?${qs}` : ""}`);
  },

  explainDecision: (decisionId: number) =>
    request<ExplainabilityReport>(`/api/v1/audit/explain/${decisionId}`),

  // Notifications
  getNotifications: (params?: {
    is_read?: boolean;
    category?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.is_read !== undefined) query.append("is_read", String(params.is_read));
    if (params?.category) query.append("category", params.category);
    if (params?.limit !== undefined) query.append("limit", String(params.limit));
    if (params?.offset !== undefined) query.append("offset", String(params.offset));
    const qs = query.toString();
    return request<NotificationItem[]>(`/api/v1/notifications${qs ? `?${qs}` : ""}`);
  },

  getUnreadNotificationCount: () =>
    request<UnreadCountResponse>("/api/v1/notifications/unread-count"),

  markNotificationRead: (id: number) =>
    request<NotificationItem>(`/api/v1/notifications/${id}/read`, {
      method: "POST",
    }),

  markAllNotificationsRead: () =>
    request<{ success: boolean; marked_count: number }>("/api/v1/notifications/read-all", {
      method: "POST",
    }),

  // Webhooks
  getWebhookEvents: (status?: string, limit?: number) => {
    const query = new URLSearchParams();
    if (status) query.append("status", status);
    if (limit) query.append("limit", String(limit));
    const qs = query.toString();
    return request<WebhookEventItem[]>(`/api/v1/webhooks/events${qs ? `?${qs}` : ""}`);
  },

  // Business Settings
  getBusinessSettings: () =>
    request<BusinessSettingsSummary>("/api/v1/cfo/settings"),

  updateBusinessSettings: (data: Partial<BusinessSettingsSummary>) =>
    request<BusinessSettingsSummary>("/api/v1/cfo/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
