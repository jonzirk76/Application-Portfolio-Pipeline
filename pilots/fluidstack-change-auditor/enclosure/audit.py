"""Narrow, explicit geometry and drawing-dependency rules for enclosure supports."""

import hashlib
import math
from collections import Counter, defaultdict

import ifcopenshell
import numpy as np
from ifcopenshell.util import element, placement, unit

from engine.audit import GUID, LENGTH_TOLERANCE, canonical_json, clean_number, differs

VERSION = "enclosure-1.0"
ROLES = {"IfcFooting": "footing", "IfcPlate": "plate", "IfcColumn": "post"}


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def positive(value):
    value = clean_number(value)
    if value <= 0:
        raise ValueError("Dimensions must be positive")
    return value


def measure(item, scale):
    if item.is_a() not in ROLES:
        raise ValueError("Unsupported class; requires footing, plate, or post")
    if item.HasOpenings:
        raise ValueError("Openings/voided solids are unsupported")
    reps = (
        [r for r in item.Representation.Representations if r.RepresentationIdentifier == "Body"]
        if item.Representation
        else []
    )
    if len(reps) != 1 or len(reps[0].Items) != 1:
        raise ValueError("Expected one Body with one solid")
    solid = reps[0].Items[0]
    if not solid.is_a("IfcExtrudedAreaSolid"):
        raise ValueError("Unsupported mesh, mapped, or boolean geometry; requires extrusion")
    direction = np.asarray(solid.ExtrudedDirection.DirectionRatios, dtype=float)
    if not np.allclose(direction / np.linalg.norm(direction), [0, 0, 1], atol=1e-10):
        raise ValueError("Only positive local Z extrusions are supported")
    if not item.ObjectPlacement:
        raise ValueError("Missing object placement")
    matrix = placement.get_local_placement(item.ObjectPlacement)
    matrix = matrix @ (
        placement.get_axis2placement(solid.Position) if solid.Position else np.eye(4)
    )
    profile = solid.SweptArea
    if getattr(profile, "Position", None):
        matrix = matrix @ placement.get_axis2placement(profile.Position)
    matrix[:3, 3] *= scale
    if not np.isfinite(matrix).all() or not np.allclose(matrix[:3, :3], np.eye(3), atol=1e-8):
        raise ValueError("This detail template requires unrotated vertical supports")
    depth = positive(solid.Depth * scale)
    kind = item.is_a()
    if kind == "IfcFooting" and profile.is_a() == "IfcCircleProfileDef":
        radius = positive(profile.Radius * scale)
        dims = {"diameter_m": radius * 2, "depth_m": depth}
        volume = math.pi * radius**2 * depth
    elif kind == "IfcPlate" and profile.is_a() == "IfcRectangleProfileDef":
        x, y = positive(profile.XDim * scale), positive(profile.YDim * scale)
        dims = {"width_m": x, "length_m": y, "thickness_m": depth}
        volume = x * y * depth
    elif kind == "IfcColumn" and profile.is_a() == "IfcRectangleHollowProfileDef":
        x, y, t = (positive(v * scale) for v in (profile.XDim, profile.YDim, profile.WallThickness))
        if 2 * t >= min(x, y):
            raise ValueError("HSS wall thickness leaves no hollow core")
        if any(
            getattr(profile, name, None) not in (None, 0.0)
            for name in ("InnerFilletRadius", "OuterFilletRadius")
        ):
            raise ValueError("Rounded HSS corners are unsupported; no approximate volume issued")
        dims = {"width_m": x, "length_m": y, "wall_thickness_m": t, "height_m": depth}
        volume = (x * y - (x - 2 * t) * (y - 2 * t)) * depth
    else:
        raise ValueError("Unsupported profile for this component role")
    return {
        **{k: clean_number(v) for k, v in dims.items()},
        "volume_m3": clean_number(volume),
        "x_m": clean_number(matrix[0, 3]),
        "y_m": clean_number(matrix[1, 3]),
        "z_m": clean_number(matrix[2, 3]),
    }, f"#{solid.id()} IfcExtrudedAreaSolid / #{profile.id()} {profile.is_a()}"


def extract(data, filename="enclosure.ifc"):
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("Maximum IFC size is 20 MiB")
    try:
        model = ifcopenshell.file.from_string(data.decode("utf-8-sig"))
        schema = model.schema
    except Exception as exc:
        raise ValueError("Unable to read IFC STEP data") from exc
    if schema != "IFC4":
        raise ValueError("Enclosure details support IFC4 only")
    projects = model.by_type("IfcProject")
    if len(projects) != 1 or not GUID.fullmatch(projects[0].GlobalId or ""):
        raise ValueError("Exactly one project with a valid GlobalId is required")
    units = projects[0].UnitsInContext
    if not units or not any(getattr(u, "UnitType", None) == "LENGTHUNIT" for u in units.Units):
        raise ValueError("Explicit length units are required")
    scale = positive(unit.calculate_unit_scale(model))
    items = model.by_type("IfcElement")
    if not items or len(items) > 2000:
        raise ValueError("Expected between 1 and 2,000 elements")
    ids = [e.GlobalId for e in items]
    if len(set(ids)) != len(ids) or any(not GUID.fullmatch(i or "") for i in ids):
        raise ValueError("Components must have unique valid GlobalIds")
    revision_id = hashlib.sha256(data).hexdigest()
    records = []
    for item in sorted(items, key=lambda e: e.GlobalId):
        groups = [g for g in element.get_groups(item) if g.ObjectType == "ENCLOSURE_SUPPORT"]
        record = {
            "guid": item.GlobalId,
            "tag": item.Tag,
            "class": item.is_a(),
            "role": ROLES.get(item.is_a()),
            "assembly": groups[0].Name if len(groups) == 1 else None,
            "assembly_guid": groups[0].GlobalId if len(groups) == 1 else None,
            "material": None,
            "dimensions": None,
            "geometry_source": None,
            "issues": [],
            "source": {
                "revision_id": revision_id,
                "step_id": item.id(),
                "file": filename,
                "global_id": item.GlobalId,
            },
        }
        if not record["assembly"]:
            record["issues"].append("Assign exactly one named ENCLOSURE_SUPPORT group")
        if not record["tag"]:
            record["issues"].append("Missing component mark")
        mat = element.get_material(item, should_inherit=True)
        assignments = [r for r in item.HasAssociations if r.is_a("IfcRelAssociatesMaterial")]
        if not assignments:
            item_type = element.get_type(item)
            assignments = [
                r
                for r in getattr(item_type, "HasAssociations", ())
                if r.is_a("IfcRelAssociatesMaterial")
            ]
        if len(assignments) == 1 and mat and mat.is_a("IfcMaterial") and mat.Name:
            record["material"] = mat.Name
        else:
            record["issues"].append("Expected one named material")
        try:
            record["dimensions"], record["geometry_source"] = measure(item, scale)
            for qset in element.get_psets(item, qtos_only=True).values():
                for name in ("NetVolume", "GrossVolume"):
                    if name in qset and differs(
                        qset[name] * unit.calculate_unit_scale(model, "VOLUMEUNIT"),
                        record["dimensions"]["volume_m3"],
                        0.000001,
                    ):
                        record["issues"].append(f"Authored {name} conflicts with measured volume")
        except (ValueError, TypeError, AttributeError, RuntimeError) as exc:
            record["issues"].append(str(exc))
        records.append(record)
    tags = Counter(r["tag"] for r in records)
    for r in records:
        if tags[r["tag"]] > 1:
            r["issues"].append("Duplicate component mark")
    return {
        "id": revision_id,
        "filename": filename,
        "schema": model.schema,
        "scope": "enclosure",
        "project_guid": projects[0].GlobalId,
        "length_unit_to_m": scale,
        "components": records,
    }


def fields(record):
    """Measured and declared detail fields, excluding byte identity and STEP numbering."""
    return {
        "tag": record["tag"],
        "class": record["class"],
        "assembly": record["assembly"],
        "assembly_guid": record["assembly_guid"],
        "material": record["material"],
        **(record["dimensions"] or {}),
    }


def fingerprint(record):
    return digest(fields(record))


def changed_fields(av, bv):
    changes = []
    for key in sorted(av.keys() | bv.keys()):
        x, y = av.get(key), bv.get(key)
        numeric = isinstance(x, (int, float)) and isinstance(y, (int, float))
        tolerance = 0.000001 if key == "volume_m3" else LENGTH_TOLERANCE
        different = differs(x, y, tolerance) if numeric else x != y
        if different:
            changes.append(
                {
                    "field": key,
                    "before": x,
                    "after": y,
                    "delta": clean_number(y - x) if numeric else None,
                }
            )
    return changes


def assemblies(snapshot):
    groups = defaultdict(list)
    for record in snapshot["components"]:
        groups[record["assembly"] or "Unassigned"].append(record)
    return dict(sorted(groups.items()))


def alignment(snapshot):
    findings = []
    for name, records in assemblies(snapshot).items():
        roles = Counter(r["role"] for r in records)
        if roles != Counter({"footing": 1, "plate": 1, "post": 1}) or any(
            r["issues"] for r in records
        ):
            findings.append(
                {
                    "assembly": name,
                    "state": "undetermined",
                    "guids": [r["guid"] for r in records],
                    "reasons": ["Requires one supported footing, plate, and post"],
                }
            )
            continue
        f, p, h = [
            next(r["dimensions"] for r in records if r["role"] == role)
            for role in ("footing", "plate", "post")
        ]
        reasons = []
        for label, item in (("Plate", p), ("Post", h)):
            offset = math.hypot(item["x_m"] - f["x_m"], item["y_m"] - f["y_m"])
            if offset > LENGTH_TOLERANCE:
                reasons.append(f"{label} center is {offset / 0.0254:.3f} in off footing center")
        if differs(f["z_m"] + f["depth_m"], p["z_m"], LENGTH_TOLERANCE):
            reasons.append("Plate underside differs from footing top (direct-bearing assumption)")
        if differs(p["z_m"] + p["thickness_m"], h["z_m"], LENGTH_TOLERANCE):
            reasons.append("Post base differs from plate top")
        if any(
            abs(h[k] - p[k]) + h[w] / 2 > p[w] / 2 + LENGTH_TOLERANCE
            for k, w in (("x_m", "width_m"), ("y_m", "length_m"))
        ):
            reasons.append("Post footprint extends beyond the plate")
        if reasons:
            findings.append(
                {
                    "assembly": name,
                    "state": "review_required",
                    "guids": [r["guid"] for r in records],
                    "reasons": reasons,
                }
            )
    return findings


def compare(baseline, revised, package):
    if baseline["project_guid"] != revised["project_guid"]:
        raise ValueError("Compare revisions from the same IFC project")
    if package["project_guid"] != revised["project_guid"]:
        raise ValueError("Drawing package belongs to a different project")
    a = {r["guid"]: r for r in baseline["components"]}
    b = {r["guid"]: r for r in revised["components"]}
    entries = []
    for guid in sorted(a.keys() | b.keys()):
        before, after = a.get(guid), b.get(guid)
        changes = []
        if before and after:
            changes = changed_fields(fields(before), fields(after))
        kind = (
            "added"
            if not before
            else "removed"
            if not after
            else "modified"
            if changes
            else "unchanged"
        )
        issues = list(
            dict.fromkeys((before or {}).get("issues", []) + (after or {}).get("issues", []))
        )
        entries.append(
            {
                "guid": guid,
                "kind": kind,
                "before": before,
                "after": after,
                "changes": changes,
                "issues": issues,
            }
        )
    drawing_findings = []
    for doc in package["documents"]:
        affected = [
            guid
            for guid, expected in doc["dependencies"].items()
            if guid not in b
            or changed_fields(expected["fields"], fields(b[guid]))
            or b[guid]["issues"]
        ]
        added = sorted(b.keys() - doc["dependencies"].keys())
        # All three pilot documents cover the entire segment, including new supports.
        if affected or added:
            drawing_findings.append(
                {
                    "document_id": doc["id"],
                    "title": doc["title"],
                    "issue_revision": package["issue_revision"],
                    "source_revision": package["source_revision"],
                    "guids": sorted(set(affected + added)),
                    "reason": "Issued detail inputs differ from the current model",
                }
            )
    findings = alignment(revised)
    summary = dict(Counter(e["kind"] for e in entries))
    for kind in ("modified", "unchanged", "added", "removed"):
        summary.setdefault(kind, 0)
    summary.update(
        stale_documents=len(drawing_findings),
        alignment_findings=len(findings),
        uncertain_components=sum(bool(e["issues"]) for e in entries),
    )
    report = {
        "engine_version": VERSION,
        "baseline_id": baseline["id"],
        "revised_id": revised["id"],
        "package_id": package["id"],
        "summary": summary,
        "entries": entries,
        "drawing_findings": drawing_findings,
        "alignment_findings": findings,
        "scope": "Detail consistency; concentric, vertical, direct-bearing supports. "
        "Illustrative dimensions; no structural capacity or code approval.",
        "tolerances": {"length_m": LENGTH_TOLERANCE, "volume_m3": 0.000001},
    }
    report["id"] = digest(report)
    return report
