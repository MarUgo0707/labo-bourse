import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base relative : fonctionne sur https://<compte>.github.io/labo-bourse/
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { fs: { allow: [".."] } },
  build: { chunkSizeWarningLimit: 1500 },
});
