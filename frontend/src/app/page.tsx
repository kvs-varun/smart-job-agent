"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import { Brain, Sparkles, Target, Upload } from "lucide-react";

import { Button } from "@/components/ui/Button";

export default function HomePage() {
  return (
    <div>
      <Hero />
      <StatsBar />
      <HowItWorks />
      <ComparisonTable />
      <FooterCta />
    </div>
  );
}

function Hero() {
  return (
    <section className="dot-grid relative overflow-hidden">
      <div className="absolute top-0 left-0 w-[400px] h-[400px] rounded-full bg-[#6366F1]/08 blur-[120px] -translate-x-1/2 -translate-y-1/4 pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-[350px] h-[350px] rounded-full bg-[#14B8A6]/06 blur-[100px] translate-x-1/4 translate-y-1/4 pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 min-h-[calc(100vh-64px)] flex flex-col justify-center py-10">
        <div className="text-center">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#6366F1]/30 bg-[#6366F1]/10 text-[#A5B4FC] text-sm font-medium">
              <Sparkles className="w-3.5 h-3.5" />
              AI-Powered Resume Intelligence
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="font-heading font-extrabold text-[44px] md:text-[56px] leading-tight text-center mt-6"
          >
            Your Resume, Tailored
            <br />
            <span className="gradient-text">for Every Job.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-4 text-[#94A3B8] text-xl text-center max-w-2xl mx-auto leading-relaxed"
          >
            Upload your resume or build from scratch. Our AI scores it, finds gaps, and rewrites it to match any job description — in
            seconds.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="flex items-center justify-center gap-4 mt-10 flex-wrap"
          >
            <Link href="/builder">
              <Button variant="primary" size="xl">Build My Resume →</Button>
            </Link>
            <Button
              variant="ghost"
              size="xl"
              onClick={() => {
                document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              See How It Works
            </Button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-16 mx-auto max-w-4xl w-full float-animation"
            style={{ filter: "drop-shadow(0 0 40px rgba(99,102,241,0.2))" }}
          >
            <div className="rounded-2xl border border-[#334155] bg-[#1E293B] overflow-hidden shadow-2xl">
              <div className="h-10 border-b border-[#334155] bg-[#243044] flex items-center px-4 gap-2">
                <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
                <div className="w-3 h-3 rounded-full bg-[#F59E0B]" />
                <div className="w-3 h-3 rounded-full bg-[#10B981]" />
                <span className="text-xs text-[#64748B] ml-3">smartjob.ai/builder</span>
              </div>

              <div className="flex h-[340px]">
                <div className="w-1/2 border-r border-[#334155] p-5">
                  <div className="text-xs text-[#64748B] font-medium mb-4 uppercase tracking-wider">Resume Input</div>
                  <div className="text-xs text-[#6366F1] mb-1">Full Name</div>
                  <div className="h-9 rounded-lg bg-[#0F172A] border border-[#334155] mb-3 w-full" />
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="h-9 rounded-lg bg-[#0F172A] border border-[#334155]" />
                    <div className="h-9 rounded-lg bg-[#0F172A] border border-[#334155]" />
                  </div>
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="h-9 rounded-lg bg-[#0F172A] border border-[#334155]" />
                    <div className="h-9 rounded-lg bg-[#0F172A] border border-[#334155]" />
                  </div>
                  <div className="h-20 rounded-lg bg-[#0F172A] border border-[#334155] mb-4 w-full" />
                  <div className="h-9 w-32 rounded-lg bg-[#6366F1]" />
                </div>

                <div className="w-1/2 p-5 bg-[#0F172A]/50">
                  <div className="text-xs text-[#64748B] font-medium mb-4 uppercase tracking-wider">Live Preview</div>
                  <div className="bg-white rounded-lg h-full shadow-xl p-3">
                    <div className="h-4 w-32 bg-[#1B3A6B] rounded mb-2" />
                    <div className="h-2 w-48 bg-[#E5E7EB] rounded mb-1" />
                    <div className="h-2 w-40 bg-[#E5E7EB] rounded" />
                    <div className="my-2 border-t border-[#E5E7EB]" />
                    <div className="h-2 w-20 bg-[#D1D5DB] rounded mb-2" />
                    <div className="space-y-2">
                      <div className="h-1.5 w-full bg-[#F3F4F6] rounded" />
                      <div className="h-1.5 w-[92%] bg-[#F3F4F6] rounded" />
                      <div className="h-1.5 w-[85%] bg-[#F3F4F6] rounded" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function StatsBar() {
  const stats = [
    { value: 50, suffix: "+", label: "Resumes Scored" },
    { value: 2, prefix: "< ", suffix: "s", label: "AI Processing Time" },
    { value: 6, suffix: "", label: "ATS-Safe Templates" },
  ];

  return (
    <section className="py-14 border-y border-[#1E293B] bg-[#1E293B]/40">
      <div className="max-w-4xl mx-auto px-6">
        <div className="flex items-center justify-center gap-16 flex-wrap">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              viewport={{ once: true }}
              className="text-center"
            >
              <div className="font-heading font-bold text-4xl gradient-text">
                {stat.prefix || ""}
                <CountUp end={stat.value} duration={2} enableScrollSpy scrollSpyOnce />
                {stat.suffix}
              </div>
              <div className="text-sm text-[#94A3B8] mt-1">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      icon: Upload,
      iconColor: "#6366F1",
      bgColor: "#6366F1",
      title: "Upload or Build From Scratch",
      body: "Drag in your existing resume or use our guided step-by-step builder. Both paths connect to the same AI intelligence engine.",
    },
    {
      icon: Brain,
      iconColor: "#14B8A6",
      bgColor: "#14B8A6",
      title: "AI Scores Every Section",
      body: "Our NLP engine checks ATS compatibility, keyword coverage, and job-description match percentage in real time.",
    },
    {
      icon: Target,
      iconColor: "#10B981",
      bgColor: "#10B981",
      title: "Tailor to Any Job & Export",
      body: "One click rewrites your bullets to match any job description. Download as PDF or DOCX, ATS-safe every time.",
    },
  ];

  return (
    <section id="how-it-works" className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="font-heading font-bold text-4xl text-center gradient-text mb-16"
        >
          How It Works
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.15 }}
              viewport={{ once: true }}
              whileHover={{ y: -4, boxShadow: "0 0 32px rgba(99,102,241,0.2)" }}
              className="bg-[#1E293B] border border-[#334155] rounded-2xl p-8 cursor-default"
            >
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center mb-6"
                style={{ backgroundColor: `${step.bgColor}18` }}
              >
                <step.icon className={step.icon === Brain ? "w-6 h-6 ai-pulse" : "w-6 h-6"} style={{ color: step.iconColor }} />
              </div>
              <h3 className="font-heading font-semibold text-lg text-white mb-3">{step.title}</h3>
              <p className="text-[#94A3B8] text-sm leading-relaxed">{step.body}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ComparisonTable() {
  const rows: Array<[string, string, string, string]> = [
    ["AI Job-Match Scoring", "✅ Real-time", "❌", "❌"],
    ["Semantic Skill Analysis", "✅ NLP-powered", "❌", "❌"],
    ["One-Click Resume Tailoring", "✅ Auto-rewrite", "❌", "❌"],
    ["ATS Score Checker", "✅ Detailed", "✅ Basic", "❌"],
    ["Application Tracker", "✅ Full dashboard", "❌", "❌"],
    ["Cover Letter AI", "✅ Job-specific", "✅ Basic", "❌"],
    ["Free PDF Export", "✅ Always free", "⚠️ Paid plan", "✅ Yes"],
    ["Outreach Email Generator", "✅ Human-sounding", "❌", "❌"],
  ];

  return (
    <section className="py-24 px-6 bg-[#1E293B]/30">
      <div className="max-w-4xl mx-auto">
        <motion.h2
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="font-heading font-bold text-4xl text-center gradient-text mb-16"
        >
          How We Compare
        </motion.h2>

        <div className="rounded-2xl border border-[#334155] overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#334155]">
                <th className="text-left px-6 py-4 text-sm font-semibold text-[#94A3B8] bg-[#1E293B]">Feature</th>
                <th className="px-6 py-4 text-sm font-semibold text-white bg-[#6366F1]">Smart Job Agent</th>
                <th className="px-6 py-4 text-sm font-semibold text-[#94A3B8] bg-[#1E293B]">ResumeGenius</th>
                <th className="px-6 py-4 text-sm font-semibold text-[#94A3B8] bg-[#1E293B]">Generic Builders</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([feature, col1, col2, col3], i) => (
                <tr
                  key={feature}
                  className={`border-b border-[#334155]/50 ${i % 2 === 0 ? "bg-[#1E293B]" : "bg-[#243044]/40"}`}
                >
                  <td className="px-6 py-4 text-sm text-[#F8FAFC]">{feature}</td>
                  <td className="px-6 py-4 text-sm text-center font-medium text-[#10B981] bg-[#6366F1]/05">{col1}</td>
                  <td className="px-6 py-4 text-sm text-center text-[#94A3B8]">{col2}</td>
                  <td className="px-6 py-4 text-sm text-center text-[#94A3B8]">{col3}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function FooterCta() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="dot-grid rounded-3xl border border-[#6366F1]/30 bg-gradient-to-br from-[#6366F1]/15 via-[#1E293B] to-[#14B8A6]/10 p-12 md:p-16 text-center relative overflow-hidden"
        >
          <h2 className="font-heading font-extrabold text-4xl gradient-text mb-4">Ready to land your next role?</h2>
          <p className="text-[#94A3B8] text-lg mb-10 max-w-xl mx-auto">
            Free forever for core features. No credit card. Start building in under 2 minutes.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link href="/builder">
              <Button variant="primary" size="xl">Start Building →</Button>
            </Link>
            <Link href="/builder">
              <Button variant="ghost" size="xl">Upload My Resume</Button>
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
