"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Loader2,
  Pause,
  Play,
  Square,
  Upload,
  XCircle,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/Button";
import { ResumeImporter } from "@/components/importer/ResumeImporter";
import { scoreResume, startAutoApply } from "@/lib/agentApi";
import type { AutoApplyResult } from "@/lib/agentApi";
import { useResumeStore } from "@/store/resumeStore";
import { cn } from "@/lib/utils";

const SCORE_THRESHOLD = 7.0;

function statusIcon(status: AutoApplyResult["status"]) {
  switch (status) {
    case "submitted": return <CheckCircle2 className="w-4 h-4 text-teal flex-shrink-0" />;
    case "failed":    return <XCircle      className="w-4 h-4 text-error flex-shrink-0" />;
    case "blocked":   return <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />;
    default:          return <Pause        className="w-4 h-4 text-text-muted flex-shrink-0" />;
  }
}

function statusBadge(status: AutoApplyResult["status"]) {
  const map: Record<AutoApplyResult["status"], string> = {
    submitted: "bg-teal/15 text-teal border-teal/30",
    failed:    "bg-error/15 text-error border-error/30",
    blocked:   "bg-amber-400/15 text-amber-400 border-amber-400/30",
    skipped:   "bg-elevated text-text-muted border-border",
  };
  return cn("text-xs font-medium px-2 py-0.5 rounded-full border capitalize", map[status]);
}

export default function AutoApplyPage() {
  const storeResume = useResumeStore((s) => s.resumeData);
  const [importOpen, setImportOpen] = React.useState(false);
  const [resumeLoaded, setResumeLoaded] = React.useState(false);

  // Preferences
  const [targetRoles, setTargetRoles] = React.useState("Software Engineer, Backend Engineer");
  const [location, setLocation]       = React.useState("Hyderabad, India");
  const [expLevel, setExpLevel]        = React.useState("fresher");
  const [platforms, setPlatforms]      = React.useState<("linkedin" | "naukri")[]>(["linkedin", "naukri"]);
  const [maxApps, setMaxApps]          = React.useState(5);

  // Score check
  const [resumeScore, setResumeScore] = React.useState<number | null>(null);
  const [scoreBusy, setScoreBusy]      = React.useState(false);

  // Apply session
  const [running, setRunning]   = React.useState(false);
  const [paused, setPaused]     = React.useState(false);
  const [results, setResults]   = React.useState<AutoApplyResult[]>([]);
  const [done, setDone]         = React.useState(false);
  const abortRef = React.useRef(false);

  async function onCheckScore() {
    if (!resumeLoaded) { toast("Upload your resume first."); return; }
    setScoreBusy(true);
    try {
      const resp = await scoreResume({ resume_data: storeResume as unknown as Record<string, unknown> });
      setResumeScore(resp.resume_score);
      if (resp.resume_score >= SCORE_THRESHOLD) {
        toast(`Score: ${resp.resume_score.toFixed(1)}/10 — Auto-apply unlocked!`);
      } else {
        toast(`Score: ${resp.resume_score.toFixed(1)}/10 — Needs ${SCORE_THRESHOLD} to unlock auto-apply`);
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setScoreBusy(false);
    }
  }

  async function onStartApply() {
    if (!resumeLoaded)                          { toast("Upload your resume first.");         return; }
    if (resumeScore === null)                   { toast("Check your score first.");           return; }
    if (resumeScore < SCORE_THRESHOLD)          { toast(`Score ${resumeScore.toFixed(1)}/10 is below ${SCORE_THRESHOLD} threshold.`); return; }
    if (platforms.length === 0)                 { toast("Select at least one platform.");     return; }

    setRunning(true);
    setPaused(false);
    setDone(false);
    setResults([]);
    abortRef.current = false;

    try {
      const resp = await startAutoApply({
        resume_data: storeResume as unknown as Record<string, unknown>,
        resume_score: resumeScore,
        preferences: {
          target_roles: targetRoles.split(",").map((s) => s.trim()).filter(Boolean),
          location,
          experience_level: expLevel,
          platforms,
          max_applications: maxApps,
        },
      });
      setResults(resp.results ?? []);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Auto-apply failed");
    } finally {
      setRunning(false);
      setDone(true);
    }
  }

  function togglePlatform(p: "linkedin" | "naukri") {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  const submitted = results.filter((r) => r.status === "submitted").length;
  const failed    = results.filter((r) => r.status === "failed").length;
  const skipped   = results.filter((r) => r.status === "skipped").length;

  const scoreOk = resumeScore !== null && resumeScore >= SCORE_THRESHOLD;

  return (
    <div className="min-h-screen bg-surface pt-20 pb-16 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-teal/10 border border-teal/20 rounded-full px-4 py-1.5 mb-4">
            <Zap className="w-4 h-4 text-teal" />
            <span className="text-sm font-medium text-teal">Auto-Apply Agent</span>
          </div>
          <h1 className="text-3xl font-heading font-bold text-white mb-3">
            Apply to jobs automatically
          </h1>
          <p className="text-text-secondary max-w-xl mx-auto">
            Agent 8 searches LinkedIn and Naukri, filters by match score ≥ 70%, and submits Easy Apply / Quick Apply on your behalf.
            Requires resume score ≥ {SCORE_THRESHOLD}/10.
          </p>
        </div>

        <div className="grid md:grid-cols-5 gap-6">
          {/* Left: setup */}
          <div className="md:col-span-2 space-y-4">
            {/* Step 1: Resume */}
            <div className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className={cn("w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                  resumeLoaded ? "bg-teal/20 text-teal" : "bg-elevated text-text-muted")}>
                  {resumeLoaded ? "✓" : "1"}
                </div>
                <span className="text-sm font-semibold text-white">Upload Resume</span>
              </div>
              {resumeLoaded ? (
                <div className="text-sm text-teal flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  {storeResume.contact?.name || "Resume loaded"}
                </div>
              ) : (
                <Button variant="ghost" size="md" className="w-full" icon={<Upload className="w-4 h-4" />}
                  onClick={() => setImportOpen(true)}>
                  Upload PDF / DOCX
                </Button>
              )}
            </div>

            {/* Step 2: Score check */}
            <div className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className={cn("w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                  scoreOk ? "bg-teal/20 text-teal" : "bg-elevated text-text-muted")}>
                  {scoreOk ? "✓" : "2"}
                </div>
                <span className="text-sm font-semibold text-white">Check Score (≥ {SCORE_THRESHOLD})</span>
              </div>
              {resumeScore !== null && (
                <div className={cn("text-sm flex items-center gap-2 mb-3",
                  scoreOk ? "text-teal" : "text-amber-400")}>
                  {scoreOk ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                  Score: {resumeScore.toFixed(1)} / 10
                  {!scoreOk && <span className="text-xs">— improve on <a href="/scorer" className="underline">Scorer page</a></span>}
                </div>
              )}
              <Button variant="ghost" size="md" className="w-full" loading={scoreBusy}
                onClick={onCheckScore}>
                {resumeScore === null ? "Check My Score" : "Re-check Score"}
              </Button>
            </div>

            {/* Step 3: Preferences */}
            <div className="bg-card border border-border rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-full bg-elevated text-text-muted flex items-center justify-center text-xs font-bold">3</div>
                <span className="text-sm font-semibold text-white">Preferences</span>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Target Roles (comma-separated)</label>
                  <input type="text" value={targetRoles} onChange={(e) => setTargetRoles(e.target.value)}
                    className="w-full rounded-lg border border-border bg-elevated px-3 py-2 text-sm text-white placeholder:text-text-muted focus:border-accent outline-none" />
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Location</label>
                  <input type="text" value={location} onChange={(e) => setLocation(e.target.value)}
                    className="w-full rounded-lg border border-border bg-elevated px-3 py-2 text-sm text-white placeholder:text-text-muted focus:border-accent outline-none" />
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Experience Level</label>
                  <select value={expLevel} onChange={(e) => setExpLevel(e.target.value)}
                    className="w-full rounded-lg border border-border bg-elevated px-3 py-2 text-sm text-white focus:border-accent outline-none">
                    <option value="fresher">Fresher (0–1 yr)</option>
                    <option value="junior">Junior (1–3 yr)</option>
                    <option value="mid">Mid (3–5 yr)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Platforms</label>
                  <div className="flex gap-2">
                    {(["linkedin", "naukri"] as const).map((p) => (
                      <button key={p} onClick={() => togglePlatform(p)}
                        className={cn("flex-1 py-1.5 rounded-lg border text-xs font-medium capitalize transition-colors",
                          platforms.includes(p) ? "bg-accent/20 border-accent text-accent" : "bg-elevated border-border text-text-muted hover:text-white")}>
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-text-muted mb-1 block">Max Applications: {maxApps}</label>
                  <input type="range" min={1} max={20} value={maxApps} onChange={(e) => setMaxApps(Number(e.target.value))}
                    className="w-full accent-accent" />
                </div>
              </div>
            </div>

            {/* Start button */}
            <Button
              variant={scoreOk ? "teal" : "ghost"}
              size="lg"
              className="w-full"
              loading={running}
              disabled={!scoreOk || running}
              icon={running ? undefined : <Play className="w-4 h-4" />}
              onClick={onStartApply}
            >
              {running ? "Applying…" : scoreOk ? "Start Auto-Apply" : `Score < ${SCORE_THRESHOLD} — Unlock Required`}
            </Button>

            {!scoreOk && resumeScore !== null && (
              <a href="/scorer">
                <Button variant="primary" size="md" className="w-full" icon={<ChevronRight className="w-4 h-4" />}>
                  Improve Score on Scorer Page
                </Button>
              </a>
            )}
          </div>

          {/* Right: live log */}
          <div className="md:col-span-3">
            <div className="bg-card border border-border rounded-2xl overflow-hidden h-full min-h-[480px] flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">Application Log</span>
                  {running && (
                    <span className="flex items-center gap-1.5 text-xs text-teal">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Running…
                    </span>
                  )}
                </div>
                {done && results.length > 0 && (
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-teal">{submitted} submitted</span>
                    <span className="text-error">{failed} failed</span>
                    {skipped > 0 && <span className="text-text-muted">{skipped} skipped</span>}
                  </div>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <AnimatePresence initial={false}>
                  {results.length === 0 && !running && (
                    <div className="flex flex-col items-center justify-center h-64 text-text-muted">
                      <Zap className="w-10 h-10 mb-3 opacity-20" />
                      <p className="text-sm">Applications will appear here as Agent 8 submits them.</p>
                      <p className="text-xs mt-1 opacity-60">Score ≥ {SCORE_THRESHOLD}/10 required to unlock.</p>
                    </div>
                  )}
                  {results.map((r, i) => (
                    <motion.div key={i}
                      initial={{ opacity: 0, x: 12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2 }}
                      className="flex items-start gap-3 rounded-xl border border-border bg-elevated p-3"
                    >
                      {statusIcon(r.status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-white truncate">{r.job_title ?? "Job"}</span>
                          {r.company && <span className="text-xs text-text-muted">@ {r.company}</span>}
                          {r.platform && <span className="text-xs text-text-muted capitalize">{r.platform}</span>}
                          <span className={statusBadge(r.status)}>{r.status}</span>
                        </div>
                        {(r.reason || r.error) && (
                          <p className="text-xs text-text-muted mt-0.5">{r.reason ?? r.error}</p>
                        )}
                        {r.match_score && (
                          <p className="text-xs text-accent mt-0.5">{Math.round(r.match_score * 100)}% match</p>
                        )}
                      </div>
                      {r.url && (
                        <a href={r.url} target="_blank" rel="noopener noreferrer"
                          className="text-text-muted hover:text-white transition-colors flex-shrink-0">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>

              {done && results.length > 0 && (
                <div className="border-t border-border px-5 py-3">
                  <a href="/tracker">
                    <Button variant="ghost" size="sm" icon={<ChevronRight className="w-4 h-4" />}>
                      View all in Tracker
                    </Button>
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <ResumeImporter
        open={importOpen}
        onOpenChange={setImportOpen}
        onImport={({ resumeData }) => {
          useResumeStore.getState().importResumeData(resumeData);
          setResumeLoaded(true);
          setResumeScore(null);
          toast("Resume loaded");
        }}
      />
    </div>
  );
}
