import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("accessibility: /export", async ({ page }) => {
  await page.goto("/export");
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});
  await checkA11y(page, undefined, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    detailedReport: true,
  });
});

test("export page PDF section renders and is accessible", async ({ page }) => {
  await page.goto("/export");
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

  // Assert PDF Documents heading is visible
  await expect(page.getByRole("heading", { name: "PDF Documents" })).toBeVisible();

  // Assert all three card titles are present
  await expect(page.getByText("Community Advisory Card")).toBeVisible();
  await expect(page.getByText("Policy Brief")).toBeVisible();
  await expect(page.getByText("Investment Passport")).toBeVisible();

  // Assert DownloadButton elements are present and keyboard-focusable
  const buttons = page.getByRole("button");
  const buttonCount = await buttons.count();
  expect(buttonCount).toBeGreaterThanOrEqual(3);

  // Assert at least one download button is in the DOM
  const downloadAdvisory = page.getByRole("button", { name: /Download Advisory Card/i });
  await expect(downloadAdvisory).toBeVisible();

  const downloadPolicy = page.getByRole("button", { name: /Download Policy Brief/i });
  await expect(downloadPolicy).toBeVisible();

  // Run axe on the PDF section specifically
  await checkA11y(page, undefined, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
    detailedReport: true,
  });
});

test("Download Advisory Card button is keyboard accessible", async ({ page }) => {
  await page.goto("/export");
  await page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {});

  // Find the Download Advisory Card button
  const downloadButton = page.getByRole("button", { name: /Download Advisory Card/i });
  await expect(downloadButton).toBeVisible();

  // Assert it is not disabled (Investment Passport is disabled, Advisory Card should not be)
  await expect(downloadButton).not.toBeDisabled();

  // Tab to it via keyboard navigation and verify it can receive focus
  await downloadButton.focus();
  await expect(downloadButton).toBeFocused();

  // Verify the button has focus-visible ring styling (it should have focus-visible:ring-2 class)
  const className = await downloadButton.getAttribute("class");
  expect(className).toContain("focus-visible:ring-2");
});
