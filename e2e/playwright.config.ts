import { defineConfig, devices } from '@playwright/test'

/**
 * ChronoFlow E2E — Playwright configuration.
 *
 * Requires the full stack to be running via docker compose:
 *   docker compose up --build -d
 *
 * Then run tests with:
 *   npx playwright test --config e2e/playwright.config.ts
 *
 * Target URLs:
 *   web: http://localhost:8080  (nginx serving the production build)
 *   api: http://localhost:8000  (FastAPI)
 */
export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:8080',
    trace: 'on-first-retry',
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'chromium-tablet',
      use: { ...devices['iPad Pro 11'] },
    },
    {
      name: 'chromium-mobile',
      use: { ...devices['Pixel 7'] },
    },
  ],
})
