"""Unit tests for configuration module"""

import pytest

from app.core.config import Settings


@pytest.mark.unit
def test_settings_with_env_vars(mock_settings_env):
    """Test Settings with valid data from environment"""
    settings = Settings()
    assert settings.openrouter_api_key == "test_key_for_testing"
    assert settings.github_token == "test_token_for_testing"
    assert settings.github_repo == "test/test"
    assert settings.max_iterations == 3


@pytest.mark.unit
def test_github_repo_parsing(mock_settings_env):
    """Test GitHub repo parsing"""
    settings = Settings()
    assert settings.owner == "test"
    assert settings.repo_name == "test"
