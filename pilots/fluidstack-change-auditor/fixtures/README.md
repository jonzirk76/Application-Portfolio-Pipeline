# Original synthetic fixtures

Generated from scratch by `scripts/fixtures.py`, without employer assets or downloaded building data. Fixed UUID-derived GlobalIds, headers, and sorted relationship sets make generation reproducible. `manifest.json` records provenance and SHA-256 hashes.

The frame has six columns and ten beams. Revision B modifies only BEAM-014 from 4.000 to 4.500 m and assigns illustrative Grade B material. Profiles are solid rectangles 0.100 × 0.200 m; the structure is not an engineering-validated design.

Procurement contains 16 baseline BOM lines and one ordered PO line, PO-1042/1. Each line is one piece; the order intentionally retains its baseline cut length and specification.

Generated fixture data is dedicated under CC0-1.0. Dependencies retain their licenses. `make fixtures` overwrites the four generated data/manifest files; keep personal revisions elsewhere.
