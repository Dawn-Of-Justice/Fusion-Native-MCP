"""Opt-in actual stdio MCP integration; --model creates and edits a new sample document."""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import sys
import uuid

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root / "src"), FUSION_MCP_STATE_DIR=str(args.output / "state"))
    params = StdioServerParameters(command=sys.executable, args=["-m", "fusion_native_mcp.server"], env=env)
    report = {}
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(name, arguments=None):
                response = await session.call_tool(name, arguments or {})
                if response.isError:
                    raise RuntimeError(str(response.content))
                return json.loads(response.content[0].text)
            report["tools"] = [t.name for t in (await session.list_tools()).tools]
            report["before"] = await call("fusion_inspect")
            for example in ("inspect_assembly.py", "inspect_cam.py"):
                report[example] = await call("fusion_execute_python", {"script": (root / "examples" / example).read_text(), "read_only": True})
            if args.model:
                create = {"script": (root / "examples/create_mounting_plate.py").read_text(), "expected_document_id": report["before"]["data"]["document"]["id"], "operation_id": str(uuid.uuid4())}
                report["create"] = await call("fusion_execute_python", create)
                assert report["create"]["state"] == "succeeded", report["create"]
                report["duplicate"] = await call("fusion_execute_python", create)
                assert report["duplicate"] == report["create"]
                doc_id = report["create"]["result"]["data"]["document_id"]
                step_path = str((args.output / "mounting-plate.step").resolve())
                script = f'''import adsk.core, adsk.fusion, json, os
def run(context):
    design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    design.userParameters.itemByName("plate_thickness").expression = "8 mm"
    if not design.computeAll():
        raise RuntimeError("Recompute failed")
    body = design.rootComponent.bRepBodies.item(0)
    bb = body.boundingBox
    path = {step_path!r}
    if os.path.exists(path):
        raise RuntimeError("Export destination already exists")
    options = design.exportManager.createSTEPExportOptions(path)
    if not design.exportManager.execute(options):
        raise RuntimeError("STEP export failed")
    print(json.dumps({{"dimensions_cm": [bb.maxPoint.x-bb.minPoint.x, bb.maxPoint.y-bb.minPoint.y, bb.maxPoint.z-bb.minPoint.z], "volume_cm3": body.volume, "export": path}}))
'''
                report["edit_export"] = await call("fusion_execute_python", {"script": script, "expected_document_id": doc_id, "operation_id": str(uuid.uuid4())})
                assert report["edit_export"]["state"] == "succeeded", report["edit_export"]
                geometry = report["edit_export"]["result"]["data"]
                assert all(abs(a-b) < 1e-6 for a,b in zip(geometry["dimensions_cm"], [8,5,.8]))
                assert abs(geometry["volume_cm3"] - (40 - 4 * math.pi * .25**2) * .8) < 1e-6
                assert Path(step_path).stat().st_size > 1000
                report["after"] = await call("fusion_inspect")
                assert report["after"]["data"]["design"]["unhealthy_features"] == []
                screenshot = await session.call_tool("fusion_screenshot", {"width": 1000, "height": 700})
                assert not screenshot.isError, screenshot
                import base64
                images = [b for b in screenshot.content if b.type == "image"]
                report["screenshot_content_types"] = [b.type for b in screenshot.content]
                if images:
                    (args.output / "mounting-plate.png").write_bytes(base64.b64decode(images[0].data))
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": True, "tools": len(report["tools"]), "model_test": args.model, "report": str(args.output / "report.json")}))


if __name__ == "__main__":
    asyncio.run(main())
