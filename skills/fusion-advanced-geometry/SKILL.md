---
name: fusion-advanced-geometry
description: "Assess and plan Autodesk Fusion surface, T-Spline form, sheet-metal, and mesh workflows. Use installed API discovery for these areas, which do not yet have dedicated typed tools in this package."
---

# Surface, form, sheet metal and mesh

Package baseline: 0.2.0. Scope: **Discovery and API-assisted planning**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Determine whether the input is a solid BRep, surface body, mesh, T-Spline form, or sheet-metal component before proposing conversion or edits. Inspect the document and scoped entities. Current typed mechanical tools do not establish dedicated support for these representations.

For surfaces, identify the target boundaries, open edges and desired continuity; verify closure before claiming a solid. For form work, preserve the intended editable representation and inspect conversion capability before generating BRep geometry. For mesh work, inspect scale, units and connectivity; do not call an STL export a repaired or editable parametric model.

For sheet metal, establish material thickness, sheet-metal rule, bend requirements, and desired folded/flat deliverable. A thin extruded solid is not evidence of a sheet-metal component. The existing sketch DXF export does not implement flat-pattern generation.

Use `fusion_api_docs` to locate the exact installed classes/members needed for the requested representation, and use read-only Python probes if appropriate. No dedicated surface/form/sheet-metal/mesh tools are advertised by this package. A UI command or online tutorial alone does not prove API availability. Implement a bounded custom operation only after verifying the needed API and its inputs; otherwise return a concrete manual workflow or implementation gap.

Verify the resulting representation and geometric properties against the intended deliverable. Do not automatically convert, flatten, repair, or discard history merely to fit the current typed tools.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
