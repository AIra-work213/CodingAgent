"""CLI interface for Coding Agents"""

import asyncio
import json
import os
from pathlib import Path

import click
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from app.cli.config import get_config_manager
from app.cli.utils import (
    cancel_task,
    check_server_health,
    create_task,
    format_duration,
    format_status,
    format_timestamp,
    get_task,
    get_task_diff,
    get_task_logs,
    list_tasks,
)
from app.core.agents.code_agent import run_code_agent
from app.core.agents.reviewer_agent import run_reviewer_agent
from app.core.config import get_settings
from app.core.tools.github_tools import (
    analyze_pr_diff,
    get_ci_results,
    get_issue_context,
)

settings = get_settings()
console = Console()


def discover_server() -> str:
    """Auto-discover server URL"""
    # 1. Check environment variable
    if settings.client_server_url:
        return settings.client_server_url

    # 2. Check config file
    config_path = Path(os.path.expanduser(settings.config_path)) / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
            default_server = config.get("default_server")
            if default_server and default_server in config.get("servers", {}):
                return config["servers"][default_server]["url"]

    # 3. Check localhost
    try:
        health = asyncio.run(check_server_health("http://localhost:8000"))
        if health and health.get("status") == "healthy":
            return "http://localhost:8000"
    except Exception:
        pass

    # 4. Return default
    return "http://localhost:8000"


@click.group()
@click.version_option(version="0.1.0")
@click.option(
    "--server",
    "-s",
    help="Server URL (auto-discover if not set)",
)
@click.pass_context
def cli(ctx: click.Context, server: str | None) -> None:
    """Coding Agents SDLC Pipeline - CLI

    Automated code generation and review system powered by LangGraph and OpenRouter.
    """
    ctx.ensure_object(dict)
    ctx.obj["server"] = server or discover_server()


# ============================================================================
# Run Command - Main entry point
# ============================================================================


@cli.command()
@click.option(
    "--server",
    "-s",
    help="Server URL (overrides discovery)",
)
@click.option(
    "--repo",
    "-r",
    required=True,
    help="Repository URL (owner/repo or full URL)",
)
@click.option(
    "--issue",
    "-i",
    "issue_number",
    type=int,
    required=True,
    help="GitHub issue number",
)
@click.option(
    "--token",
    "-t",
    help="GitHub token (uses GITHUB_TOKEN env if not set)",
)
@click.option(
    "--branch",
    "-b",
    help="Branch name for changes",
)
@click.option(
    "--max-iterations",
    "-m",
    default=5,
    help="Maximum iterations",
)
@click.pass_context
def run(
    ctx: click.Context,
    server: str | None,
    repo: str,
    issue_number: int,
    token: str | None,
    branch: str | None,
    max_iterations: int,
) -> None:
    """Run agent with live dashboard.

    Example: coding-agent run --repo owner/repo --issue 123
    """
    from app.cli.dashboard import show_task_dashboard

    server_url = server or ctx.obj.get("server", discover_server())

    rprint(
        Panel.fit(
            f"[bold cyan]Running Code Agent[/bold cyan]\n"
            f"Server: {server_url}\n"
            f"Repo: {repo}\n"
            f"Issue: #{issue_number}"
        )
    )

    # Create task
    try:
        task = asyncio.run(
            create_task(
                server_url,
                "code-agent",
                issue_number=issue_number,
                branch_name=branch,
                max_iterations=max_iterations,
                repo_url=repo,
                github_token=token,
            )
        )
        rprint(f"[green]✓ Task created: {task.id}[/green]")

        # Show dashboard
        asyncio.run(show_task_dashboard(server_url, task.id))

    except Exception as e:
        rprint(Panel.fit(f"[bold red]Error:[/bold red] {e}"))
        raise click.ClickException(str(e))


# ============================================================================
# Server Commands
# ============================================================================


@cli.group()
def server() -> None:
    """Server management commands"""
    pass


@server.command()
@click.option(
    "--host",
    "-h",
    default="0.0.0.0",
    help="Host to bind to",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    type=int,
    help="Port to bind to",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload",
)
def start(host: str, port: int, reload: bool) -> None:
    """Start the API server.

    Example: coding-agent server start
    """
    import uvicorn

    rprint(
        Panel.fit(
            f"[bold cyan]Starting Coding Agents Server[/bold cyan]\n"
            f"Host: {host}\n"
            f"Port: {port}\n"
            f"Reload: {reload or 'off'}"
        )
    )

    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@server.command()
@click.option(
    "--server",
    "-s",
    help="Server URL to check",
)
@click.pass_context
def status(ctx: click.Context, server: str | None) -> None:
    """Check server health status.

    Example: coding-agent server status
    """
    server_url = server or ctx.obj.get("server", discover_server())

    try:
        health = asyncio.run(check_server_health(server_url))

        if not health:
            rprint(Panel.fit(f"[bold red]✗ Server not reachable[/bold red]\nURL: {server_url}"))
            raise click.ClickException("Server not reachable")

        status_color = "green" if health.get("status") == "healthy" else "yellow"
        status_text = health.get("status", "unknown")

        rprint(
            Panel.fit(
                f"[bold {status_color}]Status: {status_text.upper()}[/bold {status_color}]\n\n"
                f"Version: {health.get('version', 'N/A')}\n"
                f"OpenRouter: {'✓' if health.get('openrouter_configured') else '✗'}\n"
                f"GitHub: {'✓' if health.get('github_configured') else '✗'}\n"
                f"Redis: {'✓' if health.get('redis_connected') else '✗'}\n"
                f"Active Tasks: {health.get('active_tasks', 0)}"
            )
        )

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


# ============================================================================
# Task Commands
# ============================================================================


@cli.command()
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.option(
    "--status",
    help="Filter by status",
)
@click.option(
    "--active-only",
    is_flag=True,
    help="Show only active tasks",
)
@click.pass_context
def tasks(
    ctx: click.Context,
    server: str | None,
    status: str | None,
    active_only: bool,
) -> None:
    """List all tasks.

    Example: coding-agent tasks --active-only
    """
    from app.core.models.task import TaskStatus

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        task_list = asyncio.run(
            list_tasks(
                server_url,
                status=TaskStatus(status) if status else None,
                active_only=active_only,
            )
        )

        if not task_list:
            rprint("[dim]No tasks found[/dim]")
            return

        table = Table(title="Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Progress", style="green")
        table.add_column("Step", style="white")
        table.add_column("Age", style="dim")

        for task in task_list[:20]:  # Show first 20
            progress_pct = int(task.progress * 100)
            table.add_row(
                task.id[:12] + "...",
                task.type.value,
                task.status.value,
                f"{progress_pct}%",
                task.current_step[:30] or "N/A",
                format_duration(
                    (task.updated_at - task.created_at).total_seconds() if task.updated_at else None
                ),
            )

        console.print(table)
        rprint(f"\n[dim]Total: {len(task_list)} tasks[/dim]")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command("status")
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.argument("task_id")
@click.pass_context
def task_status(ctx: click.Context, server: str | None, task_id: str) -> None:
    """Show task status.

    Example: coding-agent status abc123-def456
    """
    server_url = server or ctx.obj.get("server", discover_server())

    try:
        task = asyncio.run(get_task(server_url, task_id))

        if not task:
            rprint(f"[red]Task {task_id} not found[/red]")
            raise click.ClickException("Task not found")

        status_text = format_status(task.status)

        rprint(
            Panel.fit(
                f"[bold cyan]Task {task_id[:12]}...[/bold cyan]\n"
                f"{status_text}\n\n"
                f"Type: {task.type.value}\n"
                f"Progress: {int(task.progress * 100)}%\n"
                f"Step: {task.current_step or 'N/A'}\n"
                f"Iteration: {task.iteration}/{task.max_iterations}\n"
                f"Created: {format_timestamp(task.created_at)}\n"
                f"Duration: {format_duration(task.duration_seconds)}"
            )
        )

        # Show recent logs
        if task.logs:
            recent_logs = task.logs[-5:]
            rprint("\n[bold]Recent logs:[/bold]")
            for log in recent_logs:
                rprint(f"  [dim]{log}[/dim]")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.argument("task_id")
@click.option(
    "--limit",
    "-n",
    default=50,
    help="Number of log entries",
)
@click.pass_context
def logs(ctx: click.Context, server: str | None, task_id: str, limit: int) -> None:
    """Show task logs.

    Example: coding-agent logs abc123-def456
    """
    server_url = server or ctx.obj.get("server", discover_server())

    try:
        log_entries = asyncio.run(get_task_logs(server_url, task_id, limit))

        if not log_entries:
            rprint("[dim]No logs found[/dim]")
            return

        rprint(f"[bold]Logs for task {task_id[:12]}...:[/bold]\n")

        for entry in log_entries:
            rprint(f"  {entry}")

        rprint(f"\n[dim]Showing {len(log_entries)} entries[/dim]")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.argument("task_id")
@click.pass_context
def diff(ctx: click.Context, server: str | None, task_id: str) -> None:
    """Show task file changes diff.

    Example: coding-agent diff abc123-def456
    """
    server_url = server or ctx.obj.get("server", discover_server())

    try:
        file_diffs = asyncio.run(get_task_diff(server_url, task_id))

        if not file_diffs:
            rprint("[dim]No file changes found[/dim]")
            return

        rprint(f"[bold]File changes for task {task_id[:12]}...:[/bold]\n")

        for file_path, diff_content in file_diffs.items():
            rprint(f"[cyan]{file_path}[/cyan]")
            syntax = Syntax(diff_content, "diff", theme="monokai", line_numbers=True)
            console.print(syntax)
            rprint()

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.argument("task_id")
@click.pass_context
def stop(ctx: click.Context, server: str | None, task_id: str) -> None:
    """Stop/cancel a running task.

    Example: coding-agent stop abc123-def456
    """
    server_url = server or ctx.obj.get("server", discover_server())

    try:
        rprint(f"[yellow]Stopping task {task_id[:12]}...[/yellow]")

        task = asyncio.run(cancel_task(server_url, task_id))

        rprint(Panel.fit(f"[bold green]✓ Task stopped[/bold green]\nStatus: {task.status.value}"))

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


# ============================================================================
# Config Commands
# ============================================================================


@cli.group()
def config() -> None:
    """Configuration management commands"""
    pass


@config.command("list")
@click.option(
    "--show-tokens",
    is_flag=True,
    help="Show stored tokens (masked)",
)
def config_list(show_tokens: bool) -> None:
    """List configuration.

    Example: coding-agent config list
    """
    from app.core.config import get_settings

    settings = get_settings()
    config_mgr = get_config_manager()
    config = config_mgr.load()

    rprint(
        Panel.fit(
            f"[bold cyan]Configuration[/bold cyan]\n\n"
            f"Config File: {config_mgr.config_file}\n"
            f"Default Server: {config.get('default_server', 'local')}\n"
            f"Configured Servers: {len(config.get('servers', {}))}\n"
            f"Stored Tokens: {len(config.get('tokens', {}))}"
        )
    )

    # Show servers
    servers = config.get("servers", {})
    if servers:
        table = Table(title="Servers")
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="blue")
        table.add_column("Default", style="green")

        default = config.get("default_server", "local")
        for name, info in servers.items():
            is_default = "✓" if name == default else ""
            table.add_row(name, info.get("url", ""), is_default)

        console.print(table)

    # Show tokens (masked)
    if show_tokens:
        tokens = config.get("tokens", {})
        if tokens:
            rprint("\n[bold]Stored Tokens:[/bold]")
            for url, token in tokens.items():
                masked = token[:8] + "..." if len(token) > 8 else "***"
                rprint(f"  {url}: {masked}")


@config.command("add-server")
@click.argument("name")
@click.argument("url")
@click.option(
    "--description",
    "-d",
    default="",
    help="Server description",
)
@click.option(
    "--set-default",
    is_flag=True,
    help="Set as default server",
)
def config_add_server(name: str, url: str, description: str, set_default: bool) -> None:
    """Add a server to configuration.

    Example: coding-agent config add-server mycloud https://api.example.com
    """
    config_mgr = get_config_manager()
    config_mgr.add_server(name, url, description)

    if set_default:
        config_mgr.set_default_server(name)

    rprint(
        Panel.fit(
            f"[bold green]✓ Server added[/bold green]\n\n"
            f"Name: {name}\n"
            f"URL: {url}\n"
            f"Default: {'Yes' if set_default else 'No'}"
        )
    )


@config.command("remove-server")
@click.argument("name")
def config_remove_server(name: str) -> None:
    """Remove a server from configuration.

    Example: coding-agent config remove-server mycloud
    """
    config_mgr = get_config_manager()

    if not config_mgr.remove_server(name):
        rprint(f"[red]Server '{name}' not found[/red]")
        raise click.ClickException("Server not found")

    rprint(Panel.fit(f"[bold green]✓ Server '{name}' removed[/bold green]"))


@config.command("set-default")
@click.argument("name")
def config_set_default(name: str) -> None:
    """Set default server.

    Example: coding-agent config set-default mycloud
    """
    config_mgr = get_config_manager()

    if not config_mgr.set_default_server(name):
        rprint(f"[red]Server '{name}' not found[/red]")
        raise click.ClickException("Server not found")

    rprint(Panel.fit(f"[bold green]✓ Default server set to '{name}'[/bold green]"))


@config.command("add-token")
@click.argument("server_url")
@click.argument("token")
def config_add_token(server_url: str, token: str) -> None:
    """Store GitHub token for a server.

    Example: coding-agent config add-token https://api.example.com ghp_xxx
    """
    config_mgr = get_config_manager()
    config_mgr.add_token(server_url, token)

    masked = token[:8] + "..." if len(token) > 8 else "***"
    rprint(
        Panel.fit(
            f"[bold green]✓ Token stored[/bold green]\n\nServer: {server_url}\nToken: {masked}"
        )
    )


@config.command("remove-token")
@click.argument("server_url")
def config_remove_token(server_url: str) -> None:
    """Remove stored GitHub token for a server.

    Example: coding-agent config remove-token https://api.example.com
    """
    config_mgr = get_config_manager()

    if not config_mgr.remove_token(server_url):
        rprint(f"[yellow]No token found for {server_url}[/yellow]")
    else:
        rprint(Panel.fit(f"[bold green]✓ Token removed for {server_url}[/bold green]"))


# ============================================================================
# Legacy Commands (backward compatibility)
# ============================================================================


@cli.command("code-agent")
@click.argument("issue_number", type=int)
@click.option(
    "--branch",
    "-b",
    help="Branch name for changes",
)
@click.option(
    "--max-iterations",
    "-m",
    default=5,
    help="Maximum number of iterations",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output results to JSON file",
)
def code_agent_legacy(
    issue_number: int, branch: str | None, max_iterations: int, output: str | None
) -> None:
    """Run Code Agent directly (legacy, use 'run' command instead).

    Example: coding-agents code-agent 123
    """
    rprint(
        Panel.fit(
            f"[bold yellow]Note:[/bold yellow] This is a legacy command. "
            f"Use 'coding-agent run --repo owner/repo --issue {issue_number}' instead.\n\n"
            f"[bold blue]Code Agent[/bold blue]\nProcessing Issue #{issue_number}"
        )
    )

    # Show issue info
    with console.status("[bold yellow]Fetching issue details..."):
        issue_context = get_issue_context.invoke({"issue_number": issue_number})

    console.print(
        Panel(
            issue_context[:500] + "..." if len(issue_context) > 500 else issue_context,
            title="Issue Context",
        )
    )

    # Run the agent
    with console.status("[bold yellow]Code Agent is working..."):
        result = asyncio.run(run_code_agent(issue_number, branch, max_iterations))

    # Display results
    if result["success"]:
        rprint(
            Panel.fit(
                f"[bold green]✓ Success[/bold green]\n\n"
                f"Status: {result['status']}\n"
                f"PR URL: {result['pr_url']}\n"
                f"Files Generated: {len(result.get('files_generated', []))}"
            )
        )
    else:
        rprint(
            Panel.fit(
                f"[bold red]✗ Error[/bold red]\n\n"
                f"Status: {result['status']}\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
        )

    # Output to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"\n[dim]Results saved to {output}[/dim]")


@cli.command("reviewer")
@click.argument("pr_number", type=int)
@click.option(
    "--issue-number",
    "-i",
    type=int,
    help="Associated issue number",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output results to JSON file",
)
def reviewer_legacy(pr_number: int, issue_number: int | None, output: str | None) -> None:
    """Run Reviewer Agent directly (legacy command).

    Example: coding-agents reviewer 456
    """
    rprint(Panel.fit(f"[bold blue]Reviewer Agent[/bold blue]\nAnalyzing PR #{pr_number}"))

    # Show PR info
    with console.status("[bold yellow]Fetching PR details..."):
        diff = analyze_pr_diff.invoke({"pr_number": pr_number})
        ci = get_ci_results.invoke({"pr_number": pr_number})

    # Show CI status
    ci_status = ci.get("state", "unknown")
    ci_color = "green" if ci_status == "success" else "red" if ci_status == "failure" else "yellow"
    console.print(Panel(f"CI/CD Status: [{ci_color}]{ci_status}[/{ci_color}]", title="CI Results"))

    # Run the agent
    with console.status("[bold yellow]Reviewer Agent is working..."):
        result = asyncio.run(run_reviewer_agent(pr_number, issue_number))

    # Display results
    if result["success"]:
        decision = result.get("decision", "comment")
        decision_color = {
            "approve": "green",
            "request_changes": "red",
            "comment": "yellow",
        }.get(decision, "white")

        rprint(
            Panel.fit(
                f"[bold {decision_color}]Decision: {decision.upper()}[/bold {decision_color}]\n\n"
                f"{result.get('summary', '')}\n\n"
                f"Issues Found: {len(result.get('issues', []))}"
            )
        )
    else:
        rprint(
            Panel.fit(
                f"[bold red]✗ Error[/bold red]\n\n"
                f"Status: {result['status']}\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
        )

    # Output to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"\n[dim]Results saved to {output}[/dim]")


@cli.command("show-issue")
@click.argument("issue_number", type=int)
def show_issue(issue_number: int) -> None:
    """Display issue details.

    Example: coding-agents show-issue 123
    """
    context = get_issue_context.invoke({"issue_number": issue_number})
    console.print(Panel(context, title=f"Issue #{issue_number}"))


@cli.command("show-pr")
@click.argument("pr_number", type=int)
def show_pr(pr_number: int) -> None:
    """Display PR details.

    Example: coding-agents show-pr 456
    """
    diff = analyze_pr_diff.invoke({"pr_number": pr_number})
    ci = get_ci_results.invoke({"pr_number": pr_number})

    console.print(
        Panel(diff[:1000] + "..." if len(diff) > 1000 else diff, title=f"PR #{pr_number} Diff")
    )
    console.print(Panel(json.dumps(ci, indent=2), title="CI/CD Results"))


def main() -> None:
    """Entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()


# ============================================================================
# Monitoring Commands
# ============================================================================


@cli.group()
def monitor() -> None:
    """Repository monitoring commands"""
    pass


@monitor.command("add")
@click.argument("owner")
@click.argument("repo")
@click.option(
    "--token",
    "-t",
    "github_token",
    required=True,
    help="GitHub token for repository access",
)
@click.option(
    "--interval",
    "-i",
    "poll_interval",
    default=60,
    type=int,
    help="Poll interval in seconds (default: 60)",
)
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.pass_context
def monitor_add(
    ctx: click.Context,
    owner: str,
    repo: str,
    github_token: str,
    poll_interval: int,
    server: str | None,
) -> None:
    """Add repository to monitoring.

    Example: coding-agent monitor add facebook react --token ghp_xxx
    """
    import httpx

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        response = httpx.post(
            f"{server_url}/monitoring/repos",
            json={
                "owner": owner,
                "repo": repo,
                "github_token": github_token,
                "poll_interval": poll_interval,
            },
            timeout=30.0,
        )
        response.raise_for_status()

        result = response.json()

        rprint(
            Panel.fit(
                f"[bold green]✓ Repository added to monitoring[/bold green]\n\n"
                f"Repository: {owner}/{repo}\n"
                f"Poll Interval: {poll_interval}s\n"
                f"Server: {server_url}"
            )
        )

    except httpx.HTTPStatusError as e:
        rprint(f"[red]Error: {e.response.json().get('detail', e)}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@monitor.command("remove")
@click.argument("owner")
@click.argument("repo")
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.pass_context
def monitor_remove(
    ctx: click.Context,
    owner: str,
    repo: str,
    server: str | None,
) -> None:
    """Remove repository from monitoring.

    Example: coding-agent monitor remove facebook react
    """
    import httpx

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        response = httpx.delete(
            f"{server_url}/monitoring/repos/{owner}/{repo}",
            timeout=30.0,
        )
        response.raise_for_status()

        rprint(
            Panel.fit(
                f"[bold green]✓ Repository removed from monitoring[/bold green]\n\n"
                f"Repository: {owner}/{repo}"
            )
        )

    except httpx.HTTPStatusError as e:
        rprint(f"[red]Error: {e.response.json().get('detail', e)}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@monitor.command("list")
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.pass_context
def monitor_list(
    ctx: click.Context,
    server: str | None,
) -> None:
    """List all monitored repositories.

    Example: coding-agent monitor list
    """
    import httpx

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        response = httpx.get(
            f"{server_url}/monitoring/repos",
            timeout=30.0,
        )
        response.raise_for_status()

        repos = response.json()

        if not repos:
            rprint("[dim]No monitored repositories[/dim]")
            return

        table = Table(title="Monitored Repositories")
        table.add_column("Repository", style="cyan")
        table.add_column("Enabled", style="green")
        table.add_column("Interval", style="yellow")
        table.add_column("Last Checked", style="blue")
        table.add_column("Processed Issues", style="white")

        for r in repos:
            table.add_row(
                r["repo"],
                "✓" if r["enabled"] else "✗",
                f"{r['poll_interval']}s",
                r["last_checked"][:19] if r["last_checked"] else "Never",
                str(r["processed_issues_count"]),
            )

        console.print(table)
        rprint(f"\n[dim]Total: {len(repos)} repositories[/dim]")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@monitor.command("status")
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.pass_context
def monitor_status(
    ctx: click.Context,
    server: str | None,
) -> None:
    """Show monitoring status.

    Example: coding-agent monitor status
    """
    import httpx

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        response = httpx.get(
            f"{server_url}/monitoring/status",
            timeout=30.0,
        )
        response.raise_for_status()

        status_data = response.json()

        status_color = "green" if status_data["running"] else "yellow"
        status_text = "Running" if status_data["running"] else "Stopped"

        rprint(
            Panel.fit(
                f"[bold {status_color}]Monitoring Status: {status_text}[/bold {status_color}]\n\n"
                f"Repositories: {status_data['repos_count']}\n"
                f"Server: {server_url}"
            )
        )

        # Show repos if any
        if status_data.get("repos"):
            rprint("\n[bold]Repositories:[/bold]")
            for r in status_data["repos"]:
                rprint(f"  [cyan]{r['repo']}[/cyan]: {r['processed_issues']} issues processed")

    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@monitor.command("start")
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.pass_context
def monitor_start(
    ctx: click.Context,
    server: str | None,
) -> None:
    """Start repository monitoring.

    Example: coding-agent monitor start
    """
    import httpx

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        response = httpx.post(
            f"{server_url}/monitoring/start",
            timeout=30.0,
        )
        response.raise_for_status()

        result = response.json()

        rprint(
            Panel.fit(
                f"[bold green]✓ Monitoring started[/bold green]\n\n{result.get('message', '')}"
            )
        )

    except httpx.HTTPStatusError as e:
        rprint(f"[red]Error: {e.response.json().get('detail', e)}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


@monitor.command("stop")
@click.option(
    "--server",
    "-s",
    help="Server URL",
)
@click.pass_context
def monitor_stop(
    ctx: click.Context,
    server: str | None,
) -> None:
    """Stop repository monitoring.

    Example: coding-agent monitor stop
    """
    import httpx

    server_url = server or ctx.obj.get("server", discover_server())

    try:
        response = httpx.post(
            f"{server_url}/monitoring/stop",
            timeout=30.0,
        )
        response.raise_for_status()

        result = response.json()

        rprint(
            Panel.fit(
                f"[bold yellow]⏸ Monitoring stopped[/bold yellow]\n\n{result.get('message', '')}"
            )
        )

    except httpx.HTTPStatusError as e:
        rprint(f"[red]Error: {e.response.json().get('detail', e)}[/red]")
        raise click.ClickException(str(e))
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))
