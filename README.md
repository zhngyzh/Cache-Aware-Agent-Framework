# Cache-Aware Agent Framework

受 Claude Code prompt 分层思路启发的缓存友好型 Agent 实验框架，用于验证 prompt 前缀稳定性如何影响缓存命中率、Token 消耗和 API 成本。

## 项目定位

这个项目当前聚焦两件事：

1. 设计一套适合 prompt caching 的多轮对话框架
2. 通过对比实验量化常见 cache breaker 对命中率和成本的影响

当前版本的重点是 `prompt / message / tool schema` 的稳定性验证，以及最小可用的 tool-calling 闭环，而不是完整的生产级工具平台。

## 当前完成度

已完成：

- 静态 Prompt 与会话动态信息分层
- `BOUNDARY` 分界线设计
- Append-only 消息历史管理
- 稳定的 tool schema 缓存与确定性序列化
- Session 配置锁存，避免会话中切换关键参数
- 最小可用的 tool-calling loop
- `schema-only` / `execution-enabled` 双轨实验设计
- 结果可视化与实验摘要生成

当前已支持的最小确定性工具：

- `read_file`
- `echo_json`

暂未作为当前主线完成：

- 多轮 tool-call agent loop
- 更多可执行工具与权限控制
- 面向生产场景的工具编排与容错

## 四层缓存友好架构

```text
Layer 1: Static System Prompt
  - 身份定义
  - 能力说明
  - 规则约束

Layer 2: Session-Specific Guidance
  - 当前日期
  - 模型信息
  - 工作目录
  - BOUNDARY 分界

Layer 3: Tool Definitions
  - 稳定的工具数组
  - 按名称排序
  - 确定性 JSON 序列化

Layer 4: Append-Only Message History
  - 用户消息
  - 助手消息
  - tool 消息
```

对应代码：

- [prompt_manager.py](/C:/Users/依智/Downloads/cache/core/prompt_manager.py)
- [message_manager.py](/C:/Users/依智/Downloads/cache/core/message_manager.py)
- [tool_cache.py](/C:/Users/依智/Downloads/cache/core/tool_cache.py)
- [tool_executor.py](/C:/Users/依智/Downloads/cache/core/tool_executor.py)
- [agent.py](/C:/Users/依智/Downloads/cache/core/agent.py)

## 实验设计

### Baseline

Baseline 保持所有缓存友好约束成立：

- 静态 Prompt 与动态会话信息分离
- 消息历史只追加、不修改
- 工具定义稳定
- 会话配置锁存

结果文件：

- [baseline_results.json](/C:/Users/依智/Downloads/cache/results/baseline_results.json)

### Cache Breakers

项目将 cache breaker 拆成两条更容易解释的轨道。

`schema-only`

- 不启用真实工具执行
- 重点观察 prompt、message history、session 配置对缓存前缀的影响
- 主要场景：时间戳注入、修改历史消息、模型切换

`execution-enabled`

- 启用最小 tool-calling loop
- 基于 `read_file` / `echo_json` 这类确定性工具
- 重点观察工具集合、工具顺序、tool schema 稳定性对缓存的影响

结果文件：

- [cache_busters_results.json](/C:/Users/依智/Downloads/cache/results/cache_busters_results.json)
- [cache_busters_schema_only.json](/C:/Users/依智/Downloads/cache/results/cache_busters_schema_only.json)
- [cache_busters_execution_enabled.json](/C:/Users/依智/Downloads/cache/results/cache_busters_execution_enabled.json)

## 关键结果

旧版单轨 baseline 结果：

- 命中率 `98.23%`
- 成本约 `$0.0210`

新版双轨结果：

`schema-only` baseline

- 命中率 `92.56%`
- 成本约 `$0.0063`

`schema-only` 下降最明显的场景：

- `Modify Message History` 命中率降到 `32.99%`
- 相对 baseline 下降 `59.57` 个百分点

`execution-enabled` baseline

- 命中率 `85.58%`
- 成本约 `$0.0188`

`execution-enabled` 下降最明显的场景：

- `Non-Deterministic Serialization` 命中率降到 `12.36%`
- 相对 baseline 下降 `73.23` 个百分点

这说明：

- 在不启用工具执行时，消息历史稳定性仍然是最强信号
- 在启用最小 tool loop 后，tool schema 的确定性与顺序稳定性会显著影响缓存效果

实验摘要与图表：

- [experiment_summary.md](/C:/Users/依智/Downloads/cache/results/experiment_summary.md)
- [cache_overview.png](/C:/Users/依智/Downloads/cache/results/figures/cache_overview.png)
- [baseline_turns.png](/C:/Users/依智/Downloads/cache/results/figures/baseline_turns.png)

## 结果解读边界

为了避免过度包装，当前版本对实验结论做如下约束：

- 这个项目已经验证了 prompt 前缀稳定性、消息历史稳定性、配置锁存、tool schema 稳定性对缓存命中率的影响
- 当前已实现最小可用的 tool-calling loop，但还不是完整的生产级 tool agent
- `execution-enabled` 轨道适合说明“真实工具调用场景下的结构稳定性”，但不等同于复杂工具编排平台验证
- 成本不只受命中率影响，也受总 prompt/completion token 数量影响，因此个别场景可能出现“命中率下降但总成本未同步升高”的情况

## 项目结构

```text
cache/
├── core/
│   ├── agent.py
│   ├── message_manager.py
│   ├── prompt_manager.py
│   ├── tool_cache.py
│   └── tool_executor.py
├── experiments/
│   ├── baseline.py
│   ├── cache_busters.py
│   └── visualize_results.py
├── results/
│   ├── baseline_results.json
│   ├── cache_busters_results.json
│   ├── cache_busters_schema_only.json
│   ├── cache_busters_execution_enabled.json
│   ├── experiment_summary.md
│   └── figures/
├── tests/
├── requirements.txt
└── README.md
```

## 快速开始

```bash
uv pip install -r requirements.txt
python experiments/baseline.py
python experiments/cache_busters.py --track all --turns 5 --seed 42
python experiments/visualize_results.py
```

更细粒度的运行方式：

```bash
# 只跑 schema-only 轨道
python experiments/cache_busters.py --track schema_only --turns 5 --seed 42

# 只跑 execution-enabled 轨道
python experiments/cache_busters.py --track execution_enabled --turns 5 --seed 42

# 同时跑两条轨道
python experiments/cache_busters.py --track all --turns 5 --seed 42
```

## 当前 Tools 状态

项目现在已经实现了第一版最小 tool-calling 闭环：

- assistant 返回 `tool_calls`
- 本地执行工具
- 追加 `tool` role 消息
- 再次请求模型生成最终回答

默认情况下 tools 不启用，这样不会影响现有 baseline / cache breaker 实验。

如果要手动启用最小 tool loop，可以这样初始化：

```python
from core.agent import CacheAwareAgent

agent = CacheAwareAgent(
    enable_tools=True,
    max_tool_rounds=1,
)
```

测试命令：

```bash
.venv\Scripts\python -m unittest discover -s tests
```

## 结果可视化

```bash
python experiments/visualize_results.py
```

输出文件：

- [cache_overview.png](/C:/Users/依智/Downloads/cache/results/figures/cache_overview.png)
- [baseline_turns.png](/C:/Users/依智/Downloads/cache/results/figures/baseline_turns.png)
- [experiment_summary.md](/C:/Users/依智/Downloads/cache/results/experiment_summary.md)

这些产物适合直接用于 README 展示、项目答辩或简历附件材料。

## 技术栈

- Python 3.12
- DeepSeek API
- OpenAI-compatible SDK
- `python-dotenv`
- `matplotlib`
- `pandas`

## 简历写法参考

项目一句话版本：

> 设计并实现了一个受 Claude Code 启发的 cache-aware agent framework，通过双轨 cache breaker 实验量化验证 prompt 前缀稳定性、消息历史稳定性与 tool schema 稳定性对缓存命中率和 API 成本的影响。

简历 bullet 版本：

- 设计 Cache-Aware Agent 框架，拆分静态 Prompt、会话动态信息、稳定 tool schema 与 append-only message history，面向多轮对话场景优化 prompt caching 命中率。
- 实现最小可用的 tool-calling loop，并基于 `read_file` / `echo_json` 构建 `execution-enabled` 实验轨道，使工具调用场景下的缓存稳定性可以独立分析。
- 构建 `schema-only` 与 `execution-enabled` 双轨 cache breaker 实验；在 `schema-only` 轨道中，修改历史消息使命中率从 `92.56%` 降到 `32.99%`，在 `execution-enabled` 轨道中，非确定性序列化使命中率从 `85.58%` 降到 `12.36%`。

## 后续规划

- 扩展更多安全、确定性的本地工具
- 实现多轮 tool-call agent loop
- 增加重复实验、固定随机性与统计汇总
- 补充更细粒度的测试与结果图表
