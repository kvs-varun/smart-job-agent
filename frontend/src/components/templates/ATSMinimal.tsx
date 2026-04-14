"use client";

import * as React from "react";

import { useResumeStore } from "@/store/resumeStore";
import type { EducationEntry, ExperienceEntry, ProjectEntry } from "@/types/resume";

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
        fontFamily: "Calibri, Arial, sans-serif",
        fontSize: "10.5pt",
        lineHeight: "1.4",
        color: "#111827",
        backgroundColor: "#FFFFFF",
        padding: "0.65in",
        minHeight: "11in",
        width: "8.5in",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      <div style={{ textAlign: "center", marginBottom: "4px" }}>
        <h1
          style={{
            fontSize: "18pt",
            fontWeight: "bold",
            color: "#1B3A6B",
            margin: 0,
            letterSpacing: "0.5px",
          }}
        >
          {resume?.contact?.name || "Your Full Name"}
        </h1>
        <p
          style={{
            fontSize: "11pt",
            color: resume?.contact?.jobTitle ? "#4B5563" : "#9CA3AF",
            margin: "2px 0 0 0",
          }}
        >
          {resume?.contact?.jobTitle || "Your Target Job Title"}
        </p>
      </div>

      <div
        style={{
          textAlign: "center",
          fontSize: "9.5pt",
          color: "#6B7280",
          borderBottom: "1.5px solid #1B3A6B",
          paddingBottom: "6px",
          marginBottom: "10px",
          marginTop: "4px",
        }}
      >
        {contactFields.length > 0 ? (
          contactLine
        ) : (
          <span style={{ color: "#9CA3AF" }}>
            your.email@example.com  |  +91 XXXXX XXXXX  |  Your City, India
          </span>
        )}
      </div>

      {resume?.summary ? (
        <ResumeSection title="PROFESSIONAL SUMMARY">
          <p style={{ margin: 0, fontSize: "10pt", lineHeight: "1.5" }}>{resume.summary}</p>
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="PROFESSIONAL SUMMARY">
          <PlaceholderLines count={3} widths={["100%", "95%", "75%"]} />
        </ResumeSection>
      ) : null}

      {resume?.skills && resume.skills.length > 0 ? (
        <ResumeSection title="TECHNICAL SKILLS">
          <p style={{ margin: 0, fontSize: "10pt", lineHeight: "1.6" }}>{resume.skills.join("  ·  ")}</p>
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="TECHNICAL SKILLS">
          <PlaceholderLines count={1} widths={["90%"]} />
        </ResumeSection>
      ) : null}

      {resume?.experience && resume.experience.length > 0 ? (
        <ResumeSection title="PROFESSIONAL EXPERIENCE">
          {resume.experience.map((exp: ExperienceEntry) => (
            <div key={exp.id} style={{ marginBottom: "8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <strong style={{ fontSize: "10.5pt", color: "#111827" }}>{[exp.title, exp.company].filter(Boolean).join(" — ")}</strong>
              </div>
              {exp.description ? (
                <div style={{ marginTop: "2px", whiteSpace: "pre-line" }}>{exp.description}</div>
              ) : null}
            </div>
          ))}
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="PROFESSIONAL EXPERIENCE">
          <PlaceholderExperience />
          <PlaceholderExperience />
        </ResumeSection>
      ) : null}

      {resume?.projects && resume.projects.length > 0 ? (
        <ResumeSection title="PROJECTS">
          {resume.projects.map((p: ProjectEntry) => (
            <div key={p.id} style={{ marginBottom: "8px" }}>
              <strong style={{ fontSize: "10.5pt", color: "#111827" }}>{p.name}</strong>
              {p.description ? <div style={{ marginTop: "2px" }}>{p.description}</div> : null}
            </div>
          ))}
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="KEY PROJECTS">
          <PlaceholderProject />
        </ResumeSection>
      ) : null}

      {resume?.education && resume.education.length > 0 ? (
        <ResumeSection title="EDUCATION">
          {resume.education.map((edu: EducationEntry) => (
            <div key={edu.id} style={{ marginBottom: "6px" }}>
              <strong style={{ fontSize: "10.5pt" }}>
                {[edu.degree, edu.institution, edu.field].filter(Boolean).join(" — ")}
              </strong>
            </div>
          ))}
        </ResumeSection>
      ) : isEmpty ? (
        <ResumeSection title="EDUCATION">
          <PlaceholderLines count={2} widths={["80%", "50%"]} />
        </ResumeSection>
      ) : null}
    </div>
  );
}

function ResumeSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "12px" }}>
      <h2
        style={{
          fontSize: "10.5pt",
          fontWeight: "bold",
          color: "#1B3A6B",
          borderBottom: "1px solid #1B3A6B",
          paddingBottom: "2px",
          marginBottom: "6px",
          letterSpacing: "0.8px",
          textTransform: "uppercase",
        }}
      >
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
