"""Opt-in feature acceptance suite. Creates a dedicated document, never edits the user's model.

Pass an absolute or relative run directory. Successful steps are checkpointed, so a
development retry resumes without recreating them. Uncertain edits are NOT acknowledged.
"""
import json
import math
import sys
import time
import uuid
from pathlib import Path
from fusion_native_mcp.bridge import Bridge
from fusion_native_mcp.features import FeatureService

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
report_path = out / "features-report.json"
report = json.loads(report_path.read_text()) if report_path.exists() else {}
b = Bridge(out / "state")
s = FeatureService(b)


def save():
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def step(label, action, args, read=False):
    if label in report and report[label].get("passed"):
        return report[label]["data"]
    result = s.call(action, args, doc, str(uuid.uuid4()) if not read else None, read)
    if not read:
        if result["state"] != "succeeded":
            report[label] = {"passed": False, "operation": result}
            save()
            raise RuntimeError(json.dumps(result))
        result = result["result"]
    data = result["data"]
    assert data is not None, "Missing structured result; do not treat this as a passed step"
    report[label] = {"passed": True, "data": data}
    save()
    print(label, "passed", flush=True)
    return data


if "document" not in report:
    active = b.inspect()["data"]["document"]
    before = active["id"] if active else "__NO_DOCUMENT__"
    source = '''import adsk.core, json
def run(c):
    app=adsk.core.Application.get()
    d=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d.name='MCP Feature Acceptance'
    print(json.dumps({'id':d.creationId}))
'''
    result = b.execute(source, False, before, str(uuid.uuid4()))
    assert result["state"] == "succeeded", result
    report["document"] = result["result"]["data"]
    save()
doc = report["document"]["id"]

step("width_parameter", "parameter", {"name": "plate_width", "expression": "80 mm", "units": "mm"})
sk = step("constrained_rectangle", "sketch", {"shape": "rectangle", "name": "Plate Sketch", "component": "root", "plane": "xy", "width": "plate_width", "height": "50 mm"})
assert sk["fully_constrained"]

def feature_args(kind, refs, **kwargs):
    from fusion_native_mcp.features import FeatureSpec
    return FeatureSpec(kind=kind, entities=refs, **kwargs).model_dump()

step("extrude", "feature", feature_args("extrude", [sk["profile_references"][0]["token"]], name="Plate", distance="8 mm"))
from fusion_native_mcp.features import EntityQuery, AssemblySpec
body = step("body_query", "entities", EntityQuery(kind="bodies"), True)["items"][0]
faces = step("face_query", "entities", EntityQuery(kind="faces", scope=body["token"]), True)
assert len(faces["items"]) == 6
edges = step("edge_query", "entities", EntityQuery(kind="edges", scope=body["token"]), True)
vertical = [e for e in edges["items"] if abs(e["length_mm"]-8) < 1e-5]
assert len(vertical) == 4
step("fillet", "feature", feature_args("fillet", [e["token"] for e in vertical], name="Corner Fillets", distance="2 mm"))
step("parameter_edit", "parameter", {"name": "plate_width", "expression": "90 mm", "units": "mm"})
checks = step("geometry_validation", "validate", {"checks": [{"token": body["token"], "metric": "x", "expected": 90, "tolerance": 0.001}]}, True)
assert checks["healthy"] and checks["checks_passed"]
step("overview", "overview", {}, True)
component = step("component_create", "assembly", AssemblySpec(action="create_component", name="Spacer", translation_mm=(10,10,8)))
c_token = component["component"]["token"]
circle = step("constrained_circle", "sketch", {"shape": "circle", "name": "Spacer Profile", "component": c_token, "plane": "xy", "width": "10 mm", "height": "0 mm"})
step("spacer_extrude", "feature", feature_args("extrude", [circle["profile_references"][0]["token"]], component=c_token, distance="10 mm", name="Spacer Solid"))
copy = step("component_instance", "assembly", AssemblySpec(action="insert_component", source=c_token, translation_mm=(70,10,8)))
step("rigid_joint", "assembly", AssemblySpec(action="joint", one=component["token"], two=copy["token"], name="Spacers Joint"))
bom = step("bom", "bom", {}, True)
assert any(row["name"] == "Spacer" and row["quantity"] == 2 for row in bom["items"])
inter = step("interference", "interference", {"entities": [component["token"], copy["token"]]}, True)
assert inter["count"] == 0
step("step_export", "export", {"format": "step", "path": str(out / "assembly.step"), "entity": None})
step("dxf_export", "export", {"format": "dxf", "path": str(out / "plate.dxf"), "entity": sk["token"]})
setup = step("cam_setup", "cam_setup", {"models": [body["token"]], "name": "Acceptance Milling", "side_stock": "1 mm", "top_stock": "1 mm", "origin": "top center"})
url = "systemlibraryroot://Samples/Milling Tools (Metric).json"
tools = step("cam_tools", "tool_inventory", {"url": url, "offset": 0, "limit": 100}, True)
chosen = next(t for t in tools["tools"] if t["definition"].get("type") == "face mill")
op = step("cam_face", "cam_operation", {"setup_id": setup["id"], "strategy": "face", "name": "Acceptance Face", "tool_library_url": url,
    "tool_index": chosen["index"], "tool_fingerprint": chosen["fingerprint"], "expressions": {"tolerance": "0.01 mm", "stepover": "0.5 * tool_diameter"}})
job = step("cam_generation", "cam_generate", {"operation_ids": [op["id"]]})
deadline = time.monotonic()+120
while True:
    status = s.call("cam_job", {"job_id": job["job_id"]}, doc, read_only=True)["data"]
    if status["state"] != "running" or time.monotonic() > deadline:
        break
    time.sleep(1)
report["cam_job_result"] = status
save()
assert status["state"] == "succeeded", status
print("Feature acceptance suite passed", flush=True)
b.close()
