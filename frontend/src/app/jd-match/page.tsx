export default function JDMatchPage() {
  return (
    <div style={{ padding: "22px 0 60px" }}>
      <section className="card" style={{ padding: 18 }}>
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: 22 }}>JD Match</div>
          <div className="muted" style={{ lineHeight: 1.55 }}>
            This page will become the Job Description Intelligence Engine (match score, gaps, tailoring, ATS simulation) powered by the
            existing Flask pipeline via the <code>/flask/*</code> proxy.
          </div>
        </div>
      </section>
    </div>
  );
}
