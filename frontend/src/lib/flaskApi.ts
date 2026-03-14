import type { FinalizeResponse, PreviewResponse, ResumeData } from "@/types/resume";

export const FLASK_PROXY_BASE = "/flask";

export async function previewFromText(input: {
  resumeText: string;
  jobDescription: string;
}): Promise<PreviewResponse> {
  const res = await fetch(`${FLASK_PROXY_BASE}/agent/preview-resume-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resumeText: input.resumeText, jobDescription: input.jobDescription, role_preference: "auto" }),
  });

  const data = (await res.json()) as PreviewResponse | { error?: string };
  if (!res.ok) {
    throw new Error("error" in data && data.error ? data.error : `Preview failed (${res.status})`);
  }
  return data as PreviewResponse;
}

export async function finalizeResume(input: {
  approvedResumeJson: ResumeData;
  jobAnalysis: Record<string, unknown> | null;
}): Promise<FinalizeResponse> {
  const res = await fetch(`${FLASK_PROXY_BASE}/agent/finalize-resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved_resume_json: input.approvedResumeJson, job_analysis: input.jobAnalysis || {} }),
  });

  const data = (await res.json()) as FinalizeResponse | { error?: string };
  if (!res.ok) {
    throw new Error("error" in data && data.error ? data.error : `Finalize failed (${res.status})`);
  }
  return data as FinalizeResponse;
}
