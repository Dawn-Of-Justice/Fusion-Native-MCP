"""Read-only component, occurrence and joint inventory; does not activate a workspace."""
import json
import adsk.core
import adsk.fusion


def run(context):
    doc = adsk.core.Application.get().activeDocument
    design = next((adsk.fusion.Design.cast(p) for p in doc.products if adsk.fusion.Design.cast(p)), None)
    if not design:
        raise RuntimeError("No design in the active document")
    print(json.dumps({"components": [{"name": c.name, "bodies": c.bRepBodies.count,
        "joints": c.joints.count, "as_built_joints": c.asBuiltJoints.count} for c in design.allComponents],
        "occurrences": [{"path": o.fullPathName, "component": o.component.name} for o in design.rootComponent.allOccurrences]}))
