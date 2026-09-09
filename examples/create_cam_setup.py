"""Create a milling setup on the sample plate; no toolpaths or machine code.

Stock/WCS use Fusion defaults. This is an API integration test, not a machining plan.
"""
import json
import adsk.core
import adsk.fusion
import adsk.cam


def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if doc.name != "MCP Mounting Plate Demo":
        raise RuntimeError("Run this example only on the MCP Mounting Plate Demo")
    design = next((adsk.fusion.Design.cast(p) for p in doc.products if adsk.fusion.Design.cast(p)), None)
    if not design or design.rootComponent.bRepBodies.count != 1:
        raise RuntimeError("Expected exactly one plate body")
    workspace = app.userInterface.workspaces.itemById("CAMEnvironment")
    if not workspace:
        raise RuntimeError("Manufacture workspace unavailable")
    if not workspace.isActive and not workspace.activate():
        raise RuntimeError("Could not activate Manufacture workspace")
    cam = adsk.cam.CAM.cast(app.activeProduct)
    if not cam:
        raise RuntimeError("CAM product not ready; inspect before retrying")
    setup_input = cam.setups.createInput(adsk.cam.OperationTypes.MillingOperation)
    setup_input.name = "MCP Milling Setup Demo"
    setup_input.models = [design.rootComponent.bRepBodies.item(0)]
    setup = cam.setups.add(setup_input)
    print(json.dumps({"name": setup.name, "setups": cam.setups.count, "operations": cam.allOperations.count}))
