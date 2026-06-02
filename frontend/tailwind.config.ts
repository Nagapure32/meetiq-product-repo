import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1a1a18",
        muted: "#6b6b66",
        line: "#e2e1dc",
        shell: "#f5f4f0",
        panel: "#ffffff",
        brand: {
          DEFAULT: "#3d35b0",
          dark: "#2b249e",
          soft: "#eeedfd",
        },
      },
      fontFamily: {
        sans: ["var(--font-dm-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-dm-mono)", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 1.5px rgba(0,0,0,0.06), 0 1px 1px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};

export default config;

