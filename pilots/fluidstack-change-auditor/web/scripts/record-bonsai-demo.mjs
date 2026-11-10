// Requires the production API on localhost:8000 and a completed Bonsai authoring run.
import { chromium, expect } from '@playwright/test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const source = path.join(root, 'data/bonsai-authoring');
const destination = path.join(source, 'browser');
await mkdir(destination, { recursive: true });
const revised = await readFile(path.join(source, 'bonsai-revised.ifc'));
const digest = createHash('sha256').update(revised).digest('hex');
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: destination, size: { width: 1440, height: 1000 } } });
const page = await context.newPage();
page.setDefaultTimeout(60000);
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const video = page.video();
const caption = async text => page.evaluate(text => {
  let element = document.getElementById('bonsai-caption');
  if (!element) {
    element = document.createElement('div'); element.id = 'bonsai-caption';
    Object.assign(element.style, { position: 'fixed', bottom: '16px', left: '50%',
      transform: 'translateX(-50%)', padding: '14px 22px', background: '#12382ff5',
      color: 'white', zIndex: '99999', borderRadius: '6px', font: '15px system-ui',
      width: 'max-content', maxWidth: '90vw', textAlign: 'center' });
    document.body.append(element);
  }
  element.textContent = text;
}, text);

try {
  await page.goto('http://127.0.0.1:8000');
  await expect(page.locator('#detail h3')).toHaveText('BEAM-014');
  await page.getByRole('button', { name: 'Run unchanged control' }).click();
  await expect(page.locator('#impacts')).toContainText('No procurement discrepancies');
  await caption('Recorded browser session · Baseline against itself: no changes or PO discrepancies.');
  await page.waitForTimeout(5000);

  await page.getByLabel('Import revised IFC').setInputFiles(path.join(source, 'stale-quantities.ifc'));
  await expect(page.locator('#message')).toContainText('imported');
  await page.getByRole('button', { name: 'Run comparison' }).click();
  await expect(page.locator('#detail')).toContainText('Authored');
  await caption('Bonsai intermediate export: stale authored quantities block a definitive PO conclusion.');
  await page.waitForTimeout(6000);

  await page.getByLabel('Import revised IFC').setInputFiles(path.join(source, 'bonsai-revised.ifc'));
  await expect(page.locator('#message')).toContainText('imported');
  await page.getByRole('button', { name: 'Run comparison' }).click();
  await expect(page.locator('#model-container')).toHaveAttribute('data-revision', digest);
  await expect(page.locator('#viewer-status')).toContainText('Revised IFC loaded');
  await expect(page.locator('#detail')).toContainText('0.500 m');
  await expect(page.locator('#impacts')).toContainText('PO-1042/1');
  await caption('Import the actual Bonsai-saved IFC: one changed member, one BOM line, one PO line.');
  await page.waitForTimeout(7000);

  await page.getByRole('button', { name: 'A · Baseline', exact: true }).click();
  await expect(page.locator('#viewer-status')).toContainText('Baseline IFC loaded');
  await page.waitForTimeout(2000);
  await page.getByRole('button', { name: 'B · Revised', exact: true }).click();
  await expect(page.locator('#viewer-status')).toContainText('Revised IFC loaded');
  await page.locator('#detail summary').click();
  await page.locator('#detail').scrollIntoViewIfNeeded();
  await caption('Same GlobalId · length +0.500 m · volume +0.010 m³ · Grade B assigned to BEAM-014.');
  await page.screenshot({ path: path.join(destination, 'audit.png'), fullPage: true });
  await page.waitForTimeout(6000);

  await page.locator('#impacts').scrollIntoViewIfNeeded();
  await caption('PO-1042/1 retains 4.000 m / Grade A: two review reasons on the same order line.');
  await page.waitForTimeout(5000);
  const downloaded = page.waitForEvent('download');
  await page.locator('#export').click();
  await (await downloaded).saveAs(path.join(destination, 'export.json'));
  const report = JSON.parse(await readFile(path.join(destination, 'export.json'), 'utf8'));
  assert.equal(report.revised.id, digest);
  assert.equal(report.summary.impact_reasons, 2);
  assert.equal(report.summary.uncertain_components, 0);
  assert.equal(report.summary.flagged_po_lines, 1);
  const original = await page.request.get(`http://127.0.0.1:8000/api/revisions/${digest}/source`);
  assert.deepEqual(await original.body(), revised);
  await page.getByRole('button', { name: 'Evidence register' }).click();
  await page.locator('#evidence-panel').scrollIntoViewIfNeeded();
  await caption('Downloaded source matches the Bonsai export byte-for-byte. Agent-assisted; owner review pending.');
  await page.waitForTimeout(6000);
  assert.deepEqual(errors, []);
  await writeFile(path.join(destination, 'verification.json'), JSON.stringify({
    revised_sha256: digest, source_download_matches: true,
    summary: report.summary, page_errors: errors,
  }, null, 2) + '\n');
} finally {
  await context.close();
  await browser.close();
}
await rename(await video.path(), path.join(destination, 'browser-audit.webm'));
console.log('Verified and recorded the actual Bonsai export in the browser.');
