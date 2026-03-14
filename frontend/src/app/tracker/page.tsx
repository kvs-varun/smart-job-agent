export default function TrackerPage() {
  return (
    <div style={{ padding: "22px 0 60px" }}>
      <section className="card" style={{ padding: 18 }}>
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: 22 }}>Application Tracker</div>
          <div className="muted" style={{ lineHeight: 1.55 }}>
            This page will show your application pipeline and which resume version you used for each company.
          </div>
        </div>
      </section>
    </div>
  );
}
