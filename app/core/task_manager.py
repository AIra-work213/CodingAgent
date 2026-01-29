"""Менеджер задач с хранилищем Redis"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.models.task import Task, TaskCreateRequest, TaskStatus

settings = get_settings()


class TaskManager:
    """Менеджер для хранения и получения задач с использованием Redis"""

    def __init__(self, redis_url: str | None = None):
        """Инициализация менеджера задач"""
        self._redis: redis.Redis | None = None
        self._redis_url = redis_url or settings.redis_url
        self._lock = asyncio.Lock()
        self._task_prefix = "task:"
        self._list_key = "tasks:all"

    async def _get_redis(self) -> redis.Redis:
        """Получить или создать подключение к Redis"""
        if self._redis is None:
            self._redis = await redis.from_url(
                self._redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    async def close(self) -> None:
        """Закрыть подключение к Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _task_key(self, task_id: str) -> str:
        """Получить ключ Redis для задачи"""
        return f"{self._task_prefix}{task_id}"

    async def create(self, request: TaskCreateRequest) -> Task:
        """Создать новую задачу"""
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            type=request.type,
            issue_number=request.issue_number,
            pr_number=request.pr_number,
            branch_name=request.branch_name
            or (f"agent/issue-{request.issue_number}" if request.issue_number else None),
            max_iterations=request.max_iterations,
            status=TaskStatus.PENDING,
        )

        await self.save(task)
        await self._add_to_list(task_id)

        return task

    async def save(self, task: Task) -> None:
        """Сохранить задачу в Redis"""
        r = await self._get_redis()
        key = self._task_key(task.id)
        await r.set(key, task.model_dump_json(), ex=86400)  # TTL 24 часа

    async def get(self, task_id: str) -> Task | None:
        """Получить задачу по ID"""
        r = await self._get_redis()
        key = self._task_key(task_id)
        data = await r.get(key)

        if not data:
            return None

        return Task.model_validate_json(data)

    async def get_all(self, status: TaskStatus | None = None) -> list[Task]:
        """Получить все задачи, опционально отфильтрованные по статусу"""
        r = await self._get_redis()
        task_ids = await r.smembers(self._list_key)

        tasks = []
        for task_id in task_ids:
            task = await self.get(task_id)
            if task and (status is None or task.status == status):
                tasks.append(task)

        # Сортировка по created_at по убыванию
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    async def get_active_tasks(self) -> list[Task]:
        """Получить все активные (выполняющиеся/ожидающие) задачи"""
        return await self.get_all(status=TaskStatus.RUNNING)

    async def update(
        self,
        task_id: str,
        progress: float | None = None,
        step: str | None = None,
        log: str | None = None,
        status: TaskStatus | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Task | None:
        """Обновить поля задачи"""
        task = await self.get(task_id)
        if not task:
            return None

        if progress is not None:
            task.progress = max(0.0, min(1.0, progress))
        if step:
            task.current_step = step
        if log:
            task.add_log(log)
        if status:
            task.status = status
            if status == TaskStatus.RUNNING and not task.started_at:
                task.started_at = datetime.utcnow()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.utcnow()
                task.progress = 1.0 if status == TaskStatus.COMPLETED else task.progress
        if result:
            task.result = result
        if error:
            task.error = error

        task.updated_at = datetime.utcnow()
        await self.save(task)

        return task

    async def delete(self, task_id: str) -> bool:
        """Удалить задачу"""
        r = await self._get_redis()
        key = self._task_key(task_id)
        result = await r.delete(key)
        await r.srem(self._list_key, task_id)
        return result > 0

    async def cancel(self, task_id: str) -> Task | None:
        """Отменить выполняющуюся задачу"""
        task = await self.get(task_id)
        if not task:
            return None

        if not task.is_active:
            return task

        task.mark_cancelled()
        await self.save(task)
        return task

    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Удалить старые завершённые задачи"""
        r = await self._get_redis()
        task_ids = await r.smembers(self._list_key)

        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        removed = 0

        for task_id in task_ids:
            task = await self.get(task_id)
            if task and task.completed_at and task.completed_at.timestamp() < cutoff:
                await self.delete(task_id)
                removed += 1

        return removed

    async def _add_to_list(self, task_id: str) -> None:
        """Добавить ID задачи в список всех задач"""
        r = await self._get_redis()
        await r.sadd(self._list_key, task_id)


# Глобальный экземпляр менеджера задач
_task_manager: TaskManager | None = None


async def get_task_manager() -> TaskManager:
    """Получить или создать глобальный экземпляр менеджера задач"""
    global _task_manager

    if _task_manager is None:
        _task_manager = TaskManager()

    return _task_manager


async def close_task_manager() -> None:
    """Закрыть глобальный менеджер задач"""
    global _task_manager

    if _task_manager:
        await _task_manager.close()
        _task_manager = None
