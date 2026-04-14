"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import {
  Brain,
  ClipboardPaste,
  FileText,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { ResumePreview } from "@/components/preview/ResumePreview";
import { ResumeImporter } from "@/components/importer/ResumeImporter";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { analyzeJDMatch } from "@/lib/flaskApi";
import { EMPTY_RESUME } from "@/types/resume";
import type { ResumeData } from "@/types/resume";
import { useResumeStore } from "@/store/resumeStore";

type SkillStatus = "found" | "missing" | "not_found";

export default function JDMatchPage() {
  const [jdText, setJdText] = React.useState("");
  const [resumeText, setResumeText] = React.useState("");
  const [resumeData, setResumeData] = React.useState<ResumeData>(EMPTY_RESUME);
  const [analyzed, setAnalyzed] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [diffOpen, setDiffOpen] = React.useState(false);
  const [importOpen, setImportOpen] = React.useState(false);

  const [matchScore, setMatchScore] = React.useState<number>(0);
  const [jobSkills, setJobSkills] = React.useState<string[]>([]);
  const [matchedSkills, setMatchedSkills] = React.useState<string[]>([]);
  const [missingSkills, setMissingSkills] = React.useState<string[]>([]);
  const [additionalSkills, setAdditionalSkills] = React.useState<string[]>([]);

  const [resumeKeywords, setResumeKeywords] = React.useState<string[]>([]);
  const [jdKeywords, setJdKeywords] = React.useState<string[]>([]);
  const [keywordOverlap, setKeywordOverlap] = React.useState<string[]>([]);
  const [keywordGaps, setKeywordGaps] = React.useState<string[]>([]);
  const [recommendations, setRecommendations] = React.useState<string[]>([]);

  const storeResumeData = useResumeStore((s) => s.resumeData);

  async function onAnalyze() {
    if (!jdText.trim()) {
      toast("Paste a job description first.");
      return;
    }
    if (!resumeText.trim()) {
      toast("Upload your resume first.");
      return;
    }
    setBusy(true);
    setErrorMessage(null);
    try {
      const resp = await analyzeJDMatch(storeResumeData, jdText);

      console.log("JDMatch analyzeJDMatch response:", resp);
      console.log("JDMatch analyzeJDMatch response.llm:", (resp as any)?.llm);

      const anyResp = resp as any;
      const llm = (anyResp.llm || anyResp.llm_result || anyResp.llmResult || {}) as any;

      const scoreRaw =
        llm.match_score ??
        llm.matchScore ??
        llm.match_percentage ??
        llm.matchPercentage ??
        llm.score ??
        llm.match ??
        anyResp.match_score ??
        anyResp.matchScore ??
        anyResp.match_percentage ??
        anyResp.matchPercentage ??
        anyResp.score ??
        0;
      const scoreNum = typeof scoreRaw === "number" ? scoreRaw : Number(scoreRaw);

      const matched =
        (llm.matched_skills || llm.matchedSkills || llm.matched || llm.skills_matched || llm.skillsMatched || []) as string[];
      const missing =
        (llm.missing_skills || llm.missingSkills || llm.missing || llm.skills_missing || llm.skillsMissing || []) as string[];
      const additional =
        (llm.additional_skills || llm.additionalSkills || llm.additional || llm.extra_skills || llm.extraSkills || []) as string[];

      const keywordAnalysis = (anyResp.keyword_analysis || anyResp.keywordAnalysis || {}) as any;
      const resumeKw = (keywordAnalysis.resume_keywords || keywordAnalysis.resumeKeywords || []) as string[];
      const jdKw = (keywordAnalysis.jd_keywords || keywordAnalysis.jdKeywords || []) as string[];
      const overlapKw = (keywordAnalysis.overlap || keywordAnalysis.overlap_keywords || keywordAnalysis.overlapKeywords || []) as string[];
      const gapsKw =
        (anyResp.keyword_gaps || anyResp.keywordGaps || keywordAnalysis.gaps || keywordAnalysis.gap_keywords || keywordAnalysis.gapKeywords || keywordAnalysis.keyword_gaps || keywordAnalysis.keywordGaps || []) as string[];

      setMatchScore(Math.max(0, Math.min(100, Math.round(Number.isFinite(scoreNum) ? scoreNum : 0))));
      setMatchedSkills((matched || []).filter(Boolean));
      setMissingSkills((missing || []).filter(Boolean));
      setAdditionalSkills((additional || []).filter(Boolean));

      const allSkills = new Set<string>();
      for (const s of matched || []) allSkills.add(s);
      for (const s of missing || []) allSkills.add(s);
      for (const s of additional || []) allSkills.add(s);
      setJobSkills(Array.from(allSkills));

      setResumeKeywords((resumeKw || []).filter(Boolean));
      setJdKeywords((jdKw || []).filter(Boolean));
      setKeywordOverlap((overlapKw || []).filter(Boolean));
      setKeywordGaps((gapsKw || []).filter(Boolean));
      setRecommendations(((anyResp.recommendations || anyResp.recommendation || anyResp.recs || []) as string[]).filter(Boolean));

      setAnalyzed(true);
      toast("JD match analysis ready");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to analyze job match";
      setErrorMessage(msg);
      setAnalyzed(false);
      toast(msg);
    } finally {
      setBusy(false);
    }
  }

  const allJobSkills = React.useMemo(() => {
    const set = new Set<string>();
    for (const s of jobSkills) set.add(s);
    for (const s of matchedSkills) set.add(s);
    for (const s of missingSkills) set.add(s);
    return Array.from(set);
  }, [jobSkills, matchedSkills, missingSkills]);

  const matchLabel = React.useMemo(() => {
    if (matchScore >= 80) return "Strong Match";
    if (matchScore >= 55) return "Partial Match";
    return "Needs Work";
  }, [matchScore]);

  return (
    <div className="fixed inset-x-0 bottom-0 top-16 bg-[#0F172A]">
      <div className="flex h-full overflow-hidden">
        <section className="w-[320px] flex-shrink-0 border-r border-[#334155] bg-[#1E293B] overflow-hidden">
          <div className="h-14 flex items-center justify-between px-4 border-b border-[#334155]">
            <div className="flex items-center gap-2 text-white">
              <ClipboardPaste className="w-4 h-4 text-[#6366F1]" />
              <span className="font-heading font-semibold text-sm">Paste Job Description</span>
            </div>
          </div>

          <div className="p-4 h-[calc(100%-56px)] overflow-y-auto">
            <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold mb-2">Resume</div>
            <Button
              variant="ghost"
              size="lg"
              className="w-full"
              icon={<FileText className="w-4 h-4" />}
              onClick={() => setImportOpen(true)}
              disabled={busy}
              type="button"
            >
              Upload Resume
            </Button>

            {resumeText.trim() ? (
              <div className="mt-3 text-xs text-[#94A3B8]">Resume loaded: {resumeData.contact?.name || "(name not found)"}</div>
            ) : (
              <div className="mt-3 text-xs text-[#64748B]">Upload a PDF/DOCX to analyze JD match.</div>
            )}

            <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold mb-2 mt-4">Job description</div>
            <textarea
              className={cn(
                "w-full rounded-xl border border-[#334155] bg-[#243044] px-4 py-3 text-sm text-white",
                "placeholder:text-[#64748B] focus:border-[#6366F1] focus:ring-2 focus:ring-[#6366F1]/20 transition-all outline-none resize-none"
              )}
              rows={16}
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the full job description here — job title, requirements, responsibilities..."
              disabled={busy}
            />

            <div className="mt-4">
              <Button loading={busy} className="w-full" size="lg" onClick={onAnalyze} icon={<Target className="w-4 h-4" />}>
                Analyze Job →
              </Button>
            </div>

            {analyzed ? (
              <div className="mt-6 rounded-2xl border border-[#334155] bg-[#243044]/40 p-4">
                <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Extracted</div>
                <div className="mt-3">
                  <div className="text-sm font-semibold text-white">Role</div>
                  <div className="text-sm text-[#94A3B8]">Backend Engineer (Fresher)</div>
                </div>
                <div className="mt-4">
                  <div className="text-sm font-semibold text-white">Job skills</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {allJobSkills.slice(0, 12).map((s) => (
                      <span key={s} className="px-2.5 py-1 rounded-full bg-[#10B981]/15 border border-[#10B981]/25 text-[#6EE7B7] text-xs font-medium">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                icon={<Brain className="w-10 h-10" />}
                title="No analysis yet"
                subtitle="Paste a job description and click Analyze Job."
              />
            )}
          </div>
        </section>

        <section className="flex-1 overflow-hidden">
          <div className="h-14 flex items-center justify-between px-6 border-b border-[#334155]">
            <div className="flex items-center gap-2 text-white">
              <Brain className="w-4 h-4 text-[#14B8A6]" />
              <span className="font-heading font-semibold text-sm">Match Analysis</span>
            </div>
            <div className="text-xs text-[#64748B]">JD-specific</div>
          </div>

          <div className="h-[calc(100%-56px)] flex flex-col overflow-hidden">
            <div className="flex-1 min-h-0 overflow-y-auto p-6">
              {analyzed ? (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }} className="grid gap-6">
                  <JDMatchScoreCard score={matchScore} label={matchLabel} />

                  <div className="mt-0 bg-[#1E293B] rounded-xl border border-[#334155] overflow-hidden">
                    <div className="px-4 py-3 border-b border-[#334155]">
                      <h3 className="text-sm font-semibold text-white">Skills Matrix</h3>
                      <p className="text-xs text-[#64748B] mt-1">Matched, missing, and additional skills detected.</p>
                    </div>
                    <div className="p-4 grid gap-4">
                      <div>
                        <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Matched</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {(matchedSkills || []).length === 0 ? (
                            <span className="text-sm text-[#94A3B8]">None</span>
                          ) : (
                            matchedSkills.map((s) => (
                              <span
                                key={s}
                                className="px-2.5 py-1 rounded-full bg-[#10B981]/15 border border-[#10B981]/25 text-[#6EE7B7] text-xs font-medium"
                              >
                                {s}
                              </span>
                            ))
                          )}
                        </div>
                      </div>

                      <div>
                        <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Missing</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {(missingSkills || []).length === 0 ? (
                            <span className="text-sm text-[#94A3B8]">None</span>
                          ) : (
                            missingSkills.map((s) => (
                              <span
                                key={s}
                                className="px-2.5 py-1 rounded-full bg-[#F59E0B]/15 border border-[#F59E0B]/25 text-[#FCD34D] text-xs font-medium"
                              >
                                {s}
                              </span>
                            ))
                          )}
                        </div>
                      </div>

                      <div>
                        <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Additional</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {(additionalSkills || []).length === 0 ? (
                            <span className="text-sm text-[#94A3B8]">None</span>
                          ) : (
                            additionalSkills.map((s) => (
                              <span
                                key={s}
                                className="px-2.5 py-1 rounded-full bg-[#334155]/60 border border-[#475569] text-[#E2E8F0] text-xs font-medium"
                              >
                                {s}
                              </span>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-0 bg-[#1E293B] rounded-xl border border-[#334155] overflow-hidden">
                    <div className="px-4 py-3 border-b border-[#334155]">
                      <h3 className="text-sm font-semibold text-white">Keyword Comparison</h3>
                      <p className="text-xs text-[#64748B] mt-1">JD keywords vs resume keywords (overlap highlighted).</p>
                    </div>

                    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="rounded-xl border border-[#334155] bg-[#243044]/30 overflow-hidden">
                        <div className="px-3 py-2 border-b border-[#334155] text-xs font-semibold text-[#94A3B8]">JD Keywords</div>
                        <div className="p-3 flex flex-wrap gap-2">
                          {jdKeywords.length === 0 ? (
                            <span className="text-sm text-[#94A3B8]">None</span>
                          ) : (
                            jdKeywords.slice(0, 40).map((kw) => {
                              const isOverlap = keywordOverlap.some((x) => x.toLowerCase() === kw.toLowerCase());
                              return (
                                <span
                                  key={kw}
                                  className={cn(
                                    "px-2.5 py-1 rounded-full border text-xs font-medium",
                                    isOverlap
                                      ? "bg-[#10B981]/15 border-[#10B981]/25 text-[#6EE7B7]"
                                      : "bg-[#334155]/60 border-[#475569] text-[#E2E8F0]"
                                  )}
                                >
                                  {kw}
                                </span>
                              );
                            })
                          )}
                        </div>
                      </div>

                      <div className="rounded-xl border border-[#334155] bg-[#243044]/30 overflow-hidden">
                        <div className="px-3 py-2 border-b border-[#334155] text-xs font-semibold text-[#94A3B8]">Resume Keywords</div>
                        <div className="p-3 flex flex-wrap gap-2">
                          {resumeKeywords.length === 0 ? (
                            <span className="text-sm text-[#94A3B8]">None</span>
                          ) : (
                            resumeKeywords.slice(0, 40).map((kw) => {
                              const isOverlap = keywordOverlap.some((x) => x.toLowerCase() === kw.toLowerCase());
                              return (
                                <span
                                  key={kw}
                                  className={cn(
                                    "px-2.5 py-1 rounded-full border text-xs font-medium",
                                    isOverlap
                                      ? "bg-[#10B981]/15 border-[#10B981]/25 text-[#6EE7B7]"
                                      : "bg-[#334155]/60 border-[#475569] text-[#E2E8F0]"
                                  )}
                                >
                                  {kw}
                                </span>
                              );
                            })
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="px-4 pb-4">
                      <div className="rounded-xl border border-[#334155] bg-[#243044]/30 p-4">
                        <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Gaps</div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {keywordGaps.length === 0 ? (
                            <span className="text-sm text-[#94A3B8]">No gaps found.</span>
                          ) : (
                            keywordGaps.slice(0, 30).map((kw) => (
                              <span
                                key={kw}
                                className="px-2.5 py-1 rounded-full bg-[#F59E0B]/15 border border-[#F59E0B]/25 text-[#FCD34D] text-xs font-medium"
                              >
                                {kw}
                              </span>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-0 bg-[#1E293B] rounded-xl border border-[#334155] p-4">
                    <h3 className="text-sm font-semibold text-white mb-2">Recommendations</h3>
                    {recommendations.length === 0 ? (
                      <div className="text-sm text-[#94A3B8]">No recommendations returned.</div>
                    ) : (
                      <ul className="mt-3 space-y-2 text-sm text-[#E2E8F0] list-disc pl-5">
                        {recommendations.map((r, idx) => (
                          <li key={`${idx}-${r}`}>{r}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </motion.div>
              ) : (
                <div className="flex-1 flex items-center justify-center">
                  <EmptyState
                    icon={<Target className="w-10 h-10" />}
                    title="Paste a JD to begin"
                    subtitle="You’ll see match score, missing skills, and suggested edits here."
                  />
                </div>
              )}

              {errorMessage ? (
                <div className="mt-4 rounded-xl border border-[#EF4444]/30 bg-[#EF4444]/10 p-4">
                  <div className="text-sm font-semibold text-[#FCA5A5]">Analysis failed</div>
                  <div className="text-sm text-[#FECACA] mt-1">{errorMessage}</div>
                </div>
              ) : null}
            </div>

            <div className="flex-shrink-0 border-t border-[#334155] bg-[#0F172A] p-4">
              <div className="grid grid-cols-1 gap-3">
                <Button
                  variant="primary"
                  size="lg"
                  icon={<Sparkles className="w-4 h-4" />}
                  onClick={() => setDiffOpen(true)}
                  disabled={!analyzed}
                  type="button"
                >
                  Auto-Tailor My Resume
                </Button>
                <Button
                  variant="teal"
                  size="lg"
                  icon={<FileText className="w-4 h-4" />}
                  onClick={() => toast("Generate cover letter — coming soon")}
                  disabled={!analyzed}
                  type="button"
                >
                  Generate Cover Letter
                </Button>
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={() => toast("Write outreach email — coming soon")}
                  disabled={!analyzed}
                  type="button"
                >
                  Write Outreach Email
                </Button>
              </div>
            </div>
          </div>
        </section>

        <section className="w-[380px] flex-shrink-0 border-l border-[#334155] bg-[#0F172A] overflow-hidden hidden lg:block">
          <div className="h-14 flex items-center justify-between px-4 border-b border-[#334155]">
            <div className="text-sm font-semibold text-white">Your Resume</div>
            <div className="text-xs text-[#64748B]">Preview</div>
          </div>

          <div className="h-[calc(100%-56px)] overflow-y-auto p-4">
            <div className="w-full shadow-2xl rounded-lg overflow-hidden">
              <ResumePreview data={resumeData} />
            </div>
          </div>
        </section>
      </div>

      <ResumeImporter
        open={importOpen}
        onOpenChange={setImportOpen}
        onImport={({ resumeData }) => {
          setResumeData(resumeData);
          useResumeStore.getState().importResumeData(resumeData);
          const asText = [
            resumeData.contact?.name,
            resumeData.contact?.email,
            resumeData.contact?.phone,
            resumeData.contact?.location,
            resumeData.summary,
            (resumeData.skills || []).join(", "),
            ...(resumeData.experience || []).map((x) => [x.title, x.company, x.description].filter(Boolean).join("\n")),
            ...(resumeData.projects || []).map((x) => [x.name, x.description].filter(Boolean).join("\n")),
            ...(resumeData.education || []).map((x) => [x.degree, x.institution, x.field].filter(Boolean).join("\n")),
          ]
            .filter(Boolean)
            .join("\n\n");
          setResumeText(asText);
          setAnalyzed(false);
          toast("Resume uploaded");
        }}
      />

      <Dialog.Root open={diffOpen} onOpenChange={setDiffOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60" />
          <Dialog.Content asChild>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 10 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="fixed left-1/2 top-1/2 w-[calc(100vw-32px)] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#334155] bg-[#1E293B] p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between">
                <Dialog.Title className="font-heading font-bold text-lg text-white">Tailoring Suggestions</Dialog.Title>
                <Dialog.Close asChild>
                  <button className="text-[#94A3B8] hover:text-white">
                    <X className="w-5 h-5" />
                  </button>
                </Dialog.Close>
              </div>

              <div className="mt-4 rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Diff preview</div>
                <div className="mt-3 space-y-3 text-sm">
                  <div>
                    <div className="text-[#FCA5A5] line-through">Built an API for a college project.</div>
                    <div className="text-[#86EFAC]">Built a Flask REST API with validation and SQL-backed storage; improved response times by 20%.</div>
                  </div>
                  <div>
                    <div className="text-[#FCA5A5] line-through">Worked on backend tasks.</div>
                    <div className="text-[#86EFAC]">Implemented JWT auth, unit tests, and dockerized local dev workflow for reliable deployments.</div>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
                <Button variant="ghost" onClick={() => setDiffOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    toast("Accepted tailoring (demo). Use Builder integration next.");
                    setDiffOpen(false);
                  }}
                >
                  Accept All
                </Button>
              </div>
            </motion.div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function StatusBadge({ status }: { status: SkillStatus }) {
  if (status === "found") {
    return <span className="inline-flex rounded-full bg-[#10B981]/15 border border-[#10B981]/25 px-2.5 py-0.5 text-xs font-medium text-[#6EE7B7]">Found ✓</span>;
  }
  if (status === "missing") {
    return <span className="inline-flex rounded-full bg-[#F59E0B]/15 border border-[#F59E0B]/25 px-2.5 py-0.5 text-xs font-medium text-[#FCD34D]">Missing ⚠</span>;
  }
  return <span className="inline-flex rounded-full bg-[#EF4444]/15 border border-[#EF4444]/25 px-2.5 py-0.5 text-xs font-medium text-[#FCA5A5]">Not Found ✗</span>;
}

function JDMatchScoreCard({ score, label }: { score: number; label: string }) {
  const safe = Math.max(0, Math.min(100, Math.round(score)));
  const pct = safe / 100;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75;
  const dashOffset = arcLength - pct * arcLength;

  const stroke = safe >= 80 ? "#10B981" : safe >= 55 ? "#F59E0B" : "#EF4444";

  return (
    <div className="bg-[#1E293B] border border-[#334155] rounded-2xl p-6">
      <div className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">JD Match Score</div>
      <div className="flex flex-col items-center mb-6 mt-4">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <circle
            cx="70"
            cy="70"
            r={radius}
            fill="none"
            stroke="#334155"
            strokeWidth="10"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
            transform="rotate(-225 70 70)"
          />
          <motion.circle
            cx="70"
            cy="70"
            r={radius}
            fill="none"
            stroke={stroke}
            strokeWidth="10"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
            transform="rotate(-225 70 70)"
            initial={{ strokeDashoffset: arcLength }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.0, ease: "easeOut" }}
          />
          <text x="70" y="66" textAnchor="middle" dominantBaseline="middle" className="font-heading font-bold" fontSize="28" fill={stroke}>
            {safe}
          </text>
          <text x="70" y="84" textAnchor="middle" fontSize="11" fill="#94A3B8">
            / 100
          </text>
        </svg>
        <span className="text-sm font-medium text-[#94A3B8] mt-2">{label}</span>
      </div>
      <div className="text-xs text-[#64748B]">How well your resume matches this specific job description.</div>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mt-6 rounded-2xl border border-[#334155] bg-[#243044]/30 p-6 text-center">
      <div className="mx-auto w-fit text-[#334155]">{icon}</div>
      <div className="mt-3 font-heading font-semibold text-white">{title}</div>
      <div className="mt-2 text-sm text-[#94A3B8]">{subtitle}</div>
    </div>
  );
}
