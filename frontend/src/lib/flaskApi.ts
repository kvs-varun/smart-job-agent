import type { FinalizeResponse, PreviewResponse, ResumeData } from "@/types/resume";

export type JDMatchResponse = {
  match_score: number;
  skills_match: {
    matched: string[];
    missing: string[];
    additional: string[];
  };
  keyword_analysis: {
    resume_keywords: string[];
    jd_keywords: string[];
    overlap: string[];
    gaps: string[];
  };
  recommendations: string[];
};

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

export async function analyzeJDMatch(resumeData: ResumeData, jobDescription: string): Promise<JDMatchResponse> {
  const parts: string[] = [];
  const name = resumeData.contact?.name || "";
  const jobTitle = resumeData.contact?.jobTitle || "";
  const header = [name, jobTitle].filter(Boolean).join(" — ");
  if (header) parts.push(header);
  if (resumeData.summary) parts.push(resumeData.summary);
  if (Array.isArray(resumeData.experience) && resumeData.experience.length) {
    for (const e of resumeData.experience) {
      const line = `${e.title || ""}${e.company ? ` at ${e.company}` : ""}: ${e.description || ""}`.trim();
      if (line && line !== ":") parts.push(line);
    }
  }
  if (Array.isArray(resumeData.skills) && resumeData.skills.length) {
    parts.push(resumeData.skills.join(", "));
  }
  if (Array.isArray(resumeData.education) && resumeData.education.length) {
    for (const ed of resumeData.education) {
      const line = [ed.degree, ed.institution, ed.field].filter(Boolean).join(" — ");
      if (line) parts.push(line);
    }
  }

  const resumeText = parts.filter(Boolean).join("\n\n");

  const res = await fetch(`${FLASK_PROXY_BASE}/agent/analyze-resume-jd-match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resumeText, jobDescription }),
  });

  const rawText = await res.text();
  let data: JDMatchResponse | { error?: string };
  try {
    data = JSON.parse(rawText) as JDMatchResponse | { error?: string };
  } catch {
    throw new Error(res.ok ? "Invalid server response" : `Analyze failed (${res.status})`);
  }

  if (!res.ok) {
    throw new Error("error" in data && data.error ? data.error : `Analyze failed (${res.status})`);
  }
  return data as JDMatchResponse;
}
