---
name: fusion-existing-assemblies
description: "Inspect and edit existing nested Autodesk Fusion assemblies, repeated component definitions, and component model parameters. Use when changes must target the correct instance or preserve unrelated components."
---

# Existing assemblies

Package baseline: 0.2.0. Scope: **Typed workflow**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

Resolve the active document with `fusion_documents`, `fusion_activate_document` if needed, and `fusion_inspect`. Call `fusion_assembly_tree` and follow `next_offset` until the relevant branches are covered. Choose the exact occurrence path, such as `Module:1+Pin:1`; names alone are ambiguous.

Call `fusion_component_context(document_id, occurrence_path)`. Read the component token, fingerprint, all paths sharing the definition, external-reference status, model parameters and originating features. Native geometry is in component coordinates; proxy geometry is in assembly context. Use the context appropriate to the requested measurement or feature.

For existing parameter edits, use `fusion_edit_component_parameters` with the exact path, fresh `expected_component`, fresh `expected_fingerprint`, inspected parameter names, and unit-bearing expressions. Read [the argument example](references/parameter-edit.md) when composing the call. Set `allow_shared_definition_edit` only if changing every reported instance matches the user's intent. If the request is to change one instance only, explain the missing make-independent capability instead of modifying the shared definition.

External linked definitions are rejected by typed edits. Do not silently break links, copy components, or edit source documents. A fingerprint is a partial stale-state check, not a complete revision proof. Rediscover after a restart, archive import, or conflicting change.

Reinspect the component, check the edited dimensions and feature health, and examine affected shared instances and relevant downstream dependencies. Compare an unrelated component against its pre-edit state when preservation is part of the request. Report intended changes, observed results, and unresolved diagnostics separately.

For assembly creation, `fusion_assembly` supports component creation, instancing, and as-built joints. Rigid joints are live-tested; revolute/slider paths remain experimental and require an origin token and explicit motion verification. Do not equate moving an occurrence with defining a kinematic joint.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
