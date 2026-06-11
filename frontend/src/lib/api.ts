const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8050";

/** Thrown on non-2xx API responses so callers can distinguish 403 from empty data. */
export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

// ---------------------------------------------------------------------------
// Shared auth state: ``setApiAuth`` stores the JWT; all requests send
// ``Authorization: Bearer`` when a token is present.
// ---------------------------------------------------------------------------
type ApiAuth = {
  token?: string;
};

let _auth: ApiAuth = {
  token: (import.meta.env.VITE_AUTH_TOKEN as string | undefined) ?? undefined,
};

export function setApiAuth(next: ApiAuth) {
  _auth = { ..._auth, ...next };
}

export function getApiAuth(): ApiAuth {
  return { ..._auth };
}

function _detailToMessage(detail: unknown): string {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  return JSON.stringify(detail);
}

async function apiFetch(path: string, init: RequestInit) {
  const headers: Record<string, string> = {
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (_auth.token) {
    headers["Authorization"] = `Bearer ${_auth.token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const rawText = await res.text();
    let body: unknown = rawText;
    try {
      body = rawText ? JSON.parse(rawText) : undefined;
    } catch {
      body = rawText;
    }
    let errorMessage = `API ${res.status} ${res.statusText}`;
    if (typeof body === "object" && body !== null) {
      const o = body as Record<string, unknown>;
      const detail = o.detail ?? o.message ?? o.error;
      const msg = _detailToMessage(detail);
      if (msg) {
        errorMessage = msg;
      }
    } else if (typeof body === "string" && body.trim()) {
      errorMessage = `${errorMessage}: ${body}`;
    }
    throw new ApiError(res.status, errorMessage, body);
  }
  return res;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await apiFetch(path, { method: "GET" });
  return res.json() as Promise<T>;
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const res = await apiFetch(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  return res.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  await apiFetch(path, { method: "DELETE" });
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await apiFetch(
    path,
    {
      method: "POST",
      body: form,
    },
  );
  return res.json() as Promise<T>;
}

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

// Health
export type HealthLiveStatus = { status: string };
export type InviteProbeResponse = { status: string; checks: string[] };
export type EsignProbeResponse = { status: string; vendor: string };

// Cases
export type PartyPayload = { name: string; role: string; email?: string };
export type ParcelPayload = { county_fips: string; stage?: string; risk_score?: number; parties?: PartyPayload[] };
export type CaseCreatePayload = { project_id: string; parcels: ParcelPayload[]; jurisdiction_code: string; stage?: string };
export type CaseResponse = { project_id: string; parcel_ids: string[]; next_deadline_at?: string };
export type CaseDetails = { id: string; project_id: string; stage: string; risk_score: number; next_deadline_at?: string };

export type JurisdictionItem = { code: string; label: string; active: boolean };
export type JurisdictionsResponse = { items: JurisdictionItem[] };

export type ProjectHierarchyParcel = {
  id: string;
  stage?: string | null;
  county_fips: string;
  parcel_state?: string | null;
};
export type ProjectHierarchySegment = {
  id: string;
  name?: string | null;
  segment_number?: number | null;
  parcels: ProjectHierarchyParcel[];
};
export type ProjectHierarchyAlignment = {
  id: string;
  name: string;
  alignment_type?: string | null;
  segments: ProjectHierarchySegment[];
};
export type ProjectHierarchyResponse = {
  project: { id: string; name: string; state?: string | null; jurisdiction_code: string };
  alignments: ProjectHierarchyAlignment[];
  unassigned_parcels: ProjectHierarchyParcel[];
};

export type RulesEvaluateTrigger = {
  rule_id: string;
  version: string;
  citation: string;
  fired: boolean;
  evidence: Record<string, unknown>;
};
export type RulesEvaluateDeadline = {
  deadline_type: string;
  due_date: string;
  source: string;
  citation: string;
  inputs: Record<string, unknown>;
};
export type RulesEvaluatePayload = {
  jurisdiction: string;
  case_payload?: Record<string, unknown>;
  anchor_events?: Record<string, string>;
};
export type RulesEvaluateResponse = {
  jurisdiction: string;
  triggers: RulesEvaluateTrigger[];
  deadlines: RulesEvaluateDeadline[];
  errors: string[];
};

// Templates
export type TemplateMetadata = { id: string; version: string; locale: string; jurisdiction?: string; variables: Record<string, unknown>; privilege: string };
export type TemplateRenderPayload = {
  template_id: string;
  locale?: string;
  variables: Record<string, unknown>;
  persist?: boolean;
  project_id?: string;
  parcel_id?: string;
};
export type TemplateRenderResponse = {
  rendered: string;
  document_id?: string;
  deadline_anchors?: Record<string, string>;
};

// AI
export type AIDraftPayload = { jurisdiction: string; payload: Record<string, unknown> };
export type AIDraftResponse = { jurisdiction: string; template_id: string; rationale: string; rule_results: Array<{ rule_id: string; fired: boolean }>; suggestions: string[]; next_actions: string[] };

// Workflows
export type TaskCreatePayload = { project_id: string; parcel_id?: string; title: string; persona: string; due_at?: string };
export type TaskResponse = { task_id: string };
export type Approval = { case_id: string; action: string; due: string };
export type ApprovalsResponse = { items: Approval[] };
export type BinderExportResponse = { bundle_id: string; hash: string; storage_path: string };

// Integrations
export type DocketWebhookResponse = { received: boolean; signature_present: boolean; payload: unknown };

// Portal
export type InvitePayload = { email: string; parcel_id?: string; project_id?: string };
export type InviteResponse = { invite_id: string; email: string; parcel_id?: string; project_id?: string; status: string; expires_at: string; invite_link?: string };
export type VerifyPayload = { token: string };
export type VerifyResponse = { status: string; invite_id?: string; verified_at?: string };
export type DecisionOptionsResponse = { options: string[] };
export type DecisionPayload = { parcel_id: string; selection: string; note?: string };
export type DecisionResponse = { decision_id: string; parcel_id: string; selection: string; routed_to: string; created_at: string };
export type UploadItem = { id: string; parcel_id: string; filename: string; content_type: string; size_bytes: number; uploaded_at: string; sha256: string };
export type UploadsResponse = { items: UploadItem[] };

// Communications
export type CommItem = { id: string; ts?: string; channel: string; summary?: string; proof: unknown; status: string };
export type CommsResponse = { items: CommItem[] };
export type CommsFeedItem = CommItem & { kind?: string; parcel_id?: string | null };

// Packet
export type ChecklistItem = { label: string; done: boolean };
export type PacketChecklistResponse = { parcel_id: string; items: ChecklistItem[] };

// Rules
export type RuleResultItem = { id: string; rule_id: string; citation: string; fired: boolean; fired_at?: string; payload: Record<string, unknown> };
export type RuleResultsResponse = { parcel_id: string; items: RuleResultItem[] };

// Budgets
export type BudgetSummary = { project_id: string; cap_amount: number; actual_amount: number; utilization_pct: number; alerts: string[]; updated_at?: string };

// Binder
export type BinderSection = { name: string; status: string; detail?: string };
export type BinderStatusResponse = {
  project_id: string;
  completeness_pct?: number;
  sections: BinderSection[];
};

// Notifications
export type NotificationPreviewPayload = { template_id: string; channel: string; to: string; project_id: string; parcel_id: string; variables?: Record<string, unknown> };
export type NotificationPreviewResponse = { notification_id: string; channel: string; to: string; subject?: string; body: string; mode: string; created_at: string; communication_id?: string; audit_event_id?: string };

// Parcels
export type ParcelItem = {
  id: string;
  project_id: string;
  project_name?: string | null;
  segment_id?: string | null;
  segment_label?: string | null;
  alignment_label?: string | null;
  county?: string | null;
  parcel_state?: string | null;
  county_fips?: string;
  owner?: string | null;
  stage: string;
  risk_score: number;
  offer_status?: string | null;
  assignee_name?: string | null;
  next_deadline_at?: string;
  updated_at?: string;
  geom?: unknown;
};
export type ParcelsResponse = { total: number; items: ParcelItem[] };

export type ParcelGridSavedView = {
  id: string;
  name: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

// Deadlines
export type DeadlineItem = {
  id: string;
  title: string;
  due_at: string;
  parcel_id?: string;
  timezone: string;
  deadline_type?: string | null;
  citation?: string | null;
  source_kind?: string | null;
};
export type DeadlinesResponse = { project_id: string; items: DeadlineItem[] };
export type DeadlineCreatePayload = { project_id: string; parcel_id?: string; title: string; due_at: string; timezone?: string };
export type DeadlineCreateResponse = { deadline_id: string };
export type DeadlineIcalResponse = { project_id: string; ical: string };

// Deadline Derivation
export type DerivedDeadlineItem = {
  id: string;
  title: string;
  description: string;
  due_date: string;
  anchor_event: string;
  anchor_date: string;
  offset_days: number;
  citation: string;
  deadline_type: string;
  extendable: boolean;
  max_extension_days: number;
  notes?: string;
};
export type DeadlineDerivePayload = {
  project_id: string;
  parcel_id?: string;
  jurisdiction: string;
  anchor_events: Record<string, string>;
  template_id?: string;
  template_variables?: Record<string, unknown>;
  persist?: boolean;
  timezone?: string;
};
export type DeadlineDeriveResponse = {
  jurisdiction: string;
  project_id: string;
  parcel_id?: string;
  derived_count: number;
  persisted_count: number;
  deadlines: DerivedDeadlineItem[];
  errors: string[];
};

// Title
export type TitleInstrumentItem = { id: string; document_id?: string; created_at?: string; ocr_payload?: Record<string, unknown>; metadata?: Record<string, unknown> };
export type TitleInstrumentsResponse = { parcel_id: string; items: TitleInstrumentItem[] };
export type TitleUploadResponse = { document_id: string; sha256: string; storage_path: string };

// Appraisals
export type AppraisalData = { id: string; value?: number; summary?: string; comps?: Array<Record<string, unknown>>; completed_at?: string; attachment_id?: string };
export type AppraisalResponse = { parcel_id: string; appraisal?: AppraisalData };
export type AppraisalUpsertPayload = { parcel_id: string; value?: number; summary?: string; comps?: Array<Record<string, unknown>>; attachment_id?: string };
export type AppraisalUpsertResponse = { appraisal_id: string };

// Ops
export type RoutePlanResponse = { project_id: string; parcel_ids: string[]; csv: string };

// Outside
export type RepositoryCompletenessResponse = { project_id: string; percent: number; checks: Record<string, boolean>; missing: string[] };
export type CaseInitiatePayload = { project_id: string; parcel_id: string; template_id: string };
export type CaseInitiateResponse = { draft_id: string; docket_number: string };
export type StatusUpdatePayload = { project_id: string; parcel_id?: string; new_status: string; reason: string };
export type StatusUpdateResponse = { status_change_id: string; status: string };

// ============================================================================
// TYPED API WRAPPER FUNCTIONS
// ============================================================================

// --- Health ---
export const healthLive = () => apiGet<HealthLiveStatus>("/health/live");
export const healthInvite = () => apiGet<InviteProbeResponse>("/health/invite");
export const healthEsign = () => apiGet<EsignProbeResponse>("/health/esign");

// --- Cases ---
export const createCase = (payload: CaseCreatePayload) => apiPostJson<CaseResponse>("/cases", payload);
export const getCase = (parcelId: string) => apiGet<CaseDetails>(`/cases/${encodeURIComponent(parcelId)}`);
export const getJurisdictions = () => apiGet<JurisdictionsResponse>("/jurisdictions");
export const getProjectHierarchy = (projectId: string) =>
  apiGet<ProjectHierarchyResponse>(`/projects/${encodeURIComponent(projectId)}/hierarchy`);
export const evaluateRules = (payload: RulesEvaluatePayload) => apiPostJson<RulesEvaluateResponse>("/rules/evaluate", payload);

// --- Templates ---
export const listTemplates = () => apiGet<TemplateMetadata[]>("/templates");
export const renderTemplate = (payload: TemplateRenderPayload) => apiPostJson<TemplateRenderResponse>("/templates/render", payload);

// --- AI ---
export const generateDraft = (payload: AIDraftPayload) => apiPostJson<AIDraftResponse>("/ai/drafts", payload);

// --- Workflows ---
export const createTask = (payload: TaskCreatePayload) => apiPostJson<TaskResponse>("/workflows/tasks", payload);
export const listApprovals = () => apiGet<ApprovalsResponse>("/workflows/approvals");
export const exportBinder = (payload: { project_id: string; parcel_id?: string | null }) =>
  apiPostJson<BinderExportResponse>("/workflows/binder/export", payload);

// --- Integrations ---
export const docketWebhook = (payload: Record<string, unknown>) => apiPostJson<DocketWebhookResponse>("/integrations/dockets", payload);

// --- Portal ---
export const sendInvite = (payload: InvitePayload) => apiPostJson<InviteResponse>("/portal/invites", payload);
export const verifyInvite = (payload: VerifyPayload) => apiPostJson<VerifyResponse>("/portal/verify", payload);
export const getDecisionOptions = () => apiGet<DecisionOptionsResponse>("/portal/decision/options");
export const submitDecision = (payload: DecisionPayload) => apiPostJson<DecisionResponse>("/portal/decision", payload);
export const listUploads = (parcelId: string) => apiGet<UploadsResponse>(`/portal/uploads?parcel_id=${encodeURIComponent(parcelId)}`);
export const uploadFile = (parcelId: string, file: File) => {
  const form = new FormData();
  form.set("parcel_id", parcelId);
  form.set("file", file);
  return apiPostForm<UploadItem>("/portal/uploads", form);
};

// --- Communications ---
export const listCommunications = (parcelId: string) => apiGet<CommsResponse>(`/communications?parcel_id=${encodeURIComponent(parcelId)}`);
export const getCommunicationsFeed = (projectId: string, parcelId?: string | null) => {
  const q = new URLSearchParams({ project_id: projectId });
  if (parcelId) q.set("parcel_id", parcelId);
  return apiGet<{ items: CommsFeedItem[] }>(`/communications/feed?${q.toString()}`);
};

// --- Packet ---
export const getPacketChecklist = (parcelId: string) => apiGet<PacketChecklistResponse>(`/packet/checklist?parcel_id=${encodeURIComponent(parcelId)}`);

// --- Rules ---
export const listRuleResults = (parcelId: string) => apiGet<RuleResultsResponse>(`/rules/results?parcel_id=${encodeURIComponent(parcelId)}`);

// --- Budgets ---
export const getBudgetSummary = (projectId: string) => apiGet<BudgetSummary>(`/budgets/summary?project_id=${encodeURIComponent(projectId)}`);

// --- Binder ---
export const getBinderStatus = (projectId: string) => apiGet<BinderStatusResponse>(`/binder/status?project_id=${encodeURIComponent(projectId)}`);

// --- Notifications ---
export const previewNotification = (payload: NotificationPreviewPayload) => apiPostJson<NotificationPreviewResponse>("/notifications/preview", payload);

export const listParcelGridViews = () => apiGet<{ items: ParcelGridSavedView[] }>("/users/me/parcel-views");

export const createParcelGridView = (body: { name: string; payload: Record<string, unknown> }) =>
  apiPostJson<ParcelGridSavedView>("/users/me/parcel-views", body);

export const deleteParcelGridView = (id: string) =>
  apiDelete(`/users/me/parcel-views/${encodeURIComponent(id)}`);

export type FirmAssignee = {
  id: string;
  full_name?: string | null;
  email: string;
  persona: string;
};

export const listFirmAssignees = () => apiGet<{ items: FirmAssignee[] }>("/users/me/firm-assignees");

// --- Parcels ---
export const listParcels = (params?: {
  project_id?: string;
  stage?: string;
  min_risk?: number;
  deadline_before?: string;
  q?: string;
  county?: string;
  assigned_to?: string;
  offer_status?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.stage) query.set("stage", params.stage);
  if (params?.min_risk !== undefined) query.set("min_risk", String(params.min_risk));
  if (params?.deadline_before) query.set("deadline_before", params.deadline_before);
  if (params?.q) query.set("q", params.q);
  if (params?.county) query.set("county", params.county);
  if (params?.assigned_to) query.set("assigned_to", params.assigned_to);
  if (params?.offer_status) query.set("offer_status", params.offer_status);
  if (params?.sort) query.set("sort", params.sort);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiGet<ParcelsResponse>(`/parcels${qs ? `?${qs}` : ""}`);
};

export async function exportParcelsCsv(params?: {
  project_id?: string;
  stage?: string;
  min_risk?: number;
  deadline_before?: string;
  q?: string;
  county?: string;
  assigned_to?: string;
  offer_status?: string;
}): Promise<Blob> {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.stage) query.set("stage", params.stage);
  if (params?.min_risk !== undefined) query.set("min_risk", String(params.min_risk));
  if (params?.deadline_before) query.set("deadline_before", params.deadline_before);
  if (params?.q) query.set("q", params.q);
  if (params?.county) query.set("county", params.county);
  if (params?.assigned_to) query.set("assigned_to", params.assigned_to);
  if (params?.offer_status) query.set("offer_status", params.offer_status);
  const qs = query.toString();
  const headers: Record<string, string> = {};
  const tok = getApiAuth().token;
  if (tok) headers.Authorization = `Bearer ${tok}`;
  const res = await fetch(`${API_BASE}/parcels/export.csv${qs ? `?${qs}` : ""}`, { headers });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }
  return res.blob();
}

export type DashboardHomeResponse = {
  persona: string;
  project_id?: string | null;
  sample_size: number;
  sample_sufficient: boolean;
  parcels_by_stage: Record<string, number>;
  pending_offers_count: number;
  overdue_tasks_count: number;
  deadlines_next_14_count: number;
  pending_approvals_count: number | null;
  escalations_open_count: number | null;
  litigation_rate: number | null;
  litigation_rate_insufficient_data: boolean;
  cycle_time_median_days: number | null;
  cycle_time_insufficient_data: boolean;
  budget_utilization_pct: number | null;
  budget_utilization_insufficient_data: boolean;
};

export const getDashboardHome = (projectId?: string) => {
  const qs = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return apiGet<DashboardHomeResponse>(`/dashboard/home${qs}`);
};

export type ParcelTimelineEvent = {
  id: string;
  kind: string;
  title: string;
  detail?: string | null;
  at?: string | null;
  actor?: string | null;
  source?: string | null;
};

export const getParcelTimeline = (parcelId: string) =>
  apiGet<{ parcel_id: string; events: ParcelTimelineEvent[] }>(
    `/parcels/${encodeURIComponent(parcelId)}/timeline`,
  );

// --- Deadlines ---
export const listDeadlines = (projectId: string) => apiGet<DeadlinesResponse>(`/deadlines?project_id=${encodeURIComponent(projectId)}`);
export const createDeadline = (payload: DeadlineCreatePayload) => apiPostJson<DeadlineCreateResponse>("/deadlines", payload);
export const getDeadlinesIcal = (projectId: string) => apiGet<DeadlineIcalResponse>(`/deadlines/ical?project_id=${encodeURIComponent(projectId)}`);
export const deriveDeadlines = (payload: DeadlineDerivePayload) => apiPostJson<DeadlineDeriveResponse>("/deadlines/derive", payload);

// --- Title ---
export const listTitleInstruments = (parcelId: string) => apiGet<TitleInstrumentsResponse>(`/title/instruments?parcel_id=${encodeURIComponent(parcelId)}`);
export const uploadTitleInstrument = (parcelId: string, file: File) => {
  const form = new FormData();
  form.set("parcel_id", parcelId);
  form.set("file", file);
  return apiPostForm<TitleUploadResponse>("/title/instruments", form);
};

// --- Appraisals ---
export const getAppraisal = (parcelId: string) => apiGet<AppraisalResponse>(`/appraisals?parcel_id=${encodeURIComponent(parcelId)}`);
export const upsertAppraisal = (payload: AppraisalUpsertPayload) => apiPostJson<AppraisalUpsertResponse>("/appraisals", payload);

// --- Ops ---
export const getRoutePlan = (projectId: string) => apiGet<RoutePlanResponse>(`/ops/routes/plan?project_id=${encodeURIComponent(projectId)}`);

// --- Outside ---
export const getRepositoryCompleteness = (projectId: string) => apiGet<RepositoryCompletenessResponse>(`/outside/repository/completeness?project_id=${encodeURIComponent(projectId)}`);
export const initiateCase = (payload: CaseInitiatePayload) => apiPostJson<CaseInitiateResponse>("/outside/case/initiate", payload);
export const updateStatus = (payload: StatusUpdatePayload) => apiPostJson<StatusUpdateResponse>("/outside/status", payload);

// ============================================================================
// AI AGENTS
// ============================================================================

// Agent Types
export type AgentRunPayload = {
  agent_type: string;
  case_id?: string;
  project_id?: string;
  parcel_id?: string;
  document_id?: string;
  jurisdiction?: string;
  action?: string;
  payload?: Record<string, unknown>;
};
export type AgentRunResponse = {
  success: boolean;
  confidence: number;
  data: Record<string, unknown>;
  flags: string[];
  requires_review: boolean;
  decision_id?: string;
  escalation_id?: string;
};

export type AIDecisionItem = {
  id: string;
  agent_type: string;
  project_id?: string;
  parcel_id?: string;
  confidence: number;
  flags: string[];
  reviewed: boolean;
  review_outcome?: string;
  occurred_at: string;
};
export type AIDecisionDetail = {
  id: string;
  agent_type: string;
  project_id?: string;
  parcel_id?: string;
  context: Record<string, unknown>;
  result_data: Record<string, unknown>;
  confidence: number;
  flags: string[];
  explanation?: string;
  reviewed?: boolean;
  reviewed_by?: string;
  reviewed_at?: string;
  review_outcome?: string;
  occurred_at: string;
};

export type EscalationItem = {
  id: string;
  ai_decision_id: string;
  reason: string;
  priority: string;
  status: string;
  created_at: string;
  context_summary?: string;
};
export type EscalationDetail = {
  id: string;
  ai_decision_id: string;
  reason: string;
  priority: string;
  status: string;
  ai_decision: {
    agent_type: string;
    confidence: number;
    flags: string[];
    result_data: Record<string, unknown>;
    explanation?: string;
  };
  context_summary?: string;
  assigned_to?: string;
  resolution?: string;
  created_at: string;
  resolved_at?: string;
};
export type EscalationResolvePayload = {
  resolution: string;
  outcome: string;
};
export type EscalationResolveResponse = {
  escalation_id: string;
  status: string;
  resolution: string;
  outcome: string;
  resolved_by: string;
  resolved_at: string;
};

// --- Agents ---
export const runAgent = (payload: AgentRunPayload) => apiPostJson<AgentRunResponse>("/agents/run", payload);
export const listAIDecisions = (params?: { project_id?: string; parcel_id?: string; agent_type?: string; pending_review?: boolean; limit?: number }) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.parcel_id) query.set("parcel_id", params.parcel_id);
  if (params?.agent_type) query.set("agent_type", params.agent_type);
  if (params?.pending_review !== undefined) query.set("pending_review", String(params.pending_review));
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiGet<AIDecisionItem[]>(`/agents/decisions${qs ? `?${qs}` : ""}`);
};
export const getAIDecision = (decisionId: string) => apiGet<AIDecisionDetail>(`/agents/decisions/${encodeURIComponent(decisionId)}`);
export const listEscalations = (params?: { status?: string; priority?: string; limit?: number }) => {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.priority) query.set("priority", params.priority);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiGet<EscalationItem[]>(`/agents/escalations${qs ? `?${qs}` : ""}`);
};
export const getEscalation = (escalationId: string) => apiGet<EscalationDetail>(`/agents/escalations/${encodeURIComponent(escalationId)}`);
export const resolveEscalation = (escalationId: string, payload: EscalationResolvePayload) => 
  apiPostJson<EscalationResolveResponse>(`/agents/escalations/${encodeURIComponent(escalationId)}/resolve`, payload);

// ============================================================================
// ROE (Right-of-Entry) Management
// ============================================================================

export type ROEItem = {
  id: string;
  project_id: string;
  effective_date?: string;
  expiry_date?: string;
  status?: string;
  conditions?: string;
  permitted_activities?: string[];
  access_windows?: Record<string, unknown>;
  signed_by?: string;
  signed_at?: string;
  template_id?: string;
  document_id?: string;
  created_at?: string;
};
export type ROEsResponse = { parcel_id: string; items: ROEItem[] };
export type ROECreatePayload = {
  parcel_id: string;
  project_id: string;
  effective_date: string;
  expiry_date: string;
  conditions?: string;
  permitted_activities?: string[];
  access_windows?: Record<string, unknown>;
  template_id?: string;
  landowner_party_id?: string;
};
export type ROECreateResponse = { roe_id: string; status: string };
export type ROEUpdatePayload = {
  effective_date?: string;
  expiry_date?: string;
  conditions?: string;
  permitted_activities?: string[];
  access_windows?: Record<string, unknown>;
  status?: string;
  signed_by?: string;
  signed_at?: string;
};
export type ROEUpdateResponse = { roe_id: string; updated: boolean; changes: Record<string, unknown> };
export type ROEFieldEventPayload = {
  event_type: string;
  latitude?: number;
  longitude?: number;
  personnel_name?: string;
  notes?: string;
  photo_document_ids?: string[];
};
export type ROEFieldEventResponse = { event_id: string; roe_id: string; event_type: string; event_time: string };
export type ExpiringROEsResponse = {
  threshold_days: number;
  project_id?: string;
  count: number;
  items: Array<{ id: string; parcel_id: string; project_id: string; expiry_date?: string; days_until_expiry?: number; status?: string; expiry_warning_sent: boolean }>;
};

export const listROEs = (parcelId: string) => apiGet<ROEsResponse>(`/roe?parcel_id=${encodeURIComponent(parcelId)}`);
export const createROE = (payload: ROECreatePayload) => apiPostJson<ROECreateResponse>("/roe", payload);
export const updateROE = (roeId: string, payload: ROEUpdatePayload) => {
  return apiFetch(`/roe/${encodeURIComponent(roeId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then(res => res.json() as Promise<ROEUpdateResponse>);
};
export const createROEFieldEvent = (roeId: string, payload: ROEFieldEventPayload) => 
  apiPostJson<ROEFieldEventResponse>(`/roe/${encodeURIComponent(roeId)}/field-events`, payload);
export const listExpiringROEs = (params?: { project_id?: string; days_threshold?: number }) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.days_threshold !== undefined) query.set("days_threshold", String(params.days_threshold));
  const qs = query.toString();
  return apiGet<ExpiringROEsResponse>(`/roe/expiring${qs ? `?${qs}` : ""}`);
};

// ============================================================================
// Offers & Payment Ledger
// ============================================================================

export type OfferItem = {
  id: string;
  offer_type?: string;
  offer_number?: number;
  amount?: number;
  terms?: Record<string, unknown>;
  terms_summary?: string;
  status?: string;
  source?: string;
  created_date?: string;
  sent_date?: string;
  response_due_date?: string;
  response_date?: string;
  response_notes?: string;
  previous_offer_id?: string;
  created_at?: string;
  counter_amount?: number;
  counter_date?: string;
};
export type OffersResponse = { parcel_id: string; count: number; items: OfferItem[] };
export type OfferCreatePayload = {
  parcel_id: string;
  project_id: string;
  offer_type: string;
  amount?: number;
  terms?: Record<string, unknown>;
  terms_summary?: string;
  response_due_date?: string;
  offer_letter_id?: string;
  statutory_override_reason?: string;
};
export type OfferCreateResponse = { offer_id: string; offer_number: number };
export type CounterOfferPayload = {
  amount?: number;
  terms?: Record<string, unknown>;
  terms_summary?: string;
  source?: string;
  response_due_date?: string;
  landowner_party_id?: string;
};
export type CounterOfferResponse = { counter_id: string; original_offer_id: string; offer_number: number };
export type PaymentLedgerResponse = {
  parcel_id: string;
  exists: boolean;
  id?: string;
  project_id?: string;
  status?: string;
  current_offer_id?: string;
  settlement_offer_id?: string;
  settlement_amount?: number;
  settlement_date?: string;
  payment_instruction_date?: string;
  payment_cleared_date?: string;
  payment_reference?: string;
  status_history?: Array<Record<string, unknown>>;
  payment_status?: string;
  amount_paid?: number;
  payment_date?: string;
};

export const listOffers = (parcelId: string) => apiGet<OffersResponse>(`/offers?parcel_id=${encodeURIComponent(parcelId)}`);
export const createOffer = (payload: OfferCreatePayload) => apiPostJson<OfferCreateResponse>("/offers", payload);
export const getOfferLifecycleCheck = (parcelId: string, projectId: string) => {
  const q = new URLSearchParams({ parcel_id: parcelId, project_id: projectId });
  return apiGet<Record<string, unknown>>(`/offers/lifecycle-check?${q.toString()}`);
};
export const createCounterOffer = (offerId: string, payload: CounterOfferPayload) => 
  apiPostJson<CounterOfferResponse>(`/offers/${encodeURIComponent(offerId)}/counter`, payload);
export const getPaymentLedger = (parcelId: string) => apiGet<PaymentLedgerResponse>(`/offers/payment-ledger/${encodeURIComponent(parcelId)}`);

// ============================================================================
// Litigation Cases
// ============================================================================

export type LitigationCaseItem = {
  id: string;
  parcel_id: string;
  project_id: string;
  cause_number?: string;
  court: string;
  court_county?: string;
  is_quick_take: boolean;
  status?: string;
  lead_counsel_internal?: string;
  lead_counsel_outside?: string;
  filed_date?: string;
  commissioners_hearing_date?: string;
  trial_date?: string;
  created_at?: string;
  filing_date?: string;
  service_date?: string;
};
export type LitigationCasesResponse = { count: number; items: LitigationCaseItem[] };
export type LitigationCaseDetail = LitigationCaseItem & {
  lead_counsel_internal_id?: string;
  lead_counsel_outside_firm?: string;
  filing_document_id?: string;
  possession_order_date?: string;
  settlement_amount?: number;
  final_judgment_amount?: number;
  closed_date?: string;
  metadata?: Record<string, unknown>;
  updated_at?: string;
};
export type LitigationCaseCreatePayload = {
  parcel_id: string;
  project_id: string;
  court: string;
  court_county?: string;
  cause_number?: string;
  is_quick_take?: boolean;
  lead_counsel_internal?: string;
  lead_counsel_internal_id?: string;
  lead_counsel_outside?: string;
  lead_counsel_outside_firm?: string;
};
export type LitigationCaseCreateResponse = { case_id: string; status: string };
export type LitigationCaseUpdatePayload = {
  status?: string;
  cause_number?: string;
  court?: string;
  court_county?: string;
  is_quick_take?: boolean;
  lead_counsel_internal?: string;
  lead_counsel_outside?: string;
  filed_date?: string;
  commissioners_hearing_date?: string;
  trial_date?: string;
  settlement_amount?: number;
  closed_date?: string;
  status_notes?: string;
  filing_date?: string;
  service_date?: string;
};
export type LitigationCaseUpdateResponse = { case_id: string; updated: boolean; changes: Record<string, unknown> };
export type LitigationHistoryResponse = {
  case_id: string;
  parcel_id: string;
  current_status?: string;
  history: Array<{ id: string; old_status?: string; new_status: string; reason?: string; actor_persona?: string; occurred_at?: string }>;
};

export const listLitigationCases = (params?: { project_id?: string; parcel_id?: string; status?: string }) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.parcel_id) query.set("parcel_id", params.parcel_id);
  if (params?.status) query.set("status", params.status);
  const qs = query.toString();
  return apiGet<LitigationCasesResponse>(`/litigation${qs ? `?${qs}` : ""}`);
};
export const createLitigationCase = (payload: LitigationCaseCreatePayload) => apiPostJson<LitigationCaseCreateResponse>("/litigation", payload);
export const getLitigationCase = (caseId: string) => apiGet<LitigationCaseDetail>(`/litigation/${encodeURIComponent(caseId)}`);
export const updateLitigationCase = (caseId: string, payload: LitigationCaseUpdatePayload) => {
  return apiFetch(`/litigation/${encodeURIComponent(caseId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then(res => res.json() as Promise<LitigationCaseUpdateResponse>);
};
export const getLitigationHistory = (caseId: string) => apiGet<LitigationHistoryResponse>(`/litigation/${encodeURIComponent(caseId)}/history`);

export type LitigationTracksResponse = {
  case_id: string;
  state?: string | null;
  tx: Record<string, unknown[]>;
  in: Record<string, unknown[]>;
};
export const getLitigationTracks = (caseId: string) =>
  apiGet<LitigationTracksResponse>(`/litigation/${encodeURIComponent(caseId)}/tracks`);

export type ComplaintParcelsValidatePayload = { project_id: string; parcel_ids: string[] };
export type ComplaintParcelsValidateResponse = { ok: boolean; errors: string[] };
export const validateComplaintParcels = (payload: ComplaintParcelsValidatePayload) =>
  apiPostJson<ComplaintParcelsValidateResponse>("/litigation/complaint-parcels/validate", payload);

// ============================================================================
// Curative Items
// ============================================================================

export type CurativeItem = {
  id: string;
  item_type: string;
  description: string;
  severity: string;
  status?: string;
  responsible_party?: string;
  responsible_user_id?: string;
  due_date?: string;
  identified_date?: string;
  resolved_date?: string;
  title_instrument_id?: string;
  resolution_notes?: string;
  created_at?: string;
};
export type CurativeItemsResponse = { parcel_id: string; count: number; items: CurativeItem[] };
export type CurativeItemCreatePayload = {
  parcel_id: string;
  item_type: string;
  description: string;
  severity?: string;
  responsible_party?: string;
  responsible_user_id?: string;
  due_date?: string;
  title_instrument_id?: string;
};
export type CurativeItemCreateResponse = { item_id: string; status: string };
export type CurativeItemUpdatePayload = {
  status?: string;
  severity?: string;
  description?: string;
  responsible_party?: string;
  due_date?: string;
  resolution_notes?: string;
  resolution_document_id?: string;
};
export type CurativeItemUpdateResponse = { item_id: string; updated: boolean; changes: Record<string, unknown> };
export type CurativeAnalyticsResponse = {
  project_id?: string;
  parcel_id?: string;
  total_items: number;
  status_breakdown: Record<string, number>;
  type_breakdown: Record<string, number>;
  severity_breakdown: Record<string, number>;
  overdue_count: number;
  overdue?: number;
  by_status?: Record<string, number>;
};

export const listCurativeItems = (parcelId: string, status?: string) => {
  const query = new URLSearchParams();
  query.set("parcel_id", parcelId);
  if (status) query.set("status", status);
  return apiGet<CurativeItemsResponse>(`/title/curative?${query.toString()}`);
};
export const createCurativeItem = (payload: CurativeItemCreatePayload) => apiPostJson<CurativeItemCreateResponse>("/title/curative", payload);
export const updateCurativeItem = (itemId: string, payload: CurativeItemUpdatePayload) => {
  return apiFetch(`/title/curative/${encodeURIComponent(itemId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then(res => res.json() as Promise<CurativeItemUpdateResponse>);
};
export const getCurativeAnalytics = (params?: { project_id?: string; parcel_id?: string }) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.parcel_id) query.set("parcel_id", params.parcel_id);
  const qs = query.toString();
  return apiGet<CurativeAnalyticsResponse>(`/title/curative/analytics/summary${qs ? `?${qs}` : ""}`);
};

// ============================================================================
// Admin (Firm Admin & Platform Admin)
// ============================================================================

// Firm Admin Types
export type FirmMetrics = {
  total_projects: number;
  total_parcels: number;
  parcels_by_stage: Record<string, number>;
  active_negotiations: number;
  litigation_cases: number;
  completion_rate: number;
  pending_offers: number;
  active_roes: number;
};

export type FirmCaseItem = {
  parcel_id: string;
  project_id: string;
  project_name?: string;
  parcel_stage: string;
  litigation_status?: string;
  offer_status?: string;
  payment_status?: string;
  updated_at: string;
};

export type FirmCasesResponse = {
  cases: FirmCaseItem[];
  total: number;
  limit: number;
  offset: number;
};

export type FirmActivityItem = {
  id: string;
  action: string;
  resource: string;
  actor_persona?: string;
  occurred_at: string;
  payload: Record<string, unknown>;
};

export type FirmActivityResponse = {
  activities: FirmActivityItem[];
  days: number;
  count: number;
};

// Platform Admin Types
export type PlatformMetrics = {
  total_firms: number;
  total_parcels: number;
  total_cases: number;
  parcels_by_stage: Record<string, number>;
  cases_by_status: Record<string, number>;
  active_portal_sessions: number;
  pending_approvals: number;
  system_health: Record<string, string>;
};

export type GlobalCaseItem = {
  parcel_id: string;
  project_id: string;
  project_name?: string;
  parcel_stage: string;
  jurisdiction?: string;
  litigation_status?: string;
  litigation_case_id?: string;
  cause_number?: string;
  offer_status?: string;
  payment_status?: string;
  landowner_name?: string;
  updated_at: string;
};

export type GlobalCasesResponse = {
  cases: GlobalCaseItem[];
  total: number;
  limit: number;
  offset: number;
};

export type ProjectOverview = {
  project_id: string;
  project_name: string;
  jurisdiction: string;
  stage: string;
  parcel_count: number;
  litigation_count: number;
  completion_rate: number;
  created_at: string;
};

export type ProjectsOverviewResponse = {
  projects: ProjectOverview[];
  total: number;
  limit: number;
  offset: number;
};

export type SearchResult = {
  result_type: string;
  id: string;
  title: string;
  subtitle?: string;
  project_id?: string;
  parcel_id?: string;
};

export type GlobalSearchResponse = {
  query: string;
  results: SearchResult[];
  count: number;
};

export type HealthStatus = {
  service: string;
  status: string;
  latency_ms?: number;
  last_check: string;
};

export type PlatformHealthResponse = {
  overall_status: string;
  services: HealthStatus[];
  checked_at: string;
};

// Firm Admin API Functions
export const getFirmDashboard = () => apiGet<FirmMetrics>("/admin/firm/dashboard");

export const getFirmCases = (params?: { status?: string; litigation_status?: string; search?: string; limit?: number; offset?: number }) => {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.litigation_status) query.set("litigation_status", params.litigation_status);
  if (params?.search) query.set("search", params.search);
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());
  const qs = query.toString();
  return apiGet<FirmCasesResponse>(`/admin/firm/cases${qs ? `?${qs}` : ""}`);
};

export const getFirmActivity = (days?: number, limit?: number) => {
  const query = new URLSearchParams();
  if (days) query.set("days", days.toString());
  if (limit) query.set("limit", limit.toString());
  const qs = query.toString();
  return apiGet<FirmActivityResponse>(`/admin/firm/activity${qs ? `?${qs}` : ""}`);
};

// Platform Admin API Functions
export const getPlatformDashboard = () => apiGet<PlatformMetrics>("/admin/platform/dashboard");

export const getPlatformCases = (params?: {
  project_id?: string;
  status?: string;
  litigation_status?: string;
  case_type?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.status) query.set("status", params.status);
  if (params?.litigation_status) query.set("litigation_status", params.litigation_status);
  if (params?.case_type) query.set("case_type", params.case_type);
  if (params?.search) query.set("search", params.search);
  if (params?.date_from) query.set("date_from", params.date_from);
  if (params?.date_to) query.set("date_to", params.date_to);
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());
  const qs = query.toString();
  return apiGet<GlobalCasesResponse>(`/admin/platform/cases${qs ? `?${qs}` : ""}`);
};

export const getPlatformProjects = (params?: { jurisdiction?: string; stage?: string; search?: string; limit?: number; offset?: number }) => {
  const query = new URLSearchParams();
  if (params?.jurisdiction) query.set("jurisdiction", params.jurisdiction);
  if (params?.stage) query.set("stage", params.stage);
  if (params?.search) query.set("search", params.search);
  if (params?.limit) query.set("limit", params.limit.toString());
  if (params?.offset) query.set("offset", params.offset.toString());
  const qs = query.toString();
  return apiGet<ProjectsOverviewResponse>(`/admin/platform/projects${qs ? `?${qs}` : ""}`);
};

export const globalSearch = (q: string, limit?: number) => {
  const query = new URLSearchParams();
  query.set("q", q);
  if (limit) query.set("limit", limit.toString());
  return apiGet<GlobalSearchResponse>(`/search?${query.toString()}`);
};

export const getPlatformHealth = () => apiGet<PlatformHealthResponse>("/admin/platform/health");

// ============================================================================
// AI Copilot
// ============================================================================

export type CopilotMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: string[];
};

export type CopilotRequest = {
  question: string;
  case_id?: string;
  parcel_id?: string;
  jurisdiction?: string;
  conversation_id?: string;
  conversation_history?: Array<{ role: string; content: string }>;
  stream?: boolean;
};

export type CopilotResponse = {
  conversation_id: string;
  answer: string;
  citations: string[];
  confidence: number;
  sources: Array<{ citation: string }>;
  suggested_actions: string[];
};

export type ConversationHistory = {
  conversation_id: string;
  messages: CopilotMessage[];
};

// Non-streaming copilot request
export const askCopilot = (payload: CopilotRequest) => 
  apiPostJson<CopilotResponse>("/copilot/ask", { ...payload, stream: false });

// Get conversation history
export const getCopilotConversation = (conversationId: string) => 
  apiGet<ConversationHistory>(`/copilot/conversations/${encodeURIComponent(conversationId)}`);

// List all conversations
export type ConversationListItem = {
  conversation_id: string;
  last_updated: string;
  message_count: number;
  preview: string;
};
export type ConversationListResponse = {
  conversations: ConversationListItem[];
  count: number;
};
export const listCopilotConversations = (limit?: number) => {
  const query = new URLSearchParams();
  if (limit) query.set("limit", limit.toString());
  const qs = query.toString();
  return apiGet<ConversationListResponse>(`/copilot/conversations${qs ? `?${qs}` : ""}`);
};

// Clear conversation
export const clearCopilotConversation = (conversationId: string) =>
  apiFetch(`/copilot/conversations/${encodeURIComponent(conversationId)}`, { method: "DELETE" });

// Quick actions
export const copilotDraftResponse = (parcelId: string, responseType: string, jurisdiction?: string, notes?: string) => {
  const query = new URLSearchParams();
  query.set("parcel_id", parcelId);
  query.set("response_type", responseType);
  if (jurisdiction) query.set("jurisdiction", jurisdiction);
  if (notes) query.set("notes", notes);
  return apiPostJson<CopilotResponse>(`/copilot/draft-response?${query.toString()}`, {});
};

export const copilotSummarizeCase = (caseId?: string, parcelId?: string, jurisdiction?: string) => {
  const query = new URLSearchParams();
  if (caseId) query.set("case_id", caseId);
  if (parcelId) query.set("parcel_id", parcelId);
  if (jurisdiction) query.set("jurisdiction", jurisdiction);
  return apiPostJson<CopilotResponse>(`/copilot/summarize-case?${query.toString()}`, {});
};

export const copilotExplainRequirement = (requirement: string, jurisdiction: string) => {
  const query = new URLSearchParams();
  query.set("requirement", requirement);
  query.set("jurisdiction", jurisdiction);
  return apiPostJson<CopilotResponse>(`/copilot/explain-requirement?${query.toString()}`, {});
};

// Streaming helper - returns EventSource URL
export const getCopilotStreamUrl = () => {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8050";
  return `${API_BASE}/copilot/ask`;
};

// ============================================================================
// Task Management
// ============================================================================

export type TaskItem = {
  id: string;
  project_id: string;
  parcel_id?: string;
  title: string;
  description?: string;
  category: string;
  priority: string;
  status: string;
  persona: string;
  assigned_to?: string;
  assigned_to_name?: string;
  due_at?: string;
  created_at: string;
  is_overdue: boolean;
  metadata: Record<string, unknown>;
};

export type TaskListResponse = { tasks: TaskItem[] };

export type TaskStatsResponse = {
  total: number;
  open: number;
  in_progress: number;
  completed: number;
  overdue: number;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  by_assignee: Array<{ user_id: string; user_name: string; count: number }>;
};

export type TaskCreatePayloadV2 = {
  project_id: string;
  parcel_id?: string;
  title: string;
  description?: string;
  category?: string;
  priority?: string;
  due_at?: string | null;
  auto_assign?: boolean;
};

export type AssignmentSuggestion = {
  user_id: string;
  user_name: string;
  persona: string;
  current_workload: number;
  reason: string;
  score: number;
};

export const listTasks = (params?: {
  project_id?: string;
  parcel_id?: string;
  status?: string;
  priority?: string;
  category?: string;
  overdue_only?: boolean;
}) => {
  const query = new URLSearchParams();
  if (params?.project_id) query.set("project_id", params.project_id);
  if (params?.parcel_id) query.set("parcel_id", params.parcel_id);
  if (params?.status) query.set("status", params.status);
  if (params?.priority) query.set("priority", params.priority);
  if (params?.category) query.set("category", params.category);
  if (params?.overdue_only) query.set("overdue_only", "true");
  const qs = query.toString();
  return apiGet<TaskListResponse>(`/tasks${qs ? `?${qs}` : ""}`);
};

export const getTaskStats = (projectId?: string) => {
  const query = new URLSearchParams();
  if (projectId) query.set("project_id", projectId);
  const qs = query.toString();
  return apiGet<TaskStatsResponse>(`/tasks/stats/summary${qs ? `?${qs}` : ""}`);
};

export const createTaskV2 = (payload: TaskCreatePayloadV2) =>
  apiPostJson<TaskItem>("/tasks", payload);

export const updateTask = (taskId: string, payload: Record<string, unknown>) =>
  apiFetch(`/tasks/${encodeURIComponent(taskId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((res) => res.json());

export const completeTask = (taskId: string) =>
  apiPostJson(`/tasks/${encodeURIComponent(taskId)}/complete`, {});

export const suggestTaskAssignee = (taskId: string) =>
  apiGet<AssignmentSuggestion[]>(`/tasks/${encodeURIComponent(taskId)}/suggest-assignee`);

export const assignTask = (taskId: string, userId: string) =>
  apiPostJson(`/tasks/${encodeURIComponent(taskId)}/assign?user_id=${encodeURIComponent(userId)}`, {});

export const autoAssignTask = (taskId: string) =>
  apiPostJson(`/tasks/${encodeURIComponent(taskId)}/auto-assign`, {});
