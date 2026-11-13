# Enclosure foundation detail coordinator

Implemented November 11–12, 2026, as an extension for the ANS Structural CAD Design
Manager application. The original Fluidstack procurement workflow remains at `/`;
the enclosure workspace is at **`/enclosure.html`**.

## Run and review

From `pilots/fluidstack-change-auditor`:

```bash
uv sync --locked
make enclosure
make build
make serve
```

Open http://127.0.0.1:8000/enclosure.html. Restart an already-running API process
to load the new routes. The only added runtime library is locked `ezdxf==1.4.5`
and its resolved dependencies; existing Vite/web-ifc pins are retained. For a
fresh checkout, run `make setup` before building.

After frontend changes, run `make build`; restarting the server alone does not
compile the frontend. HTML entry pages require browser revalidation so they pick
up the current asset hashes. If a page was cached before this policy was added,
use Ctrl+Shift+R once. The current viewer label reads **GRID / IFC Z = 0**.

The workspace starts with a 24 → 30-inch diameter change to F-01 and issue A's
old drawings. Three documents require revision: S-101 (foundation plan and base
plate details), S-501 (support sections/elevations), and SCH-01 (schedule).
Generate issue B to update the package. The other assembly remains unchanged.

Use **Post alignment example** to inspect a four-inch post offset. Generating a
new package clears stale-document findings but leaves the alignment finding.
**Unchanged control** compares the baseline against itself and the baseline
package. Component selection, baseline/revised viewing, IFC import, and source,
audit, DXF, SVG, CSV, and ZIP downloads are available.

The viewer grid marks **IFC Z = 0**. In these fixtures that is the footing-top
datum: concrete extends 48 inches below it, with plates and posts above it.
The viewer preserves source coordinates instead of rebasing to a geometry point.
For uploaded models, zero remains the source reference plane; finished grade is
not inferred from a bounding box or a storey name. Survey coordinates and a
separate finished-grade datum are outside this pilot's viewer scope.

The ZIP includes the exact source IFC, issue manifest with hashes, two editable
DXFs, two SVG sheets, and JSON/CSV schedules. All generated packages remain
**review drafts**. Selecting an older package preserves its original drawing
contents and exposes differences against the selected model.

## Review artifacts

- [42-second walkthrough](artifacts/enclosure/walkthrough.webm): scripted browser review of
  pre-generated original fixtures; no manual CAD authoring claimed.
- [Workspace screenshot](artifacts/enclosure/workspace.png).
- [Revised foundation plan](artifacts/enclosure/issue-B/S-101.svg) and
  [sections/elevations](artifacts/enclosure/issue-B/S-501.svg).
- [Editable plan DXF](artifacts/enclosure/issue-B/S-101.dxf) and
  [section DXF](artifacts/enclosure/issue-B/S-501.dxf).
- [Revised schedule](artifacts/enclosure/issue-B/schedule.csv).
- [Stale-document report](artifacts/enclosure/stale-audit.json),
  [current-package report](artifacts/enclosure/current-audit.json),
  [alignment report](artifacts/enclosure/alignment-audit.json), and
  [unchanged control](artifacts/enclosure/unchanged-control.json).
- [Artifact manifest](artifacts/enclosure/manifest.json) and
  [browser verification](artifacts/enclosure/browser-verification.json).

## Implementation and data contract

`enclosure/fixtures.py` generates original CC0 IFC4 assets. `enclosure/audit.py`
extracts detail fields and compares unique GlobalIds within one project. Changed
IDs are added/removed records, not geometric identity matches. Byte hashes retain
the original revisions; STEP ordering and header edits do not change detail
findings. Measurements normalize to SI, with inch display in drawings and UI.

Supported members have one Body containing a positive-Z extrusion, an unrotated
vertical world placement, an explicit component mark, one named material, and
one named `IfcGroup` whose `ObjectType` is `ENCLOSURE_SUPPORT`. Each assembly
contains exactly one `IfcFooting` with a circle profile, one `IfcPlate` with a
solid rectangle profile, and one `IfcColumn` with a hollow rectangle profile.
Rounded HSS corners, mapped shapes, meshes, Boolean solids, and openings are
outside the initial measurement scope. IFC2x3 imports are rejected explicitly.

The engine measures diameter/depth, plate width/length/thickness, HSS outside
dimensions/wall thickness/height, volume, and location. Authored volume conflicts,
missing marks/materials/groups, and unsupported geometry remain visible and
prevent package generation. Alignment checks enforce the fixture's concentric,
direct-bearing assumptions and flag a post footprint extending beyond its plate.
These are geometric consistency rules, not capacity or code checks.

`enclosure/drawings.py` generates both CAD and SVG drawings from the measured
fields. DXF geometry is in model-space inches at 1:1, with named layers,
`ENCLOSURE` dimension style, and native `DIMENSION` entities. SVG sheets are
review previews; physical print scale depends on paper and print settings.
Templates accept up to two assemblies and reject geometry/layout that exceeds
their supported sheet bounds. They are not a general-purpose drafting engine.

Each document retains its source-model hash and per-component detail inputs and
fingerprints. The comparison uses the same 0.0001 m length and 0.000001 m³ volume
tolerances for model and document findings. All three documents cover the entire
small segment; added or removed supports therefore affect all three. Dependencies
are deliberately conservative at component level rather than annotation level.

`enclosure/store.py` reuses the original append-only revision/audit storage and
adds immutable packages and artifact bytes. `api/enclosure.py` exposes the
workflow under `/api/enclosure`. Its SQLite file is adjacent to `AUDITOR_DB`,
with `-enclosure.sqlite` appended to the stem. Browser sources are in
`web/src/enclosure.ts`; the original viewer is reused with an explicit source URL.

## Validation and remaining review

Verified November 12:

- **46 Python tests pass**, including the original 29. New checks independently
  triangulate the IFC solids, verify hollow volume, unit conversion, stale/current
  drawings, unchanged controls, post alignment, identity changes, source
  rejection, template limits, CAD readback, package hashes, and database reopen.
- Ruff passes. TypeScript and Vite production build pass. Existing dependency
  warnings about optional Three.js WebGPU exports remain; WebGL checks pass.
- **Four Playwright tests pass**, including the original two. Real IFC geometry,
  component selection, revision switching, package regeneration/downloads,
  import errors, and mobile page width were exercised.
- DXFs reopen in ezdxf without audit errors and retain inch units and native
  dimensions. SVGs parse, and footing radii agree with schedule inputs.
- All three IFC fixtures pass IfcOpenShell schema and EXPRESS-rule validation
  with no reported statements. Plan and section previews were visually inspected.
- Browser stale/current reports equal CLI reports. The scripted walkthrough
  verifies persistent alignment findings and the clean unchanged control.

The recording comparison exposed schedule column ordering that differed after
canonical JSON storage. Sorting the exported dimension fields resolved the
package-hash mismatch; a persistence-order regression check now covers it.

Owner review completed November 13, 2026. The owner confirmed: “Download package
works and the DXFs are correct.” This closes the package-download and owner DXF
review gate. The reviewing application and physical/PDF plotting results were
not specified. `browser-verification.json` retains the historical review status
at the time of the scripted recording, before this owner confirmation.

Remaining gate: **native Autodesk open/plot verification**. Native DXF entities,
successful parser readback, and the owner review do not establish Autodesk font,
plotting, or template compatibility. No AutoLISP integration, DWG/DWT/CTB package,
team deployment, or actual ANS drawing standard is claimed. Anchors, welds, and
reinforcement remain unspecified because their arrangement was not supplied.

For independent review, check F-01's 24/30-inch change across model, plan, and
schedule; the 48-inch depth, 72-inch post height, 10-inch plate width and 1/2-inch
thickness; the unchanged AS-02; and the persistent offset finding after package
regeneration. In Autodesk, check units, dimensions, layer visibility, fonts, and
plot scale before treating the drawing package as verified there.

## Reproduce evidence

```bash
uv run --locked python -m enclosure.demo --output docs/artifacts/enclosure
make test
make build
# In another terminal: make serve
cd web
npx playwright install chromium
npm run test:e2e
node scripts/record-enclosure-demo.mjs
cd ..
# Refresh hashes to include the recording and preview images.
uv run --locked python -m enclosure.demo --output docs/artifacts/enclosure
```

`AUDITOR_BASE_URL` selects a different local server for browser tests/recording.
`PLAYWRIGHT_BROWSERS_PATH` can reuse a custom browser cache. The development
verification used the existing `/tmp/portfolio-playwright` cache and a separate
review database on port 8061. TestClient needed local socket permissions outside
the restricted execution sandbox; the application itself required no workaround.
