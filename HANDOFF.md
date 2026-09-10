# Development handoff

Updated: **2026-09-10**. This document transfers project context to a new agent session. It describes current implementation and recorded evidence; it is not authorization to modify a user's design, publish a release, or execute machine code.

## Start here

The user wants a reliable, end-to-end MCP integration with Autodesk Fusion for mechanical parts, assemblies, and manufacturing. The strongest current priority is **editing an already existing, nested, multi-component document correctly**, including repeated component definitions. Do not replace this goal with a collection of new-document demos.

The project is **Fusion Native MCP**, package version **0.2.0**. The local development checkout was renamed and moved to the user's Desktop. Resolve it as `~/Desktop/Fusion-Native-MCP` on the original Windows machine; the earlier dated Codex task workspace is not the source checkout. Work from the actual repository and inspect any applicable `AGENTS.md` first.

At this handoff, the active branch was `main`, and the checkout had a clean working tree before this document's changes. Recent history was:

- `07eff42` — Add installation guide and skills documentation for Fusion Native MCP
- `8a26919` — Add comprehensive integration tests for MCP features and functionality

The configured remote is [Dawn-Of-Justice/Fusion-Native-MCP](https://github.com/Dawn-Of-Justice/Fusion-Native-MCP). A configured remote does not prove the current branch has been pushed or that GitHub CI passed. Recheck Git status, branch, upstream, and history before working; never infer them from earlier conversation summaries.

Read in this order:

1. [README](README.md) — current scope and capability matrix.
2. [Existing-model guide](docs/existing-models.md) — definition/occurrence semantics and guarded edits.
3. [Architecture and recovery](docs/architecture.md) — mutation contract and failure behavior.
4. [Validation record](docs/validation.md) and [testing](docs/testing.md) — evidence and reproduction.
5. [Roadmap](ROADMAP.md), [contributing](CONTRIBUTING.md), and relevant source modules.

The [installation guide](docs/installation.md), [cheat sheet](docs/cheatsheet.md), and [skill catalog](docs/skills.md) are user-facing onboarding documents; keep them aligned with changes.

## Architecture and source map

```text
Assistant / MCP client
  -> stdio: Python MCP SDK server
  -> document guard + persistent SQLite operation journal
  -> loopback HTTP: Autodesk native MCP endpoint
  -> Python executed inside the running Fusion process
```

No custom Fusion add-in is required. The server process runs in the external Python environment; the runtime scripts execute in Fusion and import `adsk`. Keep that boundary intact.

| File | Responsibility |
| --- | --- |
| [run.py](run.py) | Adds checkout `src` to Python's import path and launches the stdio server |
| [server.py](src/fusion_native_mcp/server.py) | Core tools, document operations, inspection, trusted Python execution and registration |
| [native.py](src/fusion_native_mcp/native.py) | Native HTTP/session handling, loopback restriction, protocol errors |
| [bridge.py](src/fusion_native_mcp/bridge.py) | Script wrapping, document guard, completion parsing, journal and recovery |
| [features.py](src/fusion_native_mcp/features.py) | Pydantic schemas, feature service, typed design/geometry/assembly/export tools |
| [existing_features.py](src/fusion_native_mcp/existing_features.py) | Existing component context and guarded model-parameter edit schemas |
| [cam_features.py](src/fusion_native_mcp/cam_features.py) | CAM, NC and drawing schemas/tools |
| [runtime.py](src/fusion_native_mcp/runtime.py) | In-Fusion geometry, modeling, assembly, validation and export handlers |
| [runtime_existing.py](src/fusion_native_mcp/runtime_existing.py) | In-Fusion nested occurrence resolution and scoped editing |
| [runtime_cam.py](src/fusion_native_mcp/runtime_cam.py) | In-Fusion CAM jobs, tools, NC and drawing handlers |

`FeatureService` reads and combines the three runtime source files, appends a `run(context)` dispatcher, then passes the script through the bridge. Ensure runtime files remain bundled in the wheel when changing packaging. Discover authoritative argument schemas from the server or source; do not invent tool names from Fusion UI commands.

Dependencies are declared in [pyproject.toml](pyproject.toml): Python >=3.11, `mcp==1.30.0`, `httpx==0.28.1`, and Pydantic >=2.11,<3. Hatchling builds wheel/source packages. There are **39 wrapper tools**; `fusion_capabilities` returns the distinct native tool set, not the wrapper tool count.

## Invariants to preserve

- Record mutations durably before sending them. A shared SQLite journal claims writes across server processes using that journal.
- An identical request under the same operation ID retrieves its prior record. A different payload under that ID is rejected. There is no automatic mutation retry.
- `started` and `uncertain` block subsequent new writes. Inspect actual effects and establish execution has finished before acknowledgement. Acknowledgement neither cancels nor undoes anything.
- Keep document identity checks inside Fusion before user code, including imports. Duplicate creation IDs are rejected. `__NO_DOCUMENT__` is valid only when no document is active.
- A successful execution response is not proof of correct geometry or machining results. Verify independently.
- Preserve completion-marker enforcement and long-source splitting. Do not remove them as unnecessary formatting.
- Component definitions own geometry/model parameters; occurrences place them. Shared-definition changes affect every occurrence, including occurrences through repeated parent subassemblies.
- Existing-component edits require the exact occurrence path, expected component token, fresh definition fingerprint, and inspected model parameter names. Reject foreign parameters, stale state, external links and unacknowledged shared edits.
- The fingerprint covers selected parameter/geometry/sketch state; it is not a complete topology/revision lock. Manual edits and unrelated native clients remain outside journal coordination.
- Distinguish native component geometry from root assembly-context proxies. Resolve and measure in the appropriate coordinate system.
- Explicit expressions carry units. Fusion API numeric lengths use centimeters; typed checks use mm and mm³.
- General Python execution has Fusion's local privileges. `read_only` guards design changes, not file/system access. Do not describe it as a sandbox.

## Lessons from live development

### Native success without execution

On the tested Fusion build, source with very long lines could report success without actually executing. The bridge splits embedded script literals into roughly 500-character adjacent chunks and requires an execution-completion marker. Offline tests verify source preservation and missing-marker rejection. An early feature run affected by this behavior is excluded from successful evidence; later fixture runs were repeated after the fix.

### Nested occurrence references

Some nested native occurrences did not yield usable tokens. The runtime resolves these through root-context proxies. Do not simplify this to unqualified component names or native occurrence tokens without reproducing the nested case.

### Shared versus independent edits

The successful acceptance fixture contains two Module instances sharing a Pin definition, plus an unrelated component. Changing the Pin definition from 20 to 25 mm updates both nested instances; the unrelated component is checked separately. A request to change only one instance requires a make-independent workflow that does not exist yet. Never satisfy that request by enabling a shared-definition edit.

### Partial effects and restarts

Some failures appeared rolled back by Fusion, but rollback is not a general guarantee. Treat uncertain effects conservatively. CAM job handles can become unknown after restarting Fusion; inspect inventory and journal records rather than resubmitting generation. Document IDs and tokens must be rediscovered after archive reopening or a restart.

## Local setup and chat integration

The original machine has a self-contained `.venv` in the Desktop checkout. `setup.ps1` creates that environment, installs dependencies and writes `mcp-config.json`; it does not automatically register a client or install skills. The launcher uses checkout source, while direct imports outside the checkout may use an installed package copy. Use the explicit checkout interpreter and correct working directory.

The prior session registered `fusion-native` in `~/.codex/config.toml` using the Desktop interpreter and `run.py`, a 30-second startup timeout and 180-second tool timeout. Both endpoint and journal use explicit configured values:

- Default endpoint: `http://127.0.0.1:27182/mcp`.
- Journal: `<checkout>/.fusion-mcp/operations.sqlite3`.
- Ten complete skill folders copied to `~/.codex/skills/fusion-*` (or the configured Codex home).

Installed skills are copies, not links. Update relevant installed copies after changing repository skills only within the user's authorized installation scope. Preserve unrelated Codex settings and existing skill customizations. A previous configuration backup is in the old task workspace's `work/codex-config-before-fusion.toml`; do not commit it or restore it wholesale over later settings.

The configured stdio launcher was tested with a real MCP client: 39 tools discovered, and native capabilities, document listing and inspection succeeded. The last read-only inspection observed Fusion **2705.1.11**, three open documents, and an active unsaved `Untitled` assembly with four components, five occurrences and no unhealthy features. This is historical context, not current target identity. Never reuse its IDs or assume it is still active.

A new chat may need an MCP restart/reconnect to expose newly configured tools. Inspect actually callable tools first. Do not claim direct chat attachment merely because a separate stdio test passed. Keep Fusion open with native MCP enabled under Preferences → General → API.

A read-only check during this handoff found zero rows in the configured journal. Fixture tests use their own output/state directories, so this does not contradict their recorded validation history. Recheck rather than assuming the journal remains empty.

Before a live mutation, inspect unresolved journal records through the tools or a read-only database connection. Preserve the journal; do not clear it to get tests or edits running. Avoid posting raw records, document tokens, local paths, or private designs to GitHub.

## Validation already recorded

- **26 offline tests** passed after repository and skill setup.
- Typed fixtures passed for constrained rectangles/circles, extrude, revolve, sweep, loft, fillet, chamfer, shell, combine, rectangular/circular patterns and holes.
- Parameters, geometry queries, feature health, numerical checks, BOM, interference, STEP and sketch DXF were checked.
- A rigid as-built joint fixture passed in the earlier development milestone.
- Explicit CAM library/tool selection, milling setup, face operation, async generation and valid-toolpath polling passed.
- Existing nested shared edits passed, including rejection of stale fingerprints, foreign model parameters and unacknowledged shared edits.
- The nested assembly was exported to F3D, only its generated fixture was closed, the archive reopened, references rediscovered, and shared length changed from 25 to 30 mm.
- All ten skill folders passed the skill-creator validator. Instructions have not all received independent behavioral/live acceptance tests.
- Wheel/source builds passed; runtime files, MIT metadata, README, skills and references were checked. Documentation links and installation-example syntax were checked.

Raw accepted reports, if still present locally, include `validation/v0.2-run2/features-report.json`, `validation/kinds-run1/kinds-report.json`, `validation/existing-run3/existing-report.json`, and `validation/reopen-run1/reopen-report.json`. Raw artifacts are ignored by Git and may be absent from a fresh clone. Public claims belong in [docs/validation.md](docs/validation.md).

## Checks for the next change

Run from the actual repository root in PowerShell:

```powershell
./.venv/Scripts/python.exe -m pytest tests -q
```

For package changes, install `build` in the environment if needed, then:

```powershell
./.venv/Scripts/python.exe -m build
```

Previous local builds used `uv build` with a dependency cache in the old task workspace. That cache is a convenience, not a repository requirement. If temporary directory permissions block pytest, use an absolute writable task-owned `--basetemp` directory and `-p no:cacheprovider`; do not alter tests to conceal an environment error.

The CI workflow runs offline tests/builds on Windows with Python 3.11/3.12. It does not run Fusion. Check actual GitHub results before reporting CI success.

Live scripts are opt-in, not collected by pytest:

| Script | Scope / prerequisite |
| --- | --- |
| `tests/live_smoke.py` | Read-only by default; `--model` creates and edits a sample design |
| `tests/live_breadth.py` | Expects the sample plate active with no prior CAM setup; not a generic read-only check |
| `tests/live_features.py` | Creates its own fixture; checkpoints successful steps and does not auto-acknowledge uncertain writes |
| `tests/live_feature_kinds.py` | Creates feature fixtures |
| `tests/live_existing.py` | Creates the repeated nested assembly and exercises scoped edits/rejections |
| `tests/live_reopen.py` | Requires the existing-fixture report; exports/closes only that fixture, reopens and edits it |

Read [testing](docs/testing.md) and the relevant script before execution. Use a new output directory for a clean acceptance run. Never point fixture tests at arbitrary customer documents. Select tests appropriate to the change rather than rerunning all live mutations for documentation edits.

## Known limits and next development

Implemented but **not live-validated**: NC program creation, post-processing, automatic cloud drawing creation, STL export, revolute/slider joints. No machine code was generated in the recorded acceptance runs.

Not implemented: single-instance independence, automatic externally linked source editing, CAM simulation, arbitrary broken-topology repair. Surface/form/sheet-metal/mesh, render/animation, simulation/generative and electronics skills primarily guide discovery; they do not create missing dedicated server capabilities. Native electronics schema discovery does not itself expose a callable wrapper tool.

Recommended next work, subject to the user's next request:

1. Improve feature-aware inspection/editing of existing components beyond parameter expressions, including explicit dependency/affected-instance summaries.
2. Design an explicit make-independent operation, with a synthetic nested/shared fixture and reference-preservation checks before claiming single-instance edits.
3. Strengthen stale-state detection and bounded inspection for large assemblies; retain current fingerprint limitations in documentation.
4. Validate moving joints, drawings and NC/post paths using specified inputs and independent output checks. Automatic drawings require a saved design; NC requires a selected post and output location.
5. Expand machining selections, machine/fixture setup and investigate actual simulation API access. Do not infer support from UI features or accepted strategy strings.

For a feature change, update schemas and runtime together, add meaningful failure/ownership tests, run the smallest relevant synthetic live fixture, and update the validation record, roadmap, tool documentation and applicable skills. A successful tool call alone is insufficient acceptance.

## Suggested first message for a new agent

> Read HANDOFF.md, inspect current Git status and relevant source, and continue Fusion Native MCP development. Prioritize reliable editing of existing nested multi-component documents. Verify current tool connectivity and document identity before any live work, preserve the operation journal and unrelated designs, and distinguish implemented features from live-validated behavior. Tell me the concrete next improvement before beginning it.
