"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, ChevronDown, ChevronUp, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

interface Props {
  matchScore: number;
  callbackProbability?: number;
  cautionMessage?: string | null;
  hardGaps?: string[];
  onOverride: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function CautionBanner({
  matchScore,
  callbackProbability,
  cautionMessage,
  hardGaps = [],
  onOverride,
  onDismiss,
  className,
}: Props) {
  const [expanded, setExpanded] = React.useState(false);

  const scorePct = Math.round(matchScore);
  const callbackPct = callbackProbability ?? Math.round(matchScore * 0.6);

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className={cn(
        "rounded-xl border border-amber-400/40 bg-amber-400/8 overflow-hidden",
        className
      )}
    >
      {/* Header row */}
      <div className="flex items-start gap-3 p-4">
        <div className="flex-shrink-0 mt-0.5">
          <div className="w-8 h-8 rounded-full bg-amber-400/20 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-amber-400 text-sm">Low Match Warning</span>
            <span className="text-xs bg-amber-400/20 text-amber-300 px-2 py-0.5 rounded-full font-mono">
              {scorePct}% match
            </span>
            <span className="text-xs bg-error/20 text-error px-2 py-0.5 rounded-full">
              ~{callbackPct}% callback chance
            </span>
          </div>

          <p className="text-sm text-text-secondary mt-1 leading-relaxed">
            {cautionMessage ??
              `Your resume matches ${scorePct}% of the job requirements. Recruiters typically shortlist candidates above 60%. Applying now risks rejection without review.`}
          </p>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 rounded-lg text-text-muted hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Toggle details"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1.5 rounded-lg text-text-muted hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Expanded gap details */}
      <AnimatePresence>
        {expanded && hardGaps.length > 0 && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-3 border-t border-amber-400/20 pt-3">
              <p className="text-xs font-semibold text-text-secondary mb-2">Critical gaps:</p>
              <div className="flex flex-wrap gap-1.5">
                {hardGaps.map((gap) => (
                  <span
                    key={gap}
                    className="text-xs bg-error/15 text-error border border-error/30 px-2 py-0.5 rounded-full"
                  >
                    {gap}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* CTA row */}
      <div className="flex items-center gap-3 px-4 pb-4 pt-1">
        <Button
          variant="ghost"
          size="sm"
          className="border-amber-400/40 text-amber-400 hover:border-amber-400 hover:text-amber-300"
          onClick={onOverride}
        >
          Proceed anyway
        </Button>
        <span className="text-xs text-text-muted">
          We&apos;ll still optimize what we can.
        </span>
      </div>
    </motion.div>
  );
}
