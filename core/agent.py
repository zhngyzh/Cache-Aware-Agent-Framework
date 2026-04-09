"""
Cache-aware agent core.

This version keeps the current single-completion behavior, but splits the flow
into smaller helpers so a tool-calling loop can be added incrementally.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from core.message_manager import AppendOnlyMessageManager, Message
from core.prompt_manager import create_default_prompt_manager
from core.tool_cache import create_default_tool_cache
from core.tool_executor import create_default_tool_executor


@dataclass
class CacheMetrics:
    """Cache-related usage metrics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cache_hit_rate(self) -> float:
        total_prompt = self.cache_hit_tokens + self.cache_miss_tokens
        if total_prompt == 0:
            return 0.0
        return self.cache_hit_tokens / total_prompt

    @property
    def cost_estimate(self) -> float:
        # DeepSeek pricing estimate:
        # - Cache hit: $0.1 / 1M tokens
        # - Cache miss: $1.0 / 1M tokens
        # - Output: $2.0 / 1M tokens
        cache_hit_cost = self.cache_hit_tokens * 0.1 / 1_000_000
        cache_miss_cost = self.cache_miss_tokens * 1.0 / 1_000_000
        output_cost = self.completion_tokens * 2.0 / 1_000_000
        return cache_hit_cost + cache_miss_cost + output_cost

    def __add__(self, other: "CacheMetrics") -> "CacheMetrics":
        return CacheMetrics(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            cache_hit_tokens=self.cache_hit_tokens + other.cache_hit_tokens,
            cache_miss_tokens=self.cache_miss_tokens + other.cache_miss_tokens,
        )


@dataclass
class SessionConfig:
    """
    Session-scoped latched configuration.

    Once the agent is created, these values should remain stable for the life of
    the session so cache prefixes stay comparable across turns.
    """

    model: str
    temperature: float
    max_tokens: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timestamp": self.timestamp,
        }


class CacheAwareAgent:
    """Base cache-aware agent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        enable_tools: bool = False,
        max_tool_rounds: int = 1,
    ):
        load_dotenv()

        self.client = OpenAI(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

        self.session_config = SessionConfig(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.enable_tools = enable_tools
        self.max_tool_rounds = max_tool_rounds

        self.prompt_manager = create_default_prompt_manager()
        self.message_manager = AppendOnlyMessageManager()
        self.tool_cache = create_default_tool_cache()
        self.tool_executor = create_default_tool_executor()
        self.metrics_history: List[CacheMetrics] = []

        self._initialize_dynamic_section()

    def _initialize_dynamic_section(self) -> None:
        session_info = self.prompt_manager.build_session_info(
            date=self.session_config.timestamp.split("T")[0],
            model=self.session_config.model,
            cwd=os.getcwd(),
        )
        self.prompt_manager.add_dynamic_section(session_info)

    def _build_system_prompt(self) -> str:
        return self.prompt_manager.build_system_prompt()

    def _append_user_message(self, user_message: str) -> None:
        self.message_manager.append(Message.user(user_message))

    def _build_api_messages(self) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": self._build_system_prompt()},
            *self.message_manager.get_api_messages(),
        ]

    def _get_enabled_tool_schemas(self) -> List[Dict[str, Any]]:
        """Expose only tools that have a local execution handler."""
        schemas: List[Dict[str, Any]] = []
        for schema in self.tool_cache.get_all_schemas():
            tool_name = schema["function"]["name"]
            if self.tool_executor.supports(tool_name):
                schemas.append(schema)
        return schemas

    def _create_completion(self, messages: List[Dict[str, Any]]) -> Any:
        request_kwargs: Dict[str, Any] = {
            "model": self.session_config.model,
            "messages": messages,
            "temperature": self.session_config.temperature,
            "max_tokens": self.session_config.max_tokens,
        }

        enabled_schemas = self._get_enabled_tool_schemas() if self.enable_tools else []
        if enabled_schemas:
            request_kwargs["tools"] = enabled_schemas

        return self.client.chat.completions.create(
            **request_kwargs,
        )

    def _append_assistant_message(self, assistant_message: Any) -> None:
        self.message_manager.append(
            Message.assistant(
                content=assistant_message.content,
                tool_calls=[tool_call.model_dump() for tool_call in assistant_message.tool_calls]
                if assistant_message.tool_calls
                else None,
            )
        )

    def _build_metrics(self, response: Any) -> CacheMetrics:
        usage = response.usage
        return CacheMetrics(
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cache_hit_tokens=getattr(usage, "prompt_cache_hit_tokens", 0),
            cache_miss_tokens=getattr(usage, "prompt_cache_miss_tokens", usage.prompt_tokens),
        )

    def _record_metrics(self, metrics: CacheMetrics, verbose: bool = False) -> None:
        self.metrics_history.append(metrics)

        if verbose:
            print(
                f"\n[Metrics] Hit: {metrics.cache_hit_tokens}, Miss: {metrics.cache_miss_tokens}, "
                f"Rate: {metrics.cache_hit_rate:.1%}, Cost: ${metrics.cost_estimate:.6f}"
            )

    def _get_tool_call_name(self, tool_call: Any) -> str:
        if isinstance(tool_call, dict):
            return tool_call["function"]["name"]
        return tool_call.function.name

    def _get_tool_call_arguments(self, tool_call: Any) -> Dict[str, Any]:
        if isinstance(tool_call, dict):
            raw_arguments = tool_call["function"]["arguments"]
        else:
            raw_arguments = tool_call.function.arguments

        if isinstance(raw_arguments, dict):
            return raw_arguments
        if not raw_arguments:
            return {}
        return json.loads(raw_arguments)

    def _get_tool_call_id(self, tool_call: Any) -> str:
        if isinstance(tool_call, dict):
            return tool_call["id"]
        return tool_call.id

    def _append_tool_message(self, tool_call_id: str, tool_name: str, content: str) -> None:
        self.message_manager.append(
            Message.tool(
                content=content,
                tool_call_id=tool_call_id,
                name=tool_name,
            )
        )

    def _execute_tool_calls(self, tool_calls: List[Any]) -> None:
        for tool_call in tool_calls:
            tool_name = self._get_tool_call_name(tool_call)
            arguments = self._get_tool_call_arguments(tool_call)
            tool_call_id = self._get_tool_call_id(tool_call)

            result = self.tool_executor.execute(tool_name, arguments)
            self._append_tool_message(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                content=result.to_message_content(),
            )

    def send_message(self, user_message: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Send a user message and return the assistant response plus cache metrics.

        This still performs a single completion round. The helper breakdown is
        intentionally shaped so a future tool-calling loop can reuse the same
        request/append/metrics steps.
        """

        self._append_user_message(user_message)
        messages = self._build_api_messages()
        response = self._create_completion(messages)
        total_metrics = self._build_metrics(response)

        assistant_message = response.choices[0].message
        self._append_assistant_message(assistant_message)

        tool_rounds = 0
        while self.enable_tools and assistant_message.tool_calls and tool_rounds < self.max_tool_rounds:
            self._execute_tool_calls(assistant_message.tool_calls)
            follow_up_messages = self._build_api_messages()
            follow_up_response = self._create_completion(follow_up_messages)
            assistant_message = follow_up_response.choices[0].message
            self._append_assistant_message(assistant_message)
            total_metrics = total_metrics + self._build_metrics(follow_up_response)
            tool_rounds += 1

        self._record_metrics(total_metrics, verbose=verbose)

        return {
            "content": assistant_message.content,
            "tool_calls": assistant_message.tool_calls,
            "metrics": total_metrics,
        }

    def get_total_metrics(self) -> CacheMetrics:
        total = CacheMetrics()
        for metrics in self.metrics_history:
            total = total + metrics
        return total

    def reset_session(self) -> None:
        self.message_manager = AppendOnlyMessageManager()
        self.metrics_history.clear()
        # Intentionally keep session_config latched across resets.
