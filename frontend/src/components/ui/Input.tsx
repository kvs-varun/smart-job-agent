"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, icon, className, id, ...props }, ref) => {
    const [focused, setFocused] = React.useState(false);
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="flex w-full flex-col gap-1.5">
        {label ? (
          <label
            htmlFor={inputId}
            className={cn(
              "text-sm font-medium transition-colors duration-200",
              focused ? "text-accent" : "text-text-secondary"
            )}
          >
            {label}
          </label>
        ) : null}

        <div className="relative">
          {icon ? (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">{icon}</span>
          ) : null}
          <input
            ref={ref}
            id={inputId}
            onFocus={(e) => {
              setFocused(true);
              props.onFocus?.(e);
            }}
            onBlur={(e) => {
              setFocused(false);
              props.onBlur?.(e);
            }}
            className={cn(
              "w-full rounded-lg border bg-elevated px-4 py-2.5 text-sm text-text-primary",
              "placeholder:text-text-muted",
              "transition-all duration-200",
              "border-border",
              focused && "border-accent ring-2 ring-accent/20",
              error && "border-error ring-2 ring-error/20",
              icon && "pl-10",
              className
            )}
            {...props}
          />
        </div>

        {error ? <p className="text-xs text-error">{error}</p> : null}
        {hint && !error ? <p className="text-xs text-text-muted">{hint}</p> : null}
      </div>
    );
  }
);
Input.displayName = "Input";
