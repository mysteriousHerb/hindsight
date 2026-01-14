# Mental Models v4 - Implementation Changes

This document summarizes the changes introduced in the `obsv2` branch, which implements the Mental Models v4 system.

## Overview

Mental Models v4 is a major refactor that introduces **synthesized knowledge** as a first-class concept. Instead of storing observations as memory_units, the system now maintains mental models - consolidated understanding about entities, concepts, and events.

## Key Concepts

### Mental Models

Mental models are synthesized summaries representing understanding about entities, concepts, or events. Each mental model has:

| Field | Description |
|-------|-------------|
| `id` | Stable identifier derived from name (e.g., `pinned-product-roadmap`) |
| `name` | Human-readable name (e.g., "Alice Chen") |
| `subtype` | How it was created: `structural`, `emergent`, `learned`, or `pinned` |
| `description` | One-liner for quick scanning/retrieval |
| `observations` | Structured content with per-observation memory attribution |
| `entity_id` | Optional link to entities table |
| `tags` | For scoped visibility filtering |

### Observations Structure

Mental model content is organized into **observations**, each with supporting memory references:

```json
{
  "observations": [
    {
      "title": "",
      "text": "Alice Chen is a senior ML engineer who joined from Google in 2023.",
      "based_on": ["uuid-1", "uuid-2"]
    },
    {
      "title": "Key Achievements",
      "text": "Led the personalization project that improved engagement by 23%.",
      "based_on": ["uuid-3"]
    }
  ]
}
```

### Mental Model Subtypes

1. **Structural** - Derived from the bank's mission. Represents what any agent with this role would need to track.
   ```
   Mission: "Be a PM for engineering team"
   → Structural models: Team Members, Sprint Goals, Key Decisions
   ```

2. **Emergent** - Discovered from data patterns (named entities mentioned frequently). Filtered by LLM to only include specific named entities (people, organizations, named projects).

3. **Learned** - Created during reflection when the agent discovers insights worth remembering. The agent calls `learn()` to create a placeholder, content is generated during refresh.

4. **Pinned** - User-defined mental models created via API. Persist across refreshes.

### Bank Mission

Banks have a `mission` field (on the bank profile) that drives structural model derivation. The mission describes who the agent is and what they're trying to accomplish.

### Reflect Agent

The reflect operation is now an **agentic loop** that iteratively gathers information using tools:

| Tool | Purpose |
|------|---------|
| `list_mental_models()` | List all mental models (names + descriptions) |
| `get_mental_model(model_id)` | Get full details of a specific mental model |
| `recall(query, max_tokens?)` | Search memories using semantic + temporal retrieval |
| `expand(memory_ids, depth)` | Get surrounding context (chunk or document) |
| `learn(name, description)` | Create a mental model placeholder |
| `done(answer, memory_ids?, model_ids?)` | Signal completion with citations |

The agent iterates up to 10 times, deciding what information to retrieve at each step.

## Breaking Changes

### 1. Observations Removed from memory_units

**Before:** Observations were stored as `fact_type='observation'` in the `memory_units` table.

**After:** Observations no longer exist as memory_units. All `memory_units` with `fact_type='observation'` are deleted during migration. Observations are now part of mental models.

```sql
DELETE FROM memory_units WHERE fact_type = 'observation';
```

**Impact:** Any code that relied on querying observations from memory_units will break. Use mental models instead.

### 2. Opinion Facts Removed from Think

**Before:** The think operation extracted opinions and stored them as `fact_type='opinion'` memory_units.

**After:** Opinion extraction is removed. Opinions are now handled through mental models during reflection.

**Code removed:**
- `hindsight_api/engine/retain/observation_regeneration.py` (deleted)
- `hindsight_api/engine/search/observation_utils.py` (deleted)
- Opinion extraction from `think_utils.py`

### 3. Entity Regenerate Endpoint Deprecated

**Before:** `POST /v1/default/banks/{bank_id}/entities/{entity_id}/regenerate` regenerated observations for an entity.

**After:** Returns 410 Gone. Use mental models refresh instead: `POST /v1/default/banks/{bank_id}/mental-models/refresh`

### 4. Reflect Returns Structured Answer with Traces

**Before:** Reflect returned plain text response.

**After:** Reflect supports structured output with memory/model citations and optional debug traces:
```json
{
  "text": "Based on Alice's expertise...",
  "tool_calls": [...],
  "llm_calls": [...],
  "mental_models": [...],
  "based_on": [{"id": "uuid", "text": "...", "type": "world"}]
}
```

## New API Endpoints

### Mental Models

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/default/banks/{bank_id}/mental-models` | List mental models (filter by subtype, tags) |
| `POST` | `/v1/default/banks/{bank_id}/mental-models` | Create a pinned mental model |
| `GET` | `/v1/default/banks/{bank_id}/mental-models/{model_id}` | Get specific mental model |
| `POST` | `/v1/default/banks/{bank_id}/mental-models/refresh` | Refresh mental models (async) |
| `POST` | `/v1/default/banks/{bank_id}/mental-models/{model_id}/generate` | Generate content for a specific model (async) |
| `DELETE` | `/v1/default/banks/{bank_id}/mental-models/{model_id}` | Delete a mental model |
| `POST` | `/v1/default/banks/{bank_id}/research` | Query mental models with agentic search |

### Bank Profile Extended

The bank profile now includes the `mission` field (replaces deprecated `background`):
```json
{
  "bank_id": "my-bank",
  "name": "Alice",
  "disposition": {...},
  "mission": "I am a software engineer helping my team stay organized and ship quality code"
}
```

## Database Schema Changes

### New Table: mental_models

```sql
CREATE TABLE mental_models (
    id VARCHAR(64) NOT NULL,
    bank_id VARCHAR(64) NOT NULL,
    subtype VARCHAR(32) NOT NULL,     -- structural, emergent, learned, pinned
    name VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    observations JSONB,               -- [{title, text, based_on}]
    entity_id UUID,
    links VARCHAR[],
    tags VARCHAR[] DEFAULT '{}',
    last_updated TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id, bank_id)
);
```

### Indexes Added

```sql
CREATE INDEX idx_mental_models_bank_id ON mental_models(bank_id);
CREATE INDEX idx_mental_models_subtype ON mental_models(bank_id, subtype);
CREATE INDEX idx_mental_models_entity_id ON mental_models(entity_id);
CREATE INDEX idx_mental_models_tags ON mental_models USING GIN(tags);
```

## Migration Path

1. **Run migrations** - The migrations will:
   - Delete all observation memory_units
   - Create mental_models table

2. **Set bank mission** - Update the bank profile with a mission:
   ```bash
   curl -X PUT "http://localhost:8000/v1/default/banks/my-bank/profile" \
     -H "Content-Type: application/json" \
     -d '{"mission": "Be a PM for the engineering team"}'
   ```

3. **Refresh mental models** - Trigger initial refresh to populate mental models:
   ```bash
   curl -X POST "http://localhost:8000/v1/default/banks/my-bank/mental-models/refresh"
   ```

## New Module Structure

```
hindsight_api/engine/
├── mental_models/           # NEW: Mental models module
│   ├── __init__.py
│   ├── models.py            # Pydantic models
│   ├── emergent.py          # Emergent model detection & filtering
│   ├── structural.py        # Structural model derivation from mission
│   └── research.py          # Research endpoint agentic loop
├── reflect/                 # NEW: Reflect agent module
│   ├── __init__.py
│   ├── agent.py             # Main agentic loop
│   ├── models.py            # Action/Result models
│   ├── prompts.py           # System prompts
│   └── tools.py             # Tool implementations
└── retain/
    └── observation_regeneration.py  # DELETED
```

## Testing

New test files:
- `tests/test_mental_models.py` - Mental models CRUD and refresh
- `tests/test_emergent_filtering.py` - Emergent candidate filtering
- `tests/test_reflect_agent.py` - Reflect agent loop with tools

## Summary of Changes by Commit

| Commit | Description |
|--------|-------------|
| `e19c6b9` | Initial mental models implementation |
| `517eee4` | Refactor entity observations |
| `f72c9f0` | Fix database patch |
| `25fb4b9` | Agentic reflect implementation |
| `987b47e` | Agentic improvements |
| `2871ddc` | Reflect agent finalization |

## File Changes Summary

- **Added:** 16 new files (~3,500 lines)
- **Deleted:** 2 files (~380 lines)
- **Modified:** 10+ files with significant changes to memory_engine.py, http.py, think_utils.py
- **Net:** ~8,400 lines added, ~1,600 lines removed
