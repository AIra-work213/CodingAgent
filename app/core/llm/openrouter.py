"""Интеграция LLM OpenRouter для LangChain"""

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

settings = get_settings()

# Доступные модели OpenRouter
OPENROUTER_MODELS = {
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "qwen-2.5-coder": "qwen/qwen2.5-coder-7b-instruct",
    "deepseek-coder": "deepseek/deepseek-coder-v2",
}


def get_openrouter_llm(
    model: Literal["gpt-4o-mini", "qwen-2.5-coder", "deepseek-coder"] = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    streaming: bool = False,
) -> BaseChatModel:
    """
    Получить экземпляр LLM OpenRouter, настроенный для LangChain.

    Args:
        model: Ключ названия модели из OPENROUTER_MODELS
        temperature: Температура семплинга
        max_tokens: Максимальное количество токенов для генерации
        streaming: Включить потоковый режим

    Returns:
        Настроенный экземпляр ChatOpenAI
    """
    model_name = OPENROUTER_MODELS.get(model, OPENROUTER_MODELS["gpt-4o-mini"])

    return ChatOpenAI(
        model=model_name,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        streaming=streaming,
    )


def get_coding_llm(streaming: bool = False) -> BaseChatModel:
    """Получить LLM, оптимизированный для задач генерации кода"""
    return get_openrouter_llm(
        model="qwen-2.5-coder",
        temperature=0.2,
        max_tokens=8192,
        streaming=streaming,
    )


def get_review_llm(streaming: bool = False) -> BaseChatModel:
    """Получить LLM, оптимизированный для задач рецензирования кода"""
    return get_openrouter_llm(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=4096,
        streaming=streaming,
    )


def get_planning_llm(streaming: bool = False) -> BaseChatModel:
    """Получить LLM, оптимизированный для планирования и анализа"""
    return get_openrouter_llm(
        model="gpt-4o-mini",
        temperature=0.5,
        max_tokens=4096,
        streaming=streaming,
    )
