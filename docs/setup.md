# Installation commands

Prepared for the inspected **Ubuntu 22.04 x86_64** environment on November 9, 2026. Already present: Python 3.10.12, Node 22.23.4, npm 10.9.9, uv 0.5.9, and Git. Blender was not found on PATH.

The pilot is now implemented. **For the existing project use `make demo` in `pilots/fluidstack-change-auditor`; do not rerun initialization/scaffolding below.** Engine/API tests and the actual browser IFC workflow pass; see the [validation record](../pilots/fluidstack-change-auditor/docs/validation.md). These commands remain a bootstrap reference for new projects.

## 1. System utilities

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates make sqlite3 xdg-utils

cd '/home/big/Documents/GitHub/Application Portfolio Pipeline'
mkdir -p pilots/fluidstack-change-auditor
cd pilots/fluidstack-change-auditor
```

The SQLite CLI helps inspect records. Python already includes the `sqlite3` library; do not install a similarly named package with pip. No GPU compute stack, database server, Docker, or paid service is required for this pilot.

## 2. uv and Python environment

Use the installed uv if its commands below succeed. On a machine without uv, use the [official installer](https://docs.astral.sh/uv/getting-started/installation/):

```bash
# Only if uv is missing, or if you choose to update the older installation:
curl -LsSf https://astral.sh/uv/install.sh -o /tmp/portfolio-uv-install.sh
sh /tmp/portfolio-uv-install.sh
export PATH="$HOME/.local/bin:$PATH"
```

Run from `pilots/fluidstack-change-auditor`:

```bash
uv python install 3.12
uv init --app --name fluidstack-change-auditor --python 3.12 --no-workspace --vcs none --no-readme
uv python pin 3.12

uv add ifcopenshell fastapi 'uvicorn[standard]' pydantic python-multipart
uv add --dev pytest httpx ruff
uv sync

uv run python -c 'import sys, sqlite3, ifcopenshell, ifcopenshell.geom, fastapi; print(sys.version); print("SQLite:", sqlite3.sqlite_version); print("IfcOpenShell:", ifcopenshell.version); print("IFC schema:", ifcopenshell.file(schema="IFC4").schema)'
```

Python 3.12 is a conservative project choice supported by the [IfcOpenShell installation documentation](https://docs.ifcopenshell.org/ifcopenshell-python/installation.html). IfcOpenShell provides the IFC engine; FastAPI/Pydantic define the API; Uvicorn serves it; multipart handles uploaded IFC files. pytest and HTTPX cover the engine/API; Ruff checks Python code. See [FastAPI's documentation](https://fastapi.tiangolo.com/).

Keep `pyproject.toml`, `.python-version`, and the generated `uv.lock`. This import check does not prove geometry extraction works; the first implementation gate must generate, open, and measure a real supported IFC solid.

## 3. TypeScript interface and BIM viewer

The installed Node 22.23.4 meets [Vite's documented requirement](https://vite.dev/guide/). Reuse it; no Node reinstall is needed on this machine. Pin Vite to the tested 7.3.8 release: the Vite 8.3.7/Rolldown 1.2.18 binary installed by the latest scaffold crashes on this machine's Intel i7-3770.

Run from the pilot root:

```bash
node --version
npm --version
node --version > .nvmrc

npm create vite@latest web -- --template vanilla-ts --no-interactive
cd web
npm install
npm install --save-dev --save-exact vite@7.3.8

# Inspect the currently published peer requirements before resolving the viewer.
npm view @thatopen/components peerDependencies --json
npm view @thatopen/components-front peerDependencies --json

npm install --save-exact --strict-peer-deps \
  @thatopen/components @thatopen/components-front \
  @thatopen/fragments web-ifc@0.0.77 three
npm install --save-dev --save-exact @types/three

npm ls @thatopen/components @thatopen/components-front @thatopen/fragments web-ifc@0.0.77 three
npm run build
cd ..
```

The [That Open guide](https://docs.thatopen.com/components/getting-started) requires compatible Three.js, Fragments, and web-ifc versions. `components-front` adds browser-oriented tools for selection/highlighting. The commands above attempt a current compatible resolution; they are not a prevalidated version matrix. If strict peer resolution fails, select versions within the displayed peer ranges and rerun the install with explicit `package@version` arguments. Do not bypass the conflict with `--force` or `--legacy-peer-deps`.

Commit `web/package.json` and `web/package-lock.json` after the viewer smoke check. A successful scaffold build only validates the starter interface. Implementation must configure matching local web-ifc WASM and Fragments worker assets, open a real IFC, and verify element selection in the built app. Do not mix assets from an unversioned CDN with locked npm packages.

### Fix for `Illegal instruction (core dumped)` during build

On this machine, TypeScript 7.0.2 passed, while Vite 8.3.7 crashed even on `--version`. A debugger traced SIGILL to the `shlx` instruction in `@rolldown/binding-linux-x64-gnu` 1.2.18. That instruction requires BMI2, which this CPU does not expose. The tested fix replaces Vite 8 with Vite 7.3.8, which uses Rollup for this build:

```bash
cd '/home/big/Documents/GitHub/Application Portfolio Pipeline/pilots/fluidstack-change-auditor/web'
npm install --save-dev --save-exact vite@7.3.8
npm run build
```

This fix has already been applied to this pilot's package manifest and lockfile, and the starter production build passed. No TypeScript, Node, or BIM-library downgrade was needed. Diagnose other SIGILL failures independently; this finding applies to the binary and CPU combination above.

## 4. Blender and Bonsai authoring

The supported user path is Blender plus the Bonsai extension. Ubuntu's older `apt` Blender package may not support current extensions. One Linux installation option is the Blender Snap linked from [Blender's official download page](https://www.blender.org/download/):

```bash
# Only needed if Snap is not already installed:
sudo apt-get install -y snapd

# Install Blender using its stable Snap channel:
sudo snap install blender --classic
snap run blender
```

If Blender is already installed, skip the install command. If Snap is unavailable on your desktop, use Blender's official Linux download instead. Choose a Blender release compatible with the stable Bonsai extension; record the exact pair after the round-trip check.

In Blender, follow the [Bonsai installation guide](https://docs.bonsaibim.org/studio/quickstart/installation.html): **Edit → Preferences → Get Extensions → Allow Online Access → search Bonsai → Install**. Confirm **Open IFC Project** appears in the File menu. This is a required GUI step for the authoring demonstration; `pip install ifcopenshell` does not install Bonsai into Blender.

November 10 verification: the installed Blender 5.2.2 needs the Python 3.13 Bonsai build; the stable extension listing excludes Blender 5.1+. An official 0.9.1-alpha261110 package is now installed in an isolated pilot profile. See the [verified version pair, exact installation commands, and authoring evidence](../pilots/fluidstack-change-auditor/docs/bonsai-validation.md). A viewport-gizmo workaround was required for the recorded run.

Blender uses its own Python environment. Keep it separate from the application's uv environment. Validate by opening the generated baseline, changing one beam, saving the IFC, and importing that file with the application.

## 5. Optional screen recording

Use your existing recorder, or install OBS:

```bash
sudo apt-get install -y obs-studio
```

## 6. Reproduction and later development commands

Once the project and lockfiles exist, subsequent environments use:

```bash
cd '/home/big/Documents/GitHub/Application Portfolio Pipeline/pilots/fluidstack-change-auditor'
uv sync --locked
npm --prefix web ci
```

After implementation creates the API and tests:

```bash
uv run pytest -q
uv run ruff check .
npm --prefix web run build

# Terminal 1, from the pilot root, after api/main.py exists:
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2, from the pilot root:
npm --prefix web run dev -- --host 127.0.0.1
```

Configure the Vite development proxy for `/api` to port 8000; build the final frontend for serving through FastAPI. The pilot now includes `api/main.py`, tests, fixtures, and `make demo`. Use its README for the implemented workflow.


Runtime compatibility update: browser testing found a JavaScript/WASM mismatch in web-ifc 0.0.78. The implemented pilot pins 0.0.77, which passes real IFC loading and selection. Keep the lockfile and rerun browser tests before upgrading.
