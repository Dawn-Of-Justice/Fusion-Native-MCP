---
name: fusion-simulation-generative
description: "Prepare Autodesk Fusion simulation or generative-design study requirements and assess installed automation capability. Use for analysis setup and result interpretation planning; this package has no dedicated study or solver tools."
---

# Simulation and generative design

Package baseline: 0.2.0. Scope: **Discovery and study planning**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Separate structural/thermal study requests from CAM simulation and assembly animation. Inspect the intended component bodies, shared placements, geometry and units. Establish the physical question, materials, loads, constraints, contacts and acceptance quantities before proposing a solver run. Do not infer physical material from display appearance.

For simulation, document load cases and boundary-condition assumptions, inspect rigid-body freedom and contact intent, and plan mesh/result convergence checks. For generative design, distinguish preserved geometry, obstacle geometry, design space, load cases, objectives and manufacturing constraints. Missing physical inputs can change the answer; request only those necessary for the study.

This package has no typed study creation, solver submission or result-reading tools. Use `fusion_api_docs` and the installed capability surface to determine whether a requested operation is exposed. Do not manufacture API methods from UI names. Entitlement and cloud execution requirements must be checked for the chosen workflow; do not launch a paid/cloud study merely to probe availability.

Provide a study plan or a verified, bounded API operation according to actual capability and the user's scope. Solver submission or a displayed contour is not validated engineering evidence. If results can be read, report units, load case, extrema, convergence evidence and modeling assumptions. Clearly separate observed results from expectations and unavailable checks.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
