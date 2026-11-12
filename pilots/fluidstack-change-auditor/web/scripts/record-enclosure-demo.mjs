// Scripted walkthrough of original fixtures, not a recording of manual CAD authoring.
// First run from the pilot root: python -m enclosure.demo --output docs/artifacts/enclosure
import assert from 'node:assert/strict';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { chromium, expect } from '@playwright/test';

const base = process.env.AUDITOR_BASE_URL || 'http://127.0.0.1:8000';
const destination = path.resolve('../docs/artifacts/enclosure');
await mkdir(destination, { recursive: true });
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: path.resolve('../data/enclosure-recording'), size: { width: 1440, height: 1000 } } });
const page = await context.newPage();
const video = page.video();
const errors = [];
page.on('pageerror', e => errors.push(e.message));
async function caption(text) {
  await page.evaluate(value => {
    let bar = document.getElementById('recording-caption');
    if (!bar) {
      bar = document.createElement('div'); bar.id = 'recording-caption'; document.body.append(bar);
      bar.style.cssText = 'position:fixed;bottom:18px;left:240px;right:24px;background:#153b30;color:white;padding:16px 20px;border-radius:6px;z-index:10000;font:16px system-ui;box-shadow:0 3px 20px #0003';
    }
    bar.textContent = value;
  }, text);
}
try {
  await page.goto(`${base}/enclosure.html`);
  await expect(page.locator('#viewer-status')).toContainText('Revised enclosure loaded', { timeout: 60000 });
  await expect(page.locator('#metrics .metric').nth(1).locator('strong')).toHaveText('3');
  await caption('Original IFC fixtures · 4 × 4 HSS posts, 10 × 10 base plates, cylindrical concrete footings.');
  await page.waitForTimeout(4500);
  await caption('F-01 changes from 24 to 30 inches in diameter. Five components remain unchanged.');
  await page.waitForTimeout(4500);
  await page.screenshot({ path: path.join(destination, 'workspace.png'), fullPage: false });
  await page.locator('#findings').scrollIntoViewIfNeeded();
  await caption('The issued plan, sections, and component schedule still contain the old footing inputs.');
  await page.waitForTimeout(4000);
  await page.locator('#drawing').scrollIntoViewIfNeeded();
  await caption('Issue A retains the 24-inch footing. Drawing source revisions are preserved.');
  await page.waitForTimeout(4500);
  const staleId = (await page.locator('#export').getAttribute('href')).split('/').at(-2);
  const stale = await (await context.request.get(`${base}/api/enclosure/audits/${staleId}/export`)).json();
  const cli = JSON.parse(await readFile(path.join(destination, 'stale-audit.json'), 'utf8'));
  assert.deepEqual(stale, cli);
  await page.getByRole('button', { name: 'Generate current package' }).click();
  await expect(page.locator('#metrics .metric').nth(1).locator('strong')).toHaveText('0');
  await page.locator('#drawing').scrollIntoViewIfNeeded();
  await caption('Generate issue B: the current model drives the DXF, SVG, and schedule. Still a review draft.');
  await page.waitForTimeout(4500);
  const planURL = new URL(await page.locator('#svg-link').getAttribute('href'), base).href;
  await page.getByLabel('Drawing', { exact: true }).selectOption('S-501');
  await caption('Sections carry footing depth, post height, plate thickness, marks, and source revision.');
  await page.waitForTimeout(4500);
  const sectionURL = new URL(await page.locator('#svg-link').getAttribute('href'), base).href;
  const currentId = (await page.locator('#export').getAttribute('href')).split('/').at(-2);
  const current = await (await context.request.get(`${base}/api/enclosure/audits/${currentId}/export`)).json();
  assert.deepEqual(current, JSON.parse(await readFile(path.join(destination, 'current-audit.json'), 'utf8')));
  await page.getByRole('button', { name: 'Post alignment example' }).click();
  await expect(page.locator('#findings')).toContainText('4.000 in off footing center');
  await page.locator('#findings').scrollIntoViewIfNeeded();
  await caption('A separate example offsets the post. Regenerating drawings cannot resolve an alignment issue.');
  await page.waitForTimeout(4500);
  await page.getByRole('button', { name: 'Generate current package' }).click();
  await expect(page.locator('#metrics .metric').nth(2).locator('strong')).toHaveText('1');
  await page.getByRole('button', { name: 'Unchanged control', exact: true }).click();
  await expect(page.locator('#metrics .metric').nth(0).locator('strong')).toHaveText('0');
  await page.locator('#metrics').scrollIntoViewIfNeeded();
  await caption('Unchanged control: zero changed components, zero stale documents, zero alignment findings.');
  await page.waitForTimeout(4500);
  // Capture clean sheet previews after the walkthrough; these also verify SVG responses.
  const preview = await browser.newPage({ viewport: { width: 1560, height: 1140 } });
  for (const [url, name] of [[planURL, 'plan.png'], [sectionURL, 'sections.png']]) {
    await preview.goto(url);
    await preview.screenshot({ path: path.join(destination, name) });
  }
  await preview.close();
  assert.deepEqual(errors, []);
  await writeFile(path.join(destination, 'browser-verification.json'), JSON.stringify({
    method: 'Scripted browser walkthrough using pre-generated original IFC revisions',
    stale_report_matches_cli: true, current_report_matches_cli: true,
    alignment_survives_regeneration: true, unchanged_control_clean: true,
    real_ifc_viewer_loaded: true, browser_errors: errors,
    owner_review: 'pending', autodesk_round_trip: 'not performed',
  }, null, 2) + '\n');
} finally {
  await context.close(); await browser.close();
}
await rename(await video.path(), path.join(destination, 'walkthrough.webm'));
console.log('Recorded and verified the enclosure detailing walkthrough.');
