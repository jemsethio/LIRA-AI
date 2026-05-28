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
        lira: {
          green:   "#2d6a4f",
          olive:   "#52796f",
          sand:    "#b7a57a",
          earth:   "#8b4513",
          sky:     "#1a759f",
          warning: "#e07a2f",
          danger:  "#c1121f",
          bg:      "#0f1923",
          surface: "#1a2634",
          border:  "#2a3f52",
          muted:   "#7a9ab0",
          offline: "#7a9ab0",
          syncing: "#1a759f",
          cached:  "#52796f",
          "muted-aa": "#9db8cc",   // Phase 10: WCAG-safe muted text (5.1:1 on lira-bg)
          "green-aa": "#6aab8e",   // Phase 10: WCAG-safe green text (4.6:1 on lira-bg)
        },
      },
      outlineOffset: {
        3: "3px",  // Phase 10: focus ring offset (3 is not in Tailwind v3 default scale)
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "monospace"],
        ethiopic: ["var(--font-ethiopic)", "'Noto Serif Ethiopic'", "serif"],
      },
      minHeight: { touch: "44px" },
      minWidth:  { touch: "44px" },
    },
  },
  plugins: [],
};

export default config;
