"""Unit tests for GitHub tools"""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.core.tools.github_tools import (
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
)


@pytest.mark.unit
def test_get_issue_context(mock_github):
    """Test getting issue context"""
    result = get_issue_context.invoke({"issue_number": 1})

    assert "Test Issue" in result
    assert "Test issue body" in result
    assert "# Issue #1" in result


@pytest.mark.unit
def test_create_branch(mock_github):
    """Test creating a branch"""
    result = create_branch.invoke({
        "branch_name": "test-branch",
        "source_branch": "main"
    })

    # Проверка на русском: "создана" означает "created"
    assert "создана" in result.lower()
    mock_github.get_repo().create_git_ref.assert_called_once()


@pytest.mark.unit
def test_create_pr(mock_github):
    """Test creating a pull request"""
    result = create_pr.invoke({
        "branch_name": "test-branch",
        "title": "Test PR",
        "body": "Test PR body",
        "base_branch": "main"
    })

    # Проверка: "pull request" (английский термин) все еще присутствует
    assert "pull request" in result.lower()
    mock_github.get_repo().create_pull.assert_called_once()


@pytest.mark.unit
def test_get_file_contents(mock_github):
    """Test getting file contents"""
    # Setup mock to return actual content
    import base64
    repo = mock_github.get_repo()
    contents = repo.get_contents("test.py", "main")
    contents.content = base64.b64encode(b"test content").decode()

    result = get_file_contents.invoke({"file_path": "test.py", "branch": "main"})

    assert "test content" in result


@pytest.mark.unit
def test_update_file_new(mock_github):
    """Test updating a file - new file (not in repo)"""
    repo = mock_github.get_repo()

    # Reset the mock for this test
    repo.get_contents.reset_mock()

    def get_contents_not_found(*args, **kwargs):
        from github import GithubException, UnknownObjectException
        raise UnknownObjectException(404, {"message": "Not found"})

    repo.get_contents.side_effect = get_contents_not_found

    result = update_file.invoke({
        "file_path": "new_file.py",
        "content": "new content",
        "commit_message": "Create file",
        "branch": "main"
    })

    # Проверка на русском: "файл" означает "file"
    assert "файл" in result.lower()


@pytest.mark.unit
def test_update_file_existing(mock_github):
    """Test updating a file - existing file"""
    result = update_file.invoke({
        "file_path": "test.py",
        "content": "updated content",
        "commit_message": "Update file",
        "branch": "main"
    })

    # Проверка на русском: "обновлён" или "создан" (updated/created)
    assert "обновл" in result.lower() or "создан" in result.lower()


@pytest.mark.unit
def test_approve_pr(mock_github):
    """Test approving a PR"""
    repo = mock_github.get_repo()
    pr = repo.get_pull(1)
    pr.create_review.return_value = MagicMock()

    result = approve_pr.invoke({"pr_number": 1})

    # Проверка на русском: "одобрен" означает "approved"
    assert "одобрен" in result.lower()
    pr.create_review.assert_called_with(event="APPROVE")


@pytest.mark.unit
def test_merge_pr(mock_github):
    """Test merging a PR"""
    repo = mock_github.get_repo()
    pr = repo.get_pull(1)
    pr.mergeable = True
    pr.merge.return_value = MagicMock()

    result = merge_pr.invoke({"pr_number": 1})

    # Проверка на русском: "слит" означает "merged"
    assert "слит" in result.lower()
    pr.merge.assert_called_once()


@pytest.mark.unit
def test_post_review_comment(mock_github):
    """Test posting a review comment"""
    repo = mock_github.get_repo()
    pr = repo.get_pull(1)
    issue = pr.as_issue()
    issue.create_comment.return_value = MagicMock()

    result = post_review_comment.invoke({
        "pr_number": 1,
        "comment": "Test comment"
    })

    # Проверка на русском: "комментарий" означает "comment"
    assert "комментарий" in result.lower()
    issue.create_comment.assert_called_with("Test comment")
