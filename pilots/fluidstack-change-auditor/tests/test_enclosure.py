import hashlib
import io
import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy

import ezdxf
import ifcopenshell.geom
import numpy as np
import pytest
from ifcopenshell.util.unit import convert_file_length_units

from enclosure.audit import alignment, compare, extract
from enclosure.drawings import generate
from enclosure.fixtures import INCH, make_model, revise


@pytest.fixture
def model():
    return make_model()


def snapshot(model):
    return extract(model.to_string().encode())


def member(model, tag):
    return next(e for e in model.by_type("IfcElement") if e.Tag == tag)


def test_fixture_units_real_geometry_and_hollow_volume(model):
    s = snapshot(model)
    assert s["length_unit_to_m"] == INCH
    assert len(s["components"]) == 6
    assert not any(r["issues"] for r in s["components"])
    assert alignment(s) == []
    post = next(r for r in s["components"] if r["tag"] == "HSS-01")
    assert post["dimensions"]["volume_m3"] == pytest.approx((4**2 - 3.5**2) * 72 * INCH**3)
    # Independently triangulate every actual IFC solid, including the hollow core.
    for entity in model.by_type("IfcElement"):
        shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), entity)
        verts = np.asarray(shape.geometry.verts).reshape(-1, 3)
        faces = np.asarray(shape.geometry.faces).reshape(-1, 3)
        volume = abs(sum(np.dot(verts[a], np.cross(verts[b], verts[c])) / 6 for a, b, c in faces))
        expected = next(
            r["dimensions"]["volume_m3"] for r in s["components"] if r["guid"] == entity.GlobalId
        )
        assert volume == pytest.approx(expected, rel=0.005)  # Circle tessellation tolerance.


def test_diameter_revision_stales_drawings_then_regeneration_resolves(model):
    a, b = snapshot(model), snapshot(revise(model))
    issued, _ = generate(a, "A")
    report = compare(a, b, issued)
    assert report["summary"] == dict(
        modified=1,
        unchanged=5,
        added=0,
        removed=0,
        stale_documents=3,
        alignment_findings=0,
        uncertain_components=0,
    )
    changed = next(e for e in report["entries"] if e["kind"] == "modified")
    assert changed["after"]["tag"] == "F-01"
    delta = next(c["delta"] for c in changed["changes"] if c["field"] == "volume_m3")
    assert delta == pytest.approx(math.pi * (15**2 - 12**2) * 48 * INCH**3)
    assert all(f["guids"] == [changed["guid"]] for f in report["drawing_findings"])
    current, _ = generate(b, "B")
    assert compare(a, b, current)["summary"]["stale_documents"] == 0
    assert current["status"] == "review_draft"


def test_unchanged_and_equivalent_units_are_clean(model):
    a = snapshot(model)
    package, _ = generate(a)
    assert compare(a, a, package)["summary"]["unchanged"] == 6
    mm = snapshot(convert_file_length_units(model, "MILLIMETER"))
    report = compare(a, mm, package)
    assert report["summary"]["modified"] == report["summary"]["stale_documents"] == 0


def test_header_change_is_not_a_detail_change(model):
    a = snapshot(model)
    package, _ = generate(a)
    model.header.file_name.time_stamp = "2030-01-01T00:00:00"
    b = snapshot(model)
    assert a["id"] != b["id"]
    assert compare(a, b, package)["summary"]["stale_documents"] == 0


def test_sub_tolerance_placement_does_not_stale_drawings(model):
    a = snapshot(model)
    package, _ = generate(a)
    point = member(model, "HSS-01").ObjectPlacement.RelativePlacement.Location
    point.Coordinates = (0.00001 / INCH, *point.Coordinates[1:])
    report = compare(a, snapshot(model), package)
    assert report["summary"]["modified"] == 0
    assert report["summary"]["stale_documents"] == 0
    assert report["alignment_findings"] == []


def test_layout_outside_template_is_rejected(model):
    for item in model.by_type("IfcElement"):
        if item.Tag.endswith("02"):
            point = item.ObjectPlacement.RelativePlacement.Location
            point.Coordinates = (point.Coordinates[0], 100.0, point.Coordinates[2])
    with pytest.raises(ValueError, match="exceeds the fixed"):
        generate(snapshot(model))


def test_alignment_remains_after_package_regeneration(model):
    a, b = snapshot(model), snapshot(revise(model, "alignment"))
    package, _ = generate(b, "B")
    report = compare(a, b, package)
    assert report["summary"]["stale_documents"] == 0
    assert len(report["alignment_findings"]) == 1
    finding = report["alignment_findings"][0]
    assert finding["assembly"] == "AS-01"
    assert any("4.000 in" in r for r in finding["reasons"])
    assert any("extends beyond" in r for r in finding["reasons"])


@pytest.mark.parametrize("mutation", ["rounded", "solid", "void", "rotated", "bad_wall"])
def test_unsupported_geometry_prevents_drawing_issue(model, mutation):
    post = member(model, "HSS-01")
    solid = post.Representation.Representations[0].Items[0]
    if mutation == "rounded":
        solid.SweptArea.OuterFilletRadius = 0.5
    elif mutation == "solid":
        solid.SweptArea = model.create_entity(
            "IfcRectangleProfileDef", ProfileType="AREA", XDim=4.0, YDim=4.0
        )
    elif mutation == "void":
        from ifcopenshell.api import feature, root

        opening = root.create_entity(model, ifc_class="IfcOpeningElement")
        feature.add_feature(model, feature=opening, element=post)
    elif mutation == "rotated":
        post.ObjectPlacement.RelativePlacement.RefDirection.DirectionRatios = (0.0, 1.0, 0.0)
    else:
        solid.SweptArea.WallThickness = 2.0
    s = snapshot(model)
    assert next(r for r in s["components"] if r["tag"] == "HSS-01")["issues"]
    with pytest.raises(ValueError, match="Resolve unsupported"):
        generate(s)


def test_removed_or_regenerated_guid_is_not_guessed_from_geometry(model):
    a = snapshot(model)
    package, _ = generate(a)
    member(model, "F-01").GlobalId = ifcopenshell.guid.new()
    report = compare(a, snapshot(model), package)
    assert report["summary"]["removed"] == report["summary"]["added"] == 1
    assert report["summary"]["stale_documents"] == 3


def test_duplicate_ids_and_cross_project_rejected(model):
    a = snapshot(model)
    package, _ = generate(a)
    b = deepcopy(a)
    b["project_guid"] = ifcopenshell.guid.new()
    with pytest.raises(ValueError, match="same IFC project"):
        compare(a, b, package)
    member(model, "F-01").GlobalId = member(model, "F-02").GlobalId
    with pytest.raises(ValueError, match="unique valid"):
        snapshot(model)


def test_ambiguous_material_prevents_package_generation(model):
    post = member(model, "HSS-01")
    extra = model.create_entity("IfcMaterial", Name="Conflicting material")
    model.create_entity(
        "IfcRelAssociatesMaterial",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[post],
        RelatingMaterial=extra,
    )
    s = snapshot(model)
    assert (
        "Expected one named material"
        in next(r for r in s["components"] if r["tag"] == "HSS-01")["issues"]
    )
    with pytest.raises(ValueError, match="Resolve unsupported"):
        generate(s)


def test_dxf_svg_schedule_and_artifact_hashes_agree(model):
    s = snapshot(revise(model))
    package, files = generate(s, "B")
    same, same_files = generate(s, "B")
    assert same == package and same_files == files
    # SQLite stores canonical JSON, so key insertion order changes on reload.
    restored = json.loads(json.dumps(s, sort_keys=True))
    restored_package, restored_files = generate(restored, "B")
    assert restored_package == package and restored_files == files
    for name, data in files.items():
        assert hashlib.sha256(data).hexdigest() == package["artifacts"][name]
    for name in ("S-101", "S-501"):
        doc = ezdxf.read(io.StringIO(files[name + ".dxf"].decode()))
        assert doc.units == ezdxf.units.IN
        assert not doc.audit().has_errors
        assert len(doc.modelspace().query("DIMENSION")) >= 6
        ET.fromstring(files[name + ".svg"])
    circles = ezdxf.read(io.StringIO(files["S-101.dxf"].decode())).modelspace().query("CIRCLE")
    assert sorted(c.dxf.radius for c in circles) == [12.0, 15.0]
    foot = next(row for row in package["schedule"] if row["mark"] == "F-01")
    assert foot["dimensions_in"]["diameter"] == 30
    assert "30" in files["S-101.svg"].decode()
    assert "AS-01" in files["schedule.csv"].decode()
