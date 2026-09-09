# Contributing

Contributions to modeling, existing-document workflows, CAM, tests, and documentation are welcome. For a large change, open an issue describing the user workflow and expected behavior before implementing it. Small fixes can go directly to a pull request.

## Set up

Fork and clone the repository, create a branch, and run these commands from its root:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[test]"
./.venv/Scripts/python.exe -m pytest tests -q
```

Use `./setup.ps1` if you also need a local MCP client configuration. Fusion is not required for offline development. Live tests require a compatible running Fusion installation; see [testing](docs/testing.md).

## Implementation expectations

- Validate tool inputs in the typed schema and validate entity ownership inside Fusion.
- Preserve document guards, durable operation claims, completion checks, and the no-automatic-retry behavior for mutations.
- Treat component definitions and placed occurrences distinctly. Discover shared and externally linked definitions before changing geometry.
- Include units in expressions; convert internal geometry units explicitly.
- Keep MCP stdout free of diagnostics. Log to stderr.
- Add regression tests for meaningful behavior changes. Use independent geometry or state checks for live acceptance, not only a successful response.
- Document partial effects, recovery behavior, and any live-validation gaps. Experimental tools must remain labeled accordingly.

Runtime modules execute inside Fusion and use `adsk`; ordinary server modules run in the external Python environment. Keep that boundary intact. See [architecture](docs/architecture.md).

## Before opening a pull request

Run offline tests and build the package:

```powershell
./.venv/Scripts/python.exe -m pip install build
./.venv/Scripts/python.exe -m build
```

Describe the problem, resulting behavior, and exact validation performed. For live checks, include the Fusion version and a sanitized result summary. State explicitly when live validation was not performed. Update the README, tool guide, roadmap, or changelog when behavior or status changes.

Do not commit local MCP configuration, operation databases, credentials, customer designs, entity tokens, or generated validation reports. Use small synthetic fixtures you have permission to share. Git ignores local validation outputs; intentional public fixtures should be reviewed separately.

## Review and community

Keep discussion respectful and focused on the work. Explain tradeoffs and respond constructively to review. Report security-sensitive issues using [SECURITY.md](SECURITY.md). Contributions are provided under this repository's MIT license.
