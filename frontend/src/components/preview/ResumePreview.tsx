import type { ResumeData } from "@/types/resume";

export function ResumePreview({ data }: { data: ResumeData }) {
  const name = data.contact?.name || "Your Name";
  const summary = data.summary || "";

  return (
    <div
      style={{
        background: "var(--color-resume-bg)",
        color: "var(--color-resume-text)",
        borderRadius: 12,
        border: "1px solid rgba(15,23,42,0.12)",
        padding: 18,
        fontFamily: "Calibri, Arial, sans-serif",
        minHeight: 620,
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 6 }}>{name}</div>
      <div style={{ fontSize: 11, marginBottom: 12, opacity: 0.8 }}>
        Email: {data.contact?.email || "your.email@example.com"} | Phone: {data.contact?.phone || "+91-XXXXXXXXXX"} | Location: {data.contact?.location || "India"}
      </div>

      <Section title="SUMMARY">
        <div style={{ fontSize: 12, lineHeight: 1.45 }}>{summary}</div>
      </Section>

      <Section title="SKILLS">
        <div style={{ fontSize: 12, lineHeight: 1.45 }}>{(data.skills || []).join(", ")}</div>
      </Section>

      {data.projects && data.projects.length > 0 ? (
        <Section title="PROJECTS">
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, lineHeight: 1.45 }}>
            {data.projects.map((x) => (
              <li key={x.id}>{x.name}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {data.education && data.education.length > 0 ? (
        <Section title="EDUCATION">
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, lineHeight: 1.45 }}>
            {data.education.map((x) => (
              <li key={x.id}>{[x.degree, x.institution].filter(Boolean).join(" — ")}</li>
            ))}
          </ul>
        </Section>
      ) : null}

      {data.experience && data.experience.length > 0 ? (
        <Section title="EXPERIENCE">
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, lineHeight: 1.45 }}>
            {data.experience.map((x) => (
              <li key={x.id}>{[x.title, x.company].filter(Boolean).join(" — ")}</li>
            ))}
          </ul>
        </Section>
      ) : null}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 800, borderBottom: "1px solid rgba(15,23,42,0.18)", paddingBottom: 4 }}>
        {title}
      </div>
      <div style={{ marginTop: 6 }}>{children}</div>
    </div>
  );
}
