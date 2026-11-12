/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Sampled from docs/design/references/*.png — indigo/violet accent on a
        // light, near-white workspace background. Keep in sync with that reference.
        brand: {
          50: "#F5F3FF",
          100: "#EDE9FE",
          200: "#DDD4FC",
          400: "#8F6FFC",
          500: "#7C5CFC",
          600: "#6D3EF0",
          700: "#5B2FD6",
          800: "#4A26B8",
        },
        ink: {
          900: "#17213F",
          700: "#26345B",
          500: "#5C6680",
          300: "#AAB2C8",
          100: "#E7EAF2",
          50: "#F1F3F9",
        },
        surface: "#F7F8FC",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        xl2: "1rem",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(23 33 63 / 0.04), 0 1px 3px 0 rgb(23 33 63 / 0.06)",
        "card-hover": "0 8px 20px -4px rgb(23 33 63 / 0.12), 0 2px 6px -1px rgb(23 33 63 / 0.06)",
      },
    },
  },
  plugins: [],
};
