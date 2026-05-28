import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("accessibility: /community", async ({ page }) => {
  await page.goto("/community");
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  await checkA11y(page, undefined, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    detailedReport: true,
  });
});
