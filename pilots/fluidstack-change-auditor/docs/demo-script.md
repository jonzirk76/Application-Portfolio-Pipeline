# Demonstration and final authoring check

November 10 update: the [87-second Bonsai recording](artifacts/bonsai/bonsai-roundtrip.webm)
now shows native authoring, save, browser import, and the resulting procurement
audit. This is an agent-assisted, edited two-session capture. See the
[authoring validation](bonsai-validation.md) for source files, hashes, reproduction,
the alpha-build workaround, and independent owner acceptance recorded November 10.

`artifacts/browser-demo.webm` is a scripted, approximately 90-second recording of actual local browser interactions using pre-generated synthetic IFC revisions. Captions explicitly disclose that it is not a live Bonsai edit. It demonstrates the unchanged control, revised import, comparison, quantities, source evidence, PO reconciliation, and evidence register.

To recreate with the application running:

```bash
cd web
node scripts/record-demo.mjs
```

On this machine prefix with `PLAYWRIGHT_BROWSERS_PATH=/tmp/portfolio-playwright` to reuse the temporary browser. The script replaces its generated recording.

## Bonsai acceptance procedure

Steps 1–8 have now been exercised through agent-assisted native Bonsai operations.
The same procedure remains available for a separate manual owner demonstration.

1. Confirm Bonsai is installed and enabled in Blender's Preferences → Get Extensions, with Open IFC Project available.
2. Open `fixtures/baseline.ifc`; save a new revision to `data/bonsai-revised.ifc`. Do not overwrite the generated fixture files.
3. Preserve BEAM-014's GlobalId. Change its supported extrusion length from 4.000 m to 4.500 m through IFC authoring controls. A Blender-only visual transform is not enough.
4. Assign a new material named Grade B to this occurrence. Renaming the shared Grade A material would affect all members.
5. Recalculate or remove stale authored quantities; otherwise the auditor correctly reports a contradiction. Save the IFC.
6. Upload this file as revision B, retain the synthetic baseline procurement, and run comparison.
7. Check source hash, identity, representation support, numeric deltas, and both PO reasons. If Bonsai changes to an unsupported representation, record that failure and the adapter needed; do not mark the full gate passed.
8. Record the actual edit/save/import/audit sequence, then publish only verified claims.

Suggested 90 seconds: 15 baseline/PO context, 25 actual edit/save, 20 import/compare, 20 source-to-order evidence, 10 unchanged control/export. Disclose edits or precomputed footage.
