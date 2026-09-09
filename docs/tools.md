# Tool reference

Version 0.2.0 exposes 39 MCP tools. Use MCP tool discovery for authoritative argument schemas; Python sources define their validation rules.

## Connection and execution

- `fusion_capabilities`
- `fusion_inspect`
- `fusion_api_docs`
- `fusion_active_command`
- `fusion_execute_python`
- `fusion_operation_status`
- `fusion_acknowledge_operation`
- `fusion_screenshot`

## Documents

- `fusion_documents`
- `fusion_new_design`
- `fusion_activate_document`
- `fusion_open_archive`

## Existing designs and geometry

- `fusion_model_overview`
- `fusion_assembly_tree`
- `fusion_component_context`
- `fusion_edit_component_parameters`
- `fusion_query_entities`

## Modeling

- `fusion_set_parameter`
- `fusion_create_sketch`
- `fusion_constrain_sketch`
- `fusion_create_feature`
- `fusion_create_holes`

## Validation and assemblies

- `fusion_validate_design`
- `fusion_recompute`
- `fusion_check_interference`
- `fusion_assembly`
- `fusion_bom`
- `fusion_export`

## CAM and drawings

- `fusion_cam_inventory`
- `fusion_cam_browse_library`
- `fusion_cam_tools`
- `fusion_cam_create_setup`
- `fusion_cam_parameters`
- `fusion_cam_create_operation`
- `fusion_cam_generate`
- `fusion_cam_job`
- `fusion_cam_create_nc_program`
- `fusion_cam_post_process`
- `fusion_create_drawing`

## Where schemas live

- [server.py](../src/fusion_native_mcp/server.py): connection, documents, general execution, recovery, and screenshots.
- [features.py](../src/fusion_native_mcp/features.py): modeling, geometry, validation, assembly, and export schemas.
- [existing_features.py](../src/fusion_native_mcp/existing_features.py): nested assembly inspection and guarded component edits.
- [cam_features.py](../src/fusion_native_mcp/cam_features.py): CAM and drawing schemas.

NC creation, post-processing, cloud drawings, STL export, and revolute/slider joint paths remain experimental. See [validation](validation.md). Read [existing models](existing-models.md) before editing shared definitions and [execution/recovery](architecture.md) before submitting mutations.
