from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "services" / "operations_ui"

sys.path.insert(0, str(UI_DIR))

import runtime  # noqa: E402


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def iter_lines(self, decode_unicode: bool):
        del decode_unicode
        return iter(())


class GatewayModelArmorTraceTest(unittest.TestCase):
    @patch.object(runtime, "_access_token", return_value="token")
    @patch.object(runtime.requests, "post", return_value=_Response(403))
    def test_denial_is_correlated_without_logging_prompt(
        self,
        _post,
        _token,
    ) -> None:
        output = io.StringIO()
        prompt = "synthetic secret bypass payload"

        with patch("sys.stdout", output):
            result = runtime.submit_handover(
                message=prompt,
                user_id="operator@example.invalid",
                request_id="operations-ui:test-trace",
            )

        trace = json.loads(output.getvalue())
        self.assertTrue(result["blocked"])
        self.assertEqual(trace["decision"], "DENY")
        self.assertEqual(trace["http_status"], 403)
        self.assertEqual(
            trace["request_id"],
            "operations-ui:test-trace",
        )
        self.assertEqual(
            trace["operational_request"],
            "handover_intake",
        )
        self.assertEqual(
            trace["gateway_path"],
            "CLIENT_TO_AGENT",
        )
        self.assertNotIn(prompt, output.getvalue())
        self.assertEqual(result["security_trace"], trace)


if __name__ == "__main__":
    unittest.main()
