import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split rarely-changing, widely-shared vendor code into stable chunks
        // so they cache independently of app code (and don't bloat one file).
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          radix: [
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-tabs",
            "@radix-ui/react-toast",
            "@radix-ui/react-tooltip",
            "@radix-ui/react-popover",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-label",
            "@radix-ui/react-slot",
          ],
        },
      },
    },
  },
  server: {
    port: 3050,
    strictPort: true,
  },
});



