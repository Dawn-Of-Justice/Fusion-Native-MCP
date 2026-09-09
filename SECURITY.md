# Security

## Trust boundary

This server executes Python in the local Fusion process. Code can access files and other resources available to Fusion. `read_only` limits design changes; it is not a Python sandbox. Only connect trusted MCP clients and run trusted scripts.

The native endpoint is restricted to loopback HTTP. Do not expose or forward it to an untrusted network. Document identity checks and journals prevent certain accidental operations, but are not an authorization system and do not coordinate unrelated native clients or manual edits.

Keep `.fusion-mcp/`, `mcp-config.json`, credentials, proprietary models, and raw operation reports private. The operation journal may contain submitted code and model information. Preserve it when recovering from uncertain operations.

## Reporting a vulnerability

If this repository's GitHub Security tab offers **Report a vulnerability**, use that private channel. Otherwise, open an issue asking maintainers for a private reporting channel without including exploit details, credentials, or customer data. Do not publish a working exploit while arranging private disclosure.

Include affected versions, prerequisites, impact, and a minimal synthetic reproduction through the private channel. There is no guaranteed response time or long-term support policy yet; fixes are targeted at the current development line.
