# Validation record

November 9, 2026. Ubuntu 22.04 x86_64 / Intel i7-3770; Python 3.12.8; Node 22.23.4.

## Verified

- **26 pytest cases:** actual geometry, exact numeric deltas, unchanged and reordered controls, mm/m equivalence, placement changes, inherited materials, regenerated/missing/duplicate IDs, add/remove cases, missing specs, unsupported shapes, stale quantities, tolerance boundaries, deterministic fixture generation, BOM lineage/orphans, API uploads/errors, immutable source retrieval, and export.
- Ruff passes. Vite 7.3.8 production build passes.
- **Two Chromium end-to-end tests:** actual IFC rendering, selection, A/B switching, evidence/downloads, unchanged control, upload validation, and a 390-pixel mobile layout without page overflow. Software WebGL was used in headless Chromium.
- Fresh checkout at `/tmp/openbim-repro-rm617_l3/pilot`: `make test demo` passed the tests, restored both lockfiles, regenerated fixtures, produced the expected report, built successfully, and launched the application on port 8000.
- The scripted browser walkthrough was recorded and inspected with ffprobe: 90.52 seconds. It explicitly labels the revisions as pre-generated fixtures.
- Expected fixture output: 16 members, 1 modified, 15 unchanged, 1 affected BOM line, 1 flagged PO line, 2 reasons, no uncertain components. Length +0.500 m; volume +0.010 m³; piece count unchanged.
- One local headless fixture read/compare run took approximately **0.044 seconds**, excluding Python startup. This is not a scalability benchmark.

## Failures fixed

1. Vite 8.3.7/Rolldown 1.2.18 crashed at a BMI2 `shlx` instruction unsupported by this CPU. Pinned Vite 7.3.8.
2. web-ifc 0.0.78 browser JavaScript/WASM mismatch caused `StreamMeshes called with 4 arguments, expected 3`. Pinned 0.0.77 and verified real browser conversion.
3. IFC API relationship sets serialized nondeterministically. Fixture sets are now sorted and GUIDs/headers fixed.
4. Malformed STEP text could fail after parsing when reading the schema. Validation now returns a controlled error.
5. Orphan BOM rows could escape component-based checks. Report diagnostics now prevent a clean reconciliation claim.
6. The console-script pytest launcher did not include the source root in a fresh checkout. The Makefile now uses `python -m pytest`, and pytest's project path is explicit.

## Outstanding and limits

**Manual Bonsai GUI edit/save round trip remains outstanding.** Blender is installed; a Bonsai extension was not located in the checked configuration directories. The recording uses explicitly labeled pre-generated revisions, so it does not satisfy the original live-authoring recording gate.

No external operator evaluation, production load, real employer data, actual ERP procurement, or LLM extraction was tested. The implementation compares documented fields rather than arbitrary property sets or a complete manufacturing graph. Actual development effort, cost, and hiring outcomes have not been measured.

Known upstream warnings: optional WebGPU exports from That Open's Three.js integration during build, and Starlette's HTTPX test-client deprecation. The tested WebGL path works. API tests require execution outside this environment's sandbox because its async thread wakeups stall TestClient.

Preserve these limits in published claims; rerun checks after engine or dependency changes.
