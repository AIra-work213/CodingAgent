"""Эндпоинты API управления задачами"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.models.task import Task, TaskCreateRequest, TaskStatus
from app.core.task_manager import get_task_manager

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(request: TaskCreateRequest) -> Task:
    """
    Создать новую задачу для генерации кода или рецензирования.

    **Примеры запросов:**

    Задача Code Agent:
    ```json
    {
        "type": "code-agent",
        "issue_number": 123,
        "branch_name": "agent/issue-123",
        "max_iterations": 5
    }
    ```

    Задача Reviewer:
    ```json
    {
        "type": "reviewer",
        "pr_number": 456,
        "issue_number": 123
    }
    ```
    """
    manager = await get_task_manager()
    task = await manager.create(request)
    return task


@router.get("", response_model=list[Task])
async def list_tasks(status: TaskStatus | None = None, active_only: bool = False) -> list[Task]:
    """
    Получить список всех задач.

    **Параметры запроса:**
    - `status`: Фильтр по статусу (pending, running, reviewing, completed, failed, cancelled)
    - `active_only`: Вернуть только активные (pending/running/reviewing) задачи
    """
    manager = await get_task_manager()

    if active_only:
        tasks = []
        for s in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.REVIEWING]:
            tasks.extend(await manager.get_all(status=s))
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    return await manager.get_all(status=status)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str) -> Task:
    """Получить детали задачи по ID."""
    manager = await get_task_manager()
    task = await manager.get(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Задача {task_id} не найдена"
        )

    return task


@router.get("/{task_id}/diff", response_model=dict[str, str])
async def get_task_diff(task_id: str) -> dict[str, str]:
    """
    Получить изменения файлов задачи.

    Возвращает словарь, сопоставляющий пути файлов с их diff.
    """
    manager = await get_task_manager()
    task = await manager.get(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Задача {task_id} не найдена"
        )

    return task.files_changed


@router.get("/{task_id}/logs", response_model=list[str])
async def get_task_logs(task_id: str, limit: int = 100) -> list[str]:
    """
    Получить логи задачи.

    **Параметры запроса:**
    - `limit`: Максимальное количество записей лога (по умолчанию: 100)
    """
    manager = await get_task_manager()
    task = await manager.get(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Задача {task_id} не найдена"
        )

    return task.logs[-limit:]


@router.delete("/{task_id}", response_model=Task)
async def cancel_task(task_id: str) -> Task:
    """
    Отменить или остановить выполняющуюся задачу.

    Помечает задачу как отменённую и останавливает любую выполняющуюся обработку.
    """
    manager = await get_task_manager()
    task = await manager.cancel(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Задача {task_id} не найдена"
        )

    return task


@router.post("/{task_id}/retry", response_model=Task)
async def retry_task(task_id: str) -> Task:
    """
    Повторить неудавшуюся или отменённую задачу.

    Создаёт новую задачу с теми же параметрами.
    """
    manager = await get_task_manager()
    original = await manager.get(task_id)

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Задача {task_id} не найдена"
        )

    # Создание новой задачи с теми же параметрами
    request = TaskCreateRequest(
        type=original.type,
        issue_number=original.issue_number,
        pr_number=original.pr_number,
        branch_name=original.branch_name,
        max_iterations=original.max_iterations,
        repo_url=None,
    )

    new_task = await manager.create(request)
    new_task.add_log(f"Повторная попытка из задачи {task_id}")

    return new_task


@router.get("/stats/summary")
async def get_task_stats() -> dict[str, Any]:
    """
    Получить сводку статистики задач.

    Возвращает количество задач по статусам и другие метрики.
    """
    manager = await get_task_manager()
    all_tasks = await manager.get_all()

    stats = {
        "total": len(all_tasks),
        "by_status": {},
        "active": 0,
        "completed": 0,
        "failed": 0,
        "avg_duration_seconds": 0.0,
    }

    durations = []
    for task in all_tasks:
        # Подсчёт по статусам
        status_key = task.status.value
        stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1

        # Подсчёт по категориям
        if task.is_active:
            stats["active"] += 1
        if task.status == TaskStatus.COMPLETED:
            stats["completed"] += 1
        if task.status == TaskStatus.FAILED:
            stats["failed"] += 1

        # Сбор продолжительностей
        if task.duration_seconds:
            durations.append(task.duration_seconds)

    if durations:
        stats["avg_duration_seconds"] = sum(durations) / len(durations)

    return stats
