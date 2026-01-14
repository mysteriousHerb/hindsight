"""
Tool schema definitions for the reflect agent.

These are OpenAI-format tool definitions used with native tool calling.
"""

from typing import Literal

# Tool definitions in OpenAI format
TOOL_LIST_MENTAL_MODELS = {
    "type": "function",
    "function": {
        "name": "list_mental_models",
        "description": "List all available mental models - your synthesized knowledge about entities, concepts, and events. Returns an array of models with id, name, and description.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

TOOL_GET_MENTAL_MODEL = {
    "type": "function",
    "function": {
        "name": "get_mental_model",
        "description": "Get full details of a specific mental model including all observations and memory references.",
        "parameters": {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "ID of the mental model (from list_mental_models results)",
                },
            },
            "required": ["model_id"],
        },
    },
}

TOOL_RECALL = {
    "type": "function",
    "function": {
        "name": "recall",
        "description": "Search memories using semantic + temporal retrieval. Returns relevant memories from experience and world knowledge, each with an 'id' you can reference.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Optional limit on result size (default 2048). Use higher values for broader searches.",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_LEARN = {
    "type": "function",
    "function": {
        "name": "learn",
        "description": "Create a placeholder for a new mental model. The actual content will be generated automatically during refresh.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Human-readable name for the mental model",
                },
                "description": {
                    "type": "string",
                    "description": "What this model should track - used as the prompt for content generation",
                },
            },
            "required": ["name", "description"],
        },
    },
}

TOOL_EXPAND = {
    "type": "function",
    "function": {
        "name": "expand",
        "description": "Get more context for one or more memories. Memory hierarchy: memory -> chunk -> document.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of memory IDs from recall results (batch multiple for efficiency)",
                },
                "depth": {
                    "type": "string",
                    "enum": ["chunk", "document"],
                    "description": "chunk: surrounding text chunk, document: full source document",
                },
            },
            "required": ["memory_ids", "depth"],
        },
    },
}

TOOL_DONE_ANSWER = {
    "type": "function",
    "function": {
        "name": "done",
        "description": "Signal completion with your final answer. Use this when you have gathered enough information to answer the question.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Your response as plain text. Do NOT use markdown formatting. Write naturally as if speaking.",
                },
                "memory_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of memory IDs from recall results that support your answer",
                },
                "model_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of mental model IDs that support your answer",
                },
            },
            "required": ["answer"],
        },
    },
}

TOOL_DONE_OBSERVATIONS = {
    "type": "function",
    "function": {
        "name": "done",
        "description": "Signal completion with structured observations about the topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "observations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Observation header (can be empty for intro/overview)",
                            },
                            "text": {
                                "type": "string",
                                "description": "Observation content. Can use lists, tables, bold, italic.",
                            },
                            "memory_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Memory IDs supporting this observation",
                            },
                        },
                        "required": ["title", "text"],
                    },
                    "description": "Array of observations, each covering a different aspect of the topic",
                },
            },
            "required": ["observations"],
        },
    },
}


def get_reflect_tools(
    enable_learn: bool = True, output_mode: Literal["answer", "observations"] = "answer"
) -> list[dict]:
    """
    Get the list of tools for the reflect agent.

    Args:
        enable_learn: Whether to include the learn tool
        output_mode: "answer" or "observations" - determines done tool format

    Returns:
        List of tool definitions in OpenAI format
    """
    tools = [
        TOOL_LIST_MENTAL_MODELS,
        TOOL_GET_MENTAL_MODEL,
        TOOL_RECALL,
    ]

    if enable_learn:
        tools.append(TOOL_LEARN)

    tools.append(TOOL_EXPAND)

    # Add appropriate done tool based on output mode
    if output_mode == "observations":
        tools.append(TOOL_DONE_OBSERVATIONS)
    else:
        tools.append(TOOL_DONE_ANSWER)

    return tools
