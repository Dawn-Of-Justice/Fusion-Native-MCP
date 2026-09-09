# Existing component edit arguments

After inspecting `fusion_component_context`, send this shape to `fusion_edit_component_parameters`. Values in angle brackets are substitutions from current inspection, not executable example values.

```json
{
  "document_id": "<current creation ID>",
  "operation_id": "<new UUID>",
  "spec": {
    "path": "Module:1+Pin:1",
    "expected_component": "<fresh component token>",
    "expected_fingerprint": "<fresh 64-character fingerprint>",
    "expressions": {"<inspected model parameter name>": "30 mm"},
    "allow_shared_definition_edit": true
  }
}
```

The shared flag is appropriate only when the user intends to edit every inspected occurrence of the definition. For a single-instance request, leave it false and report the missing independence workflow. Read context again after the edit and check the resulting dimension in the intended coordinate system.
