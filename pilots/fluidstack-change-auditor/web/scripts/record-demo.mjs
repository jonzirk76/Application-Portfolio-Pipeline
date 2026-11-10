// Requires the local API and production build on port 8000.
// This records live application interactions using pre-generated IFC revisions.
import { chromium } from 'playwright';
import { mkdir, rename } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const destination = path.join(root, 'docs/artifacts');
await mkdir(destination, { recursive: true });
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: destination, size: { width: 1440, height: 1000 } } });
const page = await context.newPage();
const video = page.video();
const started = Date.now();
const caption = async (text) => {
  await page.evaluate(text => {
    let banner = document.getElementById('recording-caption');
    if (!banner) {
      banner = document.createElement('div'); banner.id = 'recording-caption';
      Object.assign(banner.style, { position: 'fixed', bottom: '16px', left: '50%', transform: 'translateX(-50%)',
        background: '#12382fee', color: '#fff', padding: '14px 22px', borderRadius: '6px', zIndex: '99999',
        font: '14px system-ui', maxWidth: '90vw', textAlign: 'center', boxShadow: '0 6px 30px #0003' });
      document.body.append(banner);
    }
    banner.textContent = text;
  }, text);
};
try {
  await page.goto('http://127.0.0.1:8000');
  await page.locator('#model-container[data-ready="true"]').waitFor({ timeout: 60000 });
  await caption('Live auditor · Pre-generated synthetic IFC revisions · No live Bonsai edit in this recording');
  await page.waitForTimeout(8000);
  await page.getByRole('button', { name: 'Run unchanged control' }).click();
  await page.locator('#impacts .clean-result').waitFor();
  await caption('Negative control: compare the baseline with itself. No changes or procurement discrepancies.');
  await page.waitForTimeout(10000);
  await page.getByLabel('Import revised IFC').setInputFiles(path.join(root, 'fixtures/revised.ifc'));
  await page.locator('#message').filter({ hasText: 'imported' }).waitFor();
  await caption('Import revision B: the same beam identity, now 4.500 m long with illustrative Grade B material.');
  await page.waitForTimeout(7000);
  await page.getByRole('button', { name: 'Run comparison' }).click();
  await page.locator('#detail h3').filter({ hasText: 'BEAM-014' }).waitFor();
  await caption('The engine finds one changed member, one affected BOM line, and one purchase-order line.');
  await page.waitForTimeout(10000);
  await page.locator('#detail summary').click();
  await page.locator('#detail').scrollIntoViewIfNeeded();
  await caption('Evidence includes IFC GlobalId, source entity, geometry parameters, and the original file hash.');
  await page.waitForTimeout(10000);
  await page.locator('#impacts').scrollIntoViewIfNeeded();
  await caption('PO-1042/1 still orders 4.000 m / Grade A. Two review reasons, one affected order line.');
  await page.waitForTimeout(12000);
  await page.getByRole('button', { name: 'Evidence register' }).click();
  await page.locator('#evidence-panel').scrollIntoViewIfNeeded();
  await caption('Download immutable IFC sources and the complete JSON audit. Procurement records are synthetic.');
  await page.waitForTimeout(10000);
  await page.getByRole('button', { name: 'Change audit' }).click();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await caption('Deterministic engineering data → BOM lineage → procurement review. Local pilot; no engineering approval.');
  const remaining = 90000 - (Date.now() - started);
  if (remaining > 0) await page.waitForTimeout(remaining);
} finally {
  await context.close();
  await browser.close();
}
await rename(await video.path(), path.join(destination, 'browser-demo.webm'));
console.log('Recorded docs/artifacts/browser-demo.webm (scripted browser demonstration; not a Bonsai recording).');
