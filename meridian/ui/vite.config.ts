import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The built interface ships inside the Python package (meridian/app/static).
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../python/meridian/app/static", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
});
