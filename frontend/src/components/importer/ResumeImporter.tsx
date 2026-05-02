"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { Brain, Check, FileText, Sparkles, Upload, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import { EMPTY_RESUME, makeId } from "@/types/resume";
import type {
  AchievementEntry,
  CertificationEntry,
  EducationEntry,
  ExperienceEntry,
  LanguageEntry,
  OpenSourceEntry,
  ProjectEntry,
  PublicationEntry,
  ResumeData,
  VolunteeringEntry,
} from "@/types/resume";
import { parseResumeFile, type ParsedResumeV2 } from "@/lib/agentApi";

type ParseResult = {
  resumeData: ResumeData;
  parseWarnings: string[];
};

/** Map V2 LLM-parsed structure to frontend ResumeData */
function mapParsedV2ToResumeData(parsed: ParsedResumeV2): ResumeData {
  const experience: ExperienceEntry[] = (parsed.experience || []).map((exp) => ({
    id: makeId(),
    title: exp.title || "",
    company: exp.company || "",
    startDate: exp.startDate || "",
    endDate: exp.endDate || "",
    current: (exp.endDate || "").toLowerCase().includes("present"),
    location: exp.location || "",
    description: exp.description || "",
  }));

  const education: EducationEntry[] = (parsed.education || []).map((edu) => ({
    id: makeId(),
    degree: edu.degree || "",
    institution: edu.institution || "",
    field: edu.field || "",
    startYear: edu.startDate || "",
    endYear: edu.endDate || "",
    grade: edu.grade || "",
  }));

  const projects: ProjectEntry[] = (parsed.projects || []).map((proj) => ({
    id: makeId(),
    name: proj.name || "",
    description: proj.description || "",
    techStack: Array.isArray(proj.techStack) ? proj.techStack : [],
    github: proj.github || "",
    demo: proj.demo || "",
  }));

  const certifications: CertificationEntry[] = (parsed.certifications || []).map((c) => ({
    id: makeId(),
    name: c.name || "",
    issuer: c.issuer || "",
    issuedDate: c.issuedDate || "",
    expiryDate: c.expiryDate || "",
    credentialID: c.credentialID || "",
    credentialURL: c.credentialURL || "",
  }));

  const achievements: AchievementEntry[] = (parsed.achievements || []).map((a) => ({
    id: makeId(),
    title: a.title || "",
    description: a.description || "",
    date: a.date || "",
  }));

  const openSource: OpenSourceEntry[] = (parsed.openSource || []).map((o) => ({
    id: makeId(),
    project: o.project || "",
    contribution: o.contribution || "",
    github: o.github || "",
  }));

  const publications: PublicationEntry[] = (parsed.publications || []).map((p) => ({
    id: makeId(),
    title: p.title || "",
    publisher: p.publisher || "",
    date: p.date || "",
    url: p.url || "",
  }));

  const volunteering: VolunteeringEntry[] = (parsed.volunteering || []).map((v) => ({
    id: makeId(),
    role: v.role || "",
    organization: v.organization || "",
    description: v.description || "",
    startDate: v.startDate || "",
    endDate: v.endDate || "",
  }));

  const languages: LanguageEntry[] = (parsed.languages || []).map((l) => ({
    id: makeId(),
    language: l.language || "",
    proficiency: l.proficiency || "",
  }));

  return {
    ...EMPTY_RESUME,
    contact: {
      ...EMPTY_RESUME.contact,
      name: parsed.contact?.name || "",
      email: parsed.contact?.email || "",
      phone: parsed.contact?.phone || "",
      location: parsed.contact?.location || "",
      linkedin: parsed.contact?.linkedin || "",
      github: parsed.contact?.github || "",
      jobTitle: parsed.contact?.jobTitle || "",
      portfolio: parsed.contact?.portfolio || "",
    },
    summary: parsed.summary || "",
    skills: Array.isArray(parsed.skills) ? parsed.skills.filter(Boolean) : [],
    experience,
    education,
    projects,
    certifications,
    achievements,
    openSource,
    publications,
    volunteering,
    languages,
  };
}

export function ResumeImporter({
  open,
  onOpenChange,
  onImport,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (result: ParseResult) => void;
}) {
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [file, setFile] = React.useState<File | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [parsed, setParsed] = React.useState<ParseResult | null>(null);
  const [parseStage, setParseStage] = React.useState<string>("");

  React.useEffect(() => {
    if (!open) {
      setDragOver(false);
      setFile(null);
      setBusy(false);
      setParsed(null);
      setParseStage("");
    }
  }, [open]);

  function chooseFile() {
    inputRef.current?.click();
  }

  function setSelectedFile(f: File | null) {
    if (!f) return;
    if (f.size > 5 * 1024 * 1024) {
      toast("File exceeds 5MB limit. Please compress or use a different file.");
      return;
    }
    const ext = (f.name.split(".").pop() || "").toLowerCase();
    if (ext !== "pdf" && ext !== "docx") {
      toast("Only PDF and DOCX files are supported.");
      return;
    }
    setFile(f);
  }

  async function onParse() {
    if (!file) return;
    setBusy(true);
    setParsed(null);

    try {
      setParseStage("Extracting text from your resume...");
      await new Promise((r) => setTimeout(r, 300));

      setParseStage("Gemini AI is reading your resume...");

      let response;
      try {
        response = await parseResumeFile(file);
      } catch (fetchErr) {
        // Diagnose connection vs 404 vs other errors
        const errMsg = fetchErr instanceof Error ? fetchErr.message : String(fetchErr);
        if (errMsg.includes("Not Found") || errMsg.includes("404")) {
          throw new Error(
            "Backend not updated — restart uvicorn: python -m uvicorn backend_v2.main:app --port 8000 --reload"
          );
        }
        if (errMsg.includes("fetch") || errMsg.includes("network") || errMsg.includes("ECONNREFUSED")) {
          throw new Error(
            "V2 backend is not running. Start it: python -m uvicorn backend_v2.main:app --port 8000 --reload"
          );
        }
        throw fetchErr;
      }

      if (!response || !response.parsed) {
        throw new Error("AI parser returned empty result. Try a different file.");
      }

      setParseStage("Structuring your data...");
      await new Promise((r) => setTimeout(r, 200));

      const resumeData = mapParsedV2ToResumeData(response.parsed);

      const hasContent =
        resumeData.contact.name ||
        resumeData.skills.length > 0 ||
        resumeData.experience.length > 0;

      if (!hasContent) {
        throw new Error(
          "Could not extract content from this file. Try a text-based PDF (not a scanned image)."
        );
      }

      setParsed({
        resumeData,
        parseWarnings: response.parse_warnings || [],
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Parse failed. Check the browser console for details.";
      toast(msg);
      console.error("[ResumeImporter] Parse error:", e);
    } finally {
      setBusy(false);
      setParseStage("");
    }
  }

  if (!open || typeof window === "undefined") return null;

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        onClick={() => onOpenChange(false)}
        style={{
          position: "fixed", inset: 0, zIndex: 200,
          backgroundColor: "rgba(0,0,0,0.75)",
          backdropFilter: "blur(6px)",
          WebkitBackdropFilter: "blur(6px)",
        }}
      />

      {/* Centering wrapper */}
      <div
        style={{
          position: "fixed", inset: 0, zIndex: 201,
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: "40px 24px", pointerEvents: "none",
        }}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 8 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          style={{
            pointerEvents: "auto", width: "100%", maxWidth: "560px",
            maxHeight: "calc(100vh - 80px)", overflow: "hidden",
            display: "flex", flexDirection: "column",
            backgroundColor: "#1E293B", border: "1px solid #334155",
            borderRadius: "16px", boxShadow: "0 25px 60px rgba(0,0,0,0.6)",
          }}
        >
          {/* Header */}
          <div style={{
            flexShrink: 0, padding: "24px 24px 16px",
            borderBottom: "1px solid #334155",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <div>
              <h2 style={{
                fontFamily: "Plus Jakarta Sans, Inter, sans-serif",
                fontWeight: 700, fontSize: "20px", color: "#F8FAFC", margin: 0,
              }}>
                Import Your Resume
              </h2>
              <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#6366F1" }}>
                <Brain size={11} style={{ display: "inline", marginRight: 4 }} />
                Powered by Gemini AI — intelligent section extraction
              </p>
            </div>
            <button
              onClick={() => onOpenChange(false)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                color: "#94A3B8", padding: "4px", display: "flex", alignItems: "center",
              }}
              aria-label="Close"
            >
              <X size={20} />
            </button>
          </div>

          {/* Scrollable content */}
          <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
            {parsed ? (
              /* ── Parse success ── */
              <div style={{
                borderRadius: "16px", border: "1px solid #1D4ED8",
                backgroundColor: "rgba(29,78,216,0.08)", padding: "20px",
              }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: "8px",
                  color: "#6EE7B7", fontWeight: 600, fontSize: "15px",
                }}>
                  <Check size={20} />
                  AI Parsing Complete
                </div>
                <p style={{ margin: "8px 0 16px", fontSize: "12px", color: "#94A3B8" }}>
                  Gemini successfully extracted your resume into structured sections.
                  Review the counts below, then click Import.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  <Row label="Name" value={parsed.resumeData.contact?.name || "—"} />
                  <Row label="Email" value={parsed.resumeData.contact?.email || "—"} />
                  <Row label="Skills detected" value={`${parsed.resumeData.skills?.length || 0} items`} />
                  <Row label="Experience entries" value={`${parsed.resumeData.experience?.length || 0} roles`} />
                  <Row label="Projects" value={`${parsed.resumeData.projects?.length || 0} projects`} />
                  <Row label="Education" value={`${parsed.resumeData.education?.length || 0} entries`} />
                </div>

                {/* Skills preview */}
                {(parsed.resumeData.skills || []).length > 0 && (
                  <div style={{ marginTop: "16px" }}>
                    <div style={{ fontSize: "11px", color: "#64748B", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      Skills Preview
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                      {parsed.resumeData.skills.slice(0, 12).map((s) => (
                        <span key={s} style={{
                          padding: "2px 8px", borderRadius: "12px", fontSize: "11px",
                          backgroundColor: "#1E3A5F", color: "#93C5FD", border: "1px solid #1D4ED8",
                        }}>
                          {s}
                        </span>
                      ))}
                      {parsed.resumeData.skills.length > 12 && (
                        <span style={{ fontSize: "11px", color: "#64748B", padding: "2px 4px" }}>
                          +{parsed.resumeData.skills.length - 12} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {parsed.parseWarnings.length > 0 && (
                  <div style={{ marginTop: "12px", fontSize: "12px", color: "#FCD34D" }}>
                    ⚠ {parsed.parseWarnings[0]}
                  </div>
                )}
              </div>
            ) : (
              /* ── Upload state ── */
              <div>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0] || null;
                    setSelectedFile(f);
                  }}
                />

                {/* Drop zone */}
                <button
                  type="button"
                  onClick={chooseFile}
                  onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); }}
                  onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); }}
                  onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setDragOver(false); }}
                  onDrop={(e) => {
                    e.preventDefault(); e.stopPropagation(); setDragOver(false);
                    const f = e.dataTransfer.files?.[0] || null;
                    setSelectedFile(f);
                  }}
                  className={cn(
                    "w-full rounded-2xl border border-dashed px-6 py-10 text-center transition-colors",
                    dragOver
                      ? "border-[#6366F1] bg-[#6366F1]/10"
                      : "border-[#334155] bg-[#0F172A]/25 hover:border-[#6366F1]"
                  )}
                >
                  <div style={{
                    width: 56, height: 56, borderRadius: "50%",
                    background: "linear-gradient(135deg, #4F46E5, #7C3AED)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    margin: "0 auto 16px",
                  }}>
                    <Upload size={24} color="white" />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: "18px", color: "#F8FAFC", marginBottom: 4 }}>
                    Drop your PDF or DOCX here
                  </div>
                  <div style={{ fontSize: "13px", color: "#94A3B8", marginBottom: 16 }}>
                    or click to browse · Max 5MB
                  </div>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                    <Badge variant="muted">PDF</Badge>
                    <Badge variant="muted">DOCX</Badge>
                  </div>
                </button>

                {/* AI feature callout */}
                <div style={{
                  marginTop: 12, padding: "10px 14px",
                  borderRadius: 10, border: "1px solid #312E81",
                  background: "rgba(99,102,241,0.06)",
                  display: "flex", gap: 8, alignItems: "flex-start",
                }}>
                  <Sparkles size={14} color="#818CF8" style={{ marginTop: 2, flexShrink: 0 }} />
                  <div style={{ fontSize: "12px", color: "#A5B4FC" }}>
                    <strong style={{ color: "#818CF8" }}>Gemini AI Parser</strong> — Unlike basic text extraction,
                    our AI correctly identifies every section, structures your experience with title/company/dates,
                    and prevents skills contamination from experience bullets.
                  </div>
                </div>

                {/* Selected file info */}
                {file && (
                  <div style={{
                    marginTop: 16, borderRadius: 12, border: "1px solid #334155",
                    background: "rgba(36,48,68,0.4)", padding: 16,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <FileText size={20} color="#94A3B8" />
                        <div>
                          <div style={{ fontSize: "13px", fontWeight: 600, color: "#F8FAFC" }}>{file.name}</div>
                          <div style={{ fontSize: "11px", color: "#64748B" }}>{Math.round(file.size / 1024)} KB</div>
                        </div>
                      </div>
                    </div>
                    {busy && parseStage && (
                      <div style={{
                        marginTop: 12, padding: "8px 12px", borderRadius: 8,
                        background: "rgba(99,102,241,0.1)", border: "1px solid #4338CA",
                      }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          >
                            <Brain size={14} color="#818CF8" />
                          </motion.div>
                          <span style={{ fontSize: "12px", color: "#A5B4FC" }}>{parseStage}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div style={{ marginTop: 12, fontSize: "11px", color: "#64748B" }}>
                  If parsing fails, you can paste your resume text in the Builder or manually fill each section.
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div style={{
            flexShrink: 0, padding: "16px 24px",
            borderTop: "1px solid #334155", backgroundColor: "#1E293B",
            display: "flex", gap: "12px", justifyContent: "flex-end",
          }}>
            {parsed ? (
              <>
                <Button variant="ghost" onClick={() => setParsed(null)}>
                  Re-upload
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    onImport(parsed);
                    onOpenChange(false);
                    toast("✓ Resume imported — AI-structured data filled into all sections");
                  }}
                >
                  Import to Builder →
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" onClick={() => onOpenChange(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={onParse}
                  loading={busy}
                  disabled={!file}
                >
                  {busy ? "AI Parsing..." : "Parse with AI →"}
                </Button>
              </>
            )}
          </div>
        </motion.div>
      </div>
    </>,
    document.body
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex", alignItems: "center",
      justifyContent: "space-between", gap: "16px", fontSize: "13px",
    }}>
      <span style={{ color: "#94A3B8" }}>✓ {label}:</span>
      <span style={{ color: "#F8FAFC", fontWeight: 600, textAlign: "right", wordBreak: "break-all" }}>
        {value}
      </span>
    </div>
  );
}
