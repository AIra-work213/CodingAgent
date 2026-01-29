"""Reviewer Agent: LangGraph workflow for reviewing Pull Requests"""

import json
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.core.llm.openrouter import get_review_llm
from app.core.llm.prompts import CODE_REVIEW_PROMPT
from app.core.tools.github_tools import (
    analyze_pr_diff,
    approve_pr,
    get_ci_results,
    get_issue_context,
    merge_pr,
    post_review_comment,
)


class ReviewerAgentState(TypedDict):
    """State for the Reviewer Agent workflow"""

    # Input
    pr_number: int
    issue_number: int | None

    # Context
    pr_diff: str
    pr_title: str
    requirements: dict[str, Any]
    ci_results: dict[str, Any]

    # Review
    review_comments: list[dict[str, Any]]
    review_summary: str
    approval_decision: Literal["approve", "request_changes", "comment"]

    # Status tracking
    status: Literal["analyzing", "reviewing", "deciding", "done", "error"]
    error: str | None

    # Messages for LLM context
    messages: list


def analyze_pr_node(state: ReviewerAgentState) -> ReviewerAgentState:
    """Analyze the Pull Request diff and CI results"""
    print(f"[Reviewer Agent] Analyzing PR #{state['pr_number']}")

    try:
        # Get PR diff
        diff_result = analyze_pr_diff.invoke({"pr_number": state["pr_number"]})
        state["pr_diff"] = diff_result

        # Parse PR title from diff
        lines = diff_result.split("\n")
        for line in lines:
            if line.startswith("# Pull Request #"):
                state["pr_title"] = line.split(": ")[1] if ": " in line else "Unknown"
                break

        # Get CI results
        ci_results = get_ci_results.invoke({"pr_number": state["pr_number"]})
        state["ci_results"] = ci_results

        # Get requirements from issue if available
        if state.get("issue_number"):
            issue_context = get_issue_context.invoke({"issue_number": state["issue_number"]})
            # Parse requirements from issue context
            # For now, store the context
            state["requirements"] = {"issue_context": issue_context}
        else:
            state["requirements"] = {}

        state["status"] = "reviewing"
        print(
            f"[Reviewer Agent] PR Analysis complete - CI status: {ci_results.get('state', 'unknown')}"
        )

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to analyze PR: {e!s}"
        print(f"[Reviewer Agent] Error: {state['error']}")

    return state


def review_code_node(state: ReviewerAgentState) -> ReviewerAgentState:
    """Review the code changes"""
    print("[Reviewer Agent] Reviewing code changes")

    try:
        # Use LLM to review the code
        chain = CODE_REVIEW_PROMPT | get_review_llm()
        response = chain.invoke(
            {
                "pr_number": state["pr_number"],
                "pr_title": state["pr_title"],
                "requirements": json.dumps(state["requirements"], indent=2),
                "diff": state["pr_diff"],
                "ci_results": json.dumps(state["ci_results"], indent=2),
            }
        )

        # Parse review results
        review_result = json.loads(response.content)

        state["review_comments"] = review_result.get("issues", [])
        state["review_summary"] = review_result.get("summary", "")
        state["approval_decision"] = review_result.get("overall_decision", "comment")

        # Check if requirements are met
        requirements_met = review_result.get("requirements_met", True)

        print(
            f"[Reviewer Agent] Review complete: {state['approval_decision']} (score: {review_result.get('score', 'N/A')})"
        )
        print(f"[Reviewer Agent] Found {len(state['review_comments'])} issues")

        # Add positives to summary
        positives = review_result.get("positives", [])
        if positives:
            state["review_summary"] += "\n\n**Positives:**\n" + "\n".join(
                f"- {p}" for p in positives
            )

        state["status"] = "deciding"

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to review code: {e!s}"
        print(f"[Reviewer Agent] Error: {state['error']}")

    return state


def decide_action_node(state: ReviewerAgentState) -> ReviewerAgentState:
    """Decide on approval/rejection/merge"""
    print(f"[Reviewer Agent] Making decision: {state['approval_decision']}")

    try:
        decision = state["approval_decision"]
        pr_number = state["pr_number"]

        # Build review comment
        comment_body = f"""## Code Review Results

### Decision: {decision.upper()}

### Summary
{state["review_summary"]}

### Review Comments
"""

        if state["review_comments"]:
            for i, comment in enumerate(state["review_comments"], 1):
                comment_body += f"\n{i}. **[{comment['severity'].upper()}]** {comment['message']}\n"
                if "file" in comment:
                    comment_body += f"   - File: {comment['file']}:{comment.get('line', 'N/A')}\n"
                if "suggestion" in comment:
                    comment_body += f"   - Suggestion: {comment['suggestion']}\n"
        else:
            comment_body += "\nNo issues found! Code looks good."

        # Add CI status to comment
        ci_state = state["ci_results"].get("state", "unknown")
        comment_body += f"\n\n### CI/CD Status\n**Status:** {ci_state}\n"

        if ci_state == "success":
            # Post review and approve
            post_review_comment.invoke({"pr_number": pr_number, "comment": comment_body})
            approve_pr.invoke({"pr_number": pr_number})
            print(f"[Reviewer Agent] PR #{pr_number} approved")
        elif ci_state == "failure":
            comment_body += "\n⚠️ CI checks failed. Please fix before merging."
            post_review_comment.invoke({"pr_number": pr_number, "comment": comment_body})
            print(f"[Reviewer Agent] PR #{pr_number} rejected due to CI failure")
        else:
            # CI pending or no status - just post comment
            post_review_comment.invoke({"pr_number": pr_number, "comment": comment_body})
            print(f"[Reviewer Agent] Review comment posted for PR #{pr_number}")

        # Auto-merge if approved and CI passed
        if decision == "approve" and ci_state == "success":
            merge_result = merge_pr.invoke({"pr_number": pr_number})
            print(f"[Reviewer Agent] {merge_result}")
            comment_body += f"\n\n✅ **Auto-merged**: {merge_result}"

        state["status"] = "done"

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to decide action: {e!s}"
        print(f"[Reviewer Agent] Error: {state['error']}")

    return state


def should_continue_review(state: ReviewerAgentState) -> Literal["continue", "end"]:
    """Determine if workflow should continue"""
    if state["status"] == "error":
        return "end"
    if state["status"] == "done":
        return "end"
    return "continue"


def create_reviewer_agent_graph() -> StateGraph:
    """Create the Reviewer Agent LangGraph workflow"""

    # Define workflow
    workflow = StateGraph(ReviewerAgentState)

    # Add nodes
    workflow.add_node("analyze_pr", analyze_pr_node)
    workflow.add_node("review_code", review_code_node)
    workflow.add_node("decide_action", decide_action_node)

    # Set entry point
    workflow.set_entry_point("analyze_pr")

    # Add edges
    workflow.add_conditional_edges(
        "analyze_pr",
        should_continue_review,
        {
            "continue": "review_code",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "review_code",
        should_continue_review,
        {
            "continue": "decide_action",
            "end": END,
        },
    )
    workflow.add_edge("decide_action", END)

    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


async def run_reviewer_agent(
    pr_number: int,
    issue_number: int | None = None,
) -> dict[str, Any]:
    """
    Run the Reviewer Agent for a given Pull Request.

    Args:
        pr_number: GitHub pull request number
        issue_number: Associated issue number (optional)

    Returns:
        Dictionary with review results
    """
    # Initialize state
    initial_state: ReviewerAgentState = {
        "pr_number": pr_number,
        "issue_number": issue_number,
        "pr_diff": "",
        "pr_title": "",
        "requirements": {},
        "ci_results": {},
        "review_comments": [],
        "review_summary": "",
        "approval_decision": "comment",
        "status": "analyzing",
        "error": None,
        "messages": [],
    }

    # Create and run graph
    graph = create_reviewer_agent_graph()

    config = RunnableConfig(configurable={"thread_id": f"reviewer-agent-pr-{pr_number}"})

    try:
        result = await graph.ainvoke(initial_state, config)

        return {
            "success": result["status"] == "done",
            "status": result["status"],
            "decision": result.get("approval_decision", "comment"),
            "summary": result.get("review_summary", ""),
            "issues": result.get("review_comments", []),
            "ci_status": result.get("ci_results", {}).get("state", "unknown"),
            "error": result.get("error"),
        }

    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "error": str(e),
        }
