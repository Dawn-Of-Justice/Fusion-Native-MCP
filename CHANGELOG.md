# Changelog

Notable project changes are recorded here. Version headings describe local implementation milestones; they do not imply published GitHub or package-index releases.

## Unreleased

### Added

- GitHub-ready documentation, MIT license, contribution and security policies, roadmap, and issue/PR templates.
- Offline CI and package builds; portable MCP configuration example and explicit source-distribution contents.

## 0.2.0 — 2026-09-10

### Added

- 39 tools covering typed mechanical features, assembly inspection/editing, exports, and CAM workflows.
- Nested occurrence paths, component context, shared-definition and ownership guards, and definition fingerprints for existing-component parameter edits.
- Document activation and local archive reopening; validated existing assembly editing after F3D round-trip.
- Tool-library discovery and selection, milling setup, face operation, and asynchronous toolpath jobs.
- Experimental NC program, post-processing, cloud drawing, and moving-joint paths.

### Fixed

- Split long source literals and require an execution-completion marker to detect native responses that reported success without running the submitted code.
- Resolve nested occurrence references in root assembly context and distinguish proxy geometry from native component geometry.

## 0.1.0 — 2026-09-09

### Added

- Native Fusion MCP adapter using the official MCP Python SDK.
- Trusted Python execution, document identity guard, durable operation journal, replay protection, and explicit uncertain-operation recovery.
- Design inspection, installed API documentation lookup, viewport capture, and live modeling/assembly/CAM examples.
