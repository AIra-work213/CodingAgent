"""Pytest configuration and fixtures"""

import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.core.config import Settings
from app.api.main import app


# Set test environment before importing app modules
os.environ.setdefault("OPENROUTER_API_KEY", "test_key_for_testing")
os.environ.setdefault("GITHUB_TOKEN", "test_token_for_testing")
os.environ.setdefault("GITHUB_REPO", "test/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("POSTGRES_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("API_HOST", "127.0.0.1")
os.environ.setdefault("API_PORT", "8001")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("MAX_ITERATIONS", "3")
os.environ.setdefault("CODE_QUALITY_CHECKS", "false")


@pytest.fixture(autouse=True)
def mock_settings_env(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_key_for_testing")
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_for_testing")
    monkeypatch.setenv("GITHUB_REPO", "test/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "8001")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("MAX_ITERATIONS", "3")
    monkeypatch.setenv("CODE_QUALITY_CHECKS", "false")


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for testing"""
    return Settings(
        openrouter_api_key="test_api_key",
        github_token="test_github_token",
        github_repo="test/test",
        github_base_url="https://api.github.com",
        redis_url="redis://localhost:6379/1",
        postgres_url="postgresql://test:test@localhost:5432/test",
        api_host="127.0.0.1",
        api_port=8001,
        debug=True,
        langchain_tracing_v2=False,
        max_iterations=3,
        agent_timeout=60,
        code_quality_checks=False,
        default_model="gpt-4o-mini",
    )


@pytest.fixture
def mock_github() -> Generator[MagicMock, None, None]:
    """Mock GitHub client"""
    with patch("app.core.tools.github_tools.get_github_client") as mock:
        client = MagicMock()
        mock.return_value = client

        # Mock repo
        repo = MagicMock()
        client.get_repo.return_value = repo

        # Mock issue
        issue = MagicMock()
        issue.number = 1
        issue.title = "Test Issue"
        issue.body = "Test issue body"
        issue.state = "open"
        issue.user = MagicMock()
        issue.user.login = "testuser"
        issue.created_at = MagicMock()
        issue.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        issue.labels = []
        issue.get_comments.return_value = []

        repo.get_issue.return_value = issue
        repo.create_pull.return_value = MagicMock(html_url="https://github.com/test/test/pull/1")
        repo.get_branch.return_value = MagicMock(commit=MagicMock(sha="abc123"))

        # Mock file operations
        contents = MagicMock()
        contents.type = "file"
        contents.content = ""
        contents.sha = "abc123"

        # Setup get_contents to raise exception for new files
        original_get_contents = repo.get_contents

        def get_contents_side_effect(*args, **kwargs):
            path = kwargs.get("path", args[0] if args else "")
            if "new" in str(path):
                raise Exception("Not found")
            # Return contents for existing files
            return contents

        repo.get_contents = MagicMock(side_effect=get_contents_side_effect)
        repo.create_file.return_value = {"commit": MagicMock(html_url="https://github.com/test/test/commit/1")}
        repo.update_file.return_value = {"commit": MagicMock(html_url="https://github.com/test/test/commit/1")}
        repo.create_git_ref.return_value = MagicMock()

        yield client


@pytest.fixture
def mock_llm():
    """Mock LLM responses"""
    with patch("app.core.agents.code_agent.get_planning_llm") as mock_planning, \
         patch("app.core.agents.code_agent.get_coding_llm") as mock_coding, \
         patch("app.core.agents.code_agent.get_review_llm") as mock_review:

        # Create proper mock responses with type conversion
        planning_result = MagicMock()
        planning_result.content = '{"type": "feature", "title": "Test Feature", "description": "A test feature", "acceptance_criteria": ["criterion1"], "priority": "Medium", "complexity": "Simple", "files_affected": ["test.py"], "dependencies": []}'

        planning_invoke = MagicMock()
        planning_invoke.return_value = planning_result
        mock_planning.return_value = planning_invoke

        # Mock coding LLM response
        coding_result = MagicMock()
        coding_result.content = '```python\ndef test_function():\n    """Test function"""\n    return "test"\n```'

        coding_invoke = MagicMock()
        coding_invoke.return_value = coding_result
        mock_coding.return_value = coding_invoke

        # Mock review LLM response
        review_result = MagicMock()
        review_result.content = '{"is_valid": true, "issues": [], "summary": "Code looks good"}'

        review_invoke = MagicMock()
        review_invoke.return_value = review_result
        mock_review.return_value = review_invoke

        yield {
            "planning": mock_planning,
            "coding": mock_coding,
            "review": mock_review,
        }


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing API"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_issue_data() -> dict:
    """Sample issue data for testing"""
    return {
        "issue_number": 1,
        "title": "Add new feature",
        "body": "Add a new feature to the application",
        "labels": ["enhancement", "agent-task"],
    }


@pytest.fixture
def sample_pr_data() -> dict:
    """Sample PR data for testing"""
    return {
        "pr_number": 1,
        "title": "[Agent] Add new feature",
        "body": "Implementation of the new feature",
        "head": {"ref": "agent/issue-1", "sha": "abc123"},
        "base": {"ref": "main"},
    }


# ============================================================================
# Async test utilities
# ============================================================================

@pytest.fixture
def mock_langgraph():
    """Mock LangGraph workflow"""
    with patch("app.core.agents.code_agent.create_code_agent_graph") as mock_graph:
        graph = MagicMock()
        mock_graph.return_value.compile.return_value = graph

        # Mock successful execution
        graph.ainvoke = AsyncMock(return_value={
            "status": "done",
            "pr_url": "https://github.com/test/test/pull/1",
            "requirements": {"type": "feature"},
            "generated_code": {"test.py": "def test(): pass"},
            "validation_results": {"is_valid": True},
            "error": None,
        })

        yield graph
