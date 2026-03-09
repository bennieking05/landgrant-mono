import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1F4B99",
          accent: "#FF7A18",
        },
      },
    },
  },
  plugins: [],
};

export default config;
