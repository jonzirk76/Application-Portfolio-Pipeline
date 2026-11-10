"""Generate original, deterministic IFC4 fixtures; no external model assets."""

import hashlib
import json
import uuid
from pathlib import Path

import ifcopenshell
import numpy as np
from ifcopenshell.api import (
    aggregate,
    context,
    geometry,
    material,
    project,
    pset,
    root,
    spatial,
    unit,
)

ROOT = Path(__file__).resolve().parents[1]


def sort_sets(model):
    for entity in model:
        for attribute in ("RelatedObjects", "RelatedElements", "Units"):
            values = getattr(entity, attribute, None)
            if values:
                setattr(
                    entity,
                    attribute,
                    tuple(sorted(values, key=lambda value: value.id())),
                )


def make_model():
    model = project.create_file(version="IFC4")
    building_project = root.create_entity(
        model, ifc_class="IfcProject", name="Equipment support pilot"
    )
    unit.assign_unit(
        model,
        units=[
            unit.add_si_unit(model, unit_type="LENGTHUNIT"),
            unit.add_si_unit(model, unit_type="AREAUNIT"),
            unit.add_si_unit(model, unit_type="VOLUMEUNIT"),
        ],
    )
    site = root.create_entity(model, ifc_class="IfcSite", name="Synthetic site")
    building = root.create_entity(
        model, ifc_class="IfcBuilding", name="Support structure"
    )
    storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Ground")
    for parent, child in [
        (building_project, site),
        (site, building),
        (building, storey),
    ]:
        aggregate.assign_object(model, products=[child], relating_object=parent)
    parent = context.add_context(model, context_type="Model")
    body = context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=parent,
    )
    grade = material.add_material(
        model,
        name="Grade A",
        category="steel",
        description="Illustrative specification; not an engineering grade",
    )
    members = [
        ("IfcColumn", (x, y, 0), (0, 0, 1), 3.0) for x in (0, 4) for y in (0, 3, 6)
    ]
    members += [("IfcBeam", (x, y, 3), (0, 1, 0), 3.0) for x in (0, 4) for y in (0, 3)]
    members += [
        ("IfcBeam", (0, y, z), (1, 0, 0), 4.0) for z in (1.5, 3) for y in (0, 3, 6)
    ]
    for number, (kind, origin, direction, length) in enumerate(members, 1):
        tag = f"{'BEAM' if kind == 'IfcBeam' else 'COL'}-{number:03d}"
        member = root.create_entity(model, ifc_class=kind, name=tag)
        member.Tag = tag
        spatial.assign_container(model, products=[member], relating_structure=storey)
        profile = model.create_entity(
            "IfcRectangleProfileDef", ProfileType="AREA", XDim=0.1, YDim=0.2
        )
        representation = geometry.add_profile_representation(
            model, context=body, profile=profile, depth=length
        )
        geometry.assign_representation(
            model, product=member, representation=representation
        )
        transform = np.eye(4)
        axis = np.array(direction, dtype=float)
        x_axis = np.array(
            (1, 0, 0) if direction == (0, 0, 1) else (0, 0, 1), dtype=float
        )
        transform[:3, :3] = np.column_stack((x_axis, np.cross(axis, x_axis), axis))
        transform[:3, 3] = origin
        geometry.edit_object_placement(model, product=member, matrix=transform)
        material.assign_material(model, products=[member], material=grade)
        quantities = pset.add_qto(
            model, product=member, name=f"Qto_{kind[3:]}BaseQuantities"
        )
        pset.edit_qto(
            model,
            qto=quantities,
            properties={"Length": length, "NetVolume": length * 0.02},
        )
    # API creation uses random GUIDs; replace every root, including relationships.
    for index, entity in enumerate(model.by_type("IfcRoot")):
        entity.GlobalId = ifcopenshell.guid.compress(
            uuid.uuid5(uuid.NAMESPACE_URL, f"openbim-pilot/{entity.is_a()}/{index}").hex
        )
    model.header.file_name.name = "original-pilot-fixture.ifc"
    model.header.file_name.time_stamp = "2026-11-09T00:00:00"
    model.header.file_name.author = ("OpenBIM pilot",)
    model.header.file_name.organization = ("Independent synthetic demonstration",)
    sort_sets(model)
    return model


def revise(model):
    revised = ifcopenshell.file.from_string(model.to_string())
    target = next(item for item in revised.by_type("IfcBeam") if item.Tag == "BEAM-014")
    target.Representation.Representations[0].Items[0].Depth = 4.5
    grade = material.add_material(
        revised,
        name="Grade B",
        category="steel",
        description="Illustrative revised specification",
    )
    material.assign_material(revised, products=[target], material=grade)
    quantities = next(
        rel.RelatingPropertyDefinition
        for rel in target.IsDefinedBy
        if rel.RelatingPropertyDefinition.is_a("IfcElementQuantity")
    )
    pset.edit_qto(
        revised, qto=quantities, properties={"Length": 4.5, "NetVolume": 0.09}
    )
    # The new material association is also deterministic.
    for rel in target.HasAssociations:
        rel.GlobalId = ifcopenshell.guid.compress(
            uuid.uuid5(uuid.NAMESPACE_URL, "openbim-pilot/revision-b/material-014").hex
        )
    sort_sets(revised)
    return revised


def procurement_for(model):
    lines = []
    for member in sorted(model.by_type("IfcBuildingElement"), key=lambda e: e.Tag):
        lines.append(
            {
                "id": f"BOM-{member.Tag}",
                "component_guid": member.GlobalId,
                "tag": member.Tag,
                "specification": "Grade A",
                "length_m": float(
                    member.Representation.Representations[0].Items[0].Depth
                ),
                "count": 1,
            }
        )
    target = next(line for line in lines if line["tag"] == "BEAM-014")
    return {
        "synthetic": True,
        "bom_revision": "A",
        "bom_lines": lines,
        "po_lines": [
            {
                "id": "PO-1042/1",
                "po": "PO-1042",
                "bom_line_id": target["id"],
                "specification": "Grade A",
                "length_m": 4.0,
                "count": 1,
                "status": "ordered",
            }
        ],
    }


def generate(destination=ROOT / "fixtures"):
    destination.mkdir(parents=True, exist_ok=True)
    baseline = make_model()
    (destination / "baseline.ifc").write_text(baseline.to_string())
    (destination / "revised.ifc").write_text(revise(baseline).to_string())
    (destination / "procurement.json").write_text(
        json.dumps(procurement_for(baseline), indent=2) + "\n"
    )
    files = {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in ("baseline.ifc", "revised.ifc", "procurement.json")
    }
    (destination / "manifest.json").write_text(
        json.dumps(
            {
                "origin": "Generated by scripts/fixtures.py",
                "license": "CC0-1.0",
                "synthetic": True,
                "schema": "IFC4",
                "member_count": 16,
                "sha256": files,
            },
            indent=2,
        )
        + "\n"
    )
    return destination


if __name__ == "__main__":
    print(generate())
