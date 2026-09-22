// Reusable regression check for FinTech Toolkit. Loads every page, clicks
// the theme toggle once, and reports nav presence + console/page errors.
// Known-benign errors (expected, not regressions):
//   - rebalance: 404 on /api/fx (local-server probe; falls through to a
//     working fallback)
//   - stock-drop: net::ERR_CONNECTION_REFUSED to localhost:8765 (same —
//     local-server probe with a working static-data fallback)
//
// Usage:
//   node verify.mjs                          # http://localhost:8931
//   node verify.mjs https://sinliongtoo.github.io/FINTECH_plan_check
//
// Requires the `playwright` package installed (see SKILL.md) and, for the
// localhost case, a static server already running in the repo root:
//   python -m http.server 8931

import { chromium } from 'playwright';

const BASE = (process.argv[2] || 'http://localhost:8931').replace(/\/$/, '');

const PAGES = [
  ['home', '/index.html'],
  ['stock-drop', '/tools/stock-drop/index.html'],
  ['rebalance', '/tools/rebalance/index.html'],
  ['retirement', '/tools/retirement/index.html'],
  ['loan', '/tools/loan/index.html'],
  ['rules', '/tools/rules/index.html'],
];

const browser = await chromium.launch();
let anyFail = false;

// Console/pageerror messages for a failed network resource never include
// the URL (that's a browser quirk), so filtering benign errors by message
// text doesn't work. Track failing URLs directly instead and match on
// those.
const BENIGN_URL_PATTERNS = [/\/api\/fx/, /localhost:8765/, /\/api\/stock/];

for (const [name, path] of PAGES) {
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
  const errors = [];
  const badUrls = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push('console: ' + msg.text()); });
  page.on('requestfailed', (req) => badUrls.push(req.url()));
  // status >= 400 only -- 3xx redirects (e.g. the Tailwind CDN's own
  // redirect chain on retirement.html) are normal and browsers follow
  // them automatically; res.ok() is false for those too and was a
  // false-positive here.
  page.on('response', (res) => { if (res.status() >= 400) badUrls.push(res.url()); });

  await page.goto(BASE + path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(300);

  const nav = await page.locator('.ftk-nav').count();
  const themeBtn = await page.locator('.ftk-theme-btn').count();
  let clicked = false;
  if (themeBtn > 0) {
    await page.click('.ftk-theme-btn');
    await page.waitForTimeout(200);
    clicked = true;
  }

  const unexpectedUrls = badUrls.filter((u) => !BENIGN_URL_PATTERNS.some((p) => p.test(u)));
  const pageErrors = errors.filter((e) => e.startsWith('pageerror:')); // real JS exceptions are never benign
  const bad = [...new Set(unexpectedUrls)].concat(pageErrors);
  if (nav !== 1 || !clicked || bad.length) anyFail = true;

  console.log(`--- ${name} --- nav:${nav} themeBtn:${themeBtn} clicked:${clicked} failedReqs:${badUrls.length}${bad.length ? ' (UNEXPECTED:' + bad.length + ')' : ''}`);
  bad.forEach((e) => console.log('  ' + e));

  await page.context().close();
}

await browser.close();
process.exit(anyFail ? 1 : 0);
