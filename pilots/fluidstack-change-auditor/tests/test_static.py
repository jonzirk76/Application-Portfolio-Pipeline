from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import RevalidatedHtmlFiles


def test_entry_pages_revalidate_after_a_frontend_rebuild(tmp_path):
    for name in ("index.html", "enclosure.html"):
        (tmp_path / name).write_text('<script src="/assets/old.js"></script>')
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/old.js").write_text("console.log('old')")
    app = FastAPI()
    app.mount("/", RevalidatedHtmlFiles(directory=tmp_path, html=True))
    with TestClient(app) as client:
        for url, name in (("/", "index.html"), ("/enclosure.html", "enclosure.html")):
            initial = client.get(url)
            assert initial.status_code == 200
            assert initial.headers["cache-control"] == "no-cache"
            conditional = {"If-None-Match": initial.headers["etag"]}
            unchanged = client.get(url, headers=conditional)
            assert unchanged.status_code == 304
            assert unchanged.headers["cache-control"] == "no-cache"
            (tmp_path / name).write_text('<script src="/assets/new-build.js"></script>')
            rebuilt = client.get(url, headers=conditional)
            assert rebuilt.status_code == 200
            assert "/assets/new-build.js" in rebuilt.text
            assert rebuilt.headers["etag"] != initial.headers["etag"]
        # Content-addressed assets keep normal static caching behavior.
        assert "cache-control" not in client.get("/assets/old.js").headers
