"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href;

  return (
    <Link
      href={href}
      style={{
        padding: "8px 10px",
        borderRadius: 10,
        border: active ? "1px solid rgba(99,102,241,0.55)" : "1px solid transparent",
        background: active ? "rgba(99,102,241,0.12)" : "transparent",
        color: active ? "var(--color-text-primary)" : "var(--color-text-secondary)",
        transition: "all 200ms ease",
      }}
    >
      {label}
    </Link>
  );
}

export function Navbar() {
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 30,
        background: "rgba(15,23,42,0.78)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(148,163,184,0.14)",
      }}
    >
      <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14 }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              fontFamily: "var(--font-heading)",
              fontWeight: 800,
              letterSpacing: "-0.02em",
              fontSize: 18,
            }}
          >
            <span className="gradientText">SmartJob</span>
          </div>
        </Link>

        <nav style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
          <NavLink href="/builder" label="Builder" />
          <NavLink href="/jd-match" label="JD Match" />
          <NavLink href="/tracker" label="Tracker" />
        </nav>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <Link
            href="/builder"
            style={{
              padding: "9px 12px",
              borderRadius: 12,
              border: "1px solid rgba(99,102,241,0.45)",
              background: "linear-gradient(180deg, rgba(99,102,241,0.95), rgba(79,70,229,0.85))",
              color: "white",
            }}
          >
            Start Building →
          </Link>
        </div>
      </div>
    </header>
  );
}
