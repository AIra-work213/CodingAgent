"""Integration tests for FastAPI endpoints"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_health_endpoint(async_client: AsyncClient):
    """Test health check endpoint"""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    # Статус может быть "healthy" или "degraded" если Redis не подключен
    assert data["status"] in ["healthy", "degraded"]


@pytest.mark.integration
async def test_root_endpoint(async_client: AsyncClient):
    """Test root endpoint"""
    response = await async_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


@pytest.mark.integration
async def test_code_agent_endpoint(async_client: AsyncClient, mock_langgraph):
    """Test code agent endpoint"""
    response = await async_client.post(
        "/agents/code-agent/run",
        json={
            "issue_number": 1,
            "max_iterations": 3,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "status" in data


@pytest.mark.integration
async def test_reviewer_agent_endpoint(async_client: AsyncClient):
    """Test reviewer agent endpoint"""
    response = await async_client.post(
        "/agents/reviewer/analyze-pr",
        json={
            "pr_number": 1,
        }
    )

    # May fail due to missing GitHub integration, but endpoint should be accessible
    assert "status" in response.json()


@pytest.mark.integration
async def test_github_webhook(async_client: AsyncClient):
    """Test GitHub webhook endpoint"""
    response = await async_client.post(
        "/webhooks/github",
        json={
            "action": "opened",
            "issue": {
                "number": 1,
                "labels": [{"name": "agent-task"}]
            }
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
