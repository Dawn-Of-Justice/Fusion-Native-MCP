"""CAM and drawing handlers; concatenated with runtime.py inside Fusion."""
import adsk
import uuid


def cam(activate=False):
    app = core.Application.get()
    if activate:
        workspace = app.userInterface.workspaces.itemById("CAMEnvironment")
        if not workspace:
            raise RuntimeError("Manufacture workspace unavailable")
        if not workspace.isActive and not workspace.activate():
            raise RuntimeError("Could not activate Manufacture workspace")
    return cam_api.CAM.cast(app.activeDocument.products.itemByProductType("CAMProductType"))


def cam_object(oid, objects=None):
    items = objects if objects is not None else cam().allOperations
    matches = [v for v in items if str(v.operationId) == str(oid)]
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous CAM operation ID")
    return matches[0]


def cam_info(value):
    result = {"id": str(value.operationId), "name": value.name, "type": value.objectType,
              "has_error": value.hasError, "has_warning": value.hasWarning, "error": value.error, "warning": value.warning}
    if cam_api.Operation.cast(value):
        result.update(generating=value.isGenerating, has_toolpath=value.hasToolpath, valid=value.isToolpathValid,
                      strategy=value.strategy)
    return result


def cam_inventory(p):
    product = cam()
    return {"setups": [cam_info(s) for s in product.setups], "operations": [cam_info(o) for o in product.allOperations],
            "nc_programs": [cam_info(n) for n in product.ncPrograms]}


def library_browse(p):
    manager = cam_api.CAMManager.get().libraryManager
    library = manager.toolLibraries if p["kind"] == "tools" else manager.postLibrary
    url = core.URL.create(p["url"]) if p.get("url") else library.urlByLocation(cam_api.LibraryLocations.Fusion360LibraryLocation)
    return {"url": url.toString(), "folders": [u.toString() for u in library.childFolderURLs(url)],
            "assets": [u.toString() for u in library.childAssetURLs(url)]}


def tool_inventory(p):
    library = cam_api.CAMManager.get().libraryManager.toolLibraries.toolLibraryAtURL(core.URL.create(p["url"]))
    if not library:
        raise ValueError("Tool library not found")
    result = []
    end = min(library.count, p["offset"] + p["limit"])
    for index in range(p["offset"], end):
        tool = library.item(index)
        data = tool.toJson()
        result.append({"index": index, "fingerprint": hashlib.sha256(data.encode()).hexdigest(), "definition": json.loads(data)})
    return {"tools": result, "next_offset": end if end < library.count else None}


def cam_setup(p):
    models = [resolve(t) for t in p["models"]]
    for key in ("side_stock", "top_stock"):
        expr(p[key])
    product = cam(True)
    inp = product.setups.createInput(cam_api.OperationTypes.MillingOperation)
    inp.name = p["name"]
    inp.models = models
    inp.stockMode = cam_api.SetupStockModes.RelativeBoxStock
    for key, value in {"job_stockOffsetMode": "'simple'", "job_stockOffsetSides": p["side_stock"], "job_stockOffsetTop": p["top_stock"]}.items():
        param = inp.parameters.itemByName(key)
        if not param:
            raise ValueError("Unsupported setup parameter: " + key)
        param.expression = value
    inp.parameters.itemByName("wcs_origin_boxPoint").value.value = p["origin"]
    return cam_info(product.setups.add(inp))


def cam_parameters(p):
    value = cam_object(p["id"], cam().setups if p["setup"] else None)
    return {"parameters": [{"name": v.name, "expression": v.expression} for v in value.parameters]}


def cam_operation(p):
    setup = cam_object(p["setup_id"], cam().setups)
    library = cam_api.CAMManager.get().libraryManager.toolLibraries.toolLibraryAtURL(core.URL.create(p["tool_library_url"]))
    if not library or p["tool_index"] >= library.count:
        raise ValueError("Tool library/index unavailable")
    tool = library.item(p["tool_index"])
    if hashlib.sha256(tool.toJson().encode()).hexdigest() != p["tool_fingerprint"]:
        raise ValueError("Tool definition changed; inspect library and select again")
    inp = setup.operations.createInput(p["strategy"])
    if not inp:
        raise ValueError("Strategy is unavailable in this setup/license")
    inp.tool = tool
    inp.displayName = p["name"]
    # Validate all parameter names before creating the persistent operation.
    for key in p["expressions"]:
        if not inp.parameters.itemByName(key):
            raise ValueError("Unknown operation parameter: " + key)
    for key, value in p["expressions"].items():
        inp.parameters.itemByName(key).expression = value
    return cam_info(setup.operations.add(inp))


def cam_generate(p):
    product = cam()
    operations = [cam_object(v) for v in p["operation_ids"]]
    if any(v.isGenerating for v in operations):
        raise ValueError("An operation is already generating")
    future = product.generateToolpath(collection(operations))
    if not hasattr(adsk, "_fusion_native_mcp_jobs"):
        adsk._fusion_native_mcp_jobs = {}
    job_id = str(uuid.uuid4())
    adsk._fusion_native_mcp_jobs[job_id] = (core.Application.get().activeDocument.creationId, future, p["operation_ids"])
    return {"job_id": job_id, "state": "submitted", "operation_ids": p["operation_ids"]}


def cam_job(p):
    jobs = getattr(adsk, "_fusion_native_mcp_jobs", {})
    record = jobs.get(p["job_id"])
    if record is None:
        return {"state": "unknown", "reason": "Job handle absent, possibly after Fusion restart; inspect operation state without resubmitting"}
    doc_id, future, ids = record
    if doc_id != core.Application.get().activeDocument.creationId:
        raise ValueError("Job belongs to a different document")
    states = [cam_info(cam_object(v)) for v in ids]
    complete = future.isGenerationCompleted
    valid = complete and all(v["valid"] and v["has_toolpath"] and not v["has_error"] for v in states)
    return {"state": "succeeded" if valid else "failed" if complete else "running",
            "completed": future.numberOfCompleted, "total": future.numberOfOperations, "operations": states}


def nc_create(p):
    product = cam()
    operations = [cam_object(v) for v in p["operation_ids"]]
    if any(not o.isToolpathValid or not o.hasToolpath or o.hasError for o in operations):
        raise ValueError("All selected operations must have valid toolpaths without errors")
    post = cam_api.CAMManager.get().libraryManager.postLibrary.postConfigurationAtURL(core.URL.create(p["post_url"]))
    if not post:
        raise ValueError("Explicit post configuration URL not found")
    folder = os.path.abspath(p["output_folder"])
    if not os.path.isdir(folder) or os.listdir(folder):
        raise ValueError("NC output folder must exist and be empty")
    inp = product.ncPrograms.createInput()
    inp.displayName = p["name"]
    inp.operations = operations
    inp.parameters.itemByName("nc_program_filename").value.value = p["filename"]
    inp.parameters.itemByName("nc_program_output_folder").value.value = folder.replace('\\', '/')
    inp.parameters.itemByName("nc_program_openInEditor").value.value = False
    program = product.ncPrograms.add(inp)
    program.postConfiguration = post
    return dict(cam_info(program), post_url=p["post_url"], output_folder=folder, post_processed=False)


def nc_post(p):
    program = cam_object(p["program_id"], cam().ncPrograms)
    if not program.postConfiguration:
        raise ValueError("NC program has no selected post")
    for op in program.operations:
        if not cam_api.Operation.cast(op) or not op.hasToolpath or not op.isToolpathValid or op.hasError:
            raise ValueError("NC operation is not ready for post-processing")
    folder = program.parameters.itemByName("nc_program_output_folder").value.value
    if not os.path.isdir(folder) or os.listdir(folder):
        raise ValueError("Output folder is not empty; refusing possible overwrite")
    result = program.postProcess(cam_api.NCProgramPostProcessOptions.create())
    return {"accepted": bool(result), "application_has_active_jobs": core.Application.get().hasActiveJobs,
            "output_folder": folder, "files_present": os.listdir(folder),
            "note": "Post acceptance is not machine validation; inspect output and job completion"}


def drawing_create(p):
    import adsk.drawing as drawing
    doc = core.Application.get().activeDocument
    if not doc.isSaved or not doc.dataFile:
        raise ValueError("Drawing creation requires an explicitly saved cloud design")
    manager = drawing.DrawingManager.get()
    inp = manager.createDrawingInput(doc.dataFile, drawing.DrawingCreationModes.AutomaticDrawingCreationMode)
    inp.baseDocumentType = drawing.BaseDocumentTypes.FromScratchBaseDocumentType
    inp.standard = getattr(drawing.DrawingStandardTypes, p["standard"])
    inp.units = getattr(drawing.DrawingUnitTypes, p["units"])
    inp.sheetSize = getattr(drawing.SheetSizes, p["sheet_size"])
    inp.automationPreferences.globalPreferences.isAutoDimensionEnabled = p["dimensions"]
    output = manager.createDrawing(inp)
    return {"created": bool(output), "file_id": output.id if output else None,
            "note": "Drawing generation may be a cloud job; inspect the resulting drawing before release"}


HANDLERS.update({"cam_inventory": cam_inventory, "library_browse": library_browse, "tool_inventory": tool_inventory,
                 "cam_setup": cam_setup, "cam_parameters": cam_parameters, "cam_operation": cam_operation,
                 "cam_generate": cam_generate, "cam_job": cam_job, "nc_create": nc_create,
                 "nc_post": nc_post, "drawing_create": drawing_create})
