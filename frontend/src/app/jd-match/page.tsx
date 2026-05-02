"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import {
  Brain,
  ClipboardPaste,
  Download,
  FileText,
  Mail,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { ResumePreview } from "@/components/preview/ResumePreview";
import { ResumeImporter } from "@/components/importer/ResumeImporter";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { analyzeJDMatchV2, generateColdEmailV2, tailorResumeForJD } from "@/lib/agentApi";
import type { JDMatchDetails, TailoringStep, ColdEmailOutput } from "@/lib/agentApi";
import { CautionBanner } from "@/components/agents/CautionBanner";
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
  const [emailOpen, setEmailOpen] = React.useState(false);
  const [emailBusy, setEmailBusy] = React.useState(false);
  const [coldEmail, setColdEmail] = React.useState<ColdEmailOutput | null>(null);
  const [recruiterEmail, setRecruiterEmail] = React.useState("");
  const [companyName, setCompanyName] = React.useState("");
  const [roleTitleInput, setRoleTitleInput] = React.useState("");
  const [v2MatchDetails, setV2MatchDetails] = React.useState<JDMatchDetails | null>(null);
  const [tailoringPlan, setTailoringPlan] = React.useState<TailoringStep[]>([]);
  const [cautionDismissed, setCautionDismissed] = React.useState(false);
  const [proceedDespiteCaution, setProceedDespiteCaution] = React.useState(false);
  const [tailorBusy, setTailorBusy] = React.useState(false);
  const [tailoredResumeData, setTailoredResumeData] = React.useState<ResumeData | null>(null);
  const [tailoredDownloadUrl, setTailoredDownloadUrl] = React.useState<string | null>(null);
  const [tailorComplete, setTailorComplete] = React.useState(false);

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
    if (!jdText.trim()) { toast("Paste a job description first."); return; }
    if (!resumeText.trim()) { toast("Upload your resume first."); return; }
    setBusy(true);
    setErrorMessage(null);
    setTailorComplete(false);
    setTailoredResumeData(null);
    setTailoredDownloadUrl(null);
    try {
      // V2 Agent 3 — deep LLM-powered JD analysis using structured resume data
      const resp = await analyzeJDMatchV2({
        resume_text: resumeText,
        job_description: jdText,
      });
      const details = resp.jd_match_details || {} as any;

      setMatchScore(Math.round(resp.match_score ?? 0));
      setMatchedSkills((details.matched_skills || []).filter(Boolean));
      setMissingSkills((details.missing_skills || []).filter(Boolean));
      setAdditionalSkills([]);
      setJobSkills([...(details.matched_skills || []), ...(details.missing_skills || [])]);

      // Agent 3 returns keyword breakdown in details
      setJdKeywords((details.missing_skills || []).filter(Boolean));
      setResumeKeywords((details.matched_skills || []).filter(Boolean));
      setKeywordOverlap((details.matched_skills || []).filter(Boolean));
      setKeywordGaps((details.missing_skills || []).filter(Boolean));
      setRecommendations((details.recommendations || []).filter(Boolean));
      setV2MatchDetails(details as JDMatchDetails);
      setTailoringPlan(resp.tailoring_plan ?? []);
      setCautionDismissed(false);
      setProceedDespiteCaution(false);
      setAnalyzed(true);
      toast.success(`JD analysis complete — ${Math.round(resp.match_score ?? 0)}% match`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to analyze job match";
      setErrorMessage(msg);
      setAnalyzed(false);
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  }

  async function onAutoTailor() {
    if (!jdText.trim() || !resumeText.trim()) {
      toast.warning("Upload a resume and paste a job description first.");
      return;
    }
    setTailorBusy(true);
    setTailorComplete(false);
    setTailoredResumeData(null);
    setTailoredDownloadUrl(null);
    try {
      toast("AI agents rewriting your resume for this JD — ~20 seconds…");
      const resp = await tailorResumeForJD({
        resume_data: resumeData as any,
        job_description: jdText,
        selected_template: "ats_pro",
      });

      if (resp?.final_resume) {
        setTailoredResumeData(resp.final_resume as ResumeData);
        // Update store so builder gets the tailored resume
        useResumeStore.getState().importResumeData(resp.final_resume as ResumeData);
      }
      if (resp?.download_url) {
        const url = resp.download_url.startsWith("/v2/")
          ? `/api${resp.download_url}`
          : resp.download_url;
        setTailoredDownloadUrl(url);
      }
      if (resp?.jd_match_score != null) {
        setMatchScore(Math.round(resp.jd_match_score));
      }
      if (resp?.jd_match_details) {
        setV2MatchDetails(resp.jd_match_details as JDMatchDetails);
        setMatchedSkills(((resp.jd_match_details as any).matched_skills || []).filter(Boolean));
        setMissingSkills(((resp.jd_match_details as any).missing_skills || []).filter(Boolean));
        setRecommendations(((resp.jd_match_details as any).recommendations || []).filter(Boolean));
      }
      if (resp?.tailoring_plan) {
        setTailoringPlan(resp.tailoring_plan as TailoringStep[]);
      }
      setTailorComplete(true);
      setAnalyzed(true);
      toast.success("Resume rewritten for this JD ✓ — preview updated on the right");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Resume tailor failed — check backend");
    } finally {
      setTailorBusy(false);
    }
  }

  async function onWriteEmail() {
    if (!resumeText.trim()) {
      toast("Upload your resume first.");
      return;
    }
    setEmailOpen(true);
  }

  async function onGenerateColdEmail() {
    if (!recruiterEmail.trim()) { toast("Enter recruiter email."); return; }
    if (!companyName.trim())    { toast("Enter company name.");     return; }
    setEmailBusy(true);
    try {
      const resp = await generateColdEmailV2({
        resume_text: resumeText,
        recruiter_email: recruiterEmail,
        company_name: companyName,
        role_title: roleTitleInput || "Software Engineer",
        job_description: jdText || undefined,
      });
      setColdEmail(resp);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to generate email");
    } finally {
      setEmailBusy(false);
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

                  {v2MatchDetails?.caution_issued && !cautionDismissed && !proceedDespiteCaution && (
                    <CautionBanner
                      matchScore={matchScore}
                      callbackProbability={v2MatchDetails.callback_probability_pct}
                      cautionMessage={v2MatchDetails.caution_message}
                      hardGaps={v2MatchDetails.hard_gaps}
                      onOverride={() => { setProceedDespiteCaution(true); setDiffOpen(true); }}
                      onDismiss={() => setCautionDismissed(true)}
                    />
                  )}

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
                  onClick={onAutoTailor}
                  loading={tailorBusy}
                  disabled={!resumeText.trim() || !jdText.trim() || tailorBusy}
                  type="button"
                >
                  {tailorBusy ? "AI Rewriting Resume…" : tailorComplete ? "Rewrite Again for this JD" : "Rewrite Resume for this JD ✦"}
                </Button>
                {tailoredDownloadUrl && (
                  <a href={tailoredDownloadUrl} download className="w-full">
                    <Button variant="teal" size="lg" icon={<FileText className="w-4 h-4" />} className="w-full">
                      Download Tailored PDF
                    </Button>
                  </a>
                )}
                <Button
                  variant="ghost"
                  size="lg"
                  icon={<FileText className="w-4 h-4" />}
                  onClick={() => {
                    if (!resumeText.trim()) { toast("Upload your resume first."); return; }
                    try { sessionStorage.setItem("smartjob_jd_for_builder", jdText); } catch {}
                    window.location.href = "/builder";
                  }}
                  disabled={!resumeText}
                  type="button"
                >
                  Open in Builder →
                </Button>
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={onWriteEmail}
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
            <div className="text-sm font-semibold text-white">
              {tailorComplete ? (
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  JD-Tailored Resume
                </span>
              ) : "Your Resume"}
            </div>
            {tailoredDownloadUrl && (
              <a
                href={tailoredDownloadUrl}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#0D9488] hover:bg-[#0F766E] text-white text-xs font-medium transition-colors"
              >
                ↓ Download PDF
              </a>
            )}
          </div>

          <div className="h-[calc(100%-56px)] overflow-y-auto p-4">
            {tailorComplete && tailoredResumeData ? (
              <div className="mb-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-400">
                ✓ Resume fully rewritten by AI to match this JD. Skills, bullets, and summary are now
                aligned to the job requirements.
              </div>
            ) : null}
            <div className="w-full shadow-2xl rounded-lg overflow-hidden">
              <ResumePreview data={tailoredResumeData ?? resumeData} />
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

              {tailoringPlan.length > 0 ? (
                <div className="mt-4 space-y-3 max-h-80 overflow-y-auto">
                  {tailoringPlan.map((step, i) => (
                    <div key={i} className="rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs bg-[#6366F1]/20 text-[#A5B4FC] px-2 py-0.5 rounded-full font-medium">{step.section}</span>
                        <span className="text-xs text-[#64748B]">{step.action}</span>
                      </div>
                      <p className="text-sm text-[#E2E8F0]">{step.specific_change}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                  <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Tailoring plan</div>
                  <p className="text-sm text-[#94A3B8] mt-2">No tailoring steps generated. Run Auto-Tailor again with more detailed JD text.</p>
                </div>
              )}

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-end">
                <Button variant="ghost" onClick={() => setDiffOpen(false)}>Close</Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    toast("Tailoring plan copied. Apply these changes in the Builder.");
                    setDiffOpen(false);
                  }}
                >
                  Go to Builder →
                </Button>
              </div>
            </motion.div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
      {/* Cold Email Dialog */}
      <Dialog.Root open={emailOpen} onOpenChange={(open) => { setEmailOpen(open); if (!open) setColdEmail(null); }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60" />
          <Dialog.Content asChild>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 10 }}
              transition={{ duration: 0.2 }}
              className="fixed left-1/2 top-1/2 w-[calc(100vw-32px)] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[#334155] bg-[#1E293B] p-6 shadow-2xl max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-4">
                <Dialog.Title className="font-heading font-bold text-lg text-white">Write Outreach Email</Dialog.Title>
                <Dialog.Close asChild>
                  <button className="text-[#94A3B8] hover:text-white"><X className="w-5 h-5" /></button>
                </Dialog.Close>
              </div>

              {!coldEmail ? (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-[#64748B] uppercase tracking-wider font-semibold block mb-1.5">Recruiter Email *</label>
                    <input
                      type="email"
                      value={recruiterEmail}
                      onChange={(e) => setRecruiterEmail(e.target.value)}
                      placeholder="recruiter@company.com"
                      className="w-full rounded-xl border border-[#334155] bg-[#243044] px-4 py-3 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-[#64748B] uppercase tracking-wider font-semibold block mb-1.5">Company Name *</label>
                    <input
                      type="text"
                      value={companyName}
                      onChange={(e) => setCompanyName(e.target.value)}
                      placeholder="Razorpay, Google, etc."
                      className="w-full rounded-xl border border-[#334155] bg-[#243044] px-4 py-3 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-[#64748B] uppercase tracking-wider font-semibold block mb-1.5">Role Title</label>
                    <input
                      type="text"
                      value={roleTitleInput}
                      onChange={(e) => setRoleTitleInput(e.target.value)}
                      placeholder="Software Engineer"
                      className="w-full rounded-xl border border-[#334155] bg-[#243044] px-4 py-3 text-sm text-white placeholder:text-[#64748B] focus:border-[#6366F1] outline-none"
                    />
                  </div>
                  <Button variant="primary" size="lg" className="w-full" loading={emailBusy} onClick={onGenerateColdEmail}>
                    Generate Email with AI
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-[#64748B] uppercase tracking-wider font-semibold">Subject</span>
                      <span className="text-xs bg-[#6366F1]/20 text-[#A5B4FC] px-2 py-0.5 rounded-full">{coldEmail.framework}</span>
                      <span className="text-xs bg-teal/20 text-teal px-2 py-0.5 rounded-full">{coldEmail.word_count} words</span>
                    </div>
                    <p className="text-sm font-semibold text-white">{coldEmail.subject}</p>
                  </div>
                  <div className="rounded-xl border border-[#334155] bg-[#243044]/40 p-4">
                    <div className="text-xs text-[#64748B] uppercase tracking-wider font-semibold mb-2">Body</div>
                    <pre className="text-sm text-[#E2E8F0] whitespace-pre-wrap font-sans leading-relaxed">{coldEmail.body}</pre>
                  </div>
                  {coldEmail.cliches_found?.length > 0 && (
                    <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-3">
                      <p className="text-xs text-amber-400 font-semibold">AI clichés removed: {coldEmail.cliches_found.join(", ")}</p>
                    </div>
                  )}
                  <div className="flex gap-3 flex-wrap">
                    <a href={coldEmail.mailto_link} className="flex-1">
                      <Button variant="primary" size="lg" className="w-full" icon={<Mail className="w-4 h-4" />}>Open in Mail</Button>
                    </a>
                    <a href={coldEmail.gmail_url} target="_blank" rel="noopener noreferrer" className="flex-1">
                      <Button variant="teal" size="lg" className="w-full">Open in Gmail</Button>
                    </a>
                  </div>
                  <Button variant="ghost" size="sm" className="w-full" onClick={() => setColdEmail(null)}>
                    Regenerate
                  </Button>
                </div>
              )}
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
