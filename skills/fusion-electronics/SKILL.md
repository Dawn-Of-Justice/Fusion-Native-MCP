---
name: fusion-electronics
description: "Assess Fusion electronics schematics, PCB layouts, and mechanical-electrical integration using discovered native capabilities. Use for electronics workflows; the package currently has no dedicated PCB editing tools."
---

# Electronics and PCB integration

Package baseline: 0.2.0. Scope: **Discovery and inspection planning**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Determine whether the request concerns a schematic, board layout, library part, 3D PCB, or mechanical enclosure. Identify the intended electronics document and its relationship to the mechanical assembly; mechanical body inspection alone cannot prove net connectivity or board-rule compliance.

Call `fusion_capabilities` to inspect native schemas. The returned native tool names are discovery data, not automatically callable wrapper tools. This package does not expose a dedicated electronics read/write wrapper. Do not invoke an invented MCP tool or assume every electronics operation is available through `adsk.fusion`.

Use `fusion_api_docs` for an installed API path when applicable, or an actually available native connector according to its schema and authorization. Otherwise prepare a concrete electronics workflow and name the missing connector/API capability. Do not use arbitrary Python execution to assume an unsupported PCB API exists.

For ECAD/MCAD integration, verify board origin, outline, thickness, mounting holes and component envelope against the intended mechanical coordinate system. Changes to a generated 3D representation are not proof the schematic or board source was updated. For routing/library edits, preserve reference designators, package/pin mappings and net intent; report ERC/DRC only when an actual checker was run and results read.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
