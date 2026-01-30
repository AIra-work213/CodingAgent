"""Эндпоинты API для мониторинга репозиториев"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.monitoring import get_monitor

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


class RepoAddRequest(BaseModel):
    """Запрос на добавление репозитория для мониторинга"""

    owner: str = Field(..., description="Владелец репозитория (организация или пользователь)")
    repo: str = Field(..., description="Название репозитория")
    github_token: str = Field(..., description="GitHub токен для доступа к репозиторию")
    poll_interval: int = Field(default=60, ge=10, le=3600, description="Интервал опроса в секундах")


class RepoResponse(BaseModel):
    """Ответ с информацией о репозитории"""

    repo: str
    enabled: bool
    poll_interval: int
    last_checked: str
    processed_issues_count: int


class MonitorStatusResponse(BaseModel):
    """Ответ со статусом мониторинга"""

    running: bool
    repos_count: int
    repos: list[dict[str, Any]]


@router.post("/repos", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def add_monitored_repo(request: RepoAddRequest) -> dict[str, Any]:
    """
    Добавить репозиторий на мониторинг.

    **Пример запроса:**
    ```json
    {
        "owner": "facebook",
        "repo": "react",
        "github_token": "ghp_xxxxxxxxxxxx",
        "poll_interval": 60
    }
    ```
    """
    monitor = get_monitor()

    # Initialize monitor if needed
    await monitor.init_redis()

    repo = await monitor.add_repo(
        owner=request.owner,
        repo=request.repo,
        github_token=request.github_token,
        poll_interval=request.poll_interval,
    )

    return {
        "success": True,
        "repo": repo.repo_key,
        "message": f"Repository {repo.repo_key} added to monitoring",
    }


@router.delete("/repos/{owner}/{repo}", response_model=dict[str, Any])
async def remove_monitored_repo(owner: str, repo: str) -> dict[str, Any]:
    """Удалить репозиторий из мониторинга."""
    monitor = get_monitor()
    success = await monitor.remove_repo(owner, repo)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {owner}/{repo} not found in monitoring",
        )

    return {
        "success": True,
        "message": f"Repository {owner}/{repo} removed from monitoring",
    }


@router.get("/repos", response_model=list[RepoResponse])
async def list_monitored_repos() -> list[RepoResponse]:
    """Получить список всех отслеживаемых репозиториев."""
    monitor = get_monitor()
    repos = await monitor.list_repos()

    return [
        RepoResponse(
            repo=r["repo"],
            enabled=r["enabled"],
            poll_interval=r["poll_interval"],
            last_checked=r["last_checked"],
            processed_issues_count=r["processed_issues_count"],
        )
        for r in repos
    ]


@router.get("/status", response_model=MonitorStatusResponse)
async def get_monitoring_status() -> MonitorStatusResponse:
    """Получить текущий статус мониторинга."""
    monitor = get_monitor()
    status_data = monitor.get_status()

    return MonitorStatusResponse(**status_data)


@router.post("/start", response_model=dict[str, Any])
async def start_monitoring() -> dict[str, Any]:
    """Запустить мониторинг всех добавленных репозиториев."""
    monitor = get_monitor()

    if monitor.running:
        return {"success": True, "message": "Monitoring is already running"}

    await monitor.start()

    return {"success": True, "message": "Monitoring started"}


@router.post("/stop", response_model=dict[str, Any])
async def stop_monitoring() -> dict[str, Any]:
    """Остановить мониторинг."""
    monitor = get_monitor()

    if not monitor.running:
        return {"success": True, "message": "Monitoring is not running"}

    await monitor.stop()

    return {"success": True, "message": "Monitoring stopped"}
