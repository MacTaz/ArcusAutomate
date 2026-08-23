import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Build as multiple independent HTML entries (popup + options)
    rollupOptions: {
      input: {
        popup: resolve(import.meta.dirname, "popup.html"),
        options: resolve(import.meta.dirname, "options.html"),
      },
    },
    // Keep chunk sizes manageable; templates.js will be large (~400KB)
    chunkSizeWarningLimit: 2000,
  },
  // During dev, serve from ext/ root so assets/icons are reachable
  publicDir: "public",
  optimizeDeps: {
    exclude: ["pdfjs-dist"],
  },
});
