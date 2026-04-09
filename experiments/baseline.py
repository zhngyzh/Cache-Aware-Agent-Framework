"""
Baseline 实验：正确的 Cache-Aware 实现

验证四层架构的缓存效果：
- 静态 System Prompt（全局缓存）
- BOUNDARY 分隔
- 动态信息在 <system-reminder> 中
- Append-only 消息管理
- 工具定义缓存
- 配置锁存
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import CacheAwareAgent, CacheMetrics
import json


def run_baseline_experiment(num_turns: int = 10):
    """
    运行 Baseline 实验

    模拟一个多轮对话，验证缓存命中率
    """
    print("=" * 80)
    print("Baseline Experiment: Cache-Aware Agent")
    print("=" * 80)
    print()

    # 创建 Agent
    agent = CacheAwareAgent(
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=1024,
    )

    print(f"Session Config (Latched):")
    print(json.dumps(agent.session_config.to_dict(), indent=2))
    print()

    print(f"System Prompt Preview:")
    system_prompt = agent.prompt_manager.build_system_prompt()
    print(system_prompt[:500] + "...")
    print()

    print(f"Tool Cache: {len(agent.tool_cache)} tools registered")
    print()

    # 模拟对话
    questions = [
        "What is prompt caching?",
        "How does the four-layer architecture work?",
        "What is the BOUNDARY marker for?",
        "Explain append-only message management",
        "Why is tool definition caching important?",
        "What is Latch configuration?",
        "How does deterministic serialization help?",
        "What happens if we modify message history?",
        "Why should we avoid changing tools mid-session?",
        "Summarize the key cache optimization strategies",
    ]

    print(f"Running {num_turns} turns...")
    print("-" * 80)

    for i, question in enumerate(questions[:num_turns], 1):
        print(f"\n[Turn {i}] User: {question}")

        result = agent.send_message(question, verbose=True)

        print(f"[Turn {i}] Assistant: {result['content'][:200]}...")

    print()
    print("=" * 80)
    print("Experiment Results")
    print("=" * 80)

    # 汇总指标
    total_metrics = agent.get_total_metrics()

    print(f"\nTotal Metrics:")
    print(f"  Prompt Tokens: {total_metrics.prompt_tokens:,}")
    print(f"  Completion Tokens: {total_metrics.completion_tokens:,}")
    print(f"  Cache Hit Tokens: {total_metrics.cache_hit_tokens:,}")
    print(f"  Cache Miss Tokens: {total_metrics.cache_miss_tokens:,}")
    print(f"  Cache Hit Rate: {total_metrics.cache_hit_rate:.1%}")
    print(f"  Total Cost: ${total_metrics.cost_estimate:.6f}")

    # 逐轮分析
    print(f"\nPer-Turn Analysis:")
    print(f"{'Turn':<6} {'Hit':<10} {'Miss':<10} {'Rate':<8} {'Cost':<12}")
    print("-" * 56)

    for i, metrics in enumerate(agent.metrics_history, 1):
        print(f"{i:<6} {metrics.cache_hit_tokens:<10,} {metrics.cache_miss_tokens:<10,} "
              f"{metrics.cache_hit_rate:<7.1%} ${metrics.cost_estimate:<11.6f}")

    # 保存结果
    results = {
        "experiment": "baseline",
        "num_turns": num_turns,
        "total_metrics": {
            "prompt_tokens": total_metrics.prompt_tokens,
            "completion_tokens": total_metrics.completion_tokens,
            "cache_hit_tokens": total_metrics.cache_hit_tokens,
            "cache_miss_tokens": total_metrics.cache_miss_tokens,
            "cache_hit_rate": total_metrics.cache_hit_rate,
            "cost": total_metrics.cost_estimate,
        },
        "per_turn_metrics": [
            {
                "turn": i,
                "cache_hit_tokens": m.cache_hit_tokens,
                "cache_miss_tokens": m.cache_miss_tokens,
                "cache_hit_rate": m.cache_hit_rate,
                "cost": m.cost_estimate,
            }
            for i, m in enumerate(agent.metrics_history, 1)
        ]
    }

    output_file = "results/baseline_results.json"
    os.makedirs("results", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")

    return results


if __name__ == "__main__":
    run_baseline_experiment(num_turns=10)
