"""Executed inside Fusion, never imported by the host server.

All boundary geometry uses millimeters. Entity tokens are resolved, never compared
for identity. Empty and ambiguous resolution both fail before feature creation.
"""
import json
import math
import os
import hashlib
from collections import Counter
import adsk.core as core
import adsk.fusion as fusion
import adsk.cam as cam_api


def design():
    doc = core.Application.get().activeDocument
    result = fusion.Design.cast(doc.products.itemByProductType("DesignProductType")) if doc else None
    if not result:
        raise ValueError("Active document has no Design product")
    return result


def resolve(token, expected=None):
    if token == "root":
        value = design().rootComponent
    else:
        found = design().findEntityByToken(token)
        valid = []
        for e in found:
            if e and e.isValid and not any(e == old for old in valid):
                valid.append(e)
        if len(valid) != 1:
            raise ValueError("STALE_OR_AMBIGUOUS_REFERENCE: query geometry again")
        value = valid[0]
    if expected and not expected.cast(value):
        raise ValueError("Reference has wrong type: " + value.objectType)
    return value


def collection(values):
    result = core.ObjectCollection.create()
    for value in values:
        result.add(value)
    return result


def point(xyz):
    return core.Point3D.create(*(v / 10 for v in xyz))


def xyz(value):
    return [value.x * 10, value.y * 10, value.z * 10]


def expr(value, units="mm", positive=False):
    manager = design().unitsManager
    if not manager.isValidExpression(value, units):
        raise ValueError("Invalid expression for " + units + ": " + value)
    number = manager.evaluateExpression(value, units)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError("Expression must evaluate to a finite positive value")
    return core.ValueInput.createByString(value)


def ref(value):
    if fusion.Occurrence.cast(value):
        value = root_occurrence(value)
    result = {"type": value.objectType}
    if hasattr(value, "entityToken"):
        result["token"] = value.entityToken
    if hasattr(value, "name"):
        result["name"] = value.name
    return result


def describe(value):
    if fusion.Occurrence.cast(value):
        value = root_occurrence(value)
    result = ref(value)
    if hasattr(value, "boundingBox"):
        box = value.boundingBox
        result["bounds_mm"] = {"min": xyz(box.minPoint), "max": xyz(box.maxPoint)}
    if fusion.BRepBody.cast(value):
        result.update(volume_mm3=value.volume * 1000, solid=value.isSolid,
                      faces=value.faces.count, edges=value.edges.count)
    if fusion.BRepFace.cast(value):
        result.update(area_mm2=value.area * 100, point_on_face_mm=xyz(value.pointOnFace))
        shape = value.geometry
        result["surface_type"] = shape.objectType
        if core.Cylinder.cast(shape):
            result.update(radius_mm=shape.radius * 10, axis=list(shape.axis.asArray()), origin_mm=xyz(shape.origin))
        if core.Plane.cast(shape):
            result["plane_normal"] = list(shape.normal.asArray())
    if fusion.BRepEdge.cast(value):
        result.update(length_mm=value.length * 10, curve_type=value.geometry.objectType)
    if fusion.Sketch.cast(value):
        result.update(fully_constrained=value.isFullyConstrained, profiles=value.profiles.count,
                      dimensions=[{"name": d.parameter.name, "expression": d.parameter.expression} for d in value.sketchDimensions])
    if fusion.Profile.cast(value):
        result["area_mm2"] = value.areaProperties().area * 100
    if fusion.Occurrence.cast(value):
        result.update(path=value.fullPathName, component=ref(value.component), transform=list(value.transform2.asArray()))
        result["transform_units"] = "translation in centimeters"
    if hasattr(value, "healthState"):
        result.update(health=int(value.healthState), diagnostic=value.errorOrWarningMessage)
    return result


def entities(p):
    d = design()
    kind = p["kind"]
    scope = resolve(p["scope"]) if p.get("scope") else None
    if kind in ("faces", "edges"):
        body = resolve(p["scope"], fusion.BRepBody)
        source = getattr(body, kind)
    elif kind in ("profiles", "sketch_curves", "sketch_points"):
        sketch = resolve(p["scope"], fusion.Sketch)
        source = getattr(sketch, {"profiles": "profiles", "sketch_curves": "sketchCurves", "sketch_points": "sketchPoints"}[kind])
    elif kind == "features":
        source = (item.entity for item in d.timeline)
    elif kind == "components":
        source = d.allComponents
    elif kind == "occurrences":
        source = (scope or d.rootComponent).allOccurrences
    else:
        if scope and fusion.Occurrence.cast(scope) and kind == "bodies":
            source = scope.bRepBodies
            components = []
        else:
            components = [scope.component if scope and fusion.Occurrence.cast(scope) else scope] if scope else d.allComponents
        attr = {"bodies": "bRepBodies", "sketches": "sketches", "joints": "joints", "as_built_joints": "asBuiltJoints"}[kind]
        if components:
            source = (obj for c in components for obj in getattr(c, attr))
    results, matched = [], 0
    for obj in source:
        if not obj or not obj.isValid:
            continue
        if p.get("name") is not None and getattr(obj, "name", None) != p["name"]:
            continue
        item = describe(obj)
        if p.get("surface_type") and not item.get("surface_type", "").endswith("::" + p["surface_type"]):
            continue
        if p.get("radius_mm") is not None and abs(item.get("radius_mm", -1e100) - p["radius_mm"]) > p["tolerance_mm"]:
            continue
        if matched >= p["offset"]:
            results.append(item)
        matched += 1
        if len(results) > p["limit"]:
            return {"items": results[:p["limit"]], "next_offset": p["offset"] + p["limit"], "coordinate_space": "entity context; native component unless a proxy was supplied"}
    return {"items": results, "next_offset": None, "coordinate_space": "entity context; native component unless a proxy was supplied"}


def overview(p):
    d = design()
    return {"document_id": core.Application.get().activeDocument.creationId,
            "parameters": [{"name": v.name, "expression": v.expression, "unit": v.unit, "comment": v.comment} for v in d.allParameters],
            "timeline": [{"index": t.index, "name": t.name, "entity": ref(t.entity) if t.entity else None,
                          "health": int(t.healthState), "diagnostic": t.errorOrWarningMessage} for t in d.timeline],
            "components": [dict(ref(c), body_count=c.bRepBodies.count, sketch_count=c.sketches.count) for c in d.allComponents]}


def parameter(p):
    d = design()
    value = d.allParameters.itemByName(p["name"])
    if value and fusion.ModelParameter.cast(value):
        if not p.get("component"):
            raise ValueError("Model parameter edits require an explicit component; use component-context inspection first")
        owner = editable_component(p["component"], p.get("allow_shared_definition_edit", False))
        if owner.modelParameters.itemByName(p["name"]) != value:
            raise ValueError("PARAMETER_OUTSIDE_TARGET")
    units = value.unit if value else p["units"]
    expr(p["expression"], units)
    if value:
        value.expression = p["expression"]
    else:
        value = d.userParameters.add(p["name"], core.ValueInput.createByString(p["expression"]), units, p.get("comment", ""))
    if not d.computeAll():
        raise RuntimeError("Parameter changed but recompute failed; inspect feature health")
    return {"name": value.name, "expression": value.expression, "unit": value.unit}


def plane(component, name):
    return {"xy": component.xYConstructionPlane, "xz": component.xZConstructionPlane, "yz": component.yZConstructionPlane}[name]


def sketch_create(p):
    component = editable_component(p["component"], p.get("allow_shared_definition_edit", False))
    width = expr(p["width"], positive=True)
    height = expr(p["height"], positive=True) if p["shape"] == "rectangle" else None
    support = plane(component, p["plane"])
    offset = p.get("offset", "0 mm")
    offset_value = expr(offset)
    if abs(design().unitsManager.evaluateExpression(offset, "mm")) > 1e-10:
        plane_input = component.constructionPlanes.createInput()
        plane_input.setByOffset(support, offset_value)
        support = component.constructionPlanes.add(plane_input)
    s = component.sketches.add(support)
    s.name = p["name"]
    dims = s.sketchDimensions
    if p["shape"] == "rectangle":
        w = design().unitsManager.evaluateExpression(p["width"], "mm")
        h = design().unitsManager.evaluateExpression(p["height"], "mm")
        lines = s.sketchCurves.sketchLines.addTwoPointRectangle(core.Point3D.create(0, 0, 0), core.Point3D.create(w, h, 0))
        # Rectangle adds horizontal/vertical and endpoint coincidence constraints.
        # Ground only the origin corner; dimensions remain editable.
        lines.item(0).startSketchPoint.isFixed = True
        a = dims.addDistanceDimension(lines.item(0).startSketchPoint, lines.item(0).endSketchPoint,
            fusion.DimensionOrientations.HorizontalDimensionOrientation, core.Point3D.create(w/2, -h/4, 0))
        a.parameter.expression = p["width"]
        b = dims.addDistanceDimension(lines.item(1).startSketchPoint, lines.item(1).endSketchPoint,
            fusion.DimensionOrientations.VerticalDimensionOrientation, core.Point3D.create(w*1.2, h/2, 0))
        b.parameter.expression = p["height"]
    else:
        r = design().unitsManager.evaluateExpression(p["width"], "mm") / 2
        circle = s.sketchCurves.sketchCircles.addByCenterRadius(core.Point3D.create(0, 0, 0), r)
        circle.centerSketchPoint.isFixed = True
        dims.addDiameterDimension(circle, core.Point3D.create(r*2, r*2, 0)).parameter.expression = p["width"]
    design().computeAll()
    if not s.isFullyConstrained and hasattr(s, "autoConstrain"):
        auto_input = s.createAutoConstrainInput()
        auto_input.datumPoint = s.originPoint
        auto_input.resultOption = fusion.AutoConstrainResultTypes.Option2AutoConstrainResultType
        s.autoConstrain(auto_input)
    if not s.isFullyConstrained:
        raise RuntimeError("Sketch created but not fully constrained; inspect before continuing")
    return dict(describe(s), profile_references=[ref(v) for v in s.profiles])


def constrain(p):
    s = resolve(p["sketch"], fusion.Sketch)
    editable_component(s.parentComponent.entityToken, p.get("allow_shared_definition_edit", False))
    if not hasattr(s, "autoConstrain"):
        raise RuntimeError("AutoConstrain is unavailable in this Fusion version")
    input_value = s.createAutoConstrainInput()
    input_value.datumPoint = s.originPoint
    input_value.resultOption = fusion.AutoConstrainResultTypes.Option2AutoConstrainResultType
    result = s.autoConstrain(input_value)
    return {"sketch": describe(s), "fully_constrained": result.isFullyConstrained}


def axis(component, name):
    return {"x": component.xConstructionAxis, "y": component.yConstructionAxis, "z": component.zConstructionAxis}[name]


def feature(p):
    c = editable_component(p["component"], p.get("allow_shared_definition_edit", False))
    f = c.features
    kind = p["kind"]
    refs = [owned_entity(resolve(t), c) for t in p["entities"]]
    if not refs:
        raise ValueError("At least one entity required")
    operation = {"new_body": fusion.FeatureOperations.NewBodyFeatureOperation, "join": fusion.FeatureOperations.JoinFeatureOperation,
                 "cut": fusion.FeatureOperations.CutFeatureOperation, "intersect": fusion.FeatureOperations.IntersectFeatureOperation}[p["operation"]]
    primary = refs[0] if len(refs) == 1 else collection(refs)
    if kind == "extrude":
        result = f.extrudeFeatures.addSimple(primary, expr(p["distance"]), operation)
    elif kind == "revolve":
        inp = f.revolveFeatures.createInput(primary, owned_entity(resolve(p["axis_token"]), c) if p.get("axis_token") else axis(c, p["axis"]), operation)
        inp.setAngleExtent(False, expr(p["angle"], "deg", True))
        result = f.revolveFeatures.add(inp)
    elif kind == "fillet":
        inp = f.filletFeatures.createInput()
        inp.edgeSetInputs.addConstantRadiusEdgeSet(collection(refs), expr(p["distance"], positive=True), True)
        result = f.filletFeatures.add(inp)
    elif kind == "chamfer":
        inp = f.chamferFeatures.createInput2()
        inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(collection(refs), expr(p["distance"], positive=True), True)
        result = f.chamferFeatures.add(inp)
    elif kind == "shell":
        inp = f.shellFeatures.createInput(collection(refs), True)
        inp.insideThickness = expr(p["distance"], positive=True)
        result = f.shellFeatures.add(inp)
    elif kind == "combine":
        if len(refs) < 2 or p["operation"] == "new_body":
            raise ValueError("Combine requires target plus tool bodies and join/cut/intersect")
        inp = f.combineFeatures.createInput(refs[0], collection(refs[1:]))
        inp.operation = operation
        inp.isKeepToolBodies = p["keep_tools"]
        result = f.combineFeatures.add(inp)
    elif kind == "loft":
        if len(refs) < 2:
            raise ValueError("Loft requires at least two ordered profile sections")
        inp = f.loftFeatures.createInput(operation)
        for r in refs:
            inp.loftSections.add(r)
        result = f.loftFeatures.add(inp)
    elif kind == "sweep":
        path = f.createPath(owned_entity(resolve(p["path_token"]), c))
        inp = f.sweepFeatures.createInput(primary, path, operation)
        result = f.sweepFeatures.add(inp)
    elif kind == "rectangular_pattern":
        inp = f.rectangularPatternFeatures.createInput(collection(refs), axis(c, p["axis"]),
            core.ValueInput.createByReal(p["quantity"]), expr(p["distance"], positive=True), fusion.PatternDistanceType.SpacingPatternDistanceType)
        result = f.rectangularPatternFeatures.add(inp)
    elif kind == "circular_pattern":
        inp = f.circularPatternFeatures.createInput(collection(refs), axis(c, p["axis"]))
        inp.quantity = core.ValueInput.createByReal(p["quantity"])
        inp.totalAngle = expr(p["angle"], "deg", True)
        result = f.circularPatternFeatures.add(inp)
    else:
        raise ValueError("Unsupported feature")
    if not result:
        raise RuntimeError("Fusion returned no feature")
    result.name = p["name"]
    return describe(result)


def holes(p):
    c = editable_component(p["component"], p.get("allow_shared_definition_edit", False))
    points = [owned_entity(resolve(t, fusion.SketchPoint), c) for t in p["points"]]
    diameter = expr(p["diameter"], positive=True)
    depth = expr(p["depth"], positive=True)
    inp = c.features.holeFeatures.createSimpleInput(diameter)
    inp.setPositionBySketchPoints(collection(points))
    inp.setDistanceExtent(depth)
    value = c.features.holeFeatures.add(inp)
    value.name = p["name"]
    return describe(value)


def validate(p):
    d = design()
    if p.get("recompute") and not d.computeAll():
        raise RuntimeError("Recompute failed; read health report")
    problems = [{"name": t.name, "index": t.index, "diagnostic": t.errorOrWarningMessage} for t in d.timeline if t.healthState != fusion.FeatureHealthStates.HealthyFeatureHealthState]
    sketches = [describe(s) for c in d.allComponents for s in c.sketches if not s.isFullyConstrained]
    measurements = []
    for check in p.get("checks", []):
        obj = resolve(check["token"], fusion.BRepBody)
        box = obj.boundingBox
        actual = {"x": (box.maxPoint.x-box.minPoint.x)*10, "y": (box.maxPoint.y-box.minPoint.y)*10,
                  "z": (box.maxPoint.z-box.minPoint.z)*10, "volume": obj.volume*1000}[check["metric"]]
        measurements.append(dict(check, actual=actual, passed=abs(actual-check["expected"]) <= check["tolerance"]))
    return {"healthy": not problems, "feature_problems": problems, "underconstrained_sketches": sketches, "measurements": measurements,
            "checks_passed": all(c["passed"] for c in measurements)}


def interference(p):
    items = collection([resolve(t) for t in p["entities"]])
    inp = design().createInterferenceInput(items)
    inp.areCoincidentFacesIncluded = False
    results = design().analyzeInterference(inp)
    return {"count": results.count, "pairs": [{"one": ref(v.entityOne), "two": ref(v.entityTwo)} for v in results]}


def assembly(p):
    c = editable_component(p["component"], p.get("allow_shared_definition_edit", False))
    if p["action"] == "create_component":
        transform = core.Matrix3D.create()
        transform.translation = core.Vector3D.create(*(v/10 for v in p["translation_mm"]))
        value = c.occurrences.addNewComponent(transform)
        value.component.name = p["name"]
        return describe(value)
    if p["action"] == "insert_component":
        source = resolve(p["source"], fusion.Component)
        transform = core.Matrix3D.create()
        transform.translation = core.Vector3D.create(*(v/10 for v in p["translation_mm"]))
        return describe(c.occurrences.addExistingComponent(source, transform))
    one, two = resolve(p["one"], fusion.Occurrence), resolve(p["two"], fusion.Occurrence)
    geometry = None
    if p["motion"] != "rigid":
        geometry = fusion.JointGeometry.createByPoint(resolve(p["origin_token"]))
    inp = c.asBuiltJoints.createInput(one, two, geometry)
    direction = {"x": fusion.JointDirections.XAxisJointDirection, "y": fusion.JointDirections.YAxisJointDirection, "z": fusion.JointDirections.ZAxisJointDirection}[p["axis"]]
    if p["motion"] == "rigid":
        inp.setAsRigidJointMotion()
    elif p["motion"] == "revolute":
        inp.setAsRevoluteJointMotion(direction)
    else:
        inp.setAsSliderJointMotion(direction)
    value = c.asBuiltJoints.add(inp)
    value.name = p["name"]
    if p.get("minimum") is not None or p.get("maximum") is not None:
        motion = value.jointMotion
        limits = motion.rotationLimits if p["motion"] == "revolute" else motion.slideLimits
        convert = math.radians if p["motion"] == "revolute" else lambda x: x/10
        if p.get("minimum") is not None:
            limits.minimumValue = convert(p["minimum"])
            limits.isMinimumValueEnabled = True
        if p.get("maximum") is not None:
            limits.maximumValue = convert(p["maximum"])
            limits.isMaximumValueEnabled = True
    return describe(value)


def bom(p):
    d = design()
    # Count object identity rather than token strings or names.
    rows = []
    for c in d.allComponents:
        if c == d.rootComponent:
            continue
        quantity = sum(o.component == c for o in d.rootComponent.allOccurrences)
        rows.append(dict(ref(c), part_number=c.partNumber, description=c.description, quantity=quantity))
    return {"items": rows, "scope": "flattened occurrences, including nested components"}


def export_file(p):
    path = os.path.abspath(p["path"])
    if not os.path.isdir(os.path.dirname(path)):
        raise ValueError("Export parent directory must exist")
    if os.path.exists(path):
        raise ValueError("Export destination exists; choose a new path")
    d = design()
    fmt = p["format"]
    geometry = resolve(p["entity"]) if p.get("entity") else d.rootComponent
    if fmt == "bom_json":
        with open(path, "x", encoding="utf-8") as stream:
            json.dump(bom({}), stream, indent=2)
    else:
        manager = d.exportManager
        if fmt == "step":
            opts = manager.createSTEPExportOptions(path, geometry)
        elif fmt == "f3d":
            opts = manager.createFusionArchiveExportOptions(path)
        elif fmt == "stl":
            opts = manager.createSTLExportOptions(geometry, path)
            opts.sendToPrintUtility = False
        else:
            opts = manager.createDXFSketchExportOptions(path, geometry)
        if not manager.execute(opts):
            raise RuntimeError("Export failed")
    return {"path": path, "bytes": os.path.getsize(path)}


HANDLERS = {"entities": entities, "overview": overview, "parameter": parameter, "sketch": sketch_create,
            "constrain": constrain, "feature": feature, "holes": holes, "validate": validate,
            "interference": interference, "assembly": assembly, "bom": bom, "export": export_file}
