import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": "http://localhost:8777",
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: (id: string) => {
          if (!id.includes("node_modules")) return undefined;
          if (
            id.includes("react") ||
            id.includes("react-dom") ||
            id.includes("react-router-dom")
          ) {
            return "vendor-react";
          }
          if (id.includes("i18next") || id.includes("react-i18next")) {
            return "vendor-i18n";
          }
          if (
            id.includes("recharts") ||
            id.includes("apexcharts") ||
            id.includes("react-apexcharts")
          ) {
            return "vendor-charts";
          }
          if (
            id.includes("axios") ||
            id.includes("dayjs") ||
            id.includes("lucide-react")
          ) {
            return "vendor-utils";
          }
          return "vendor";
        },
      },
    },
  },
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "i18next",
      "react-i18next",
    ],
  },
});
