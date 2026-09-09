---
name: fusion-drawings
description: "Prepare engineering drawing requests and use the experimental automatic drawing tool in Autodesk Fusion. Use for sheets, drawing standards, views and dimensions; not viewport rendering."
---

# Engineering drawings

Package baseline: 0.2.0. Scope: **Experimental creation**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Identify the intended saved design and whether the request targets a part or assembly. Establish sheet standard, units, sheet size, and necessary views or annotations from the request. Do not infer tolerances or GD&T from nominal geometry.

Inspect `fusion_create_drawing` and the installed Drawing API with `fusion_api_docs`. The current tool creates an automatic cloud drawing from an already saved design; it is not a general drawing editor. Its schema supports ISO/ASME standards, compatible sheet sizes, millimeter/inch units, and automatic dimensions. It has not been live-validated. Saving an unsaved design to a cloud project needs an explicit destination and a supported separate workflow.

If the requested drawing fits the tool, execute within the user's authorized scope and inspect the returned state. Cloud job submission is not completed drawing output. Discover the installed job/result API before polling; do not invent a drawing-status MCP tool.

Check actual sheets, views, scale, dimensions, and assembly annotation against the request using available read/API capabilities. List anything that cannot be inspected or generated. Do not substitute `fusion_screenshot` or sketch DXF for an associative drawing, and do not claim PDF export exists in `fusion_export`.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
