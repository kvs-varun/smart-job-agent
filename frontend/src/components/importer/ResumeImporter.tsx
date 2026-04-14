"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { Check, FileText, Upload, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import { EMPTY_RESUME, makeId } from "@/types/resume";
import type {
  EducationEntry,
  ExperienceEntry,
  PreviewResponse,
  ProjectEntry,
  ResumeData,
} from "@/types/resume";

type ParseResult = {
  resumeData: ResumeData;
  parseWarnings: string[];
};

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

  React.useEffect(() => {
    if (!open) {
      setDragOver(false);
      setFile(null);
      setBusy(false);
      setParsed(null);
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
    try {
      const form = new FormData();
      form.append("resumeFile", file);
      form.append("jobDescription", "");
      form.append("role_preference", "auto");

      const res = await fetch(`/flask/agent/preview-resume-upload`, {
        method: "POST",
        body: form,
      });

      const data = (await res.json()) as PreviewResponse | { error?: string };
      if (!res.ok) {
        throw new Error(
          "error" in data && data.error
            ? data.error
            : `Parse failed (${res.status})`
        );
      }

      const resp = data as PreviewResponse;
      const rp = resp.resume_preview || ({} as any);

      const experience: ExperienceEntry[] = Array.isArray(rp.experience)
        ? (rp.experience as unknown[])
            .filter((x) => typeof x === "string")
            .map((desc) => ({
              id: makeId(),
              title: "",
              company: "",
              startDate: "",
              endDate: "",
              current: false,
              location: "",
              description: String(desc),
            }))
        : [];

      const education: EducationEntry[] = Array.isArray(rp.education)
        ? (rp.education as unknown[])
            .filter((x) => typeof x === "string")
            .map((line) => ({
              id: makeId(),
              degree: String(line),
              institution: "",
              field: "",
              startYear: "",
              endYear: "",
              grade: "",
            }))
        : [];

      const projects: ProjectEntry[] = Array.isArray(rp.projects)
        ? (rp.projects as unknown[])
            .filter((x) => typeof x === "string")
            .map((name) => ({
              id: makeId(),
              name: String(name),
              description: "",
              techStack: [],
              github: "",
              demo: "",
            }))
        : [];

      const resumeData: ResumeData = {
        ...EMPTY_RESUME,
        contact: {
          ...EMPTY_RESUME.contact,
          name: (rp.name || "") as string,
          email: (rp.contact?.email || "") as string,
          phone: (rp.contact?.phone || "") as string,
          location: (rp.contact?.location || "") as string,
          linkedin: (rp.contact?.linkedinUrl || "") as string,
          github: (rp.contact?.githubUrl || "") as string,
          portfolio: (rp.contact?.portfolioUrl || "") as string,
        },
        summary: (rp.summary || "") as string,
        skills: Array.isArray(rp.skills)
          ? ((rp.skills as unknown[]).filter(
              (x) => typeof x === "string"
            ) as string[])
          : [],
        experience,
        education,
        projects,
      };

      const result: ParseResult = {
        resumeData,
        parseWarnings: (rp.parse_warnings || []) as string[],
      };

      setParsed(result);
    } catch (e) {
      toast(
        e instanceof Error
          ? e.message
          : "Couldn't read this file. Try a different PDF or paste your resume text instead."
      );
    } finally {
      setBusy(false);
    }
  }

  // ─── Nothing renders when modal is closed ───────────────────────────────────
  if (!open || typeof window === "undefined") return null;

  // ─── createPortal renders directly into document.body ───────────────────────
  // This bypasses ALL parent transforms (including PageTransition framer-motion)
  // so position:fixed works relative to the real screen, not any parent element.
  return createPortal(
    <>
      {/* ── BACKDROP ── covers the full real screen ── */}
      <div
        onClick={() => onOpenChange(false)}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 200,
          backgroundColor: "rgba(0, 0, 0, 0.75)",
          backdropFilter: "blur(6px)",
          WebkitBackdropFilter: "blur(6px)",
        }}
      />

      {/* ── CENTERING WRAPPER — flexbox centers the modal, no transform conflict ── */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 201,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 24px",
          pointerEvents: "none",
        }}
      >
      {/* ── MODAL ── Framer Motion only handles opacity/scale/y, not positioning ── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.98, y: 8 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        style={{
          pointerEvents: "auto",
          width: "100%",
          maxWidth: "560px",
          maxHeight: "calc(100vh - 80px)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          backgroundColor: "#1E293B",
          border: "1px solid #334155",
          borderRadius: "16px",
          boxShadow: "0 25px 60px rgba(0,0,0,0.6)",
          outline: "none",
        }}
      >
        {/* ── HEADER — never scrolls ── */}
        <div
          style={{
            flexShrink: 0,
            padding: "24px 24px 16px",
            borderBottom: "1px solid #334155",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2
            style={{
              fontFamily: "Plus Jakarta Sans, Inter, sans-serif",
              fontWeight: 700,
              fontSize: "20px",
              color: "#F8FAFC",
              margin: 0,
            }}
          >
            Import Your Resume
          </h2>
          <button
            onClick={() => onOpenChange(false)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#94A3B8",
              padding: "4px",
              display: "flex",
              alignItems: "center",
            }}
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* ── SCROLLABLE CONTENT ── */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
          {parsed ? (
            /* ── PARSE SUCCESS STATE ── */
            <div
              style={{
                borderRadius: "16px",
                border: "1px solid #334155",
                backgroundColor: "rgba(36,48,68,0.4)",
                padding: "20px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  color: "#6EE7B7",
                  fontWeight: 600,
                  fontSize: "15px",
                }}
              >
                <Check size={20} />
                Resume Parsed Successfully
              </div>
              <div
                style={{
                  marginTop: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                }}
              >
                <Row label="Name" value={parsed.resumeData.contact?.name || "—"} />
                <Row label="Email" value={parsed.resumeData.contact?.email || "—"} />
                <Row
                  label="Experiences detected"
                  value={String(parsed.resumeData.experience?.length || 0)}
                />
                <Row
                  label="Education entries"
                  value={String(parsed.resumeData.education?.length || 0)}
                />
                <Row
                  label="Skills detected"
                  value={String(parsed.resumeData.skills?.length || 0)}
                />
                <Row
                  label="Projects detected"
                  value={String(parsed.resumeData.projects?.length || 0)}
                />
              </div>
              {parsed.parseWarnings.length > 0 && (
                <div
                  style={{
                    marginTop: "16px",
                    fontSize: "12px",
                    color: "#FCD34D",
                  }}
                >
                  ⚠ {parsed.parseWarnings[0]}
                </div>
              )}
            </div>
          ) : (
            /* ── UPLOAD STATE ── */
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
                onDragEnter={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDragOver(true);
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDragOver(true);
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDragOver(false);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDragOver(false);
                  const f = e.dataTransfer.files?.[0] || null;
                  setSelectedFile(f);
                }}
                className={cn(
                  "w-full rounded-2xl border border-dashed border-[#334155] px-6 py-10 text-center transition-colors",
                  dragOver
                    ? "border-[#6366F1] bg-[#6366F1]/05"
                    : "bg-[#0F172A]/25 hover:border-[#6366F1]"
                )}
              >
                <Upload className="mx-auto h-10 w-10 text-[#6366F1]" />
                <div className="mt-4 font-heading font-semibold text-white text-lg">
                  Drop your PDF or DOCX here
                </div>
                <div className="mt-1 text-sm text-[#94A3B8]">
                  or click to browse · Max 5MB
                </div>
                <div className="mt-4 flex items-center justify-center gap-2">
                  <Badge variant="muted">PDF</Badge>
                  <Badge variant="muted">DOCX</Badge>
                </div>
              </button>

              {/* Selected file info */}
              {file && (
                <div className="mt-4 rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-[#94A3B8]" />
                      <div>
                        <div className="text-sm font-medium text-white">
                          {file.name}
                        </div>
                        <div className="text-xs text-[#64748B]">
                          {Math.round(file.size / 1024)} KB
                        </div>
                      </div>
                    </div>
                    <Button variant="primary" loading={busy} onClick={onParse}>
                      {busy ? "Reading..." : "Parse Resume →"}
                    </Button>
                  </div>
                </div>
              )}

              <div className="mt-4 text-xs text-[#64748B]">
                If parsing fails, you can paste your resume text in the Builder
                export step.
              </div>
            </div>
          )}
        </div>

        {/* ── FOOTER — never scrolls, always visible ── */}
        <div
          style={{
            flexShrink: 0,
            padding: "16px 24px",
            borderTop: "1px solid #334155",
            backgroundColor: "#1E293B",
            display: "flex",
            gap: "12px",
            justifyContent: "flex-end",
          }}
        >
          {parsed ? (
            <>
              <Button variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  onImport(parsed);
                  onOpenChange(false);
                  toast("Resume imported into builder ✓");
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
                Parse Resume →
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
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
        fontSize: "13px",
      }}
    >
      <span style={{ color: "#94A3B8" }}>✓ {label}:</span>
      <span
        style={{
          color: "#F8FAFC",
          fontWeight: 600,
          textAlign: "right",
          wordBreak: "break-all",
        }}
      >
        {value}
      </span>
    </div>
  );
}
