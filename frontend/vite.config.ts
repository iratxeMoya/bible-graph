import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173 },
  // Cytoscape ocupa unos 750 kB sin comprimir; el aviso por defecto salta a los 500.
  build: { chunkSizeWarningLimit: 1000 },
  test: { environment: "node" },
});
