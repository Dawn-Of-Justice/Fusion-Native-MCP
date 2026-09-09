"""Opt-in assembly and CAM setup test, after live_smoke --model."""
import asyncio
import json
import os
from pathlib import Path
import sys
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    root = Path(__file__).resolve().parents[1]
    out = root / "validation"
    env = dict(os.environ, PYTHONPATH=str(root / "src"), FUSION_MCP_STATE_DIR=str(out / "state"))
    report = {}
    async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "fusion_native_mcp.server"], env=env)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(name, arguments=None):
                response = await session.call_tool(name, arguments or {})
                assert not response.isError, response
                return json.loads(response.content[0].text)
            for filename in ("create_cam_setup.py", "create_rigid_assembly.py"):
                state = (await call("fusion_inspect"))["data"]
                result = await call("fusion_execute_python", {"script": (root / "examples" / filename).read_text(), "expected_document_id": state["document"]["id"], "operation_id": str(uuid.uuid4())})
                report[filename] = result
                (out / "breadth-report.json").write_text(json.dumps(report, indent=2))
                assert result["state"] == "succeeded", result
                verified = (await call("fusion_inspect"))["data"]
                report[filename + ":verified"] = verified
                if filename == "create_cam_setup.py":
                    assert verified["cam"]["setups"] == 1
                else:
                    assert verified["design"]["occurrences"] == 2
                    assembly = await call("fusion_execute_python", {"script": (root / "examples/inspect_assembly.py").read_text(), "read_only": True})
                    assert sum(c["as_built_joints"] for c in assembly["data"]["components"]) == 1
                    assert verified["design"]["unhealthy_features"] == []
                    report["assembly_inventory"] = assembly
    (out / "breadth-report.json").write_text(json.dumps(report, indent=2))
    print("Assembly and CAM setup integration tests passed")


if __name__ == "__main__":
    asyncio.run(main())
