"""
Local tool execution layer.

This module keeps tool execution separate from tool schema generation so the
agent can evolve from "schema only" to a real tool-calling loop incrementally.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class ToolExecutionResult:
    """Normalized tool execution result."""

    name: str
    success: bool
    output: dict[str, Any]

    def to_message_content(self) -> str:
        """Serialize output deterministically for stable tool messages."""
        payload = {
            "tool": self.name,
            "success": self.success,
            "output": self.output,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class LocalToolExecutor:
    """Simple registry-based local tool executor."""

    def __init__(self) -> None:
        self._handlers: Dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        self._handlers[name] = handler

    def supports(self, name: str) -> bool:
        return name in self._handlers

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolExecutionResult:
        if name not in self._handlers:
            return ToolExecutionResult(
                name=name,
                success=False,
                output={"error": f"Unsupported tool: {name}"},
            )

        try:
            output = self._handlers[name](arguments)
            return ToolExecutionResult(name=name, success=True, output=output)
        except Exception as exc:  # noqa: BLE001
            return ToolExecutionResult(
                name=name,
                success=False,
                output={"error": str(exc)},
            )


def _read_file_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    file_path = arguments["file_path"]
    path = Path(file_path).expanduser().resolve()

    return {
        "file_path": str(path),
        "content": path.read_text(encoding="utf-8"),
    }


def _echo_json_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    return {"text": arguments["text"]}


def create_default_tool_executor() -> LocalToolExecutor:
    """
    Create the deterministic tool set for the first tool-calling phase.

    We intentionally keep the set small and deterministic so execution-enabled
    cache experiments remain easy to reason about.
    """

    executor = LocalToolExecutor()
    executor.register("echo_json", _echo_json_handler)
    executor.register("read_file", _read_file_handler)
    return executor
