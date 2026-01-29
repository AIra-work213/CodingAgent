"""Эндпоинты SSE (Server-Sent Events) для потоковой передачи логов"""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.core.models.task import TaskStatus
from app.core.task_manager import get_task_manager

router = APIRouter(prefix="/tasks", tags=["Streaming"])


@router.get("/{task_id}/logs/stream")
async def stream_logs(task_id: str):
    """
    Потоковая передача логов задачи через Server-Sent Events.

    Возвращает непрерывный поток записей логов по мере их добавления в задачу.
    Подключение остаётся открытым до завершения или неудачи задачи.

    Типы событий:
    - `log`: Новая запись лога с полем `message`
    - `status`: Изменение статуса с полем `status`
    - `done`: Завершение задачи/финальный статус
    - `error`: Событие ошибки с полем `error`
    """
    manager = await get_task_manager()

    async def event_generator():
        """Генератор SSE-событий"""
        task = await manager.get(task_id)

        if not task:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Задача {task_id} не найдена"}),
            }
            return

        # Отправка текущих логов сначала
        for log in task.logs:
            yield {
                "event": "log",
                "data": json.dumps({"message": log, "timestamp": datetime.utcnow().isoformat()}),
            }

        # Отслеживание индекса последнего лога для отправки только новых логов
        last_log_count = len(task.logs)

        while task.is_active:
            await asyncio.sleep(0.5)  # Опрос каждые 500 мс

            # Обновление состояния задачи
            task = await manager.get(task_id)
            if not task:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": f"Задача {task_id} исчезла"}),
                }
                break

            # Отправка новых логов
            if len(task.logs) > last_log_count:
                for log in task.logs[last_log_count:]:
                    yield {
                        "event": "log",
                        "data": json.dumps(
                            {"message": log, "timestamp": datetime.utcnow().isoformat()}
                        ),
                    }
                last_log_count = len(task.logs)

            # Отправка обновлений статуса
            yield {
                "event": "status",
                "data": json.dumps(
                    {
                        "status": task.status.value,
                        "progress": task.progress,
                        "step": task.current_step,
                    }
                ),
            }

        # Финальный статус
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "status": task.status.value,
                    "progress": task.progress,
                    "result": task.result,
                    "error": task.error,
                }
            ),
        }

    return EventSourceResponse(event_generator())


@router.get("/{task_id}/stream")
async def stream_task_updates(task_id: str):
    """
    Потоковая передача всех обновлений задачи через Server-Sent Events.

    Аналогично /logs/stream, но включает все обновления состояния задачи:
    - Изменения прогресса
    - Изменения статуса
    - Новые логи
    - Результат/ошибка при завершении
    """
    manager = await get_task_manager()

    async def event_generator():
        """Генератор SSE-событий"""
        task = await manager.get(task_id)

        if not task:
            yield {
                "event": "error",
                "data": json.dumps({"error": f"Задача {task_id} не найдена"}),
            }
            return

        # Отправка начального состояния
        yield {
            "event": "init",
            "data": json.dumps(task.model_dump()),
        }

        last_updated = task.updated_at

        while task.is_active:
            await asyncio.sleep(0.5)

            # Обновление состояния задачи
            task = await manager.get(task_id)
            if not task:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": f"Задача {task_id} исчезла"}),
                }
                break

            # Отправка обновления, если задача изменилась
            if task.updated_at > last_updated:
                yield {
                    "event": "update",
                    "data": json.dumps(task.model_dump()),
                }
                last_updated = task.updated_at

        # Финальное состояние
        yield {
            "event": "complete",
            "data": json.dumps(task.model_dump()),
        }

    return EventSourceResponse(event_generator())
