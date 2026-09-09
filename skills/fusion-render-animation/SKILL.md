---
name: fusion-render-animation
description: "Plan and inspect Autodesk Fusion rendering and assembly-animation workflows, discovering installed APIs where execution is requested. Use for presentation images or exploded animations, not engineering drawings or kinematic validation."
---

# Render and animation

Package baseline: 0.2.0. Scope: **Discovery and API-assisted planning**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Distinguish a viewport capture, photorealistic render, exploded animation, and physical motion study. `fusion_screenshot` captures the current viewport; it does not render a scene or generate video. This package has no dedicated render or animation creation tools.

For rendering, inspect the intended visible components and establish camera, appearance, environment, output dimensions and destination as needed. Appearance is not engineering material assignment. Search installed API documentation for the required rendering and camera members before constructing a custom script.

For animation, identify exact occurrence paths, baseline placements, explosion sequence and output intent. Storyboard transforms should not be replaced with permanent assembly placement edits. Discover whether the installed API supports the required storyboard and publishing operation; a workspace's presence is not sufficient evidence.

Use available read-only inspection to prepare the scene or storyboard plan. Execute only a verified API path within the request's scope and validate resulting files. A queued cloud render is not a completed image. Publishing or sharing externally is a distinct action from preparing a local presentation; retain the user's chosen output scope.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
