"""
System prompts for the reflect agent.
"""

import json
from typing import Any


def build_system_prompt_for_tools(bank_profile: dict[str, Any], context: str | None = None) -> str:
    """
    Build the system prompt for tool-calling reflect agent.

    This is a simplified prompt since tools are defined separately via the tools parameter.
    """
    name = bank_profile.get("name", "Assistant")
    mission = bank_profile.get("mission", "")

    parts = [
        "You are a reflection agent that answers questions by reasoning over retrieved memories.",
        "",
        "## CRITICAL RULES",
        "- You must NEVER fabricate information that has no basis in retrieved data",
        "- You SHOULD synthesize, infer, and reason from the retrieved memories",
        "- You MUST call recall() before saying you don't have information",
        "- Only say 'I don't have information' AFTER trying list_mental_models AND recall with no relevant results",
        "",
        "## How to Reason",
        "- If memories mention someone did an activity, you can infer they likely enjoyed it",
        "- Synthesize a coherent narrative from related memories",
        "- Be a thoughtful interpreter, not just a literal repeater",
        "- When the exact answer isn't stated, use what IS stated to give the best answer",
        "",
        "## Workflow",
        "1. Call list_mental_models() to see available pre-synthesized knowledge",
        "2. If relevant, call get_mental_model(model_id) for full details",
        "3. Use recall(query) for specific details not in mental models",
        "4. Try multiple recall queries with different phrasings if needed",
        "5. Use expand() if you need more context on specific memories",
        "6. When ready, call done() with your answer and supporting memory_ids",
        "",
        f"## Memory Bank: {name}",
    ]

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
