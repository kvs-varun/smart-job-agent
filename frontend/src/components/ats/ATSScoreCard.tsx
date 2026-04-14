"use client";

import * as React from "react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

interface ATSScoreCardProps {
  score: number;
  breakdown?: {
    keywords: number;
    contact: number;
    formatting: number;
    skills: number;
  };
  issues?: Array<{
    severity: "high" | "medium" | "low";
    text: string;
    stepIndex?: number;
  }>;
  onNavigateToStep?: (step: number) => void;
}

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const ARC_LENGTH = CIRCUMFERENCE * 0.75;

function getScoreColor(score: number) {
  if (score <= 40) return "#EF4444";
  if (score <= 70) return "#F59E0B";
  if (score <= 90) return "#10B981";
  return "url(#scoreGradient)";
}

function getScoreLabel(score: number) {
  if (score <= 40) return "Needs Work";
  if (score <= 70) return "Good Start";
  if (score <= 90) return "Strong Resume";
  return "Excellent";
}

export function ATSScoreCard({ score, breakdown, issues, onNavigateToStep }: ATSScoreCardProps) {
  const safeScore = Math.max(0, Math.min(100, Math.round(score)));

  const items = React.useMemo(
    () => [
      { label: "Keyword Match", value: breakdown?.keywords ?? 0 },
      { label: "Contact Info", value: breakdown?.contact ?? 0 },
      { label: "Formatting", value: breakdown?.formatting ?? 0 },
      { label: "Skills", value: breakdown?.skills ?? 0 },
    ],
    [breakdown]
  );

  return (
    <div className="bg-[#1E293B] border border-[#334155] rounded-2xl p-6">
      <div className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">ATS Score</div>

      <div className="flex flex-col items-center mb-8 mt-4">
        <svg width="140" height="140" viewBox="0 0 140 140">
          <defs>
            <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#6366F1" />
              <stop offset="100%" stopColor="#14B8A6" />
            </linearGradient>
          </defs>

          <circle
            cx="70"
            cy="70"
            r={RADIUS}
            fill="none"
            stroke="#334155"
            strokeWidth="10"
            strokeDasharray={`${ARC_LENGTH} ${CIRCUMFERENCE}`}
            strokeLinecap="round"
            transform="rotate(-225 70 70)"
          />

          <motion.circle
            cx="70"
            cy="70"
            r={RADIUS}
            fill="none"
            stroke={getScoreColor(safeScore)}
            strokeWidth="10"
            strokeDasharray={`${ARC_LENGTH} ${CIRCUMFERENCE}`}
            strokeLinecap="round"
            transform="rotate(-225 70 70)"
            initial={{ strokeDashoffset: ARC_LENGTH }}
            animate={{ strokeDashoffset: ARC_LENGTH - (safeScore / 100) * ARC_LENGTH }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />

          <text
            x="70"
            y="66"
            textAnchor="middle"
            dominantBaseline="middle"
            className="font-heading font-bold"
            fontSize="28"
            fill="url(#scoreGradient)"
          >
            {safeScore}
          </text>
          <text x="70" y="84" textAnchor="middle" fontSize="11" fill="#94A3B8">
            / 100
          </text>
        </svg>

        <span className="text-sm font-medium text-[#94A3B8] mt-2">{getScoreLabel(safeScore)}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        {items.map((item) => (
          <div key={item.label} className="bg-[#243044] rounded-xl p-3">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-[#94A3B8]">{item.label}</span>
              <span className="text-xs font-bold text-white">{item.value}%</span>
            </div>
            <div className="h-1 rounded-full bg-[#334155]">
              <motion.div
                className="h-full rounded-full bg-[#6366F1]"
                initial={{ width: 0 }}
                animate={{ width: `${Math.max(0, Math.min(100, item.value))}%` }}
                transition={{ duration: 0.8, delay: 0.3 }}
              />
            </div>
          </div>
        ))}
      </div>

      {issues && issues.length > 0 ? (
        <div>
          <h4 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider mb-3">Issues</h4>
          <div className="flex flex-col gap-2">
            {issues.map((issue, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full mt-1.5 flex-shrink-0",
                    issue.severity === "high"
                      ? "bg-[#EF4444]"
                      : issue.severity === "medium"
                        ? "bg-[#F59E0B]"
                        : "bg-[#10B981]"
                  )}
                />
                <span className="text-[#94A3B8] flex-1">{issue.text}</span>
                {issue.stepIndex !== undefined && onNavigateToStep ? (
                  <button
                    onClick={() => onNavigateToStep(issue.stepIndex as number)}
                    className="text-xs text-[#6366F1] hover:underline flex-shrink-0"
                  >
                    Fix →
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
