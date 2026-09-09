import concurrent.futures
import json
import threading

import httpx
import pytest

from fusion_native_mcp.bridge import Bridge, script_wrapper, COMPLETION_MARKER
from fusion_native_mcp.native import NativeClient, NativeError

SCRIPT = "def run(context):\n    print('ok')\n"


class FakeNative:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def call(self, name, arguments):
        self.calls += 1
        if self.error:
            raise self.error
        return {"content": [{"type": "text", "text": json.dumps({"success": True, "message": "ok\n" + COMPLETION_MARKER + "\n"})}]}

    def close(self):
        pass


def test_replay_persisted_after_restart(tmp_path):
    native = FakeNative()
    b = Bridge(tmp_path, native)
    first = b.execute(SCRIPT, False, "doc-1", "op-1")
    b.close()
    b = Bridge(tmp_path, native)
    assert b.execute(SCRIPT, False, "doc-1", "op-1") == first
    assert native.calls == 1
    with pytest.raises(ValueError, match="different request"):
        b.execute(SCRIPT + "\n# different", False, "doc-1", "op-1")
    b.close()


def test_uncertain_blocks_edits_but_allows_inspection(tmp_path):
    native = FakeNative(TimeoutError("lost response"))
    b = Bridge(tmp_path, native)
    assert b.execute(SCRIPT, False, "doc", "op")["state"] == "uncertain"
    native.error = None
    b.execute(SCRIPT, True)
    with pytest.raises(ValueError, match="unresolved"):
        b.execute(SCRIPT, False, "doc", "next")
    b.acknowledge("op", "Inspected document and confirmed execution finished")
    assert b.execute(SCRIPT, False, "doc", "next")["state"] == "succeeded"
    b.close()


def test_document_guard_precedes_user_top_level_code(monkeypatch):
    import sys
    import types
    core = types.ModuleType("adsk.core")
    core.Application = types.SimpleNamespace(get=lambda: types.SimpleNamespace(activeDocument=types.SimpleNamespace(creationId="other")))
    adsk = types.ModuleType("adsk")
    adsk.core = core
    monkeypatch.setitem(sys.modules, "adsk", adsk)
    monkeypatch.setitem(sys.modules, "adsk.core", core)
    namespace = {}
    exec(script_wrapper("raise AssertionError('user code ran')\ndef run(c): pass", "expected"), namespace)
    with pytest.raises(RuntimeError, match="DOCUMENT_MISMATCH"):
        namespace["run"](None)


def test_parallel_duplicate_executes_once(tmp_path):
    native = FakeNative()
    b = Bridge(tmp_path, native)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: b.execute(SCRIPT, False, "doc", "same"), range(8)))
    assert native.calls == 1
    assert all(r["state"] == "succeeded" for r in results)
    b.close()


def test_cross_instance_unresolved_claim(tmp_path):
    class SlowNative(FakeNative):
        def call(self, *args):
            started.set()
            release.wait(5)
            return super().call(*args)
    started, release = threading.Event(), threading.Event()
    a = Bridge(tmp_path, SlowNative())
    b = Bridge(tmp_path, FakeNative())
    with concurrent.futures.ThreadPoolExecutor() as pool:
        running = pool.submit(a.execute, SCRIPT, False, "doc", "a")
        assert started.wait(3)
        try:
            with pytest.raises(ValueError, match="unresolved"):
                b.execute(SCRIPT, False, "doc", "b")
        finally:
            release.set()
        assert running.result()["state"] == "succeeded"
    a.close()
    b.close()


@pytest.mark.parametrize("script", ["print('x')", "async def run(c): pass", "def run(a,b): pass"])
def test_invalid_entrypoint(script):
    with pytest.raises(ValueError):
        script_wrapper(script, "doc")


def test_native_session_and_nested_failure():
    seen = []
    def handle(request):
        data = json.loads(request.content)
        seen.append(data["method"])
        if data["method"] == "initialize":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": data["id"], "result": {"protocolVersion": "2025-03-26"}}, headers={"MCP-Session-Id": "session"})
        assert request.headers["MCP-Session-Id"] == "session"
        if data["method"] == "notifications/initialized":
            return httpx.Response(202)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": data["id"], "result": {"content": [{"type": "text", "text": '{"success":false,"error":"bad geometry"}'}]}})
    c = NativeClient(transport=httpx.MockTransport(handle))
    with pytest.raises(NativeError, match="bad geometry"):
        c.call("fusion_mcp_execute", {})
    assert seen == ["initialize", "notifications/initialized", "tools/call"]
    c.close()


def test_remote_endpoint_rejected():
    with pytest.raises(ValueError, match="local HTTP"):
        NativeClient("http://example.com/mcp")


def test_expired_native_session_is_not_replayed():
    initializes = 0
    calls = 0
    def handle(request):
        nonlocal initializes, calls
        data=json.loads(request.content)
        if data['method']=='initialize':
            initializes += 1
            return httpx.Response(200,json={'id':data['id'],'result':{'protocolVersion':'2025-03-26'}},headers={'MCP-Session-Id':str(initializes)})
        if data['method']=='notifications/initialized':
            return httpx.Response(202)
        calls += 1
        if calls==1:
            return httpx.Response(404,json={'error':'Session expired'})
        return httpx.Response(200,json={'id':data['id'],'result':{'content':[]}})
    c=NativeClient(transport=httpx.MockTransport(handle))
    with pytest.raises(httpx.HTTPStatusError):
        c.call('fusion_mcp_execute',{})
    assert calls==1
    c.call('fusion_mcp_read',{})
    assert calls==2 and initializes==2
    c.close()
