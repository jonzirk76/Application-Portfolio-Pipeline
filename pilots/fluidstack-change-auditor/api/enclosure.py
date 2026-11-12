"""Local enclosure import, drawing generation, and revision audit endpoints."""

import io
import json
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from api.models import StrictModel
from enclosure.audit import compare, extract
from enclosure.drawings import generate as generate_package
from enclosure.fixtures import FIXTURES, generate
from enclosure.store import EnclosureStore

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class DetailAudit(StrictModel):
    baseline_id: Hash
    revised_id: Hash
    package_id: Hash


class PackageRequest(StrictModel):
    revision_id: Hash
    issue_revision: Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,20}$")]


def setup(app, database):
    store = EnclosureStore(database)
    router = APIRouter(prefix="/api/enclosure", tags=["Enclosure detailing"])

    def seed():
        if not all(
            (FIXTURES / f"{name}.ifc").exists() for name in ("baseline", "revised", "misaligned")
        ):
            generate()
        ids = {}
        for name in ("baseline", "revised", "misaligned"):
            data = (FIXTURES / f"{name}.ifc").read_bytes()
            ids[f"{name}_id"] = store.add_revision(extract(data, f"enclosure-{name}.ifc"), data)[
                "id"
            ]
        package, files = generate_package(store.revision(ids["baseline_id"]), "A")
        ids["package_id"] = store.add_package(package, files)["id"]
        app.state.enclosure_demo = ids

    @router.get("/demo")
    def demo():
        return app.state.enclosure_demo

    @router.get("/revisions")
    def revisions():
        return store.revisions()

    @router.post("/revisions", status_code=201)
    async def upload(file: UploadFile):
        try:
            name = Path(file.filename or "enclosure.ifc").name
            if not name.lower().endswith(".ifc"):
                raise HTTPException(422, "Choose an IFC STEP file")
            data = await file.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise HTTPException(413, "Maximum IFC size is 20 MiB")
            try:
                snapshot = await run_in_threadpool(extract, data, name)
            except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
                raise HTTPException(422, str(exc)) from exc
            return store.add_revision(snapshot, data)
        finally:
            await file.close()

    @router.get("/revisions/{identifier}/source")
    def source(identifier: str):
        return Response(
            store.original(identifier),
            media_type="application/x-step",
            headers={"Content-Disposition": 'attachment; filename="enclosure-source.ifc"'},
        )

    @router.get("/packages")
    def packages():
        return store.packages()

    @router.post("/packages", status_code=201)
    def package(payload: PackageRequest):
        try:
            manifest, files = generate_package(
                store.revision(payload.revision_id), payload.issue_revision
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return store.add_package(manifest, files)

    @router.get("/packages/{identifier}")
    def manifest(identifier: str):
        return store.package(identifier)

    @router.get("/packages/{identifier}/files/{name}")
    def artifact(identifier: str, name: str):
        # SQLite lookup only: URL names never become filesystem paths.
        data = store.artifact(identifier, name)
        ext = name.rsplit(".", 1)[-1]
        content_type = {
            "svg": "image/svg+xml",
            "dxf": "application/dxf",
            "json": "application/json",
            "csv": "text/csv",
        }.get(ext, "application/octet-stream")
        return Response(
            data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'{"inline" if ext == "svg" else "attachment"}; filename="{name}"',
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            },
        )

    @router.get("/packages/{identifier}/download")
    def download(identifier: str):
        manifest = store.package(identifier)
        output = io.BytesIO()
        files = {name: store.artifact(identifier, name) for name in manifest["artifacts"]}
        files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
        files["source.ifc"] = store.original(manifest["source_revision"])
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        return Response(
            output.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="enclosure-drawing-package.zip"'},
        )

    @router.post("/audits")
    def audit(payload: DetailAudit):
        try:
            report = compare(
                store.revision(payload.baseline_id),
                store.revision(payload.revised_id),
                store.package(payload.package_id),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return store.add_audit(report)

    @router.get("/audits/{identifier}/export")
    def export(identifier: str):
        return Response(
            json.dumps(store.audit(identifier), indent=2) + "\n",
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="enclosure-audit.json"'},
        )

    app.include_router(router)
    app.state.enclosure_store = store
    return seed
