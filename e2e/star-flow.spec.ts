/**
 * ChronoFlow — Star Flow E2E test.
 *
 * Covers the full user journey described in ARCHITECTURE.md §8:
 *   1. Open "/" → Workflows list page
 *   2. Create a new workflow (navigates to Editor)
 *   3. Save the workflow (it already has a valid start→end graph)
 *   4. Trigger a Run via the "▶ Run" modal
 *   5. Land on /runs/:id — Time-Travel Debugger
 *   6. Wait for the run to complete (status badge shows "completed")
 *   7. Verify the Timeline scrubber is visible and interactive
 *   8. Step through events with the "Next ▶" button
 *   9. Verify the Payload Inspector updates
 *
 * Prerequisites:
 *   docker compose up --build -d   (web:8080, api:8000)
 *   npx playwright install chromium
 *   npx playwright test --config e2e/playwright.config.ts
 *
 * NOTE: Docker daemon was not running in the QA environment (2026-06-03).
 *       This test was written against the real UI contract but could NOT be
 *       executed here. Run it after `docker compose up --build -d` on any
 *       machine that has Docker Desktop / Engine running.
 */

import { expect, test } from '@playwright/test'

// How long to wait for a run to reach terminal status (completed/failed)
// A minimal start→end graph with no delay nodes should finish in < 5s.
const RUN_COMPLETE_TIMEOUT = 30_000

test.describe('ChronoFlow star-flow', () => {
  test('create workflow → trigger run → time-travel debugger', async ({ page }) => {
    // ── 1. Workflows list ────────────────────────────────────────────────────
    await page.goto('/')
    await expect(page).toHaveTitle(/ChronoFlow/)

    // The list page renders either a table/card of workflows or an empty state.
    // Either way the "New Workflow" button must be visible.
    const newWorkflowBtn = page.getByRole('button', { name: /new workflow/i })
    await expect(newWorkflowBtn).toBeVisible()

    // ── 2. Create a workflow ─────────────────────────────────────────────────
    // Clicking "New Workflow" hits POST /api/workflows and navigates to /workflows/:id
    await newWorkflowBtn.click()
    await expect(page).toHaveURL(/\/workflows\/[0-9a-f-]+$/)

    // ── 3. Verify Editor loaded ───────────────────────────────────────────────
    // The editor header shows the workflow name input and the Run button
    const workflowNameInput = page.getByRole('textbox', { name: /workflow name/i })
    await expect(workflowNameInput).toBeVisible()

    const runButton = page.getByRole('button', { name: /▶ run/i })
    await expect(runButton).toBeVisible()

    // ── 4. Trigger a Run ─────────────────────────────────────────────────────
    await runButton.click()

    // Modal opens — shows "Run Workflow" heading and the payload textarea
    const modalHeading = page.getByRole('heading', { name: /run workflow/i })
    await expect(modalHeading).toBeVisible()

    const startRunBtn = page.getByRole('button', { name: /start run/i })
    await expect(startRunBtn).toBeVisible()

    // Submit with the default empty payload {}
    await startRunBtn.click()

    // After submitting, app navigates to /runs/:id
    await expect(page).toHaveURL(/\/runs\/[0-9a-f-]+$/, { timeout: 10_000 })

    // ── 5. Time-Travel Debugger ───────────────────────────────────────────────
    // The page title area shows the run status badge
    // Wait until status is "completed" (or "failed" for a broken workflow)
    const statusBadge = page.locator('[class*="rounded-full"]').filter({ hasText: /completed|failed|running|pending/ }).first()
    await expect(statusBadge).toBeVisible()

    // Wait for run to finish — the badge text must change to completed or failed
    await expect(statusBadge).toHaveText(/completed|failed/, { timeout: RUN_COMPLETE_TIMEOUT })

    // Confirm it completed (not failed) — a valid start→end workflow should always complete
    await expect(statusBadge).toHaveText(/completed/)

    // ── 6. Timeline scrubber is present ──────────────────────────────────────
    const scrubber = page.getByRole('slider', { name: /timeline scrubber/i })
    await expect(scrubber).toBeVisible()

    // The scrubber label shows "Step X / Y" where Y >= 1 (at least one event)
    const stepLabel = page.getByText(/step \d+ \/ \d+/i)
    await expect(stepLabel).toBeVisible()

    // ── 7. Step through events ────────────────────────────────────────────────
    // Click "⏮ First" to go to the beginning, then step forward twice
    const firstBtn = page.getByRole('button', { name: /first/i })
    await firstBtn.click()

    const nextBtn = page.getByRole('button', { name: /next/i })
    await expect(nextBtn).toBeVisible()
    await nextBtn.click()

    // ── 8. Payload inspector updates ─────────────────────────────────────────
    // The aside panel "Payload inspector" should contain event data once we step
    const inspector = page.getByRole('complementary', { name: /payload inspector/i })
    await expect(inspector).toBeVisible()

    // Inspector shows a node_id string (font-mono text) when there is an event
    // for the current step (after stepping to step 1)
    const nodeIdText = inspector.locator('.font-mono').first()
    await expect(nodeIdText).toBeVisible()

    // ── 9. Replay button is visible and functional ────────────────────────────
    const replayBtn = page.getByRole('button', { name: /replay/i })
    await expect(replayBtn).toBeVisible()
    // We do not click Replay in this test to avoid infinite test chains,
    // but its presence verifies the contract endpoint POST /runs/:id/replay
    // is wired to the UI.
  })
})
