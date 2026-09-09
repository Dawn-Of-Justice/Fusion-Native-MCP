# Packaged Fusion skills

These ten skills accompany Fusion Native MCP 0.2.0. They are instructions for an assistant, not additional MCP tools or proof of automation support. Product-area grouping was reviewed against the [Autodesk help home](https://help.autodesk.com/view/fusion360/ENU/) and [workspace tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) on September 10, 2026.

## Catalog

| Skill | Product area | Package support |
| --- | --- | --- |
| [fusion-documents](../skills/fusion-documents/SKILL.md) | Documents and exports | Typed workflow |
| [fusion-mechanical-modeling](../skills/fusion-mechanical-modeling/SKILL.md) | Sketches and solid parts | Typed workflow |
| [fusion-existing-assemblies](../skills/fusion-existing-assemblies/SKILL.md) | Existing assemblies | Typed workflow |
| [fusion-manufacturing](../skills/fusion-manufacturing/SKILL.md) | Manufacturing and CAM | Typed face workflow; experimental NC |
| [fusion-drawings](../skills/fusion-drawings/SKILL.md) | Engineering drawings | Experimental creation |
| [fusion-advanced-geometry](../skills/fusion-advanced-geometry/SKILL.md) | Surface, form, sheet metal and mesh | Discovery and API-assisted planning |
| [fusion-render-animation](../skills/fusion-render-animation/SKILL.md) | Render and animation | Discovery and API-assisted planning |
| [fusion-simulation-generative](../skills/fusion-simulation-generative/SKILL.md) | Simulation and generative design | Discovery and study planning |
| [fusion-electronics](../skills/fusion-electronics/SKILL.md) | Electronics and PCB integration | Discovery and inspection planning |
| [fusion-api-recovery](../skills/fusion-api-recovery/SKILL.md) | Custom API and operation recovery | Tracked execution and recovery |

## Coverage decisions

Sketch and Solid share a modeling skill; Render and Animation share a presentation skill; Simulation and Generative Design share study planning. Surface, Form and Sheet Metal are covered by advanced geometry, with Mesh included as a related representation workflow. Assemblies and Manufacture have dedicated skills because component identity and asynchronous CAM jobs require distinct handling.

Projects/hubs are covered only to the extent needed for document selection and output scope. Fusion Manage administration, change orders, user invitations, extensions and account billing are not automated by this package. Drawing, NC and moving-joint paths remain experimental. Discovery skills must report a missing API rather than claim execution or create a dummy deliverable.

## Use and distribution

See the [installation guide](installation.md#5-install-the-optional-skills) for a PowerShell installation example and the [cheat sheet](cheatsheet.md) for prompts and tool sequences.

Each folder in `skills/` is self-contained; copy the complete folder, including any `references/`, into the skill directory supported by your assistant. Register the MCP server separately using the repository setup instructions. Copying skill files does not start Fusion or install an MCP connection. Clients without skill discovery can load the relevant SKILL.md as workflow instructions.

For a Codex installation, skill folders can be placed in `$CODEX_HOME/skills` (normally `~/.codex/skills`). This repository does not change your global skill installation. Select folders deliberately and review any existing names before replacing them. Keep installed copies synchronized when updating this package.

Example requests:

- `$fusion-existing-assemblies`: Inspect the nested assembly and change the pin length in every instance of the selected definition to 30 mm; verify the unrelated bracket stays unchanged.
- `$fusion-mechanical-modeling`: Create a new dimensioned mounting plate with the supplied dimensions and verify its thickness and feature health.
- `$fusion-manufacturing`: Inspect the current milling setup and generate the selected face operation using the specified tool; report toolpath validity.
- `$fusion-simulation-generative`: Prepare the study inputs and determine which installed APIs can automate the setup; do not submit a solve.

Skills are included in source distributions under this project's MIT license. The Python wheel contains the MCP server; skills are distributed through the source checkout/archive. No extra Python runtime dependency is required by the skills.

## Maintenance and review

Update the relevant skill when schemas or validated behavior change. Keep descriptions selective and distinguish typed, experimental and discovery workflows. Validate frontmatter with the skill-creator validator when available. Review these scenarios before expanding claims:

| Scenario | Expected decision |
| --- | --- |
| Change only one occurrence of a shared definition | Identify all affected instances; do not set the shared-edit flag or invent make-independent support |
| Fusion restarts while CAM generation is pending | Rediscover current state; do not replay a mutation because the old job ID is unknown |
| Create a drawing from an unsaved design | Identify the saved-design prerequisite and missing destination/workflow |
| Ask for PCB routing or a solver run | Discover actual callable capability; do not invent typed tools or fabricate success |
| Export a flat pattern | Do not substitute sketch DXF for sheet-metal unfolding |
| Request a render | Distinguish a viewport screenshot from a completed render |

These are review cases, not live acceptance-test results. No new Fusion capability is live-validated by adding instruction files.
