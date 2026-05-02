/**
 * Smart Job Agent V2 — FastAPI client
 * All calls proxy through Next.js: /api/v2/* → http://localhost:8000/v2/*
 */

const BASE = "/api/v2";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AgentBuildResponse {
  ok: boolean;
  session_id: string;
  download_url: string | null;
  pdf_path: string | null;
  final_resume: Record<string, unknown> | null;
  tailored_resume: Record<string, unknown> | null;  // alias of final_resume — used by JD tailor
  tailoring_plan: string[];
  quality_gate: QualityGate | null;
  jd_match_score: number | null;
  jd_match_details: JDMatchDetails | null;
  caution_issued: boolean;
  cold_email_output: ColdEmailOutput | null;
  resume_score: number | null;
  score_breakdown: ScoreBreakdown | null;
  mentor_feedback: string | null;
  mentor_recommendations: MentorResource[] | null;
  auto_apply_results: AutoApplyResult[] | null;
  change_log: ChangeLogEntry[] | null;
  agent_health_map: Record<string, string>;
  supervisor_interventions: string[];
}

export interface QualityGate {
  passed: boolean;
  ats_score: number;
  issues: string[];
  suggestions: string[];
}

export interface JDMatchDetails {
  match_score: number;
  skill_match_pct: number;
  keyword_coverage_pct: number;
  matched_skills: string[];
  missing_skills: string[];
  hard_gaps: string[];
  caution_issued: boolean;
  callback_probability_pct: number;
  caution_message: string | null;
  company_type: "service" | "product" | "startup" | "unknown";
  tailoring_plan: TailoringStep[];
  recommendations: string[];
  strengths: string[];
  verdict: string;
}

export interface TailoringStep {
  action: string;
  section: string;
  specific_change: string;
}

export interface ColdEmailOutput {
  subject: string;
  body: string;
  framework: string;
  tone: string;
  word_count: number;
  mailto_link: string;
  gmail_url: string;
  cliches_found: string[];
}

export interface ScoreBreakdown {
  ats_compliance: number;
  content_quality: number;
  skill_alignment: number;
  profile_strength: number;
  presentation: number;
}

export interface MentorResource {
  title: string;
  url: string;
  provider: string;
  duration_hours: number;
  free: boolean;
  relevance_score: number;
  skill_gap: string;
}

export interface AutoApplyResult {
  job_title?: string;
  company?: string;
  url?: string;
  platform?: string;
  match_score?: number;
  status: "submitted" | "failed" | "skipped" | "blocked";
  reason?: string;
  error?: string;
}

export interface ChangeLogEntry {
  agent: string;
  action: string;
  [key: string]: unknown;
}

export interface JDMatchRequest {
  resume_text: string;
  job_description: string;
  selected_template?: string;
}

export interface ColdEmailRequest {
  resume_text?: string;
  resume_data?: Record<string, unknown>;
  recruiter_email: string;
  candidate_email?: string;
  company_name: string;
  role_title: string;
  job_description?: string;
  recruiter_name?: string;
}

export interface ScoreRequest {
  resume_data: Record<string, unknown>;
  job_description?: string;
}

export interface AutoApplyPreferences {
  target_roles?: string[];
  location?: string;
  experience_level?: string;
  platforms?: ("linkedin" | "naukri")[];
  max_applications?: number;
}

// ── API functions ─────────────────────────────────────────────────────────────

/** Full 8-agent pipeline from pasted resume text */
export async function buildResumeFromText(input: {
  resume_text: string;
  job_description?: string;
  selected_template?: string;
  role_preference?: string;
  candidate_email?: string;
  recruiter_email?: string;
  company_name?: string;
  role_title?: string;
  auto_apply_enabled?: boolean;
}): Promise<AgentBuildResponse> {
  return post("/agent/build-resume", input);
}

// ── Parsed resume structure returned by V2 LLM parser ────────────────────────
export interface ParsedResumeV2 {
  contact: {
    name: string;
    email: string;
    phone: string;
    location: string;
    linkedin: string;
    github: string;
    portfolio?: string;
    jobTitle: string;
  };
  summary: string;
  skills: string[];
  experience: Array<{
    title: string;
    company: string;
    location: string;
    startDate: string;
    endDate: string;
    description: string;
  }>;
  projects: Array<{
    name: string;
    description: string;
    techStack: string[];
    github: string;
    demo: string;
  }>;
  education: Array<{
    institution: string;
    degree: string;
    field: string;
    grade: string;
    startDate: string;
    endDate: string;
  }>;
  certifications?: Array<{
    name: string;
    issuer: string;
    issuedDate: string;
    expiryDate: string;
    credentialID: string;
    credentialURL: string;
  }>;
  achievements?: Array<{
    title: string;
    description: string;
    date: string;
  }>;
  openSource?: Array<{
    project: string;
    contribution: string;
    github: string;
  }>;
  publications?: Array<{
    title: string;
    publisher: string;
    date: string;
    url: string;
  }>;
  volunteering?: Array<{
    role: string;
    organization: string;
    description: string;
    startDate: string;
    endDate: string;
  }>;
  languages?: Array<{
    language: string;
    proficiency: string;
  }>;
}

/**
 * LLM-powered resume parsing (V2).
 * Sends file to Gemini for intelligent structured extraction.
 * Returns clean, properly structured data — no skills contamination.
 */
export async function parseResumeFile(file: File): Promise<{
  ok: boolean;
  parsed: ParsedResumeV2;
  filename: string;
  parse_warnings: string[];
}> {
  const form = new FormData();
  form.append("file", file);
  return postForm("/agent/parse-resume", form);
}

/** Full 8-agent pipeline from uploaded PDF/DOCX */
export async function buildResumeFromUpload(
  file: File,
  options: {
    job_description?: string;
    selected_template?: string;
    role_preference?: string;
    candidate_email?: string;
    recruiter_email?: string;
    company_name?: string;
    role_title?: string;
  }
): Promise<AgentBuildResponse> {
  const form = new FormData();
  form.append("file", file);
  Object.entries(options).forEach(([k, v]) => {
    if (v !== undefined) form.append(k, String(v));
  });
  return postForm("/agent/build-resume-upload", form);
}

/** Full 8-agent pipeline from structured resume data (no file upload needed) */
export async function buildResumeFromData(input: {
  resume_data: Record<string, unknown>;
  job_description?: string;
  selected_template?: string;
  role_preference?: string;
}): Promise<AgentBuildResponse> {
  return post("/agent/build-resume", input);
}

/** Generate PDF from approved resume JSON (skip agent pipeline) */
export async function finalizeResumeV2(input: {
  resume_data: Record<string, unknown>;
  selected_template?: string;
  session_id?: string;
}): Promise<{ ok: boolean; download_url: string; pdf_path: string }> {
  return post("/agent/finalize-resume", input);
}

/** Fast AI summary writer — role-targeted, assertive, recruiter-grade */
export async function generateSummary(input: {
  resume_data?: Record<string, unknown>;
  existing_summary?: string;
  job_description?: string;
  role_title?: string;
  target_role?: string;        // role selector value — takes priority over role_title
  consent_given?: boolean;     // GDPR: must be true before AI processing
}): Promise<{ ok: boolean; summary: string }> {
  return post("/agent/generate-summary", input);
}

/**
 * Full JD-specific resume rewrite — runs all agents, returns tailored resume + PDF.
 * Used by JD Match "Rewrite Resume for this JD" button.
 */
export async function tailorResumeForJD(input: {
  resume_data: Record<string, unknown>;
  job_description: string;
  selected_template?: string;
  role_preference?: string;
}): Promise<AgentBuildResponse> {
  return post("/agent/jd-tailor", input);
}

/** Agent 3 only — JD match without full pipeline */
export async function analyzeJDMatchV2(input: JDMatchRequest): Promise<{
  ok: boolean;
  session_id: string;
  match_score: number;
  jd_match_details: JDMatchDetails;
  caution_issued: boolean;
  tailoring_plan: TailoringStep[];
}> {
  return post("/agent/jd-match", input);
}

/** Agent 4 only — cold email generation */
export async function generateColdEmailV2(input: ColdEmailRequest): Promise<
  ColdEmailOutput & { ok: boolean; session_id: string }
> {
  return post("/agent/cold-email", input);
}

/** Agent 7 only — resume scoring + mentor recommendations */
export async function scoreResume(input: ScoreRequest): Promise<{
  ok: boolean;
  session_id: string;
  resume_score: number;
  score_breakdown: ScoreBreakdown;
  mentor_feedback: string;
  mentor_recommendations: MentorResource[];
}> {
  return post("/agent/score", input);
}

/** Agent 8 — trigger automated job applications */
export async function startAutoApply(input: {
  resume_data: Record<string, unknown>;
  resume_score: number;
  preferences: AutoApplyPreferences;
}): Promise<{ ok: boolean; session_id: string; results: AutoApplyResult[] }> {
  return post("/agent/auto-apply", input);
}

/** Poll agent session state */
export async function getSession(sessionId: string) {
  return get(`/agent/session/${sessionId}`);
}

/** Tracker — PostgreSQL backed */
export async function trackerAddV2(app: {
  company: string;
  role: string;
  job_url?: string;
  status?: string;
  notes?: string;
  session_id?: string;
}) {
  return post("/tracker/add", app);
}

export async function trackerListV2(sessionId?: string) {
  const qs = sessionId ? `?session_id=${sessionId}` : "";
  return get(`/tracker/list${qs}`);
}

export async function trackerUpdateV2(id: string, status: string, notes?: string) {
  return post("/tracker/update", { id, status, notes });
}

/** V2 health check */
export async function checkV2Health() {
  return get("/health");
}
