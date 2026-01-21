"""
System prompts for the reflect agent.
"""

import json
from typing import Any


def _extract_directive_rules(directives: list[dict[str, Any]]) -> list[str]:
    """
    Extract directive rules as a list of strings.

    Args:
        directives: List of directive mental models with observations

    Returns:
        List of directive rule strings
    """
    rules = []
    for directive in directives:
        directive_name = directive.get("name", "")
        observations = directive.get("observations", [])
        if observations:
            for obs in observations:
                # Support both Pydantic Observation objects and dicts
                if hasattr(obs, "title"):
                    title = obs.title
                    content = obs.content
                else:
                    title = obs.get("title", "")
                    content = obs.get("content", "")
                if title and content:
                    rules.append(f"**{title}**: {content}")
                elif content:
                    rules.append(content)
        elif directive_name:
            # Fallback to description if no observations
            desc = directive.get("description", "")
            if desc:
                rules.append(f"**{directive_name}**: {desc}")
    return rules


def build_directives_section(directives: list[dict[str, Any]]) -> str:
    """
    Build the directives section for the system prompt.

    Directives are hard rules that MUST be followed in all responses.

    Args:
        directives: List of directive mental models with observations
    """
    if not directives:
        return ""

    rules = _extract_directive_rules(directives)
    if not rules:
        return ""

    parts = [
        "## DIRECTIVES (MANDATORY)",
        "These are hard rules you MUST follow in ALL responses:",
        "",
    ]

    for rule in rules:
        parts.append(f"- {rule}")

    parts.extend(
        [
            "",
            "NEVER violate these directives, even if other context suggests otherwise.",
            "IMPORTANT: Do NOT explain or justify how you handled directives in your answer. Just follow them silently.",
            "",
        ]
    )
    return "\n".join(parts)


def build_directives_reminder(directives: list[dict[str, Any]]) -> str:
    """
    Build a reminder section for directives to place at the end of the prompt.

    Args:
        directives: List of directive mental models with observations
    """
    if not directives:
        return ""

    rules = _extract_directive_rules(directives)
    if not rules:
        return ""

    parts = [
        "",
        "## REMINDER: MANDATORY DIRECTIVES",
        "Before responding, ensure your answer complies with ALL of these directives:",
        "",
    ]

    for i, rule in enumerate(rules, 1):
        parts.append(f"{i}. {rule}")

    parts.append("")
    parts.append("Your response will be REJECTED if it violates any directive above.")
    parts.append("Do NOT include any commentary about how you handled directives - just follow them.")
    return "\n".join(parts)


def build_system_prompt_for_tools(
    bank_profile: dict[str, Any],
    context: str | None = None,
    directives: list[dict[str, Any]] | None = None,
) -> str:
    """
    Build the system prompt for tool-calling reflect agent.

    This is a simplified prompt since tools are defined separately via the tools parameter.

    Args:
        bank_profile: Bank profile with name and mission
        context: Optional additional context
        directives: Optional list of directive mental models to inject as hard rules
    """
    name = bank_profile.get("name", "Assistant")
    mission = bank_profile.get("mission", "")

    no_info_rule = (
        "- Only say 'I don't have information' AFTER trying list_mental_models AND recall with no relevant results"
    )

    parts = []

    # Inject directives at the VERY START for maximum prominence
    if directives:
        parts.append(build_directives_section(directives))

    parts.extend(
        [
            "You are a reflection agent that answers questions by reasoning over retrieved memories.",
            "",
        ]
    )

    parts.extend(
        [
            "## CRITICAL RULES",
            "- You must NEVER fabricate information that has no basis in retrieved data",
            "- You SHOULD synthesize, infer, and reason from the retrieved memories",
            "- You MUST call recall() before saying you don't have information",
            no_info_rule,
            "",
            "## How to Reason",
            "- If memories mention someone did an activity, you can infer they likely enjoyed it",
            "- Synthesize a coherent narrative from related memories",
            "- Be a thoughtful interpreter, not just a literal repeater",
            "- When the exact answer isn't stated, use what IS stated to give the best answer",
            "",
            "## Query Strategy (IMPORTANT)",
            "recall() uses semantic search. NEVER just echo the user's question - decompose it into targeted searches:",
            "",
            "BAD: User asks 'recurring lesson themes between students' → recall('recurring lesson themes between students')",
            "GOOD: Break it down into component searches:",
            "  1. recall('lessons') - find all lesson-related memories",
            "  2. recall('teaching sessions') - alternative phrasing",
            "  3. recall('student progress') - find student-related memories",
            "  4. recall('topics taught') - find subject matter",
            "",
            "Think: What ENTITIES and CONCEPTS does this question involve? Search for each separately.",
            "- Questions about patterns → search for the individual instances first",
            "- Questions comparing things → search for each thing separately",
            "- Questions about relationships → search for each party involved",
            "",
            "## Workflow",
        ]
    )

    # Answer mode: include mental model lookup in workflow
    parts.extend(
        [
            "1. Review the pre-fetched mental models for relevant synthesized knowledge",
            "2. If relevant, call get_mental_model(model_id) for full observations",
            "3. DECOMPOSE the question into component searches (see Query Strategy above)",
            "   - Identify entities and concepts in the question",
            "   - Search for each separately with targeted queries",
            "4. Run multiple recall() calls - don't just echo the user's question",
            "5. Use expand() if you need more context on specific memories",
            "6. BEFORE answering: Check if any person/project/concept from the memories deserves a mental model - use learn() if so",
            "7. When ready, call done() with your answer and supporting memory_ids",
            "",
            "## When to Use learn() - IMPORTANT",
            "ACTIVELY look for opportunities to use learn() when you discover:",
            "- A person mentioned in 2+ memories who has no mental model yet",
            "- A project or concept the user asks about that has no mental model",
            "- A pattern or topic worth tracking for future questions",
            "",
            "DO NOT wait to be asked - proactively create models when you see the need.",
            "Example: learn(name='Project Alpha', description='Track goals, status, and key decisions for Project Alpha')",
            "",
            "## Output Format: Plain Text Answer",
            "Call done() with a plain text 'answer' field.",
            "- Do NOT use markdown formatting",
            "- NEVER include memory IDs, UUIDs, or 'Memory references' in the answer text",
            "- Put memory IDs ONLY in the memory_ids array parameter, not in the answer",
        ]
    )

    parts.append("")
    parts.append(f"## Memory Bank: {name}")

    if mission:
        parts.append(f"Mission: {mission}")

    # Disposition traits
    disposition = bank_profile.get("disposition", {})
    if disposition:
        traits = []
        if "skepticism" in disposition:
            traits.append(f"skepticism={disposition['skepticism']}")
        if "literalism" in disposition:
            traits.append(f"literalism={disposition['literalism']}")
        if "empathy" in disposition:
            traits.append(f"empathy={disposition['empathy']}")
        if traits:
            parts.append(f"Disposition: {', '.join(traits)}")

    if context:
        parts.append(f"\n## Additional Context\n{context}")

    # Add directive reminder at the END for recency effect
    if directives:
        parts.append(build_directives_reminder(directives))

    return "\n".join(parts)


def build_agent_prompt(
    query: str,
    context_history: list[dict],
    bank_profile: dict,
    additional_context: str | None = None,
) -> str:
    """Build the user prompt for the reflect agent."""
    parts = []

    # Bank identity
    name = bank_profile.get("name", "Assistant")
    mission = bank_profile.get("mission", "")

    parts.append(f"## Memory Bank Context\nName: {name}")
    if mission:
        parts.append(f"Mission: {mission}")

    # Disposition traits if present
    disposition = bank_profile.get("disposition", {})
    if disposition:
        traits = []
        if "skepticism" in disposition:
            traits.append(f"skepticism={disposition['skepticism']}")
        if "literalism" in disposition:
            traits.append(f"literalism={disposition['literalism']}")
        if "empathy" in disposition:
            traits.append(f"empathy={disposition['empathy']}")
        if traits:
            parts.append(f"Disposition: {', '.join(traits)}")

    # Additional context from caller
    if additional_context:
        parts.append(f"\n## Additional Context\n{additional_context}")

    # Tool call history
    if context_history:
        parts.append("\n## Tool Results (synthesize and reason from this data)")
        for i, entry in enumerate(context_history, 1):
            tool = entry["tool"]
            output = entry["output"]
            # Format as proper JSON for LLM readability
            try:
                output_str = json.dumps(output, indent=2, default=str)
            except (TypeError, ValueError):
                output_str = str(output)
            parts.append(f"\n### Call {i}: {tool}\n```json\n{output_str}\n```")

    # The question
    parts.append(f"\n## Question\n{query}")

    # Instructions
    if context_history:
        parts.append(
            "\n## Instructions\n"
            "Based on the tool results above, either call more tools or provide your final answer. "
            "Synthesize and reason from the data - make reasonable inferences when helpful. "
            "If you have related information, use it to give the best possible answer."
        )
    else:
        parts.append(
            "\n## Instructions\n"
            "Start by calling list_mental_models() to see available mental models - they contain pre-synthesized knowledge. "
            "If a relevant model exists, use get_mental_model(model_id) to get its observations. "
            "Then use recall(query) for specific details not covered by mental models."
        )

    return "\n".join(parts)


def build_final_prompt(
    query: str,
    context_history: list[dict],
    bank_profile: dict,
    additional_context: str | None = None,
) -> str:
    """Build the final prompt when forcing a text response (no tools)."""
    parts = []

    # Bank identity
    name = bank_profile.get("name", "Assistant")
    mission = bank_profile.get("mission", "")

    parts.append(f"## Memory Bank Context\nName: {name}")
    if mission:
        parts.append(f"Mission: {mission}")

    # Disposition traits if present
    disposition = bank_profile.get("disposition", {})
    if disposition:
        traits = []
        if "skepticism" in disposition:
            traits.append(f"skepticism={disposition['skepticism']}")
        if "literalism" in disposition:
            traits.append(f"literalism={disposition['literalism']}")
        if "empathy" in disposition:
            traits.append(f"empathy={disposition['empathy']}")
        if traits:
            parts.append(f"Disposition: {', '.join(traits)}")

    # Additional context from caller
    if additional_context:
        parts.append(f"\n## Additional Context\n{additional_context}")

    # Tool call history
    if context_history:
        parts.append("\n## Retrieved Data (synthesize and reason from this data)")
        for entry in context_history:
            tool = entry["tool"]
            output = entry["output"]
            # Format as proper JSON for LLM readability
            try:
                output_str = json.dumps(output, indent=2, default=str)
            except (TypeError, ValueError):
                output_str = str(output)
            parts.append(f"\n### From {tool}:\n```json\n{output_str}\n```")
    else:
        parts.append("\n## Retrieved Data\nNo data was retrieved.")

    # The question
    parts.append(f"\n## Question\n{query}")

    # Final instructions
    parts.append(
        "\n## Instructions\n"
        "Provide a thoughtful answer by synthesizing and reasoning from the retrieved data above. "
        "You can make reasonable inferences from the memories, but don't completely fabricate information."
        "If the exact answer isn't stated, use what IS stated to give the best possible answer. "
        "Only say 'I don't have information' if the retrieved data is truly unrelated to the question."
    )

    return "\n".join(parts)


FINAL_SYSTEM_PROMPT = """You are a thoughtful assistant that synthesizes answers from retrieved memories.

Your approach:
- Reason over the retrieved memories to answer the question
- Make reasonable inferences when the exact answer isn't explicitly stated
- Connect related memories to form a complete picture
- Be helpful - if you have related information, use it to give the best possible answer

Only say "I don't have information" if the retrieved data is truly unrelated to the question.
Do NOT fabricate information that has no basis in the retrieved data."""


# =============================================================================
# 4-Phase Mental Model Reflect Prompts
# =============================================================================

SEED_PHASE_SYSTEM_PROMPT = """You are analyzing memories to build a mental model.

## CRITICAL: Choose the Right Format Based on the Model's Purpose

First, read the "Topic Focus" (the model's description) and decide:

**Option A - Consolidated Reference Document** (use when the purpose is to capture structured knowledge):
- The model's purpose describes mapping, tracking, cataloging, or building a reference
- Examples: "Map customers to locations", "Track routes", "Record which person is where"
- Generate exactly 1 candidate containing THE ACTUAL DATA in a MARKDOWN TABLE
- **CRITICAL: Output the actual table with real data, NOT a description of what the table would contain**
- Include every entity/mapping you can extract from the memories - be exhaustive

**Option B - Behavioral Observations** (use for patterns, beliefs, preferences):
- The model's purpose is about understanding behaviors, patterns, or preferences
- Examples: "Learn about this person", "Track preferences", "Understand habits"
- Generate 5-15 separate observation candidates about different patterns

## Output Format
```json
{
  "candidates": [
    {
      "content": "The observation content (actual table with data for Option A, prose for Option B)",
      "seed_memory_ids": ["memory_id_1", "memory_id_2", ...]
    }
  ]
}
```

## Example: Option A - Reference Document (CORRECT)
If the topic is "Map each customer to their office location":
```json
{
  "candidates": [
    {
      "content": "## Customer Office Directory\n\n| Customer | Company | Room | Floor | Door |\n|----------|---------|------|-------|------|\n| Peter Collins | Recruitment Agency | 101 | 1 | door_west_101 |\n| Dr. Amanda Lee | Health First Clinic | 103 | 1 | door_west_103 |\n| James Chen | Tech Solutions Inc | 101 | 1 | door_west_101 |\n| Thomas Moore | Music Academy | 202 | 2 | door_east_202 |\n\n### Building Layout\n- Lobby → stairs_up → Floor 1 Hallway\n- Floor 1 Hallway has doors to rooms 101, 102, 103\n- Floor 1 Hallway → stairs_up → Floor 2 Hallway\n- Floor 2 Hallway has doors to rooms 201, 202",
      "seed_memory_ids": ["id1", "id2", "id3", "id4", "id5", "id6"]
    }
  ]
}
```

## Example: Option A - Reference Document (WRONG - do NOT do this)
```json
{
  "candidates": [
    {
      "content": "The table lists each customer with their company, room, floor, and door.",
      "seed_memory_ids": ["id1", "id2"]
    }
  ]
}
```
^ This is WRONG because it describes the table instead of containing the actual data.

## Example: Option B - Behavioral Observations
If the topic is "Learn about Dr. Amanda Lee's preferences":
```json
{
  "candidates": [
    {"content": "Dr. Amanda Lee prefers morning appointments", "seed_memory_ids": ["id1", "id2"]},
    {"content": "Dr. Amanda Lee is meticulous about medical records", "seed_memory_ids": ["id3", "id4"]}
  ]
}
```

## Rules
- DO NOT mix formats - either one big table OR multiple observations
- For Option A: Output THE ACTUAL DATA in table format, not a description of it
- For Option A: be EXHAUSTIVE, include EVERY data point from ALL memories
- For Option B: focus on patterns that appear multiple times
- Skip patterns already covered by existing observations
- Return empty candidates array if nothing new to add"""


def build_seed_phase_prompt(
    memories: list[dict],
    topic: str | None = None,
    existing_observations: list[dict] | None = None,
    subtype: str | None = None,
) -> str:
    """Build the user prompt for the seed phase.

    Args:
        memories: List of memories to analyze
        topic: Optional topic focus for the mental model
        existing_observations: Optional list of existing observations to avoid rediscovering
        subtype: Optional mental model subtype (not currently used, kept for API compatibility)
    """
    parts = []

    if topic:
        parts.append(f"## Topic Focus (READ THIS TO DECIDE FORMAT)\n{topic}\n")

    # Include existing observations for context
    if existing_observations:
        parts.append("## Existing Observations")
        parts.append("Review existing content - update/extend if reference document, avoid if behavioral:\n")
        for i, obs in enumerate(existing_observations, 1):
            title = obs.get("title", "")
            content = obs.get("content", "")
            parts.append(f"{i}. **{title}**: {content}\n")
        parts.append("")

    parts.append("## Memories to Analyze\n")
    for mem in memories:
        mem_id = mem.get("id", "unknown")
        content = mem.get("content", mem.get("text", ""))
        timestamp = mem.get("timestamp", mem.get("created_at", ""))
        parts.append(f"[{mem_id}] ({timestamp}): {content}\n")

    parts.append("\n## Instructions")
    parts.append("1. Read the Topic Focus above to understand the model's purpose")
    parts.append("2. Decide: Is this a reference document (Option A) or behavioral observations (Option B)?")
    parts.append("3. Generate candidates in the appropriate format")

    return "\n".join(parts)


VALIDATE_PHASE_SYSTEM_PROMPT = """You are validating candidate observations against evidence.

For each candidate, you have:
- Supporting memories (evidence FOR the observation)
- Contradicting memories (evidence AGAINST the observation)

## Your Task
1. Evaluate each candidate based on the evidence
2. For valid candidates, extract EXACT QUOTES from supporting memories
3. Discard candidates with insufficient or contradicting evidence
4. Merge similar candidates into single, refined observations

## Rules for Quotes
- Quotes must be EXACT text from the memory, not paraphrased
- Each quote should directly support the observation
- The MORE evidence quotes, the BETTER - don't limit yourself, include ALL relevant quotes (10, 20, 50+)
- Observations with only 1-2 quotes are weak and should be discarded unless the evidence is exceptionally strong
- Stronger observations have more supporting evidence - aim for comprehensive coverage

## Output Format
Return validated observations with evidence:
```json
{
  "observations": [
    {
      "title": "Short descriptive title (3-8 words) - like a headline",
      "content": "The full observation content - detailed explanation of the pattern/belief",
      "evidence": [
        {
          "memory_id": "exact_memory_id",
          "quote": "Exact quote from the memory text",
          "relevance": "Brief explanation of how this supports the observation",
          "timestamp": "2024-01-15T10:00:00Z"
        }
      ]
    }
  ],
  "discarded": [
    {
      "content": "The discarded candidate",
      "reason": "Why it was discarded (insufficient evidence, contradicted, etc.)"
    }
  ],
  "merged": [
    {
      "from": ["candidate 1 content", "candidate 2 content"],
      "into": "The merged observation content"
    }
  ]
}
```

## Title Guidelines
- Title should be a SHORT label (like "Prefers morning meetings" or "Coffee enthusiast")
- NOT a truncated version of the content
- Think of it as a category/tag for the observation

Be rigorous: only keep observations with clear, verifiable evidence from multiple memories."""


def build_validate_phase_prompt(candidates_with_evidence: list[dict]) -> str:
    """Build the user prompt for the validate phase."""
    parts = ["## Candidates to Validate\n"]

    for i, item in enumerate(candidates_with_evidence, 1):
        candidate = item.get("candidate", {})
        supporting = item.get("supporting_memories", [])
        contradicting = item.get("contradicting_memories", [])

        parts.append(f"### Candidate {i}: {candidate.get('content', '')}")

        if supporting:
            parts.append("\n**Supporting Evidence:**")
            for mem in supporting:
                mem_id = mem.get("id", "unknown")
                content = mem.get("content", mem.get("text", ""))
                timestamp = mem.get("timestamp", mem.get("created_at", ""))
                parts.append(f"- [{mem_id}] ({timestamp}): {content}")

        if contradicting:
            parts.append("\n**Contradicting Evidence:**")
            for mem in contradicting:
                mem_id = mem.get("id", "unknown")
                content = mem.get("content", mem.get("text", ""))
                timestamp = mem.get("timestamp", mem.get("created_at", ""))
                parts.append(f"- [{mem_id}] ({timestamp}): {content}")

        if not supporting and not contradicting:
            parts.append("\n*No additional evidence found*")

        parts.append("")

    parts.append("## Instructions")
    parts.append("1. Evaluate each candidate based on its evidence")
    parts.append("2. Keep candidates with strong supporting evidence")
    parts.append("3. Discard candidates with no evidence or strong contradictions")
    parts.append("4. Merge similar candidates")
    parts.append("5. Extract EXACT quotes (copy-paste from memory text) for evidence")

    return "\n".join(parts)


COMPARE_PHASE_SYSTEM_PROMPT = """You are merging new observations with an existing mental model.

You have:
- EXISTING observations (from the current mental model)
- NEW observations (from this reflect cycle)

## Your Task
Produce the final, complete mental model by:
1. Keeping existing observations that are still valid
2. Updating existing observations with new evidence (ADD new evidence to existing)
3. Adding new observations that don't overlap with existing
4. Removing existing observations that are contradicted by new evidence
5. Merging overlapping observations

## Rules
- The final model should have no contradictions
- Each observation must have evidence with exact quotes
- COMBINE evidence from both existing and new observations
- If an existing observation has new supporting evidence, ADD ALL the new evidence to it
- Include ALL relevant evidence - the more quotes the better (10, 20, 50+ is great)
- Observations with more evidence are more reliable - don't limit the number of quotes

## Output Format
Return the complete, final mental model:
```json
{
  "observations": [
    {
      "title": "Short descriptive title (3-8 words)",
      "content": "Full observation content - detailed explanation",
      "evidence": [
        {
          "memory_id": "id",
          "quote": "exact quote",
          "relevance": "explanation",
          "timestamp": "ISO timestamp"
        }
      ],
      "created_at": "ISO timestamp of when observation was first created"
    }
  ],
  "changes": {
    "kept": ["Observation that was kept unchanged"],
    "updated": [{"from": "old content", "to": "new content", "reason": "why"}],
    "added": ["New observation that was added"],
    "removed": [{"content": "removed observation", "reason": "why removed"}],
    "merged": [{"from": ["obs1", "obs2"], "into": "merged observation"}]
  }
}
```"""


def build_compare_phase_prompt(
    existing_observations: list[dict],
    new_observations: list[dict],
) -> str:
    """Build the user prompt for the compare phase."""
    parts = []

    parts.append("## Existing Mental Model Observations")
    if existing_observations:
        for i, obs in enumerate(existing_observations, 1):
            title = obs.get("title", "")
            content = obs.get("content", obs.get("text", ""))
            evidence = obs.get("evidence", [])
            parts.append(f"\n### Existing {i}: {title}")
            parts.append(f"Content: {content}")
            if evidence:
                parts.append(f"Evidence ({len(evidence)} items):")
                for ev in evidence[:5]:  # Show max 5 evidence items
                    parts.append(f'  - [{ev.get("memory_id", "?")}]: "{ev.get("quote", "")}"')
                if len(evidence) > 5:
                    parts.append(f"  ... and {len(evidence) - 5} more")
    else:
        parts.append("*No existing observations*")

    parts.append("\n## New Observations from This Reflect")
    if new_observations:
        for i, obs in enumerate(new_observations, 1):
            title = obs.get("title", "")
            content = obs.get("content", "")
            evidence = obs.get("evidence", [])
            parts.append(f"\n### New {i}: {title}")
            parts.append(f"Content: {content}")
            if evidence:
                parts.append(f"Evidence ({len(evidence)} items):")
                for ev in evidence:
                    parts.append(f'  - [{ev.get("memory_id", "?")}]: "{ev.get("quote", "")}"')
    else:
        parts.append("*No new observations*")

    parts.append("\n## Instructions")
    parts.append("Merge these into a coherent, non-contradictory mental model.")
    parts.append("Preserve all valid evidence. Remove stale or contradicted observations.")

    return "\n".join(parts)


# =============================================================================
# UPDATE EXISTING Phase Prompts (for diff-based refresh)
# =============================================================================

UPDATE_EXISTING_SYSTEM_PROMPT = """You are updating existing observations with newly found evidence.

For each existing observation, you have been given:
- The original observation (title, content, existing evidence)
- Newly found supporting memories
- Newly found contradicting memories

## Your Task
1. Extract EXACT QUOTES from new supporting memories to add to the observation
2. Flag observations with strong contradicting evidence for potential removal
3. Keep existing evidence intact - only ADD new evidence

## Rules for Quotes
- Quotes must be EXACT text from the memory, not paraphrased
- Each quote should directly support the observation
- Include ALL relevant quotes from the new memories

## Output Format
Return updated observations with new evidence:
```json
{
  "updated_observations": [
    {
      "title": "Original title",
      "content": "Original content",
      "existing_evidence_count": 5,
      "new_evidence": [
        {
          "memory_id": "exact_memory_id",
          "quote": "Exact quote from the memory text",
          "relevance": "Brief explanation of how this supports the observation",
          "timestamp": "2024-01-15T10:00:00Z"
        }
      ],
      "has_contradiction": false,
      "contradiction_note": null
    }
  ]
}
```

If an observation has strong contradicting evidence, set has_contradiction=true and explain in contradiction_note."""


def build_update_existing_prompt(observations_with_evidence: list[dict]) -> str:
    """Build the user prompt for the update existing phase.

    Args:
        observations_with_evidence: List of existing observations with new evidence found
    """
    parts = ["## Existing Observations to Update\n"]

    for i, item in enumerate(observations_with_evidence, 1):
        obs = item.get("observation", {})
        supporting = item.get("supporting_memories", [])
        contradicting = item.get("contradicting_memories", [])

        title = obs.get("title", "")
        content = obs.get("content", "")
        existing_evidence = obs.get("evidence", [])

        parts.append(f"### Observation {i}: {title}")
        parts.append(f"Content: {content}")
        parts.append(f"Existing evidence count: {len(existing_evidence)}")

        if supporting:
            parts.append("\n**New Supporting Memories:**")
            for mem in supporting:
                mem_id = mem.get("id", "unknown")
                mem_content = mem.get("content", mem.get("text", ""))
                timestamp = mem.get("timestamp", mem.get("created_at", ""))
                parts.append(f"- [{mem_id}] ({timestamp}): {mem_content}")

        if contradicting:
            parts.append("\n**New Contradicting Memories:**")
            for mem in contradicting:
                mem_id = mem.get("id", "unknown")
                mem_content = mem.get("content", mem.get("text", ""))
                timestamp = mem.get("timestamp", mem.get("created_at", ""))
                parts.append(f"- [{mem_id}] ({timestamp}): {mem_content}")

        if not supporting and not contradicting:
            parts.append("\n*No new evidence found*")

        parts.append("")

    parts.append("## Instructions")
    parts.append("1. Extract EXACT quotes from new supporting memories")
    parts.append("2. Flag observations with strong contradictions")
    parts.append("3. Return the updated observations with new evidence added")

    return "\n".join(parts)


# =============================================================================
# Structural Model Extraction Prompts (Two-Phase)
# =============================================================================

STRUCTURAL_EXTRACT_SYSTEM_PROMPT = """You are extracting structured data from memories to build a reference document.

## Your Task
1. Read the model's PURPOSE to understand what kind of data to extract
2. For each memory, extract the key information as a descriptive text line
3. Provide a synthesis_prompt describing how to format the final table

## Rules
- Extract ONLY data explicitly stated in memories - don't infer
- Include memory_id and exact quote for each extraction
- extracted_text should be a concise description of the relevant data (e.g., "Peter Collins works at room 101")
- Skip memories that don't contain relevant structured data

## Output Format
```json
{
  "extractions": [
    {
      "memory_id": "the-memory-id",
      "extracted_text": "Customer: Peter Collins, Room: 101, Floor: 1, Door: door_west_101",
      "quote": "Exact text supporting this extraction"
    }
  ],
  "synthesis_prompt": "Create a table with columns: Customer, Room, Floor, Door. Group by floor."
}
```

The synthesis_prompt tells the next phase how to format the data into a useful table."""


def build_structural_extract_prompt(
    memories: list[dict],
    topic: str,
) -> str:
    """Build the user prompt for the structural extraction phase.

    Args:
        memories: List of memories to extract from
        topic: The mental model's purpose/description
    """
    parts = []

    parts.append(f"## Model Purpose\n{topic}")
    parts.append("")

    parts.append("## Memories to Process")
    for mem in memories:
        mem_id = mem.get("id", "unknown")
        content = mem.get("content", mem.get("text", ""))
        parts.append(f"\n[{mem_id}]: {content}")

    parts.append("\n## Instructions")
    parts.append("1. Based on the purpose, decide what data fields are relevant")
    parts.append("2. Extract those fields from each memory")
    parts.append("3. Provide a synthesis_prompt describing the ideal table structure")

    return "\n".join(parts)


STRUCTURAL_SYNTHESIZE_SYSTEM_PROMPT = """You are synthesizing extracted data into a consolidated reference document.

## Your Task
Take the extracted data points and create ONE comprehensive observation containing:
1. A markdown table with all unique entries
2. Any additional notes about patterns or structure

## Rules
- Deduplicate entries (same entity should appear once with most complete data)
- Resolve conflicts by using the most recent or most detailed information
- Include ALL extracted entities in the table
- Group related information logically
- Add a "Navigation/Structure Notes" section if relevant patterns exist

## Output Format
```json
{
  "title": "Short descriptive title (3-8 words)",
  "content": "## Table Title\n\n| Col1 | Col2 | ... |\n|------|------|-----|\n| val1 | val2 | ... |\n\n### Additional Notes\n- Note 1\n- Note 2",
  "evidence": [
    {
      "memory_id": "id",
      "quote": "exact quote from extraction",
      "relevance": "brief explanation"
    }
  ]
}
```

Be exhaustive - include every unique data point from the extractions."""


def build_structural_synthesize_prompt(
    extractions: list[dict],
    topic: str,
    synthesis_guidance: str,
    existing_content: str | None = None,
) -> str:
    """Build the user prompt for the structural synthesis phase.

    Args:
        extractions: List of extracted data points from phase 1
        topic: The mental model's purpose/description
        synthesis_guidance: Guidance from extraction phase on how to format the table
        existing_content: Optional existing observation content to update
    """
    parts = []

    parts.append(f"## Model Purpose\n{topic}")
    parts.append("")

    if synthesis_guidance:
        parts.append(f"## Formatting Guidance\n{synthesis_guidance}")
        parts.append("")

    if existing_content:
        parts.append("## Existing Content (update with new data)")
        parts.append(existing_content)
        parts.append("")

    parts.append("## Extracted Data Points")
    parts.append("```json")
    parts.append(json.dumps(extractions, indent=2, default=str))
    parts.append("```")

    parts.append("\n## Instructions")
    parts.append("1. Deduplicate entries (merge data for same entity)")
    parts.append("2. Create a comprehensive markdown table based on the data")
    parts.append("3. Add notes section for patterns/structure if relevant")
    if existing_content:
        parts.append("4. Merge with existing content - update changed entries, add new ones")

    return "\n".join(parts)
