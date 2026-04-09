"""
Append-only 消息管理器

基于 Claude Code 的设计原则：
- 消息只能追加，永不修改
- 保护缓存前缀的完整性
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """消息数据类"""
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为 API 格式"""
        result = {"role": self.role.value}

        if self.content is not None:
            result["content"] = self.content

        if self.tool_calls is not None:
            result["tool_calls"] = self.tool_calls

        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id

        if self.name is not None:
            result["name"] = self.name

        return result

    @classmethod
    def user(cls, content: str) -> "Message":
        """创建用户消息"""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None) -> "Message":
        """创建助手消息"""
        return cls(role=MessageRole.ASSISTANT, content=content, tool_calls=tool_calls)

    @classmethod
    def tool(cls, content: str, tool_call_id: str, name: str) -> "Message":
        """创建工具消息"""
        return cls(role=MessageRole.TOOL, content=content, tool_call_id=tool_call_id, name=name)


class AppendOnlyMessageManager:
    """
    Append-only 消息管理器

    核心原则：
    1. 只能追加新消息
    2. 禁止修改历史消息
    3. 禁止删除消息
    4. 保护缓存前缀完整性
    """

    def __init__(self):
        self._messages: List[Message] = []
        self._locked = False

    def append(self, message: Message) -> None:
        """追加新消息（唯一允许的修改操作）"""
        self._messages.append(message)

    def get_messages(self) -> List[Message]:
        """获取消息列表的只读副本"""
        return self._messages.copy()

    def get_api_messages(self) -> List[Dict[str, Any]]:
        """获取 API 格式的消息列表"""
        return [msg.to_dict() for msg in self._messages]

    def __len__(self) -> int:
        """返回消息数量"""
        return len(self._messages)

    def __getitem__(self, index: int) -> Message:
        """允许读取消息"""
        return self._messages[index]

    def __setitem__(self, index: int, value: Any) -> None:
        """禁止修改历史消息"""
        raise RuntimeError(
            "Cannot modify message history! "
            "Modifying messages breaks cache prefix. "
            "Use append() to add new messages only."
        )

    def __delitem__(self, index: int) -> None:
        """禁止删除消息"""
        raise RuntimeError(
            "Cannot delete messages! "
            "Deleting messages breaks cache prefix. "
            "Message history must be append-only."
        )

    def clear(self) -> None:
        """禁止清空消息"""
        raise RuntimeError(
            "Cannot clear message history! "
            "Use a new MessageManager instance for a new session."
        )

    def pop(self, *args, **kwargs) -> None:
        """禁止 pop 操作"""
        raise RuntimeError(
            "Cannot pop messages! "
            "Message history must be append-only."
        )

    def remove(self, *args, **kwargs) -> None:
        """禁止 remove 操作"""
        raise RuntimeError(
            "Cannot remove messages! "
            "Message history must be append-only."
        )

    def insert(self, *args, **kwargs) -> None:
        """禁止 insert 操作"""
        raise RuntimeError(
            "Cannot insert messages! "
            "Use append() to add messages at the end only."
        )

    def __repr__(self) -> str:
        return f"AppendOnlyMessageManager(messages={len(self._messages)})"
