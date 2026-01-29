"""Модели данных задач для Coding Agents"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Тип задачи"""

    CODE_AGENT = "code-agent"
    REVIEWER = "reviewer"


class TaskStatus(str, Enum):
    """Статус задачи"""

    PENDING = "pending"
    RUNNING = "running"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskCreateRequest(BaseModel):
    """Запрос на создание новой задачи"""

    type: TaskType = Field(..., description="Тип агента для запуска")
    issue_number: int | None = Field(None, description="Номер GitHub issue (для code-agent)")
    pr_number: int | None = Field(None, description="Номер GitHub PR (для reviewer)")
    branch_name: str | None = Field(None, description="Имя ветки для изменений")
    max_iterations: int = Field(5, ge=1, le=10, description="Максимальное количество итераций")
    repo_url: str | None = Field(
        None, description="URL репозитория (опционально, используется значение из .env)"
    )
    github_token: str | None = Field(
        None, description="GitHub токен клиента (опционально, используется значение из .env)"
    )


class Task(BaseModel):
    """Модель задачи с отслеживанием статуса"""

    id: str = Field(..., description="Уникальный идентификатор задачи")
    type: TaskType = Field(..., description="Тип задачи")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Текущий статус")

    # Входные параметры
    issue_number: int | None = Field(None, description="Связанный номер issue")
    pr_number: int | None = Field(None, description="Связанный номер PR")
    branch_name: str | None = Field(None, description="Имя ветки для изменений")
    max_iterations: int = Field(5, description="Максимальное количество итераций")

    # Отслеживание прогресса
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Прогресс (0-1)")
    current_step: str = Field(default="", description="Описание текущего шага")
    iteration: int = Field(default=1, description="Номер текущей итерации")

    # Хранение данных
    logs: list[str] = Field(default_factory=list, description="Логи задачи")
    files_changed: dict[str, str] = Field(
        default_factory=dict, description="Изменения файлов (путь -> diff)"
    )
    requirements: dict[str, Any] | None = Field(None, description="Извлечённые требования")
    implementation_plan: dict[str, Any] | None = Field(None, description="План реализации")

    # Результаты
    result: dict[str, Any] | None = Field(None, description="Данные результата задачи")
    error: str | None = Field(None, description="Сообщение об ошибке при неудаче")

    # Метки времени
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Время создания")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Время последнего обновления"
    )
    started_at: datetime | None = Field(None, description="Время начала задачи")
    completed_at: datetime | None = Field(None, description="Время завершения задачи")

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "use_enum_values": True,
    }

    def add_log(self, message: str) -> None:
        """Добавить сообщение в лог"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        self.updated_at = datetime.utcnow()

    def update_progress(
        self, progress: float, step: str | None = None, log: str | None = None
    ) -> None:
        """Обновить прогресс задачи"""
        self.progress = max(0.0, min(1.0, progress))
        if step:
            self.current_step = step
        if log:
            self.add_log(log)
        self.updated_at = datetime.utcnow()

    def mark_started(self) -> None:
        """Пометить задачу как начатую"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.add_log("Задача начата")

    def mark_completed(self, result: dict[str, Any] | None = None) -> None:
        """Пометить задачу как завершённую"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.progress = 1.0
        if result:
            self.result = result
        self.add_log("Задача завершена")

    def mark_failed(self, error: str) -> None:
        """Пометить задачу как неудавшуюся"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.error = error
        self.add_log(f"Задача завершилась с ошибкой: {error}")

    def mark_cancelled(self) -> None:
        """Пометить задачу как отменённую"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.add_log("Задача отменена")

    @property
    def duration_seconds(self) -> float | None:
        """Получить продолжительность задачи в секундах"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None

    @property
    def is_active(self) -> bool:
        """Проверить, активна ли задача"""
        return self.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.REVIEWING]
