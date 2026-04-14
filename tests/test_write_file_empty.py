"""
Test write_file with empty content.
"""

import tempfile
import unittest
from pathlib import Path

from core.tool_executor import create_default_tool_executor


class WriteFileEmptyContentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.executor = create_default_tool_executor(workspace_root=self.workspace)

    def test_write_file_allows_empty_string(self):
        result = self.executor.execute("write_file", {"file_path": "empty.txt", "content": ""})

        self.assertTrue(result.success)
        self.assertEqual(result.status, "ok")

        file_path = self.workspace / "empty.txt"
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.read_text(encoding="utf-8"), "")
        self.assertEqual(result.output["bytes_written"], 0)

    def test_write_file_can_clear_existing_file(self):
        # Create file with content
        file_path = self.workspace / "clear_me.txt"
        file_path.write_text("original content", encoding="utf-8")

        # Clear it
        result = self.executor.execute("write_file", {"file_path": "clear_me.txt", "content": ""})

        self.assertTrue(result.success)
        self.assertEqual(file_path.read_text(encoding="utf-8"), "")
        self.assertEqual(result.output["bytes_written"], 0)


if __name__ == "__main__":
    unittest.main()
