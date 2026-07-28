import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const frontendRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: frontendRoot,
  plugins: [react()],
  build: {
    outDir: fileURLToPath(
      new URL("../backend/app/static", import.meta.url)
    ),
    emptyOutDir: true
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false
      }
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: [fileURLToPath(new URL("./tests/setup.ts", import.meta.url))],
    css: true
  }
});
