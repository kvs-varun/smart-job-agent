"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Award,
  BookOpen,
  ChevronRight,
  ExternalLink,
  FileText,
  Sparkles,
  Star,
  Target,
  Upload,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { ResumeImporter } from "@/components/importer/ResumeImporter";
import { scoreResume } from "@/lib/agentApi";
import type { ScoreBreakdown, MentorResource } from "@/lib/agentApi";
import { useResumeStore } from "@/store/resumeStore";
import { cn } from "@/lib/utils";

const DIMENSION_META: Record<keyof ScoreBreakdown, { label: string; max: number; color: string }> = {
  ats_compliance:   { label: "ATS Compliance",    max: 2.0, color: "#6366F1" },
  content_quality:  { label: "Content Quality",   max: 2.5, color: "#14B8A6" },
  skill_alignment:  { label: "Skill Alignment",   max: 2.0, color: "#10B981" },
  profile_strength: { label: "Profile Strength",  max: 2.0, color: "#F59E0B" },
  presentation:     { label: "Presentation",      max: 1.5, color: "#8B5CF6" },
};

function ScoreRing({ score, max = 10 }: { score: number; max?: number }) {
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  const arc = circumference * 0.75;
  const pct = Math.max(0, Math.min(1, score / max));
  const offset = arc - pct * arc;
  const color = score >= 8 ? "#10B981" : score >= 6 ? "#F59E0B" : "#EF4444";

  return (
    <div className="flex flex-col items-center">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle cx="90" cy="90" r={radius} fill="none" stroke="#1E293B" strokeWidth="12"
          strokeDasharray={`${arc} ${circumference}`} strokeLinecap="round" transform="rotate(-225 90 90)" />
        <motion.circle cx="90" cy="90" r={radius} fill="none" stroke={color} strokeWidth="12"
          strokeDasharray={`${arc} ${circumference}`} strokeLinecap="round" transform="rotate(-225 90 90)"
          initial={{ strokeDashoffset: arc }} animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: "easeOut" }} />
        <text x="90" y="84" textAnchor="middle" dominantBaseline="middle" fontSize="36" fontWeight="bold" fill={color}>
          {score.toFixed(1)}
        </text>
        <text x="90" y="108" textAnchor="middle" fontSize="13" fill="#64748B">/ {max}.0</text>
      </svg>
      <span className="text-sm font-medium text-text-secondary mt-1">
        {score >= 8 ? "Excellent" : score >= 6 ? "Good" : score >= 4 ? "Fair" : "Needs Work"}
      </span>
    </div>
  );
}

function DimensionBar({ dim, value, meta }: { dim: string; value: number; meta: { label: string; max: number; color: string } }) {
  const pct = Math.max(0, Math.min(1, value / meta.max)) * 100;
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-text-secondary">{meta.label}</span>
        <span className="text-sm font-semibold text-white">{value.toFixed(1)} / {meta.max}</span>
      </div>
      <div className="h-2 rounded-full bg-elevated overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: meta.color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
        />
      </div>
    </div>
  );
}

function ResourceCard({ resource }: { resource: MentorResource }) {
  return (
    <motion.a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      className="block rounded-xl border border-border bg-card hover:border-accent/50 transition-colors p-4 group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-xs bg-teal/15 text-teal border border-teal/30 px-2 py-0.5 rounded-full font-medium">FREE</span>
            <span className="text-xs text-text-muted">{resource.provider}</span>
            {resource.duration_hours > 0 && (
              <span className="text-xs text-text-muted">{resource.duration_hours}h</span>
            )}
          </div>
          <p className="text-sm font-semibold text-white group-hover:text-accent transition-colors line-clamp-2">{resource.title}</p>
          <p className="text-xs text-text-muted mt-1">Gap: {resource.skill_gap}</p>
        </div>
        <ExternalLink className="w-4 h-4 text-text-muted group-hover:text-accent flex-shrink-0 mt-0.5 transition-colors" />
      </div>
      <div className="mt-2 flex items-center gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <Star
            key={i}
            className={cn("w-3 h-3", i < Math.round(resource.relevance_score * 5) ? "text-amber-400 fill-amber-400" : "text-border")}
          />
        ))}
        <span className="text-xs text-text-muted ml-1">relevance</span>
      </div>
    </motion.a>
  );
}

export default function ScorerPage() {
  const storeResume = useResumeStore((s) => s.resumeData);
  const [importOpen, setImportOpen] = React.useState(false);
  const [resumeText, setResumeText] = React.useState("");
  const [jdText, setJdText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [score, setScore] = React.useState<number | null>(null);
  const [breakdown, setBreakdown] = React.useState<ScoreBreakdown | null>(null);
  const [mentorFeedback, setMentorFeedback] = React.useState<string | null>(null);
  const [resources, setResources] = React.useState<MentorResource[]>([]);
  const [tab, setTab] = React.useState<"score" | "mentor" | "resources">("score");

  async function onScore() {
    if (!resumeText.trim() && !Object.values(storeResume.contact).some(Boolean)) {
      toast("Upload a resume first.");
      return;
    }
    setBusy(true);
    try {
      const resp = await scoreResume({
        resume_data: storeResume as unknown as Record<string, unknown>,
        job_description: jdText || undefined,
      });
      setScore(resp.resume_score);
      setBreakdown(resp.score_breakdown);
      setMentorFeedback(resp.mentor_feedback);
      setResources(resp.mentor_recommendations ?? []);
      setTab("score");
      toast("Resume scored");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setBusy(false);
    }
  }

  const hasResults = score !== null;

  return (
    <div className="min-h-screen bg-surface pt-20 pb-16 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-accent/10 border border-accent/20 rounded-full px-4 py-1.5 mb-4">
            <Award className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium text-accent">Resume Scorer & Mentor</span>
          </div>
          <h1 className="text-3xl font-heading font-bold text-white mb-3">
            How strong is your resume?
          </h1>
          <p className="text-text-secondary max-w-xl mx-auto">
            AI scores your resume 0–10 across 5 dimensions and recommends free certified courses to close your gaps.
          </p>
        </div>

        {/* Input panel */}
        <div className="bg-card border border-border rounded-2xl p-6 mb-6">
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-xs text-text-muted uppercase tracking-wider font-semibold mb-2">Resume</div>
              {resumeText ? (
                <div className="rounded-xl border border-teal/30 bg-teal/5 p-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-teal" />
                    <span className="text-sm text-white">{storeResume.contact?.name || "Resume loaded"}</span>
                  </div>
                  <button onClick={() => setImportOpen(true)} className="text-xs text-text-muted hover:text-white transition-colors">
                    Change
                  </button>
                </div>
              ) : (
                <Button variant="ghost" size="lg" className="w-full" icon={<Upload className="w-4 h-4" />}
                  onClick={() => setImportOpen(true)}>
                  Upload Resume (PDF / DOCX)
                </Button>
              )}
            </div>

            <div>
              <div className="text-xs text-text-muted uppercase tracking-wider font-semibold mb-2">Job Description (optional)</div>
              <textarea
                className="w-full rounded-xl border border-border bg-elevated px-3 py-2.5 text-sm text-white placeholder:text-text-muted focus:border-accent outline-none resize-none transition-colors"
                rows={3}
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste job description for skill-aligned scoring..."
              />
            </div>
          </div>

          <Button variant="primary" size="lg" className="w-full" loading={busy} icon={<Sparkles className="w-4 h-4" />}
            onClick={onScore}>
            Score My Resume
          </Button>
        </div>

        {/* Results */}
        <AnimatePresence>
          {hasResults && breakdown && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              {/* Tab bar */}
              <div className="flex gap-1 bg-card border border-border rounded-xl p-1 mb-6">
                {[
                  { id: "score",     label: "Score",       icon: Zap },
                  { id: "mentor",    label: "Feedback",    icon: Target },
                  { id: "resources", label: "Free Courses", icon: BookOpen },
                ].map(({ id, label, icon: Icon }) => (
                  <button key={id} onClick={() => setTab(id as typeof tab)}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all",
                      tab === id ? "bg-accent text-white" : "text-text-secondary hover:text-white"
                    )}>
                    <Icon className="w-4 h-4" />
                    <span className="hidden sm:inline">{label}</span>
                  </button>
                ))}
              </div>

              {tab === "score" && (
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-card border border-border rounded-2xl p-6 flex flex-col items-center">
                    <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">Overall Score</h2>
                    <ScoreRing score={score!} />
                  </div>
                  <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
                    <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">Breakdown</h2>
                    {(Object.keys(DIMENSION_META) as Array<keyof ScoreBreakdown>).map((dim) => (
                      <DimensionBar key={dim} dim={dim} value={breakdown[dim]} meta={DIMENSION_META[dim]} />
                    ))}
                  </div>
                </div>
              )}

              {tab === "mentor" && mentorFeedback && (
                <div className="bg-card border border-border rounded-2xl p-6">
                  <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
                    <Target className="w-4 h-4 text-accent" />
                    Mentor Feedback
                  </h2>
                  <div className="prose prose-invert prose-sm max-w-none">
                    {mentorFeedback.split("\n").filter(Boolean).map((line, i) => (
                      <p key={i} className="text-text-secondary leading-relaxed mb-2">{line}</p>
                    ))}
                  </div>
                  <div className="mt-6 pt-4 border-t border-border">
                    <a href="/builder">
                      <Button variant="primary" icon={<ChevronRight className="w-4 h-4" />}>
                        Improve Resume in Builder
                      </Button>
                    </a>
                  </div>
                </div>
              )}

              {tab === "resources" && (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">
                      Free Certified Courses ({resources.length})
                    </h2>
                    <span className="text-xs text-teal">100% Free · No paywall</span>
                  </div>
                  {resources.length === 0 ? (
                    <div className="bg-card border border-border rounded-2xl p-8 text-center">
                      <BookOpen className="w-10 h-10 text-border mx-auto mb-3" />
                      <p className="text-text-secondary">No recommendations generated. Score your resume first.</p>
                    </div>
                  ) : (
                    <div className="grid sm:grid-cols-2 gap-4">
                      {resources.map((r, i) => <ResourceCard key={i} resource={r} />)}
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {!hasResults && !busy && (
          <div className="text-center py-16 text-text-muted">
            <Award className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm">Upload your resume and click "Score My Resume" to see your results.</p>
          </div>
        )}
      </div>

      <ResumeImporter
        open={importOpen}
        onOpenChange={setImportOpen}
        onImport={({ resumeData }) => {
          useResumeStore.getState().importResumeData(resumeData);
          const text = [
            resumeData.contact?.name,
            resumeData.summary,
            (resumeData.skills || []).join(", "),
            ...(resumeData.experience || []).map((x) => `${x.title} ${x.company} ${x.description}`),
          ].filter(Boolean).join("\n\n");
          setResumeText(text);
          toast("Resume loaded");
        }}
      />
    </div>
  );
}
