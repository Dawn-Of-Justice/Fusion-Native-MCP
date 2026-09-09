"""Create a separate two-component sample with an as-built rigid joint."""
import json
import adsk.core
import adsk.fusion


def run(context):
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name = "MCP Rigid Assembly Demo"
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    occurrences = []
    for name, z, width, depth, height in [("Base", 0, 4, 3, 0.5), ("Block", 0.5, 2, 2, 1)]:
        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(0, 0, z)
        occurrence = root.occurrences.addNewComponent(transform)
        occurrence.component.name = name
        component = occurrence.component
        sketch = component.sketches.add(component.xYConstructionPlane)
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(width, depth, 0))
        component.features.extrudeFeatures.addSimple(sketch.profiles.item(0), adsk.core.ValueInput.createByReal(height), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        sketch.isVisible = False
        occurrences.append(occurrence)
    joint_input = root.asBuiltJoints.createInput(occurrences[0], occurrences[1], None)
    joint_input.setAsRigidJointMotion()
    joint = root.asBuiltJoints.add(joint_input)
    joint.name = "Base to Block"
    app.activeViewport.fit()
    print(json.dumps({"document_id": doc.creationId, "occurrences": root.occurrences.count, "rigid_joints": root.asBuiltJoints.count}))
