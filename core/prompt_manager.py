"""
四层 Prompt 架构管理器

基于 Claude Code 的设计：
- Layer 1: System Prompt (静态段 + BOUNDARY + 动态段)
- Layer 2: Tool Definitions
- Layer 3: Message History
"""

from typing import List, Dict, Any
from datetime import datetime
import os


class PromptLayerManager:
    """管理四层 Prompt 架构"""

    # BOUNDARY 标记，分隔静态段和动态段
    BOUNDARY = "# Session-specific guidance"

    def __init__(self):
        self.static_sections: List[str] = []
        self.dynamic_sections: List[str] = []
        self.tools: List[Dict[str, Any]] = []
        self.messages: List[Dict[str, Any]] = []

    def add_static_section(self, section: str) -> None:
        """添加静态 System Prompt 段（全局缓存）"""
        self.static_sections.append(section)

    def add_dynamic_section(self, section: str) -> None:
        """添加动态 System Prompt 段（会话特定）"""
        self.dynamic_sections.append(section)

    def build_system_prompt(self) -> str:
        """构建完整的 System Prompt，插入 BOUNDARY"""
        parts = []

        # 静态段
        if self.static_sections:
            parts.append("\n\n".join(self.static_sections))

        # BOUNDARY 标记
        parts.append(self.BOUNDARY)

        # 动态段
        if self.dynamic_sections:
            parts.append("\n\n".join(self.dynamic_sections))

        return "\n\n".join(parts)

    def build_session_info(self, **kwargs) -> str:
        """构建会话特定信息（动态段）"""
        info_parts = []

        # 当前日期
        if "date" not in kwargs:
            kwargs["date"] = datetime.now().strftime("%Y-%m-%d")

        # 工作目录
        if "cwd" not in kwargs:
            kwargs["cwd"] = os.getcwd()

        # 构建 system-reminder 格式
        info_parts.append("<system-reminder>")
        for key, value in kwargs.items():
            info_parts.append(f"{key}: {value}")
        info_parts.append("</system-reminder>")

        return "\n".join(info_parts)

    def get_cache_breakpoints(self) -> List[int]:
        """
        返回缓存断点位置

        根据 Claude Code 的设计：
        - System Prompt 末尾标记 cache_control
        - 最后一条消息标记 cache_control
        """
        breakpoints = [0]  # System Prompt
        if self.messages:
            breakpoints.append(len(self.messages) - 1)  # 最后一条消息
        return breakpoints


# 预定义的静态 System Prompt 段
IDENTITY_SECTION = """You are a Cache-Aware AI Agent, designed to demonstrate optimal prompt caching strategies.

Your purpose is to showcase how proper prompt architecture can maximize cache hit rates and minimize API costs."""

CAPABILITIES_SECTION = """You have access to various tools for:
- File operations (read, write, edit)
- Code analysis and quality checks
- Python code execution
- Web search and information retrieval"""

RULES_SECTION = """Follow these rules:
1. Always use tools when appropriate
2. Provide clear explanations of your actions
3. Be concise and direct in responses
4. Prioritize cache efficiency in your design"""

TOOL_USAGE_SECTION = """When using tools:
- Call tools with properly formatted JSON arguments
- Wait for tool results before proceeding
- Handle errors gracefully
- Explain tool usage to the user"""


def create_default_prompt_manager() -> PromptLayerManager:
    """创建默认的 Prompt 管理器，包含标准静态段"""
    manager = PromptLayerManager()

    # 添加静态段（这些内容永不改变，可以全局缓存）
    manager.add_static_section(IDENTITY_SECTION)
    manager.add_static_section(CAPABILITIES_SECTION)
    manager.add_static_section(RULES_SECTION)
    manager.add_static_section(TOOL_USAGE_SECTION)

    return manager
