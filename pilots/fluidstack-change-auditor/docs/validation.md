# Validation record

Updated November 10, 2026. Ubuntu 22.04 x86_64 / Intel i7-3770; Python 3.12.8; Node 22.23.4.

## Verified

- **29 pytest cases:** the original 26 engine/API cases plus three regressions using actual Bonsai exports: supported geometry/identity, stale-quantity uncertainty, and evidence integrity.
- Ruff passes. Vite 7.3.8 production build passes.
- **Two Chromium end-to-end tests:** actual IFC rendering, selection, A/B switching, evidence/downloads, unchanged control, upload validation, and a 390-pixel mobile layout without page overflow. Software WebGL was used in headless Chromium.
- Fresh checkout at `/tmp/openbim-repro-rm617_l3/pilot`: `make test demo` passed the tests, restored both lockfiles, regenerated fixtures, produced the expected report, built successfully, and launched the application on port 8000.
- The scripted browser walkthrough was recorded and inspected with ffprobe: 90.52 seconds. It explicitly labels the revisions as pre-generated fixtures.
- **Bonsai authoring round trip:** native operations in Blender 5.2.2 / Bonsai 0.9.1-alpha261110 produced a new supported IFC revision. The actual export passes the expected audit; an independent geometry-kernel check confirms 0.090 m³. The intermediate stale-quantity export produces uncertainty instead of definitive PO flags.
- The Bonsai export renders in the browser, switches A/B, and downloads byte-for-byte. Its browser JSON equals the CLI report. The edited authoring → browser recording is **87.134 seconds**. See the [full evidence and method](bonsai-validation.md); authoring was agent-assisted.
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

**Bonsai authoring gate accepted November 10, 2026.** After receiving the independent-review checklist, the owner confirmed “all of those check out.” This closes the gate for the disclosed agent-assisted native edit/save/import/audit workflow. An unaided human mouse-and-keyboard session is not claimed. See the [acceptance record](bonsai-validation.md#owner-review).

The compatible Bonsai alpha build crashed in its extrusion guide during one capture attempt. The successful recording hides viewport gizmos; the authoring evidence includes the crash trace and workaround. The isolated profile and downloaded extension are local, ignored runtime files.

No external operator evaluation, production load, real employer data, actual ERP procurement, or LLM extraction was tested. The implementation compares documented fields rather than arbitrary property sets or a complete manufacturing graph. Actual development effort, cost, and hiring outcomes have not been measured.

Known upstream warnings: optional WebGPU exports from That Open's Three.js integration during build, and Starlette's HTTPX test-client deprecation. The tested WebGL path works. API tests require execution outside this environment's sandbox because its async thread wakeups stall TestClient.

Preserve these limits in published claims; rerun checks after engine or dependency changes.
