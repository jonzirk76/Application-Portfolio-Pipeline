"""Headless audit entry point: python -m scripts.audit --help."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from api.models import Procurement
from engine.audit import compare, extract
from scripts.fixtures import ROOT


def main():
    parser = argparse.ArgumentParser(
        description="Compare supported IFC4 members and synthetic procurement"
    )
    parser.add_argument("--baseline", type=Path, default=ROOT / "fixtures/baseline.ifc")
    parser.add_argument("--revised", type=Path, default=ROOT / "fixtures/revised.ifc")
    parser.add_argument(
        "--procurement", type=Path, default=ROOT / "fixtures/procurement.json"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "data/audit.json")
    args = parser.parse_args()
    started = perf_counter()
    procurement = Procurement.model_validate_json(
        args.procurement.read_text()
    ).model_dump()
    report = compare(
        extract(args.baseline.read_bytes(), args.baseline.name),
        extract(args.revised.read_bytes(), args.revised.name),
        procurement,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "report": str(args.output),
                "summary": report["summary"],
                "elapsed_seconds": round(perf_counter() - started, 4),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
