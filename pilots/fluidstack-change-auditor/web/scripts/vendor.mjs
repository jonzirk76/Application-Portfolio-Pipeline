import { mkdir, copyFile } from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const destination = new URL('public/vendor/', root);
await mkdir(destination, { recursive: true });
for (const file of ['web-ifc.wasm', 'web-ifc-mt.wasm']) {
  await copyFile(new URL(`node_modules/web-ifc/${file}`, root), new URL(file, destination));
}
await copyFile(new URL('node_modules/@thatopen/fragments/dist/Worker/worker.mjs', root), new URL('fragments-worker.mjs', destination));
console.log('Copied version-matched IFC assets.');
