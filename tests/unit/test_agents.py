"""Unit tests for Agent workflows"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
async def test_code_agent_initial_state():
    """Test Code Agent initial state structure"""
    from app.core.agents.code_agent import CodeAgentState

    state: CodeAgentState = {
        "issue_number": 1,
        "branch_name": "test-branch",
        "issue": "",
        "requirements": {},
        "implementation_plan": {},
        "current_code": {},
        "generated_code": {},
        "validation_results": {},
        "pr_url": "",
        "pr_number": 0,
        "feedback": [],
        "iteration": 1,
        "max_iterations": 5,
        "status": "parsing",
        "error": None,
        "messages": [],
    }

    assert state["issue_number"] == 1
    assert state["status"] == "parsing"
    assert state["iteration"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reviewer_agent_initial_state():
    """Test Reviewer Agent initial state structure"""
    from app.core.agents.reviewer_agent import ReviewerAgentState

    state: ReviewerAgentState = {
        "pr_number": 1,
        "issue_number": None,
        "pr_diff": "",
        "pr_title": "",
        "requirements": {},
        "ci_results": {},
        "review_comments": [],
        "review_summary": "",
        "approval_decision": "comment",
        "status": "analyzing",
        "error": None,
        "messages": [],
    }

    assert state["pr_number"] == 1
    assert state["status"] == "analyzing"
    assert state["approval_decision"] == "comment"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parse_issue_node(mock_github, mock_llm):
    """Test parse_issue node"""
    import json
    from app.core.agents.code_agent import parse_issue_node, CodeAgentState

    state: CodeAgentState = {
        "issue_number": 1,
        "branch_name": "test-branch",
        "issue": "",
        "requirements": {},
        "implementation_plan": {},
        "current_code": {},
        "generated_code": {},
        "validation_results": {},
        "pr_url": "",
        "pr_number": 0,
        "feedback": [],
        "iteration": 1,
        "max_iterations": 5,
        "status": "parsing",
        "error": None,
        "messages": [],
    }

    result = parse_issue_node(state)

    assert result["status"] == "analyzing"
    assert "requirements" in result
    # JSON parsing from LLM response
    assert result["requirements"]["type"] in ["feature", "bugfix", "refactor", "test", "docs", "chore"]


@pytest.mark.unit
def test_should_continue():
    """Test should_continue decision function"""
    from app.core.agents.code_agent import should_continue, CodeAgentState

    # Test done state
    state_done: CodeAgentState = {
        "issue_number": 1,
        "branch_name": "test",
        "issue": "",
        "requirements": {},
        "implementation_plan": {},
        "current_code": {},
        "generated_code": {},
        "validation_results": {},
        "pr_url": "",
        "pr_number": 0,
        "feedback": [],
        "iteration": 1,
        "max_iterations": 5,
        "status": "done",
        "error": None,
        "messages": [],
    }

    assert should_continue(state_done) == "end"

    # Test error state
    state_error = state_done.copy()
    state_error["status"] = "error"
    assert should_continue(state_error) == "end"

    # Test continuing state
    state_continuing = state_done.copy()
    state_continuing["status"] = "parsing"
    assert should_continue(state_continuing) == "continue"
