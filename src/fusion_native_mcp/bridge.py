import ast
import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path

from .native import NativeClient


INSPECT_SCRIPT = '''import json, adsk.core, adsk.fusion, adsk.cam
def product(doc, name):
    try:
        return doc.products.itemByProductType(name)
    except RuntimeError as error:
        if 'failed to find product' in str(error):
            return None
        raise
def run(context):
    app = adsk.core.Application.get()
    doc = app.activeDocument
    result = {"version": app.version, "document": None}
    if doc:
        result["document"] = {"id": doc.creationId, "name": doc.name,
            "modified": doc.isModified, "saved": doc.isSaved}
        design = adsk.fusion.Design.cast(product(doc, "DesignProductType"))
        if design:
            root = design.rootComponent
            result["design"] = {"components": design.allComponents.count,
                "occurrences": root.allOccurrences.count, "root_bodies": root.bRepBodies.count,
                "root_sketches": root.sketches.count, "timeline_count": design.timeline.count,
                "parameters": [{"name": p.name, "expression": p.expression, "unit": p.unit}
                    for p in design.userParameters],
                "unhealthy_features": [{"name": t.name, "message": t.errorOrWarningMessage}
                    for t in design.timeline
                    if t.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState]}
        cam = adsk.cam.CAM.cast(product(doc, "CAMProductType"))
        result["cam"] = {"available_in_document": bool(cam)}
        if cam:
            result["cam"].update({"setups": cam.setups.count, "operations": cam.allOperations.count,
                "nc_programs": cam.ncPrograms.count})
    print(json.dumps(result))
'''


COMPLETION_MARKER = "__FUSION_NATIVE_MCP_COMPLETED_0_2__"


def script_result(result, require_completion=False):
    """Normalize native stdout, including Fusion's extra string escaping."""
    for block in result.get("content", []):
        if block.get("type") != "text":
            continue
        try:
            outer = json.loads(block["text"])
        except (ValueError, TypeError):
            continue
        if not isinstance(outer, dict) or not isinstance(outer.get("message"), str):
            continue
        stdout = outer["message"]
        # Native versions differ in whether stdout is escaped a second time.
        if '\\n' in stdout or '\\"' in stdout:
            try:
                stdout = json.loads('"' + stdout + '"')
            except ValueError:
                pass
        completed = stdout.rstrip().endswith(COMPLETION_MARKER)
        if require_completion and not completed:
            raise RuntimeError("Native runner returned without a script completion marker; outcome is unverified")
        if completed:
            stdout = stdout.rstrip()[:-len(COMPLETION_MARKER)].rstrip('\r\n')
        try:
            data = json.loads(stdout)
        except ValueError:
            data = None
        return {"stdout": stdout, "data": data}
    if require_completion:
        raise RuntimeError("Native runner returned no script output/completion marker")
    return {"native_result": result}


def script_wrapper(script, expected_document_id):
    tree = ast.parse(script)
    runs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    if len(runs) != 1 or len(runs[0].args.posonlyargs) + len(runs[0].args.args) != 1 or runs[0].args.vararg or runs[0].args.kwarg or runs[0].args.kwonlyargs:
        raise ValueError("Script must define exactly one synchronous run(context) function with one argument")
    # Fusion's native runner silently drops scripts containing very long source
    # lines. Adjacent literals keep transported lines short without altering code.
    literals = '\n'.join('        ' + repr(script[i:i+500]) for i in range(0, len(script), 500))
    return f'''import adsk.core
def run(context):
    doc = adsk.core.Application.get().activeDocument
    expected = {expected_document_id!r}
    if expected == "__NO_DOCUMENT__" and doc is not None:
        raise RuntimeError("DOCUMENT_MISMATCH: a document was opened before execution")
    if expected not in (None, "__NO_DOCUMENT__") and (doc is None or str(doc.creationId) != expected):
        raise RuntimeError("DOCUMENT_MISMATCH: inspect again before editing")
    if expected not in (None, "__NO_DOCUMENT__") and sum(str(d.creationId) == expected for d in adsk.core.Application.get().documents) != 1:
        raise RuntimeError("AMBIGUOUS_DOCUMENT: multiple open copies have the same creation ID")
    namespace = {{"__name__": "fusion_mcp_script"}}
    source = (
{literals}
    )
    exec(compile(source, "<fusion-mcp-script>", "exec"), namespace)
    namespace["run"](context)
    print({COMPLETION_MARKER!r})
'''


class Bridge:
    def __init__(self, state_dir, native=None):
        self.native = native or NativeClient()
        self.lock = threading.RLock()
        Path(state_dir).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(Path(state_dir) / "operations.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL, result TEXT, updated REAL NOT NULL)")
        self.db.commit()

    def read(self, query):
        with self.lock:
            return self.native.call("fusion_mcp_read", query)

    def inspect(self):
        return self.execute(INSPECT_SCRIPT, read_only=True)

    def operation(self, operation_id):
        with self.lock:
            row = self.db.execute("SELECT state,result,updated FROM operations WHERE id=?", (operation_id,)).fetchone()
            if not row:
                return {"id": operation_id, "state": "not_found"}
            return {"id": operation_id, "state": row[0], "result": json.loads(row[1]) if row[1] else None, "updated": row[2]}

    def acknowledge(self, operation_id, resolution):
        """Unblock later writes after the caller has inspected partial/uncertain effects."""
        if not resolution.strip():
            raise ValueError("A description of the verified outcome/recovery is required")
        with self.lock:
            op = self.operation(operation_id)
            if op["state"] not in ("uncertain", "started"):
                raise ValueError("Only uncertain or interrupted operations need acknowledgement")
            self._finish(operation_id, "acknowledged", {"previous": op, "resolution": resolution})
            return self.operation(operation_id)

    def _finish(self, operation_id, state, result):
        self.db.execute("UPDATE operations SET state=?,result=?,updated=? WHERE id=?", (state, json.dumps(result), time.time(), operation_id))
        self.db.commit()

    def execute(self, script, read_only=False, expected_document_id=None, operation_id=None):
        if not read_only and (not expected_document_id or not operation_id or not operation_id.strip()):
            raise ValueError("Edits require expected_document_id from inspect and a unique operation_id")
        wrapped = script_wrapper(script, expected_document_id)
        arguments = {"featureType": "script", "object": {"script": wrapped, "readOnly": read_only}}
        with self.lock:
            if read_only:
                return script_result(self.native.call("fusion_mcp_execute", arguments), require_completion=True)
            fingerprint = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
            # BEGIN IMMEDIATE also serializes claims across processes sharing the journal.
            self.db.execute("BEGIN IMMEDIATE")
            try:
                prior = self.db.execute("SELECT fingerprint FROM operations WHERE id=?", (operation_id,)).fetchone()
                if prior:
                    if prior[0] != fingerprint:
                        raise ValueError("operation_id already belongs to a different request")
                    self.db.commit()
                    return self.operation(operation_id)
                unresolved = self.db.execute("SELECT id FROM operations WHERE state IN ('started','uncertain')").fetchone()
                if unresolved:
                    raise ValueError(f"Inspect and acknowledge unresolved operation {unresolved[0]} before further edits")
                self.db.execute("INSERT INTO operations VALUES (?,?,?,?,?)", (operation_id, fingerprint, "started", None, time.time()))
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise
            try:
                result = script_result(self.native.call("fusion_mcp_execute", arguments), require_completion=True)
            except Exception as exc:
                # Even a reported script failure can follow partial geometry changes.
                self._finish(operation_id, "uncertain", {"error": str(exc), "instruction": "Inspect the document before recovery; do not replay automatically."})
            else:
                self._finish(operation_id, "succeeded", result)
            return self.operation(operation_id)

    def close(self):
        self.native.close()
        self.db.close()
