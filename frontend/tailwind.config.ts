import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0F172A",
        card: "#1E293B",
        elevated: "#243044",
        border: "#334155",
        accent: "#6366F1",
        "accent-hover": "#4F46E5",
        teal: "#14B8A6",
        success: "#10B981",
        warning: "#F59E0B",
        error: "#EF4444",
        info: "#38BDF8",
        "text-primary": "#F8FAFC",
        "text-secondary": "#94A3B8",
        "text-muted": "#64748B",
        "text-accent": "#A5B4FC",
      },
      fontFamily: {
        heading: ["Plus Jakarta Sans", "Inter", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backgroundImage: {
        "gradient-accent": "linear-gradient(135deg, #6366F1 0%, #14B8A6 100%)",
        "gradient-card": "linear-gradient(145deg, #1E293B 0%, #243044 100%)",
      },
      boxShadow: {
        "glow-indigo": "0 0 24px rgba(99, 102, 241, 0.25)",
        "glow-teal": "0 0 24px rgba(20, 184, 166, 0.2)",
        card: "0 4px 24px rgba(0, 0, 0, 0.3)",
      },
      animation: {
        "ai-pulse": "ai-pulse 1.8s ease-in-out infinite",
        shimmer: "shimmer 1.5s infinite",
        "fade-up": "fade-up 0.4s ease-out",
        float: "float 4s ease-in-out infinite",
      },
      keyframes: {
        "ai-pulse": {
          "0%, 100%": { opacity: "0.6", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.03)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
