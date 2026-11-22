import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  outputDir: "/reports/results",
  fullyParallel: true,
  workers: 2,
  // Flaky tests are fixed, not retried.
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: [["list"], ["junit", { outputFile: "/reports/e2e-junit.xml" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.E2E_BASE_URL,
    // The certificate of the local CA is verified by the smoke test.
    ignoreHTTPSErrors: true,
    viewport: { width: 1360, height: 860 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
