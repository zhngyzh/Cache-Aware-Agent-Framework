# Prompt Cache Stability Experiments for Tool-Using Agents

This repository is an experiment project, not a general-purpose agent framework.
It studies how prompt-prefix stability, append-only history, and deterministic
tool definitions affect cache hit rate, token usage, and API cost in tool-using
LLM agents.

## Scope

This project focuses on two questions:

1. How should a tool-using agent be structured to stay cache-friendly?
2. How much do common cache breakers hurt hit rate and cost in repeatable runs?

Implemented today:

- Four-layer cache-friendly request structure
- Append-only message history
- Deterministic tool schema serialization
- Full tool-calling loop with bounded multi-turn orchestration
- Repeatable experiments, aggregate summaries, and result visualization

Out of scope:

- Production-grade orchestration
- Rich permissioning and scheduling systems
- Broad agent platform abstractions

## Core Design

```text
Layer 1: Static System Prompt
  - role and rules
  - stable across the whole session

Layer 2: Session Configuration
  - model / temperature / max_tokens / timestamp
  - latched when the session starts

Layer 3: Tool Definitions
  - stable schemas
  - sorted by name
  - deterministically serialized

Layer 4: Append-Only Message History
  - user / assistant / tool messages
  - append only, no mutation, no deletion
```

Main implementation files:

- `core/prompt_manager.py`
- `core/message_manager.py`
- `core/tool_cache.py`
- `core/tool_executor.py`
- `core/agent.py`

Technical detail lives in `ARCHITECTURE.md`.

## Experiment Layout

### Baseline

`baseline.py` represents the cache-friendly implementation with:

- static prompt separated from dynamic session data
- append-only message history
- stable tool definitions
- latched session configuration

### Cache Breakers

`cache_busters.py` has two tracks.

`schema-only`

- no real tool execution
- measures instability from prompt, message history, and session config changes

`execution-enabled`

- enables the minimal tool loop
- measures instability from tool set changes, ordering changes, and schema serialization

### Multi-Turn Tool Orchestration

`multi_turn_tools.py` compares different `max_tool_rounds` settings and records:

- cache hit rate
- total cost
- tool execution count
- truncation caused by `max_tool_rounds`

## Result Snapshot

Official experiment configuration:

- `turns = 5`
- `repeats = 5`
- `seed = 42`

### Baseline

- Cache Hit Rate: `97.98% +/- 0.28%`
- Total Cost: `$0.0094 +/- $0.0015`

### Schema-Only Track

- Baseline: `95.59% +/- 1.56%`
- `Modify Message History`: `19.21% +/- 2.92%`
- `Model Switch Mid-Session`: `76.65% +/- 11.63%`

Takeaway:

- editing old messages is the strongest cache breaker in this track

### Execution-Enabled Track

Takeaways:

- non-deterministic serialization is the strongest cache breaker
- tool execution success rate is `100%`
- the observed differences come from structural instability, not execution noise

### Multi-Turn Tool Orchestration

| Config | Cache Hit Rate | Total Cost | Tool Exec |
|--------|----------------|------------|-----------|
| max_rounds_1 | 85.24% +/- 1.68% | $0.0141 +/- $0.0038 | 5.0 |
| max_rounds_2 | 86.43% +/- 2.09% | $0.0422 +/- $0.0031 | 9.0 |
| max_rounds_3 | 84.94% +/- 1.65% | $0.0560 +/- $0.0031 | 10.0 |

Takeaways:

- higher `max_tool_rounds` allows deeper orchestration
- cost rises quickly as orchestration depth increases
- the useful tradeoff is capability versus cost, not simply "more rounds is better"

Result files:

- `results/baseline_results.json`
- `results/cache_busters_results.json`
- `results/multi_turn_tools_results.json`
- `results/experiment_summary.md`

## Running

### Install

```bash
uv pip install -r requirements.txt
```

### Full Experiments

```bash
python experiments/baseline.py --turns 5 --seed 42 --repeats 5
python experiments/cache_busters.py --track all --turns 5 --seed 42 --repeats 5
python experiments/multi_turn_tools.py --turns 5 --seed 42 --repeats 5
python experiments/visualize_results.py
python experiments/visualize_multi_turn.py results/multi_turn_tools_results.json
```

### Smoke Test

```bash
python experiments/baseline.py --turns 1 --seed 42 --repeats 1 --output-dir results/dev_smoke
python experiments/cache_busters.py --track all --turns 1 --seed 42 --repeats 1 --output-dir results/dev_smoke
python experiments/multi_turn_tools.py --turns 2 --seed 42 --repeats 2 --output-dir results/dev_smoke
python experiments/visualize_results.py --results-dir results/dev_smoke
python experiments/visualize_multi_turn.py results/dev_smoke/multi_turn_tools_results.json
```

### Tests

```bash
python -m unittest discover -s tests
```

Current test count: `29`

## Default Tools

The default deterministic local tools are:

- `echo_json`
- `list_directory`
- `read_file`
- `search_content`
- `write_file`

Shared constraints:

- stable schema serialization
- workspace-bounded file access
- structured outputs
- traceable execution summaries and error codes

## Repository Layout

```text
core/
  agent.py
  prompt_manager.py
  message_manager.py
  tool_cache.py
  tool_executor.py

experiments/
  baseline.py
  cache_busters.py
  multi_turn_tools.py
  visualize_results.py
  visualize_multi_turn.py

results/
  *.json
  figures/

tests/
  test_*.py
```

## Tech Stack

- Python 3.11+
- OpenAI-compatible API
- `unittest`
- `matplotlib`

## Limits

- This is an experiment repo, not a production agent platform
- The tool set stays intentionally small to preserve determinism and interpretability
- Cost is affected by both cache hit rate and prompt/completion token volume
- These results are useful for cache-friendly design decisions, not for claiming full production readiness
