"""Regression coverage using actual Bonsai-saved exports, not generated revisions."""

import hashlib
import json
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
import pytest

from engine.audit import compare, extract

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/artifacts/bonsai"


def report_for(name):
    baseline = ROOT / "fixtures/baseline.ifc"
    revised = EVIDENCE / name
    return compare(
        extract(baseline.read_bytes(), baseline.name),
        extract(revised.read_bytes(), revised.name),
        json.loads((ROOT / "fixtures/procurement.json").read_text()),
    )


def test_bonsai_export_preserves_identity_and_measured_geometry():
    report = report_for("bonsai-revised.ifc")
    assert report["summary"] == {
        "modified": 1, "added": 0, "removed": 0, "unchanged": 15,
        "unresolved": 0, "affected_bom_lines": 1, "flagged_po_lines": 1,
        "uncertain_components": 0, "impact_reasons": 2,
    }
    change = next(e for e in report["entries"] if e["kind"] == "modified")
    assert change["match_method"] == "global_id"
    assert change["before"]["guid"] == change["after"]["guid"]
    assert change["after"]["tag"] == "BEAM-014"
    assert change["after"]["specification"] == "Grade B"
    assert change["after"]["authored_quantities"] == {}
    fields = {c["field"]: c for c in change["changes"]}
    assert set(fields) == {"length_m", "volume_m3", "specification"}
    assert fields["length_m"]["delta"] == 0.5
    assert fields["volume_m3"]["delta"] == 0.01
    assert {impact["po_line_id"] for impact in report["impacts"]} == {"PO-1042/1"}
    assert all(line["count"] == 1 for line in report["bom"]["revised"])
    model = ifcopenshell.open(str(EVIDENCE / "bonsai-revised.ifc"))
    assert model.header.file_name.originating_system.startswith("Bonsai ")
    beam = model.by_guid(change["after"]["guid"])
    shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), beam)
    assert ifcopenshell.util.shape.get_volume(shape.geometry) == pytest.approx(0.09)


def test_bonsai_stale_quantities_block_definitive_procurement_claims():
    report = report_for("stale-quantities.ifc")
    assert report["summary"]["modified"] == 1
    assert report["summary"]["unchanged"] == 15
    assert report["summary"]["uncertain_components"] == 1
    assert report["summary"]["flagged_po_lines"] == 0
    assert report["impacts"]
    assert all(i["state"] == "undetermined" for i in report["impacts"])
    assert all(i["po_line_id"] is None for i in report["impacts"])


def test_bonsai_evidence_matches_recorded_source_hashes():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest() == digest
    session = json.loads((EVIDENCE / "session.json").read_text())
    assert session["complete"] is True
    assert session["baseline_sha256"] == hashlib.sha256(
        (ROOT / "fixtures/baseline.ifc").read_bytes()
    ).hexdigest()
    assert session["revised_sha256"] == manifest["sha256"]["bonsai-revised.ifc"]
    assert report_for("bonsai-revised.ifc") == json.loads(
        (EVIDENCE / "audit.json").read_text()
    )
    assert json.loads((EVIDENCE / "browser-export.json").read_text()) == json.loads(
        (EVIDENCE / "audit.json").read_text()
    )
