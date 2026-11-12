"""Reproduce enclosure fixtures, drawing issues, and audit evidence without a browser."""

import argparse
import hashlib
import json
from pathlib import Path

from enclosure.audit import compare, extract
from enclosure.drawings import generate as drawings
from enclosure.fixtures import FIXTURES, generate
from scripts.fixtures import ROOT


def run(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    generate()
    sources = {
        name: (FIXTURES / f"{name}.ifc").read_bytes()
        for name in ("baseline", "revised", "misaligned")
    }
    snapshots = {name: extract(data, f"enclosure-{name}.ifc") for name, data in sources.items()}
    packages = {}
    for issue, name in (("A", "baseline"), ("B", "revised")):
        package, files = drawings(snapshots[name], issue)
        packages[issue] = package
        folder = destination / f"issue-{issue}"
        folder.mkdir(exist_ok=True)
        for filename, data in files.items():
            (folder / filename).write_bytes(data)
        (folder / "source.ifc").write_bytes(sources[name])
        (folder / "manifest.json").write_text(json.dumps(package, indent=2) + "\n")
    a, b = snapshots["baseline"], snapshots["revised"]
    reports = {
        "stale-audit": compare(a, b, packages["A"]),
        "current-audit": compare(a, b, packages["B"]),
        "unchanged-control": compare(a, a, packages["A"]),
        "alignment-audit": compare(a, snapshots["misaligned"], packages["A"]),
    }
    for name, report in reports.items():
        (destination / f"{name}.json").write_text(json.dumps(report, indent=2) + "\n")
    manifest = {
        "method": "Deterministic original IFC fixtures and generated drawing packages; no manual CAD authoring claimed",
        "license": "Original model and drawing assets CC0-1.0",
        "summaries": {name: report["summary"] for name, report in reports.items()},
        "sha256": {
            str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(destination.rglob("*"))
            if p.is_file() and p != destination / "manifest.json"
        },
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/enclosure-demo")
    args = parser.parse_args()
    print(json.dumps(run(args.output)["summaries"], indent=2))
