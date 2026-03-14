"use client";

import { useMemo } from "react";
import { ResumePreview } from "@/components/preview/ResumePreview";
import { finalizeResume, previewFromText } from "@/lib/flaskApi";
import type { ResumeData } from "@/types/resume";
import { ResumeStoreProvider, useResumeStore } from "@/store/resumeStore";

export default function BuilderPage() {
  return (
    <ResumeStoreProvider>
      <BuilderInner />
    </ResumeStoreProvider>
  );
}

function BuilderInner() {
  const { state, dispatch } = useResumeStore();

  const canPreview = useMemo(() => {
    return !!state.resumeText.trim() && !!state.jobDescription.trim() && !state.busy;
  }, [state.resumeText, state.jobDescription, state.busy]);

  const canFinalize = useMemo(() => {
    return state.previewReady && !state.busy;
  }, [state.previewReady, state.busy]);

  async function onCheckMatch() {
    dispatch({ type: "setError", error: null });
    if (!state.resumeText.trim() || !state.jobDescription.trim()) {
      dispatch({ type: "setError", error: "Please paste your resume text and the job description." });
      return;
    }

    dispatch({ type: "setBusy", busy: true });
    try {
      const resp = await previewFromText({ resumeText: state.resumeText, jobDescription: state.jobDescription });

      const rp = resp.resume_preview || {};
      const nextResumeData: ResumeData = {
        name: rp.name || null,
        title: null,
        contact: rp.contact || {},
        summary: rp.summary || "",
        skills: rp.skills || [],
        projects: rp.projects || [],
        education: rp.education || [],
        experience: rp.experience || [],
        familiarity_exposure: rp.familiarity_exposure || [],
      };
      dispatch({ type: "setResumeData", resumeData: nextResumeData });

      const scores = resp.analysis?.scores || {};
      const gate = resp.analysis?.quality_gate || {};
      dispatch({
        type: "setPreview",
        payload: {
          previewReady: true,
          jobAnalysis: (resp.analysis?.job_analysis as Record<string, unknown>) || null,
          matchPct: (scores.match_percentage ?? null) as number | null,
          atsAlignmentScore: (scores.ats_alignment_score ?? null) as number | null,
          matchedSkills: (scores.matched_skills || []) as string[],
          missingSkills: (scores.missing_skills || []) as string[],
          gatePassed: (gate.passed ?? null) as boolean | null,
          gateScore: (gate.ats_gate_score ?? null) as number | null,
          gateCoverage: (gate.keyword_coverage ?? null) as number | null,
          gateSuggestions: (gate.suggestions || []) as string[],
        },
      });
      dispatch({ type: "setStep", step: 2 });
    } catch (e) {
      dispatch({ type: "setError", error: e instanceof Error ? e.message : String(e) });
    } finally {
      dispatch({ type: "setBusy", busy: false });
    }
  }

  async function onFinalize() {
    dispatch({ type: "setError", error: null });
    if (!state.previewReady) {
      dispatch({ type: "setError", error: "Please run Check Job Match first." });
      return;
    }

    dispatch({ type: "setBusy", busy: true });
    try {
      const resp = await finalizeResume({ approvedResumeJson: state.resumeData, jobAnalysis: state.jobAnalysis });
      dispatch({ type: "setFinalize", payload: { pdfReady: true, downloadUrl: resp.download_url } });
      dispatch({ type: "setStep", step: 4 });
    } catch (e) {
      dispatch({ type: "setError", error: e instanceof Error ? e.message : String(e) });
      dispatch({ type: "setStep", step: 3 });
    } finally {
      dispatch({ type: "setBusy", busy: false });
    }
  }

  return (
    <div style={{ padding: "18px 0 60px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1.2fr",
          gap: 14,
          alignItems: "start",
        }}
      >
        <section className="card" style={{ padding: 16 }}>
          <div style={{ display: "grid", gap: 10 }}>
            <div style={{ fontFamily: "var(--font-heading)", fontWeight: 900, fontSize: 20 }}>Resume Builder (v1)</div>
            <div className="muted" style={{ lineHeight: 1.55 }}>
              This is the new builder shell. It uses the existing Flask pipeline for preview and final PDF generation.
            </div>

            {state.error ? (
              <div
                style={{
                  border: "1px solid rgba(239,68,68,0.45)",
                  background: "rgba(239,68,68,0.10)",
                  borderRadius: 12,
                  padding: 10,
                  whiteSpace: "pre-wrap",
                }}
              >
                {state.error}
              </div>
            ) : null}

            <div
              style={{
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <StepPill active={state.step === 1}>1) Input</StepPill>
              <StepPill active={state.step === 2}>2) Preview</StepPill>
              <StepPill active={state.step === 3}>3) Approve</StepPill>
              <StepPill active={state.step === 4}>4) Download</StepPill>
            </div>

            <label className="muted" style={{ fontSize: 12 }}>
              Step 1 — Paste resume text
            </label>
            <textarea
              value={state.resumeText}
              onChange={(e) => {
                dispatch({ type: "setResumeText", resumeText: e.target.value });
                dispatch({ type: "resetAfterInputChange" });
              }}
              placeholder="Paste your resume text here..."
              style={textareaStyle}
              disabled={state.busy}
            />

            <label className="muted" style={{ fontSize: 12 }}>
              Step 1 — Paste job description
            </label>
            <textarea
              value={state.jobDescription}
              onChange={(e) => {
                dispatch({ type: "setJobDescription", jobDescription: e.target.value });
                dispatch({ type: "resetAfterInputChange" });
              }}
              placeholder="Paste the job description here..."
              style={textareaStyle}
              disabled={state.busy}
            />

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button disabled={!canPreview} onClick={onCheckMatch} style={primaryBtnStyle}>
                {state.busy ? "Working…" : "Check Job Match"}
              </button>
              <button
                disabled={!state.previewReady || state.busy}
                onClick={() => dispatch({ type: "setStep", step: 3 })}
                style={ghostBtnStyle}
              >
                Edit & Approve
              </button>
            </div>

            {state.previewReady ? (
              <div style={{ display: "grid", gap: 10, marginTop: 8 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <Metric label="Match %" value={state.matchPct !== null ? `${state.matchPct}%` : "--"} />
                  <Metric label="ATS alignment" value={state.atsAlignmentScore !== null ? String(state.atsAlignmentScore) : "--"} />
                </div>

                <div style={{ borderTop: "1px solid rgba(148,163,184,0.16)", paddingTop: 10 }}>
                  <div style={{ fontWeight: 800 }}>Missing skills (Exposure only)</div>
                  <div className="muted" style={{ fontSize: 12, lineHeight: 1.5, marginTop: 4 }}>
                    We never add fake experience. Only add missing skills to Exposure if you genuinely studied/practiced them.
                  </div>
                  <ul style={{ margin: "8px 0 0", paddingLeft: 18, lineHeight: 1.55 }}>
                    {state.missingSkills.slice(0, 16).map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ display: "grid", gap: 8 }}>
                  <div style={{ fontWeight: 800 }}>Finalize</div>
                  <div className="muted" style={{ fontSize: 12, lineHeight: 1.5 }}>
                    Step 3 → Step 4: Finalize generates the PDF only if the quality gate passes.
                  </div>
                  <button disabled={!canFinalize} onClick={onFinalize} style={primaryBtnStyle}>
                    {state.busy ? "Generating…" : "Finalize ATS Resume"}
                  </button>
                  {state.downloadUrl ? (
                    <a
                      href={state.downloadUrl}
                      style={{
                        display: "inline-block",
                        padding: "10px 12px",
                        borderRadius: 12,
                        border: "1px solid rgba(99,102,241,0.35)",
                        background: "rgba(99,102,241,0.10)",
                      }}
                    >
                      Download PDF
                    </a>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <section className="card" style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
            <div style={{ fontFamily: "var(--font-heading)", fontWeight: 900 }}>Live Preview</div>
            <div className="muted" style={{ fontSize: 12 }}>
              ATS-safe preview (single column)
            </div>
          </div>
          <ResumePreview data={state.resumeData} />
        </section>
      </div>
    </div>
  );
}

function StepPill({ active, children }: { active: boolean; children: React.ReactNode }) {
  return (
    <span
      style={{
        fontSize: 12,
        padding: "4px 10px",
        borderRadius: 999,
        border: active ? "1px solid rgba(99,102,241,0.55)" : "1px solid rgba(148,163,184,0.18)",
        background: active ? "rgba(99,102,241,0.14)" : "rgba(30,41,59,0.25)",
        color: active ? "var(--color-text-primary)" : "var(--color-text-secondary)",
      }}
    >
      {children}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: "1px solid rgba(148,163,184,0.16)", borderRadius: 12, padding: 10, background: "rgba(2,6,23,0.16)" }}>
      <div className="muted" style={{ fontSize: 12 }}>
        {label}
      </div>
      <div style={{ fontFamily: "var(--font-heading)", fontWeight: 900, fontSize: 22, marginTop: 4 }}>{value}</div>
    </div>
  );
}

const textareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: 140,
  resize: "vertical",
  borderRadius: 12,
  padding: 10,
  border: "1px solid rgba(148,163,184,0.18)",
  background: "rgba(2,6,23,0.22)",
  color: "var(--color-text-primary)",
  outline: "none",
  fontSize: 13,
  lineHeight: 1.45,
};

const primaryBtnStyle: React.CSSProperties = {
  border: "1px solid rgba(99,102,241,0.45)",
  background: "linear-gradient(180deg, rgba(99,102,241,0.95), rgba(79,70,229,0.85))",
  color: "white",
  padding: "10px 12px",
  borderRadius: 12,
  cursor: "pointer",
};

const ghostBtnStyle: React.CSSProperties = {
  border: "1px solid rgba(148,163,184,0.18)",
  background: "rgba(30,41,59,0.35)",
  color: "var(--color-text-primary)",
  padding: "10px 12px",
  borderRadius: 12,
  cursor: "pointer",
};
