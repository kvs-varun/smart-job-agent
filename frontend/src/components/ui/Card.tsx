"use client";

import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover = false, glow = false, onClick }: CardProps) {
  return (
    <motion.div
      whileHover={hover ? { y: -4, boxShadow: "0 0 32px rgba(99,102,241,0.25)" } : undefined}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      onClick={onClick}
      className={cn(
        "rounded-xl border border-border bg-card p-6 shadow-card",
        hover && "cursor-pointer",
        glow && "shadow-glow-indigo",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
