"""Synchronous adapter for Fusion's JSON-response Streamable HTTP endpoint.

No tool call is automatically retried. SDK handles the public MCP transport.
"""
import itertools
import json
from urllib.parse import urlparse

import httpx


class NativeError(RuntimeError):
    pass


class NativeClient:
    def __init__(self, endpoint="http://127.0.0.1:27182/mcp", timeout=120, transport=None):
        url = urlparse(endpoint)
        if url.scheme != "http" or url.hostname not in ("127.0.0.1", "::1", "localhost") or url.username or url.password:
            raise ValueError("Fusion endpoint must be a local HTTP URL without credentials")
        self.endpoint = endpoint
        self.http = httpx.Client(timeout=timeout, trust_env=False, follow_redirects=False, transport=transport)
        self.ids = itertools.count(1)
        self.session = None
        self.protocol = "2025-03-26"
        self.info = None

    def _rpc(self, method, params=None, notification=False):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            payload["id"] = next(self.ids)
        headers = {"Accept": "application/json, text/event-stream"}
        if self.session:
            headers.update({"MCP-Session-Id": self.session, "MCP-Protocol-Version": self.protocol})
        response = self.http.post(self.endpoint, json=payload, headers=headers)
        if response.status_code == 404:
            self.session = None
        response.raise_for_status()
        if method == "initialize":
            self.session = response.headers.get("MCP-Session-Id")
        if notification:
            return None
        if "application/json" not in response.headers.get("Content-Type", ""):
            raise NativeError("Unexpected upstream transport: this adapter requires Fusion JSON responses")
        data = response.json()
        if data.get("id") != payload["id"]:
            raise NativeError("Mismatched upstream response ID")
        if "error" in data:
            raise NativeError(json.dumps(data["error"]))
        if "result" not in data:
            raise NativeError("Missing upstream result")
        return data["result"]

    def connect(self):
        self.info = self._rpc("initialize", {"protocolVersion": self.protocol, "capabilities": {},
            "clientInfo": {"name": "fusion-native-mcp", "version": "0.2.0"}})
        self.protocol = self.info["protocolVersion"]
        self._rpc("notifications/initialized", notification=True)
        return self.info

    def request(self, method, params=None):
        if self.info is None or self.session is None:
            self.connect()
        return self._rpc(method, params)

    def tools(self):
        items, cursor, seen = [], None, set()
        while True:
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            items.extend(result["tools"])
            cursor = result.get("nextCursor")
            if not cursor:
                return items
            if cursor in seen:
                raise NativeError("Repeated tools pagination cursor")
            seen.add(cursor)

    def call(self, name, arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise NativeError(json.dumps(result))
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    value = json.loads(block["text"])
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict) and value.get("success") is False:
                    raise NativeError(json.dumps(value))
        return result

    def close(self):
        self.http.close()
