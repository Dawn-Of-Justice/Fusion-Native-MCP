# Roadmap

The goal is reliable end-to-end Fusion workflows, with particular emphasis on existing multi-component designs. This is a priority plan, not a promise of dates or complete API coverage. Completion requires implementation, independent validation, and recovery documentation.

## Delivered â€” v0.2

- [x] Native MCP bridge, document identity checks, persistent operation journal, and explicit uncertain-operation recovery.
- [x] Typed sketches and mechanical features with numerical/feature-health inspection.
- [x] Nested assembly discovery, shared-definition inspection, and guarded component parameter edits.
- [x] Existing assembly F3D export/reopen with reference rediscovery and subsequent edits.
- [x] Rigid assembly fixture, BOM, interference, and STEP/DXF export workflows.
- [x] Tool-library selection, milling setup, face operation, and asynchronous toolpath generation.

- [x] Packaged workflow skills covering core operations and discovery for additional Fusion workspaces.

## Priority 1 â€” Existing-document editing

- [ ] Feature-aware inspection and edits beyond parameter expressions: suppression, feature inputs, and clearer dependency previews.
- [ ] Explicit single-instance independence with a preview of affected definitions and references.
- [ ] Linked-component source-document workflow with save/update handling and no implicit break-link.
- [ ] Stronger stale-state detection and bounded, paginated inspection for large assemblies.

Acceptance: edit a nested repeated assembly, verify the intended instances and dependent geometry, preserve unrelated components, and reject stale or ambiguous targets.

## Priority 2 â€” Broader mechanical workflows

- [ ] More sketch primitives and explicit geometric/dimensional constraints.
- [ ] Live validation of revolute and slider joints, including measured motion limits.
- [ ] Live validation of STL export and cloud drawing creation with explicit destination inputs.
- [ ] Feature-specific failure diagnostics and recoverable multi-step workflows.

Acceptance: reproducible synthetic fixtures with dimensional, constraint, and feature-health checks; document partial failure behavior.

## Priority 3 â€” Manufacturing completion

- [ ] Expand CAM geometry selection and operation coverage beyond the validated face workflow.
- [ ] Machine, fixture, stock, and WCS configuration with inspectable selections.
- [ ] Live validation of NC program creation and post-processing with an explicitly selected post and output location.
- [ ] Investigate available APIs for simulation and collision verification before defining supported coverage.

Acceptance: inspect setup and tool choices, generate valid toolpaths, verify resulting files and post configuration, and distinguish generation success from machining verification.

## Priority 4 â€” Compatibility and releases

- [ ] Test macOS installation and native connection behavior.
- [ ] Maintain a Fusion/native-protocol compatibility matrix across upgrades.
- [ ] Add SSE support if required by supported native endpoints.
- [ ] Add release artifact verification and a repeatable tagged-release procedure.

## How priorities change

Open a feature issue with a concrete part, assembly, or manufacturing workflow. Include expected inputs, output, and a measurable acceptance criterion. See [contributing](CONTRIBUTING.md) and the [current validation record](docs/validation.md).
