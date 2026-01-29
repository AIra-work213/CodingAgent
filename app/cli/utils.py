"""Вспомогательные функции CLI"""

import asyncio
from datetime import datetime
from typing import Any

import httpx

from app.core.models.task import Task, TaskStatus


async def create_task(
    server_url: str,
    task_type: str,
    issue_number: int | None = None,
    pr_number: int | None = None,
    branch_name: str | None = None,
    max_iterations: int = 5,
    repo_url: str | None = None,
    github_token: str | None = None,
) -> Task:
    """Создать новую задачу через API"""
    async with httpx.AsyncClient() as client:
        json_data = {
            "type": task_type,
            "issue_number": issue_number,
            "pr_number": pr_number,
            "branch_name": branch_name,
            "max_iterations": max_iterations,
        }
        if repo_url:
            json_data["repo_url"] = repo_url
        if github_token:
            json_data["github_token"] = github_token

        response = await client.post(
            f"{server_url}/tasks",
            json=json_data,
            timeout=30.0,
        )
        response.raise_for_status()
        return Task.model_validate(response.json())


async def get_task(server_url: str, task_id: str) -> Task | None:
    """Получить детали задачи"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{server_url}/tasks/{task_id}", timeout=10.0)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return Task.model_validate(response.json())
    except Exception:
        return None


async def list_tasks(
    server_url: str, status: TaskStatus | None = None, active_only: bool = False
) -> list[Task]:
    """Получить список задач"""
    async with httpx.AsyncClient() as client:
        params = {}
        if status:
            params["status"] = status.value
        if active_only:
            params["active_only"] = True

        response = await client.get(f"{server_url}/tasks", params=params, timeout=10.0)
        response.raise_for_status()
        return [Task.model_validate(t) for t in response.json()]


async def cancel_task(server_url: str, task_id: str) -> Task:
    """Отменить задачу"""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{server_url}/tasks/{task_id}", timeout=10.0)
        response.raise_for_status()
        return Task.model_validate(response.json())


async def get_task_logs(server_url: str, task_id: str, limit: int = 100) -> list[str]:
    """Получить логи задачи"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{server_url}/tasks/{task_id}/logs",
            params={"limit": limit},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def get_task_diff(server_url: str, task_id: str) -> dict[str, str]:
    """Получить изменения файлов задачи"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/tasks/{task_id}/diff", timeout=10.0)
        response.raise_for_status()
        return response.json()


async def check_server_health(server_url: str) -> dict[str, Any] | None:
    """Проверить работоспособность сервера"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{server_url}/health", timeout=5.0)
            response.raise_for_status()
            return response.json()
    except Exception:
        return None


def format_duration(seconds: float | None) -> str:
    """Форматировать продолжительность в удобочитаемый формат"""
    if seconds is None:
        return "N/A"

    if seconds < 60:
        return f"{seconds:.1f}с"
    if seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}м"
    hours = seconds / 3600
    return f"{hours:.1f}ч"


def format_status(status: TaskStatus) -> str:
    """Форматировать статус задачи с эмодзи"""
    status_emoji = {
        TaskStatus.PENDING: "⏳",
        TaskStatus.RUNNING: "🔄",
        TaskStatus.REVIEWING: "👀",
        TaskStatus.COMPLETED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.CANCELLED: "🚫",
    }
    return f"{status_emoji.get(status, '')} {status.value}"


def format_progress(progress: float) -> str:
    """Форматировать прогресс как процент с индикатором"""
    percent = int(progress * 100)
    bar_length = 20
    filled = int(bar_length * progress)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"{percent}% [{bar}]"


def format_timestamp(dt: datetime | None) -> str:
    """Форматировать дату и время для отображения"""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")
