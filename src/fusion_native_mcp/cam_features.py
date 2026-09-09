from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .features import Spec


class MillingSetupSpec(Spec):
    models: list[str] = Field(min_length=1)
    name: str = "MCP Milling Setup"
    side_stock: str = "1 mm"
    top_stock: str = "1 mm"
    origin: Literal["top center", "top 1", "top 2", "top 3", "top 4", "center", "bottom center"] = "top center"


class CAMOperationSpec(Spec):
    setup_id: str
    strategy: str = Field(min_length=1, description="Installed strategy identifier, e.g. face or adaptive. Geometry-dependent strategies may require further selection inputs.")
    name: str = "MCP Operation"
    tool_library_url: str
    tool_index: int = Field(ge=0)
    tool_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expressions: dict[str, str] = Field(default_factory=dict, description="Explicit Fusion CAM parameter expressions; unknown names are rejected")


class NCProgramSpec(Spec):
    operation_ids: list[str] = Field(min_length=1)
    post_url: str = Field(min_length=1, description="Explicit post configuration URL discovered from the post library")
    output_folder: str
    filename: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    name: str = "MCP NC Program"

    @model_validator(mode="after")
    def absolute_folder(self):
        if not Path(self.output_folder).is_absolute():
            raise ValueError("Output folder must be absolute")
        return self


class DrawingSpec(Spec):
    standard: Literal["ISODrawingStandardType", "ASMEDrawingStandardType"] = "ISODrawingStandardType"
    units: Literal["MillimeterDrawingUnitType", "InchDrawingUnitType"] = "MillimeterDrawingUnitType"
    sheet_size: Literal["A4ISOSheetSize", "A3ISOSheetSize", "A2ISOSheetSize", "AASMESheetSize", "BASMESheetSize"] = "A3ISOSheetSize"
    dimensions: bool = True

    @model_validator(mode="after")
    def compatible_sheet(self):
        if (self.standard == "ISODrawingStandardType") != ("ISO" in self.sheet_size):
            raise ValueError("Sheet size must match drawing standard")
        return self


def register_cam(mcp, service):
    @mcp.tool()
    def fusion_cam_inventory(document_id: str) -> dict:
        """Read CAM setups, operations, errors, toolpath validity and NC programs."""
        return service.call("cam_inventory", {}, document_id, read_only=True)

    @mcp.tool()
    def fusion_cam_browse_library(document_id: str, kind: Literal["tools", "posts"], url: str | None = None) -> dict:
        """Browse tool/post library folders and asset URLs; omit URL for the Fusion library root."""
        return service.call("library_browse", {"kind": kind, "url": url}, document_id, read_only=True)

    @mcp.tool()
    def fusion_cam_tools(document_id: str, library_url: str, offset: int = 0, limit: int = 20) -> dict:
        """Read tool definitions with fingerprints to detect changes between selection and use."""
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("offset >= 0 and 1 <= limit <= 100 required")
        return service.call("tool_inventory", {"url": library_url, "offset": offset, "limit": limit}, document_id, read_only=True)

    @mcp.tool()
    def fusion_cam_create_setup(document_id: str, operation_id: str, spec: MillingSetupSpec) -> dict:
        """Activate Manufacture and create a milling setup with relative-box stock and a box-point WCS origin. Machine and fixtures are not automatically selected."""
        return service.call("cam_setup", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_cam_parameters(document_id: str, cam_id: str, setup: bool = False) -> dict:
        """Inspect installed CAM parameter names and expressions on an operation or setup."""
        return service.call("cam_parameters", {"id": cam_id, "setup": setup}, document_id, read_only=True)

    @mcp.tool()
    def fusion_cam_create_operation(document_id: str, operation_id: str, spec: CAMOperationSpec) -> dict:
        """Create a CAM operation with an explicitly selected tool and parameter expressions. Valid toolpaths must be generated and checked separately."""
        return service.call("cam_operation", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_cam_generate(document_id: str, operation_id: str, cam_operation_ids: list[str]) -> dict:
        """Start asynchronous toolpath generation and return a job ID. Poll fusion_cam_job; do not resubmit on timeout."""
        if not cam_operation_ids:
            raise ValueError("Select operations to generate")
        return service.call("cam_generate", {"operation_ids": cam_operation_ids}, document_id, operation_id)

    @mcp.tool()
    def fusion_cam_job(document_id: str, job_id: str) -> dict:
        """Poll generation completion and toolpath validity without blocking Fusion's main thread. Jobs become unknown after a Fusion restart."""
        return service.call("cam_job", {"job_id": job_id}, document_id, read_only=True)

    @mcp.tool()
    def fusion_cam_create_nc_program(document_id: str, operation_id: str, spec: NCProgramSpec) -> dict:
        """Experimental, not yet live-validated: prepare an NC program with a chosen post and empty output folder; does not post-process yet."""
        return service.call("nc_create", spec, document_id, operation_id)

    @mcp.tool()
    def fusion_cam_post_process(document_id: str, operation_id: str, program_id: str) -> dict:
        """Experimental, not yet live-validated: post-process the explicitly configured NC program to its empty output folder. Inspect results and machine/post suitability before machining."""
        return service.call("nc_post", {"program_id": program_id}, document_id, operation_id)

    @mcp.tool()
    def fusion_create_drawing(document_id: str, operation_id: str, spec: DrawingSpec) -> dict:
        """Experimental, not yet live-validated: create an automatic cloud drawing from an already saved design, with configurable standard, sheet and auto-dimensions. Requires the installed Drawing API; may start a cloud job."""
        return service.call("drawing_create", spec, document_id, operation_id)
