import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(dirname, "frontend/src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./frontend/src/test/setup.ts"],
    include: ["frontend/src/**/*.{test,spec}.{ts,tsx}"],
  },
});
