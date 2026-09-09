# Architecture and execution contract


```text
MCP client
  └─ stdio → this Python server (official MCP SDK)
       ├─ inspect / API docs / viewport / document list
       ├─ document guard + operation journal
       └─ local HTTP → Autodesk native MCP → Fusion Python API
```

No custom Fusion add-in is required. Fusion must remain open with its native MCP enabled. The adapter currently supports the native endpoint's JSON responses to Streamable HTTP requests; it deliberately reports an error if a future Fusion version responds using SSE instead.

## Execution contract

1. Inspect the active document. `data.document.id` is its Fusion creation ID.
2. Read the installed API docs for the operation you intend to implement.
3. Submit a Python script defining exactly one synchronous `run(context)` function. Imports are allowed. Do not suppress exceptions that indicate failure.
4. For edits, provide `expected_document_id` and a unique `operation_id` (UUID recommended). The document check runs inside Fusion before any user script code, including top-level imports. Multiple open copies with the same creation ID are rejected.
5. Independently inspect geometry/feature state or CAM results after execution. `succeeded` only means the script returned without a reported failure.

For read-only scripts set `read_only=true`. Fusion enforces a design modification guard, including during active command dialogs. This is **not a Python sandbox**: scripts execute with Fusion's local Python privileges and can access files and other system resources. Use a trusted MCP client and trusted code. The creation-ID check validates the initial target; arbitrary script code can deliberately switch documents after it passes.

Use explicit unit expressions such as `"8 mm"` for `ValueInput`. Numeric Fusion geometry coordinates use internal units (centimeters for lengths); convert units explicitly. See [examples](../examples/) for complete scripts.

## Failures, concurrency and recovery

- A mutation is recorded before sending it to Fusion. SQLite claims prevent overlapping writes from server instances sharing the same journal.
- The same ID and identical request returns its existing record; different code under that ID is rejected.
- A timeout, disconnect, native error, or partial script failure is conservatively recorded as `uncertain`. No automatic retry or rollback occurs.
- An interrupted process leaves `started` in the journal. Both `started` and `uncertain` block subsequent new writes.
- Inspect Fusion, wait for any pending execution to finish, and recover partial changes if necessary. Then call `fusion_acknowledge_operation` with a concrete account of the verified result. Acknowledgement does not undo or cancel anything.
- Use a **new** operation ID only when a new execution is intended. Keep the journal; deleting it removes duplicate protection.
- Reads and writes are serialized within a server instance. Status calls in that instance may wait behind an active request. Separate journal instances, other native clients, and interactive user edits are outside this lock.
- The initial document identity guard is not a document revision check. Users should avoid simultaneous manual edits during scripts. Cancelling an MCP request does not guarantee cancellation inside Fusion.
- The specialized existing-component edit adds a definition-state fingerprint check. It covers inspected parameters, body bounds/volume/topology counts and sketch summaries; it is not a complete document revision or topology identity system. Read fresh context after edits and restarts.
- A lost native session is surfaced as an error; a later call can initialize a new session. An uncertain write remains blocked until reconciled.
