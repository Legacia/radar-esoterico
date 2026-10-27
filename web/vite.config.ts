/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, a API roda à parte (python -m radar.servidor --porta 8502)
// e o Vite repassa /api para ela. Na versão final, a própria API serve web/dist.
const api = process.env.RADAR_API ?? "http://127.0.0.1:8502";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": api } },
  build: { outDir: "dist", emptyOutDir: true },
  test: { environment: "jsdom", include: ["tests/**/*.test.ts?(x)"], setupFiles: ["tests/preparar.ts"] },
});
