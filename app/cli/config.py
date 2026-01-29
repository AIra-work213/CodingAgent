"""Управление файлом конфигурации CLI"""

import json
import os
from pathlib import Path
from typing import Any


class ConfigManager:
    """Менеджер файла конфигурации CLI"""

    def __init__(self, config_path: str | None = None):
        """Инициализация менеджера конфигурации"""
        if config_path:
            self.config_dir = Path(os.path.expanduser(config_path))
        else:
            self.config_dir = Path(os.path.expanduser("~/.coding-agent"))

        self.config_file = self.config_dir / "config.json"
        self._config: dict[str, Any] = {}

    def ensure_config_dir(self) -> None:
        """Убедиться, что каталог конфигурации существует"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        """Загрузить конфигурацию из файла"""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self._config = json.load(f)
        else:
            self._config = self._get_default_config()

        return self._config

    def save(self) -> None:
        """Сохранить конфигурацию в файл"""
        self.ensure_config_dir()
        with open(self.config_file, "w") as f:
            json.dump(self._config, f, indent=2)

    def _get_default_config(self) -> dict[str, Any]:
        """Получить конфигурацию по умолчанию"""
        return {
            "version": "1.0",
            "default_server": "local",
            "servers": {
                "local": {
                    "url": "http://localhost:8000",
                    "description": "Локальный сервер разработки",
                }
            },
            "tokens": {},
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение конфигурации"""
        if not self._config:
            self.load()
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Установить значение конфигурации"""
        if not self._config:
            self.load()
        self._config[key] = value
        self.save()

    def add_server(self, name: str, url: str, description: str = "") -> None:
        """Добавить сервер в конфигурацию"""
        if not self._config:
            self.load()

        if "servers" not in self._config:
            self._config["servers"] = {}

        self._config["servers"][name] = {
            "url": url,
            "description": description,
        }
        self.save()

    def remove_server(self, name: str) -> bool:
        """Удалить сервер из конфигурации"""
        if not self._config:
            self.load()

        if "servers" in self._config and name in self._config["servers"]:
            del self._config["servers"][name]

            # Обновить default_server при необходимости
            if self._config.get("default_server") == name:
                self._config["default_server"] = "local"

            self.save()
            return True

        return False

    def set_default_server(self, name: str) -> bool:
        """Установить сервер по умолчанию"""
        if not self._config:
            self.load()

        if "servers" in self._config and name in self._config["servers"]:
            self._config["default_server"] = name
            self.save()
            return True

        return False

    def get_server_url(self, name: str) -> str | None:
        """Получить URL сервера по имени"""
        if not self._config:
            self.load()

        servers = self._config.get("servers", {})
        if name in servers:
            return servers[name]["url"]

        return None

    def list_servers(self) -> dict[str, dict[str, str]]:
        """Получить список всех серверов"""
        if not self._config:
            self.load()

        return self._config.get("servers", {})

    def add_token(self, server_url: str, token: str) -> None:
        """Сохранить GitHub токен для сервера"""
        if not self._config:
            self.load()

        if "tokens" not in self._config:
            self._config["tokens"] = {}

        self._config["tokens"][server_url] = token
        self.save()

    def get_token(self, server_url: str) -> str | None:
        """Получить GitHub токен для сервера"""
        if not self._config:
            self.load()

        tokens = self._config.get("tokens", {})
        return tokens.get(server_url)

    def remove_token(self, server_url: str) -> bool:
        """Удалить GitHub токен для сервера"""
        if not self._config:
            self.load()

        if "tokens" in self._config and server_url in self._config["tokens"]:
            del self._config["tokens"][server_url]
            self.save()
            return True

        return False


# Глобальный экземпляр конфигурации
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Получить или создать глобальный экземпляр менеджера конфигурации"""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

    return _config_manager
