"""
Cache breaker experiments split into two interpretable tracks:

1. schema_only:
   Focuses on prompt/message/session stability without active tool execution.
2. execution_enabled:
   Enables the minimal read_file/echo_json tool loop so tool-related cache
   breakage can be evaluated separately from pure prefix stability issues.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Type

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import CacheAwareAgent


RESULTS_DIR = Path("results")
COMBINED_OUTPUT = RESULTS_DIR / "cache_busters_results.json"
SCHEMA_OUTPUT = RESULTS_DIR / "cache_busters_schema_only.json"
EXECUTION_OUTPUT = RESULTS_DIR / "cache_busters_execution_enabled.json"

SCHEMA_ONLY_QUESTIONS = [
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

EXECUTION_ENABLED_QUESTIONS = [
    "Use the read_file tool to inspect README.md and summarize the project goal.",
    "Use the read_file tool to inspect core/prompt_manager.py and explain the BOUNDARY design.",
    "Use the read_file tool to inspect core/message_manager.py and explain how append-only history is enforced.",
    "Use the read_file tool to inspect core/tool_cache.py and summarize the tool schema caching strategy.",
    "Use the read_file tool to inspect README.md and list the current tools status section.",
]


class BrokenAgent1_TimestampInStatic(CacheAwareAgent):
    """Inject a dynamic timestamp into the static prompt section."""

    def _initialize_dynamic_section(self) -> None:
        self.prompt_manager.add_static_section(f"Current timestamp: {time.time()}")
        super()._initialize_dynamic_section()


class BrokenAgent2_DynamicTools(CacheAwareAgent):
    """Change the exposed tool set between turns while keeping read_file available."""

    def _get_enabled_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = super()._get_enabled_tool_schemas()
        if random.random() > 0.5:
            return [schema for schema in schemas if schema["function"]["name"] != "echo_json"]
        return schemas


class BrokenAgent3_UnstableToolOrder(CacheAwareAgent):
    """Shuffle tool order on each request."""

    def _get_enabled_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = super()._get_enabled_tool_schemas()
        random.shuffle(schemas)
        return schemas


class BrokenAgent4_ModifyHistory(CacheAwareAgent):
    """Mutate the first historical user message after the first turn."""

    def _append_user_message(self, user_message: str) -> None:
        super()._append_user_message(user_message)
        if len(self.message_manager) > 1:
            self.message_manager._messages[0].content += f" [Modified at {time.time()}]"


class BrokenAgent5_NonDeterministicSerialization(CacheAwareAgent):
    """Rebuild tool schemas with randomly ordered keys on each request."""

    def _shuffle_structure(self, value: Any) -> Any:
        if isinstance(value, dict):
            items = list(value.items())
            random.shuffle(items)
            return {key: self._shuffle_structure(item_value) for key, item_value in items}
        if isinstance(value, list):
            return [self._shuffle_structure(item) for item in value]
        return value

    def _get_enabled_tool_schemas(self) -> List[Dict[str, Any]]:
        schemas = super()._get_enabled_tool_schemas()
        return [self._shuffle_structure(schema) for schema in schemas]


class BrokenAgent6_ModelSwitch(CacheAwareAgent):
    """Switch models between requests inside the same session."""

    def _create_completion(self, messages: List[Dict[str, Any]]) -> Any:
        self.session_config.model = random.choice(["deepseek-chat", "deepseek-reasoner"])
        return super()._create_completion(messages)


TRACK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "schema_only": {
        "title": "Schema-Only Track",
        "questions": SCHEMA_ONLY_QUESTIONS,
        "agent_kwargs": {
            "enable_tools": False,
            "temperature": 0.7,
        },
        "baseline_dynamic_section": "Track mode: schema-only. Answer directly without using tools.",
        "scenarios": [
            (BrokenAgent1_TimestampInStatic, "1. Timestamp in Static Section"),
            (BrokenAgent4_ModifyHistory, "4. Modify Message History"),
            (BrokenAgent6_ModelSwitch, "6. Model Switch Mid-Session"),
        ],
        "output_file": SCHEMA_OUTPUT,
    },
    "execution_enabled": {
        "title": "Execution-Enabled Track",
        "questions": EXECUTION_ENABLED_QUESTIONS,
        "agent_kwargs": {
            "enable_tools": True,
            "max_tool_rounds": 1,
            "temperature": 0.0,
        },
        "baseline_dynamic_section": "Track mode: execution-enabled. Use tools when the user explicitly asks for file inspection.",
        "scenarios": [
            (BrokenAgent2_DynamicTools, "2. Dynamic Tool Add/Remove"),
            (BrokenAgent3_UnstableToolOrder, "3. Unstable Tool Order"),
            (BrokenAgent5_NonDeterministicSerialization, "5. Non-Deterministic Serialization"),
        ],
        "output_file": EXECUTION_OUTPUT,
    },
}


def create_agent(agent_class: Type[CacheAwareAgent], track_name: str) -> CacheAwareAgent:
    config = TRACK_CONFIGS[track_name]
    agent = agent_class(
        model="deepseek-chat",
        max_tokens=1024,
        **config["agent_kwargs"],
    )
    agent.prompt_manager.add_dynamic_section(config["baseline_dynamic_section"])
    return agent


def run_track_baseline(track_name: str, num_turns: int) -> Dict[str, Any]:
    config = TRACK_CONFIGS[track_name]
    agent = create_agent(CacheAwareAgent, track_name)

    print(f"\n{'=' * 80}")
    print(f"Baseline: {config['title']}")
    print(f"{'=' * 80}\n")

    for turn, question in enumerate(config["questions"][:num_turns], 1):
        print(f"[Turn {turn}] User: {question}")
        result = agent.send_message(question, verbose=True)
        preview = (result["content"] or "")[:150]
        print(f"[Turn {turn}] Assistant: {preview}...\n")

    total_metrics = agent.get_total_metrics()
    return {
        "scenario": "Baseline",
        "total_metrics": {
            "cache_hit_rate": total_metrics.cache_hit_rate,
            "cost": total_metrics.cost_estimate,
            "cache_hit_tokens": total_metrics.cache_hit_tokens,
            "cache_miss_tokens": total_metrics.cache_miss_tokens,
            "prompt_tokens": total_metrics.prompt_tokens,
            "completion_tokens": total_metrics.completion_tokens,
        },
    }


def run_cache_buster_experiment(
    agent_class: Type[CacheAwareAgent],
    scenario_name: str,
    track_name: str,
    num_turns: int,
) -> Dict[str, Any]:
    config = TRACK_CONFIGS[track_name]

    print(f"\n{'=' * 80}")
    print(f"{config['title']} | Scenario: {scenario_name}")
    print(f"{'=' * 80}\n")

    agent = create_agent(agent_class, track_name)

    for turn, question in enumerate(config["questions"][:num_turns], 1):
        print(f"[Turn {turn}] User: {question}")
        result = agent.send_message(question, verbose=True)
        preview = (result["content"] or "")[:150]
        print(f"[Turn {turn}] Assistant: {preview}...\n")

    total_metrics = agent.get_total_metrics()
    print(f"\nResults for {scenario_name}:")
    print(f"  Cache Hit Rate: {total_metrics.cache_hit_rate:.1%}")
    print(f"  Total Cost: ${total_metrics.cost_estimate:.6f}")

    return {
        "scenario": scenario_name,
        "total_metrics": {
            "cache_hit_rate": total_metrics.cache_hit_rate,
            "cost": total_metrics.cost_estimate,
            "cache_hit_tokens": total_metrics.cache_hit_tokens,
            "cache_miss_tokens": total_metrics.cache_miss_tokens,
            "prompt_tokens": total_metrics.prompt_tokens,
            "completion_tokens": total_metrics.completion_tokens,
        },
    }


def run_track(track_name: str, num_turns: int) -> Dict[str, Any]:
    config = TRACK_CONFIGS[track_name]

    baseline = run_track_baseline(track_name, num_turns)
    scenarios = [
        run_cache_buster_experiment(agent_class, scenario_name, track_name, num_turns)
        for agent_class, scenario_name in config["scenarios"]
    ]

    track_results = {
        "track": track_name,
        "title": config["title"],
        "num_turns": num_turns,
        "baseline": baseline,
        "scenarios": scenarios,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    config["output_file"].write_text(
        json.dumps(track_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return track_results


def run_all_cache_busters(num_turns: int = 5) -> Dict[str, Any]:
    print("=" * 80)
    print("Cache Busters Experiment: Split Tracks")
    print("=" * 80)

    schema_only = run_track("schema_only", num_turns)
    execution_enabled = run_track("execution_enabled", num_turns)

    combined = {
        "experiment": "cache_busters",
        "tracks": {
            "schema_only": schema_only,
            "execution_enabled": execution_enabled,
        },
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    COMBINED_OUTPUT.write_text(
        json.dumps(combined, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {COMBINED_OUTPUT}")
    print(f"Schema-only track saved to: {SCHEMA_OUTPUT}")
    print(f"Execution-enabled track saved to: {EXECUTION_OUTPUT}")

    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run cache breaker experiments in schema-only or execution-enabled mode."
    )
    parser.add_argument(
        "--track",
        choices=["all", "schema_only", "execution_enabled"],
        default="all",
        help="Which experiment track to run.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=5,
        help="Number of turns to run per track.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for repeatable scenario behavior.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    random.seed(args.seed)

    if args.track == "all":
        run_all_cache_busters(num_turns=args.turns)
    else:
        result = run_track(args.track, args.turns)
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
