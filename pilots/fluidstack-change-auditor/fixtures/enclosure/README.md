# Original enclosure fixtures

Original model assets dedicated under **CC0-1.0**. No geometry from the researched
public IFC models was copied. Regenerate with `python -m enclosure.fixtures` from
the pilot root, using the locked environment.

Two support assemblies each contain a cylindrical cast-in-place concrete
footing, base plate, and square hollow post. The owner selected approximate
4 × 4-inch HSS outside dimensions and a 10 × 10-inch plate. All other dimensions
are illustrative: 1/4-inch post wall, 72-inch post height, 1/2-inch plate thickness,
24-inch footing diameter, and 48-inch concrete depth. No catalog section, loads,
soil properties, reinforcement, anchors, welds, or engineered sizing are claimed.

The IFC4 source uses inch length units, SI area/volume units, stable GlobalIds,
explicit `ENCLOSURE_SUPPORT` groups, and assigned materials. HSS corners are
idealized as sharp. Group marks are AS-01 and AS-02. Footing tops are at elevation
zero; plates bear directly on the footings and posts start at the plate tops.
Footing centers are 96 inches apart.

- `baseline.ifc`: two concentric assemblies.
- `revised.ifc`: F-01 diameter increases from 24 to 30 inches; other components
  retain their identity and geometry.
- `misaligned.ifc`: HSS-01 moves 4 inches in X; the plate and footing stay fixed.
- `manifest.json`: provenance, assumptions, and source-file SHA-256 hashes.

The intended workflow is a detailing and revision-consistency example. In a real
project, foundation classification and dimensions follow the engineering design.
