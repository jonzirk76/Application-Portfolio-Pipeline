import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite")) as client:
        yield client


def test_complete_api_workflow_and_export(client):
    demo = client.get("/api/demo").json()
    response = client.post("/api/audits", json=demo)
    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["flagged_po_lines"] == 1
    assert client.get(f"/api/audits/{report['id']}").json() == report
    download = client.get(f"/api/audits/{report['id']}/export")
    assert download.json() == report
    assert "attachment" in download.headers["content-disposition"]
    assert client.post("/api/audits", json=demo).json()["id"] == report["id"]
    control = client.post(
        "/api/audits", json={**demo, "revised_id": demo["baseline_id"]}
    ).json()
    assert control["summary"]["modified"] == 0
    assert control["impacts"] == []


def test_uploaded_revision_preserves_source_and_is_idempotent(client):
    demo = client.get("/api/demo").json()
    source = client.get(f"/api/revisions/{demo['revised_id']}/source").content
    first = client.post(
        "/api/revisions",
        files={"file": ("../new.ifc", source, "application/octet-stream")},
    )
    assert first.status_code == 201
    assert first.json()["id"] == demo["revised_id"]
    assert len(client.get("/api/revisions").json()) == 2
    assert client.get(f"/api/revisions/{first.json()['id']}/source").content == source


def test_bad_uploads_and_missing_records(client):
    assert (
        client.post("/api/revisions", files={"file": ("bad.txt", b"bad")}).status_code
        == 422
    )
    assert (
        client.post("/api/revisions", files={"file": ("bad.ifc", b"bad")}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/revisions", files={"file": ("big.ifc", b"x" * (20 * 1024 * 1024 + 1))}
        ).status_code
        == 413
    )
    assert client.get("/api/revisions/unknown").status_code == 404
    assert client.post("/api/audits", json={}).status_code == 422


def test_procurement_validation(client):
    demo = client.get("/api/demo").json()
    procurement = client.get(f"/api/procurement/{demo['procurement_id']}").json()
    assert (
        client.post("/api/procurement", json=procurement).json()["id"]
        == demo["procurement_id"]
    )
    procurement["po_lines"][0]["bom_line_id"] = "missing"
    assert client.post("/api/procurement", json=procurement).status_code == 422
