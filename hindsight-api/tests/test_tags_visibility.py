"""
Tests for tags-based visibility scoping.

This module tests the tags feature which allows filtering memories by visibility tags.
Use cases:
- Multi-user agent: Agent has a single memory bank, users should only see memories from
  conversations they participated in
- Student tracking: Teacher tracks students, students should only see their own data

The tags use OR-based matching: a memory matches if ANY of its tags overlap with the request tags.
"""
import pytest
import pytest_asyncio
import httpx
from datetime import datetime
from hindsight_api.api import create_app
from hindsight_api.engine.search.tags import build_tags_where_clause_simple


# ============================================================================
# Unit Tests for tags SQL builder
# ============================================================================


class TestTagsWhereClauseBuilder:
    """Unit tests for the tags WHERE clause SQL builder."""

    def test_no_tags_returns_empty_string(self):
        """When tags is None, should return empty string (no filtering)."""
        result = build_tags_where_clause_simple(None, 5)
        assert result == ""

    def test_empty_tags_list_returns_empty_string(self):
        """When tags is an empty list, should return empty string (no filtering)."""
        result = build_tags_where_clause_simple([], 5)
        assert result == ""

    def test_tags_generates_overlap_clause(self):
        """When tags are provided, should generate PostgreSQL array overlap clause."""
        result = build_tags_where_clause_simple(["user_a"], 5)
        assert result == "AND tags && $5"

    def test_tags_with_different_param_num(self):
        """Should use the provided parameter number."""
        result = build_tags_where_clause_simple(["user_a", "user_b"], 3)
        assert result == "AND tags && $3"

    def test_tags_with_table_alias(self):
        """Should include table alias when provided."""
        result = build_tags_where_clause_simple(["user_a"], 5, table_alias="mu.")
        assert result == "AND mu.tags && $5"

    def test_tags_match_any_uses_overlap(self):
        """When match='any', should use overlap operator (&&)."""
        result = build_tags_where_clause_simple(["user_a"], 5, match="any")
        assert result == "AND tags && $5"

    def test_tags_match_all_uses_contains(self):
        """When match='all', should use contains operator (@>)."""
        result = build_tags_where_clause_simple(["user_a"], 5, match="all")
        assert result == "AND tags @> $5"

    def test_tags_match_all_with_table_alias(self):
        """Should use contains operator with table alias."""
        result = build_tags_where_clause_simple(["user_a", "user_b"], 3, table_alias="mu.", match="all")
        assert result == "AND mu.tags @> $3"


# ============================================================================
# Integration Tests for tags in retain/recall/reflect
# ============================================================================


@pytest_asyncio.fixture
async def api_client(memory):
    """Create an async test client for the FastAPI app."""
    app = create_app(memory, initialize_memory=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_bank_id():
    """Provide a unique bank ID for this test run."""
    return f"tags_test_{datetime.now().timestamp()}"


@pytest.mark.asyncio
async def test_retain_with_tags(api_client, test_bank_id):
    """Test that memories can be stored with tags."""
    # Store memory with tags
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {
                    "content": "Alice loves hiking in the mountains.",
                    "tags": ["user_alice"]
                }
            ]
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["items_count"] == 1


@pytest.mark.asyncio
async def test_retain_with_document_tags(api_client, test_bank_id):
    """Test that document-level tags are applied to all items."""
    # Store memories with document-level tags
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "document_tags": ["session_123"],
            "items": [
                {"content": "Bob discussed the quarterly report."},
                {"content": "Charlie mentioned the new product launch."}
            ]
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["items_count"] == 2


@pytest.mark.asyncio
async def test_retain_merges_document_and_item_tags(api_client, test_bank_id):
    """Test that document tags and item tags are merged."""
    # Store memory with both document and item tags
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "document_tags": ["session_abc"],
            "items": [
                {
                    "content": "Dave talked about machine learning.",
                    "tags": ["user_dave"]
                }
            ]
        }
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True


@pytest.mark.asyncio
async def test_recall_without_tags_returns_all_memories(api_client, test_bank_id):
    """Test that recall without tags returns all memories (no filtering)."""
    # Store memories for different users
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {"content": "Eve works on natural language processing.", "tags": ["user_eve"]},
                {"content": "Frank specializes in computer vision.", "tags": ["user_frank"]},
            ]
        }
    )
    assert response.status_code == 200

    # Recall without tags - should return all
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories/recall",
        json={"query": "Who works on what?", "budget": "low"}
    )
    assert response.status_code == 200
    results = response.json()["results"]

    # Should find both Eve and Frank
    texts = [r["text"] for r in results]
    assert any("Eve" in t for t in texts), "Should find Eve"
    assert any("Frank" in t for t in texts), "Should find Frank"


@pytest.mark.asyncio
async def test_recall_with_tags_filters_memories(api_client, test_bank_id):
    """Test that recall with tags only returns matching memories."""
    # Store memories for different users
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {"content": "Grace is a data scientist at Google.", "tags": ["user_grace"]},
                {"content": "Henry is a software engineer at Meta.", "tags": ["user_henry"]},
            ]
        }
    )
    assert response.status_code == 200

    # Recall with user_grace tag - should only return Grace's memory
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories/recall",
        json={"query": "Who works at which company?", "budget": "low", "tags": ["user_grace"]}
    )
    assert response.status_code == 200
    results = response.json()["results"]

    # Should find Grace but not Henry
    texts = [r["text"] for r in results]
    assert any("Grace" in t for t in texts), "Should find Grace with user_grace tag"
    # Henry should NOT be found since he has user_henry tag
    assert not any("Henry" in t for t in texts), "Should NOT find Henry (different tag)"


@pytest.mark.asyncio
async def test_recall_with_multiple_tags_uses_or_matching(api_client, test_bank_id):
    """Test that multiple tags use OR matching (any match returns the memory)."""
    # Store memories for different users
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {"content": "Ivan leads the security team.", "tags": ["user_ivan"]},
                {"content": "Julia manages the design team.", "tags": ["user_julia"]},
                {"content": "Karl oversees the marketing team.", "tags": ["user_karl"]},
            ]
        }
    )
    assert response.status_code == 200

    # Recall with user_ivan OR user_julia - should return both Ivan and Julia, but not Karl
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories/recall",
        json={"query": "Who leads which team?", "budget": "low", "tags": ["user_ivan", "user_julia"]}
    )
    assert response.status_code == 200
    results = response.json()["results"]

    texts = [r["text"] for r in results]
    assert any("Ivan" in t for t in texts), "Should find Ivan (tag matches)"
    assert any("Julia" in t for t in texts), "Should find Julia (tag matches)"
    assert not any("Karl" in t for t in texts), "Should NOT find Karl (tag doesn't match)"


@pytest.mark.asyncio
async def test_recall_returns_memories_with_any_overlapping_tag(api_client, test_bank_id):
    """Test that memories with multiple tags are returned if ANY tag matches."""
    # Store memory with multiple tags
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {
                    "content": "Lisa and Mike discussed the budget in a group chat.",
                    "tags": ["user_lisa", "user_mike"]  # Memory visible to both
                },
                {"content": "Nancy reviewed the budget alone.", "tags": ["user_nancy"]},
            ]
        }
    )
    assert response.status_code == 200

    # Recall with user_lisa - should return the group chat memory
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories/recall",
        json={"query": "What was discussed about the budget?", "budget": "low", "tags": ["user_lisa"]}
    )
    assert response.status_code == 200
    results = response.json()["results"]

    texts = [r["text"] for r in results]
    assert any("Lisa" in t and "Mike" in t for t in texts), "Should find group chat (Lisa is in tags)"
    assert not any("Nancy" in t for t in texts), "Should NOT find Nancy's memory"


@pytest.mark.asyncio
async def test_reflect_with_tags_filters_memories(api_client, test_bank_id):
    """Test that reflect with tags only uses matching memories for reasoning."""
    # Store different memories for different users
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {"content": "Oscar's favorite color is blue.", "tags": ["user_oscar"]},
                {"content": "Peter's favorite color is red.", "tags": ["user_peter"]},
            ]
        }
    )
    assert response.status_code == 200

    # Reflect with user_oscar tag - should only use Oscar's memories
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/reflect",
        json={
            "query": "What is the favorite color?",
            "budget": "low",
            "tags": ["user_oscar"],
            "include": {"facts": {}}  # Request facts to verify what was used
        }
    )
    assert response.status_code == 200
    result = response.json()

    # The response should mention Oscar's color (blue), not Peter's (red)
    # Note: We can check based_on facts if they're returned
    if result.get("based_on"):
        fact_texts = [f["text"] for f in result["based_on"]]
        # Should use Oscar's memory
        assert any("Oscar" in t or "blue" in t for t in fact_texts), "Should use Oscar's memory"


@pytest.mark.asyncio
async def test_recall_with_empty_tags_returns_all(api_client, test_bank_id):
    """Test that empty tags list behaves same as no tags (returns all)."""
    # Store memories
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories",
        json={
            "items": [
                {"content": "Quinn studies mathematics.", "tags": ["user_quinn"]},
                {"content": "Rachel studies physics.", "tags": ["user_rachel"]},
            ]
        }
    )
    assert response.status_code == 200

    # Recall with empty tags list - should return all
    response = await api_client.post(
        f"/v1/default/banks/{test_bank_id}/memories/recall",
        json={"query": "Who studies what?", "budget": "low", "tags": []}
    )
    assert response.status_code == 200
    results = response.json()["results"]

    texts = [r["text"] for r in results]
    assert any("Quinn" in t for t in texts), "Should find Quinn"
    assert any("Rachel" in t for t in texts), "Should find Rachel"


@pytest.mark.asyncio
async def test_multi_user_agent_visibility(api_client):
    """
    Test multi-user agent visibility scoping.

    Scenario:
    - Agent has one memory bank
    - Agent chats with User A (room 1) and User B (room 2) separately
    - Agent also hosts a group chat with both users (room 3)
    - User A should only see memories from rooms 1 and 3
    - User B should only see memories from rooms 2 and 3
    - Agent (no filter) should see all memories
    """
    bank_id = f"multi_user_test_{datetime.now().timestamp()}"

    # Store memories from different chat rooms
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories",
        json={
            "items": [
                # Room 1: Agent + User A private chat
                {"content": "User A said they prefer morning meetings.", "tags": ["user_a"]},
                # Room 2: Agent + User B private chat
                {"content": "User B mentioned they like afternoon meetings.", "tags": ["user_b"]},
                # Room 3: Group chat with both users
                {"content": "In the group meeting, they agreed to meet at noon.", "tags": ["user_a", "user_b"]},
            ]
        }
    )
    assert response.status_code == 200

    # User A queries - should see their private chat and group chat
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories/recall",
        json={"query": "What meeting time preferences were discussed?", "budget": "low", "tags": ["user_a"]}
    )
    assert response.status_code == 200
    user_a_results = response.json()["results"]
    user_a_texts = [r["text"] for r in user_a_results]

    assert any("morning" in t for t in user_a_texts), "User A should see their own preference (morning)"
    assert any("noon" in t for t in user_a_texts), "User A should see group chat (noon)"
    assert not any("afternoon" in t for t in user_a_texts), "User A should NOT see User B's private preference"

    # User B queries - should see their private chat and group chat
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories/recall",
        json={"query": "What meeting time preferences were discussed?", "budget": "low", "tags": ["user_b"]}
    )
    assert response.status_code == 200
    user_b_results = response.json()["results"]
    user_b_texts = [r["text"] for r in user_b_results]

    assert any("afternoon" in t for t in user_b_texts), "User B should see their own preference (afternoon)"
    assert any("noon" in t for t in user_b_texts), "User B should see group chat (noon)"
    assert not any("morning" in t for t in user_b_texts), "User B should NOT see User A's private preference"

    # Agent queries (no filter) - should see everything
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories/recall",
        json={"query": "What meeting time preferences were discussed?", "budget": "low"}  # No tags
    )
    assert response.status_code == 200
    agent_results = response.json()["results"]
    agent_texts = [r["text"] for r in agent_results]

    assert any("morning" in t for t in agent_texts), "Agent should see User A's preference"
    assert any("afternoon" in t for t in agent_texts), "Agent should see User B's preference"
    assert any("noon" in t for t in agent_texts), "Agent should see group chat"


@pytest.mark.asyncio
async def test_student_tracking_visibility(api_client):
    """
    Test student tracking visibility scoping.

    Scenario:
    - Teacher bot has one memory bank
    - Teacher records observations for Student A, Student B
    - Student A should only see their own data
    - Teacher (no filter) should see all student data
    """
    bank_id = f"student_test_{datetime.now().timestamp()}"

    # Store memories for different students
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories",
        json={
            "items": [
                {"content": "Student A showed improvement in algebra today.", "tags": ["student_a"]},
                {"content": "Student B struggled with geometry concepts.", "tags": ["student_b"]},
                {"content": "Student A participated actively in class discussion.", "tags": ["student_a"]},
            ]
        }
    )
    assert response.status_code == 200

    # Student A queries - should only see their own data
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories/recall",
        json={"query": "How am I doing in class?", "budget": "low", "tags": ["student_a"]}
    )
    assert response.status_code == 200
    student_a_results = response.json()["results"]
    student_a_texts = [r["text"] for r in student_a_results]

    assert any("algebra" in t for t in student_a_texts), "Student A should see their algebra progress"
    assert any("participated" in t for t in student_a_texts), "Student A should see their participation"
    assert not any("Student B" in t or "geometry" in t for t in student_a_texts), "Student A should NOT see Student B's data"

    # Teacher queries (no filter) - should see all students
    response = await api_client.post(
        f"/v1/default/banks/{bank_id}/memories/recall",
        json={"query": "Which students need help?", "budget": "low"}  # No tags
    )
    assert response.status_code == 200
    teacher_results = response.json()["results"]
    teacher_texts = [r["text"] for r in teacher_results]

    assert any("Student A" in t for t in teacher_texts), "Teacher should see Student A's data"
    assert any("Student B" in t for t in teacher_texts), "Teacher should see Student B's data"
