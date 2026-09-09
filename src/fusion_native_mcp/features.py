"""Typed contracts and script transport for native feature implementations."""
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class EntityQuery(Spec):
    kind: Literal["components", "occurrences", "bodies", "faces", "edges", "sketches", "profiles", "sketch_curves", "sketch_points", "features", "joints", "as_built_joints"]
    scope: str | None = None
    name: str | None = None
    surface_type: Literal["Plane", "Cylinder", "Cone", "Sphere", "Torus", "NurbsSurface"] | None = None
    radius_mm: float | None = Field(default=None, gt=0)
    tolerance_mm: float = Field(default=0.001, gt=0)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def scope_required(self):
        if self.kind in ("faces", "edges", "profiles", "sketch_curves", "sketch_points") and not self.scope:
            raise ValueError("A body/sketch scope token is required for this entity kind")
        if (self.surface_type or self.radius_mm is not None) and self.kind != "faces":
            raise ValueError("Surface and radius filters apply to faces")
        return self


class ParameterSpec(Spec):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    expression: str = Field(min_length=1)
    units: str = "mm"
    comment: str = ""
    component: str | None = Field(default=None, description="Required for editing an existing model parameter; user parameters are design-wide")
    allow_shared_definition_edit: bool = False


class SketchSpec(Spec):
    shape: Literal["rectangle", "circle"]
    name: str = "MCP Sketch"
    component: str = "root"
    plane: Literal["xy", "xz", "yz"] = "xy"
    width: str = Field(description="Rectangle width or circle diameter, e.g. '40 mm' or a parameter name")
    height: str = "20 mm"
    allow_shared_definition_edit: bool = False
    offset: str = Field(default="0 mm", description="Offset from the selected component construction plane")


class FeatureSpec(Spec):
    kind: Literal["extrude", "revolve", "fillet", "chamfer", "shell", "combine", "loft", "sweep", "rectangular_pattern", "circular_pattern"]
    entities: list[str] = Field(min_length=1, description="Ordered entity tokens: profiles, edges, faces, bodies or features as appropriate")
    name: str = "MCP Feature"
    component: str = "root"
    operation: Literal["new_body", "join", "cut", "intersect"] = "new_body"
    distance: str = "5 mm"
    angle: str = "360 deg"
    axis: Literal["x", "y", "z"] = "z"
    axis_token: str | None = None
    path_token: str | None = None
    quantity: int = Field(default=2, ge=2, le=1000)
    keep_tools: bool = True
    allow_shared_definition_edit: bool = False

    @model_validator(mode="after")
    def required_references(self):
        if self.kind in ("loft", "combine") and len(self.entities) < 2:
            raise ValueError("Loft/combine requires at least two entities")
        if self.kind == "combine" and self.operation == "new_body":
            raise ValueError("Combine requires join, cut, or intersect")
        if self.kind == "sweep" and not self.path_token:
            raise ValueError("Sweep requires path_token")
        return self


class HoleSpec(Spec):
    points: list[str] = Field(min_length=1, description="SketchPoint tokens returned by an entity query")
    diameter: str
    depth: str
    component: str = "root"
    name: str = "MCP Holes"
    allow_shared_definition_edit: bool = False


class MeasurementCheck(Spec):
    token: str
    metric: Literal["x", "y", "z", "volume"]
    expected: float
    tolerance: float = Field(default=0.001, gt=0, description="mm for dimensions; mm^3 for volume")


class AssemblySpec(Spec):
    action: Literal["create_component", "insert_component", "joint"]
    name: str = "MCP Component"
    component: str = "root"
    translation_mm: tuple[float, float, float] = (0, 0, 0)
    source: str | None = None
    one: str | None = None
    two: str | None = None
    motion: Literal["rigid", "revolute", "slider"] = "rigid"
    origin_token: str | None = None
    axis: Literal["x", "y", "z"] = "z"
    minimum: float | None = Field(default=None, description="Degrees for revolute; millimeters for slider")
    maximum: float | None = None
    allow_shared_definition_edit: bool = False

    @model_validator(mode="after")
    def validate_joint(self):
        if self.action == "insert_component" and not self.source:
            raise ValueError("Existing component token required")
        if self.action == "joint":
            if not self.one or not self.two:
                raise ValueError("Two occurrence references required")
            if self.motion != "rigid" and not self.origin_token:
                raise ValueError("Moving joint requires an origin point token")
            if self.motion == "rigid" and (self.minimum is not None or self.maximum is not None):
                raise ValueError("Rigid joints have no motion limits")
            if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
                raise ValueError("Minimum exceeds maximum")
        return self


class ExportSpec(Spec):
    format: Literal["step", "stl", "f3d", "dxf", "bom_json"]
    path: str
    entity: str | None = None

    @model_validator(mode="after")
    def validate_export(self):
        if not Path(self.path).is_absolute():
            raise ValueError("Export path must be absolute")
        if self.format == "dxf" and not self.entity:
            raise ValueError("DXF requires a sketch token")
        suffix = Path(self.path).suffix.lower()
        extensions = {"step": (".step", ".stp"), "stl": (".stl",), "f3d": (".f3d",), "dxf": (".dxf",), "bom_json": (".json",)}
        if suffix not in extensions[self.format]:
            raise ValueError("Filename extension does not match export format")
        return self


class FeatureService:
    def __init__(self, bridge):
        self.bridge = bridge

    def call(self, action, spec, document_id, operation_id=None, read_only=False):
        params = spec.model_dump() if isinstance(spec, BaseModel) else spec
        source = Path(__file__).with_name("runtime.py").read_text(encoding="utf-8")
        for filename in ("runtime_cam.py", "runtime_existing.py"):
            source += "\n" + Path(__file__).with_name(filename).read_text(encoding="utf-8")
        payload = json.dumps(params, allow_nan=False)
        source += f'\ndef run(context):\n    params = json.loads({payload!r})\n    print(json.dumps(HANDLERS[{action!r}](params)))\n'
        return self.bridge.execute(source, read_only, document_id, operation_id)


def register_features(mcp, bridge):
    service = FeatureService(bridge)

    @mcp.tool()
    def fusion_model_overview(document_id: str) -> dict:
        """Read parameter expressions, timeline, feature diagnostics and component structure. For large designs prefer paginated entity queries."""
        return service.call("overview", {}, document_id, read_only=True)

    @mcp.tool()
    def fusion_query_entities(document_id: str, query: EntityQuery) -> dict:
        """Discover geometry and re-usable entity tokens. Faces/edges require a body scope; profiles/points/curves require sketch scope. Filters are exact, never choose an ambiguous result silently."""
        return service.call("entities", query, document_id, read_only=True)

    @mcp.tool()
    def fusion_set_parameter(document_id: str, operation_id: str, spec: ParameterSpec) -> dict:
        """Create a user parameter or edit an existing user/model parameter expression, then recompute."""
        return service.call("parameter", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_create_sketch(document_id: str, operation_id: str, spec: SketchSpec) -> dict:
        """Create a dimension-driven rectangle or circle at the component origin, and require full constraint. Returns profile references."""
        return service.call("sketch", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_constrain_sketch(document_id: str, operation_id: str, sketch_token: str, allow_shared_definition_edit: bool = False) -> dict:
        """Apply Fusion AutoConstrain to an existing sketch and report whether it became fully constrained. Geometry may be adjusted."""
        return service.call("constrain", {"sketch": sketch_token, "allow_shared_definition_edit": allow_shared_definition_edit}, document_id, operation_id)

    @mcp.tool()
    def fusion_create_feature(document_id: str, operation_id: str, spec: FeatureSpec) -> dict:
        """Create extrude/revolve/sweep/loft, fillet/chamfer/shell, booleans, or patterns. Query entity tokens first; supply their owning component. Inspect feature health after edits."""
        return service.call("feature", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_create_holes(document_id: str, operation_id: str, spec: HoleSpec) -> dict:
        """Create depth-limited simple holes at selected sketch points."""
        return service.call("holes", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_validate_design(document_id: str, checks: list[MeasurementCheck] = []) -> dict:
        """Report unhealthy features, underconstrained sketches and numeric body checks. This does not certify manufacturability."""
        return service.call("validate", {"checks": [v.model_dump() for v in checks]}, document_id, read_only=True)

    @mcp.tool()
    def fusion_recompute(document_id: str, operation_id: str) -> dict:
        """Recompute the design and report remaining problems; does not invent replacements for broken references."""
        return service.call("validate", {"recompute": True}, document_id, operation_id)

    @mcp.tool()
    def fusion_check_interference(document_id: str, entities: list[str]) -> dict:
        """Analyze interference between explicit bodies/occurrences, excluding coincident faces."""
        if len(entities) < 2:
            raise ValueError("At least two entities required")
        return service.call("interference", {"entities": entities}, document_id, read_only=True)

    @mcp.tool()
    def fusion_assembly(document_id: str, operation_id: str, spec: AssemblySpec) -> dict:
        """Create/instance components or add rigid, revolute or slider as-built joints with optional motion limits."""
        return service.call("assembly", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_bom(document_id: str) -> dict:
        """Return a flattened component bill of materials and occurrence quantities."""
        return service.call("bom", {}, document_id, read_only=True)

    @mcp.tool()
    def fusion_export(document_id: str, operation_id: str, spec: ExportSpec) -> dict:
        """Export STEP, STL, F3D archive, sketch DXF, or BOM JSON to a new absolute path. Existing destinations are rejected."""
        return service.call("export", spec, document_id, operation_id)

    return service
