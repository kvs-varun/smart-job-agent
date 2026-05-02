"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "ghost" | "teal" | "danger" | "subtle";
export type ButtonSize = "sm" | "md" | "lg" | "xl" | "icon";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-white hover:bg-accent-hover shadow-glow-indigo hover:shadow-glow-indigo",
        ghost:
          "border border-border text-text-secondary hover:border-accent hover:text-white bg-transparent",
        teal: "bg-teal text-white hover:bg-teal/90 shadow-glow-teal",
        danger: "bg-error text-white hover:bg-error/90",
        subtle: "bg-elevated text-text-secondary hover:bg-card hover:text-white",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-5 text-sm",
        lg: "h-12 px-7 text-base",
        xl: "h-14 px-9 text-lg",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

export function Button({
  className,
  variant,
  size,
  loading,
  icon,
  children,
  disabled,
  ...props
}: ButtonProps) {
  // Explicitly pass disabled as boolean to avoid SSR/CSR hydration mismatch
  // where framer-motion renders disabled={false} as disabled="" on the server
  const isDisabled = disabled === true || loading === true;
  return (
    <motion.button
      whileTap={isDisabled ? undefined : { scale: 0.97 }}
      whileHover={isDisabled ? undefined : { scale: 1.02 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={isDisabled}
      {...(props as any)}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      {children}
    </motion.button>
  );
}
