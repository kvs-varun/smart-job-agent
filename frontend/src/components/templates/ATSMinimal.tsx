"use client";

import * as React from "react";

import { useResumeStore } from "@/store/resumeStore";
import type { AchievementEntry, CertificationEntry, EducationEntry, ExperienceEntry, LanguageEntry, OpenSourceEntry, ProjectEntry, VolunteeringEntry } from "@/types/resume";

// ─── Professional Color Palette ───────────────────────────────────────────────
// Based on Harvard/Jake's Resume standards: near-black text, charcoal accents
// No bright colors — recruiters and ATS parsers both prefer monochrome
const C = {
  name:        "#0F1923",   // Near-black — commanding, authoritative
  jobTitle:    "#374151",   // Charcoal gray — professional subtitle
  contact:     "#4B5563",   // Medium gray — readable, not distracting
  divider:     "#9CA3AF",   // Light gray rule — subtle, not colored
  sectionHead: "#0F1923",   // Same dark as name — consistent authority
  bodyText:    "#1F2937",   // Dark charcoal — warm black, easy to read
  bullet:      "#1F2937",   // Same as body
  highlight:   "#374151",   // Charcoal for bold labels
  linkColor:   "#374151",   // No blue links — keeps professional monochrome
  border:      "#D1D5DB",   // Very light gray for subtle borders
  placeholder: "#E5E7EB",   // Ghost color for empty state preview
} as const;

export function ATSMinimal() {
  const { resumeData: resume } = useResumeStore();

  const isEmpty = !resume?.contact?.name || resume.contact.name === "";

  const contactFields = [
    resume?.contact?.email,
    resume?.contact?.phone,
    resume?.contact?.location,
    resume?.contact?.linkedin,
    resume?.contact?.github,
    resume?.contact?.portfolio,
  ].filter(Boolean) as string[];

  const contactLine = contactFields.join("  |  ");

  return (
    <div
      id="ats-resume-output"
      style={{
        fontFamily: "'Times New Roman', Georgia, serif",
        fontSize: "10.5pt",
        lineHeight: "1.45",
        color: C.bodyText,
        backgroundColor: "#FFFFFF",
        padding: "0.6in 0.7in",
        minHeight: "11in",
        width: "8.5in",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      {/* ── Header ── */}
      <div style={{ textAlign: "center", marginBottom: "6px" }}>
        <h1 style={{ fontSize: "20pt", fontWeight: "700", color: C.name, margin: 0, letterSpacing: "1px", fontFamily: "'Times New Roman', Georgia, serif" }}>
          {resume?.contact?.name || "Your Full Name"}
        </h1>
        {resume?.contact?.jobTitle ? (
          <p style={{ fontSize: "10.5pt", color: C.jobTitle, margin: "2px 0 0 0", fontStyle: "italic", letterSpacing: "0.3px" }}>
            {resume.contact.jobTitle}
          </p>
        ) : null}
      </div>

      {/* ── Contact line ── */}
      <div style={{ textAlign: "center", fontSize: "9.5pt", color: C.contact, borderBottom: `1.5px solid ${C.divider}`, paddingBottom: "7px", marginBottom: "11px", marginTop: "4px" }}>
        {contactFields.length > 0 ? contactLine : (
          <span style={{ color: C.placeholder }}>your.email@example.com  |  +91 XXXXX XXXXX  |  Your City, India</span>
        )}
      </div>

      {/* ── Professional Summary ── */}
      {resume?.summary ? (
        <ResumeSection title="Professional Summary">
          <p style={{ margin: 0, fontSize: "10pt", lineHeight: "1.55", color: C.bodyText, textAlign: "justify" }}>{resume.summary}</p>
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="Professional Summary">
          <PlaceholderLines count={3} widths={["100%", "95%", "75%"]} />
        </ResumeSection>
      ) : null}

      {/* ── Technical Skills ── */}
      {resume?.skills && resume.skills.length > 0 ? (
        <ResumeSection title="Technical Skills">
          <p style={{ margin: 0, fontSize: "10pt", lineHeight: "1.6", color: C.bodyText }}>{resume.skills.join("  ·  ")}</p>
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="Technical Skills">
          <PlaceholderLines count={1} widths={["90%"]} />
        </ResumeSection>
      ) : null}

      {/* ── Professional Experience ── */}
      {resume?.experience && resume.experience.length > 0 ? (
        <ResumeSection title="Professional Experience">
          {resume.experience.map((exp: ExperienceEntry, idx: number) => {
            const rawDesc = (exp.description || "").trim();
            const descLines = rawDesc.split(/\n/).map((l: string) => l.trim()).filter(Boolean);
            const hasBullets = descLines.some((l: string) => /^[•\-–*]/.test(l));
            const dateRange = [exp.startDate, exp.endDate || (exp.current ? "Present" : "")].filter(Boolean).join(" – ");

            return (
              <div key={exp.id} style={{ marginBottom: idx < resume.experience.length - 1 ? "8px" : "0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "8px" }}>
                  <strong style={{ fontSize: "10.5pt", color: C.sectionHead, fontWeight: "700", flexShrink: 1 }}>
                    {exp.title || "Role"}{exp.company ? ` — ${exp.company}` : ""}
                  </strong>
                  {dateRange ? (
                    <span style={{ fontSize: "9.5pt", color: C.contact, whiteSpace: "nowrap", flexShrink: 0 }}>
                      {dateRange}
                    </span>
                  ) : null}
                </div>
                {exp.location ? (
                  <div style={{ fontSize: "9.5pt", color: C.contact, fontStyle: "italic", marginTop: "1px" }}>
                    {exp.location}
                  </div>
                ) : null}
                {descLines.length > 0 ? (
                  <div style={{ marginTop: "2px", fontSize: "10pt", lineHeight: "1.45", color: C.bodyText }}>
                    {hasBullets ? (
                      descLines.map((line: string, i: number) => {
                        const text = line.replace(/^[•\-–*]\s*/, "");
                        return (
                          <div key={i} style={{ display: "flex", gap: "5px", marginTop: i > 0 ? "1px" : 0 }}>
                            <span style={{ flexShrink: 0, userSelect: "none" }}>•</span>
                            <span>{text}</span>
                          </div>
                        );
                      })
                    ) : descLines.length > 1 ? (
                      descLines.map((line: string, i: number) => (
                        <div key={i} style={{ display: "flex", gap: "5px", marginTop: i > 0 ? "1px" : 0 }}>
                          <span style={{ flexShrink: 0, userSelect: "none" }}>•</span>
                          <span>{line}</span>
                        </div>
                      ))
                    ) : (
                      <div style={{ textAlign: "justify" }}>{descLines[0]}</div>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })}
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="Professional Experience">
          <PlaceholderExperience />
          <PlaceholderExperience />
        </ResumeSection>
      ) : null}

      {/* ── Projects ── */}
      {resume?.projects && resume.projects.length > 0 ? (
        <ResumeSection title="Projects">
          {resume.projects.map((p: ProjectEntry, idx: number) => {
            // Normalize description: split on newlines, trim each line, drop blanks
            const rawDesc = (p.description || "").trim();
            const descLines = rawDesc.split(/\n/).map((l: string) => l.trim()).filter(Boolean);
            const hasBullets = descLines.some((l: string) => /^[•\-–*]/.test(l));

            // Tech stack — from explicit field, or try to parse from title "(Tech: ...)"
            const techStack = p.techStack && p.techStack.length > 0 ? p.techStack : [];
            const techLine = techStack.slice(0, 6).join(" · ");

            // Clean URLs — strip protocol for display
            const githubDisplay = p.github ? p.github.replace(/^https?:\/\//, "") : null;
            const demoDisplay   = p.demo   ? p.demo.replace(/^https?:\/\//, "")   : null;

            return (
              <div key={p.id} style={{ marginBottom: idx < resume.projects.length - 1 ? "7px" : "0" }}>
                {/* ── Row 1: Project name (left) + GitHub link (right) ── */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "8px" }}>
                  <strong style={{ fontSize: "10.5pt", color: C.sectionHead, fontWeight: "700", flexShrink: 1 }}>
                    {p.name || "Untitled Project"}
                  </strong>
                  {githubDisplay ? (
                    <span style={{ fontSize: "9pt", color: C.contact, whiteSpace: "nowrap", flexShrink: 0 }}>
                      {githubDisplay}
                    </span>
                  ) : null}
                </div>

                {/* ── Row 2: Tech stack + demo (only if data exists) ── */}
                {(techLine || demoDisplay) ? (
                  <div style={{ fontSize: "9.5pt", color: C.contact, marginTop: "1px", lineHeight: "1.4" }}>
                    {techLine ? <span><em>Tech:</em> {techLine}</span> : null}
                    {demoDisplay ? (
                      <span style={{ marginLeft: techLine ? "10px" : 0 }}>
                        | <em>Demo:</em> {demoDisplay}
                      </span>
                    ) : null}
                  </div>
                ) : null}

                {/* ── Row 3: Description as proper bullets ── */}
                {descLines.length > 0 ? (
                  <div style={{ marginTop: "2px", fontSize: "10pt", lineHeight: "1.45", color: C.bodyText }}>
                    {hasBullets ? (
                      // Already bulleted — strip prefix and re-render with consistent bullet
                      descLines.map((line: string, i: number) => {
                        const text = line.replace(/^[•\-–*]\s*/, "");
                        return (
                          <div key={i} style={{ display: "flex", gap: "5px", marginTop: i > 0 ? "1px" : 0 }}>
                            <span style={{ flexShrink: 0, userSelect: "none" }}>•</span>
                            <span>{text}</span>
                          </div>
                        );
                      })
                    ) : descLines.length > 1 ? (
                      // Multi-line plain text — treat each line as a bullet
                      descLines.map((line: string, i: number) => (
                        <div key={i} style={{ display: "flex", gap: "5px", marginTop: i > 0 ? "1px" : 0 }}>
                          <span style={{ flexShrink: 0, userSelect: "none" }}>•</span>
                          <span>{line}</span>
                        </div>
                      ))
                    ) : (
                      // Single paragraph — render inline, no bullet needed
                      <div style={{ textAlign: "justify" }}>{descLines[0]}</div>
                    )}
                  </div>
                ) : null}
              </div>
            );
          })}
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="Projects">
          <PlaceholderProject />
        </ResumeSection>
      ) : null}

      {/* ── Education ── */}
      {resume?.education && resume.education.length > 0 ? (
        <ResumeSection title="Education">
          {resume.education.map((edu: EducationEntry) => (
            <div key={edu.id} style={{ marginBottom: "7px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <strong style={{ fontSize: "10.5pt", color: C.sectionHead, fontWeight: "700" }}>
                  {[edu.degree, edu.field ? `in ${edu.field}` : ""].filter(Boolean).join(" ")}
                </strong>
                <span style={{ fontSize: "9.5pt", color: C.contact, whiteSpace: "nowrap", marginLeft: "8px" }}>
                  {[edu.startYear, edu.endYear].filter(Boolean).join(" – ")}
                </span>
              </div>
              <div style={{ fontSize: "10pt", color: C.bodyText }}>{edu.institution}</div>
              {edu.grade ? <div style={{ fontSize: "9.5pt", color: C.contact }}>{edu.grade}</div> : null}
            </div>
          ))}
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="Education">
          <PlaceholderLines count={2} widths={["80%", "50%"]} />
        </ResumeSection>
      ) : null}

      {/* ── Certifications ── */}
      {resume?.certifications && resume.certifications.length > 0 ? (
        <ResumeSection title="Certifications">
          {resume.certifications.map((cert: CertificationEntry) => (
            <div key={cert.id} style={{ marginBottom: "5px", display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <strong style={{ fontSize: "10pt", color: C.sectionHead }}>{cert.name}</strong>
                {cert.issuer ? <span style={{ fontSize: "9.5pt", color: C.contact }}> — {cert.issuer}</span> : null}
                {cert.credentialURL ? <span style={{ fontSize: "9pt", color: C.contact, marginLeft: "6px" }}> [Credential]</span> : null}
              </div>
              {cert.issuedDate ? (
                <span style={{ fontSize: "9.5pt", color: C.contact, whiteSpace: "nowrap", marginLeft: "8px" }}>
                  {cert.issuedDate}{cert.expiryDate ? ` – ${cert.expiryDate}` : ""}
                </span>
              ) : null}
            </div>
          ))}
        </ResumeSection>
      ) : null}

      {/* ── Achievements ── */}
      {resume?.achievements && resume.achievements.length > 0 ? (
        <ResumeSection title="Achievements & Awards">
          {resume.achievements.map((ach: AchievementEntry) => (
            <div key={ach.id} style={{ marginBottom: "4px", display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <strong style={{ fontSize: "10pt", color: C.sectionHead }}>{ach.title}</strong>
                {ach.description ? <span style={{ fontSize: "9.5pt", color: C.bodyText }}> — {ach.description}</span> : null}
              </div>
              {ach.date ? <span style={{ fontSize: "9.5pt", color: C.contact, whiteSpace: "nowrap", marginLeft: "8px" }}>{ach.date}</span> : null}
            </div>
          ))}
        </ResumeSection>
      ) : null}

      {/* ── Open Source ── */}
      {resume?.openSource && resume.openSource.length > 0 ? (
        <ResumeSection title="Open Source Contributions">
          {resume.openSource.map((os: OpenSourceEntry) => (
            <div key={os.id} style={{ marginBottom: "5px" }}>
              <strong style={{ fontSize: "10pt", color: C.sectionHead }}>{os.project}</strong>
              {os.github ? <span style={{ fontSize: "9.5pt", color: C.contact, marginLeft: "6px" }}>{os.github}</span> : null}
              {os.contribution ? <div style={{ fontSize: "9.5pt", color: C.bodyText, marginTop: "1px" }}>{os.contribution}</div> : null}
            </div>
          ))}
        </ResumeSection>
      ) : null}

      {/* ── Volunteering ── */}
      {resume?.volunteering && resume.volunteering.length > 0 ? (
        <ResumeSection title="Volunteering & Community">
          {resume.volunteering.map((vol: VolunteeringEntry) => (
            <div key={vol.id} style={{ marginBottom: "5px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <strong style={{ fontSize: "10pt", color: C.sectionHead }}>{vol.role}{vol.organization ? ` — ${vol.organization}` : ""}</strong>
                <span style={{ fontSize: "9.5pt", color: C.contact, marginLeft: "8px" }}>{[vol.startDate, vol.endDate].filter(Boolean).join(" – ")}</span>
              </div>
              {vol.description ? <div style={{ fontSize: "9.5pt", color: C.bodyText }}>{vol.description}</div> : null}
            </div>
          ))}
        </ResumeSection>
      ) : null}

      {/* ── Languages ── */}
      {resume?.languages && resume.languages.length > 0 ? (
        <ResumeSection title="Languages">
          <p style={{ margin: 0, fontSize: "10pt", color: C.bodyText }}>
            {resume.languages.map((l: LanguageEntry) => l.proficiency ? `${l.language} (${l.proficiency})` : l.language).join("  ·  ")}
          </p>
        </ResumeSection>
      ) : null}
    </div>
  );
}

function ResumeSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "13px" }}>
      <h2 style={{
        fontSize: "10.5pt",
        fontWeight: "700",
        color: C.sectionHead,
        borderBottom: `1px solid ${C.divider}`,
        paddingBottom: "2px",
        marginBottom: "6px",
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        fontFamily: "'Times New Roman', Georgia, serif",
      }}>
        {title}
      </h2>
      {children}
    </div>
  );
}

function PlaceholderLines({ count, widths }: { count: number; widths: string[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            height: "10px",
            width: widths[i] || "80%",
            backgroundColor: "#E5E7EB",
            borderRadius: "3px",
          }}
        />
      ))}
    </div>
  );
}

function PlaceholderExperience() {
  return (
    <div style={{ marginBottom: "12px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
        <div style={{ height: "11px", width: "200px", backgroundColor: "#D1D5DB", borderRadius: "3px" }} />
        <div style={{ height: "11px", width: "100px", backgroundColor: "#E5E7EB", borderRadius: "3px" }} />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "5px", paddingLeft: "12px" }}>
        {["96%", "88%", "72%"].map((w, i) => (
          <div key={i} style={{ height: "9px", width: w, backgroundColor: "#F3F4F6", borderRadius: "3px" }} />
        ))}
      </div>
    </div>
  );
}

function PlaceholderProject() {
  return (
    <div style={{ marginBottom: "8px" }}>
      <div
        style={{
          height: "11px",
          width: "180px",
          backgroundColor: "#D1D5DB",
          borderRadius: "3px",
          marginBottom: "6px",
        }}
      />
      <PlaceholderLines count={2} widths={["90%", "70%"]} />
    </div>
  );
}
