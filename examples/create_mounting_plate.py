"""Creates a separate sample document. API numeric lengths below are centimeters.

Plate dimensions: 80 x 50 mm; thickness is a user parameter. Four 5 mm holes.
The rectangle and hole positions remain editable sketch geometry, not fully constrained.
"""
import json
import adsk.core
import adsk.fusion


def run(context):
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name = "MCP Mounting Plate Demo"
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    design.userParameters.add("plate_thickness", adsk.core.ValueInput.createByString("6 mm"), "mm", "MCP demo plate thickness")
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = "Plate Outline"
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(8, 5, 0))
    extrudes = root.features.extrudeFeatures
    plate = extrudes.addSimple(sketch.profiles.item(0), adsk.core.ValueInput.createByString("plate_thickness"), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    plate.name = "Plate Thickness"
    plate.bodies.item(0).name = "Mounting Plate"
    holes = root.sketches.add(root.xYConstructionPlane)
    holes.name = "Mounting Holes"
    for x, y in [(1, 1), (7, 1), (7, 4), (1, 4)]:
        holes.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(x, y, 0), 0.25)
    profiles = adsk.core.ObjectCollection.create()
    for profile in holes.profiles:
        profiles.add(profile)
    cut = extrudes.addSimple(profiles, adsk.core.ValueInput.createByString("plate_thickness"), adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut.name = "Four Mounting Holes"
    sketch.isVisible = False
    holes.isVisible = False
    app.activeViewport.fit()
    print(json.dumps({"document_id": doc.creationId, "name": doc.name, "bodies": root.bRepBodies.count}))
