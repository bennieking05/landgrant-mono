import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0F3D7A",
          accent: "#FF7A18",
        },
      },
    },
  },
  plugins: [],
};

export default config;
