import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-accent/20 text-accent",
        success: "bg-success/20 text-success",
        warning: "bg-warning/20 text-warning",
        error: "bg-error/20 text-error",
        teal: "bg-teal/20 text-teal",
        muted: "bg-elevated text-text-secondary",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export function Badge({
  className,
  variant,
  children,
}: React.PropsWithChildren<VariantProps<typeof badgeVariants> & { className?: string }>) {
  return <span className={cn(badgeVariants({ variant }), className)}>{children}</span>;
}
