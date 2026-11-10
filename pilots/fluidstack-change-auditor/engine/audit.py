"""Semantic comparison and illustrative impact rules, independent of HTTP/UI."""

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal

import ifcopenshell
import numpy as np
from ifcopenshell.util import element, placement, unit

VERSION = "pilot-1.0"
LENGTH_TOLERANCE = 0.0001
VOLUME_TOLERANCE = 0.000001
GUID = re.compile(r"^[0-3][0-9A-Za-z_$]{21}$")


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def differs(a, b, tolerance):
    return abs(Decimal(str(a)) - Decimal(str(b))) > Decimal(str(tolerance))


def clean_number(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Non-finite numeric value")
    return round(value, 10)


def extract(data: bytes, filename="model.ifc"):
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("Maximum IFC size is 20 MiB")
    try:
        model = ifcopenshell.file.from_string(data.decode("utf-8-sig"))
        schema = model.schema
    except Exception as exc:
        raise ValueError("Unable to read IFC STEP data") from exc
    if schema != "IFC4":
        raise ValueError("This pilot supports IFC4 only")
    projects = model.by_type("IfcProject")
    if len(projects) != 1:
        raise ValueError("Exactly one IfcProject is required")
    project = projects[0]
    if not project.UnitsInContext or not any(
        u.UnitType == "LENGTHUNIT"
        for u in project.UnitsInContext.Units
        if hasattr(u, "UnitType")
    ):
        raise ValueError("Explicit IFC project length units are required")
    scale = unit.calculate_unit_scale(model)
    volume_scale = unit.calculate_unit_scale(model, "VOLUMEUNIT")
    digest = hashlib.sha256(data).hexdigest()
    entities = model.by_type("IfcElement")
    if len(entities) > 2000:
        raise ValueError("Pilot limit: 2,000 IFC elements")
    counts = Counter(e.GlobalId for e in entities if e.GlobalId)
    records = []
    for entity in sorted(
        entities, key=lambda e: (e.Tag or "", e.GlobalId or "", e.id())
    ):
        issues = []
        guid = entity.GlobalId
        valid_id = bool(guid and GUID.fullmatch(guid))
        if not valid_id:
            issues.append("Missing or invalid GlobalId")
        if guid and counts[guid] > 1:
            issues.append("Duplicate GlobalId")
        container = element.get_container(entity)
        source = {
            "revision_id": digest,
            "step_id": entity.id(),
            "global_id": guid,
            "entity": entity.is_a(),
            "file": filename,
        }
        record = {
            "key": f"{digest}:{entity.id()}",
            "guid": guid,
            "valid_id": valid_id and counts[guid] == 1,
            "tag": entity.Tag,
            "name": entity.Name,
            "class": entity.is_a(),
            "container": container.Name if container else None,
            "container_guid": container.GlobalId if container else None,
            "source": source,
            "issues": issues,
            "geometry": None,
            "placement": None,
            "specification": None,
            "material_source": [],
            "authored_quantities": {},
        }
        try:
            matrix = placement.get_local_placement(entity.ObjectPlacement)
            matrix[:3, 3] *= scale
            record["placement"] = [
                [clean_number(v) for v in row] for row in matrix.tolist()
            ]
            if not entity.ObjectPlacement:
                issues.append("Missing object placement")
            if entity.is_a() not in ("IfcBeam", "IfcColumn"):
                raise ValueError(
                    "Unsupported element class; only beams and columns are measured"
                )
            if entity.HasOpenings:
                raise ValueError(
                    "Openings/voided members are outside the supported quantity scope"
                )
            bodies = (
                [
                    rep
                    for rep in entity.Representation.Representations
                    if rep.RepresentationIdentifier == "Body"
                ]
                if entity.Representation
                else []
            )
            if len(bodies) != 1 or len(bodies[0].Items) != 1:
                raise ValueError(
                    "Expected one Body representation containing one solid"
                )
            solid = bodies[0].Items[0]
            if not solid.is_a("IfcExtrudedAreaSolid") or not solid.SweptArea.is_a(
                "IfcRectangleProfileDef"
            ):
                raise ValueError(
                    "Unsupported geometry; requires a straight rectangular extrusion"
                )
            direction = np.asarray(solid.ExtrudedDirection.DirectionRatios, dtype=float)
            direction /= np.linalg.norm(direction)
            if not np.allclose(direction, (0, 0, 1), atol=1e-10):
                raise ValueError(
                    "Oblique or reversed extrusion is outside the supported scope"
                )
            profile = solid.SweptArea
            length, width, height = [
                clean_number(v * scale)
                for v in (solid.Depth, profile.XDim, profile.YDim)
            ]
            if min(length, width, height) <= 0:
                raise ValueError("Dimensions must be positive")
            solid_matrix = (
                placement.get_axis2placement(solid.Position)
                if solid.Position
                else np.eye(4)
            )
            solid_matrix[:3, 3] *= scale
            profile_matrix = (
                placement.get_axis2placement(profile.Position)
                if profile.Position
                else np.eye(4)
            )
            profile_matrix[:3, 3] *= scale
            record["geometry"] = {
                "length_m": length,
                "width_m": width,
                "height_m": height,
                "volume_m3": clean_number(length * width * height),
                "solid_position": np.round(solid_matrix, 10).tolist(),
                "profile_position": np.round(profile_matrix, 10).tolist(),
                "source_path": f"#{solid.id()}.Depth / #{profile.id()}.XDim,YDim",
            }
        except (ValueError, AttributeError, TypeError, RuntimeError) as exc:
            issues.append(str(exc))
        try:
            materials = element.get_materials(entity, should_inherit=True)
            names = sorted(
                {m.Name.strip() for m in materials if m.Name and m.Name.strip()}
            )
            record["material_source"] = [
                {"step_id": m.id(), "name": m.Name} for m in materials
            ]
            if len(names) == 1 and len(materials) == 1:
                record["specification"] = names[0]
            else:
                issues.append("Missing or ambiguous material specification")
        except (ValueError, AttributeError, RuntimeError):
            issues.append("Unable to resolve material specification")
        for rel in entity.IsDefinedBy:
            qto = rel.RelatingPropertyDefinition
            if not qto.is_a("IfcElementQuantity"):
                continue
            for quantity in qto.Quantities:
                if quantity.is_a("IfcQuantityLength") and quantity.Name == "Length":
                    factor = (
                        unit.calculate_unit_scale(model)
                        if not quantity.Unit
                        else unit.convert_unit(
                            1,
                            quantity.Unit,
                            unit.get_project_unit(model, "LENGTHUNIT"),
                        )
                        * scale
                    )
                    value = clean_number(quantity.LengthValue * factor)
                    key, computed, tolerance = "length_m", "length_m", LENGTH_TOLERANCE
                elif quantity.is_a("IfcQuantityVolume") and quantity.Name in (
                    "NetVolume",
                    "GrossVolume",
                ):
                    if quantity.Unit:
                        issues.append("Explicit volume quantity unit is not supported")
                        continue
                    value = clean_number(quantity.VolumeValue * volume_scale)
                    key, computed, tolerance = (
                        "volume_m3",
                        "volume_m3",
                        VOLUME_TOLERANCE,
                    )
                else:
                    continue
                record["authored_quantities"][f"{qto.Name}.{quantity.Name}"] = {
                    "value": value,
                    "unit": key,
                    "step_id": quantity.id(),
                }
                if record["geometry"] and differs(
                    value, record["geometry"][computed], tolerance
                ):
                    issues.append(
                        f"Authored {quantity.Name} disagrees with geometry at #{quantity.id()}"
                    )
        records.append(record)
    return {
        "id": digest,
        "filename": filename,
        "schema": model.schema,
        "project_guid": project.GlobalId,
        "length_unit_to_m": scale,
        "extractor_version": VERSION,
        "components": records,
    }


def field_changes(a, b):
    changes = []
    for field in ("class", "tag", "name", "container", "specification"):
        if a[field] != b[field]:
            changes.append(
                {"field": field, "before": a[field], "after": b[field], "unit": None}
            )
    ga, gb = a["geometry"], b["geometry"]
    if ga and gb:
        for field in ("length_m", "width_m", "height_m", "volume_m3"):
            tolerance = VOLUME_TOLERANCE if field == "volume_m3" else LENGTH_TOLERANCE
            if differs(ga[field], gb[field], tolerance):
                changes.append(
                    {
                        "field": field,
                        "before": ga[field],
                        "after": gb[field],
                        "delta": clean_number(gb[field] - ga[field]),
                        "unit": "m³" if field == "volume_m3" else "m",
                    }
                )
        for field in ("solid_position", "profile_position"):
            if matrix_changed(ga[field], gb[field]):
                changes.append(
                    {
                        "field": field,
                        "before": ga[field],
                        "after": gb[field],
                        "unit": "SI matrix",
                    }
                )
    elif bool(ga) != bool(gb):
        changes.append(
            {
                "field": "geometry_availability",
                "before": bool(ga),
                "after": bool(gb),
                "unit": None,
            }
        )
    if matrix_changed(a["placement"], b["placement"]):
        changes.append(
            {
                "field": "placement",
                "before": a["placement"],
                "after": b["placement"],
                "unit": "SI matrix",
            }
        )
    return changes


def matrix_changed(a, b):
    if a is None or b is None:
        return a != b
    return any(
        differs(a[i][j], b[i][j], LENGTH_TOLERANCE if j == 3 else 1e-8)
        for i in range(4)
        for j in range(4)
    )


def compare(a, b, procurement):
    """Return a stable, evidence-bearing report; no wall-clock metadata."""
    if a["project_guid"] != b["project_guid"]:
        raise ValueError("Revisions must belong to the same IFC project")
    before, after = a["components"], b["components"]
    pending_a, pending_b = {c["key"]: c for c in before}, {c["key"]: c for c in after}
    pairs = []
    by_guid = {c["guid"]: c for c in after if c["valid_id"]}
    for old in before:
        new = by_guid.get(old["guid"]) if old["valid_id"] else None
        if new:
            pairs.append((old, new, "global_id"))
            pending_a.pop(old["key"])
            pending_b.pop(new["key"])

    def fallback(c):
        return (
            (c["class"], c["tag"], c["container_guid"])
            if c["tag"] and c["container_guid"]
            else None
        )

    groups_a, groups_b = defaultdict(list), defaultdict(list)
    for c in pending_a.values():
        groups_a[fallback(c)].append(c)
    for c in pending_b.values():
        groups_b[fallback(c)].append(c)
    for key in sorted(k for k in groups_a if k is not None):
        old, new = groups_a[key], groups_b.get(key, [])
        if len(old) == len(new) == 1 and not any(
            "Duplicate GlobalId" in c["issues"] for c in old + new
        ):
            pairs.append((old[0], new[0], "tag_class_container_candidate"))
            pending_a.pop(old[0]["key"])
            pending_b.pop(new[0]["key"])
    # Do not infer removals/additions where broken identity could hide a counterpart.
    identity_broken = any(
        not c["valid_id"] for c in list(pending_a.values()) + list(pending_b.values())
    )
    entries = []
    for old, new, method in pairs:
        changes = field_changes(old, new)
        uncertain = method != "global_id" or bool(old["issues"] or new["issues"])
        entries.append(
            {
                "kind": "modified" if changes else "unchanged",
                "match_method": method,
                "confidence": "candidate" if method != "global_id" else "exact",
                "before": old,
                "after": new,
                "changes": changes,
                "uncertain": uncertain,
            }
        )
    for side, remaining in (("removed", pending_a), ("added", pending_b)):
        for c in remaining.values():
            uncertain = identity_broken or bool(c["issues"])
            entries.append(
                {
                    "kind": "unresolved" if identity_broken else side,
                    "match_method": "unmatched",
                    "confidence": "unresolved" if identity_broken else "exact",
                    "before": c if side == "removed" else None,
                    "after": c if side == "added" else None,
                    "changes": [],
                    "uncertain": uncertain,
                }
            )
    entries.sort(
        key=lambda e: (
            (e["after"] or e["before"])["tag"] or "",
            (e["after"] or e["before"])["source"]["step_id"],
        )
    )
    impacts = []
    baseline_bom = deepcopy(procurement["bom_lines"])
    baseline_ids = Counter(c["guid"] for c in before)
    diagnostics = [
        f"{line['id']}: BOM component has no unique baseline IFC identity"
        for line in baseline_bom
        if baseline_ids[line["component_guid"]] != 1
    ]
    revised_bom = []
    for c in after:
        linked = (
            [line for line in baseline_bom if line["component_guid"] == c["guid"]]
            if c["valid_id"]
            else []
        )
        entry = next(e for e in entries if e["after"] and e["after"]["key"] == c["key"])
        revised_bom.append(
            {
                "id": linked[0]["id"]
                if len(linked) == 1
                else f"NEW-{c['source']['step_id']}",
                "baseline_line_id": linked[0]["id"] if len(linked) == 1 else None,
                "revision_id": b["id"],
                "component_guid": c["guid"],
                "tag": c["tag"],
                "specification": c["specification"],
                "length_m": c["geometry"]["length_m"] if c["geometry"] else None,
                "count": 1,
                "source": c["source"],
                "review_state": "undetermined" if entry["uncertain"] else "evaluated",
            }
        )
    for index, entry in enumerate(entries):
        entry["id"] = f"change-{index + 1:03d}"
        old, new = entry["before"], entry["after"]
        component = new or old
        guid = (old or new)["guid"]
        lines = (
            [line for line in baseline_bom if line["component_guid"] == guid]
            if guid
            else []
        )
        entry["bom_line_ids"] = [line["id"] for line in lines]
        entry["issues"] = sorted(
            set((old["issues"] if old else []) + (new["issues"] if new else []))
        )
        if entry["confidence"] != "exact":
            entry["issues"].append(
                "Identity requires review; procurement impact is not definitive"
            )
        reasons = []
        if entry["uncertain"]:
            reasons.append(
                (
                    "IDENTITY_OR_DATA_UNKNOWN",
                    "undetermined",
                    "Resolve identity or source-data diagnostics before procurement review",
                    None,
                    None,
                )
            )
        elif entry["kind"] == "added":
            reasons.append(
                (
                    "NEW_COMPONENT",
                    "review_required",
                    "Source the new component and reconcile its BOM line",
                    None,
                    None,
                )
            )
        elif entry["kind"] == "removed":
            for line in lines:
                pos = [
                    po
                    for po in procurement["po_lines"]
                    if po["bom_line_id"] == line["id"]
                ]
                for po in pos or [None]:
                    reasons.append(
                        (
                            "REMOVED_COMPONENT",
                            "review_required",
                            "Review removed BOM item and any existing order for cancellation",
                            line,
                            po,
                        )
                    )
        else:
            if not lines:
                reasons.append(
                    (
                        "BOM_LINK_MISSING",
                        "undetermined",
                        "No baseline BOM lineage is available",
                        None,
                        None,
                    )
                )
            for line in lines:
                # Validate the claimed baseline lineage before reasoning about the PO.
                if old and (
                    line["specification"] != old["specification"]
                    or differs(
                        line["length_m"], old["geometry"]["length_m"], LENGTH_TOLERANCE
                    )
                ):
                    reasons.append(
                        (
                            "BASELINE_BOM_MISMATCH",
                            "undetermined",
                            "Baseline BOM does not agree with baseline IFC evidence",
                            line,
                            None,
                        )
                    )
                    continue
                for po in (
                    p for p in procurement["po_lines"] if p["bom_line_id"] == line["id"]
                ):
                    if po["specification"] != new["specification"]:
                        reasons.append(
                            (
                                "PO_SPECIFICATION_MISMATCH",
                                "review_required",
                                "Ordered specification differs from the revised member",
                                line,
                                po,
                            )
                        )
                    if differs(
                        po["length_m"], new["geometry"]["length_m"], LENGTH_TOLERANCE
                    ):
                        reasons.append(
                            (
                                "PO_CUT_LENGTH_MISMATCH",
                                "review_required",
                                "Ordered cut length differs from the revised member",
                                line,
                                po,
                            )
                        )
                fields = {change["field"] for change in entry["changes"]}
                if fields - {
                    "name",
                    "tag",
                    "container",
                    "specification",
                    "length_m",
                    "volume_m3",
                }:
                    reasons.append(
                        (
                            "ENGINEERING_REVIEW",
                            "review_required",
                            "Placement, profile or class changed; synthetic PO checks do not establish suitability",
                            line,
                            None,
                        )
                    )
        entry["review_state"] = (
            "undetermined"
            if any(r[1] == "undetermined" for r in reasons)
            else "review_required"
            if reasons or entry["kind"] != "unchanged"
            else "no_discrepancy"
        )
        for rule, state, message, line, po in reasons:
            impacts.append(
                {
                    "id": f"impact-{len(impacts) + 1:03d}",
                    "change_id": entry["id"],
                    "component_guid": component["guid"],
                    "tag": component["tag"],
                    "rule": rule,
                    "rule_version": VERSION,
                    "state": state,
                    "message": message,
                    "bom_line_id": line["id"] if line else None,
                    "po_line_id": po["id"] if po else None,
                    "ordered": deepcopy(po),
                    "before_source": old["source"] if old else None,
                    "after_source": new["source"] if new else None,
                }
            )
    counts = Counter(e["kind"] for e in entries)
    affected_bom = {
        line for e in entries if e["kind"] != "unchanged" for line in e["bom_line_ids"]
    }
    affected_bom.update(i["bom_line_id"] for i in impacts if i["bom_line_id"])
    summary = {
        kind: counts[kind]
        for kind in ("modified", "added", "removed", "unchanged", "unresolved")
    }
    summary.update(
        {
            "affected_bom_lines": len(affected_bom),
            "flagged_po_lines": len(
                {i["po_line_id"] for i in impacts if i["po_line_id"]}
            ),
            "uncertain_components": sum(
                e["review_state"] == "undetermined" for e in entries
            ),
            "impact_reasons": len(impacts),
        }
    )
    report = {
        "diagnostics": diagnostics,
        "review_state": "undetermined"
        if diagnostics or summary["uncertain_components"]
        else "review_required"
        if impacts or summary["modified"] or summary["added"] or summary["removed"]
        else "no_discrepancy",
        "engine_version": VERSION,
        "synthetic_procurement": True,
        "scope": "IFC4 rectangular beam/column extrusions; illustrative procurement rules; no engineering approval",
        "tolerances": {"length_m": LENGTH_TOLERANCE, "volume_m3": VOLUME_TOLERANCE},
        "baseline": {k: v for k, v in a.items() if k != "components"},
        "revised": {k: v for k, v in b.items() if k != "components"},
        "procurement_sha256": hashlib.sha256(
            canonical_json(procurement).encode()
        ).hexdigest(),
        "summary": summary,
        "entries": entries,
        "impacts": impacts,
        "bom": {"baseline": baseline_bom, "revised": revised_bom},
        "purchase_orders": procurement["po_lines"],
    }
    report["id"] = hashlib.sha256(canonical_json(report).encode()).hexdigest()
    return report
