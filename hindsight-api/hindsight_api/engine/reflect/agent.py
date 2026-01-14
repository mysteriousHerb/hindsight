"""
Reflect agent - agentic loop for reflection with native tool calling.
"""

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal

from .models import LLMCall, MentalModelInput, Observation, ReflectAgentResult, ToolCall
from .prompts import FINAL_SYSTEM_PROMPT, build_final_prompt, build_system_prompt_for_tools
from .tools_schema import get_reflect_tools

if TYPE_CHECKING:
    from ..llm_wrapper import LLMProvider
    from ..response_models import LLMToolCall

logger = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 10


async def run_reflect_agent(
    llm_config: "LLMProvider",
    bank_id: str,
    query: str,
    bank_profile: dict[str, Any],
    lookup_fn: Callable[[str | None], Awaitable[dict[str, Any]]],
    recall_fn: Callable[[str, int], Awaitable[dict[str, Any]]],
    expand_fn: Callable[[list[str], str], Awaitable[dict[str, Any]]],
    learn_fn: Callable[[MentalModelInput], Awaitable[dict[str, Any]]] | None = None,
    context: str | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    max_tokens: int | None = None,
    response_schema: dict | None = None,
    output_mode: Literal["answer", "observations"] = "answer",
) -> ReflectAgentResult:
    """
    Execute the reflect agent loop using native tool calling.

    The agent iteratively calls tools to gather information and learn,
    then provides a final answer via the done() tool.

    Args:
        llm_config: LLM provider for agent calls
        bank_id: Bank identifier
        query: Question to answer
        bank_profile: Bank profile with name and mission
        lookup_fn: Tool callback for lookup (model_id) -> result
        recall_fn: Tool callback for recall (query, max_tokens) -> result
        expand_fn: Tool callback for expand (memory_id, depth) -> result
        learn_fn: Optional tool callback for learn (MentalModelInput) -> result.
                  If None, learn tool is disabled.
        context: Optional additional context
        max_iterations: Maximum number of iterations before forcing response
        max_tokens: Maximum tokens for the final response
        response_schema: Optional JSON Schema for structured output in final response
        output_mode: "answer" returns final text, "observations" returns structured observations

    Returns:
        ReflectAgentResult with final answer and metadata
    """
    enable_learn = learn_fn is not None
    reflect_id = f"{bank_id[:8]}-{int(time.time() * 1000) % 100000}"
    start_time = time.time()

    # Get tools for this agent
    tools = get_reflect_tools(enable_learn=enable_learn, output_mode=output_mode)

    # Build initial messages
    system_prompt = build_system_prompt_for_tools(bank_profile, context)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    # Tracking
    mental_models_created: list[str] = []
    total_tools_called = 0
    tool_trace: list[ToolCall] = []
    tool_trace_summary: list[dict[str, Any]] = []
    llm_trace: list[dict[str, Any]] = []
    context_history: list[dict[str, Any]] = []  # For final prompt fallback

    # Track available IDs for validation (prevents hallucinated citations)
    available_memory_ids: set[str] = set()
    available_model_ids: set[str] = set()

    def _get_llm_trace() -> list[LLMCall]:
        return [LLMCall(scope=c["scope"], duration_ms=c["duration_ms"]) for c in llm_trace]

    def _log_completion(answer: str, iterations: int, forced: bool = False):
        elapsed_ms = int((time.time() - start_time) * 1000)
        tools_summary = (
            ", ".join(
                f"{t['tool']}({t['input_summary']})={t['duration_ms']}ms/{t.get('output_chars', 0)}c"
                for t in tool_trace_summary
            )
            or "none"
        )
        llm_summary = ", ".join(f"{c['scope']}={c['duration_ms']}ms" for c in llm_trace) or "none"
        total_llm_ms = sum(c["duration_ms"] for c in llm_trace)
        total_tools_ms = sum(t["duration_ms"] for t in tool_trace_summary)

        answer_preview = answer[:100] + "..." if len(answer) > 100 else answer
        mode = "forced" if forced else "done"
        logger.info(
            f"[REFLECT {reflect_id}] {mode} | "
            f"query='{query[:50]}...' | "
            f"iterations={iterations} | "
            f"llm=[{llm_summary}] ({total_llm_ms}ms) | "
            f"tools=[{tools_summary}] ({total_tools_ms}ms) | "
            f"answer='{answer_preview}' | "
            f"total={elapsed_ms}ms"
        )

    for iteration in range(max_iterations):
        is_last = iteration == max_iterations - 1
        logger.debug(f"[REFLECT {reflect_id}] Iteration {iteration + 1}/{max_iterations}")

        if is_last:
            # Force text response on last iteration - no tools
            prompt = build_final_prompt(query, context_history, bank_profile, context)
            llm_start = time.time()
            response = await llm_config.call(
                messages=[
                    {"role": "system", "content": FINAL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                scope="reflect_agent_final",
                max_completion_tokens=max_tokens,
            )
            llm_trace.append({"scope": "final", "duration_ms": int((time.time() - llm_start) * 1000)})
            answer = response.strip()
            _log_completion(answer, iteration + 1, forced=True)
            return ReflectAgentResult(
                text=answer,
                iterations=iteration + 1,
                tools_called=total_tools_called,
                mental_models_created=mental_models_created,
                tool_trace=tool_trace,
                llm_trace=_get_llm_trace(),
            )

        # Call LLM with tools
        logger.info(f"[REFLECT {reflect_id}] Iteration {iteration + 1} - calling LLM with {len(tools)} tools")
        llm_start = time.time()

        try:
            result = await llm_config.call_with_tools(
                messages=messages,
                tools=tools,
                scope="reflect_agent",
                tool_choice="required" if iteration == 0 else "auto",  # Force tool use on first iteration
            )
            llm_duration = int((time.time() - llm_start) * 1000)
            tool_names = [tc.name for tc in result.tool_calls] if result.tool_calls else []
            logger.info(
                f"[REFLECT {reflect_id}] LLM call completed in {llm_duration}ms, "
                f"tool_calls={tool_names}, finish={result.finish_reason}"
            )
            llm_trace.append({"scope": f"agent_{iteration + 1}", "duration_ms": llm_duration})

        except Exception as e:
            llm_trace.append(
                {"scope": f"agent_{iteration + 1}_err", "duration_ms": int((time.time() - llm_start) * 1000)}
            )
            # Guardrail: If no evidence gathered yet, retry
            has_gathered_evidence = bool(available_memory_ids) or bool(available_model_ids)
            if not has_gathered_evidence and iteration < max_iterations - 1:
                logger.warning(f"[REFLECT {reflect_id}] LLM call failed: {e}, but no evidence gathered yet. Retrying.")
                continue

            logger.warning(f"[REFLECT {reflect_id}] LLM call failed: {e}, forcing final response")
            prompt = build_final_prompt(query, context_history, bank_profile, context)
            llm_start = time.time()
            response = await llm_config.call(
                messages=[
                    {"role": "system", "content": FINAL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                scope="reflect_agent_final",
                max_completion_tokens=max_tokens,
            )
            llm_trace.append({"scope": "final", "duration_ms": int((time.time() - llm_start) * 1000)})
            answer = response.strip()
            _log_completion(answer, iteration + 1, forced=True)
            return ReflectAgentResult(
                text=answer,
                iterations=iteration + 1,
                tools_called=total_tools_called,
                mental_models_created=mental_models_created,
                tool_trace=tool_trace,
                llm_trace=_get_llm_trace(),
            )

        # No tool calls - LLM wants to respond with text
        if not result.tool_calls:
            if result.content:
                answer = result.content.strip()
                _log_completion(answer, iteration + 1)
                return ReflectAgentResult(
                    text=answer,
                    iterations=iteration + 1,
                    tools_called=total_tools_called,
                    mental_models_created=mental_models_created,
                    tool_trace=tool_trace,
                    llm_trace=_get_llm_trace(),
                )
            # Empty response, force final
            prompt = build_final_prompt(query, context_history, bank_profile, context)
            llm_start = time.time()
            response = await llm_config.call(
                messages=[
                    {"role": "system", "content": FINAL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                scope="reflect_agent_final",
                max_completion_tokens=max_tokens,
            )
            llm_trace.append({"scope": "final", "duration_ms": int((time.time() - llm_start) * 1000)})
            answer = response.strip()
            _log_completion(answer, iteration + 1, forced=True)
            return ReflectAgentResult(
                text=answer,
                iterations=iteration + 1,
                tools_called=total_tools_called,
                mental_models_created=mental_models_created,
                tool_trace=tool_trace,
                llm_trace=_get_llm_trace(),
            )

        # Check for done tool call
        done_call = next((tc for tc in result.tool_calls if tc.name == "done"), None)
        if done_call:
            # Guardrail: Require evidence before done
            has_gathered_evidence = bool(available_memory_ids) or bool(available_model_ids)
            if not has_gathered_evidence and iteration < max_iterations - 1:
                logger.debug(
                    f"[REFLECT {reflect_id}] Rejecting early done - no evidence gathered. "
                    f"Forcing agent to gather evidence first."
                )
                # Add assistant message and fake tool result asking for evidence
                messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [_tool_call_to_dict(done_call)],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": done_call.id,
                        "content": json.dumps(
                            {
                                "error": "You must call recall() or list_mental_models() to gather evidence before providing your final answer."
                            }
                        ),
                    }
                )
                continue

            # Process done tool
            return _process_done_tool(
                done_call,
                output_mode,
                available_memory_ids,
                available_model_ids,
                iteration + 1,
                total_tools_called,
                mental_models_created,
                tool_trace,
                _get_llm_trace(),
                _log_completion,
                reflect_id,
            )

        # Execute other tools in parallel
        other_tools = [tc for tc in result.tool_calls if tc.name != "done"]
        if other_tools:
            # Add assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [_tool_call_to_dict(tc) for tc in other_tools],
                }
            )

            # Execute tools in parallel
            logger.info(f"[REFLECT {reflect_id}] Executing {len(other_tools)} tools in parallel")
            parallel_start = time.time()

            tool_tasks = [
                _execute_tool_with_timing(tc, lookup_fn, recall_fn, expand_fn, learn_fn) for tc in other_tools
            ]
            tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)

            parallel_ms = int((time.time() - parallel_start) * 1000)
            logger.info(f"[REFLECT {reflect_id}] All {len(other_tools)} tools completed in {parallel_ms}ms")
            total_tools_called += len(other_tools)

            # Process results and add to messages
            for tc, result_data in zip(other_tools, tool_results):
                if isinstance(result_data, Exception):
                    output = {"error": str(result_data)}
                    duration_ms = 0
                    logger.debug(f"[REFLECT {reflect_id}] Tool {tc.name} failed: {result_data}")
                else:
                    output, duration_ms = result_data

                    # Track created mental models
                    if tc.name == "learn" and isinstance(output, dict) and "model_id" in output:
                        mental_models_created.append(output["model_id"])

                    # Track available memory IDs from recall
                    if tc.name == "recall" and isinstance(output, dict) and "memories" in output:
                        for memory in output["memories"]:
                            if "id" in memory:
                                available_memory_ids.add(memory["id"])

                    # Track available model IDs
                    if tc.name in ("list_mental_models", "get_mental_model") and isinstance(output, dict):
                        if output.get("found") and "model" in output:
                            model_id = output["model"].get("id")
                            if model_id:
                                available_model_ids.add(model_id)
                        elif "models" in output:
                            for model in output["models"]:
                                if "id" in model:
                                    available_model_ids.add(model["id"])

                # Add tool result message
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(output, default=str),
                    }
                )

                # Track for logging and context history
                input_dict = {"tool": tc.name, **tc.arguments}
                input_summary = _summarize_input(tc.name, tc.arguments)

                tool_trace.append(ToolCall(tool=tc.name, input=input_dict, output=output, duration_ms=duration_ms))

                try:
                    output_chars = len(json.dumps(output))
                except (TypeError, ValueError):
                    output_chars = len(str(output))

                tool_trace_summary.append(
                    {
                        "tool": tc.name,
                        "input_summary": input_summary,
                        "duration_ms": duration_ms,
                        "output_chars": output_chars,
                    }
                )

                # Keep context history for fallback final prompt
                context_history.append({"tool": tc.name, "input": input_dict, "output": output})

    # Should not reach here
    answer = "I was unable to formulate a complete answer within the iteration limit."
    _log_completion(answer, max_iterations, forced=True)
    return ReflectAgentResult(
        text=answer,
        iterations=max_iterations,
        tools_called=total_tools_called,
        mental_models_created=mental_models_created,
        tool_trace=tool_trace,
        llm_trace=_get_llm_trace(),
    )


def _tool_call_to_dict(tc: "LLMToolCall") -> dict[str, Any]:
    """Convert LLMToolCall to OpenAI message format."""
    return {
        "id": tc.id,
        "type": "function",
        "function": {
            "name": tc.name,
            "arguments": json.dumps(tc.arguments),
        },
    }


def _process_done_tool(
    done_call: "LLMToolCall",
    output_mode: str,
    available_memory_ids: set[str],
    available_model_ids: set[str],
    iterations: int,
    total_tools_called: int,
    mental_models_created: list[str],
    tool_trace: list[ToolCall],
    llm_trace: list[LLMCall],
    log_completion: Callable,
    reflect_id: str,
) -> ReflectAgentResult:
    """Process the done tool call and return the result."""
    args = done_call.arguments

    if output_mode == "observations" and "observations" in args:
        # Process observations
        observations: list[Observation] = []
        used_memory_ids: list[str] = []

        for obs_data in args["observations"]:
            validated_mids = []
            for mid in obs_data.get("memory_ids", []):
                if mid in available_memory_ids:
                    validated_mids.append(mid)
                    if mid not in used_memory_ids:
                        used_memory_ids.append(mid)
                else:
                    logger.debug(f"[REFLECT {reflect_id}] Filtered invalid memory_id: {mid}")

            observations.append(
                Observation(
                    title=obs_data.get("title", ""),
                    text=obs_data.get("text", ""),
                    memory_ids=validated_mids,
                )
            )

        # Build text from observations
        text_parts = []
        for obs in observations:
            if obs.title:
                text_parts.append(f"## {obs.title}\n{obs.text}")
            else:
                text_parts.append(obs.text)
        answer = "\n\n".join(text_parts)

        log_completion(answer, iterations)
        return ReflectAgentResult(
            text=answer,
            observations=observations,
            iterations=iterations,
            tools_called=total_tools_called,
            mental_models_created=mental_models_created,
            tool_trace=tool_trace,
            llm_trace=llm_trace,
            used_memory_ids=used_memory_ids,
        )

    # Default: answer mode
    answer = args.get("answer", "").strip()
    if not answer:
        answer = "No answer provided."

    # Validate IDs
    used_memory_ids = [mid for mid in args.get("memory_ids", []) if mid in available_memory_ids]
    used_model_ids = [mid for mid in args.get("model_ids", []) if mid in available_model_ids]

    log_completion(answer, iterations)
    return ReflectAgentResult(
        text=answer,
        iterations=iterations,
        tools_called=total_tools_called,
        mental_models_created=mental_models_created,
        tool_trace=tool_trace,
        llm_trace=llm_trace,
        used_memory_ids=used_memory_ids,
        used_model_ids=used_model_ids,
    )


async def _execute_tool_with_timing(
    tc: "LLMToolCall",
    lookup_fn: Callable[[str | None], Awaitable[dict[str, Any]]],
    recall_fn: Callable[[str, int], Awaitable[dict[str, Any]]],
    expand_fn: Callable[[list[str], str], Awaitable[dict[str, Any]]],
    learn_fn: Callable[[MentalModelInput], Awaitable[dict[str, Any]]] | None = None,
) -> tuple[dict[str, Any], int]:
    """Execute a tool call and return result with timing."""
    tool_desc = _get_tool_description(tc.name, tc.arguments)
    logger.info(f"[TOOL DEBUG] Starting {tc.name}: {tool_desc}")
    start = time.time()

    result = await _execute_tool(tc.name, tc.arguments, lookup_fn, recall_fn, expand_fn, learn_fn)

    duration_ms = int((time.time() - start) * 1000)
    try:
        result_chars = len(json.dumps(result))
    except (TypeError, ValueError):
        result_chars = len(str(result))
    logger.info(f"[TOOL DEBUG] Completed {tc.name}: {duration_ms}ms, {result_chars} chars output")

    return result, duration_ms


def _get_tool_description(tool_name: str, args: dict[str, Any]) -> str:
    """Get a brief description of the tool call for logging."""
    if tool_name == "list_mental_models":
        return "listing all models"
    elif tool_name == "get_mental_model":
        return f"model_id={args.get('model_id')}"
    elif tool_name == "recall":
        query = args.get("query", "")
        query_preview = query[:30] + "..." if len(query) > 30 else query
        return f"query='{query_preview}', max_tokens={args.get('max_tokens', 2048)}"
    elif tool_name == "learn":
        return f"name={args.get('name', '?')}"
    elif tool_name == "expand":
        count = len(args.get("memory_ids", []))
        return f"{count} memory_ids, depth={args.get('depth', 'chunk')}"
    return str(args)[:50]


async def _execute_tool(
    tool_name: str,
    args: dict[str, Any],
    lookup_fn: Callable[[str | None], Awaitable[dict[str, Any]]],
    recall_fn: Callable[[str, int], Awaitable[dict[str, Any]]],
    expand_fn: Callable[[list[str], str], Awaitable[dict[str, Any]]],
    learn_fn: Callable[[MentalModelInput], Awaitable[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Execute a single tool by name."""
    if tool_name == "list_mental_models":
        return await lookup_fn(None)

    elif tool_name == "get_mental_model":
        model_id = args.get("model_id")
        if not model_id:
            return {"error": "get_mental_model requires model_id"}
        return await lookup_fn(model_id)

    elif tool_name == "recall":
        query = args.get("query")
        if not query:
            return {"error": "recall requires a query parameter"}
        max_tokens = args.get("max_tokens", 2048)
        return await recall_fn(query, max_tokens)

    elif tool_name == "learn":
        if learn_fn is None:
            return {"error": "learn tool is not available"}
        name = args.get("name")
        description = args.get("description")
        if not name or not description:
            return {"error": "learn requires name and description"}
        return await learn_fn(MentalModelInput(name=name, description=description))

    elif tool_name == "expand":
        memory_ids = args.get("memory_ids", [])
        if not memory_ids:
            return {"error": "expand requires memory_ids"}
        depth = args.get("depth", "chunk")
        return await expand_fn(memory_ids, depth)

    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _summarize_input(tool_name: str, args: dict[str, Any]) -> str:
    """Create a brief summary of tool input for logging."""
    if tool_name == "list_mental_models":
        return ""
    elif tool_name == "get_mental_model":
        return args.get("model_id", "?")
    elif tool_name == "recall":
        query = args.get("query", "")
        return f"'{query[:20]}...'" if len(query) > 20 else f"'{query}'"
    elif tool_name == "learn":
        return args.get("name", "?")[:20]
    elif tool_name == "expand":
        count = len(args.get("memory_ids", []))
        depth = args.get("depth", "chunk")
        return f"{count}ids/{depth}"
    return ""
