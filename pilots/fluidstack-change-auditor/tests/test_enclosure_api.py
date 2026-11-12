import hashlib
import io
import zipfile

from fastapi.testclient import TestClient

from api.main import create_app
from enclosure.fixtures import make_model, revise


def test_api_import_generate_export_and_reopen(tmp_path):
    model = make_model()
    database = tmp_path / "test.sqlite"
    with TestClient(create_app(database)) as client:
        demo = client.get("/api/enclosure/demo").json()
        request = {k: demo[k] for k in ("baseline_id", "revised_id", "package_id")}
        report = client.post("/api/enclosure/audits", json=request).json()
        assert report["summary"]["stale_documents"] == 3
        data = revise(model).to_string().encode()
        uploaded = client.post("/api/enclosure/revisions", files={"file": ("edited.ifc", data)})
        assert uploaded.status_code == 201
        assert (
            client.get(f"/api/enclosure/revisions/{uploaded.json()['id']}/source").content == data
        )
        package = client.post(
            "/api/enclosure/packages",
            json={"revision_id": demo["revised_id"], "issue_revision": "B"},
        ).json()
        request["package_id"] = package["id"]
        assert (
            client.post("/api/enclosure/audits", json=request).json()["summary"]["stale_documents"]
            == 0
        )
        response = client.get(f"/api/enclosure/packages/{package['id']}/download")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert (
                hashlib.sha256(archive.read("source.ifc")).hexdigest() == package["source_revision"]
            )
            for name, digest in package["artifacts"].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        assert (
            client.post("/api/enclosure/revisions", files={"file": ("bad.ifc", b"bad")}).status_code
            == 422
        )
        assert (
            client.get(f"/api/enclosure/packages/{package['id']}/files/missing.svg").status_code
            == 404
        )
        assert (
            client.post(
                "/api/enclosure/packages",
                json={"revision_id": demo["revised_id"], "issue_revision": "../bad"},
            ).status_code
            == 422
        )
    with TestClient(create_app(database)) as client:
        assert client.get(f"/api/enclosure/packages/{package['id']}").json() == package
        assert client.get(f"/api/enclosure/audits/{report['id']}/export").json() == report
