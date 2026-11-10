"""Run inside a fresh Bonsai-enabled Blender GUI; records an assisted authoring run.

blender --python scripts/bonsai_author.py
Outputs go to data/bonsai-authoring/. Never run against an unsaved user session.
"""

import hashlib
import json
import textwrap
import time
import traceback
from pathlib import Path


def main():
    import blf
    import bonsai.tool as tool
    import bpy
    import ifcopenshell
    import ifcopenshell.util.element

    root = Path(__file__).resolve().parents[1]
    baseline = root / "fixtures/baseline.ifc"
    output = root / "data/bonsai-authoring"
    output.mkdir(parents=True, exist_ok=True)
    if bpy.app.background or tool.Ifc.get():
        raise RuntimeError("Use a fresh Blender GUI session with Bonsai enabled")
    if (output / "session.json").exists():
        raise RuntimeError("Archive the previous data/bonsai-authoring run first")
    original_hash = hashlib.sha256(baseline.read_bytes()).hexdigest()
    session = {
        "mode": "agent-assisted Bonsai GUI; native operators driven by Python",
        "blender": bpy.app.version_string,
        "ifcopenshell": ifcopenshell.version,
        "baseline_sha256": original_hash,
        "steps": [],
        "complete": False,
    }
    state = {"caption": "Agent-assisted Bonsai authoring; native IFC controls"}
    started = time.monotonic()

    def caption():
        lines = textwrap.wrap(state["caption"], 65)
        lines.append("Agent-assisted session | synthetic model")
        if "beam" in state:
            beam = state["beam"]
            material = ifcopenshell.util.element.get_material(beam)
            solid = beam.Representation.Representations[0].Items[0]
            lines += [
                f"BEAM-014 | Depth {solid.Depth:.3f} m | {material.Name}",
                f"GlobalId: {beam.GlobalId}",
            ]
        for i, line in enumerate(reversed(lines)):
            blf.position(0, 115, 30 + i * 25, 0)
            blf.size(0, 17)
            blf.color(0, 1, 1, 1, 1)
            blf.draw(0, line)

    handle = bpy.types.SpaceView3D.draw_handler_add(caption, (), "WINDOW", "POST_PIXEL")

    def write_session():
        (output / "session.json").write_text(json.dumps(session, indent=2) + "\n")

    def load():
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.context.preferences.view.ui_scale = 0.6
        bpy.ops.bim.load_project(
            filepath=str(baseline), should_start_fresh_session=False,
            skip_autosave_recovery=True,
        )
        model = tool.Ifc.get()
        beam = next(e for e in model.by_type("IfcBeam") if e.Tag == "BEAM-014")
        obj = tool.Ifc.get_object(beam)
        for selected in bpy.context.selected_objects:
            selected.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        state.update(model=model, beam=beam, obj=obj, guid=beam.GlobalId)
        bpy.ops.bim.get_representation_ifc_parameters()
        view = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
        region = next(r for r in view.regions if r.type == "WINDOW")
        with bpy.context.temp_override(area=view, region=region):
            bpy.ops.view3d.view_all(center=False)
        view.spaces.active.region_3d.view_distance = 12
        view.spaces.active.overlay.show_floor = False
        # The tested alpha build's extrusion guide retains an invalid RNA
        # target after a parameter update. Hide viewport gizmos for this run.
        view.spaces.active.show_gizmo = False
        for props in tool.Blender.get_area_props(bpy.context.screen):
            props.tab = "GEOMETRY"

    def length():
        params = tool.Geometry.get_mesh_props(state["obj"].data).ifc_parameters
        index = next(i for i, p in enumerate(params) if p.name == "IfcExtrudedAreaSolid/Depth")
        params[index].value = 4.5
        bpy.ops.bim.update_parametric_representation(index=index)

    def material():
        bpy.ops.bim.add_material(
            name="Grade B", category="steel",
            description="Illustrative specification; not an engineering grade",
        )
        grade = next(m for m in state["model"].by_type("IfcMaterial") if m.Name == "Grade B")
        props = tool.Material.get_object_material_props(state["obj"])
        props.material = str(grade.id())
        bpy.ops.bim.assign_material(obj=state["obj"].name, material_type="IfcMaterial")
        bpy.ops.bim.save_project(filepath=str(output / "stale-quantities.ifc"))

    def quantities():
        # Preserve the stale export as a negative control, then remove only this
        # occurrence's authored quantities. The auditor measures the actual solid.
        for rel in list(state["beam"].IsDefinedBy):
            if rel.is_a("IfcRelDefinesByProperties"):
                qto = rel.RelatingPropertyDefinition
                if qto.is_a("IfcElementQuantity"):
                    bpy.ops.bim.remove_pset(
                        pset_id=qto.id(), obj=state["obj"].name, obj_type="Object",
                    )

    def save():
        bpy.ops.bim.save_project(filepath=str(output / "bonsai-revised.ifc"))
        assert state["beam"].GlobalId == state["guid"]
        assert hashlib.sha256(baseline.read_bytes()).hexdigest() == original_hash
        session["revised_sha256"] = hashlib.sha256(
            (output / "bonsai-revised.ifc").read_bytes()
        ).hexdigest()
        session["ifc_originating_system"] = state["model"].header.file_name.originating_system

    steps = iter([
        ("Baseline IFC loaded: 4.000 m / Grade A", load),
        ("Bonsai extrusion parameter changed: 4.000 to 4.500 m", length),
        ("Grade B assigned to this beam; stale quantities saved as a control", material),
        ("Stale authored quantities removed from this occurrence", quantities),
        ("New IFC saved by Bonsai; original GlobalId preserved", save),
    ])

    def advance():
        try:
            label, action = next(steps)
        except StopIteration:
            session["complete"] = True
            write_session()
            return None
        try:
            action()
            state["caption"] = label
            beam = state["beam"]
            session["steps"].append({
                "label": label, "elapsed_seconds": round(time.monotonic() - started, 3),
                "global_id": beam.GlobalId,
                "depth_m": beam.Representation.Representations[0].Items[0].Depth,
                "material": ifcopenshell.util.element.get_material(beam).Name,
                "quantities": ifcopenshell.util.element.get_psets(beam, qtos_only=True),
            })
            write_session()
            for area in bpy.context.screen.areas:
                area.tag_redraw()
            return 7.0
        except Exception:
            session["error"] = traceback.format_exc()
            write_session()
            bpy.types.SpaceView3D.draw_handler_remove(handle, "WINDOW")
            return None

    # Allow the window recorder to attach before authoring begins.
    bpy.app.timers.register(advance, first_interval=10.0)


if __name__ == "__main__":
    main()
