# Project Guidelines

## Code Style
- 使用 Python 3.12 风格与类型注解，保持函数与数据类职责单一。
- 仅做最小必要改动，避免无关重构或格式化噪音。
- 新增逻辑优先与现有组件保持一致：`@dataclass`、显式方法命名、清晰 docstring。

## Architecture
- `core/`：缓存优化框架核心。
- `core/prompt_manager.py`：四层 Prompt 架构，静态段与动态段由 `# Session-specific guidance` 分界。
- `core/message_manager.py`：消息历史必须 append-only，禁止修改/删除历史消息。
- `core/tool_cache.py`：工具定义缓存与确定性序列化，保证字节级稳定。
- `core/agent.py`：会话配置锁存（Latch）、请求发送与缓存指标统计。
- `experiments/`：实验脚本（baseline 与 cache busters）。
- `results/`：实验输出 JSON，不在实现改动中手动篡改历史结果文件。

更多背景见 [README](../README.md)。

## Build and Run
- 安装依赖：`uv pip install -r requirements.txt`
- 基线实验：`python experiments/baseline.py`
- 破坏场景实验：`python experiments/cache_busters.py`

运行前确保设置 `DEEPSEEK_API_KEY`（可通过 `.env`）。

## Conventions
- 缓存稳定性优先，尤其是以下约定：
- System Prompt 静态段保持稳定；动态信息仅放在分界线之后。
- 消息历史只追加，不回写历史内容。
- 工具定义必须稳定：不在会话中动态增删工具，不改变工具顺序。
- JSON 序列化必须确定性：`json.dumps(..., sort_keys=True, ensure_ascii=False)`。
- 会话中不要切换模型或变更关键 session 配置。

六大反模式与影响见 [README 的 Cache Busters 章节](../README.md#cache-busters-六大破坏场景)。

## Agent Editing Guardrails
- 修改 `core/` 时，优先检查是否会降低缓存命中率或破坏缓存前缀稳定性。
- 若必须改动协议（消息结构、工具 schema、Prompt 结构），同步更新 `experiments/` 以保证对比实验可复现。
- 除非任务明确要求，不要引入与缓存研究无关的新基础设施。
