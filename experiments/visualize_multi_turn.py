"""
Visualize multi-turn tool orchestration experiment results.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from experiments.visualize_results import (
    format_cost_with_std,
    format_percent_with_std,
    build_tool_observability_sections,
)


def visualize_multi_turn_results(results_file: Path) -> None:
    with open(results_file, encoding="utf-8") as f:
        results = json.load(f)

    print()
    print("=" * 80)
    print("Multi-Turn Tool Orchestration Experiment Results")
    print("=" * 80)
    print()

    print(f"Experiment: {results['experiment']}")
    print(f"Schema Version: {results['schema_version']}")
    print(f"Turns per Run: {results['num_turns']}")
    print(f"Repeats per Config: {results['repeat_count']}")
    print(f"Configurations Tested: {', '.join(str(x) for x in results['max_tool_rounds_tested'])}")
    print()

    print("=" * 80)
    print("Configuration Comparison")
    print("=" * 80)
    print()

    configs = results["configurations"]

    # Header
    print(f"{'Config':<18} {'Cache Hit Rate':<22} {'Total Cost':<22} {'Tool Exec':<12}")
    print("-" * 74)

    for config_name in sorted(configs.keys()):
        config_data = configs[config_name]
        summary = config_data["summary"]
        metrics = summary["aggregate_total_metrics"]
        tool_obs = summary.get("aggregate_tool_observability", {}).get("metrics", {})

        hit_rate = format_percent_with_std(
            metrics["cache_hit_rate"]["mean"],
            metrics["cache_hit_rate"]["std"]
        )
        cost = format_cost_with_std(
            metrics["cost"]["mean"],
            metrics["cost"]["std"]
        )
        tool_exec = tool_obs.get("total_tool_executions", {}).get("mean", 0)

        print(f"{config_name:<18} {hit_rate:<22} {cost:<22} {tool_exec:<12.1f}")

    print()
    print("=" * 80)
    print("Detailed Analysis by Configuration")
    print("=" * 80)

    for config_name in sorted(configs.keys()):
        config_data = configs[config_name]
        summary = config_data["summary"]
        metrics = summary["aggregate_total_metrics"]
        tool_obs = summary.get("aggregate_tool_observability", {}).get("metrics", {})

        print()
        print(f"## {config_name}")
        print()

        print("Cache Metrics:")
        print(f"  Hit Rate: {format_percent_with_std(metrics['cache_hit_rate']['mean'], metrics['cache_hit_rate']['std'])}")
        print(f"  Total Cost: {format_cost_with_std(metrics['cost']['mean'], metrics['cost']['std'])}")
        print(f"  Prompt Tokens: {metrics['prompt_tokens']['mean']:.0f} +/- {metrics['prompt_tokens']['std']:.0f}")
        print(f"  Cache Hit Tokens: {metrics['cache_hit_tokens']['mean']:.0f} +/- {metrics['cache_hit_tokens']['std']:.0f}")
        print(f"  Cache Miss Tokens: {metrics['cache_miss_tokens']['mean']:.0f} +/- {metrics['cache_miss_tokens']['std']:.0f}")
        print()

        if tool_obs:
            print("Tool Observability:")
            total_exec = tool_obs.get("total_tool_executions", {}).get("mean", 0)
            successful = tool_obs.get("successful_tool_executions", {}).get("mean", 0)
            failed = tool_obs.get("failed_tool_executions", {}).get("mean", 0)

            print(f"  Total Tool Executions: {total_exec:.1f}")
            print(f"  Successful: {successful:.1f}")
            print(f"  Failed: {failed:.1f}")

            if "tools_executed" in tool_obs:
                print(f"  Tools Used: {', '.join(tool_obs['tools_executed'])}")

            terminated = tool_obs.get("turns_terminated_by_max_rounds", {}).get("mean", 0)
            if terminated > 0:
                print(f"  Turns Terminated by max_tool_rounds: {terminated:.1f}")
            print()

    print()
    print("=" * 80)
    print("Key Insights")
    print("=" * 80)
    print()

    # Compare max_rounds_1 vs max_rounds_2
    if "max_rounds_1" in configs and "max_rounds_2" in configs:
        r1_metrics = configs["max_rounds_1"]["summary"]["aggregate_total_metrics"]
        r2_metrics = configs["max_rounds_2"]["summary"]["aggregate_total_metrics"]

        hit_rate_diff = r1_metrics["cache_hit_rate"]["mean"] - r2_metrics["cache_hit_rate"]["mean"]
        cost_diff = r2_metrics["cost"]["mean"] - r1_metrics["cost"]["mean"]

        print(f"max_rounds_1 vs max_rounds_2:")
        print(f"  Cache Hit Rate: {hit_rate_diff:+.2%} (higher is better)")
        print(f"  Cost Difference: ${cost_diff:+.4f} (max_rounds_2 costs more)")
        print()

    print("Observations:")
    print("  - Higher max_tool_rounds allows more tool orchestration")
    print("  - More tool rounds = more API calls = higher cost")
    print("  - Cache hit rate may vary based on conversation complexity")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize multi-turn tool orchestration results.")
    parser.add_argument(
        "results_file",
        type=Path,
        help="Path to the multi_turn_tools_results.json file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    visualize_multi_turn_results(args.results_file)
