# Fusion Native MCP cheat sheet

Keep Fusion open with native MCP enabled and connect your assistant to this package. Need setup? See [installation](installation.md). Prefer natural-language requests; the assistant can discover tool argument schemas.

## Copy-and-use prompts

| Task | Prompt |
| --- | --- |
| Check connection | “Use Fusion Native MCP to list open documents and inspect the active design without modifying it.” |
| Inspect an assembly | “Show the nested component tree, repeated definitions, linked components, and unhealthy features in the active assembly.” |
| Identify an edit target | “Inspect the pin in Module:1. Show its exact occurrence path, editable dimensions, and every instance that shares its definition.” |
| Edit every shared instance | “Change the selected pin definition to 30 mm long in all its instances. Verify both the new length and that the unrelated bracket stays unchanged.” |
| Request a single-instance edit | “I want only this occurrence changed. First check whether it shares a definition; do not change the shared definition.” |
| Create a part | “Create a separate design with an 80 × 50 × 8 mm rectangular plate. Use dimensioned geometry and verify its dimensions and feature health.” |
| Check interference | “Check interference between the selected shaft and housing, identifying the exact components and affected bodies.” |
| Export | “Export the inspected component as STEP to my specified absolute file path, and verify the resulting file.” |
| Inspect CAM | “List current setups, tools, operations, and toolpath validity without changing anything.” |
| Generate toolpaths | “Generate the selected face operation using its inspected setup and tool. Poll completion and report errors and validity.” |
| Recover after interruption | “Inspect the interrupted operation and the current Fusion state. Tell me what completed before attempting any further edit.” |

Occurrence paths and dimensions above are examples: use the actual design's inspected targets. Supply output paths and machine/tool inputs when the task requires them.

## Skills at a glance

In clients supporting explicit skill invocation, prefix a request with the skill name, for example `$fusion-existing-assemblies`. Ordinary task wording can also select an applicable skill.

| Skill | Use it for |
| --- | --- |
| `$fusion-documents` | Select/open documents and export deliverables |
| `$fusion-mechanical-modeling` | Dimensioned sketches, solid parts, feature additions |
| `$fusion-existing-assemblies` | Nested components, shared definitions, scoped parameter edits |
| `$fusion-manufacturing` | Milling setup, tool selection, toolpath jobs, requested experimental NC output |
| `$fusion-drawings` | Drawing requirements and experimental automatic drawing creation |
| `$fusion-advanced-geometry` | Assess surface, form, sheet-metal and mesh automation capability |
| `$fusion-render-animation` | Plan rendering/animation and discover installed APIs |
| `$fusion-simulation-generative` | Prepare study requirements and discover automation capability |
| `$fusion-electronics` | Assess schematic/PCB and ECAD/MCAD integration capabilities |
| `$fusion-api-recovery` | Custom Python operations and uncertain-write recovery |

Advanced geometry, rendering/animation, simulation/generative design, and electronics require capability discovery and do not have dedicated creation tools in the package. Skills are not additional Fusion features. See [support boundaries](skills.md).

## Tool sequences

| Workflow | Typical calls |
| --- | --- |
| Connect and identify | `fusion_capabilities` → `fusion_documents` → `fusion_inspect` |
| Select another open document | `fusion_documents` → `fusion_activate_document` → `fusion_inspect` |
| Edit an existing component | `fusion_assembly_tree` → `fusion_component_context` → `fusion_edit_component_parameters` → reinspection and validation |
| Build a part | `fusion_new_design` if requested → `fusion_set_parameter` → `fusion_create_sketch` → `fusion_query_entities` → `fusion_create_feature` → `fusion_validate_design` |
| Prepare CAM | `fusion_cam_inventory` → `fusion_cam_browse_library` → `fusion_cam_tools` → `fusion_cam_create_setup` → `fusion_cam_create_operation` |
| Generate CAM | `fusion_cam_generate` once → `fusion_cam_job` until complete → `fusion_cam_inventory` |
| Export | Inspect target → `fusion_export` → verify file |
| Reconcile interruption | `fusion_operation_status` → inspect actual effects and confirm execution finished → recover if needed → `fusion_acknowledge_operation` |

These are workflow outlines, not fixed scripts. Discover the current schema and reuse suitable existing features/setups. The [complete tool reference](tools.md) lists all 39 tools.

## IDs, units, and component scope

- **Document ID:** Current Fusion creation ID from inspection; use it for the document guard. Names can repeat.
- **Occurrence path:** Exact nested placement, such as `Module:1+Pin:1`. A component definition can appear at multiple paths.
- **Entity token:** Fresh reference returned by inspection/query, not a guessed index. Rediscover after reopening, restarting, or relevant geometry changes.
- **Component fingerprint:** Fresh definition-state fingerprint from context; it detects some stale edits, not every possible document change.
- **Operation ID:** Unique for each intended mutation. Reuse with the identical request retrieves its journal record; a new ID must not be used to blindly retry uncertain work.
- **Units:** Prefer expressions such as `30 mm` and `90 deg`. Numeric Fusion API lengths use centimeters; typed dimension/volume checks use mm/mm³.

Changing a shared definition changes every instance. `allow_shared_definition_edit=true` means that result is intended. Single-instance independence and automatic linked-source editing are not implemented.

## Status and recovery

| Result | Meaning and next step |
| --- | --- |
| `succeeded` | Execution returned successfully; independently verify geometry or CAM output |
| `started` | Execution was claimed and may still be running or interrupted; inspect before new writes |
| `uncertain` | Effects are unverified; do not retry or acknowledge automatically |
| CAM job running | Poll its existing job ID; do not start generation again |
| Stale target / wrong document | Rediscover identity and state; resolve ambiguity before editing |

Acknowledgement is not rollback. Keep the journal and verify Fusion has finished before recording recovery. Custom Python runs with Fusion's local privileges; read-only is a design guard, not a filesystem sandbox.

## What is ready, experimental, or missing?

| Status | Coverage |
| --- | --- |
| Live-tested fixtures | Core solid features, nested shared-parameter edits, rigid joint, geometry checks, STEP/F3D/sketch DXF, BOM, interference, face CAM generation |
| Implemented, not live-validated | STL export, revolute/slider joints, automatic cloud drawings, NC program creation and post-processing |
| No dedicated execution coverage | Surface/form/sheet-metal/mesh workflows, render/animation, simulation/generative studies, PCB editing |
| Not implemented | Make-one-instance-independent, automatic linked-source editing, CAM simulation, arbitrary topology repair |

A screenshot is not a render or engineering drawing. Sketch DXF is not a sheet-metal flat pattern. Valid toolpath generation is not machining/collision certification. See [validation](validation.md) and [roadmap](../ROADMAP.md).

## Useful local commands

Run from the checkout root in PowerShell:

```powershell
# Initial setup (regenerates local mcp-config.json)
./setup.ps1

# Offline tests; does not connect to Fusion
./.venv/Scripts/python.exe -m pytest tests -q

# Refresh dependencies after a source update
./.venv/Scripts/python.exe -m pip install ".[test]"
```

Use the [installation troubleshooting table](installation.md#troubleshooting) for connection problems and [existing-assembly guide](existing-models.md) for the guarded edit argument example.
