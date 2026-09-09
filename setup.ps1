$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$environmentPath = Join-Path $projectRoot '.venv'
python -m venv $environmentPath
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
$projectPython = Join-Path $environmentPath 'Scripts/python.exe'
& $projectPython -m pip install "$projectRoot[test]"
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
$config = @{
    mcpServers = @{
        'fusion-native' = @{
            command = $projectPython
            args = @((Join-Path $projectRoot 'run.py'))
            env = @{
                FUSION_MCP_ENDPOINT = 'http://127.0.0.1:27182/mcp'
                FUSION_MCP_STATE_DIR = (Join-Path $projectRoot '.fusion-mcp')
            }
        }
    }
}
$config | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $projectRoot 'mcp-config.json') -Encoding utf8
Write-Output 'Installed. Import the server entry in mcp-config.json into your MCP client.'
