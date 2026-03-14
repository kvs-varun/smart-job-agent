export default function Home() {
  return (
    <div style={{ padding: "40px 0 60px" }}>
      <section className="card" style={{ padding: 22, boxShadow: "var(--shadow)" }}>
        <div style={{ display: "grid", gap: 12 }}>
          <h1 className="h1" style={{ fontSize: 44, lineHeight: 1.05 }}>
            <span className="gradientText">Your Resume. Tailored for Every Job.</span>
            <br />
            Powered by AI.
          </h1>
          <p className="muted" style={{ fontSize: 18, lineHeight: 1.5, maxWidth: 780 }}>
            Upload your resume or build from scratch. Our engine scores it against any job description, helps you fix gaps ethically,
            and generates an ATS-friendly PDF in minutes.
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 6 }}>
            <a
              href="/builder"
              style={{
                background: "linear-gradient(180deg, rgba(99,102,241,0.95), rgba(79,70,229,0.85))",
                border: "1px solid rgba(99,102,241,0.45)",
                padding: "10px 14px",
                borderRadius: 12,
                color: "white",
              }}
            >
              Build My Resume →
            </a>
            <a
              href="/jd-match"
              style={{
                background: "rgba(30,41,59,0.35)",
                border: "1px solid var(--border)",
                padding: "10px 14px",
                borderRadius: 12,
              }}
            >
              See Job Match →
            </a>
          </div>
        </div>
      </section>

      <section style={{ marginTop: 14, display: "grid", gap: 12 }}>
        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: "grid", gap: 6 }}>
            <div style={{ fontFamily: "var(--font-heading)", fontWeight: 700 }}>What you get</div>
            <div className="muted" style={{ lineHeight: 1.55 }}>
              - ATS-friendly one-page PDF
              <br />- JD match analysis (matched + missing skills)
              <br />- Ethical tailoring (no fake experience)
              <br />- Ready-to-send cold email + LinkedIn message
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
