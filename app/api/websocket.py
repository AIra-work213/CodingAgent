"""Менеджер WebSocket-подключений для обновлений задач в реальном времени"""

import asyncio
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.core.task_manager import get_task_manager


class ConnectionManager:
    """Менеджер WebSocket-подключений"""

    def __init__(self):
        """Инициализация менеджера подключений"""
        # task_id -> список WebSocket-подключений
        self.active_connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        """Подключить WebSocket к задаче"""
        await websocket.accept()

        async with self._lock:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = []
            self.active_connections[task_id].append(websocket)

        # Отправить начальное состояние задачи
        try:
            manager = await get_task_manager()
            task = await manager.get(task_id)
            if task:
                await self.send_personal_message(
                    task_id, {"type": "init", "task": task.model_dump()}
                )
        except Exception as e:
            await self.send_personal_message(
                task_id, {"type": "error", "message": f"Не удалось загрузить задачу: {e}"}
            )

    async def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        """Отключить WebSocket от задачи"""
        async with self._lock:
            if task_id in self.active_connections:
                self.active_connections[task_id].remove(websocket)
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]

    async def send_personal_message(self, task_id: str, message: dict[str, Any]) -> None:
        """Отправить сообщение всем подключениям для задачи"""
        async with self._lock:
            connections = self.active_connections.get(task_id, []).copy()

        # Отправка вне блокировки для избежания блокировок
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Подключение может быть закрыто, удаляем его
                await self.disconnect(task_id, connection)

    async def broadcast_task_update(
        self,
        task_id: str,
        update_type: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Транслировать обновление задачи всем подключённым клиентам"""
        message = {"type": update_type, "task_id": task_id}
        if data:
            message.update(data)

        await self.send_personal_message(task_id, message)

    async def broadcast_progress(
        self,
        task_id: str,
        progress: float,
        step: str,
        log: str | None = None,
    ) -> None:
        """Транслировать обновление прогресса"""
        await self.broadcast_task_update(
            task_id,
            "progress",
            {"progress": progress, "step": step, "log": log},
        )

    async def broadcast_status(
        self,
        task_id: str,
        status: str,
    ) -> None:
        """Транслировать изменение статуса"""
        await self.broadcast_task_update(
            task_id,
            "status",
            {"status": status},
        )

    async def broadcast_log(
        self,
        task_id: str,
        log: str,
    ) -> None:
        """Транслировать новую запись лога"""
        await self.broadcast_task_update(
            task_id,
            "log",
            {"log": log},
        )

    async def broadcast_error(
        self,
        task_id: str,
        error: str,
    ) -> None:
        """Транслировать ошибку"""
        await self.broadcast_task_update(
            task_id,
            "error",
            {"error": error},
        )

    def get_connection_count(self, task_id: str) -> int:
        """Получить количество активных подключений для задачи"""
        return len(self.active_connections.get(task_id, []))

    def get_all_connection_counts(self) -> dict[str, int]:
        """Получить количество подключений для всех задач"""
        return {
            task_id: len(connections) for task_id, connections in self.active_connections.items()
        }


# Глобальный экземпляр менеджера подключений
manager = ConnectionManager()


async def notify_task_update(
    task_id: str,
    progress: float | None = None,
    step: str | None = None,
    log: str | None = None,
    status: str | None = None,
) -> None:
    """
    Уведомить подключённых клиентов об обновлениях задачи.
    Это основная функция для вызова из кода агента.
    """
    if progress is not None or step:
        # Получить текущее состояние задачи для прогресса
        mgr = await get_task_manager()
        task = await mgr.get(task_id)
        if task:
            progress = progress if progress is not None else task.progress
            step = step or task.current_step
            await manager.broadcast_progress(task_id, progress, step, log)

    if status:
        await manager.broadcast_status(task_id, status)
    elif log:
        await manager.broadcast_log(task_id, log)
