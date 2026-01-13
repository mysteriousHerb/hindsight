"""
Tags filtering utilities for retrieval.

Provides SQL building functions for filtering memories by tags.
Supports two matching modes:
- "any" (OR): a memory matches if ANY of its tags overlap with ANY of the request tags
- "all" (AND): a memory matches if ALL of the request tags are present in its tags
"""

from typing import Literal

TagsMatch = Literal["any", "all"]


def build_tags_where_clause(
    tags: list[str] | None,
    param_offset: int = 1,
    table_alias: str = "",
    match: TagsMatch = "any",
) -> tuple[str, list, int]:
    """
    Build a SQL WHERE clause for filtering by tags.

    Supports two matching modes:
    - "any" (default): Uses PostgreSQL array overlap operator (&&)
      Memory with tags ['a', 'b'] matches request tags ['a'] (overlap on 'a')
    - "all": Uses PostgreSQL array contains operator (@>)
      Memory with tags ['a', 'b'] matches request tags ['a'] (contains 'a')
      Memory with tags ['a'] does NOT match request tags ['a', 'b'] (missing 'b')

    Args:
        tags: List of tags to filter by. If None or empty, returns empty clause (no filtering).
        param_offset: Starting parameter number for SQL placeholders (default 1).
        table_alias: Optional table alias prefix (e.g., "mu." for "memory_units mu").
        match: Matching mode - "any" for OR, "all" for AND. Defaults to "any".

    Returns:
        Tuple of (sql_clause, params, next_param_offset):
        - sql_clause: SQL WHERE clause string (e.g., "AND mu.tags && $1")
        - params: List of parameter values to bind
        - next_param_offset: Next available parameter number

    Example:
        >>> clause, params, next_offset = build_tags_where_clause(['user_a', 'user_b'], 3, 'mu.')
        >>> print(clause)  # "AND mu.tags && $3"
        >>> print(params)  # [['user_a', 'user_b']]
        >>> print(next_offset)  # 4
    """
    if not tags:
        return "", [], param_offset

    column = f"{table_alias}tags" if table_alias else "tags"
    # && = overlap (any match), @> = contains (all must match)
    operator = "&&" if match == "any" else "@>"
    clause = f"AND {column} {operator} ${param_offset}"
    return clause, [tags], param_offset + 1


def build_tags_where_clause_simple(
    tags: list[str] | None,
    param_num: int,
    table_alias: str = "",
    match: TagsMatch = "any",
) -> str:
    """
    Build a simple SQL WHERE clause for tags filtering.

    This is a convenience version that returns just the clause string,
    assuming the caller will add the tags array to their params list.

    Args:
        tags: List of tags to filter by. If None or empty, returns empty string.
        param_num: Parameter number to use in the clause.
        table_alias: Optional table alias prefix.
        match: Matching mode - "any" for OR, "all" for AND. Defaults to "any".

    Returns:
        SQL clause string (e.g., "AND mu.tags && $3") or empty string.
    """
    if not tags:
        return ""

    column = f"{table_alias}tags" if table_alias else "tags"
    operator = "&&" if match == "any" else "@>"
    return f"AND {column} {operator} ${param_num}"
