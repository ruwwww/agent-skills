#!/usr/bin/env python3
"""
archi.py - Deterministic CLI helper for Archi MCP Server (http://127.0.0.1:18090/mcp)
Allows AI agents to easily inspect, create, connect, and layout ArchiMate models in Archi.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error

DEFAULT_URL = os.environ.get("ARCHI_MCP_URL", "http://127.0.0.1:18090/mcp")

class ArchiClient:
    def __init__(self, endpoint=DEFAULT_URL):
        self.endpoint = endpoint
        self.session_id = None
        self._request_id = 1
        self._initialize()

    def _post(self, payload):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self.session_id = sid
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} {e.reason}: {err_body}")

    def _initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "archi-cli", "version": "1.0.0"}
            }
        }
        self._request_id += 1
        res = self._post(payload)
        data = self._parse_response(res)
        if "error" in data:
            raise RuntimeError(f"MCP Initialize failed: {data['error']}")

    def _parse_response(self, raw_body):
        for line in raw_body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        try:
            return json.loads(raw_body)
        except Exception:
            raise ValueError(f"Could not parse MCP response: {raw_body[:200]}")

    def call_tool(self, tool_name, arguments=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }
        self._request_id += 1
        res = self._post(payload)
        parsed = self._parse_response(res)
        if "error" in parsed:
            raise RuntimeError(f"Tool {tool_name} returned error: {parsed['error']}")
        
        result_content = parsed.get("result", {}).get("content", [])
        if result_content and result_content[0].get("type") == "text":
            text_val = result_content[0]["text"]
            try:
                return json.loads(text_val)
            except Exception:
                return {"text": text_val}
        return parsed.get("result", {})

def main():
    parser = argparse.ArgumentParser(description="Archi MCP CLI Helper for Agents")
    parser.add_argument("--url", default=DEFAULT_URL, help="Archi MCP Endpoint")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    subparsers.add_parser("info", help="Get model info and statistics")
    subparsers.add_parser("views", help="List all diagram views")

    p_vc = subparsers.add_parser("view-contents", help="Get contents of a specific view")
    p_vc.add_argument("view_id", help="View ID")

    p_search = subparsers.add_parser("search", help="Search elements by keyword")
    p_search.add_argument("query", help="Search term")
    p_search.add_argument("--type", help="Filter by element type")

    p_get = subparsers.add_parser("get-element", help="Get details of an element by ID")
    p_get.add_argument("element_id", help="Element ID")

    p_ce = subparsers.add_parser("create-element", help="Create an ArchiMate element")
    p_ce.add_argument("--type", required=True, help="Element type (e.g. ApplicationComponent, BusinessProcess)")
    p_ce.add_argument("--name", required=True, help="Element name")
    p_ce.add_argument("--doc", default="", help="Documentation text")
    p_ce.add_argument("--force", action="store_true", help="Force creation")

    p_cr = subparsers.add_parser("create-rel", help="Create a relationship between elements")
    p_cr.add_argument("--type", required=True, help="Relationship type")
    p_cr.add_argument("--source", required=True, help="Source element ID")
    p_cr.add_argument("--target", required=True, help="Target element ID")
    p_cr.add_argument("--name", default="", help="Optional name")
    p_cr.add_argument("--access", choices=["access", "read", "write", "readwrite"], help="Access type")

    p_cv = subparsers.add_parser("create-view", help="Create a new diagram view")
    p_cv.add_argument("--name", required=True, help="View name")
    p_cv.add_argument("--router", default="manhattan", choices=["manhattan", "manual"])

    p_av = subparsers.add_parser("add-to-view", help="Add an element to a view")
    p_av.add_argument("--view-id", required=True, help="Target View ID")
    p_av.add_argument("--element-id", required=True, help="Element ID")
    p_av.add_argument("--x", type=int)
    p_av.add_argument("--y", type=int)
    p_av.add_argument("--width", type=int, default=120)
    p_av.add_argument("--height", type=int, default=55)
    p_av.add_argument("--auto-connect", action="store_true")

    p_ac = subparsers.add_parser("auto-connect", help="Auto connect all relationships on a view")
    p_ac.add_argument("view_id", help="View ID")

    p_al = subparsers.add_parser("auto-layout", help="Run ELK auto-layout and routing on a view")
    p_al.add_argument("view_id", help="View ID")
    p_al.add_argument("--direction", default="DOWN", choices=["DOWN", "RIGHT", "UP", "LEFT"])

    p_exp = subparsers.add_parser("export-view", help="Export a view diagram to image file")
    p_exp.add_argument("view_id", help="View ID")
    p_exp.add_argument("output_path", help="Output file path (.png, .svg, .pdf)")

    p_call = subparsers.add_parser("call", help="Call any Archi MCP tool directly")
    p_call.add_argument("tool", help="MCP tool name")
    p_call.add_argument("args", nargs="?", default="{}", help="JSON string of arguments")

    args = parser.parse_args()
    client = ArchiClient(args.url)

    if args.cmd == "info":
        res = client.call_tool("get-model-info")
        print(json.dumps(res, indent=2))
    elif args.cmd == "views":
        res = client.call_tool("get-views")
        print(json.dumps(res, indent=2))
    elif args.cmd == "view-contents":
        res = client.call_tool("get-view-contents", {"viewId": args.view_id})
        print(json.dumps(res, indent=2))
    elif args.cmd == "search":
        params = {"query": args.query}
        if args.type:
            params["type"] = args.type
        res = client.call_tool("search-elements", params)
        print(json.dumps(res, indent=2))
    elif args.cmd == "get-element":
        res = client.call_tool("get-element", {"id": args.element_id})
        print(json.dumps(res, indent=2))
    elif args.cmd == "create-element":
        params = {"type": args.type, "name": args.name}
        if args.doc:
            params["documentation"] = args.doc
        if args.force:
            params["force"] = True
        res = client.call_tool("create-element", params)
        print(json.dumps(res, indent=2))
    elif args.cmd == "create-rel":
        params = {"type": args.type, "sourceId": args.source, "targetId": args.target}
        if args.name:
            params["name"] = args.name
        if args.access:
            params["accessType"] = args.access
        res = client.call_tool("create-relationship", params)
        print(json.dumps(res, indent=2))
    elif args.cmd == "create-view":
        params = {"name": args.name, "connectionRouterType": args.router}
        res = client.call_tool("create-view", params)
        print(json.dumps(res, indent=2))
    elif args.cmd == "add-to-view":
        params = {
            "viewId": args.view_id,
            "elementId": args.element_id,
            "width": args.width,
            "height": args.height,
            "autoConnect": args.auto_connect
        }
        if args.x is not None and args.y is not None:
            params["x"] = args.x
            params["y"] = args.y
        res = client.call_tool("add-to-view", params)
        print(json.dumps(res, indent=2))
    elif args.cmd == "auto-connect":
        res = client.call_tool("auto-connect-view", {"viewId": args.view_id})
        print(json.dumps(res, indent=2))
    elif args.cmd == "auto-layout":
        res = client.call_tool("auto-layout-and-route", {"viewId": args.view_id, "direction": args.direction})
        print(json.dumps(res, indent=2))
    elif args.cmd == "export-view":
        ext = os.path.splitext(args.output_path)[1].lower()
        fmt = "PNG"
        if ext == ".svg":
            fmt = "SVG"
        elif ext == ".pdf":
            fmt = "PDF"
        out_abs = os.path.abspath(args.output_path)
        res = client.call_tool("export-view", {"viewId": args.view_id, "outputPath": out_abs, "format": fmt})
        print(json.dumps(res, indent=2))
    elif args.cmd == "call":
        tool_args = json.loads(args.args)
        res = client.call_tool(args.tool, tool_args)
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
