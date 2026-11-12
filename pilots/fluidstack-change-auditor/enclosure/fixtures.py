"""Original CC0 inch-authored enclosure assemblies with deterministic revisions."""

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
    group,
    material,
    project,
    root,
    spatial,
    style,
    unit,
)

from scripts.fixtures import ROOT, sort_sets

INCH = 0.0254
FIXTURES = ROOT / "fixtures/enclosure"


def make_model():
    model = project.create_file(version="IFC4")
    proj = root.create_entity(model, ifc_class="IfcProject", name="Enclosure detailing example")
    unit.assign_unit(
        model,
        units=[
            unit.add_conversion_based_unit(model, name="inch"),
            unit.add_si_unit(model, unit_type="AREAUNIT"),
            unit.add_si_unit(model, unit_type="VOLUMEUNIT"),
        ],
    )
    site = root.create_entity(model, ifc_class="IfcSite", name="Illustrative site")
    building = root.create_entity(model, ifc_class="IfcBuilding", name="Enclosure segment")
    level = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Footing top datum")
    for parent, child in [(proj, site), (site, building), (building, level)]:
        aggregate.assign_object(model, products=[child], relating_object=parent)
    parent = context.add_context(model, context_type="Model")
    body = context.add_context(
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=parent,
    )
    concrete = material.add_material(model, name="Illustrative cast-in-place concrete")
    steel = material.add_material(model, name="Illustrative steel; grade unspecified")
    for index, x in enumerate((0, 96), 1):
        assembly = group.add_group(model, name=f"AS-{index:02}")
        assembly.ObjectType = "ENCLOSURE_SUPPORT"
        specs = [
            (
                "IfcFooting",
                "F",
                "PAD_FOOTING",
                -48,
                48,
                model.create_entity("IfcCircleProfileDef", ProfileType="AREA", Radius=12.0),
                concrete,
                (0.65, 0.67, 0.64),
            ),
            (
                "IfcPlate",
                "BP",
                "USERDEFINED",
                0,
                0.5,
                model.create_entity(
                    "IfcRectangleProfileDef", ProfileType="AREA", XDim=10.0, YDim=10.0
                ),
                steel,
                (0.72, 0.49, 0.22),
            ),
            (
                "IfcColumn",
                "HSS",
                "COLUMN",
                0.5,
                72,
                model.create_entity(
                    "IfcRectangleHollowProfileDef",
                    ProfileType="AREA",
                    XDim=4.0,
                    YDim=4.0,
                    WallThickness=0.25,
                    InnerFilletRadius=0.0,
                    OuterFilletRadius=0.0,
                ),
                steel,
                (0.28, 0.44, 0.39),
            ),
        ]
        for kind, prefix, predefined, z, depth, profile, mat, color in specs:
            item = root.create_entity(
                model, ifc_class=kind, predefined_type=predefined, name=f"{prefix}-{index:02}"
            )
            item.Tag = item.Name
            if kind == "IfcPlate":
                item.ObjectType = "BASE_PLATE"
            spatial.assign_container(model, products=[item], relating_structure=level)
            group.assign_group(model, products=[item], group=assembly)
            representation = geometry.add_profile_representation(
                model, context=body, profile=profile, depth=depth * INCH
            )
            geometry.assign_representation(model, product=item, representation=representation)
            matrix = np.eye(4)
            matrix[:3, 3] = np.array([x, 0, z]) * INCH
            geometry.edit_object_placement(model, product=item, matrix=matrix)
            material.assign_material(model, products=[item], material=mat)
            surface = style.add_style(model, name=prefix)
            style.add_surface_style(
                model,
                style=surface,
                ifc_class="IfcSurfaceStyleShading",
                attributes={
                    "SurfaceColour": dict(zip(("Red", "Green", "Blue"), color, strict=True))
                },
            )
            style.assign_representation_styles(
                model, shape_representation=representation, styles=[surface]
            )
    for index, entity in enumerate(model.by_type("IfcRoot")):
        entity.GlobalId = ifcopenshell.guid.compress(
            uuid.uuid5(uuid.NAMESPACE_URL, f"ans-enclosure/{entity.is_a()}/{index}").hex
        )
    model.header.file_name.name = "enclosure-example.ifc"
    model.header.file_name.time_stamp = "2026-11-11T00:00:00"
    model.header.file_name.author = ("Independent portfolio example",)
    model.header.file_name.organization = ("Original CC0 illustrative geometry",)
    sort_sets(model)
    return model


def revise(model, scenario="diameter"):
    revised = ifcopenshell.file.from_string(model.to_string())
    if scenario == "diameter":
        footing = next(e for e in revised.by_type("IfcFooting") if e.Tag == "F-01")
        footing.Representation.Representations[0].Items[0].SweptArea.Radius = 15.0
    elif scenario == "alignment":
        post = next(e for e in revised.by_type("IfcColumn") if e.Tag == "HSS-01")
        point = post.ObjectPlacement.RelativePlacement.Location
        point.Coordinates = (point.Coordinates[0] + 4.0, *point.Coordinates[1:])
    else:
        raise ValueError("Unknown enclosure scenario")
    sort_sets(revised)
    return revised


def generate(destination=FIXTURES):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    baseline = make_model()
    models = {
        "baseline": baseline,
        "revised": revise(baseline),
        "misaligned": revise(baseline, "alignment"),
    }
    hashes = {}
    for name, model in models.items():
        data = model.to_string().encode()
        (destination / f"{name}.ifc").write_bytes(data)
        hashes[f"{name}.ifc"] = hashlib.sha256(data).hexdigest()
    (destination / "manifest.json").write_text(
        json.dumps(
            {
                "origin": "Original geometry generated by enclosure/fixtures.py",
                "license": "CC0-1.0",
                "synthetic": True,
                "schema": "IFC4",
                "authoring_units": "inch",
                "assemblies": 2,
                "components": 6,
                "assumptions": [
                    "4x4 inch HSS and 10x10 inch plate approximate owner experience",
                    "Other dimensions are illustrative, not engineered",
                    "HSS has idealized sharp corners; no catalog weight claim",
                    "Concentric supports, direct bearing, no modeled anchors or welds",
                ],
                "sha256": hashes,
            },
            indent=2,
        )
        + "\n"
    )
    return destination


if __name__ == "__main__":
    print(generate())
