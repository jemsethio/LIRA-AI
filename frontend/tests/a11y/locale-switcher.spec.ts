// Created in 11-01 Wave 0
import { test, expect } from '@playwright/test';

test('Locale switcher renders EN/አማ/OM buttons', async ({ page }) => {
  await page.goto('/en/');
  await expect(page.getByRole('button', { name: 'English' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'አማርኛ (Amharic)' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Afaan Oromoo (Oromo)' })).toBeVisible();
});

test('EN button is aria-pressed=true on /en/ page', async ({ page }) => {
  await page.goto('/en/');
  const enBtn = page.getByRole('button', { name: 'English' });
  await expect(enBtn).toHaveAttribute('aria-pressed', 'true');
});

test('Clicking አማ navigates to /am/', async ({ page }) => {
  await page.goto('/en/');
  await page.getByRole('button', { name: 'አማርኛ (Amharic)' }).click();
  await page.waitForURL(/\/am(\/|$)/);
  expect(page.url()).toMatch(/\/am(\/|$)/);
});

test('Clicking OM navigates to /om/', async ({ page }) => {
  await page.goto('/en/');
  await page.getByRole('button', { name: 'Afaan Oromoo (Oromo)' }).click();
  await page.waitForURL(/\/om(\/|$)/);
  expect(page.url()).toMatch(/\/om(\/|$)/);
});
