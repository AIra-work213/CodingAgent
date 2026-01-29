"""Unit tests for LLM integration"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.llm.openrouter import (
    get_openrouter_llm,
    get_coding_llm,
    get_review_llm,
    get_planning_llm,
    OPENROUTER_MODELS,
)


@pytest.mark.unit
def test_openrouter_models():
    """Test OpenRouter models configuration"""
    assert "gpt-4o-mini" in OPENROUTER_MODELS
    assert "qwen-2.5-coder" in OPENROUTER_MODELS
    assert "deepseek-coder" in OPENROUTER_MODELS


@pytest.mark.unit
@patch("app.core.llm.openrouter.ChatOpenAI")
def test_get_openrouter_llm(mock_chat_openai):
    """Test getting OpenRouter LLM"""
    mock_instance = MagicMock()
    mock_chat_openai.return_value = mock_instance

    result = get_openrouter_llm(
        model="gpt-4o-mini",
        temperature=0.5,
        max_tokens=2048,
    )

    mock_chat_openai.assert_called_once()
    assert result == mock_instance


@pytest.mark.unit
@patch("app.core.llm.openrouter.get_openrouter_llm")
def test_get_coding_llm(mock_get_llm):
    """Test getting coding LLM"""
    mock_instance = MagicMock()
    mock_get_llm.return_value = mock_instance

    result = get_coding_llm()

    mock_get_llm.assert_called_with(
        model="qwen-2.5-coder",
        temperature=0.2,
        max_tokens=8192,
        streaming=False,
    )
    assert result == mock_instance


@pytest.mark.unit
@patch("app.core.llm.openrouter.get_openrouter_llm")
def test_get_review_llm(mock_get_llm):
    """Test getting review LLM"""
    mock_instance = MagicMock()
    mock_get_llm.return_value = mock_instance

    result = get_review_llm()

    mock_get_llm.assert_called_with(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=4096,
        streaming=False,
    )
    assert result == mock_instance


@pytest.mark.unit
@patch("app.core.llm.openrouter.get_openrouter_llm")
def test_get_planning_llm(mock_get_llm):
    """Test getting planning LLM"""
    mock_instance = MagicMock()
    mock_get_llm.return_value = mock_instance

    result = get_planning_llm()

    mock_get_llm.assert_called_with(
        model="gpt-4o-mini",
        temperature=0.5,
        max_tokens=4096,
        streaming=False,
    )
    assert result == mock_instance
