---
name: fusion-documents
description: "Inspect, select, reopen, and export Autodesk Fusion documents through Fusion Native MCP. Use for document targeting and deliverables; not hub administration or PLM release actions."
---

# Documents and exports

Package baseline: 0.2.0. Scope: **Typed workflow**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Use `fusion_documents` and `fusion_inspect` to identify the active design. Match identity and context, not only a display name. `fusion_activate_document` requires both current and target creation IDs plus an operation ID; duplicate IDs are rejected. Activation does not save or close other documents.

For a new design, pass the active ID to `fusion_new_design.expected_document_id`; use `__NO_DOCUMENT__` only when there is no active document. For local archives, `fusion_open_archive` takes an existing absolute F3D/F3Z path and opens a new document. Reinspect after either action; do not reuse old geometry tokens after reopening or restarting Fusion.

For `fusion_export`, choose the requested format and an absolute destination with a matching extension. STEP, F3D, sketch DXF, and BOM JSON have tested paths; STL remains unvalidated. DXF requires the selected sketch token. Confirm target ownership and scope before export; a sketch DXF is not a sheet-metal flat pattern or an engineering drawing. Verify the resulting file exists and has the intended contents where tooling permits.

Saving a cloud design, changing a hub, inviting collaborators, or releasing a PLM item is a separate action without a dedicated tool in this package. Discover installed APIs if the user requests it; do not infer authorization from a request to open or export a model.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
