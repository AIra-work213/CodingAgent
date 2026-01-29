"""Rich CLI Dashboard для мониторинга задач в реальном времени"""

import asyncio
import json

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from app.cli.utils import (
    format_duration,
    format_status,
    format_timestamp,
    get_task,
)


class TaskDashboard:
    """Live dashboard для мониторинга задач"""

    def __init__(self, server_url: str, task_id: str, refresh_rate: float = 1.0):
        """Инициализация dashboard"""
        self.server_url = server_url
        self.task_id = task_id
        self.refresh_rate = refresh_rate
        self.console = Console()
        self.task = None
        self.ws_url = self._get_ws_url()
        self.running = True

    def _get_ws_url(self) -> str:
        """Преобразовать HTTP URL в WebSocket URL"""
        if self.server_url.startswith("https://"):
            return self.server_url.replace("https://", "wss://")
        return self.server_url.replace("http://", "ws://")

    async def run(self):
        """Запуск live dashboard"""
        # Сначала пробуем WebSocket, при ошибке переходим на опрос
        try:
            await self._run_websocket()
        except Exception:
            # Резервный вариант - опрос
            await self._run_polling()

    async def _run_websocket(self):
        """Запуск dashboard с обновлениями WebSocket"""
        import websockets

        async with websockets.connect(f"{self.ws_url}/ws/tasks/{self.task_id}") as websocket:
            with Live(
                self._generate_layout(),
                console=self.console,
                refresh_per_second=2,
            ) as live:
                while self.running:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), timeout=self.refresh_rate
                        )
                        data = json.loads(message)
                        self._handle_update(data)
                        live.update(self._generate_layout())
                    except asyncio.TimeoutError:
                        # Тайм-аут, обновить состояние задачи
                        await self._refresh_task()
                        live.update(self._generate_layout())

    async def _run_polling(self):
        """Запуск dashboard с резервным опросом"""
        with Live(
            self._generate_layout(),
            console=self.console,
            refresh_per_second=1,
        ) as live:
            while self.running:
                await self._refresh_task()
                live.update(self._generate_layout())

                # Остановить, если задача завершена
                if self.task and not self.task.is_active:
                    self.console.print(
                        f"\n[bold green]Задача {self.task_id} завершена![/bold green]"
                    )
                    break

                await asyncio.sleep(self.refresh_rate)

    async def _refresh_task(self):
        """Обновить состояние задачи из API"""
        self.task = await get_task(self.server_url, self.task_id)

    def _handle_update(self, data: dict):
        """Обработать сообщение обновления WebSocket"""
        msg_type = data.get("type", "")

        if msg_type == "init":
            self.task = data.get("task")
            if isinstance(self.task, dict):
                # Преобразовать в объект Task (упрощённо)
                pass

        elif msg_type == "progress":
            if self.task:
                self.task["progress"] = data.get("progress", self.task.get("progress", 0))
                self.task["current_step"] = data.get("step", "")

        elif msg_type == "status":
            if self.task:
                self.task["status"] = data.get("status")

        elif msg_type == "log":
            if self.task and "logs" in self.task:
                self.task["logs"].append(data.get("log", ""))

        elif msg_type == "complete" or msg_type == "done":
            self.running = False

    def _generate_layout(self) -> Layout:
        """Сгенерировать макет Rich для dashboard"""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # Заголовок
        layout["header"].update(self._generate_header())

        # Основная часть
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )

        layout["left"].split_column(
            Layout(name="progress", size=8),
            Layout(name="logs"),
        )

        layout["right"].update(self._generate_info_panel())

        # Секция прогресса
        layout["progress"].update(self._generate_progress())

        # Секция логов
        layout["logs"].update(self._generate_logs())

        # Футер
        layout["footer"].update(self._generate_footer())

        return layout

    def _generate_header(self) -> Panel:
        """Сгенерировать панель заголовка"""
        if not self.task:
            return Panel(
                f"[bold cyan]Задача {self.task_id[:8]}...[/bold cyan]",
                title="Coding Agents Dashboard",
                border_style="cyan",
            )

        status_text = format_status(self.task.status)
        return Panel(
            f"[bold cyan]Задача {self.task_id[:8]}...[/bold cyan] | {status_text}",
            title="Coding Agents Dashboard",
            border_style="cyan",
        )

    def _generate_progress(self) -> Panel:
        """Сгенерировать панель прогресса"""
        if not self.task:
            return Panel(
                "[dim]Загрузка задачи...[/dim]",
                title="Прогресс",
                border_style="blue",
            )

        progress = self.task.progress if hasattr(self.task, "progress") else 0
        step = self.task.current_step if hasattr(self.task, "current_step") else ""
        status = self.task.status if hasattr(self.task, "status") else "unknown"

        # Индикатор прогресса
        progress_text = f"[cyan]{int(progress * 100)}%[/cyan]"
        bar_length = 40
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Информация о статусе
        status_color = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
        }.get(status, "white")

        info = f"""
[bold]Статус:[/bold] [{status_color}]{status}[/{status_color}]
[bold]Шаг:[/bold] {step or "N/A"}
[bold]Прогресс:[/bold] {progress_text} [cyan]{bar}[/cyan]
        """.strip()

        return Panel(
            info,
            title="Прогресс",
            border_style="blue",
        )

    def _generate_logs(self) -> Panel:
        """Сгенерировать панель логов"""
        if not self.task:
            return Panel(
                "[dim]Загрузка логов...[/dim]",
                title="Логи",
                border_style="yellow",
            )

        logs = self.task.logs if hasattr(self.task, "logs") else []
        # Показать последние 15 логов
        recent_logs = logs[-15:] if logs else ["Логов пока нет"]

        log_text = "\n".join(recent_logs)

        return Panel(
            log_text,
            title=f"Логи (всего {len(logs)})",
            border_style="yellow",
            padding=(0, 1),
        )

    def _generate_info_panel(self) -> Panel:
        """Сгенерировать информационную панель"""
        if not self.task:
            return Panel(
                "[dim]Загрузка...[/dim]",
                title="Информация о задаче",
                border_style="green",
            )

        info = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        info.add_column("Поле", style="cyan")
        info.add_column("Значение")

        info.add_row("ID", self.task_id[:12] + "...")
        info.add_row("Тип", str(self.task.type) if hasattr(self.task, "type") else "unknown")

        if hasattr(self.task, "issue_number") and self.task.issue_number:
            info.add_row("Issue", f"#{self.task.issue_number}")
        if hasattr(self.task, "pr_number") and self.task.pr_number:
            info.add_row("PR", f"#{self.task.pr_number}")

        if hasattr(self.task, "created_at"):
            info.add_row("Создана", format_timestamp(self.task.created_at))

        duration = None
        if hasattr(self.task, "duration_seconds"):
            duration = self.task.duration_seconds
        if duration:
            info.add_row("Длительность", format_duration(duration))

        if hasattr(self.task, "iteration"):
            info.add_row("Итерация", f"{self.task.iteration}/{self.task.max_iterations}")

        # Количество изменённых файлов
        if hasattr(self.task, "files_changed"):
            file_count = len(self.task.files_changed) if self.task.files_changed else 0
            info.add_row("Файлов", str(file_count))

        return Panel(
            info,
            title="Информация о задаче",
            border_style="green",
        )

    def _generate_footer(self) -> Panel:
        """Сгенерировать футер с горячими клавишами"""
        shortcuts = "[dim]Q: Выход | D: Diff | L: Логи | S: Стоп[/dim]"
        return Panel(
            shortcuts,
            border_style="dim",
            padding=(0, 1),
        )

    def stop(self):
        """Остановить dashboard"""
        self.running = False


async def show_task_dashboard(server_url: str, task_id: str):
    """
    Показать live dashboard для задачи.

    Это основная точка входа для функции dashboard.
    """
    dashboard = TaskDashboard(server_url, task_id)
    await dashboard.run()
