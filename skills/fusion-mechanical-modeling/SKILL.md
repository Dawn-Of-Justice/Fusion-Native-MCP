---
name: fusion-mechanical-modeling
description: "Create dimensioned sketches and solid mechanical parts in Autodesk Fusion using typed MCP tools. Use for part creation and feature additions; prefer the assembly skill for edits to existing shared definitions."
---

# Sketches and solid parts

Package baseline: 0.2.0. Scope: **Typed workflow**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Translate requirements into dimensions, units, target component, and intended feature operations. Use `fusion_inspect` and `fusion_model_overview` to inspect an existing design; for a new part, create a separate design only when consistent with the request. Distinguish adding a body from creating an independently placed component.

Use `fusion_set_parameter` for design-wide user parameters. `fusion_create_sketch` supports origin-based rectangles and circles on component XY/XZ/YZ planes with an offset. Its `width` is the circle diameter, not radius. It requires full constraint. Do not claim support for arbitrary sketch shapes through this schema; use installed API documentation for an explicitly needed custom script.

Discover profiles, points, faces, and edges through `fusion_query_entities` with a sketch/body scope. Select by geometry and ownership, never a guessed list index. `fusion_create_feature` supports extrude, revolve, loft, sweep, fillet, chamfer, shell, combine, and rectangular/circular patterns. A sweep needs a path token; loft/combine need multiple ordered entities; combine needs join/cut/intersect. `fusion_create_holes` needs sketch-point tokens. Inspect the current MCP schema before constructing arguments.

Supply the intended component token instead of accepting `root` by accident. When it belongs to a repeated or linked assembly, inspect shared paths and ownership first. A definition edit affects all instances; making one instance independent is not implemented. Do not substitute a design-wide parameter edit for a scoped model-parameter edit.

Use unit-bearing expressions, such as `8 mm`. Fusion API numeric lengths use centimeters; typed measurement checks use millimeters and cubic millimeters. Verify dimensions or volume independently with `fusion_validate_design`, inspect feature/sketch health, and use `fusion_check_interference` where fit matters. A screenshot supports presentation but is not dimensional verification.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
