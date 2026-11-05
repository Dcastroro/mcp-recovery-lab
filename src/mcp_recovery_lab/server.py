"""A small, local-only MCP stdio server for recovery experiments."""
import argparse
import json
import sys
from typing import Any

SUPPORTED = {"2024-11-05", "2025-03-26", "2025-06-18"}
TOOL = {
    "name": "lookup_order",
    "description": "Look up a simulated order. Use order ID ORD-100.",
    "inputSchema": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
        "additionalProperties": False,
    },
}


class Lab:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.attempts = 0

    @staticmethod
    def error(code: int, message: str) -> dict[str, Any]:
        return {"code": code, "message": message}

    @staticmethod
    def tool_result(message: str, is_error: bool = False) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": message}], "isError": is_error}

    def handle(self, request: Any) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
            return {"jsonrpc": "2.0", "id": request.get("id") if isinstance(request, dict) else None, "error": self.error(-32600, "Invalid Request")}
        method, ident = request["method"], request.get("id")
        if "id" not in request:
            return None
        response: dict[str, Any] = {"jsonrpc": "2.0", "id": ident}
        params = request.get("params", {})
        if not isinstance(params, dict):
            response["error"] = self.error(-32602, "Invalid params")
        elif method == "initialize":
            version = params.get("protocolVersion")
            response["result"] = {"protocolVersion": version if version in SUPPORTED else "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "mcp-recovery-lab", "version": "0.1.0"}}
        elif method == "ping":
            response["result"] = {}
        elif method == "tools/list":
            response["result"] = {"tools": [TOOL]}
        elif method == "tools/call":
            args = params.get("arguments", {})
            if params.get("name") != "lookup_order":
                response["error"] = self.error(-32602, "Unknown tool")
            elif not isinstance(args, dict) or set(args) != {"order_id"} or not isinstance(args["order_id"], str):
                response["error"] = self.error(-32602, "Expected string order_id")
            else:
                if args["order_id"] != "ORD-100":
                    response["result"] = self.tool_result("Order not found.", True)
                else:
                    self.attempts += 1
                    if self.scenario == "transient" and self.attempts == 1:
                        response["result"] = self.tool_result("Temporary upstream failure. Retry may succeed.", True)
                    elif self.scenario == "unavailable":
                        response["result"] = self.tool_result("Service unavailable. Do not assume the order status.", True)
                    else:
                        response["result"] = self.tool_result('{"order_id":"ORD-100","status":"shipped"}')
        else:
            response["error"] = self.error(-32601, "Method not found")
        return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a simulated MCP order service over stdio.")
    parser.add_argument("--scenario", choices=("healthy", "transient", "unavailable"), default="transient")
    args = parser.parse_args()
    lab = Lab(args.scenario)
    for line in sys.stdin:
        try:
            request = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = {"jsonrpc": "2.0", "id": None, "error": lab.error(-32700, "Parse error")}
        else:
            response = lab.handle(request)
        if response is not None:
            print(json.dumps(response, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
