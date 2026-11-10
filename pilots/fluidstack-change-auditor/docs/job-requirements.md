# Role-to-evidence mapping

Target: [Fluidstack Software Engineer, Manufacturing & Supply Chain](https://fluidstack.com/jobs/1f191895-fcfd-4cfb-8d4f-2cc3904e3cf2), reviewed November 9, 2026. These mappings are interpretations, not claims about Fluidstack's internal stack.

| Relevant area | Implemented evidence | Boundary |
| --- | --- | --- |
| Python/TypeScript delivery | Engine, API, browser interface, tests | Local pilot |
| BOM/procurement consistency | BEAM-014 → BOM-BEAM-014 → PO-1042/1 | Synthetic records |
| Engineering change traceability | Source hashes, identifiers, before/after values, versioned rules | Bounded IFC4 support |
| Operator-oriented workflows | Select, inspect, reconcile, export | No operator evaluation/adoption |
| Autonomous delivery | Reproducible workflow and regression suite | Effort not independently measured |
| AI-assisted development | Agent implementation, test evidence, runtime debugging | Not deployed LLM/MCP experience |
| Real document extraction | Not demonstrated | Explicit gap |

IFC is our chosen open format; the posting does not establish it as a production requirement. No separate Forward Deployed Engineer posting was verified.

Portfolio description:

> Built a local IFC revision auditor in Python and TypeScript that traces supported geometry and material changes through synthetic BOM and purchase-order records, with source-linked evidence, negative controls, and a reproducible demonstration.

Use measured validation results alongside that description. Do not claim procurement savings, avoided production failures, factory adoption, or general CAD support.
