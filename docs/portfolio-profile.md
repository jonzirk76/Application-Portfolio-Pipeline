# Portfolio profile — pilot 001

Prepared November 9, 2026. Status: **proposed; no completed implementation or measured results yet**.

| Field | Profile |
| --- | --- |
| Program | Application Portfolio Pipeline |
| Project | OpenBIM Engineering Change Auditor |
| Target | Fluidstack — Software Engineer, Manufacturing & Supply Chain |
| Intended user | Engineer or procurement reviewer reconciling a model revision with ordered items |
| Problem | A design change can leave BOM and purchase-order assumptions inconsistent with the revised component |
| Proposed value | Explain which records require review and expose the source evidence for each conclusion |
| Scope | Small IFC4 structural frame; two revisions; synthetic BOM/procurement records; local application |
| Time budget | Two calendar days, 20 focused hours including setup and validation |
| Stack | Python, IfcOpenShell, SQLite, FastAPI, TypeScript/Vite, That Open; Bonsai for authoring |
| Differentiator | Traceable geometry/specification → BOM → PO impact with deterministic negative controls |
| Independence | Personal project; no Fluidstack affiliation or endorsement; no employer code, data, or proprietary rules |

## Positioning

Planned project description:

> A local IFC engineering change auditor that compares model revisions, traces supported geometry and material changes into synthetic BOM and procurement records, and produces deterministic reports with source evidence.

The case study should show that the author can learn an unfamiliar engineering format, choose a narrow consequential workflow, integrate mature libraries, and make uncertainty visible. The engineering depth comes from identity, units, immutable revision history, and explainable impact rules.

## Job-to-evidence mapping

These are our interpretations of the [published role](https://fluidstack.com/jobs/1f191895-fcfd-4cfb-8d4f-2cc3904e3cf2), reviewed November 9, 2026. Every artifact below is planned.

| Relevant area | Proposed evidence | Honest boundary |
| --- | --- | --- |
| Python/TypeScript delivery | Engine, API, browser interface, tests | Portfolio software, not production deployment |
| BOM and procurement consistency | Revision-linked BOM/PO discrepancy report | Synthetic records; no ERP integration |
| Engineering change traceability | Immutable snapshots and source-to-impact chain | Narrow supported IFC representation |
| Autonomous delivery under deadlines | Work log, release artifacts, recorded effort | One experiment does not establish repeatability |
| Operator-oriented interfaces | Focused review table and 90-second walkthrough | Usability/adoption unproven without external evaluation |
| AI-assisted development | Documented assistance, review decisions, corrections | Coding assistance does not establish deployed LLM/MCP experience |
| Production LLM extraction and real operational adoption | No evidence from this MVP | Explicit portfolio gaps |

No separate Forward Deployed Engineer posting was supplied or verified. Describe potential transfer to that work without claiming a validated match to a specific opening.

## Reviewer experience and demonstration

The README opens with the problem, a screenshot of a real report, and a short video. Provide quickstart instructions, expected outputs, limitations, and a link to the tests. A reviewer should be able to inspect the core evidence without installing Bonsai.

| Video time | Action | Evidence |
| --- | --- | --- |
| 0–15 seconds | Inspect BEAM-014 and the baseline PO | Original length, material, linked order |
| 15–40 seconds | Change beam length and material in Bonsai; save revised IFC | Actual authored revision |
| 40–60 seconds | Import/compare revisions in the auditor | One modified member; correct quantity deltas |
| 60–80 seconds | Select procurement discrepancy | Highlighted beam, baseline/revised values, BOM/PO lineage, rule |
| 80–90 seconds | Show unchanged-model control and report download | No false alert in the control; inspectable exported evidence |

Editing the recording for time is fine; disclose precomputed runs. A fixture-driven audit must be shown as a fixture-driven audit, not as a live edit.

## Pilot scorecard

The program hypothesis is that a role-specific, reproducible engineering artifact can be built economically and make relevant capability easier for a reviewer to evaluate. A single job response cannot establish causality.

| Measure | Target | Current result |
| --- | --- | --- |
| Correctness | All required acceptance cases pass | 29 Python tests and two browser tests pass; independent owner review pending |
| Evidence completeness | Every discrepancy links source, revision, rule, BOM and PO where applicable | Fixture and actual Bonsai-export reports retain lineage; saved/downloaded source bytes match |
| Full demonstration | 90-second edit → audit → procurement walkthrough | 87-second agent-assisted Bonsai authoring and browser audit recorded; owner acceptance pending |
| Reproduction | One fresh-directory run succeeds after documented prerequisites | Fresh-directory application run verified November 9; isolated Bonsai authoring captured November 10 |
| Effort | At most 20 active hours across two calendar days | Not measured |
| Runtime | Record ingest/diff times, element count, file size, hardware | One 16-member fixture comparison measured at approximately 0.044 seconds; no scalability benchmark |
| Development cost | Log actual paid tool/API usage; no paid runtime API required by design | Not measured |
| Reviewer comprehension | If a reviewer is available, they identify what changed, why it matters, and where evidence lives within two minutes | Not evaluated |
| Hiring signal | Track application date, project-linked replies, interviews, and technical feedback over 30 days after submission | No application submitted |
| Reuse | Identify reusable modules and later measure effort on pilot 002 | Not established |

Advance to a second pilot if the core workflow is correct, reproducible, and explainable within budget. If setup dominates, improve the template first. If the engine works but the full demonstration misses its gate, record a partial result and the actual remaining effort. Preserve negative findings.

## Publication package and claims

Prepare a repository, 90-second video, one-page case study, architecture diagram, fixture manifest, example audit, test evidence, and limitations. Keep measurements in a small `pilot-results.json` or Markdown table for comparison across later projects.

After successful implementation, adapt this resume bullet using actual measurements:

> Built an IFC revision auditor in Python and TypeScript that traces geometry and material changes through synthetic BOM and purchase-order records, with [N] passing regression cases and a reproducible local demonstration.

Do not claim time saved, prevented procurement costs, real factory readiness, operator adoption, or production scalability without independent evidence. Keep the completed-project description narrower than the supported implementation.


Implementation update: a working local pilot now exists. See the [measured validation results](../pilots/fluidstack-change-auditor/docs/validation.md). November 10 update: the [Bonsai authoring round trip](../pilots/fluidstack-change-auditor/docs/bonsai-validation.md) is verified with agent assistance and an 87-second recording. Independent owner review remains pending; planned outcomes above should not be read as achieved claims.
