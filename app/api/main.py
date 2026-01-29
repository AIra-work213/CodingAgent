"""FastAPI приложение для Coding Agents"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api import tasks
from app.api.streaming import router as streaming_router
from app.api.websocket import manager
from app.core.agents.code_agent import run_code_agent
from app.core.agents.reviewer_agent import run_reviewer_agent
from app.core.config import get_settings
from app.core.task_manager import close_task_manager, get_task_manager

settings = get_settings()


# ============================================================================
# Модели запросов/ответов
# ============================================================================


class CodeAgentRequest(BaseModel):
    """Модель запроса для Code Agent"""

    issue_number: int = Field(..., description="Номер GitHub issue для обработки")
    branch_name: str | None = Field(
        None, description="Имя ветки (автоматически генерируется, если не указано)"
    )
    max_iterations: int = Field(5, ge=1, le=10, description="Максимальное количество итераций")


class ReviewerAgentRequest(BaseModel):
    """Модель запроса для Reviewer Agent"""

    pr_number: int = Field(..., description="Номер Pull Request для рецензирования")
    issue_number: int | None = Field(None, description="Связанный номер issue")


class AgentResponse(BaseModel):
    """Модель ответа для выполнения агента"""

    success: bool
    status: str
    data: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Ответ проверки работоспособности"""

    status: str
    version: str
    openrouter_configured: bool
    github_configured: bool
    redis_connected: bool
    active_tasks: int = 0


# ============================================================================
# Жизненный цикл приложения
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Менеджер жизненного цикла приложения"""
    # Запуск
    print("Запуск Coding Agents API...")
    print(f"Режим отладки: {settings.debug}")
    print(f"GitHub репозиторий: {settings.github_repo}")
    print(f"Redis URL: {settings.redis_url}")

    # Инициализация подключения менеджера задач
    try:
        manager = await get_task_manager()
        r = await manager._get_redis()
        await r.ping()
        print("✓ Подключение к Redis установлено")
    except Exception as e:
        print(f"✗ Не удалось подключиться к Redis: {e}")

    yield

    # Завершение работы
    print("Завершение работы Coding Agents API...")
    await close_task_manager()
    print("✓ Менеджер задач закрыт")


app = FastAPI(
    title="Coding Agents SDLC Pipeline",
    description="Автоматизированная система генерации и рецензирования кода на базе LangGraph и OpenRouter",
    version="0.1.0",
    lifespan=lifespan,
)

# Подключение роутеров
app.include_router(tasks.router)
app.include_router(streaming_router)


# ============================================================================
# Эндпоинты работоспособности и информации
# ============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Эндпоинт проверки работоспособности"""
    redis_connected = False
    active_tasks = 0

    try:
        manager = await get_task_manager()
        r = await manager._get_redis()
        await r.ping()
        redis_connected = True
        active_tasks = len(await manager.get_active_tasks())
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        version="0.1.0",
        openrouter_configured=bool(
            settings.openrouter_api_key
            and settings.openrouter_api_key != "your_openrouter_api_key_here"
        ),
        github_configured=bool(
            settings.github_token and settings.github_token != "your_github_token_here"
        ),
        redis_connected=redis_connected,
        active_tasks=active_tasks,
    )


@app.get("/", tags=["Info"])
async def root() -> dict[str, str]:
    """Корневой эндпоинт с информацией об API"""
    return {
        "name": "Coding Agents SDLC Pipeline",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================================
# Эндпоинты Code Agent
# ============================================================================


@app.post("/agents/code-agent/run", response_model=AgentResponse, tags=["Code Agent"])
async def run_code_agent_endpoint(request: CodeAgentRequest) -> AgentResponse:
    """
    Запуск Code Agent для обработки GitHub Issue и создания Pull Request.

    Агент выполнит:
    1. Парсинг issue для извлечения требований
    2. Анализ репозитория и создание плана реализации
    3. Генерацию кода для необходимых изменений
    4. Валидацию сгенерированного кода
    5. Создание ветки и pull request

    Пример:
    ```json
    {
        "issue_number": 123,
        "branch_name": "agent/issue-123",
        "max_iterations": 5
    }
    ```
    """
    try:
        result = await run_code_agent(
            issue_number=request.issue_number,
            branch_name=request.branch_name,
            max_iterations=request.max_iterations,
        )

        return AgentResponse(
            success=result["success"],
            status=result["status"],
            data=result if result["success"] else None,
            error=result.get("error"),
        )

    except Exception as e:
        return AgentResponse(
            success=False,
            status="error",
            error=str(e),
        )


@app.get("/agents/code-agent/status/{task_id}", tags=["Code Agent"])
async def get_code_agent_status(task_id: str) -> dict[str, str]:
    """
    Получить статус выполняющейся задачи Code Agent.

    Args:
        task_id: ID задачи для проверки

    Returns:
        Словарь с информацией о статусе задачи
    """
    # Пока возвращаем заглушку
    # В production будет запрос к хранилищу задач
    return {
        "task_id": task_id,
        "status": "unknown",
        "message": "Отслеживание статуса задачи еще не реализовано",
    }


# ============================================================================
# Эндпоинты Reviewer Agent
# ============================================================================


@app.post("/agents/reviewer/analyze-pr", response_model=AgentResponse, tags=["Reviewer Agent"])
async def run_reviewer_agent_endpoint(request: ReviewerAgentRequest) -> AgentResponse:
    """
    Запуск Reviewer Agent для анализа Pull Request.

    Агент выполнит:
    1. Анализ diff PR и результатов CI/CD
    2. Сравнение реализации с требованиями
    3. Генерацию комментариев рецензии кода
    4. Одобрение или запрос изменений

    Пример:
    ```json
    {
        "pr_number": 456,
        "issue_number": 123
    }
    ```
    """
    try:
        result = await run_reviewer_agent(
            pr_number=request.pr_number,
            issue_number=request.issue_number,
        )

        return AgentResponse(
            success=result["success"],
            status=result["status"],
            data=result if result["success"] else None,
            error=result.get("error"),
        )

    except Exception as e:
        return AgentResponse(
            success=False,
            status="error",
            error=str(e),
        )


# ============================================================================
# Эндпоинты вебхуков
# ============================================================================


@app.post("/webhooks/github", tags=["Webhooks"])
async def github_webhook(payload: dict) -> dict[str, str]:
    """
    Обработка событий вебхука GitHub.

    Поддерживаемые события:
    - issues: Вызывается при создании/обновлении issue
    - pull_request: Вызывается при открытии/обновлении PR

    Вебхук запускает соответствующий агент в зависимости от типа события.
    """
    event_type = payload.get("action", "unknown")

    # Проверка issue с меткой "agent-task"
    if "issue" in payload and "label" in payload.get("issue", {}):
        labels = [l["name"] for l in payload["issue"].get("labels", [])]
        if "agent-task" in labels:
            # Запуск code agent (async в production)
            issue_number = payload["issue"]["number"]
            return {"status": "triggered", "agent": "code-agent", "issue": issue_number}

    # Проверка событий PR
    if "pull_request" in payload:
        pr_number = payload["pull_request"]["number"]
        return {"status": "triggered", "agent": "reviewer-agent", "pr": pr_number}

    return {"status": "received", "event": event_type}


# ============================================================================
# Эндпоинты WebSocket
# ============================================================================


@app.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket эндпоинт для обновлений задач в реальном времени.

    Подключение для получения обновлений конкретной задачи:
    - Обновления прогресса
    - Изменения статуса
    - Новые записи логов
    - События завершения/ошибок

    Типы сообщений:
    - `init`: Начальное состояние задачи
    - `progress`: Обновление прогресса с `progress` (0-1), `step` и `log`
    - `status`: Изменение статуса с `status`
    - `log`: Новая запись лога с `log`
    - `error`: Событие ошибки с `error`
    """
    await manager.connect(task_id, websocket)
    try:
        while True:
            # Поддержание соединения и обработка сообщений клиента
            data = await websocket.receive_text()
            # Эхо-ответ или обработка сообщений клиента при необходимости
    except WebSocketDisconnect:
        await manager.disconnect(task_id, websocket)
    except Exception:
        await manager.disconnect(task_id, websocket)


# ============================================================================
# Обработчики ошибок
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Обработка HTTP исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Обработка общих исключений"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(exc)},
    )


# ============================================================================
# Точка входа
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
