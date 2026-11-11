# ANS extension — enclosure foundation detailing

Prepared November 11, 2026. Status: **initial source research complete; proposed scope,
not implemented**. This extends the completed OpenBIM Engineering Change Auditor.

## Role and portfolio position

Target: **ANS — Structural CAD Design Manager**. The owner supplied the full
description from [Indeed](https://www.indeed.com/viewjob?jk=2e6661ce96d72303) after
the posting could not be retrieved directly. The supplied description is the
basis for this mapping; no separate employer verification is claimed.

The role emphasizes Autodesk drawing production, foundation and connection
details, CAD standards and templates, drawing revision control, automation, and
coordination across structural, civil, electrical, and geotechnical disciplines.
BIM is a plus. The advertisement does not specifically name enclosure footings;
the connection is to its cast-in-place concrete and non-building structure work.

The owner's relevant experience is an enclosure assembly incorporating
**cylindrical poured concrete footers, base plates, and HSS posts**. The owner
selected a nominal 4 × 4 post and 10 × 10 base plate as approximate example sizes;
inches are assumed from context. Enclosure use, anchor arrangement, and design
criteria have not been supplied.
Do not describe that experience as BESS work without confirmation.

Working project name: **Enclosure Foundation Detail Coordinator**.

| Field | Proposed profile |
| --- | --- |
| User | CAD lead checking a revised enclosure support assembly before drawing issue |
| Problem | A footing, post, or connection change leaves a plan, detail, or schedule inconsistent |
| Deliverable | Small IFC assembly, coordinated drawing package, and an evidence-linked revision report |
| Value | Make detailing assumptions explicit and identify exactly which deliverables need review |
| Reuse | Existing revision identity, source hashes, comparison workflow, viewer, and export evidence |
| New capability | Circular concrete geometry, hollow steel profiles, connection data, and drawing dependencies |
| Portfolio boundary | Independent demonstration; no ANS project data or endorsement |

Proposed case-study statement, to use only after implementation:

> Extended an IFC revision auditor into an enclosure foundation detailing workflow
> that links cylindrical concrete footings, base plates, and HSS posts to drawing
> details and schedules, exposing stale deliverables after a design revision.

This demonstrates standards and automation work. Team leadership and expert
Autodesk proficiency require additional evidence from the owner's experience.

## Public IFC model research

Two models were downloaded to temporary storage and parsed with the installed
IfcOpenShell 0.9.0.post1. Exact source commits, checksums, sizes, and entity counts
are in [the inspection record](artifacts/ans/model-survey.json). These are entity
and representation inspections, not a visual review or a full validity check.

| Candidate | Verified content | Suitability |
| --- | --- | --- |
| [buildingSMART Building-Structural IFC4](https://github.com/buildingSMART/Certification-datasets/blob/80d976a9b193a26a8e928c3e79bff67af1de68a8/IFC%204.0.2.1%20%28IFC%204%20ADD2%20TC1%29/Simple-Scene/Building-Structural.ifc) | 185,185 bytes; 17 elements; one `IfcFooting` named house foundation, represented by a triangulated face set; no `IfcColumn` or `IfcPlate` entities | Compact external interoperability reference; unsuitable as a ready-made parametric enclosure assembly |
| [buildingSMART Medical-Dental Clinic structural model](https://github.com/buildingsmart-community/Community-Sample-Test-Files/blob/31eb1dd0a0406fb9ebf0ebd823b48e1ec95afc08/IFC%202.3.0.1%20%28IFC%202x3%29/Medical-Dental%20Clinic/Clinic_Structural.ifc) | 19,058,175 bytes; IFC2X3; 1,094 elements; 96 footings and 195 columns; no `IfcPlate`, `IfcMechanicalFastener`, or named hollow profile entities | Richer foundation reference, but requires schema and representation work; no complete target assembly verified |

Both permit adaptation under CC BY 4.0 according to their publishers:
[Certification license](https://github.com/buildingSMART/Certification-datasets/blob/80d976a9b193a26a8e928c3e79bff67af1de68a8/LICENSE)
and [Clinic attribution instructions](https://github.com/buildingsmart-community/Community-Sample-Test-Files/blob/31eb1dd0a0406fb9ebf0ebd823b48e1ec95afc08/IFC%202.3.0.1%20%28IFC%202x3%29/Medical-Dental%20Clinic/README.md).
Preserve those notices, source links, and a description of modifications with any
redistributed derivative. The Clinic publisher specifies attribution to
`BSI (2020) "Medical-Dental Test Files," buildingSMART International`.

Class absence does not prove absence of a shape: an exporter may encode a plate
as another entity. Neither inspection establishes an exact cylindrical
footing/base-plate/HSS assembly. VIKTOR's public structural sample was also
considered, but its repository tree exposed no license file; reuse rights were
not established, so it is not selected.

**Recommendation:** author a small original parametric IFC4 assembly reflecting
the owner's detailing experience. Retain the public samples as external import
references. This avoids spending the next prototype converting an unrelated
building model. An original fixture can use the same explicit CC0 convention as
the first pilot; copied third-party geometry would retain its own attribution.

## First demonstration

Use a short enclosure segment with two repeated support assemblies. One is the
changed assembly; the other is an unchanged control. Represent enclosure infill
only as needed to explain the support layout.

Each assembly contains a cylindrical cast-in-place foundation, a base plate,
and an HSS post. Record the footing diameter and concrete depth, top elevation,
post section and wall thickness, plate dimensions and thickness, and component
marks. Confirm the connection arrangement before adding anchor or weld details.
Use clearly labeled demonstration dimensions where the owner cannot recall them.

Initial fixture inputs (illustrative geometry, not structural sizing):

| Parameter | Baseline input | Basis |
| --- | --- | --- |
| HSS outside dimensions | 4 × 4 in | Owner's approximate example |
| Base-plate plan dimensions | 10 × 10 in | Owner's approximate example |
| HSS wall thickness | 1/4 in | Proposed fixture input; not a verified catalog section |
| HSS length above plate | 72 in | Proposed fixture input |
| Base-plate thickness | 1/2 in | Proposed fixture input |
| Concrete cylinder diameter | 24 in | Proposed fixture input |
| Concrete cylinder depth | 48 in | Proposed fixture input |
| Revised cylinder diameter | 30 in on one assembly | Proposed change for the demonstration |

Preserve inch-based authoring/display values and normalize measurements to SI
inside the comparison engine. An idealized hollow profile must disclose its
corner-radius assumptions; do not label its computed volume as a catalog weight.

Generate a foundation plan, typical section/elevation, base-plate detail, and
component schedule from an explicit detail data contract. Give every drawing
and schedule its own revision and source-model hash. Keep engineering input
values separate from software-computed quantities.

Demonstrate a footing diameter revision while intentionally retaining the old
issued schedule/detail. The report should identify the changed foundation, its
quantity delta, and affected drawing references. Regenerating and reviewing the
package resolves the stale entries. A second case moves a post relative to its
plate and footing, exposing an alignment discrepancy against the declared
assembly layout. A concentric layout is a fixture assumption, not a universal
engineering requirement.

The first version checks documented dimensions, alignment, and revision
consistency. Structural capacity, soil capacity, embedment adequacy, and code
compliance are not outcomes of those checks.

## Dependency-ordered workplan

Aim for a first vertical slice in roughly two working sessions, using the first
pilot's delivery as a reference, not a verified time estimate for this scope.
Defer broader model ingestion before dropping the drawing evidence.

1. **Assembly and fixture contract.** Confirm the remembered assembly; author
   IFC4 baseline/revision pairs with stable GlobalIds and an unchanged assembly.
   Define component marks, relationships, units, drawing IDs, and source hashes.
   Use `IfcFooting` for a shallow footing; do not classify a deep foundation from
   its cylindrical shape alone. Use `IfcColumn` for the post and `IfcPlate` for
   the plate. Choose the exact profile from the confirmed HSS shape.
2. **Geometry and detailing extraction.** Add circular extrusions and supported
   hollow HSS profiles, including explicit treatment of corner radii. Track
   diameter, concrete depth, plate thickness, and HSS wall thickness as distinct
   dimensions. Do not reuse a solid rectangular beam's volume for hollow steel.
   Unsupported mapped, voided, or mesh geometry must remain visibly unsupported.
3. **Detail and schedule package.** Create a consistent layer/block naming
   convention, units, dimension styles, component marks, title block, and issue
   register. Produce editable DXF plus a reviewable PDF or SVG. Define which
   detail fields are generated and which require an engineering input.
4. **Revision dependencies.** Link component changes to affected sheet/detail
   IDs and schedule entries. Report before/after values, source revisions, and
   the specific review reason. Distinguish a stale artifact from an incorrect
   engineering design. Preserve the existing procurement demonstration.
5. **Browser and CAD review.** Select the affected assembly in the existing
   viewer and open its associated detail/report. Inspect the DXF in Autodesk
   software when available, checking scale, fonts, dimensions, layers, and plot
   output. DXF generation alone is not evidence of an Autodesk round trip.
6. **Evidence and release.** Record an edit → stale detail → corrected package
   walkthrough, owner review, regression results, and actual session effort.
   Preserve the source bytes and drawing issue manifest used in the recording.

Start with adjacent modules in the existing pilot so revision storage and viewer
behavior can be reused. Extract shared infrastructure only when an actual second
consumer requires it. Establish stable `ans-*` commit scopes when implementation
ownership is concrete; follow the existing dependency-order policy.

## Acceptance gates

- A baseline compared with itself produces no change or stale-detail finding.
- A diameter-only revision changes the correct footing and concrete quantity;
  the other support assembly remains unchanged.
- Hollow steel volume and wall thickness are preserved; unsupported profiles
  produce an explicit limitation rather than an invented quantity.
- A declared alignment violation identifies the post, plate, and foundation
  involved, with the assumed target layout visible to the reviewer.
- An old detail/schedule revision is flagged, and a corrected issue resolves it.
- Plan, section, detail, and schedule agree on supported dimensions and marks.
- Source hashes and drawing revisions survive export and reimport.
- Existing Fluidstack Python and browser checks continue to pass.
- Owner reviews the drawing package and the demonstrated detailing workflow.

## Software implications

The installed Python, IfcOpenShell, Bonsai, FastAPI, and browser stack are enough
for the model and audit work. Keep the existing Vite and web-ifc pins.

For DXF generation, [ezdxf](https://ezdxf.readthedocs.io/en/stable/) is a candidate
addition. Its documented drawing add-on supports SVG/PDF output; choose and lock
the required rendering dependencies when implementing that deliverable. No
additional packages have been installed for this research. Autodesk availability
remains to be confirmed before native CAD review; inch-based dimensions are the
working assumption for this fixture.
