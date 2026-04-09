"""
Generate presentation-friendly charts and summaries from experiment results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
BASELINE_FILE = RESULTS_DIR / "baseline_results.json"
CACHE_BUSTERS_FILE = RESULTS_DIR / "cache_busters_results.json"
SUMMARY_FILE = RESULTS_DIR / "experiment_summary.md"
OVERVIEW_FIGURE = FIGURES_DIR / "cache_overview.png"
BASELINE_TURNS_FIGURE = FIGURES_DIR / "baseline_turns.png"


def load_json(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_legacy_rows(
    baseline: dict[str, Any], cache_busters: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    baseline_metrics = baseline["total_metrics"]
    rows = [
        {
            "group": "legacy",
            "label": "Baseline",
            "hit_rate": baseline_metrics["cache_hit_rate"],
            "cost": baseline_metrics["cost"],
            "delta_hit": 0.0,
            "delta_cost": 0.0,
            "cache_hit_tokens": baseline_metrics["cache_hit_tokens"],
            "cache_miss_tokens": baseline_metrics["cache_miss_tokens"],
        }
    ]

    for item in cache_busters:
        metrics = item["total_metrics"]
        rows.append(
            {
                "group": "legacy",
                "label": item["scenario"],
                "hit_rate": metrics["cache_hit_rate"],
                "cost": metrics["cost"],
                "delta_hit": metrics["cache_hit_rate"] - baseline_metrics["cache_hit_rate"],
                "delta_cost": metrics["cost"] - baseline_metrics["cost"],
                "cache_hit_tokens": metrics["cache_hit_tokens"],
                "cache_miss_tokens": metrics["cache_miss_tokens"],
            }
        )
    return rows


def build_track_rows(cache_busters: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for track_name, track_data in cache_busters["tracks"].items():
        baseline = track_data["baseline"]["total_metrics"]
        rows.append(
            {
                "group": track_name,
                "label": f"{track_name} / Baseline",
                "hit_rate": baseline["cache_hit_rate"],
                "cost": baseline["cost"],
                "delta_hit": 0.0,
                "delta_cost": 0.0,
                "cache_hit_tokens": baseline["cache_hit_tokens"],
                "cache_miss_tokens": baseline["cache_miss_tokens"],
            }
        )

        for item in track_data["scenarios"]:
            metrics = item["total_metrics"]
            rows.append(
                {
                    "group": track_name,
                    "label": f"{track_name} / {item['scenario']}",
                    "hit_rate": metrics["cache_hit_rate"],
                    "cost": metrics["cost"],
                    "delta_hit": metrics["cache_hit_rate"] - baseline["cache_hit_rate"],
                    "delta_cost": metrics["cost"] - baseline["cost"],
                    "cache_hit_tokens": metrics["cache_hit_tokens"],
                    "cache_miss_tokens": metrics["cache_miss_tokens"],
                }
            )

    return rows


def build_comparison_rows(
    baseline: dict[str, Any], cache_busters: dict[str, Any] | list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if isinstance(cache_busters, list):
        return build_legacy_rows(baseline, cache_busters)
    return build_track_rows(cache_busters)


def plot_overview(rows: list[dict[str, Any]]) -> None:
    labels = [row["label"] for row in rows]
    hit_rates = [row["hit_rate"] * 100 for row in rows]
    costs = [row["cost"] for row in rows]
    colors = ["#2f6bff" if "Baseline" in row["label"] else "#ef6c57" for row in rows]

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle("Cache-Aware Agent Experiment Overview", fontsize=16, fontweight="bold")

    axes[0].barh(labels, hit_rates, color=colors)
    axes[0].invert_yaxis()
    axes[0].set_title("Cache Hit Rate")
    axes[0].set_xlabel("Hit Rate (%)")
    axes[0].set_xlim(0, 100)
    for index, value in enumerate(hit_rates):
        axes[0].text(min(value + 1, 99.2), index, f"{value:.2f}%", va="center", fontsize=9)

    axes[1].barh(labels, costs, color=colors)
    axes[1].invert_yaxis()
    axes[1].set_title("Estimated Cost")
    axes[1].set_xlabel("Cost (USD)")
    max_cost = max(costs) if costs else 0.0
    axes[1].set_xlim(0, max_cost * 1.2 if max_cost else 1)
    for index, value in enumerate(costs):
        axes[1].text(value + max_cost * 0.02, index, f"${value:.4f}", va="center", fontsize=9)

    fig.tight_layout()
    OVERVIEW_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OVERVIEW_FIGURE, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_baseline_turns(baseline: dict[str, Any]) -> None:
    metrics = baseline["per_turn_metrics"]
    turns = [item["turn"] for item in metrics]
    hit_rates = [item["cache_hit_rate"] * 100 for item in metrics]
    costs = [item["cost"] for item in metrics]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle("Baseline Per-Turn Trends", fontsize=16, fontweight="bold")

    axes[0].plot(turns, hit_rates, marker="o", color="#2f6bff", linewidth=2)
    axes[0].set_ylabel("Hit Rate (%)")
    axes[0].set_ylim(0, 100)
    axes[0].grid(alpha=0.3)

    axes[1].plot(turns, costs, marker="o", color="#ef6c57", linewidth=2)
    axes[1].set_ylabel("Cost (USD)")
    axes[1].set_xlabel("Turn")
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    BASELINE_TURNS_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(BASELINE_TURNS_FIGURE, dpi=160, bbox_inches="tight")
    plt.close(fig)


def write_summary(rows: list[dict[str, Any]]) -> None:
    lines = ["# Experiment Summary", ""]
    groups = sorted({row["group"] for row in rows})

    for group in groups:
        group_rows = [row for row in rows if row["group"] == group]
        lines.extend(
            [
                f"## {group}",
                "",
                "| Scenario | Hit Rate | Delta vs Baseline | Cost | Delta Cost | Cache Hit Tokens | Cache Miss Tokens |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )

        for row in group_rows:
            lines.append(
                "| {label} | {hit_rate:.2%} | {delta_hit:+.2%} | ${cost:.4f} | ${delta_cost:+.4f} | {cache_hit_tokens:,} | {cache_miss_tokens:,} |".format(
                    **row
                )
            )

        strongest_drop = min(
            [row for row in group_rows if "Baseline" not in row["label"]],
            key=lambda item: item["delta_hit"],
            default=None,
        )
        if strongest_drop:
            lines.extend(
                [
                    "",
                    f"Key takeaway: **{strongest_drop['label']}** shows the largest drop in this track.",
                    "",
                ]
            )

    SUMMARY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    baseline = load_json(BASELINE_FILE)
    cache_busters = load_json(CACHE_BUSTERS_FILE)

    rows = build_comparison_rows(baseline, cache_busters)
    plot_overview(rows)
    plot_baseline_turns(baseline)
    write_summary(rows)

    print("Generated artifacts:")
    print(f"- {OVERVIEW_FIGURE.relative_to(ROOT)}")
    print(f"- {BASELINE_TURNS_FIGURE.relative_to(ROOT)}")
    print(f"- {SUMMARY_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
