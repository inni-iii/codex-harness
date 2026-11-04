"""A recorded failure must become actionable model context, not only a file."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import lifecycle_hooks as hooks


class FeedbackRegression(unittest.TestCase):
    def test_callback_failure_is_delivered_once_and_reappears_on_resume(self):
        with tempfile.TemporaryDirectory(prefix="hook-feedback-") as temporary:
            root = Path(temporary).resolve()
            config = root / "tools/harness/harness.toml"
            config.parent.mkdir(parents=True)
            config.write_text("version=1\n")
            event = {"hook_event_name": "PreToolUse", "session_id": "feedback-session",
                     "tool_name": "Bash", "tool_input": {"command": "pwd"}}

            def invoke(payload):
                output, error = io.StringIO(), io.StringIO()
                with patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()))), \
                        redirect_stdout(output), redirect_stderr(error):
                    code = hooks.main(root)
                return code, json.loads(output.getvalue()) if output.getvalue() else {}, error.getvalue()

            with patch("harness.remote_guard.inspect", side_effect=ValueError("private-original-input")):
                self.assertEqual(invoke(event)[0], 1)
            code, result, error = invoke(event)
            self.assertEqual(code, 0)
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("hook status", context)
            self.assertIn("remote_guard", context)
            self.assertIn(".runtime/hook-errors/", context)
            self.assertNotIn("private-original-input", context + error)
            self.assertEqual(invoke(event)[1], {})
            resumed = invoke(dict(event, hook_event_name="SessionStart", source="resume"))[1]
            self.assertIn(".runtime/hook-errors/", resumed["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
