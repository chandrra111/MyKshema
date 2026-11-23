import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#EEF3FA", 100: "#D9E3F2", 200: "#B3C6E4", 300: "#7F9DCC", 400: "#4C72AE",
          500: "#2C548F", 600: "#1E3F72", 700: "#16305A", 800: "#0F2344", 900: "#0A1A33", 950: "#061022",
        },
        teal: {
          50: "#ECFDF9", 100: "#CFF8EF", 200: "#A0EFDF", 300: "#67DFCB", 400: "#2DC7B1",
          500: "#12AB98", 600: "#0B897C", 700: "#0D6D64", 800: "#105751", 900: "#114844",
        },
      },
      fontFamily: { sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"] },
      boxShadow: {
        card: "0 1px 2px rgba(10,26,51,0.04), 0 4px 16px rgba(10,26,51,0.06)",
        lift: "0 8px 30px rgba(10,26,51,0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;
