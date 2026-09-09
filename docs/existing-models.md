# Editing an existing assembly

The key distinction is **component definition versus occurrence**. A definition holds geometry and model parameters. An occurrence places that definition in an assembly. Editing a definition changes every occurrence of it, including instances reached through repeated parent subassemblies.

## Select the document and occurrence

Call `fusion_documents`, then `fusion_activate_document` if necessary. Use `fusion_inspect` to obtain the active document's creation ID. Do not reuse IDs or geometry assumptions without rediscovery after a Fusion restart or archive import.

Call `fusion_assembly_tree(document_id)` and paginate using `next_offset`. Choose an exact path such as `Module:1+Pin:1`. Names alone are not sufficient: another subassembly can have its own `Pin:1`.

`fusion_component_context(document_id, occurrence_path)` returns:

- The component and occurrence references.
- Every occurrence path that shares this definition.
- Whether the occurrence is inside an external reference.
- Model parameters with expressions, units, roles and originating features.
- Native bodies in the component's coordinates and proxy bodies in the occurrence's assembly context.
- A fingerprint of the current definition state.

Fusion cannot produce usable tokens for some nested native occurrences. The server converts those to a root-context proxy before returning a reference. Geometry queries scoped to an occurrence return its body proxies; component-scoped queries return native geometry.

## Edit a parameter in that component

Use the actual parameter name and role returned by inspection. For example, an extrusion's `AlongDistance` parameter may be named `d9`; that name must not be guessed.

```json
{
  "document_id": "<current document ID>",
  "operation_id": "<new UUID>",
  "spec": {
    "path": "Module:1+Pin:1",
    "expected_component": "<fresh component token>",
    "expected_fingerprint": "<fresh 64-character fingerprint>",
    "expressions": {"<inspected parameter name>": "30 mm"},
    "allow_shared_definition_edit": true
  }
}
```

Pass this to `fusion_edit_component_parameters`. Set the shared-definition flag only when changing every listed instance is intended. Otherwise leave it false; the tool rejects edits to repeated definitions. It does not quietly make an independent copy.

Before changing anything, the tool resolves the path, validates the expected component, checks external/reference and repeated-instance constraints, compares the state fingerprint, verifies every parameter belongs to that component, and validates expressions. It then recomputes and checks for newly introduced feature diagnostics. The result contains before/after states and affected instance paths.

The fingerprint covers parameter expressions, body volume/bounds/topology counts and sketch summaries. It is a useful stale-state check, not a complete topology or document revision proof. Downstream components can legitimately change when they reference the edited geometry; inspect those dependencies as part of verification.

## Adding features to an existing component

Supply its component token to the sketch, feature or hole tool. Select entities from that same component. The server validates ownership, resolves assembly proxies to native geometry, and rejects accidental cross-component inputs. Shared and externally referenced definitions receive the same checks.

`fusion_set_parameter` changes user parameters at design scope. Existing model parameters require an explicit component. Prefer `fusion_edit_component_parameters` for existing assemblies because it also checks the inspected state fingerprint.

## Verify and recover

Re-read the component context and compare expected dimensions. `fusion_validate_design` checks numerical body dimensions/volume, unhealthy features and underconstrained sketches. `fusion_check_interference` checks selected bodies or occurrences.

After a failure or timeout, inspect first. A failed script can leave partial effects even though some tested failures were rolled back by Fusion. The server keeps the operation uncertain until recovery is documented with `fusion_acknowledge_operation`. Do not reuse a new operation ID as a way to blindly retry.

External linked components are read-only through these typed editing tools. Opening and editing their source design is a separate workflow; automatic break-link and make-independent operations are not implemented.

## Verified fixture

The acceptance test builds two instances of `Module`, each containing the same `Pin` definition, plus an unrelated component. It then edits the already-created pin from 20 to 25 mm, verifies both nested instances, confirms the unrelated component is unchanged, and checks rejection of shared edits without the flag, stale state, and a foreign parameter. A second test exports this assembly to F3D, closes the generated fixture, reopens it, rediscovers references, and changes the shared pin from 25 to 30 mm.

Raw reports remain local under `validation/` and are excluded from Git. See the [validation summary](validation.md) and [test instructions](testing.md).
