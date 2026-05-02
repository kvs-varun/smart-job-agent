"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Loader2, Clock, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export type AgentStatus = "pending" | "running" | "ok" | "degraded" | "failed" | "skipped";

export interface AgentInfo {
  key: string;
  label: string;
  shortLabel: string;
}

export const AGENTS: AgentInfo[] = [
  { key: "parse_resume",    label: "Parser",       shortLabel: "Parse" },
  { key: "architect",       label: "Architect",    shortLabel: "Build" },
  { key: "enhancer",        label: "Enhancer",     shortLabel: "Enhance" },
  { key: "quality_gate",    label: "ATS Gate",     shortLabel: "ATS" },
  { key: "pdf_generator",   label: "PDF Gen",      shortLabel: "PDF" },
  { key: "jd_strategist",   label: "JD Match",     shortLabel: "JD" },
  { key: "scorer",          label: "Scorer",       shortLabel: "Score" },
  { key: "cold_email",      label: "Cold Email",   shortLabel: "Email" },
  { key: "auto_apply",      label: "Auto-Apply",   shortLabel: "Apply" },
];

interface Props {
  healthMap?: Record<string, string>;
  currentAgent?: string;
  interventions?: string[];
  className?: string;
}

function statusIcon(status: AgentStatus, current: boolean) {
  if (current) return <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" />;
  switch (status) {
    case "ok":       return <CheckCircle2 className="w-3.5 h-3.5 text-teal" />;
    case "failed":   return <XCircle className="w-3.5 h-3.5 text-error" />;
    case "degraded": return <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
    case "skipped":  return <Clock className="w-3.5 h-3.5 text-text-muted" />;
    default:         return <div className="w-3.5 h-3.5 rounded-full border border-border" />;
  }
}

function statusColor(status: AgentStatus, current: boolean): string {
  if (current) return "border-accent/60 bg-accent/10 text-accent";
  switch (status) {
    case "ok":       return "border-teal/40 bg-teal/10 text-teal";
    case "failed":   return "border-error/40 bg-error/10 text-error";
    case "degraded": return "border-amber-400/40 bg-amber-400/10 text-amber-400";
    case "skipped":  return "border-border bg-elevated text-text-muted";
    default:         return "border-border bg-surface text-text-muted";
  }
}

export function AgentStatusBar({ healthMap = {}, currentAgent, interventions = [], className }: Props) {
  const hasInterventions = interventions.length > 0;

  return (
    <div className={cn("w-full space-y-3", className)}>
      {/* Agent pills */}
      <div className="flex flex-wrap gap-2">
        {AGENTS.map((agent) => {
          const rawStatus = (healthMap[agent.key] ?? "pending") as AgentStatus;
          const isCurrent = currentAgent === agent.key;
          const status: AgentStatus = isCurrent ? "running" : rawStatus;

          return (
            <motion.div
              key={agent.key}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-all duration-300",
                statusColor(status, isCurrent)
              )}
            >
              {statusIcon(status, isCurrent)}
              <span className="hidden sm:inline">{agent.label}</span>
              <span className="sm:hidden">{agent.shortLabel}</span>
            </motion.div>
          );
        })}
      </div>

      {/* Supervisor interventions */}
      <AnimatePresence>
        {hasInterventions && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="rounded-lg border border-amber-400/30 bg-amber-400/5 px-3 py-2 space-y-1">
              <p className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" />
                Supervisor interventions
              </p>
              {interventions.map((msg, i) => (
                <p key={i} className="text-xs text-text-secondary pl-5">{msg}</p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
