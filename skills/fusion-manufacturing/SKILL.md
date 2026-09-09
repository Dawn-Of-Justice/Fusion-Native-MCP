---
name: fusion-manufacturing
description: "Prepare milling setups, select tools, generate and inspect CAM toolpaths through Fusion Native MCP. Use for manufacturing/CAM and explicitly requested experimental NC output; not structural simulation."
---

# Manufacturing and CAM

Package baseline: 0.2.0. Scope: **Typed face workflow; experimental NC**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Inspect the target document, selected model bodies, and `fusion_cam_inventory`. Discover tool/post libraries with `fusion_cam_browse_library`; inspect tools with `fusion_cam_tools`. Use the selected tool's library URL, index, and fresh fingerprint. Do not choose a tool or post by index alone or guess feeds/speeds that determine machining behavior.

`fusion_cam_create_setup` creates a milling setup with relative-box side/top stock and a box-point WCS origin. It does not automatically configure machines, fixtures, or arbitrary axis orientation. Inspect setup parameters and resulting orientation against the user's intended stock and setup. Ask for missing machine/material/cutting inputs only when they are needed to produce the requested result.

Use `fusion_cam_parameters` to discover installed parameter names and expressions. `fusion_cam_create_operation` requires an explicit strategy and tool. The face workflow is live-tested; accepting a strategy string does not prove support for its required geometry selections. Do not call unsupported adaptive or multi-axis workflows validated merely because operation creation succeeds.

Start generation once with `fusion_cam_generate`, then poll the returned job through `fusion_cam_job`. A timeout is not cancellation. After a Fusion restart, job IDs can become unknown: inspect CAM inventory and journal state instead of resubmitting blindly. Verify completion, toolpath validity, errors, and affected operations independently.

NC creation/post-processing are implemented but not live-validated. When NC output is requested, inspect the chosen post and operations, use an explicit absolute empty output folder and valid filename, create the NC program, then post-process it and inspect output files. Generating a toolpath does not by itself authorize producing or running machine code. Preserve existing authorization; do not ask again for an already specified output action.

No CAM simulation or machine collision-verification tool is implemented. Report that gap when relevant to output acceptance; do not describe generated code as machine-verified. Additive, turning, nesting, and advanced machining require installed capability discovery before offering execution.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
