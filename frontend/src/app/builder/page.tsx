"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  Brain,
  Briefcase,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  FileText,
  FolderOpen,
  Github,
  GraduationCap,
  Layout,
  Linkedin,
  Mail,
  MapPin,
  Phone,
  Plus,
  Sparkles,
  Trash2,
  User,
  X,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { ATSMinimal } from "@/components/templates/ATSMinimal";
import { ATSScoreCard } from "@/components/ats/ATSScoreCard";
import { ResumeImporter } from "@/components/importer/ResumeImporter";
import type { EducationEntry, ExperienceEntry, ProjectEntry, ResumeData } from "@/types/resume";
import { useResumeStore } from "@/store/resumeStore";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import * as flaskApi from "@/lib/flaskApi";

export default function BuilderPage() {
  return <BuilderInner />;
}

function isValidEmail(email: string) {
  const e = (email || "").trim();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}

function normalizePhone(phone: string) {
  return (phone || "").replace(/[^0-9]/g, "");
}

function validateStep(step: number, resume: ResumeData): { ok: boolean; message: string } {
  if (step === 0) {
    if (!resume.contact.name.trim()) return { ok: false, message: "Full name is required." };
    if (!isValidEmail(resume.contact.email)) return { ok: false, message: "Please enter a valid email address." };
    const digits = normalizePhone(resume.contact.phone);
    if (digits.length < 10) return { ok: false, message: "Please enter a valid phone number (at least 10 digits)." };
    return { ok: true, message: "" };
  }
  if (step === 1) {
    if (!resume.summary.trim()) return { ok: false, message: "Professional summary is required." };
    if (resume.summary.trim().length < 30) return { ok: false, message: "Summary is too short (min 30 characters)." };
    return { ok: true, message: "" };
  }
  if (step === 2) {
    if (resume.experience.length === 0) return { ok: false, message: "Add at least 1 work experience entry." };
    const bad = resume.experience.some((x) => !x.title.trim() || !x.company.trim() || !x.description.trim());
    if (bad) return { ok: false, message: "Each experience must have Title, Company, and Description." };
    return { ok: true, message: "" };
  }
  if (step === 3) {
    if (resume.education.length === 0) return { ok: false, message: "Add at least 1 education entry." };
    const bad = resume.education.some((x) => !x.degree.trim() || !x.institution.trim());
    if (bad) return { ok: false, message: "Each education entry must have Degree and Institution." };
    return { ok: true, message: "" };
  }
  if (step === 4) {
    if (resume.skills.length < 5) return { ok: false, message: "Add at least 5 skills." };
    return { ok: true, message: "" };
  }
  if (step === 5) {
    if (resume.projects.length === 0) return { ok: false, message: "Add at least 1 project." };
    const bad = resume.projects.some((p) => !p.name.trim());
    if (bad) return { ok: false, message: "Each project must have a name." };
    return { ok: true, message: "" };
  }
  return { ok: true, message: "" };
}

function BuilderInner() {
  const resumeData = useResumeStore((s) => s.resumeData);
  const activeStep = useResumeStore((s) => s.activeStep);
  const completedSteps = useResumeStore((s) => s.completedSteps);
  const setActiveStep = useResumeStore((s) => s.setActiveStep);
  const markStepComplete = useResumeStore((s) => s.markStepComplete);
  const updateContact = useResumeStore((s) => s.updateContact);
  const setSummary = useResumeStore((s) => s.setSummary);
  const addExperience = useResumeStore((s) => s.addExperience);
  const updateExperience = useResumeStore((s) => s.updateExperience);
  const removeExperience = useResumeStore((s) => s.removeExperience);
  const addEducation = useResumeStore((s) => s.addEducation);
  const updateEducation = useResumeStore((s) => s.updateEducation);
  const removeEducation = useResumeStore((s) => s.removeEducation);
  const addSkill = useResumeStore((s) => s.addSkill);
  const removeSkill = useResumeStore((s) => s.removeSkill);
  const addProject = useResumeStore((s) => s.addProject);
  const updateProject = useResumeStore((s) => s.updateProject);
  const removeProject = useResumeStore((s) => s.removeProject);
  const importResumeData = useResumeStore((s) => s.importResumeData);

  const [mobileView, setMobileView] = React.useState<"edit" | "preview">("edit");
  const [importOpen, setImportOpen] = React.useState(false);
  const [isExportingPdf, setIsExportingPdf] = React.useState(false);

  const handleExportPdf = React.useCallback(async () => {
    try {
      setIsExportingPdf(true);
      const result = await flaskApi.finalizeResume({ approvedResumeJson: resumeData, jobAnalysis: null });

      const downloadUrl = result.download_url;
      if (!downloadUrl) throw new Error("Missing download URL");

      const pdfRes = await fetch(downloadUrl);
      if (!pdfRes.ok) throw new Error(`Failed to download PDF (${pdfRes.status})`);

      const pdfBlob = await pdfRes.blob();
      const objectUrl = URL.createObjectURL(pdfBlob);
      try {
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = "resume.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
      } finally {
        URL.revokeObjectURL(objectUrl);
      }

      toast("PDF downloaded");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to export PDF");
    } finally {
      setIsExportingPdf(false);
    }
  }, [resumeData]);

  React.useEffect(() => {
    try {
      const raw = sessionStorage.getItem("smartjob_import_resume_data");
      if (!raw) return;
      sessionStorage.removeItem("smartjob_import_resume_data");
      const parsed = JSON.parse(raw) as ResumeData;
      if (!parsed || typeof parsed !== "object") return;
      importResumeData(parsed);
      setActiveStep(0);
      toast("Resume imported");
    } catch {
      // ignore
    }
  }, [importResumeData, setActiveStep]);

  const atsScore = React.useMemo(() => computeATSScore(resumeData), [resumeData]);
  const breakdown = React.useMemo(() => {
    const keywords = Math.min(100, Math.round((resumeData.skills.length / 10) * 100));
    const contact = resumeData.contact.email || resumeData.contact.phone ? 100 : 60;
    const formatting = 92;
    const skills = Math.min(100, Math.round((resumeData.skills.length / 10) * 100));
    return { keywords, contact, formatting, skills };
  }, [resumeData.contact.email, resumeData.contact.phone, resumeData.skills.length]);

  const issues = React.useMemo(() => {
    const out: Array<{ severity: "high" | "medium" | "low"; text: string; stepIndex?: number }> = [];
    if (!resumeData.contact.email) out.push({ severity: "medium", text: "Add an email address.", stepIndex: 0 });
    if (!resumeData.summary) out.push({ severity: "medium", text: "Add a professional summary.", stepIndex: 1 });
    if (resumeData.skills.length < 8) out.push({ severity: "low", text: "Skills section has fewer than 8 items.", stepIndex: 4 });
    if (resumeData.experience.length === 0) out.push({ severity: "medium", text: "Add at least one work experience entry.", stepIndex: 2 });
    return out;
  }, [resumeData.contact.email, resumeData.experience.length, resumeData.skills.length, resumeData.summary]);

  const stepValidation = React.useMemo(() => validateStep(activeStep, resumeData), [activeStep, resumeData]);
  const canGoNext = stepValidation.ok;

  const STEPS = React.useMemo(
    () => [
      { id: 0, label: "Contact Info", icon: User },
      { id: 1, label: "Professional Summary", icon: FileText },
      { id: 2, label: "Work Experience", icon: Briefcase },
      { id: 3, label: "Education", icon: GraduationCap },
      { id: 4, label: "Skills", icon: Zap },
      { id: 5, label: "Projects", icon: FolderOpen },
      { id: 6, label: "Export", icon: Download },
    ],
    []
  );

  return (
    <div className="fixed inset-x-0 bottom-0 top-16 flex overflow-hidden bg-[#0F172A]">
      <aside
        className={cn(
          "flex-shrink-0 border-r border-[#334155] bg-[#1E293B] flex flex-col",
          mobileView === "preview" ? "hidden md:flex" : "flex"
        )}
        style={{
          width: "420px",
          height: "100%",
          overflow: "hidden",
        }}
      >
        <div
          className="flex-shrink-0 border-b border-[#334155] flex items-center justify-between px-4"
          style={{ height: "56px" }}
        >
          <Link href="/" className="flex items-center gap-1.5 text-[#94A3B8] hover:text-white text-sm">
            <ChevronLeft className="w-4 h-4" />Back
          </Link>
          <span className="font-heading font-semibold text-sm text-white">Resume Builder</span>
          <span className="text-xs text-[#10B981] flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />Saved
          </span>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="px-4 pt-3 pb-2">
            <button
              onClick={() => setImportOpen(true)}
              className="w-full px-4 py-3 rounded-xl border border-dashed border-[#334155] hover:border-[#6366F1] bg-[#243044]/50 hover:bg-[#6366F1]/05 transition-all text-left"
              type="button"
            >
              <p className="text-sm font-semibold text-white">Already have a resume?</p>
              <p className="text-xs text-[#94A3B8] mt-0.5">Upload it → auto-fill all fields</p>
            </button>
          </div>

          <div className="px-3 pb-2">
            {STEPS.map((step) => {
              const isActive = activeStep === step.id;
              const isCompleted = completedSteps.includes(step.id);
              return (
                <button
                  key={step.id}
                  onClick={() => setActiveStep(step.id)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 rounded-lg text-sm transition-all mb-1",
                    "h-9",
                    isActive
                      ? "bg-[#6366F1]/15 text-white border border-[#6366F1]/30"
                      : "text-[#94A3B8] hover:bg-[#243044] hover:text-white border border-transparent"
                  )}
                  type="button"
                >
                  <div
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0",
                      isCompleted
                        ? "bg-[#10B981]/20 text-[#10B981]"
                        : isActive
                          ? "bg-[#6366F1] text-white"
                          : "bg-[#243044] text-[#64748B]"
                    )}
                  >
                    {isCompleted ? <Check className="w-3 h-3" /> : step.id + 1}
                  </div>
                  <span className="font-medium truncate">{step.label}</span>
                  {isActive ? <ChevronRight className="w-3.5 h-3.5 ml-auto text-[#6366F1] flex-shrink-0" /> : null}
                </button>
              );
            })}
          </div>

          <div className="px-4 pb-3">
            <div className="flex justify-between text-xs text-[#64748B] mb-1.5">
              <span>Progress</span>
              <span>{Math.round((completedSteps.length / STEPS.length) * 100)}% complete</span>
            </div>
            <div className="h-1.5 rounded-full bg-[#334155]">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-[#6366F1] to-[#14B8A6]"
                animate={{ width: `${(completedSteps.length / STEPS.length) * 100}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
          </div>

          <div className="h-px bg-[#334155] mx-4" />

          <div className="px-4 py-4" style={{ paddingBottom: "80px" }}>
            <AnimatePresence mode="wait">
              <motion.div
                key={activeStep}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ duration: 0.2 }}
              >
                {renderStepContent({
                  activeStep,
                  resumeData,
                  updateContact,
                  setSummary,
                  addExperience,
                  updateExperience,
                  removeExperience,
                  addEducation,
                  updateEducation,
                  removeEducation,
                  addSkill,
                  removeSkill,
                  addProject,
                  updateProject,
                  removeProject,
                  atsScore,
                  breakdown,
                  issues,
                  onExportPdf: handleExportPdf,
                  isExportingPdf,
                  onNavigateToStep: (step) => setActiveStep(step),
                })}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        <div
          className="flex-shrink-0 border-t border-[#334155] flex items-center justify-between px-4 bg-[#1E293B]"
          style={{ height: "56px" }}
        >
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setActiveStep(Math.max(0, activeStep - 1))}
            disabled={activeStep === 0}
            icon={<ChevronLeft className="w-4 h-4" />}
            type="button"
          >
            Previous
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              const v = validateStep(activeStep, resumeData);
              if (!v.ok) {
                toast(v.message);
                return;
              }
              markStepComplete(activeStep);
              setActiveStep(Math.min(STEPS.length - 1, activeStep + 1));
            }}
            disabled={!canGoNext}
            type="button"
          >
            {activeStep === STEPS.length - 1 ? "Export Resume" : "Next →"}
          </Button>
        </div>
      </aside>

      <main
        className={cn(
          "flex-1 flex flex-col overflow-hidden bg-[#0F172A]",
          mobileView === "edit" ? "hidden md:flex" : "flex"
        )}
      >
        <div className="flex-1 min-h-0 overflow-y-auto bg-[#0F172A]">
          <div className="sticky top-0 z-10 h-14 flex-shrink-0 border-b border-[#334155] flex items-center justify-between px-6 bg-[#0F172A]">
            <div className="flex items-center gap-2.5">
              <span className="font-heading font-semibold text-sm text-white">Live Preview</span>
              <span className="flex items-center gap-1.5 text-xs text-[#10B981]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse" />
                Real-time
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => toast("Only ATS Minimal is available right now")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#334155] bg-[#1E293B] text-sm text-[#94A3B8] hover:border-[#6366F1] hover:text-white transition-all"
              >
                <Layout className="w-3.5 h-3.5" />
                ATS Minimal
                <ChevronDown className="w-3.5 h-3.5" />
              </button>
              <Button
                variant="primary"
                size="sm"
                icon={<Download className="w-3.5 h-3.5" />}
                onClick={handleExportPdf}
                disabled={isExportingPdf}
                type="button"
              >
                Export PDF
              </Button>
            </div>
          </div>

          <div className="p-6">
            <div className="mx-auto" style={{ maxWidth: "680px" }}>
              <div
                className="origin-top"
                style={{
                  transform: "scale(0.72)",
                  transformOrigin: "top center",
                  width: "8.5in",
                  marginLeft: "auto",
                  marginRight: "auto",
                  boxShadow: "0 8px 40px rgba(0,0,0,0.5)",
                  borderRadius: "4px",
                }}
              >
                <ATSMinimal />
              </div>
            </div>
          </div>
        </div>
      </main>

      <div className="fixed bottom-0 left-0 right-0 md:hidden border-t border-[#334155] bg-[#1E293B] z-50">
        <div className="flex h-14">
          <button
            onClick={() => setMobileView("edit")}
            className={cn(
              "flex-1 text-sm font-medium transition-colors",
              mobileView === "edit" ? "text-white border-t-2 border-[#6366F1]" : "text-[#94A3B8]"
            )}
          >
            Edit
          </button>
          <button
            onClick={() => setMobileView("preview")}
            className={cn(
              "flex-1 text-sm font-medium transition-colors",
              mobileView === "preview" ? "text-white border-t-2 border-[#6366F1]" : "text-[#94A3B8]"
            )}
          >
            Preview
          </button>
        </div>
      </div>

      <ResumeImporter
        open={importOpen}
        onOpenChange={setImportOpen}
        onImport={({ resumeData }) => {
          importResumeData(resumeData);
          setActiveStep(0);
        }}
      />
    </div>
  );
}

function renderStepContent(input: {
  activeStep: number;
  resumeData: ResumeData;
  updateContact: (field: keyof ResumeData["contact"], value: string) => void;
  setSummary: (summary: string) => void;
  addExperience: () => void;
  updateExperience: (id: string, field: keyof ExperienceEntry, value: any) => void;
  removeExperience: (id: string) => void;
  addEducation: () => void;
  updateEducation: (id: string, field: keyof EducationEntry, value: any) => void;
  removeEducation: (id: string) => void;
  addSkill: (skill: string) => void;
  removeSkill: (skill: string) => void;
  addProject: () => void;
  updateProject: (id: string, field: keyof ProjectEntry, value: any) => void;
  removeProject: (id: string) => void;
  atsScore: number;
  breakdown: { keywords: number; contact: number; formatting: number; skills: number };
  issues: Array<{ severity: "high" | "medium" | "low"; text: string; stepIndex?: number }>;
  onExportPdf: () => void;
  isExportingPdf: boolean;
  onNavigateToStep: (step: number) => void;
}) {
  const {
    activeStep,
    resumeData,
    updateContact,
    setSummary,
    addExperience,
    updateExperience,
    removeExperience,
    addEducation,
    updateEducation,
    removeEducation,
    addSkill,
    removeSkill,
    addProject,
    updateProject,
    removeProject,
    atsScore,
    breakdown,
    issues,
    onExportPdf,
    isExportingPdf,
    onNavigateToStep,
  } = input;

  if (activeStep === 0) {
    return (
      <div>
        <h3 className="font-heading font-semibold text-base text-white mb-6">Contact Information</h3>
        <div className="grid grid-cols-1 gap-4">
          <Field label="Full Name" icon={<User className="w-4 h-4" />}>
            <input
              value={resumeData.contact.name}
              onChange={(e) => updateContact("name", e.target.value)}
              placeholder="Your full name"
              className={textInput}
            />
          </Field>
          <Field label="Target Job Title" icon={<Briefcase className="w-4 h-4" />}>
            <input
              value={resumeData.contact.jobTitle}
              onChange={(e) => updateContact("jobTitle", e.target.value)}
              placeholder="Full-Stack Engineer"
              className={textInput}
            />
          </Field>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Email" icon={<Mail className="w-4 h-4" />}>
              <input
                value={resumeData.contact.email}
                onChange={(e) => updateContact("email", e.target.value)}
                placeholder="you@example.com"
                className={textInput}
              />
            </Field>
            <Field label="Phone" icon={<Phone className="w-4 h-4" />}>
              <input
                value={resumeData.contact.phone}
                onChange={(e) => updateContact("phone", e.target.value)}
                placeholder="+91 98765 43210"
                className={textInput}
              />
            </Field>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Location" icon={<MapPin className="w-4 h-4" />}>
              <input
                value={resumeData.contact.location}
                onChange={(e) => updateContact("location", e.target.value)}
                placeholder="Bengaluru, India"
                className={textInput}
              />
            </Field>
            <Field label="LinkedIn URL" icon={<Linkedin className="w-4 h-4" />}>
              <input
                value={resumeData.contact.linkedin}
                onChange={(e) => updateContact("linkedin", e.target.value)}
                placeholder="https://linkedin.com/in/..."
                className={textInput}
              />
            </Field>
          </div>
          <Field label="GitHub URL" icon={<Github className="w-4 h-4" />}>
            <input
              value={resumeData.contact.github}
              onChange={(e) => updateContact("github", e.target.value)}
              placeholder="https://github.com/..."
              className={textInput}
            />
          </Field>
          <Field label="Portfolio URL" icon={<Layout className="w-4 h-4" />}>
            <input
              value={resumeData.contact.portfolio}
              onChange={(e) => updateContact("portfolio", e.target.value)}
              placeholder="https://your-portfolio.com"
              className={textInput}
            />
          </Field>
        </div>
      </div>
    );
  }

  if (activeStep === 1) {
    const count = (resumeData.summary || "").length;
    return (
      <div>
        <h3 className="font-heading font-semibold text-base text-white mb-6">Professional Summary</h3>
        <textarea
          className={textArea}
          rows={6}
          value={resumeData.summary || ""}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="Write a 2-3 sentence professional summary..."
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-[#64748B]">{count} / 400</span>
          <Button
            variant="teal"
            size="sm"
            icon={<Sparkles className="w-3.5 h-3.5" />}
            onClick={() => toast("AI generation — coming soon")}
          >
            Generate with AI
          </Button>
        </div>
      </div>
    );
  }

  if (activeStep === 2) {
    return (
      <div className="flex flex-col gap-3">
        <h3 className="font-heading font-semibold text-base text-white mb-2">Work Experience</h3>
        {resumeData.experience.length === 0 ? (
          <p className="text-sm text-[#64748B] text-center py-4">No experience added yet. Click below to add your first role.</p>
        ) : null}
        {resumeData.experience.map((exp) => (
          <ExperienceCard
            key={exp.id}
            entry={exp}
            onChange={(field, value) => updateExperience(exp.id, field, value)}
            onRemove={() => removeExperience(exp.id)}
          />
        ))}
        <button
          onClick={addExperience}
          className="w-full py-3 rounded-xl border border-dashed border-[#334155] text-sm text-[#94A3B8] hover:border-[#6366F1] hover:text-[#6366F1] transition-colors flex items-center justify-center gap-2 mt-2"
          type="button"
        >
          <Plus className="w-4 h-4" />Add Experience
        </button>
      </div>
    );
  }

  if (activeStep === 3) {
    return (
      <div className="flex flex-col gap-3">
        <h3 className="font-heading font-semibold text-base text-white mb-2">Education</h3>
        {resumeData.education.length === 0 ? (
          <p className="text-sm text-[#64748B] text-center py-4">No education added yet. Click below to add your first entry.</p>
        ) : null}
        {resumeData.education.map((edu) => (
          <EducationCard
            key={edu.id}
            entry={edu}
            onChange={(field, value) => updateEducation(edu.id, field, value)}
            onRemove={() => removeEducation(edu.id)}
          />
        ))}
        <button
          onClick={addEducation}
          className="w-full py-3 rounded-xl border border-dashed border-[#334155] text-sm text-[#94A3B8] hover:border-[#6366F1] hover:text-[#6366F1] transition-colors flex items-center justify-center gap-2 mt-2"
          type="button"
        >
          <Plus className="w-4 h-4" />Add Education
        </button>
      </div>
    );
  }

  if (activeStep === 4) {
    return (
      <div className="flex flex-col gap-4">
        <h3 className="font-heading font-semibold text-base text-white mb-2">Skills</h3>
        <SkillTagInput skills={resumeData.skills} onAdd={addSkill} onRemove={removeSkill} />
        {resumeData.skills.length < 8 ? (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-[#F59E0B]/10 border border-[#F59E0B]/30">
            <span className="text-[#F59E0B] text-xs mt-0.5">⚠</span>
            <p className="text-xs text-[#F59E0B]">Add at least 8 skills to improve your ATS score. Current: {resumeData.skills.length}</p>
          </div>
        ) : null}
      </div>
    );
  }

  if (activeStep === 5) {
    return (
      <div className="flex flex-col gap-3">
        <h3 className="font-heading font-semibold text-base text-white mb-2">Projects</h3>
        {resumeData.projects.length === 0 ? (
          <p className="text-sm text-[#64748B] text-center py-4">No projects added yet. Click below to add your first project.</p>
        ) : null}
        {resumeData.projects.map((proj) => (
          <ProjectCard
            key={proj.id}
            entry={proj}
            onChange={(field, value) => updateProject(proj.id, field, value)}
            onRemove={() => removeProject(proj.id)}
          />
        ))}
        <button
          onClick={addProject}
          className="w-full py-3 rounded-xl border border-dashed border-[#334155] text-sm text-[#94A3B8] hover:border-[#6366F1] hover:text-[#6366F1] transition-colors flex items-center justify-center gap-2 mt-2"
          type="button"
        >
          <Plus className="w-4 h-4" />Add Project
        </button>
      </div>
    );
  }

  return (
    <div>
      <h3 className="font-heading font-semibold text-base text-white mb-6">Export</h3>

      <ATSScoreCard score={atsScore} breakdown={breakdown} issues={issues} onNavigateToStep={(s) => onNavigateToStep(s)} />

      <div className="mt-4 grid grid-cols-1 gap-3">
        <Button
          variant="primary"
          size="lg"
          icon={<Download className="w-4 h-4" />}
          onClick={onExportPdf}
          disabled={isExportingPdf}
        >
          {isExportingPdf ? "Generating PDF…" : "Download PDF"}
        </Button>
        <Button variant="ghost" size="lg" icon={<FileText className="w-4 h-4" />} onClick={() => toast("DOCX export — coming soon")}
        >
          Download DOCX
        </Button>
        <Button variant="subtle" size="lg" icon={<Copy className="w-4 h-4" />} onClick={() => toast("Copy plain text — coming soon")}
        >
          Copy Plain Text
        </Button>
      </div>
    </div>
  );
}

function computeATSScore(resume: ResumeData): number {
  let score = 0;
  const contactFields: Array<keyof ResumeData["contact"]> = ["name", "email", "phone", "location"];
  score +=
    contactFields.filter((f) => (resume.contact[f] || "").trim()).length * (25 / contactFields.length);
  if (resume.summary.trim().length > 50) score += 15;
  score += Math.min(resume.experience.length, 3) * (25 / 3);
  score += Math.min(resume.skills.length, 10) * (20 / 10);
  if (resume.education.length > 0) score += 10;
  if (resume.projects.length > 0) score += 5;
  return Math.round(Math.min(score, 100));
}

function Input({
  label,
  icon,
  value,
  onChange,
  placeholder,
  type,
  disabled,
}: {
  label: string;
  icon?: React.ReactNode;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}) {
  return (
    <Field label={label} icon={icon ?? null}>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={type}
        disabled={disabled}
        className={textInput}
      />
    </Field>
  );
}

function ExperienceCard({
  entry,
  onChange,
  onRemove,
}: {
  entry: ExperienceEntry;
  onChange: (field: keyof ExperienceEntry, value: any) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = React.useState(true);
  return (
    <div className="border border-[#334155] rounded-xl bg-[#243044]/50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => setExpanded((e) => !e)}>
        <span className="text-sm font-medium text-white truncate">
          {entry.title || entry.company ? `${entry.title}${entry.company ? ` @ ${entry.company}` : ""}` : "New Experience"}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            type="button"
          >
            <Trash2 className="w-3.5 h-3.5 text-[#EF4444]" />
          </button>
          <ChevronDown className={cn("w-4 h-4 text-[#94A3B8] transition-transform", expanded && "rotate-180")} />
        </div>
      </div>
      {expanded ? (
        <div className="px-4 pb-4 flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2">
            <Input label="Job Title" value={entry.title} onChange={(e) => onChange("title", e.target.value)} placeholder="Software Engineer" />
            <Input label="Company" value={entry.company} onChange={(e) => onChange("company", e.target.value)} placeholder="Company" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input label="Start Date" value={entry.startDate} onChange={(e) => onChange("startDate", e.target.value)} placeholder="Mar 2025" />
            <Input
              label="End Date"
              value={entry.endDate}
              onChange={(e) => onChange("endDate", e.target.value)}
              placeholder="Jul 2025"
              disabled={entry.current}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[#94A3B8] cursor-pointer">
            <input
              type="checkbox"
              checked={entry.current}
              onChange={(e) => onChange("current", e.target.checked)}
              className="rounded"
            />
            Currently working here
          </label>
          <Input label="Location" value={entry.location} onChange={(e) => onChange("location", e.target.value)} placeholder="Hyderabad / Remote" />
          <div>
            <label className="text-sm font-medium text-[#94A3B8] block mb-1.5">Description</label>
            <textarea
              value={entry.description}
              onChange={(e) => onChange("description", e.target.value)}
              rows={4}
              placeholder={"• Built X\n• Improved Y\n• Reduced Z"}
              className="w-full rounded-lg border border-[#334155] bg-[#0F172A] px-3 py-2 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 resize-none outline-none"
            />
            <p className="text-xs text-[#64748B] mt-1">One bullet per line. Start each line with •</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function EducationCard({
  entry,
  onChange,
  onRemove,
}: {
  entry: EducationEntry;
  onChange: (field: keyof EducationEntry, value: any) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = React.useState(true);
  return (
    <div className="border border-[#334155] rounded-xl bg-[#243044]/50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => setExpanded((e) => !e)}>
        <span className="text-sm font-medium text-white truncate">
          {entry.degree || entry.institution ? `${entry.degree}${entry.institution ? ` @ ${entry.institution}` : ""}` : "New Education"}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            type="button"
          >
            <Trash2 className="w-3.5 h-3.5 text-[#EF4444]" />
          </button>
          <ChevronDown className={cn("w-4 h-4 text-[#94A3B8] transition-transform", expanded && "rotate-180")} />
        </div>
      </div>
      {expanded ? (
        <div className="px-4 pb-4 flex flex-col gap-3">
          <Input label="Degree" value={entry.degree} onChange={(e) => onChange("degree", e.target.value)} placeholder="B.Tech" />
          <Input label="Institution" value={entry.institution} onChange={(e) => onChange("institution", e.target.value)} placeholder="University" />
          <Input label="Field of Study" value={entry.field} onChange={(e) => onChange("field", e.target.value)} placeholder="Computer Science" />
          <div className="grid grid-cols-2 gap-2">
            <Input label="Start Year" value={entry.startYear} onChange={(e) => onChange("startYear", e.target.value)} placeholder="2022" />
            <Input label="End Year" value={entry.endYear} onChange={(e) => onChange("endYear", e.target.value)} placeholder="2026" />
          </div>
          <Input label="Grade/CGPA" value={entry.grade} onChange={(e) => onChange("grade", e.target.value)} placeholder="8.5" />
        </div>
      ) : null}
    </div>
  );
}

function ProjectCard({
  entry,
  onChange,
  onRemove,
}: {
  entry: ProjectEntry;
  onChange: (field: keyof ProjectEntry, value: any) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = React.useState(true);
  return (
    <div className="border border-[#334155] rounded-xl bg-[#243044]/50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 cursor-pointer" onClick={() => setExpanded((e) => !e)}>
        <span className="text-sm font-medium text-white truncate">{entry.name || "New Project"}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            type="button"
          >
            <Trash2 className="w-3.5 h-3.5 text-[#EF4444]" />
          </button>
          <ChevronDown className={cn("w-4 h-4 text-[#94A3B8] transition-transform", expanded && "rotate-180")} />
        </div>
      </div>
      {expanded ? (
        <div className="px-4 pb-4 flex flex-col gap-3">
          <Input label="Project Name" value={entry.name} onChange={(e) => onChange("name", e.target.value)} placeholder="Project" />
          <div>
            <label className="text-sm font-medium text-[#94A3B8] block mb-1.5">Description</label>
            <textarea
              value={entry.description}
              onChange={(e) => onChange("description", e.target.value)}
              rows={4}
              placeholder="What did you build?"
              className="w-full rounded-lg border border-[#334155] bg-[#0F172A] px-3 py-2 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 resize-none outline-none"
            />
          </div>
          <Input label="GitHub URL" value={entry.github} onChange={(e) => onChange("github", e.target.value)} placeholder="https://github.com/..." />
          <Input label="Demo URL" value={entry.demo} onChange={(e) => onChange("demo", e.target.value)} placeholder="https://..." />
        </div>
      ) : null}
    </div>
  );
}

function SkillTagInput({
  skills,
  onAdd,
  onRemove,
}: {
  skills: string[];
  onAdd: (s: string) => void;
  onRemove: (s: string) => void;
}) {
  const [input, setInput] = React.useState("");
  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-3 min-h-[40px]">
        {skills.map((skill) => (
          <motion.span
            key={skill}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#6366F1]/15 border border-[#6366F1]/30 text-[#A5B4FC] text-xs font-medium"
          >
            {skill}
            <button onClick={() => onRemove(skill)} className="text-[#A5B4FC] hover:text-white" type="button">
              <X className="w-3 h-3" />
            </button>
          </motion.span>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === ",") && input.trim()) {
            e.preventDefault();
            onAdd(input.trim());
            setInput("");
          }
          if (e.key === "Backspace" && !input && skills.length > 0) {
            onRemove(skills[skills.length - 1]);
          }
        }}
        placeholder="Type a skill and press Enter..."
        className="w-full rounded-lg border border-[#334155] bg-[#243044] px-4 py-2.5 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] outline-none"
      />
      <p className="text-xs text-[#64748B] mt-1.5">Press Enter or comma to add · Backspace to remove last</p>
    </div>
  );
}

function Field({ label, icon, children }: { label: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2 text-sm font-medium text-[#94A3B8]">
        <span className="text-[#64748B]">{icon}</span>
        {label}
      </div>
      {children}
    </div>
  );
}

function StringListStep({
  title,
  icon,
  items,
  placeholder,
  onChange,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  placeholder: string;
  onChange: (items: string[]) => void;
}) {
  const text = items.join("\n");
  return (
    <div>
      <h3 className="font-heading font-semibold text-base text-white mb-6">{title}</h3>
      <div className="text-xs text-[#64748B] mb-2 flex items-center gap-2">
        <span className="text-[#94A3B8]">{icon}</span>
        One line per item
      </div>
      <textarea
        className={textArea}
        rows={10}
        value={text}
        onChange={(e) => {
          const next = e.target.value
            .split("\n")
            .map((x) => x.trim())
            .filter(Boolean);
          onChange(next);
        }}
        placeholder={placeholder}
      />
    </div>
  );
}

function SkillsStep({
  skills,
  onChange,
  missingSkills,
}: {
  skills: string[];
  onChange: (skills: string[]) => void;
  missingSkills: string[];
}) {
  const [value, setValue] = React.useState("");

  function addSkill(s: string) {
    const normalized = s.trim();
    if (!normalized) return;
    if (skills.some((x) => x.toLowerCase() === normalized.toLowerCase())) return;
    onChange([...skills, normalized]);
  }

  return (
    <div>
      <h3 className="font-heading font-semibold text-base text-white mb-6">Skills</h3>

      <div className="flex flex-col gap-2">
        <div className="text-xs text-[#64748B]">Type a skill and press Enter</div>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addSkill(value);
              setValue("");
            }
          }}
          placeholder="e.g., React, SQL, Flask"
          className={textInput}
        />

        <div className="mt-2 flex flex-wrap gap-2">
          {skills.map((s) => (
            <motion.span
              key={s}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 320, damping: 24 }}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#6366F1]/15 border border-[#6366F1]/30 text-[#A5B4FC] text-xs font-medium"
            >
              {s}
              <button
                onClick={() => onChange(skills.filter((x) => x !== s))}
                className="text-[#A5B4FC] hover:text-white"
                aria-label={`Remove ${s}`}
              >
                <X className="w-3 h-3" />
              </button>
            </motion.span>
          ))}
        </div>
      </div>

      {missingSkills.length > 0 ? (
        <div className="mt-6 rounded-2xl border border-[#334155] bg-[#243044]/40 p-4">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-white">Missing skills from JD</div>
            <div className="text-xs text-[#64748B]">Add only if genuinely learned</div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {missingSkills.slice(0, 16).map((s) => (
              <button
                key={s}
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#14B8A6]/10 border border-[#14B8A6]/25 text-[#5EEAD4] text-xs font-medium hover:bg-[#14B8A6]/15"
                onClick={() => addSkill(s)}
              >
                <Plus className="w-3.5 h-3.5" />
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

const textInput =
  "w-full rounded-lg border border-[#334155] bg-[#243044] px-4 py-2.5 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 transition-all outline-none";

const textArea =
  "w-full rounded-lg border border-[#334155] bg-[#243044] px-4 py-3 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 transition-all resize-none outline-none";
