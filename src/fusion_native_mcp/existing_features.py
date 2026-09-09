from pydantic import Field
from .features import Spec


class ComponentParameterEdit(Spec):
    path: str = Field(description="Exact full occurrence path from fusion_assembly_tree")
    expected_component: str = Field(description="Component token returned by fusion_component_context")
    expected_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expressions: dict[str, str] = Field(min_length=1, description="Model parameter names and new unit-aware expressions, limited to this component")
    allow_shared_definition_edit: bool = Field(default=False, description="Explicitly allow changing the definition used by every listed occurrence")


def register_existing(mcp, service):
    @mcp.tool()
    def fusion_assembly_tree(document_id: str, offset: int = 0, limit: int = 100) -> dict:
        """Read exact nested occurrence paths, component definitions, repeated-instance counts and external-link flags."""
        if offset < 0 or not 1 <= limit <= 500:
            raise ValueError("Invalid pagination")
        return service.call("assembly_tree", {"offset": offset, "limit": limit}, document_id, read_only=True)

    @mcp.tool()
    def fusion_component_context(document_id: str, occurrence_path: str) -> dict:
        """Inspect an existing component's native/proxy geometry, model parameters, feature origins, state fingerprint and all affected occurrence paths."""
        return service.call("component_context", {"path": occurrence_path}, document_id, read_only=True)

    @mcp.tool()
    def fusion_edit_component_parameters(document_id: str, operation_id: str, spec: ComponentParameterEdit) -> dict:
        """Edit only the selected component's existing model parameters. Reject stale state, foreign parameters, external links and unacknowledged repeated instances. Recompute and check new feature errors; return before/after definition states."""
        return service.call("edit_existing_parameters", spec, document_id, operation_id)
