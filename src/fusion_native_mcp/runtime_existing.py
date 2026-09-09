"""Explicit assembly-context inspection and component-scoped existing-model edits."""


def occurrence_at(path):
    matches = [o for o in design().rootComponent.allOccurrences if o.fullPathName == path]
    if len(matches) != 1:
        raise ValueError("OCCURRENCE_PATH_NOT_UNIQUE: supply an exact full path from the assembly tree")
    return matches[0]


def root_occurrence(value):
    # Native nested occurrences cannot produce tokens. Resolve their root-context
    # proxy before returning an actionable reference to the client.
    all_occurrences = list(design().rootComponent.allOccurrences)
    for candidate in all_occurrences:
        if candidate == value:
            return candidate
    native = value.nativeObject or value
    matches = [o for o in all_occurrences if (o.nativeObject or o) == native]
    if len(matches) != 1:
        raise ValueError("AMBIGUOUS_OCCURRENCE_CONTEXT: query the exact root-context path")
    return matches[0]


def component_instances(component):
    return [o for o in design().rootComponent.allOccurrences if o.component == component]


def is_external_context(occurrence):
    for o in design().rootComponent.allOccurrences:
        if o.isReferencedComponent and (o == occurrence or occurrence.fullPathName.startswith(o.fullPathName + "+")):
            return True
    return False


def editable_component(token, allow_shared=False):
    component = resolve(token, fusion.Component)
    instances = component_instances(component)
    if any(is_external_context(o) for o in instances):
        raise ValueError("EXTERNAL_COMPONENT: edit the source design; this tool will not break links")
    if len(instances) > 1 and not allow_shared:
        raise ValueError("SHARED_DEFINITION: this change affects multiple occurrences; inspect context and explicitly enable shared-definition editing")
    return component


def definition_state(component):
    # Tokens are not hashes/identity strings: exclude them from the state fingerprint.
    state = {"name": component.name,
        "parameters": sorted([{"name": p.name, "expression": p.expression, "unit": p.unit} for p in component.modelParameters], key=lambda p: p["name"]),
        "bodies": [{"name": b.name, "volume_mm3": round(b.volume*1000, 7), "faces": b.faces.count, "edges": b.edges.count,
                    "bounds_mm": {"min": xyz(b.boundingBox.minPoint), "max": xyz(b.boundingBox.maxPoint)}} for b in component.bRepBodies],
        "sketches": [{"name": s.name, "curves": s.sketchCurves.count, "constrained": s.isFullyConstrained} for s in component.sketches]}
    digest = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return state, digest


def owned_entity(entity, component):
    native = getattr(entity, "nativeObject", None) or entity
    if fusion.Profile.cast(native):
        owner = native.parentSketch.parentComponent
    elif fusion.BRepFace.cast(native) or fusion.BRepEdge.cast(native):
        owner = native.body.parentComponent
    elif fusion.SketchEntity.cast(native):
        owner = native.parentSketch.parentComponent
    else:
        owner = getattr(native, "parentComponent", None)
    if owner is None or owner != component:
        raise ValueError("ENTITY_OUTSIDE_TARGET_COMPONENT: choose the owning component and inspect shared instances")
    return native


def assembly_tree(p):
    root = design().rootComponent
    all_items = list(root.allOccurrences)
    page = all_items[p["offset"]:p["offset"]+p["limit"]]
    return {"root": ref(root), "total_occurrences": len(all_items),
        "items": [{"path": o.fullPathName, "parent_path": o.fullPathName.rsplit("+", 1)[0] if "+" in o.fullPathName else None,
                   "occurrence": ref(o), "component": ref(o.component), "external": is_external_context(o),
                   "shared_instance_count": len(component_instances(o.component)), "grounded": o.isGrounded,
                   "visible": o.isVisible} for o in page],
        "next_offset": p["offset"]+p["limit"] if p["offset"]+p["limit"] < len(all_items) else None}


def component_context(p):
    occurrence = occurrence_at(p["path"])
    c = occurrence.component
    state, digest = definition_state(c)
    instances = component_instances(c)
    return {"path": occurrence.fullPathName, "component": ref(c), "occurrence": ref(occurrence),
            "external": is_external_context(occurrence), "affected_occurrence_paths": [o.fullPathName for o in instances],
            "definition_fingerprint": digest, "definition": state,
            "native_bodies": [describe(b) for b in c.bRepBodies],
            "occurrence_bodies": [describe(b) for b in occurrence.bRepBodies],
            "coordinate_notes": "native_bodies use component-local coordinates; occurrence_bodies use the supplied assembly context",
            "model_parameters": [{"name": v.name, "expression": v.expression, "unit": v.unit,
                "role": v.role, "created_by": ref(v.createdBy) if v.createdBy else None} for v in c.modelParameters]}


def edit_existing_parameters(p):
    occurrence = occurrence_at(p["path"])
    c = occurrence.component
    expected = resolve(p["expected_component"], fusion.Component)
    if expected != c:
        raise ValueError("COMPONENT_CHANGED: the path now refers to a different component")
    editable_component(p["expected_component"], p["allow_shared_definition_edit"])
    state, digest = definition_state(c)
    if digest != p["expected_fingerprint"]:
        raise ValueError("STALE_COMPONENT_STATE: inspect this component again before editing")
    parameters = []
    for name, expression in p["expressions"].items():
        value = c.modelParameters.itemByName(name)
        if not value:
            raise ValueError("PARAMETER_OUTSIDE_TARGET: " + name)
        expr(expression, value.unit)
        parameters.append((value, expression))
    before_errors = {(t.index, t.errorOrWarningMessage) for t in design().timeline if t.healthState != fusion.FeatureHealthStates.HealthyFeatureHealthState}
    for value, expression in parameters:
        value.expression = expression
    if not design().computeAll():
        raise RuntimeError("Edited parameters but recompute failed")
    after_errors = {(t.index, t.errorOrWarningMessage) for t in design().timeline if t.healthState != fusion.FeatureHealthStates.HealthyFeatureHealthState}
    if after_errors - before_errors:
        raise RuntimeError("Edit introduced new feature diagnostics: " + repr(after_errors-before_errors))
    new_state, new_digest = definition_state(c)
    return {"path": p["path"], "affected_occurrence_paths": [o.fullPathName for o in component_instances(c)],
            "before": state, "after": new_state, "definition_fingerprint": new_digest}


HANDLERS.update({"assembly_tree": assembly_tree, "component_context": component_context,
                 "edit_existing_parameters": edit_existing_parameters})
