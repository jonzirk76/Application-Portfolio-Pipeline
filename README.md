# Application Portfolio Pipeline — pilot planning pack

Prepared November 9, 2026. Status: **working local pilot; manual Bonsai authoring gate outstanding**.

Pilot: **OpenBIM Engineering Change Auditor**, an independent portfolio project targeted at Fluidstack's Software Engineer, Manufacturing & Supply Chain role.

- [Workplan and prompt analysis](docs/pilot-workplan.md): scope, architecture, two-day schedule, acceptance criteria, and execution brief.
- [Portfolio profile](docs/portfolio-profile.md): positioning, role alignment, demonstration, evidence, and experiment metrics.
- [Installation commands](docs/setup.md): Ubuntu setup, Python and browser dependencies, Bonsai installation, and validation.
- [Commit policy](docs/commit-policy.md): concise subsystem subjects and dependency-ordered changes for agent navigation.

The [implemented pilot](pilots/fluidstack-change-auditor/README.md) follows one beam revision from IFC geometry through synthetic BOM and procurement evidence. See its [validation record](pilots/fluidstack-change-auditor/docs/validation.md) for measured results and outstanding scope.

```bash
cd pilots/fluidstack-change-auditor
make demo
```

Open http://127.0.0.1:8000. The original planning documents describe intended scope; the pilot validation record describes achieved results.
