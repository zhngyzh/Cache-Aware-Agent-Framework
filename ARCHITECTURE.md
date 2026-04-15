# Prompt Cache Stability Architecture

This document explains the technical design behind the experiment repository.
It is scoped to cache-friendly prompt construction, deterministic tool
definitions, and append-only message history for tool-using agents. It is not
intended to describe a general-purpose production orchestration platform.

## Four Layers

```text
Layer 1: Static System Prompt
  - role definition
  - tool usage rules
  - stable across the session

Layer 2: Session Configuration
  - model / temperature / max_tokens / timestamp
  - latched at session start

Layer 3: Tool Schema Cache
  - stable tool schemas
  - sorted by tool name
  - deterministically serialized

Layer 4: Append-Only Message History
  - user / assistant / tool messages
  - append only
```

## Design Principles

### Prefix Stability

Prompt caching depends on repeated prefixes. The design therefore keeps layers
1-3 stable and lets layer 4 grow only by appending new messages.

### Deterministic Serialization

Equivalent tool definitions must serialize to the same bytes. The project uses
sorted tool names and deterministic JSON serialization to avoid accidental
cache misses.

### Append-Only History

Old messages are not edited or deleted. This protects the cached prefix and
makes trace analysis easier.

### Latched Session Configuration

Session configuration is created once and then treated as immutable so that the
request prefix does not drift mid-session.

## Tool Execution Layer

The local tool layer is intentionally small and deterministic.

Properties:

- workspace-bounded file access
- structured errors
- deterministic output ordering
- trace-friendly execution summaries

## Multi-Turn Tool Orchestration

The tool loop supports multiple rounds but is bounded by `max_tool_rounds`.
When the bound is reached, the implementation preserves append-only history by
adding skipped tool responses instead of mutating old messages.

## Experiment Structure

The repository contains three main experiment paths:

- `baseline.py`
- `cache_busters.py`
- `multi_turn_tools.py`

Together they measure how prompt structure, session stability, tool stability,
and orchestration depth affect cache behavior and cost.

## Limits

- small deterministic tool set by design
- not a production-ready agent runtime
- results are intended to support architectural comparison, not benchmark every
  possible agent workload
