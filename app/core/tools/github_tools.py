"""Инструменты GitHub API с использованием PyGithub и LangChain"""

from typing import Any

from langchain_core.tools import tool

from app.core.config import get_settings
from github import Github, GithubException

settings = get_settings()


def get_github_client() -> Github:
    """Получить аутентифицированный клиент GitHub"""
    return Github(settings.github_token, base_url=settings.github_base_url)


def get_repo() -> Any:
    """Получить настроенный репозиторий"""
    client = get_github_client()
    return client.get_repo(settings.github_repo)


@tool
def get_issue_context(issue_number: int) -> str:
    """
    Получить полный контекст GitHub Issue, включая название, тело, метки и комментарии.

    Args:
        issue_number: Номер GitHub issue

    Returns:
        Форматированная строка с контекстом issue
    """
    try:
        repo = get_repo()
        issue = repo.get_issue(issue_number)

        # Сборка строки контекста
        context_parts = [
            f"# Issue #{issue.number}: {issue.title}",
            f"**Состояние:** {issue.state}",
            f"**Автор:** {issue.user.login}",
            f"**Создан:** {issue.created_at.isoformat()}",
            f"**Метки:** {', '.join([label.name for label in issue.labels])}",
            "",
            "## Описание",
            issue.body or "Описание не предоставлено.",
        ]

        # Добавление комментариев при наличии
        comments = list(issue.get_comments())
        if comments:
            context_parts.append("\n## Комментарии")
            for comment in comments:
                context_parts.append(
                    f"**{comment.user.login}** ({comment.created_at.isoformat()}):\n{comment.body}"
                )

        return "\n".join(context_parts)

    except GithubException as e:
        return f"Ошибка получения issue: {e!s}"


@tool
def analyze_pr_diff(pr_number: int) -> str:
    """
    Получить diff кода для Pull Request.

    Args:
        pr_number: Номер pull request

    Returns:
        Форматированная строка с diff
    """
    try:
        repo = get_repo()
        pr = repo.get_pull(pr_number)

        # Получение diff
        diff_parts = [f"# Pull Request #{pr.number}: {pr.title}", ""]
        diff_parts.append(f"**Ветка:** {pr.head.ref} -> {pr.base.ref}")
        diff_parts.append(f"**Состояние:** {pr.state}")
        diff_parts.append(f"**Автор:** {pr.user.login}")
        diff_parts.append(f"**Добавлений:** {pr.additions}")
        diff_parts.append(f"**Удалений:** {pr.deletions}")
        diff_parts.append(f"**Изменённых файлов:** {pr.changed_files}")
        diff_parts.append("")

        # Получение diff файлов
        for file in pr.get_files():
            diff_parts.append(f"## {file.filename}")
            diff_parts.append(f"**Статус:** {file.status}")
            diff_parts.append(f"**Изменения:** +{file.additions} -{file.deletions}")
            diff_parts.append("")
            diff_parts.append("```diff")
            diff_parts.append(file.patch or "Diff недоступен (бинарный файл или слишком большой)")
            diff_parts.append("```")
            diff_parts.append("")

        return "\n".join(diff_parts)

    except GithubException as e:
        return f"Ошибка получения diff PR: {e!s}"


@tool
def create_pr(
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "main",
) -> str:
    """
    Создать Pull Request.

    Args:
        branch_name: Имя ветки с изменениями
        title: Заголовок PR
        body: Тело описания PR
        base_branch: Целевая ветка (по умолчанию: main)

    Returns:
        URL созданного PR
    """
    try:
        repo = get_repo()
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )
        return f"Pull Request создан: {pr.html_url}"

    except GithubException as e:
        return f"Ошибка создания PR: {e!s}"


@tool
def post_review_comment(pr_number: int, comment: str) -> str:
    """
    Опубликовать комментарий рецензии к Pull Request.

    Args:
        pr_number: Номер pull request
        comment: Текст комментария для публикации

    Returns:
        Подтверждающее сообщение
    """
    try:
        repo = get_repo()
        pr = repo.get_pull(pr_number)
        issue = pr.as_issue()
        issue.create_comment(comment)
        return f"Комментарий опубликован в PR #{pr_number}"

    except GithubException as e:
        return f"Ошибка публикации комментария: {e!s}"


@tool
def get_ci_results(pr_number: int) -> dict[str, Any]:
    """
    Получить результаты CI/CD для Pull Request.

    Args:
        pr_number: Номер pull request

    Returns:
        Словарь с информацией о статусе CI
    """
    try:
        repo = get_repo()
        pr = repo.get_pull(pr_number)
        head_sha = pr.head.sha

        # Получение объединённого статуса
        combined_status = repo.get_commit(sha=head_sha).get_combined_status()

        results = {
            "state": combined_status.state,
            "statuses": [],
            "total_count": combined_status.total_count,
        }

        for status in combined_status.statuses:
            results["statuses"].append(
                {
                    "context": status.context,
                    "state": status.state,
                    "description": status.description,
                    "target_url": status.target_url,
                }
            )

        return results

    except GithubException as e:
        return {"error": str(e), "state": "error"}


@tool
def create_branch(branch_name: str, source_branch: str = "main") -> str:
    """
    Создать новую ветку из исходной ветки.

    Args:
        branch_name: Имя для новой ветки
        source_branch: Ветка для создания из (по умолчанию: main)

    Returns:
        Подтверждающее сообщение
    """
    try:
        repo = get_repo()
        source = repo.get_branch(source_branch)
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)
        return f"Ветка '{branch_name}' создана из '{source_branch}'"

    except GithubException as e:
        return f"Ошибка создания ветки: {e!s}"


@tool
def get_file_contents(file_path: str, branch: str = "main") -> str:
    """
    Получить содержимое файла из репозитория.

    Args:
        file_path: Путь к файлу в репозитории
        branch: Ветка для получения файла (по умолчанию: main)

    Returns:
        Содержимое файла как строка
    """
    try:
        repo = get_repo()
        contents = repo.get_contents(file_path, ref=branch)

        if contents.type == "file":
            # Декодирование base64 содержимого
            import base64

            decoded = base64.b64decode(contents.content).decode("utf-8")
            return decoded
        else:
            return f"Ошибка: {file_path} не является файлом (тип: {contents.type})"

    except GithubException as e:
        return f"Ошибка получения файла: {e!s}"


@tool
def update_file(
    file_path: str,
    content: str,
    commit_message: str,
    branch: str = "main",
) -> str:
    """
    Обновить или создать файл в репозитории.

    Args:
        file_path: Путь к файлу
        content: Новое содержимое файла
        commit_message: Сообщение коммита
        branch: Ветка для коммита

    Returns:
        Подтверждающее сообщение с URL коммита
    """
    try:
        repo = get_repo()

        # Попытка получить существующий файл
        try:
            contents = repo.get_contents(file_path, ref=branch)
            result = repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=contents.sha,
                branch=branch,
            )
            return f"Файл обновлён: {result['commit'].html_url}"
        except GithubException:
            # Файл не существует, создаём новый
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch,
            )
            return f"Файл создан: {result['commit'].html_url}"

    except GithubException as e:
        return f"Ошибка обновления файла: {e!s}"


@tool
def get_repository_structure(branch: str = "main") -> str:
    """
    Получить структуру репозитория (вид дерева).

    Args:
        branch: Ветка для анализа (по умолчанию: main)

    Returns:
        Форматированная строка со структурой репозитория
    """
    try:
        repo = get_repo()
        tree = repo.get_git_tree(sha=branch, recursive=True)

        structure = []
        for item in tree.tree:
            structure.append(f"{'📁' if item.type == 'tree' else '📄'} {item.path}")

        return "\n".join(structure) if structure else "Репозиторий пуст"

    except GithubException as e:
        return f"Ошибка получения структуры репозитория: {e!s}"


@tool
def approve_pr(pr_number: int) -> str:
    """
    Одобрить Pull Request.

    Args:
        pr_number: Номер pull request

    Returns:
        Подтверждающее сообщение
    """
    try:
        repo = get_repo()
        pr = repo.get_pull(pr_number)
        pr.create_review(event="APPROVE")
        return f"PR #{pr_number} одобрен"

    except GithubException as e:
        return f"Ошибка одобрения PR: {e!s}"


@tool
def merge_pr(pr_number: int, commit_message: str | None = None) -> str:
    """
    Слить Pull Request.

    Args:
        pr_number: Номер pull request
        commit_message: Опциональное пользовательское сообщение коммита

    Returns:
        Подтверждающее сообщение
    """
    try:
        repo = get_repo()
        pr = repo.get_pull(pr_number)

        if pr.mergeable:
            pr.merge(commit_message=commit_message)
            return f"PR #{pr_number} успешно слит"
        else:
            return f"PR #{pr_number} не может быть слит"

    except GithubException as e:
        return f"Ошибка слияния PR: {e!s}"


# Экспорт всех инструментов для LangChain
GITHUB_TOOLS = [
    get_issue_context,
    analyze_pr_diff,
    create_pr,
    post_review_comment,
    get_ci_results,
    create_branch,
    get_file_contents,
    update_file,
    get_repository_structure,
    approve_pr,
    merge_pr,
]
