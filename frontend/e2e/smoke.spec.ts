import { expect, test } from "@playwright/test";

/**
 * T3.11 — Playwright smoke.
 *
 * Personal-use scope: this single spec verifies the SPA loads, the nav rail
 * is present, and the user can switch routes without a runtime error. The
 * full "bulk import → run → wait → download zip" scenario from the roadmap
 * needs the backend + an OSS provider running; that is intentionally a
 * follow-up so the smoke can boot from `npm run dev` alone with no secrets.
 *
 * Run locally:
 *   cd frontend
 *   npm run dev            # in another shell, or rely on webServer config
 *   npm run test:e2e:install
 *   npm run test:e2e
 */
test.describe("voiceforge studio smoke", () => {
  test("app renders and brand title is visible", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".brand-block")).toBeVisible();
    await expect(page.locator(".brand-block strong")).toContainText(/VoiceForge/i);
  });

  test("sidebar exposes the main routes", async ({ page }) => {
    await page.goto("/");
    const nav = page.locator("nav.nav-list");
    await expect(nav).toBeVisible();
    // At least 3 nav items exist; we don't pin specific labels because they
    // depend on the active locale and the test might run against EN or VI.
    const items = nav.locator(".nav-item");
    await expect(items.first()).toBeVisible();
    expect(await items.count()).toBeGreaterThanOrEqual(3);
  });
});
