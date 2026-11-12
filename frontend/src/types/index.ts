/**
 * Guardian CFO Data Contracts
 */

export interface ServiceStatus {
  configured: boolean;
  status: string;
  details?: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  database: {
    status: string;
    type: string;
    error: string | null;
  };
  paypal: ServiceStatus;
  openai: ServiceStatus;
  timestamp: string;
}

export interface UserSummary {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface BusinessSummary {
  id: number;
  name: string;
  legal_name?: string | null;
  currency: string;
  total_balance: number;
  monthly_budget: number;
  monthly_spent: number;
  owner_id: number;
}

export interface BusinessSettingsSummary {
  id: number;
  auto_approve_threshold: number;
  max_single_payment_limit: number;
  require_dual_approval_above: number;
  risk_tolerance_level: string;
  notification_email?: string | null;
  enable_paypal_sandbox: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserSummary;
  business: BusinessSummary;
}

export interface CompanyMetrics {
  name: string;
  operating_currency: string;
  total_balance: number;
  monthly_budget: number;
  monthly_spent: number;
  budget_remaining: number;
  runway_months: number;
  burn_rate_daily: number;
}

export interface InvoiceSubmission {
  title: string;
  vendor: string;
  vendor_email: string;
  category: string;
  amount: number;
  currency: string;
  notes?: string;
}

export interface FinancialDecision {
  id: number;
  title: string;
  vendor: string;
  vendor_email: string;
  category: string;
  amount: number;
  currency: string;
  status: "PENDING" | "ANALYZING" | "AWAITING_APPROVAL" | "APPROVED" | "REJECTED" | "PAID" | "FAILED";
  cfo_recommendation: "APPROVE" | "FLAG_FOR_REVIEW" | "REJECT" | "UNDER_REVIEW";
  cfo_rationale: string | null;
  budget_impact_pct: number;
  runway_impact_days: number;
  current_stage: string;
  created_at: string;
  updated_at: string;
}

export interface RiskSignalItem {
  id: string;
  name: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  score_impact: number;
  description: string;
  evidence: string;
}

export interface RiskPolicyThresholds {
  low_min: number;
  low_max: number;
  medium_min: number;
  medium_max: number;
  high_min: number;
  high_max: number;
  critical_min: number;
  critical_max: number;
  notice: string;
}

export interface GuardianRiskAssessment {
  id: number;
  decision_id: number;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  verdict: "SAFE_TO_PAY" | "REQUIRES_MANUAL_REVIEW" | "REQUIRES_DUAL_EXECUTIVE_APPROVAL" | "BLOCKED";
  recommended_action?: string;
  plain_explanation?: string;
  detected_signals?: RiskSignalItem[];
  supporting_evidence?: string[];
  missing_information?: string[];
  flags: string[];
  vendor_verified: boolean;
  is_duplicate_invoice: boolean;
  anomaly_detected: boolean;
  verification_hash?: string;
  created_at?: string;
}

export interface SecurityAlert {
  id: number;
  business_id: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  title: string;
  description: string;
  status: "OPEN" | "INVESTIGATING" | "RESOLVED" | "DISMISSED";
  created_at: string;
  resolved_at?: string | null;
}

export interface PayPalOrderResponse {
  transaction_id: number;
  decision_id: number;
  paypal_order_id: string;
  status: string;
  is_sandbox: boolean;
  approval_url: string | null;
  amount: number;
  currency: string;
  recipient_email: string;
}

export interface AuditLogItem {
  id: number;
  decision_id?: number | null;
  stage: string;
  actor: string;
  action: string;
  summary: string;
  details?: string | null;
  rationale?: string | null;
  ip_address?: string | null;
  timestamp: string;
}

export interface ApproverDetail {
  step: number;
  user_id?: number | null;
  name: string;
  email?: string | null;
  role?: string | null;
  approved_at: string;
  notes?: string | null;
}

export interface RejectionDetail {
  user_id?: number | null;
  name: string;
  email?: string | null;
  rejected_at: string;
  reason: string;
}

export interface ApprovalDetails {
  status: string;
  requires_dual_approval: boolean;
  approvers: ApproverDetail[];
  rejected_by?: RejectionDetail | null;
}

export interface ProviderStatusDetails {
  provider: string;
  mode: string;
  order_id?: string | null;
  capture_id?: string | null;
  status: string;
  reconciled_at?: string | null;
  settlement_amount?: string | null;
}

export interface ExplainabilityReport {
  decision_id: number;
  title: string;
  vendor: string;
  amount: number;
  currency: string;
  current_status: string;
  cfo_reasoning?: string | null;
  guardian_security_summary?: string | null;
  audit_trail: AuditLogItem[];

  // 6 Core Transparent Explainability Answers
  what_happened: string;
  why_flagged: string;
  evidence_detected: string[];
  action_taken: string;
  approval_details: ApprovalDetails;
  final_provider_status: ProviderStatusDetails;
}

export type NotificationCategory =
  | "HIGH_RISK_DETECTED"
  | "PAYMENT_AWAITING_APPROVAL"
  | "PAYMENT_APPROVED"
  | "PAYMENT_REJECTED"
  | "PAYMENT_COMPLETED"
  | "PAYMENT_FAILED"
  | "UNUSUAL_FINANCIAL_ACTIVITY";

export type NotificationSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface NotificationItem {
  id: number;
  business_id: number;
  user_id?: number | null;
  category: NotificationCategory | string;
  severity: NotificationSeverity | string;
  title: string;
  message: string;
  payment_draft_id?: number | null;
  transaction_id?: number | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface WebhookEventItem {
  id: number;
  business_id?: number | null;
  event_type: string;
  event_id: string;
  status: "RECEIVED" | "PROCESSED" | "FAILED" | string;
  error_message?: string | null;
  created_at: string;
  processed_at?: string | null;
  payload: string;
}

// ==========================================
// Financial Analytics Data Contracts
// ==========================================

export interface FinancialSummary {
  currency: string;
  total_revenue: number;
  previous_revenue: number;
  revenue_growth_pct: number;
  total_expenses: number;
  previous_expenses: number;
  expense_change_pct: number;
  net_cash_flow: number;
  previous_net_cash_flow: number;
  net_cash_flow_change: number;
  cash_flow_margin_pct: number;
  burn_rate_monthly: number;
  runway_months: number;
  treasury_balance: number;
  period_start: string;
  period_end: string;
  comparison_period_start: string;
  comparison_period_end: string;
  total_transactions: number;
}

export interface TrendItem {
  month: string;
  label: string;
  revenue: number;
  expenses: number;
  net_cash_flow: number;
}

export interface CategoryBreakdownItem {
  category: string;
  total_amount: number;
  percentage_share: number;
  transaction_count: number;
}

export interface CategoryAnalysisResponse {
  expenses_by_category: CategoryBreakdownItem[];
  revenue_by_category: CategoryBreakdownItem[];
  total_expenses: number;
  total_revenue: number;
}

export interface ExpenseAnomaly {
  category: string;
  vendor?: string | null;
  current_amount: number;
  previous_amount: number;
  increase_pct: number;
  severity: "MODERATE" | "SIGNIFICANT" | "CRITICAL";
  reason: string;
}

export interface RecurringExpenseItem {
  vendor_name: string;
  category: string;
  amount: number;
  frequency: string;
  annualized_amount: number;
  last_paid_date?: string | null;
}

export interface RecurringExpensesResponse {
  total_recurring_monthly: number;
  total_recurring_annual: number;
  items: RecurringExpenseItem[];
}

// ==========================================
// AI CFO Chat & Consultation Contracts
// ==========================================

export interface ChatQueryRequest {
  prompt: string;
  session_id?: number | null;
}

export interface ChatQueryResponse {
  session_id: number;
  session_title: string;
  message_id: number;
  role: string;
  reply: string;
  tools_executed: string[];
  insight_card?: {
    type: string;
    data: Record<string, unknown>;
  } | null;
  timestamp: string;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  reasoning_meta?: string | null;
  created_at: string;
}

export interface ChatSession {
  id: number;
  business_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatSessionDetail {
  id: number;
  business_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

// ==========================================
// Secure Payment Management Contracts
// ==========================================

export type PaymentStatus =
  | "DRAFT"
  | "RISK_REVIEWED"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "PROVIDER_PENDING"
  | "COMPLETED"
  | "REJECTED"
  | "FAILED"
  | "EXPIRED"
  | "REVIEW_REQUIRED";

export interface Vendor {
  id: number;
  business_id: number;
  name: string;
  email: string;
  website?: string | null;
  status: string;
  trust_score: number;
  bank_or_paypal_email?: string | null;
  total_paid: number;
  created_at: string;
}

export interface VendorCreatePayload {
  name: string;
  email: string;
  website?: string;
  bank_or_paypal_email?: string;
}

export interface PaymentDraft {
  id: number;
  business_id: number;
  vendor_id: number;
  vendor_name: string;
  vendor_email: string;
  title: string;
  amount: number;
  currency: string;
  category: string;
  purpose?: string | null;
  invoice_number?: string | null;
  invoice_url?: string | null;
  description?: string | null;
  status: PaymentStatus;
  cfo_recommendation: string;
  cfo_rationale?: string | null;
  budget_impact_pct: number;
  runway_impact_days: number;
  details_hash?: string | null;
  idempotency_key?: string | null;
  approved_at?: string | null;
  approved_by_id?: number | null;
  approved_by_name?: string | null;
  expires_at?: string | null;
  requires_dual_approval?: boolean;
  secondary_approved_at?: string | null;
  secondary_approved_by_id?: number | null;
  secondary_approved_by_name?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
  policy_eligibility?: {
    can_approve: boolean;
    mandatory_block: boolean;
    requires_dual_approval: boolean;
    status: string;
    current_step: number;
    total_steps: number;
    step_name?: string;
    reason: string;
    recommended_action: string;
    primary_approver_id?: number;
    primary_approver_name?: string;
    primary_approved_at?: string;
  } | null;
  approvals?: Array<{
    id: number;
    approved_by_id: number;
    approved_by_name?: string | null;
    status: string;
    approval_role: string;
    notes?: string | null;
    details_hash?: string | null;
    approved_at: string;
    expires_at?: string | null;
  }>;
  risk_assessment?: {
    id: number;
    risk_score: number;
    risk_level: string;
    verdict: string;
    recommended_action: string;
    plain_explanation: string;
    risk_signals?: Array<{
      id: string;
      name: string;
      severity: string;
      score_impact: number;
      description: string;
      evidence: string;
    }>;
    supporting_evidence?: string[];
    missing_information?: string[];
    vendor_verified?: boolean;
    is_duplicate_invoice?: boolean;
    verification_hash?: string;
    created_at?: string;
  } | null;
}

export interface PaymentDraftCreatePayload {
  vendor_id?: number | null;
  new_vendor?: VendorCreatePayload | null;
  title: string;
  amount: number;
  currency: string;
  category: string;
  purpose: string;
  invoice_number?: string | null;
  invoice_url?: string | null;
  idempotency_key?: string | null;
  auto_run_risk_scan?: boolean;
}

export interface PaymentDraftUpdatePayload {
  title?: string;
  amount?: number;
  currency?: string;
  category?: string;
  purpose?: string;
  invoice_number?: string;
  invoice_url?: string;
}

export interface ExecutePaymentPayload {
  draft_id: number;
  idempotency_key?: string | null;
  payment_method: "SIMULATED_PROVIDER" | "PAYPAL_SANDBOX";
}

export interface ExecutePaymentResponse {
  transaction_id: number;
  draft_id: number;
  status: string;
  amount: number;
  currency: string;
  recipient_email: string;
  provider_reference: string;
  payment_method: string;
  is_sandbox: boolean;
  approval_url?: string | null;
  settled_at?: string | null;
  message: string;
}

export interface PayPalConfig {
  configured: boolean;
  mode: string;
  base_url: string;
  client_id_preview?: string | null;
  status: string;
  details: string;
}

export interface PayPalOrderDraftResponse {
  transaction_id: number;
  draft_id: number;
  paypal_order_id: string;
  status: string;
  is_sandbox: boolean;
  approval_url?: string | null;
  amount: number;
  currency: string;
  recipient_email: string;
}

export interface PaymentTransactionItem {
  id: number;
  business_id: number;
  vendor_id?: number | null;
  payment_draft_id?: number | null;
  transaction_type: string;
  amount: number;
  currency: string;
  status: string;
  category: string;
  description?: string | null;
  is_recurring: boolean;
  recurring_frequency?: string | null;
  idempotency_key?: string | null;
  payment_method: string;
  paypal_order_id?: string | null;
  paypal_capture_id?: string | null;
  settled_at?: string | null;
  created_at: string;
}

// ==========================================
// Payment Decision Room Contracts
// ==========================================

export interface DecisionRoomOverview {
  draft_id: number;
  title: string;
  vendor_id: number;
  vendor_name: string;
  vendor_email: string;
  vendor_status: string;
  amount: number;
  currency: string;
  invoice_number?: string | null;
  invoice_url?: string | null;
  purpose?: string | null;
  category: string;
  status: string;
  created_at: string;
  updated_at: string;
  details_hash?: string | null;
  idempotency_key?: string | null;
}

export interface DecisionRoomRiskSignal {
  id: string;
  name: string;
  severity: string;
  score_impact: number;
  description: string;
  evidence: string;
}

export interface DecisionRoomRiskAssessment {
  id?: number | null;
  risk_score: number;
  risk_level: string;
  verdict: string;
  recommended_action: string;
  plain_explanation: string;
  signals: DecisionRoomRiskSignal[];
  supporting_evidence: string[];
  missing_information: string[];
  flags: string[];
  verification_hash?: string | null;
  anomaly_detected: boolean;
  vendor_verified: boolean;
  is_duplicate_invoice: boolean;
  created_at?: string | null;
}

export interface DecisionRoomAiRecommendation {
  why_risky: string;
  verified_facts: string[];
  cash_flow_impact: string;
  required_verifications: string[];
  recommended_reviewer_action: string;
  is_ai_generated: boolean;
  disclaimer: string;
}

export interface DecisionRoomCommitmentItem {
  vendor_name: string;
  category: string;
  amount: number;
  frequency: string;
}

export interface DecisionRoomCashFlowImpact {
  available_cash_before: number;
  payment_amount: number;
  projected_cash_after: number;
  percentage_cash_consumed: number;
  monthly_budget: number;
  monthly_spent_before: number;
  projected_monthly_spent: number;
  percentage_budget_consumed: number;
  remaining_budget_before: number;
  projected_remaining_budget: number;
  runway_impact_days: number;
  projected_runway_months: number;
  commitments_monthly_total: number;
  active_commitments_count: number;
  commitments_sample: DecisionRoomCommitmentItem[];
  calculation_notes: string;
}

export interface DecisionRoomApprover {
  step: number;
  user_id?: number | null;
  name: string;
  email?: string | null;
  role?: string | null;
  approved_at: string;
  notes?: string | null;
  details_hash?: string | null;
}

export interface DecisionRoomApprovalWorkflow {
  can_approve: boolean;
  mandatory_block: boolean;
  requires_dual_approval: boolean;
  current_step: number;
  total_steps: number;
  step_name: string;
  reason: string;
  recommended_action: string;
  primary_approver?: DecisionRoomApprover | null;
  secondary_approver?: DecisionRoomApprover | null;
  approval_history: DecisionRoomApprover[];
  rejection_reason?: string | null;
  details_hash?: string | null;
  expires_at?: string | null;
  is_expired: boolean;
}

export interface DecisionRoomAuditItem {
  id: number;
  stage: string;
  actor: string;
  action: string;
  summary: string;
  details?: string | null;
  rationale?: string | null;
  timestamp: string;
}

export interface DecisionRoomPayPalStatus {
  is_configured: boolean;
  mode: string;
  client_id_preview?: string | null;
  order_id?: string | null;
  capture_id?: string | null;
  approval_url?: string | null;
  transaction_status?: string | null;
  settled_at?: string | null;
}

export interface PaymentDecisionRoomResponse {
  overview: DecisionRoomOverview;
  risk_assessment: DecisionRoomRiskAssessment;
  ai_recommendation: DecisionRoomAiRecommendation;
  cash_flow_impact: DecisionRoomCashFlowImpact;
  approval_workflow: DecisionRoomApprovalWorkflow;
  audit_timeline: DecisionRoomAuditItem[];
  paypal_status: DecisionRoomPayPalStatus;
}

