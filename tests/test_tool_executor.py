import json
import unittest

from core.tool_executor import ToolExecutionResult, create_default_tool_executor


class ToolExecutorTests(unittest.TestCase):
    def test_default_executor_supports_minimal_deterministic_tools(self):
        executor = create_default_tool_executor()

        self.assertTrue(executor.supports("echo_json"))
        self.assertTrue(executor.supports("read_file"))
        self.assertFalse(executor.supports("write_file"))

    def test_unsupported_tool_returns_structured_error(self):
        executor = create_default_tool_executor()

        result = executor.execute("missing_tool", {})

        self.assertFalse(result.success)
        self.assertIn("Unsupported tool", result.output["error"])

    def test_tool_execution_result_serializes_deterministically(self):
        result = ToolExecutionResult(
            name="read_file",
            success=True,
            output={"b": 2, "a": 1},
        )

        serialized = result.to_message_content()
        parsed = json.loads(serialized)

        self.assertEqual(parsed["tool"], "read_file")
        self.assertTrue(parsed["success"])
        self.assertEqual(list(parsed["output"].keys()), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
