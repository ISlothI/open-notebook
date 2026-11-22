import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    // The development proxy forwards the public host name.
    allowedHosts: ["localhost"],
    hmr: { protocol: "wss", clientPort: 9443 },
  },
  test: { environment: "jsdom", restoreMocks: true, fsModuleCache: false },
});
