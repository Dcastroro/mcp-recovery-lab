import json
import unittest
from types import SimpleNamespace

from examples.verify_scenarios import verify_result


def result(**fields):
    payload = {"order_id": "ORD-100", "status": "processing", **fields}
    content = SimpleNamespace(type="text", text=json.dumps(payload))
    return SimpleNamespace(content=[content], is_error=False)


class VerifierTests(unittest.TestCase):
    def test_stale_revision_must_be_an_integer(self):
        verify_result(result(revision=1), ("processing", 1))
        for value in (True, 1.0, "1", None):
            with self.subTest(value=value), self.assertRaisesRegex(AssertionError, "integer"):
                verify_result(result(revision=value), ("processing", 1))

    def test_unversioned_response_omits_the_revision_field(self):
        verify_result(result(), ("processing", None))
        with self.assertRaisesRegex(AssertionError, "without a revision"):
            verify_result(result(revision=None), ("processing", None))
