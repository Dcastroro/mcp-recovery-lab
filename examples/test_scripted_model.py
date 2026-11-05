"""Regression checks for the deterministic example; requires Pydantic AI."""
import unittest
from types import SimpleNamespace

from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_agent import scripted_model


def response(*parts):
    return scripted_model([SimpleNamespace(parts=list(parts))], None).parts[0]


def tool_result(content):
    return ToolReturnPart("lookup_order", content)


class ScriptedModelTests(unittest.TestCase):
    def test_retries_only_the_known_temporary_error(self):
        self.assertIsInstance(response(tool_result("Temporary upstream failure. Retry may succeed.")), ToolCallPart)
        self.assertEqual(response(tool_result("Permission denied")).content, "The order status could not be verified.")

    def test_validates_order_and_status_before_claiming_shipped(self):
        initial = tool_result("Temporary upstream failure. Retry may succeed.")
        for value in (
            {"order_id": "ORD-100", "status": "not shipped"},
            {"order_id": "ORD-OTHER", "status": "shipped"},
            "status: shipped",
            {"order_id": "ORD-100", "status": "unshipped"},
        ):
            with self.subTest(value=value):
                self.assertEqual(response(initial, tool_result(value)).content, "The order status could not be verified.")
        valid = {"order_id": "ORD-100", "status": "shipped"}
        self.assertEqual(response(initial, ToolReturnPart("other_tool", valid)).content, "The order status could not be verified.")
        self.assertEqual(response(initial, ToolReturnPart("lookup_order", valid, outcome="failed")).content, "The order status could not be verified.")
        self.assertEqual(response(initial, tool_result(valid)).content, "Order ORD-100 is shipped (simulated data).")


if __name__ == "__main__":
    unittest.main()
