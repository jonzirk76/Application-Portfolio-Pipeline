import json
from copy import deepcopy

import ifcopenshell
import ifcopenshell.geom
import pytest
from ifcopenshell.api import material, root
from ifcopenshell.api import type as type_api
from ifcopenshell.util.unit import convert_file_length_units

from engine.audit import LENGTH_TOLERANCE, VOLUME_TOLERANCE, compare, differs, extract
from scripts.fixtures import generate, make_model, procurement_for, revise


@pytest.fixture
def baseline():
    return make_model()


def snapshot(model):
    return extract(model.to_string().encode())


def target(model):
    return next(e for e in model.by_type("IfcBeam") if e.Tag == "BEAM-014")


def audit(a, b, procurement=None):
    return compare(snapshot(a), snapshot(b), procurement or procurement_for(a))


def test_real_geometry_and_expected_revision(baseline):
    shape = ifcopenshell.geom.create_shape(
        ifcopenshell.geom.settings(), target(baseline)
    )
    assert len(shape.geometry.verts) == 24
    report = audit(baseline, revise(baseline))
    assert report["summary"] == {
        "modified": 1,
        "added": 0,
        "removed": 0,
        "unchanged": 15,
        "unresolved": 0,
        "affected_bom_lines": 1,
        "flagged_po_lines": 1,
        "uncertain_components": 0,
        "impact_reasons": 2,
    }
    entry = next(e for e in report["entries"] if e["kind"] == "modified")
    fields = {c["field"]: c for c in entry["changes"]}
    assert fields["length_m"]["delta"] == 0.5
    assert fields["volume_m3"]["delta"] == 0.01
    assert fields["specification"]["after"] == "Grade B"
    assert {i["po_line_id"] for i in report["impacts"]} == {"PO-1042/1"}
    assert all(
        i["before_source"]["global_id"] == target(baseline).GlobalId
        for i in report["impacts"]
    )
    assert all(line["count"] == 1 for line in report["bom"]["revised"])


def test_unchanged_is_clean(baseline):
    report = audit(baseline, baseline)
    assert report["summary"]["unchanged"] == 16
    assert report["impacts"] == []


def test_reordered_entities_and_header_do_not_change_results(baseline):
    source = baseline.to_string()
    start, tail = source.split("DATA;\n", 1)
    body, end = tail.split("ENDSEC;", 1)
    serialized = (
        start.replace("2026-11-09T00:00:00", "2026-11-10T01:02:03")
        + "DATA;\n"
        + "\n".join(reversed(body.strip().splitlines()))
        + "\nENDSEC;"
        + end
    )
    reordered = ifcopenshell.file.from_string(serialized)
    assert audit(baseline, reordered)["summary"]["modified"] == 0
    assert audit(baseline, reordered)["impacts"] == []


def test_equivalent_mm_units(baseline):
    millimeters = convert_file_length_units(baseline, "MILLIMETER")
    report = audit(baseline, millimeters)
    assert report["summary"]["modified"] == 0
    assert report["impacts"] == []


def test_placement_change_not_quantity(baseline):
    changed = ifcopenshell.file.from_string(baseline.to_string())
    member = target(changed)
    member.ObjectPlacement.RelativePlacement.Location.Coordinates = (0.2, 0.0, 3.0)
    report = audit(baseline, changed)
    entry = next(e for e in report["entries"] if e["kind"] == "modified")
    assert {c["field"] for c in entry["changes"]} == {"placement"}
    assert report["impacts"][0]["rule"] == "ENGINEERING_REVIEW"


def test_inherited_type_material(baseline):
    member = target(baseline)
    material.unassign_material(baseline, products=[member])
    beam_type = root.create_entity(
        baseline, ifc_class="IfcBeamType", name="Synthetic rectangular type"
    )
    type_api.assign_type(baseline, related_objects=[member], relating_type=beam_type)
    grade = material.add_material(baseline, name="Grade A")
    material.assign_material(baseline, products=[beam_type], material=grade)
    changed = ifcopenshell.file.from_string(baseline.to_string())
    changed.by_id(grade.id()).Name = "Grade B"
    report = audit(baseline, changed)
    assert any(i["rule"] == "PO_SPECIFICATION_MISMATCH" for i in report["impacts"])


def test_regenerated_id_is_candidate_not_definitive_impact(baseline):
    changed = revise(baseline)
    target(changed).GlobalId = ifcopenshell.guid.new()
    report = audit(baseline, changed)
    entry = next(e for e in report["entries"] if e["confidence"] == "candidate")
    assert entry["review_state"] == "undetermined"
    assert report["summary"]["flagged_po_lines"] == 0
    assert any(i["rule"] == "IDENTITY_OR_DATA_UNKNOWN" for i in report["impacts"])


@pytest.mark.parametrize("bad_id", [None, "invalid"])
def test_missing_or_invalid_id_explicit(baseline, bad_id):
    changed = revise(baseline)
    member = target(changed)
    # STEP allows us to represent malformed data even where setters enforce schema.
    text = changed.to_string().replace(
        f"'{member.GlobalId}'", "$" if bad_id is None else "'invalid'"
    )
    report = compare(
        snapshot(baseline), extract(text.encode()), procurement_for(baseline)
    )
    assert report["summary"]["uncertain_components"] >= 1
    assert report["summary"]["flagged_po_lines"] == 0


def test_duplicate_ids_not_silently_collapsed(baseline):
    changed = revise(baseline)
    changed.by_type("IfcColumn")[0].GlobalId = target(changed).GlobalId
    report = audit(baseline, changed)
    assert report["summary"]["unresolved"] > 0
    assert any("Duplicate GlobalId" in e["issues"] for e in report["entries"])
    assert report["summary"]["flagged_po_lines"] == 0


def test_added_removed_are_distinct(baseline):
    changed = ifcopenshell.file.from_string(baseline.to_string())
    member = target(changed)
    member.GlobalId = ifcopenshell.guid.new()
    member.Tag = "BEAM-NEW"
    report = audit(baseline, changed)
    assert report["summary"]["added"] == report["summary"]["removed"] == 1
    assert {i["rule"] for i in report["impacts"]} == {
        "NEW_COMPONENT",
        "REMOVED_COMPONENT",
    }


def test_missing_material_is_unknown(baseline):
    changed = revise(baseline)
    material.unassign_material(changed, products=[target(changed)])
    report = audit(baseline, changed)
    assert report["summary"]["uncertain_components"] == 1
    assert report["summary"]["flagged_po_lines"] == 0


def test_unsupported_shape_is_not_zero(baseline):
    changed = revise(baseline)
    target(changed).Representation.Representations[0].Items[
        0
    ].SweptArea = changed.create_entity(
        "IfcCircleProfileDef", ProfileType="AREA", Radius=0.1
    )
    report = audit(baseline, changed)
    entry = next(e for e in report["entries"] if e["after"]["tag"] == "BEAM-014")
    assert entry["after"]["geometry"] is None
    assert entry["review_state"] == "undetermined"


def test_stale_authored_quantity(baseline):
    changed = ifcopenshell.file.from_string(baseline.to_string())
    target(changed).Representation.Representations[0].Items[0].Depth = 4.5
    report = audit(baseline, changed)
    entry = next(e for e in report["entries"] if e["kind"] == "modified")
    assert entry["after"]["geometry"]["length_m"] == 4.5
    assert any("disagrees" in issue for issue in entry["issues"])
    assert entry["review_state"] == "undetermined"


@pytest.mark.parametrize("tolerance", [LENGTH_TOLERANCE, VOLUME_TOLERANCE])
def test_tolerance_boundaries(tolerance):
    assert not differs(0, tolerance * 0.99, tolerance)
    assert not differs(0, tolerance, tolerance)
    assert differs(0, tolerance * 1.01, tolerance)


def test_deterministic_generation_and_report(tmp_path, baseline):
    generate(tmp_path / "first")
    generate(tmp_path / "second")
    for name in ("baseline.ifc", "revised.ifc", "procurement.json", "manifest.json"):
        assert (tmp_path / "first" / name).read_bytes() == (
            tmp_path / "second" / name
        ).read_bytes()
    assert audit(baseline, revise(baseline)) == audit(baseline, revise(baseline))


def test_input_rejection(baseline):
    with pytest.raises(ValueError, match="Unable to read"):
        extract(b"not an IFC")
    with pytest.raises(ValueError, match="IFC4 only"):
        extract(ifcopenshell.file(schema="IFC2X3").to_string().encode())
    baseline.by_type("IfcProject")[0].UnitsInContext = None
    with pytest.raises(ValueError, match="length units"):
        snapshot(baseline)


def test_baseline_bom_disagreement_is_unknown(baseline):
    procurement = procurement_for(baseline)
    next(line for line in procurement["bom_lines"] if line["tag"] == "BEAM-014")[
        "length_m"
    ] = 9.0
    report = audit(baseline, revise(baseline), procurement)
    assert any(i["rule"] == "BASELINE_BOM_MISMATCH" for i in report["impacts"])
    assert report["summary"]["flagged_po_lines"] == 0


def test_input_procurement_is_immutable(baseline):
    procurement = procurement_for(baseline)
    copy = deepcopy(procurement)
    audit(baseline, revise(baseline), procurement)
    assert json.dumps(copy, sort_keys=True) == json.dumps(procurement, sort_keys=True)


def test_bom_lineage_survives_revision(baseline):
    report = audit(baseline, revise(baseline))
    line = next(line for line in report["bom"]["revised"] if line["tag"] == "BEAM-014")
    assert line["id"] == line["baseline_line_id"] == "BOM-BEAM-014"
    assert line["length_m"] == 4.5
    assert (
        next(line for line in report["bom"]["baseline"] if line["tag"] == "BEAM-014")[
            "length_m"
        ]
        == 4
    )


def test_orphan_bom_records_prevent_clean_report(baseline):
    procurement = procurement_for(baseline)
    procurement["bom_lines"][0]["component_guid"] = ifcopenshell.guid.new()
    report = audit(baseline, baseline, procurement)
    assert report["diagnostics"]
    assert report["review_state"] == "undetermined"
