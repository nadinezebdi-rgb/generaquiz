/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        terracotta: {
          DEFAULT: "#E07A5F",
          dark: "#C9694E",
          light: "#F2A78F",
        },
        navy: {
          DEFAULT: "#1E3A5F",
          dark: "#142A47",
        },
        mustard: {
          DEFAULT: "#F2CC8F",
          dark: "#E5B96A",
        },
        bordeaux: "#722F37",
        cream: {
          DEFAULT: "#F4F1DE",
          dark: "#E8E2C9",
        },
        bgmain: "#FDFBF7",
        ink: "#1A2530",
        // Shadcn fallbacks
        background: "#FDFBF7",
        foreground: "#1A2530",
        border: "#E8E2C9",
        input: "#E8E2C9",
        ring: "#E07A5F",
        primary: { DEFAULT: "#E07A5F", foreground: "#FFFFFF" },
        secondary: { DEFAULT: "#F4F1DE", foreground: "#1E3A5F" },
        muted: { DEFAULT: "#F4F1DE", foreground: "#334155" },
        accent: { DEFAULT: "#F2CC8F", foreground: "#1A2530" },
        destructive: { DEFAULT: "#D9534F", foreground: "#FFFFFF" },
        popover: { DEFAULT: "#FFFFFF", foreground: "#1A2530" },
        card: { DEFAULT: "#FFFFFF", foreground: "#1A2530" },
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "serif"],
        sans: ['"Work Sans"', "system-ui", "sans-serif"],
      },
      borderRadius: {
        lg: "1rem",
        md: "0.75rem",
        sm: "0.5rem",
      },
      boxShadow: {
        soft: "0 4px 16px -4px rgba(30, 58, 95, 0.08)",
        warm: "0 8px 24px -8px rgba(224, 122, 95, 0.35)",
      },
      keyframes: {
        "accordion-down": { from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
