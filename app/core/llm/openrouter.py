"""Интеграция LLM OpenRouter для LangChain

Использует БЕСПЛАТНЫЕ модели OpenRouter.
"""

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

settings = get_settings()

# ============================================================================
# БЕСПЛАТНЫЕ модели OpenRouter (2026)
# ============================================================================

# Основные бесплатные модели
OPENROUTER_FREE_MODELS = {
    # Google Gemini (часто бесплатен)
    "gemini-flash": "google/gemini-flash-1.5",
    # Qwen отличные бесплатные модели для кода
    "qwen-2.5-coder-7b": "qwen/qwen-2.5-coder-7b-instruct",
    "qwen-2.5-coder-32b": "qwen/qwen-2.5-coder-32b-instruct",
    # GPT-4o-mini (иногда бесплатен через промо)
    "gpt-4o-mini": "openai/gpt-4o-mini",
    # DeepSeek отличные бесплатные модели
    "deepseek-coder": "deepseek/deepseek-coder",
    "deepseek-chat": "deepseek/deepseek-chat",
    # Meta Llama (бесплатные)
    "llama-3-8b": "meta-llama/llama-3-8b-instruct",
    "llama-3-70b": "meta-llama/llama-3-70b-instruct",
    # Mistral (часто бесплатны)
    "mistral-7b": "mistralai/mistral-7b-instruct",
    "mistral-tiny": "mistralai/mistral-tiny",
}

# Рекомендуемые конфигурации для разных задач
DEFAULT_MODELS = {
    "coding": "qwen-2.5-coder-32b",  # Лучшая бесплатная модель для кода
    "review": "qwen-2.5-coder-32b",  # Используем ту же модель для review
    "planning": "qwen-2.5-coder-32b",  # Хорошая для планирования
}


def get_openrouter_llm(
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    streaming: bool = False,
) -> BaseChatModel:
    """
    Получить экземпляр LLM OpenRouter, настроенный для LangChain.

    Использует бесплатные модели OpenRouter по умолчанию.

    Args:
        model: Ключ названия модели из OPENROUTER_FREE_MODELS (если None, использует gpt-4o-mini)
        temperature: Температура семплинга
        max_tokens: Максимальное количество токенов для генерации
        streaming: Включить потоковый режим

    Returns:
        Настроенный экземпляр ChatOpenAI
    """
    if model is None:
        model = "gpt-4o-mini"

    model_name = OPENROUTER_FREE_MODELS.get(model, model)

    # Если модель не найдена в словаре, используем как есть
    if model_name not in OPENROUTER_FREE_MODELS.values():
        if "/" not in model_name:
            # Попробуем найти по значению
            for key, value in OPENROUTER_FREE_MODELS.items():
                if value.endswith(model_name):
                    model_name = value
                    break
            else:
                # Fallback на qwen coder (надежная бесплатная модель)
                model_name = OPENROUTER_FREE_MODELS["qwen-2.5-coder-32b"]

    print(f"[LLM] Using model: {model_name}")

    return ChatOpenAI(
        model=model_name,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


def get_coding_llm(streaming: bool = False) -> BaseChatModel:
    """Получить LLM, оптимизированный для задач генерации кода.

    Использует qwen-2.5-coder-32b - лучшую бесплатную модель для кода.
    """
    return get_openrouter_llm(
        model=DEFAULT_MODELS["coding"],
        temperature=0.2,
        max_tokens=8192,
        streaming=streaming,
    )


def get_review_llm(streaming: bool = False) -> BaseChatModel:
    """Получить LLM, оптимизированный для задач рецензирования кода.

    Использует gemini-flash для быстрого анализа.
    """
    return get_openrouter_llm(
        model=DEFAULT_MODELS["review"],
        temperature=0.3,
        max_tokens=4096,
        streaming=streaming,
    )


def get_planning_llm(streaming: bool = False) -> BaseChatModel:
    """Получить LLM, оптимизированный для планирования и анализа.

    Использует qwen-2.5-coder-32b для лучшего понимания контекста.
    """
    return get_openrouter_llm(
        model=DEFAULT_MODELS["planning"],
        temperature=0.5,
        max_tokens=4096,
        streaming=streaming,
    )


def list_free_models() -> list[dict]:
    """Получить список доступных бесплатных моделей."""
    return [
        {"key": key, "model_id": model, "recommended_for": get_recommendation(key)}
        for key, model in OPENROUTER_FREE_MODELS.items()
    ]


def get_recommendation(model_key: str) -> str:
    """Получить рекомендацию по использованию модели."""
    recommendations = {
        "gemini-flash": "review, planning (быстрая)",
        "qwen-2.5-coder-7b": "coding (быстрая)",
        "qwen-2.5-coder-32b": "coding, planning (качественная)",
        "gpt-4o-mini": "общие задачи",
        "deepseek-coder": "coding (хорошая)",
        "deepseek-chat": "chat, анализ",
        "llama-3-8b": "общие задачи (быстрая)",
        "llama-3-70b": "качественные задачи",
        "mistral-7b": "общие задачи",
        "mistral-tiny": "быстрые задачи",
    }
    return recommendations.get(model_key, "общие задачи")
