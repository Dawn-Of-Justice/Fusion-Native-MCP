# Installation guide

Install the server, connect your assistant, and optionally add the workflow skills. Windows is the live-tested platform. The commands below assume PowerShell and a source checkout of this repository.

## 1. Prerequisites

- Autodesk Fusion with its native MCP feature available and enabled. Follow the [Autodesk MCP overview](https://help.autodesk.com/view/fusion360/ENU/?guid=FMCP-OVERVIEW) for your installed version.
- Python 3.11 or newer. The recorded live tests used Python 3.12 and Fusion 2705.1.11.
- An MCP client that can launch a local stdio server, such as Codex.
- Internet access for the initial Python dependency installation.

No custom Fusion add-in, OpenAI API key, or Autodesk API credential is configured by this package. Your assistant and Fusion retain their own account and access requirements. See [validation](validation.md) for coverage limits.

## 2. Get the source and install

Clone this repository using its GitHub clone URL, or download and extract its source archive. Open PowerShell in the folder containing `pyproject.toml`, `run.py`, and `setup.ps1`. Use a stable location: client launch paths point to this folder.

```powershell
python --version
./setup.ps1
```

The script creates `.venv`, installs the server and test dependencies, and writes a local `mcp-config.json` with absolute paths. It does not register the server in your assistant or install skills. Rerunning setup regenerates the configuration, including resetting the endpoint to the package default.

If PowerShell blocks the script, use the manual installation below instead of changing your system execution policy:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install ".[test]"
```

For manual installation, copy [mcp-config.example.json](../mcp-config.example.json) to `mcp-config.json` and replace every `C:/path/to/Fusion-Native-MCP` with your checkout's absolute path. Manual installation does not generate that file for you. Virtual-environment activation is optional because these commands use its interpreter directly.

## 3. Start Fusion's native endpoint

Open Fusion and enable its native MCP server under **Preferences → General → API**, as described in the Autodesk overview. Keep Fusion open while using the integration. Note the endpoint displayed by Fusion; this package defaults to:

```text
http://127.0.0.1:27182/mcp
```

If your endpoint differs, update `FUSION_MCP_ENDPOINT` in the client configuration you actually register. Only loopback HTTP endpoints are accepted. Do not replace this with a remote host or expose it over the public network.

There are two connections: your assistant launches this Python server over **stdio**, and the Python server connects to Fusion over **local HTTP**. Registering only Fusion's URL bypasses this package's typed tools and operation journal.

## 4. Connect your assistant

Choose the instructions for your client. Merge the Fusion entry into existing configuration; do not replace unrelated server settings.

### Codex

The [official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) describes the shared configuration and server settings. Add this entry to your Codex `config.toml`, normally `~/.codex/config.toml`. Replace all example paths with real absolute paths:

```toml
[mcp_servers.fusion-native]
enabled = true
command = "C:/path/to/Fusion-Native-MCP/.venv/Scripts/python.exe"
args = ["C:/path/to/Fusion-Native-MCP/run.py"]
startup_timeout_sec = 30
tool_timeout_sec = 180

[mcp_servers.fusion-native.env]
FUSION_MCP_ENDPOINT = "http://127.0.0.1:27182/mcp"
FUSION_MCP_STATE_DIR = "C:/path/to/Fusion-Native-MCP/.fusion-mcp"
PYTHONDONTWRITEBYTECODE = "1"
```

If `fusion-native` already exists, update that entry rather than adding a duplicate TOML table. Forward slashes in Windows paths avoid TOML backslash escaping problems.

In the desktop app, open **Settings → MCP servers** and restart the Fusion server after saving. If it does not appear, reopen the app. The CLI's `codex mcp list` verifies configuration; it does not by itself prove Fusion is responding. Longer tool timeouts do not cancel execution or make retries safe.

### Clients using mcpServers JSON

Copy the `fusion-native` entry from the generated `mcp-config.json` into your client's `mcpServers` object. The entry supplies `command`, `args`, and `env`. For other formats, enter those same values in the client's stdio server settings. Restart or reconnect the server using that client's controls.

The client launches and manages the Python process. You do not need a second terminal running `run.py`. Starting it manually waits for MCP messages on stdin; it is not a conversational command prompt.

### Journal location

Use one stable, absolute `FUSION_MCP_STATE_DIR` for every client controlling the same Fusion session. Keep that directory across restarts and updates. It stores operation records used to detect repeated or uncertain writes. Separate journals do not coordinate with one another.

## 5. Install the optional skills

Skills teach the assistant workflows; the MCP server provides the executable tools. The source checkout/archive includes all ten skill folders. The Python wheel contains the server, so obtain the source archive as well if you want skills.

For Codex, copy each complete `skills/fusion-*` folder into `$CODEX_HOME/skills`, normally `~/.codex/skills`. This PowerShell example, run from the repository root, installs all ten and stops before copying if any destination already exists:

```powershell
$skillRoot = if ($env:CODEX_HOME) {
    Join-Path $env:CODEX_HOME 'skills'
} else {
    Join-Path $env:USERPROFILE '.codex/skills'
}
$sourceSkills = @(Get-ChildItem -LiteralPath './skills' -Directory -Filter 'fusion-*')
if ($sourceSkills.Count -ne 10) { throw 'Expected ten packaged Fusion skills' }
foreach ($skill in $sourceSkills) {
    if (Test-Path -LiteralPath (Join-Path $skillRoot $skill.Name)) {
        throw "Skill already installed: $($skill.Name). Review it before updating."
    }
}
New-Item -ItemType Directory -Path $skillRoot -Force | Out-Null
foreach ($skill in $sourceSkills) {
    Copy-Item -LiteralPath $skill.FullName -Destination $skillRoot -Recurse -ErrorAction Stop
}
```

Keep the `references/` subfolders with their skills. Installed skills become available on the next turn; reconnect/reopen the client if its discovery list remains stale. Other clients should use their supported skill location or load the relevant `SKILL.md` as instructions. See the [catalog](skills.md) for scope and support levels.

## 6. Verify from chat

Ask:

> Use Fusion Native MCP to list the available tools and open documents, then inspect the active design. Do not modify anything.

Expected checks:

1. The wrapper exposes 39 tools in version 0.2.0.
2. `fusion_capabilities` reaches Fusion's native endpoint. It lists native capabilities, whose count differs from the wrapper's 39 tools.
3. `fusion_documents` and `fusion_inspect` return the actual open document state. Compare the active design with Fusion's UI.
4. For an assembly, `fusion_assembly_tree` returns its nested occurrence paths.

An empty design is valid for a connection check. No open document should not be mistaken for a transport failure. Begin with inspection, then try a separate synthetic part before editing a complex design.

Optional offline verification:

```powershell
./.venv/Scripts/python.exe -m pytest tests -q
```

Offline tests do not connect to Fusion. For explicit live acceptance scripts and their side effects, read [testing](testing.md). See the [cheat sheet](cheatsheet.md) for everyday prompts.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| `python` missing or wrong version | Install/select Python 3.11+ and reopen PowerShell; check `python --version` |
| Server process fails to start | Check the absolute interpreter and `run.py` paths; install dependencies into that exact environment |
| Connection refused | Open Fusion, enable native MCP, and compare its port with the registered endpoint |
| Config changed but tools missing | Restart the MCP server in the client; reopen the client if needed |
| Native tools appear but typed Fusion tools do not | Ensure the client launches this package over stdio rather than connecting directly to Fusion's URL |
| Document mismatch or stale component fingerprint | Reinspect and rediscover the correct document/component; do not guess IDs or reuse stale tokens |
| Writes blocked by `started` or `uncertain` | Inspect journal status and actual Fusion effects; reconcile before acknowledgement or another mutation |
| CAM job unknown after restarting Fusion | Inspect CAM inventory and operation state; do not resubmit solely because a job ID was lost |
| HTTP/SSE compatibility error | The current bridge supports JSON responses; check the installed Fusion version and [validation](validation.md) |
| Skill is visible but cannot execute | Verify the MCP connection separately; skills do not supply missing server tools |

`fusion_acknowledge_operation` records verified recovery; it does not undo or cancel anything. A client timeout can occur while Fusion continues working. See [architecture and recovery](architecture.md).

## Updating, moving, and removing

For an update, stop the client-managed server after pending operations finish, preserve your journal and local configuration, update the source, and reinstall dependencies with the manual pip command above. Reconnect and repeat the read-only verification. Review and refresh installed skill copies separately.

If moving the checkout, recreate `.venv` at the destination, update all registered absolute paths, and preserve the journal as one consistent directory after all clients stop using it. Do not leave clients pointing at different copies of the journal.

To disconnect, disable/remove only the `fusion-native` entry in your client's MCP settings and restart its connection. Remove only the installed `fusion-*` skill folders you intentionally installed. Keep the project and journal until any uncertain operations have been reconciled.
