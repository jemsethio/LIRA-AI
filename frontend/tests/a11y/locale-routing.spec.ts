// Created in 11-01 Wave 0
import { test, expect } from '@playwright/test';

test('English locale: html[lang] is en', async ({ page }) => {
  await page.goto('/en/');
  const lang = await page.locator('html').getAttribute('lang');
  expect(lang).toBe('en');
});

test('Amharic locale: html[lang] is am', async ({ page }) => {
  await page.goto('/am/');
  const lang = await page.locator('html').getAttribute('lang');
  expect(lang).toBe('am');
});

test('Oromo locale: html[lang] is om', async ({ page }) => {
  await page.goto('/om/');
  const lang = await page.locator('html').getAttribute('lang');
  expect(lang).toBe('om');
});

test('Root / redirects to /en/', async ({ page }) => {
  await page.goto('/');
  expect(page.url()).toMatch(/\/en(\/|$)/);
});

test('Amharic page loads without horizontal scroll', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto('/am/');
  const body = page.locator('body');
  const scrollWidth = await body.evaluate(el => el.scrollWidth);
  const clientWidth = await body.evaluate(el => el.clientWidth);
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 5);
});
