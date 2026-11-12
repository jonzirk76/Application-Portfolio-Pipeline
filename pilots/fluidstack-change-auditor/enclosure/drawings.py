"""One measured detail contract drives editable inch DXF, SVG, and schedules."""

import csv
import hashlib
import io
import json
import re
from html import escape

import ezdxf

from enclosure.audit import alignment, assemblies, digest, fields, fingerprint
from enclosure.fixtures import INCH

# Artifact identity must not change because the same package was generated later.
# ezdxf's fixed metadata mode removes timestamps and random document GUIDs.
ezdxf.options.write_fixed_meta_data_for_testing = True
WIDTH, HEIGHT = 260, 190
COLORS = {
    "S-CONC": "#68776d",
    "S-STEEL": "#27564a",
    "S-PLATE": "#a5752b",
    "S-DIMS": "#4c6560",
    "S-TEXT": "#243b33",
    "S-BORDER": "#a5b1a8",
}


def inches(record):
    return {
        key: round(value / INCH, 9)
        for key, value in sorted(record["dimensions"].items())
        if key != "volume_m3"
    }


def fmt(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


class Sheet:
    def __init__(self, title, sheet_id, revision, source):
        self.doc = ezdxf.new("R2010")
        self.doc.units = ezdxf.units.IN
        self.doc.header["$MEASUREMENT"] = 0
        for index, layer in enumerate(COLORS, 1):
            self.doc.layers.add(layer, color=index + 1)
        self.doc.dimstyles.new(
            "ENCLOSURE",
            dxfattribs={
                "dimtxt": 2.0,
                "dimasz": 0.8,
                "dimtad": 1,
                "dimdec": 3,
                "dimzin": 8,
            },
        )
        self.space = self.doc.modelspace()
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
            f'width="1560" height="1140" role="img" aria-label="{escape(title)}">',
            '<rect width="100%" height="100%" fill="#fffef9"/>',
        ]
        self.rect(2, 2, WIDTH - 4, HEIGHT - 4, "S-BORDER")
        self.text(8, HEIGHT - 11, title, 4)
        self.text(8, HEIGHT - 17, "ENCLOSURE SUPPORTS / ILLUSTRATIVE DETAILING EXAMPLE", 2)
        self.line(2, 15, WIDTH - 2, 15, "S-BORDER")
        self.text(
            8,
            10,
            f"{sheet_id}  |  ISSUE {revision}  |  REVIEW DRAFT  |  ALL DIMENSIONS IN INCHES",
            2,
        )
        self.text(8, 5, f"SOURCE SHA-256 {source[:24]}  |  FULL HASH IN ISSUE MANIFEST", 1.7)

    def line(self, x1, y1, x2, y2, layer="S-DIMS"):
        self.space.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer})
        self.svg.append(
            f'<line x1="{x1}" y1="{HEIGHT - y1}" x2="{x2}" y2="{HEIGHT - y2}" '
            f'stroke="{COLORS[layer]}" stroke-width="0.2"/>'
        )

    def rect(self, x, y, width, height, layer):
        self.space.add_lwpolyline(
            [(x, y), (x + width, y), (x + width, y + height), (x, y + height)],
            close=True,
            dxfattribs={"layer": layer},
        )
        self.svg.append(
            f'<rect x="{x}" y="{HEIGHT - y - height}" width="{width}" height="{height}" '
            f'fill="none" stroke="{COLORS[layer]}" stroke-width="0.3"/>'
        )

    def circle(self, x, y, radius, layer):
        self.space.add_circle((x, y), radius, dxfattribs={"layer": layer})
        self.svg.append(
            f'<circle cx="{x}" cy="{HEIGHT - y}" r="{radius}" fill="none" '
            f'stroke="{COLORS[layer]}" stroke-width="0.3"/>'
        )

    def text(self, x, y, value, size=2.2):
        self.space.add_text(value, dxfattribs={"height": size, "layer": "S-TEXT", "insert": (x, y)})
        self.svg.append(
            f'<text x="{x}" y="{HEIGHT - y}" fill="{COLORS["S-TEXT"]}" '
            f'font-family="sans-serif" font-size="{size}">{escape(value)}</text>'
        )

    def dimension(self, p1, p2, base, vertical=False):
        self.space.add_linear_dim(
            base=base,
            p1=p1,
            p2=p2,
            angle=90 if vertical else 0,
            dimstyle="ENCLOSURE",
            dxfattribs={"layer": "S-DIMS"},
        ).render()
        # SVG projection of the same measured dimension, without duplicating DXF entities.
        if vertical:
            a, b = (base[0], p1[1]), (base[0], p2[1])
            tx, ty = base[0] + 1, (p1[1] + p2[1]) / 2
            value = abs(p2[1] - p1[1])
        else:
            a, b = (p1[0], base[1]), (p2[0], base[1])
            tx, ty = (p1[0] + p2[0]) / 2, base[1] + 1
            value = abs(p2[0] - p1[0])
        for u, v in ((p1, a), (p2, b), (a, b)):
            self.svg.append(
                f'<path d="M{u[0]} {HEIGHT - u[1]} L{v[0]} {HEIGHT - v[1]}" '
                'fill="none" stroke="#4c6560" stroke-width="0.15"/>'
            )
        for x, y in (a, b):
            self.svg.append(
                f'<path d="M{x - 0.7} {HEIGHT - y + 0.7} l1.4 -1.4" '
                'stroke="#4c6560" stroke-width="0.2"/>'
            )
        self.svg.append(
            f'<text x="{tx}" y="{HEIGHT - ty}" font-family="sans-serif" '
            f'font-size="2" fill="#4c6560">{fmt(value)}</text>'
        )

    def export(self):
        output = io.StringIO()
        self.doc.write(output)
        return {
            "dxf": output.getvalue().encode(),
            "svg": ("\n".join(self.svg) + "</svg>\n").encode(),
        }


def render_plan(snapshot, issue):
    sheet = Sheet("FOUNDATION PLAN & BASE PLATE DETAILS", "S-101", issue, snapshot["id"])
    records = snapshot["components"]
    min_x = min(inches(r)["x_m"] for r in records)
    min_y = min(inches(r)["y_m"] for r in records)
    max_x = max(inches(r)["x_m"] for r in records)
    max_y = max(inches(r)["y_m"] for r in records)
    if max_x - min_x > 160 or max_y - min_y > 50:
        raise ValueError("Support layout exceeds the fixed detail sheet; review template scale")
    sheet.text(10, 159, "PLAN — COMPONENT LOCATIONS AT 1:1 IN DXF MODEL SPACE", 2.3)
    for index, (name, members) in enumerate(assemblies(snapshot).items()):
        for r in members:
            d = inches(r)
            x, y = d["x_m"] - min_x + 40, d["y_m"] - min_y + 120
            rx = d.get("diameter_m", d.get("width_m", 0)) / 2
            ry = d.get("diameter_m", d.get("length_m", 0)) / 2
            if x - rx < 8 or x + rx > 248 or y - ry < 95 or y + ry + 5 > 152:
                raise ValueError("Component exceeds the fixed plan template; review sheet scale")
            if r["role"] == "footing":
                radius = d["diameter_m"] / 2
                sheet.circle(x, y, radius, "S-CONC")
                sheet.dimension((x - radius, y), (x + radius, y), (x, y - radius - 8))
                sheet.text(x - radius, y + radius + 5, f"{name} / {r['tag']}")
            else:
                layer = "S-PLATE" if r["role"] == "plate" else "S-STEEL"
                sheet.rect(
                    x - d["width_m"] / 2, y - d["length_m"] / 2, d["width_m"], d["length_m"], layer
                )
                if r["role"] == "post":
                    t = d["wall_thickness_m"]
                    sheet.rect(
                        x - d["width_m"] / 2 + t,
                        y - d["length_m"] / 2 + t,
                        d["width_m"] - 2 * t,
                        d["length_m"] - 2 * t,
                        layer,
                    )
        p = next(r for r in members if r["role"] == "plate")
        h = next(r for r in members if r["role"] == "post")
        pd, hd = inches(p), inches(h)
        x, y = 40 + index * 110, 63
        sheet.rect(
            x - pd["width_m"] / 2, y - pd["length_m"] / 2, pd["width_m"], pd["length_m"], "S-PLATE"
        )
        hx, hy = x + hd["x_m"] - pd["x_m"], y + hd["y_m"] - pd["y_m"]
        sheet.rect(
            hx - hd["width_m"] / 2,
            hy - hd["length_m"] / 2,
            hd["width_m"],
            hd["length_m"],
            "S-STEEL",
        )
        t = hd["wall_thickness_m"]
        sheet.rect(
            hx - hd["width_m"] / 2 + t,
            hy - hd["length_m"] / 2 + t,
            hd["width_m"] - 2 * t,
            hd["length_m"] - 2 * t,
            "S-STEEL",
        )
        sheet.dimension((x - pd["width_m"] / 2, y), (x + pd["width_m"] / 2, y), (x, y - 12))
        sheet.dimension((x, y - pd["length_m"] / 2), (x, y + pd["length_m"] / 2), (x + 12, y), True)
        sheet.text(x - 22, 80, f"{p['tag']} / {h['tag']} — BASE PLATE PLAN")
        sheet.text(
            x - 22,
            42,
            f"PLATE {fmt(pd['width_m'])} x {fmt(pd['length_m'])} x {fmt(pd['thickness_m'])}",
        )
        sheet.text(x - 22, 37, f"HSS {fmt(hd['width_m'])} x {fmt(hd['length_m'])} x {fmt(t)} WALL")
    footings = sorted(
        (inches(r) for r in records if r["role"] == "footing"), key=lambda d: d["x_m"]
    )
    if len(footings) == 2:
        points = [(d["x_m"] - min_x + 40, d["y_m"] - min_y + 120) for d in footings]
        sheet.dimension(points[0], points[1], (points[0][0], 88))
    sheet.text(
        8,
        25,
        "Anchors and welds are not specified in this example. Refer to S-501 for vertical dimensions.",
        2,
    )
    sheet.text(
        8,
        20,
        "HSS corners are idealized as sharp. Dimensions are illustrative; package requires owner review.",
        2,
    )
    return sheet.export()


def render_sections(snapshot, issue):
    sheet = Sheet("SUPPORT SECTIONS & ELEVATIONS", "S-501", issue, snapshot["id"])
    for index, (name, members) in enumerate(assemblies(snapshot).items()):
        f, p, h = [
            next(r for r in members if r["role"] == role) for role in ("footing", "plate", "post")
        ]
        fd, pd, hd = inches(f), inches(p), inches(h)
        x, y = 50 + 115 * index, 40
        for r, d, width, depth, layer in [
            (f, fd, fd["diameter_m"], fd["depth_m"], "S-CONC"),
            (p, pd, pd["width_m"], pd["thickness_m"], "S-PLATE"),
            (h, hd, hd["width_m"], hd["height_m"], "S-STEEL"),
        ]:
            cx, bottom = x + d["x_m"] - fd["x_m"], y + d["z_m"] - fd["z_m"]
            if bottom < 35 or bottom + depth > 165 or width > 60:
                raise ValueError("Component exceeds the fixed section template; review sheet scale")
            sheet.rect(cx - width / 2, bottom, width, depth, layer)
            sheet.text(x + 18, bottom + depth / 2, r["tag"])
            if r["role"] == "post":
                for sign in (-1, 1):
                    xx = cx + sign * (width / 2 - d["wall_thickness_m"])
                    sheet.line(xx, bottom, xx, bottom + depth, "S-STEEL")
        sheet.dimension((x - fd["diameter_m"] / 2, y), (x + fd["diameter_m"] / 2, y), (x, y - 8))
        sheet.dimension((x, y), (x, y + fd["depth_m"]), (x - 25, y), True)
        bottom = y + hd["z_m"] - fd["z_m"]
        sheet.dimension((x, bottom), (x, bottom + hd["height_m"]), (x - 25, bottom), True)
        sheet.text(x - 25, 167, f"{name} / SECTION THROUGH POST CENTER", 2.3)
        sheet.text(x + 18, y + fd["depth_m"] + 5, f"PLATE t={fmt(pd['thickness_m'])}", 2)
        sheet.text(x - 25, 25, f"FOOTING TOP EL. {fmt(fd['z_m'] + fd['depth_m'])} in", 2)
    sheet.text(
        8,
        20,
        "Direct-bearing, concentric layout assumed. Reinforcement, anchors, welds and soil design are unspecified.",
        2,
    )
    return sheet.export()


def generate(snapshot, issue="A"):
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,20}", issue):
        raise ValueError(
            "Issue revision must be 1–20 letters, digits, dots, hyphens, or underscores"
        )
    if any(r["issues"] for r in snapshot["components"]):
        raise ValueError(
            "Resolve unsupported geometry and source issues before generating drawings"
        )
    groups = assemblies(snapshot)
    if len(groups) > 2 or any(f["state"] == "undetermined" for f in alignment(snapshot)):
        raise ValueError("Template requires one or two complete support assemblies")
    files = {}
    documents = []
    dependencies = {
        r["guid"]: {"fingerprint": fingerprint(r), "fields": fields(r)}
        for r in snapshot["components"]
    }
    for sheet_id, title, render in [
        ("S-101", "Foundation plan and plate details", render_plan),
        ("S-501", "Support sections and elevations", render_sections),
    ]:
        formats = {}
        for ext, data in render(snapshot, issue).items():
            name = f"{sheet_id}.{ext}"
            files[name] = data
            formats[ext] = name
        documents.append(
            {"id": sheet_id, "title": title, "dependencies": dependencies, "files": formats}
        )
    schedule = []
    for r in sorted(snapshot["components"], key=lambda r: (r["assembly"], r["tag"])):
        schedule.append(
            {
                "mark": r["tag"],
                "assembly": r["assembly"],
                "guid": r["guid"],
                "role": r["role"],
                "material": r["material"],
                "dimensions_in": {k.removesuffix("_m"): round(v, 6) for k, v in inches(r).items()},
                "volume_m3": r["dimensions"]["volume_m3"],
            }
        )
    files["schedule.json"] = (json.dumps(schedule, indent=2) + "\n").encode()
    csv_file = io.StringIO(newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["assembly", "mark", "role", "dimensions (in)", "volume (m3)", "GlobalId"])
    for row in schedule:
        cells = [
            row["assembly"],
            row["mark"],
            row["role"],
            "; ".join(f"{k}={fmt(v)}" for k, v in row["dimensions_in"].items()),
            row["volume_m3"],
            row["guid"],
        ]
        writer.writerow(
            [
                "'" + c if isinstance(c, str) and c.startswith(("=", "+", "-", "@")) else c
                for c in cells
            ]
        )
    files["schedule.csv"] = csv_file.getvalue().encode()
    documents.append(
        {
            "id": "SCH-01",
            "title": "Component schedule",
            "dependencies": dependencies,
            "files": {"json": "schedule.json", "csv": "schedule.csv"},
        }
    )
    package = {
        "source_revision": snapshot["id"],
        "project_guid": snapshot["project_guid"],
        "issue_revision": issue,
        "status": "review_draft",
        "template_version": "1.0",
        "documents": documents,
        "schedule": schedule,
        "alignment_findings": alignment(snapshot),
        "artifacts": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "assumptions": "Illustrative dimensions; sharp HSS corners; concentric direct bearing; "
        "anchors, welds, reinforcement, and structural capacity unspecified.",
    }
    package["id"] = digest(package)
    return package, files
