"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { ResumeImporter } from "@/components/importer/ResumeImporter";
import { cn } from "@/lib/utils";

function useScrollPosition(thresholdPx: number) {
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > thresholdPx);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [thresholdPx]);

  return scrolled;
}

export function Navbar() {
  const pathname = usePathname();
  const scrolled = useScrollPosition(60);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [importOpen, setImportOpen] = React.useState(false);

  function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
    const active = pathname === href;
    return (
      <Link
        href={href}
        className={cn(
          "text-sm text-[#94A3B8] hover:text-white transition-colors duration-200",
          active && "text-white relative"
        )}
      >
        {children}
        {active ? (
          <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-[#6366F1] rounded-full" />
        ) : null}
      </Link>
    );
  }

  return (
    <motion.header
      className="fixed top-0 left-0 right-0 z-50"
      animate={{
        backgroundColor: scrolled ? "rgba(15,23,42,0.90)" : "rgba(15,23,42,0)",
        borderBottomColor: scrolled ? "rgba(51,65,85,0.5)" : "rgba(51,65,85,0)",
      }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      style={{ borderBottomWidth: 1, borderBottomStyle: "solid", backdropFilter: scrolled ? "blur(12px)" : undefined }}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#6366F1]" />
            <span className="font-heading font-bold text-xl gradient-text">SmartJob</span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          <NavLink href="/builder">Builder</NavLink>
          <NavLink href="/jd-match">JD Match</NavLink>
          <NavLink href="/tracker">Tracker</NavLink>
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setImportOpen(true)}>
            Upload Resume
          </Button>
          <Link href="/builder">
            <Button variant="primary" size="sm">Start Building →</Button>
          </Link>
        </div>

        <button className="md:hidden text-[#94A3B8] hover:text-white transition-colors" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      <AnimatePresence>
        {mobileOpen ? (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="absolute top-16 left-0 right-0 bg-[#1E293B] border-b border-[#334155] md:hidden overflow-hidden"
          >
            <div className="flex flex-col px-6 py-4 gap-4">
              <NavLink href="/builder">
                <span className="font-medium text-base">Builder</span>
              </NavLink>
              <NavLink href="/jd-match">
                <span className="font-medium text-base">JD Match</span>
              </NavLink>
              <NavLink href="/tracker">
                <span className="font-medium text-base">Tracker</span>
              </NavLink>
              <div className="flex flex-col gap-3 pt-2">
                <Button variant="ghost" size="md" className="w-full" onClick={() => setImportOpen(true)}>
                  Upload Resume
                </Button>
                <Link href="/builder" className="w-full">
                  <Button variant="primary" size="md" className="w-full">Start Building →</Button>
                </Link>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <ResumeImporter
        open={importOpen}
        onOpenChange={setImportOpen}
        onImport={({ resumeData }) => {
          try {
            sessionStorage.setItem("smartjob_import_resume_data", JSON.stringify(resumeData));
          } catch {
            // ignore
          }
          window.location.href = "/builder";
        }}
      />
    </motion.header>
  );
}
