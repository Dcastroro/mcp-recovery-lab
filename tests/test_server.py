import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mcp_recovery_lab.server import Lab  # noqa: E402


def request(method, params=None, ident=1):
    return {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}


def call(lab, order="ORD-100"):
    return lab.handle(request("tools/call", {"name": "lookup_order", "arguments": {"order_id": order}}))


class RecoveryTests(unittest.TestCase):
    def test_transient_recovers_on_retry(self):
        lab = Lab("transient")
        self.assertTrue(call(lab)["result"]["isError"])
        self.assertEqual(json.loads(call(lab)["result"]["content"][0]["text"])["status"], "shipped")

    def test_unavailable_never_fabricates_a_success(self):
        lab = Lab("unavailable")
        self.assertTrue(all(call(lab)["result"]["isError"] for _ in range(3)))

    def test_rate_limit_recovers_after_two_valid_calls(self):
        lab = Lab("rate-limit")
        self.assertTrue(call(lab, "unknown")["result"]["isError"])
        self.assertTrue(call(lab)["result"]["isError"])
        self.assertTrue(call(lab)["result"]["isError"])
        self.assertFalse(call(lab)["result"]["isError"])

    def test_stale_read_exposes_a_newer_revision(self):
        lab = Lab("stale")
        first = json.loads(call(lab)["result"]["content"][0]["text"])
        second = json.loads(call(lab)["result"]["content"][0]["text"])
        self.assertEqual((first["status"], first["revision"]), ("processing", 1))
        self.assertEqual((second["status"], second["revision"]), ("shipped", 2))
        self.assertEqual(second, json.loads(call(lab)["result"]["content"][0]["text"]))

    def test_healthy_and_not_found(self):
        lab = Lab("healthy")
        self.assertFalse(call(lab)["result"]["isError"])
        self.assertTrue(call(lab, "unknown")["result"]["isError"])

    def test_validates_arguments(self):
        lab = Lab("healthy")
        for args in ({}, {"order_id": 123}, {"order_id": "ORD-100", "extra": True}):
            self.assertEqual(lab.handle(request("tools/call", {"name": "lookup_order", "arguments": args}))["error"]["code"], -32602)

    def test_capabilities_and_unknown_method(self):
        lab = Lab("healthy")
        self.assertEqual(lab.handle(request("initialize", {"protocolVersion": "2025-06-18"}))["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(lab.handle(request("tools/list"))["result"]["tools"][0]["name"], "lookup_order")
        self.assertEqual(lab.handle(request("missing"))["error"]["code"], -32601)
        self.assertIsNone(lab.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_stdio_is_json_only_and_handles_bad_input(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        lines = ["not-json", json.dumps(request("ping")), json.dumps(request("tools/call", {"name": "lookup_order", "arguments": {"order_id": "ORD-100"}}))]
        p = subprocess.run([sys.executable, "-m", "mcp_recovery_lab.server", "--scenario", "healthy"], input="\n".join(lines) + "\n", capture_output=True, text=True, env=env, timeout=10, check=True)
        responses = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(len(responses), 3)
        self.assertEqual(responses[0]["error"]["code"], -32700)
        self.assertEqual(responses[1]["result"], {})
        self.assertFalse(responses[2]["result"]["isError"])
        self.assertEqual(p.stderr, "")


if __name__ == "__main__":
    unittest.main()
