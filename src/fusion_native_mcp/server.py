import atexit
import os
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from .bridge import Bridge
from .native import NativeClient


def build_server(state_dir=None, endpoint=None):
    bridge = Bridge(state_dir or os.getenv("FUSION_MCP_STATE_DIR", str(Path.cwd() / ".fusion-mcp")),
                    NativeClient(endpoint or os.getenv("FUSION_MCP_ENDPOINT", "http://127.0.0.1:27182/mcp")))
    atexit.register(bridge.close)
    mcp = FastMCP("Fusion Native MCP", instructions="Inspect before editing. Use the returned document id and a unique operation id for each edit. Read API documentation before writing scripts. Scripts have full local Python privileges; readOnly is a Fusion design guard, not a Python sandbox. Verify results after edits. A timeout does not cancel Fusion execution. Never automatically replay uncertain writes.")

    @mcp.tool()
    def fusion_new_design(operation_id: str, name: str = "MCP Design", expected_document_id: str = "__NO_DOCUMENT__") -> dict:
        """Create a separate unsaved design. Supply the current document ID if one is open; the default requires no open active document."""
        import json
        script = 'import adsk.core, json\ndef run(context):\n    doc = adsk.core.Application.get().documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)\n    doc.name = ' + repr(name) + '\n    print(json.dumps({"id": doc.creationId, "name": doc.name}))\n'
        return bridge.execute(script, False, expected_document_id, operation_id)

    @mcp.tool()
    def fusion_capabilities() -> dict:
        """Discover native tool schemas from the running Fusion installation."""
        with bridge.lock:
            return {"endpoint": bridge.native.endpoint, "tools": bridge.native.tools(), "server": bridge.native.info}

    @mcp.tool()
    def fusion_inspect() -> dict:
        """Read active document identity, design counts, parameters, feature health and CAM counts."""
        return bridge.inspect()

    @mcp.tool()
    def fusion_api_docs(search_pattern: str, category: Literal["class", "member", "description", "all"] = "all", namespace_filter: str = "") -> dict:
        """Search the installed Fusion API docs by regular expression, including adsk.cam."""
        query = {"queryType": "apiDocumentation", "searchPattern": search_pattern, "apiCategory": category}
        if namespace_filter:
            query["filter"] = namespace_filter
        return bridge.read(query)

    @mcp.tool()
    def fusion_documents() -> dict:
        """List open documents with creation IDs for explicit activation and edit targeting."""
        script = 'import adsk.core,json\ndef run(c):\n    print(json.dumps({"documents":[{"id":d.creationId,"name":d.name,"active":d.isActive,"saved":d.isSaved,"modified":d.isModified} for d in adsk.core.Application.get().documents]}))\n'
        return bridge.execute(script, read_only=True)

    @mcp.tool()
    def fusion_activate_document(current_document_id: str, target_document_id: str, operation_id: str) -> dict:
        """Activate exactly one already-open document by creation ID. Reject duplicate IDs; never save or close other documents."""
        script = 'import adsk.core,json\ndef run(c):\n    docs=[d for d in adsk.core.Application.get().documents if str(d.creationId)==' + repr(target_document_id) + ']\n    if len(docs)!=1:\n        raise ValueError("Target document missing or ambiguous")\n    if not docs[0].activate():\n        raise RuntimeError("Document activation failed")\n    print(json.dumps({"id":docs[0].creationId,"name":docs[0].name}))\n'
        return bridge.execute(script, False, current_document_id, operation_id)

    @mcp.tool()
    def fusion_open_archive(path: str, operation_id: str, expected_document_id: str = "__NO_DOCUMENT__") -> dict:
        """Open a local F3D/F3Z archive in a new document; preserve other open documents. Reinspect returned document identity before editing."""
        source = Path(path)
        if not source.is_absolute() or not source.is_file() or source.suffix.lower() not in ('.f3d','.f3z'):
            raise ValueError('Supply an existing absolute F3D/F3Z archive path')
        script = 'import adsk.core,json\ndef run(c):\n    manager=adsk.core.Application.get().importManager\n    options=manager.createFusionArchiveImportOptions(' + repr(str(source)) + ')\n    doc=manager.importToNewDocument(options)\n    if not doc:\n        raise RuntimeError("Archive import failed")\n    print(json.dumps({"id":doc.creationId,"name":doc.name}))\n'
        return bridge.execute(script, False, expected_document_id, operation_id)

    @mcp.tool()
    def fusion_active_command() -> dict:
        """Inspect any active command dialog and its current inputs."""
        return bridge.read({"queryType": "activeCommand"})

    @mcp.tool()
    def fusion_execute_python(script: str, read_only: bool = False, expected_document_id: str | None = None, operation_id: str | None = None) -> dict:
        """Run Python defining run(context) inside Fusion. Supports all installed API namespaces.

        Mutations require document id from fusion_inspect and a unique operation_id.
        Repeat the same id/request to retrieve its prior result without executing again.
        Exceptions may leave partial changes. Inspect results separately; succeeded means
        the script returned, not that geometry or machining correctness was verified.
        Script code is trusted local code, not sandboxed. Use explicit units in scripts.
        """
        return bridge.execute(script, read_only, expected_document_id, operation_id)

    @mcp.tool()
    def fusion_operation_status(operation_id: str) -> dict:
        """Retrieve persisted operation status without retrying it."""
        return bridge.operation(operation_id)

    @mcp.tool()
    def fusion_acknowledge_operation(operation_id: str, resolution: str) -> dict:
        """After inspecting/recovering uncertain effects, record the outcome and unblock later edits.

        This neither cancels execution nor undoes changes. Verify that Fusion has finished first.
        """
        return bridge.acknowledge(operation_id, resolution)

    @mcp.tool()
    def fusion_screenshot(width: int = 1000, height: int = 700) -> list:
        """Capture the current viewport without changing its direction."""
        if not 32 <= width <= 4096 or not 32 <= height <= 4096:
            raise ValueError("Screenshot dimensions must be between 32 and 4096")
        from mcp.types import ImageContent, TextContent
        import json
        result = bridge.read({"queryType": "screenshot", "width": width, "height": height, "direction": "current"})
        content = []
        for block in result.get("content", []):
            if block.get("type") == "image":
                content.append(ImageContent.model_validate(block))
            elif block.get("type") == "text":
                try:
                    data = json.loads(block["text"])
                except ValueError:
                    data = {}
                if isinstance(data, dict) and data.get("base64Data"):
                    content.append(ImageContent(type="image", data=data["base64Data"], mimeType=data.get("mimeType", "image/png")))
                else:
                    content.append(TextContent(type="text", text=block["text"]))
        return content

    from .features import register_features
    from .cam_features import register_cam
    service = register_features(mcp, bridge)
    register_cam(mcp, service)
    from .existing_features import register_existing
    register_existing(mcp, service)
    return mcp


def main():
    import logging
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('mcp.server.lowlevel.server').setLevel(logging.WARNING)
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
