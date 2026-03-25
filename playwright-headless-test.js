/**
 * Quick Playwright test: Chromium headless launch.
 * Run: node playwright-headless-test.js
 */
const { chromium } = require('playwright');

(async () => {
  let browser;
  try {
    console.log('Launching Chromium in headless mode...');
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto('about:blank');
    const title = await page.title();
    console.log('Chromium launched successfully. Page title:', title);
    await browser.close();
    console.log('SUCCESS: Playwright headless Chromium is working.');
    process.exit(0);
  } catch (err) {
    console.error('FAILED:', err.message);
    process.exit(1);
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
})();
