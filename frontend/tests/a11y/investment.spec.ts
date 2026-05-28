import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("accessibility: /investment", async ({ page }) => {
  await page.goto("/investment");
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  await checkA11y(page, undefined, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    detailedReport: true,
  });
});
