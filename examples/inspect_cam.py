"""Read-only CAM inventory. Setup/toolpath creation depends on the actual machining task."""
import json
import adsk.core
import adsk.cam


def run(context):
    doc = adsk.core.Application.get().activeDocument
    cam = next((adsk.cam.CAM.cast(p) for p in doc.products if adsk.cam.CAM.cast(p)), None)
    if not cam:
        print(json.dumps({"available": False, "reason": "No CAM product initialized in this document"}))
        return
    print(json.dumps({"available": True, "setups": [{"name": s.name} for s in cam.setups],
        "operations": [{"name": o.name} for o in cam.allOperations], "nc_programs": cam.ncPrograms.count}))
