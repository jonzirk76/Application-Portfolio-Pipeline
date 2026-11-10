import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from api.models import AuditRequest, Procurement
from engine.audit import compare, extract
from engine.store import Store
from scripts.fixtures import ROOT, generate


def create_app(database=None):
    store = Store(
        database or os.environ.get("AUDITOR_DB", ROOT / "data/auditor.sqlite")
    )

    @asynccontextmanager
    async def lifespan(app):
        fixture_path = ROOT / "fixtures"
        if not (fixture_path / "baseline.ifc").exists():
            generate()
        ids = []
        for name in ("baseline.ifc", "revised.ifc"):
            data = (fixture_path / name).read_bytes()
            snapshot = store.add_revision(extract(data, name), data)
            ids.append(snapshot["id"])
        procurement = Procurement.model_validate_json(
            (fixture_path / "procurement.json").read_text()
        ).model_dump()
        app.state.demo = {
            "baseline_id": ids[0],
            "revised_id": ids[1],
            "procurement_id": store.add_procurement(procurement),
        }
        yield

    app = FastAPI(
        title="OpenBIM Engineering Change Auditor", version="1.0.0", lifespan=lifespan
    )
    app.state.store = store

    @app.exception_handler(KeyError)
    async def not_found(_request, _exc):
        return JSONResponse({"detail": "Record not found"}, status_code=404)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "scope": "local synthetic pilot"}

    @app.get("/api/demo")
    def demo():
        return app.state.demo

    @app.get("/api/revisions")
    def revisions():
        return store.revisions()

    @app.post("/api/revisions", status_code=201)
    async def upload(file: UploadFile):
        try:
            filename = Path(file.filename or "model.ifc").name
            if not filename.lower().endswith(".ifc"):
                raise HTTPException(422, "Choose an IFC STEP file (.ifc)")
            data = await file.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise HTTPException(413, "Maximum IFC size is 20 MiB")
            try:
                snapshot = await run_in_threadpool(extract, data, filename)
            except (ValueError, RuntimeError, TypeError, AttributeError) as exc:
                raise HTTPException(422, str(exc)) from exc
            return store.add_revision(snapshot, data)
        finally:
            await file.close()

    @app.get("/api/revisions/{identifier}/source")
    def source(identifier: str):
        return Response(
            store.original(identifier),
            media_type="application/x-step",
            headers={"Content-Disposition": 'attachment; filename="source.ifc"'},
        )

    @app.get("/api/revisions/{identifier}")
    def revision(identifier: str):
        return store.revision(identifier)

    @app.post("/api/procurement", status_code=201)
    def procurement(payload: Procurement):
        return {"id": store.add_procurement(payload.model_dump())}

    @app.get("/api/procurement/{identifier}")
    def procurement_record(identifier: str):
        return store.procurement(identifier)

    @app.post("/api/audits")
    def audit(payload: AuditRequest):
        try:
            report = compare(
                store.revision(payload.baseline_id),
                store.revision(payload.revised_id),
                store.procurement(payload.procurement_id),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return store.add_audit(report)

    @app.get("/api/audits/{identifier}")
    def get_audit(identifier: str):
        return store.audit(identifier)

    @app.get("/api/audits/{identifier}/export")
    def export(identifier: str):
        return Response(
            json.dumps(store.audit(identifier), indent=2, allow_nan=False) + "\n",
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="engineering-change-audit.json"'
            },
        )

    # Keep API routes ahead of the static app. No SPA catchall for unknown API paths.
    dist = ROOT / "web/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
