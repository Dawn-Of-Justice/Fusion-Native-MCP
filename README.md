# Fusion Native MCP

**Control Autodesk Fusion through its native MCP endpoint: mechanical modeling, existing assemblies, and CAM workflows.**

Fusion Native MCP connects an MCP-compatible assistant to the Fusion desktop application. It provides 39 tools for inspecting designs, creating features, editing existing components, exporting models, and generating toolpaths. A persistent operation journal tracks writes and prevents blind retries after a disconnect.

Version **0.2.0** · Python **3.11+** · **MIT** · Windows live-tested

This is an independent community project, not an Autodesk product. It is under active development; tool coverage is not equivalent to complete Fusion API coverage.

[Quick start](#quick-start) · [Existing assemblies](docs/existing-models.md) · [Tool reference](docs/tools.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

## What it can do

| Area | Available workflows | Validation status |
| --- | --- | --- |
| Mechanical parts | Constrained rectangle/circle sketches, extrude, revolve, sweep, loft, fillet, chamfer, shell, combine, patterns, holes | Live-tested on generated fixtures |
| Existing assemblies | Nested occurrence paths, shared-definition discovery, component parameter edits with ownership and stale-state checks | Live-tested, including F3D export/reopen |
| Assembly creation | Components, instances, as-built joints, BOM and interference | Rigid joint tested; revolute/slider experimental |
| Inspection and export | Entity queries, parameters, feature health, numerical geometry checks, screenshots, STEP/F3D/DXF | Live-tested; STL experimental |
| CAM | Tool libraries, milling setup, face operation, asynchronous toolpath generation | Face workflow live-tested |
| NC and drawings | NC program creation, post-processing, automatic cloud drawings | Implemented, not live-validated |
| Custom operations | Execute trusted Python through the installed Fusion API | General execution tested; individual scripts require verification |

Making one shared instance independent, automatic linked-source editing, CAM simulation, and arbitrary broken-topology repair are not implemented. See the [validation record](docs/validation.md) for the tested environment and limits.

## How it works

```text
MCP-compatible client
    | stdio
Fusion Native MCP (Python)
    | document checks + SQLite operation journal
    | local HTTP
Autodesk Fusion native MCP
    | Fusion Python API
Open Fusion document
```

No custom Fusion add-in is required. Fusion must be running with its native MCP server enabled. This adapter currently handles JSON HTTP responses; SSE responses are unsupported.

## Quick start

### 1. Prepare Fusion

Install Fusion and enable its native MCP server using the [Autodesk MCP overview](https://help.autodesk.com/view/fusion360/ENU/?guid=FMCP-OVERVIEW). Keep Fusion open and note its local endpoint. The default used here is `http://127.0.0.1:27182/mcp`.

You also need Python 3.11 or newer and an MCP client capable of launching a stdio server. Windows is the tested platform; macOS setup and live behavior are not yet validated.

### 2. Install this checkout

Download or clone this repository, open PowerShell in its root, and run:

```powershell
./setup.ps1
```

The script creates `.venv`, installs the package and test dependencies, and generates `mcp-config.json` with absolute paths for this checkout. Rerunning it regenerates that local configuration.

For manual installation:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install ".[test]"
```

### 3. Connect your MCP client

Import the `fusion-native` server entry from the generated `mcp-config.json` into your client's MCP settings. For clients with a different configuration format, use its `command`, `args`, and environment values. Restart or reconnect the client after changing its configuration.

The portable [configuration example](mcp-config.example.json) uses placeholder paths; replace them with your checkout's absolute paths. The real configuration stays local and is ignored by Git.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `FUSION_MCP_ENDPOINT` | `http://127.0.0.1:27182/mcp` | Native endpoint; only loopback HTTP URLs are accepted |
| `FUSION_MCP_STATE_DIR` | `.fusion-mcp` in the working directory | Durable journal; use one shared absolute directory across clients |

### 4. Verify the connection

Ask your client to call `fusion_capabilities`, `fusion_documents`, then `fusion_inspect`. Confirm that the returned document is the one you intend to work on. Tools are discoverable through MCP; full argument schemas are supplied by the server.

An example first prompt:

> Inspect the active Fusion design. List its component hierarchy, shared definitions, and unhealthy features. Do not modify it.

For a first modeling task, create a separate design and verify the resulting dimensions and feature health. [Example Python scripts](examples/) demonstrate modeling, rigid assemblies, and CAM inspection. They are scripts for execution inside Fusion, not standalone Python programs.

## Working on an existing multi-component document

1. List and activate the intended document, then obtain its current creation ID.
2. Call `fusion_assembly_tree` and choose an exact occurrence path, such as `Module:1+Pin:1`.
3. Call `fusion_component_context` to inspect parameters, geometry, shared instances, and the definition fingerprint.
4. Call `fusion_edit_component_parameters` with those fresh references. Explicitly allow a shared-definition edit only when every listed instance should change.
5. Reinspect the component, validate the design, and check relevant downstream geometry.

An occurrence places a component definition in an assembly. Editing that definition changes every instance. External linked definitions are rejected by the typed editing tools. References must be rediscovered after reopening a document or restarting Fusion. Read the [complete existing-model guide](docs/existing-models.md) for an argument example and recovery behavior.

## Execution and recovery

Mutations require an operation ID and a document identity guard. Reusing an ID with the identical request returns its recorded result; changing the request under that ID is rejected. A timeout or ambiguous execution blocks new writes until you inspect Fusion and record recovery with `fusion_acknowledge_operation`.

Acknowledgement does not undo, cancel, or retry an operation. Keep the journal: deleting it removes duplicate protection. A successful script result is not proof of correct geometry or valid machining output.

`fusion_execute_python` runs with Fusion's local Python privileges. Its read-only flag guards design changes; it is not a filesystem or operating-system sandbox. Use trusted clients and scripts. See [architecture and recovery](docs/architecture.md) and [security](SECURITY.md).

## Development

```powershell
./.venv/Scripts/python.exe -m pip install -e ".[test]"
./.venv/Scripts/python.exe -m pytest tests -q
```

Offline tests do not require Fusion. Live scripts are opt-in and can modify documents; read [testing](docs/testing.md) before running them. GitHub Actions is configured to run offline tests and package builds on Windows with Python 3.11 and 3.12.

```text
src/fusion_native_mcp/  Protocol adapter, typed tools, and Fusion runtimes
tests/                 Offline tests and explicit live acceptance scripts
examples/              Scripts intended to run inside Fusion
docs/                  Architecture, existing models, tools, testing, validation
.github/               CI, issue forms, and pull request template
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [ROADMAP.md](ROADMAP.md), and [CHANGELOG.md](CHANGELOG.md). Source distributions include the guides and examples; local journals, credentials, environments, and generated CAD artifacts are excluded.

## License and references

Released under the [MIT License](LICENSE). Autodesk Fusion and third-party dependencies remain subject to their own terms.

- [Autodesk Fusion MCP overview](https://help.autodesk.com/view/fusion360/ENU/?guid=FMCP-OVERVIEW)
- [Fusion API reference](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Welcome.htm)
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)
