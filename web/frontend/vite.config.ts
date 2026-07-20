import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  base: "./",
  server: {
    // In dev, forward API calls to the FastAPI server (`palette serve`).
    proxy: {
      "/api": "http://127.0.0.1:8710",
      "/list": "http://127.0.0.1:8710",
    },
  },
  build: { outDir: "dist" },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
