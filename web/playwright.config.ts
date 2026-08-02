import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright — smoke at 320 / 768 / 1024 + C1 mood visual regression (Chromium).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  expect: {
    toHaveScreenshot: {
      animations: "disabled",
      maxDiffPixelRatio: 0.04,
    },
  },
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5173",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: "mobile-320",
      use: { viewport: { width: 320, height: 568 } },
      testMatch: /smoke\.spec\.ts/,
    },
    {
      name: "tablet-768",
      use: { viewport: { width: 768, height: 1024 } },
      testMatch: /smoke\.spec\.ts/,
    },
    {
      name: "desktop-1024",
      use: { viewport: { width: 1024, height: 768 } },
      testMatch: /smoke\.spec\.ts/,
    },
    {
      // Mood visual + token tests at a fixed desktop viewport
      name: "mood-shell",
      use: { viewport: { width: 1024, height: 768 } },
      testMatch: /mood-shell\.spec\.ts/,
    },
  ],
});
