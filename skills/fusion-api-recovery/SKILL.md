---
name: fusion-api-recovery
description: "Write bounded custom Fusion Python operations and reconcile interrupted Fusion Native MCP writes. Use when typed tools cannot express a requested operation or a journal operation is started or uncertain."
---

# Custom API and operation recovery

Package baseline: 0.2.0. Scope: **Tracked execution and recovery**. Skills guide tool use; they do not add server capabilities.

## Execution contract

Requires this package's connected stdio MCP server and an open Fusion installation with native MCP enabled. Use client tool discovery for current argument schemas; displayed tool names may carry a client-specific prefix. Inspect document identity before edits and reuse fresh entity references. Every mutation needs its operation ID and document guard. If execution becomes uncertain, inspect the journal and Fusion before any new write; acknowledgement records recovery and does not undo or cancel. Server-side checks remain authoritative.

## Workflow

For a custom operation, inspect document identity and search `fusion_api_docs` for the exact installed classes and members. Prefer an existing typed tool when it expresses the task. Discovery of a native tool schema does not make that tool a callable wrapper method.

Submit `fusion_execute_python` with one synchronous `run(context)` function. Use `read_only=true` for probes that do not modify designs. Imports and code execute with Fusion's local privileges; read-only is not a filesystem sandbox. For edits, supply the current `expected_document_id` and a unique operation ID. Do not switch to a different document inside a guarded script to bypass target checks. Use explicit units and bounded, inspectable output.

The bridge splits long source literals and requires a completion marker. Do not fabricate or print the bridge's marker to mask missing execution, swallow relevant exceptions, or equate a returned success with verified geometry. Verify target state through a separate inspection.

For `started` or `uncertain`, retrieve `fusion_operation_status`, inspect Fusion and determine whether execution is still running. A timeout or cancelled client call does not prove cancellation. Do not issue the same mutation under a new ID, delete the journal, or automatically acknowledge to unblock progress.

Once execution is finished, establish what actually changed and recover partial effects within the user's scope. Use `fusion_acknowledge_operation` with a concrete resolution describing the inspected result; it neither cancels nor undoes work. If the actual state cannot be established, keep mutations blocked and explain the missing evidence. Reusing an identical operation ID/request retrieves its existing record; it is not a way to resume partial code.

Clients sharing one absolute journal directory share write claims. Separate journals, unrelated native clients and manual edits are outside that coordination. A definition fingerprint is also not a complete document revision lock.

## Source

Consult the relevant collection in the [Autodesk Fusion tutorial index](https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-TUTORIALS.htm) for product workflows. For execution, installed API documentation and actual MCP schemas take precedence over UI examples.
