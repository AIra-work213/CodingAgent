"""Модуль мониторинга репозиториев для автоматического обнаружения новых issues"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Awaitable, Callable

import httpx
from redis import asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()


@dataclass
class MonitoredRepo:
    """Конфигурация отслеживаемого репозитория"""

    owner: str
    repo: str
    github_token: str
    poll_interval: int = 60  # seconds
    last_checked: datetime = field(default_factory=datetime.now)
    enabled: bool = True
    processed_issues: set[int] = field(default_factory=set)

    @property
    def repo_key(self) -> str:
        """Уникальный ключ для репозитория"""
        return f"{self.owner}/{self.repo}"

    @property
    def redis_key(self) -> str:
        """Ключ для хранения в Redis"""
        return f"monitor:repo:{self.repo_key.replace('/', '_')}"

    def to_dict(self) -> dict:
        """Сериализация в dict"""
        return {
            "owner": self.owner,
            "repo": self.repo,
            "github_token": self.github_token,
            "poll_interval": self.poll_interval,
            "last_checked": self.last_checked.isoformat(),
            "enabled": self.enabled,
            "processed_issues": list(self.processed_issues),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MonitoredRepo":
        """Десериализация из dict"""
        data["last_checked"] = datetime.fromisoformat(data["last_checked"])
        data["processed_issues"] = set(data["processed_issues"])
        return cls(**data)


class RepositoryMonitor:
    """Мониторинг репозиториев GitHub для автоматического обнаружения новых issues"""

    def __init__(self):
        self.redis: aioredis.Redis | None = None
        self.monitored_repos: dict[str, MonitoredRepo] = {}
        self.running = False
        self.tasks: list[asyncio.Task] = []
        self.issue_callbacks: list[Callable[[str, int, dict], Awaitable[None]]] = []

    async def init_redis(self):
        """Инициализация Redis подключения"""
        if self.redis is None:
            self.redis = aioredis.from_url(settings.redis_url)
            await self.load_monitored_repos()

    async def load_monitored_repos(self):
        """Загрузка отслеживаемых репозиториев из Redis"""
        if self.redis is None:
            return

        pattern = "monitor:repo:*"
        # Use scan to get keys matching pattern
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    try:
                        repo = MonitoredRepo.from_dict(json.loads(data))
                        if repo.enabled:
                            self.monitored_repos[repo.repo_key] = repo
                    except Exception as e:
                        print(f"[Monitor] Error loading repo {key}: {e}")
            if cursor == 0:
                break

    async def save_repo(self, repo: MonitoredRepo):
        """Сохранение конфигурации репозитория в Redis"""
        if self.redis is None:
            await self.init_redis()

        await self.redis.set(repo.redis_key, json.dumps(repo.to_dict()), ex=86400 * 30)  # 30 days

    async def add_repo(
        self,
        owner: str,
        repo: str,
        github_token: str,
        poll_interval: int = 60,
    ) -> MonitoredRepo:
        """Добавление репозитория на мониторинг"""
        await self.init_redis()

        monitored = MonitoredRepo(
            owner=owner,
            repo=repo,
            github_token=github_token,
            poll_interval=poll_interval,
        )

        self.monitored_repos[monitored.repo_key] = monitored
        await self.save_repo(monitored)

        print(f"[Monitor] Added repository: {monitored.repo_key} (interval: {poll_interval}s)")
        return monitored

    async def remove_repo(self, owner: str, repo: str) -> bool:
        """Удаление репозитория из мониторинга"""
        await self.init_redis()

        repo_key = f"{owner}/{repo}"

        if repo_key in self.monitored_repos:
            del self.monitored_repos[repo_key]

            if self.redis:
                await self.redis.delete(f"monitor:repo:{repo_key.replace('/', '_')}")

            print(f"[Monitor] Removed repository: {repo_key}")
            return True

        return False

    async def get_repo_issues(
        self, repo: MonitoredRepo, state: str = "open", since: datetime | None = None
    ) -> list[dict]:
        """Получение списка issues из репозитория"""
        url = f"{settings.github_base_url}/repos/{repo.repo_key}/issues"

        headers = {
            "Authorization": f"Bearer {repo.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        params: dict[str, str | int] = {
            "state": state,
            "per_page": 100,
            "sort": "created",
            "direction": "desc",
        }

        if since:
            params["since"] = since.isoformat()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"[Monitor] Error fetching issues for {repo.repo_key}: {e}")
            return []

    def register_callback(self, callback: Callable[[str, int, dict], Awaitable[None]]):
        """Регистрация callback для обработки новых issues"""

        self.issue_callbacks.append(callback)

    async def _poll_repo(self, repo: MonitoredRepo):
        """Фоновая задача polling для конкретного репозитория"""
        print(f"[Monitor] Started polling {repo.repo_key} every {repo.poll_interval}s")

        while repo.enabled and self.running:
            try:
                # Get issues since last check
                issues = await self.get_repo_issues(repo, since=repo.last_checked)

                for issue in issues:
                    issue_number = issue.get("number")
                    if not issue_number:
                        continue

                    # Skip pull requests
                    if "pull_request" in issue:
                        continue

                    # Skip already processed
                    if issue_number in repo.processed_issues:
                        continue

                    print(f"[Monitor] New issue found: {repo.repo_key}#{issue_number} - {issue.get('title')}")

                    # Mark as processed
                    repo.processed_issues.add(issue_number)

                    # Call registered callbacks
                    for callback in self.issue_callbacks:
                        try:
                            await callback(repo.repo_key, issue_number, issue)
                        except Exception as e:
                            print(f"[Monitor] Callback error: {e}")

                # Update last checked
                repo.last_checked = datetime.now()
                await self.save_repo(repo)

            except Exception as e:
                print(f"[Monitor] Polling error for {repo.repo_key}: {e}")

            # Wait for next poll
            await asyncio.sleep(repo.poll_interval)

    async def start(self):
        """Запуск мониторинга всех репозиториев"""
        if self.running:
            print("[Monitor] Already running")
            return

        await self.init_redis()
        self.running = True

        # Start polling task for each repo
        for repo in self.monitored_repos.values():
            if repo.enabled:
                task = asyncio.create_task(self._poll_repo(repo))
                self.tasks.append(task)

        print(f"[Monitor] Started monitoring {len(self.tasks)} repositories")

    async def stop(self):
        """Остановка мониторинга"""
        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks.clear()
        print("[Monitor] Stopped monitoring")

    def get_status(self) -> dict:
        """Получение статуса мониторинга"""
        return {
            "running": self.running,
            "repos_count": len(self.monitored_repos),
            "repos": [
                {
                    "repo": repo.repo_key,
                    "enabled": repo.enabled,
                    "poll_interval": repo.poll_interval,
                    "last_checked": repo.last_checked.isoformat(),
                    "processed_issues": len(repo.processed_issues),
                }
                for repo in self.monitored_repos.values()
            ],
        }

    async def list_repos(self) -> list[dict]:
        """Список всех отслеживаемых репозиториев"""
        await self.init_redis()
        return [
            {
                "repo": repo.repo_key,
                "enabled": repo.enabled,
                "poll_interval": repo.poll_interval,
                "last_checked": repo.last_checked.isoformat(),
                "processed_issues_count": len(repo.processed_issues),
            }
            for repo in self.monitored_repos.values()
        ]


# Global singleton
_monitor_instance: RepositoryMonitor | None = None


def get_monitor() -> RepositoryMonitor:
    """Получение singleton экземпляра монитора"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = RepositoryMonitor()
    return _monitor_instance
