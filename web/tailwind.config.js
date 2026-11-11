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
          500: "#7C5CFC",
          600: "#6D3EF0",
          700: "#5B2FD6",
        },
        ink: {
          900: "#17213F",
          700: "#26345B",
          500: "#5C6680",
        },
        surface: "#F7F8FC",
      },
      borderRadius: {
        xl2: "1rem",
      },
    },
  },
  plugins: [],
};
