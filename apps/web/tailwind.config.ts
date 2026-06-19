import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * Design tokens are declared as RGB channel triplets in globals.css
 * (`--token: R G B`) so Tailwind opacity modifiers (`bg-primary/10`) work.
 * Theme: deep dark with a violet "AI agent" accent; light theme overrides.
 */
const rgb = (v: string) => `rgb(var(${v}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.25rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        bg: rgb("--bg"),
        "bg-subtle": rgb("--bg-subtle"),
        card: rgb("--card"),
        "card-hover": rgb("--card-hover"),
        popover: rgb("--popover"),
        border: rgb("--border"),
        "border-strong": rgb("--border-strong"),
        input: rgb("--input"),
        foreground: rgb("--foreground"),
        muted: rgb("--muted"),
        primary: {
          DEFAULT: rgb("--primary"),
          foreground: rgb("--primary-foreground"),
          soft: rgb("--primary-soft"),
        },
        success: { DEFAULT: rgb("--success"), foreground: rgb("--success-foreground") },
        warning: { DEFAULT: rgb("--warning"), foreground: rgb("--warning-foreground") },
        danger: { DEFAULT: rgb("--danger"), foreground: rgb("--danger-foreground") },
        info: { DEFAULT: rgb("--info"), foreground: rgb("--info-foreground") },
        ring: rgb("--ring"),
      },
      borderRadius: {
        "2xl": "calc(var(--radius) + 8px)",
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        soft: "0 1px 2px rgb(0 0 0 / 0.04), 0 8px 24px -14px rgb(0 0 0 / 0.45)",
        card: "0 1px 0 0 rgb(255 255 255 / 0.03) inset, 0 1px 3px rgb(0 0 0 / 0.25)",
        glow: "0 0 0 1px rgb(var(--primary) / 0.20), 0 10px 40px -12px rgb(var(--primary) / 0.45)",
        "glow-sm": "0 0 18px -6px rgb(var(--primary) / 0.55)",
        focus: "0 0 0 2px rgb(var(--bg)), 0 0 0 4px rgb(var(--ring) / 0.7)",
      },
      backgroundImage: {
        "glow-radial":
          "radial-gradient(60% 60% at 50% 0%, rgb(var(--primary) / 0.18) 0%, transparent 70%)",
        "primary-gradient":
          "linear-gradient(135deg, rgb(var(--primary)) 0%, rgb(var(--primary-soft)) 100%)",
        grid: "linear-gradient(rgb(var(--border) / 0.5) 1px, transparent 1px), linear-gradient(90deg, rgb(var(--border) / 0.5) 1px, transparent 1px)",
      },
      backgroundSize: { grid: "32px 32px" },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.97)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(12px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out both",
        "fade-up": "fade-up 0.28s cubic-bezier(0.22,1,0.36,1) both",
        "scale-in": "scale-in 0.18s cubic-bezier(0.22,1,0.36,1) both",
        "slide-in-right": "slide-in-right 0.24s cubic-bezier(0.22,1,0.36,1) both",
        shimmer: "shimmer 1.6s infinite",
        "pulse-glow": "pulse-glow 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
