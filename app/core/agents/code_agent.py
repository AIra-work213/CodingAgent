"""Code Agent: LangGraph workflow for processing Issues and generating code"""

import json
from typing import Annotated, Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.core.llm.openrouter import get_coding_llm, get_planning_llm
from app.core.llm.prompts import (
    CODE_GENERATION_PROMPT,
    CODE_VALIDATION_PROMPT,
    ISSUE_PARSER_PROMPT,
    REQUIREMENTS_ANALYZER_PROMPT,
)
from app.core.tools.github_tools import (
    create_branch,
    create_pr,
    get_file_contents,
    get_issue_context,
    get_repository_structure,
    update_file,
)


class CodeAgentState(TypedDict):
    """State for the Code Agent workflow"""

    # Input
    issue_number: int
    branch_name: str

    # Parsed data
    issue: str
    requirements: dict[str, Any]
    implementation_plan: dict[str, Any]

    # Code generation
    current_code: dict[str, str]
    generated_code: dict[str, str]
    validation_results: dict[str, Any]

    # PR info
    pr_url: str
    pr_number: int

    # Iteration
    feedback: list[str]
    iteration: int
    max_iterations: int

    # Status
    status: Literal["parsing", "analyzing", "generating", "validating", "pr", "done", "error"]
    error: str | None

    # Messages for LLM context
    messages: Annotated[list, add_messages]


def parse_issue_node(state: CodeAgentState) -> CodeAgentState:
    """Парсит Issue для получения требований по задаче"""
    print(f"[Code Agent] Парсинг Issue #{state['issue_number']}")

    try:
        # Get issue context from GitHub
        issue_context = get_issue_context.invoke({"issue_number": state["issue_number"]})

        # Use LLM to parse the issue
        chain = ISSUE_PARSER_PROMPT | get_planning_llm()

        # Extract issue title and body from context
        lines = issue_context.split("\n")
        title = lines[0].replace("# Issue #", "").split(": ")[1] if ": " in lines[0] else "Unknown"
        body = (
            "\n".join(lines[lines.index("## Description") + 1 :])
            if "## Description" in issue_context
            else ""
        )

        response = chain.invoke(
            {
                "issue_number": state["issue_number"],
                "issue_title": title,
                "issue_body": body,
            }
        )

        # Parse JSON response
        requirements = json.loads(response.content)

        state["requirements"] = requirements
        state["issue"] = issue_context
        state["status"] = "analyzing"
        state["messages"] = [
            SystemMessage(content="Я занимаюсь парсингом issue для получения требований к задаче"),
            HumanMessage(content=issue_context),
        ]

        print(
            f"[Code Agent] Полученная информация: {requirements.get('type', 'unknown')} - {requirements.get('title', 'no title')}"
        )

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to parse issue: {e!s}"
        print(f"[Code Agent] Error: {state['error']}")

    return state


def analyze_requirements_node(state: CodeAgentState) -> CodeAgentState:
    """Анализ информации и создание плана разработки"""
    print("[Code Agent] Анализ информации и создание плана разработки")

    try:
        # Get repository context
        repo_structure = get_repository_structure.invoke({"branch": "main"})

        # Use LLM to analyze requirements
        chain = REQUIREMENTS_ANALYZER_PROMPT | get_planning_llm()
        response = chain.invoke(
            {
                "requirements": json.dumps(state["requirements"], indent=2),
                "repo_context": repo_structure,
            }
        )

        # Parse implementation plan
        implementation_plan = json.loads(response.content)

        state["implementation_plan"] = implementation_plan
        state["status"] = "generating"
        state["messages"].append(
            SystemMessage(
                content=f"Implementation plan created with {len(implementation_plan.get('files_to_create', []))} files to create and {len(implementation_plan.get('files_to_modify', []))} files to modify."
            )
        )

        print(
            f"[Code Agent] Implementation plan: {len(implementation_plan.get('implementation_strategy', []))} steps"
        )

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to analyze requirements: {e!s}"
        print(f"[Code Agent] Error: {state['error']}")

    return state


def generate_code_node(state: CodeAgentState) -> CodeAgentState:
    """Generate code based on requirements and implementation plan"""
    print(f"[Code Agent] Generating code (iteration {state['iteration']})")

    try:
        requirements = state["requirements"]
        implementation_plan = state["implementation_plan"]
        generated_code = {}

        # Generate code for each file
        for file_info in implementation_plan.get("files_to_create", []):
            file_path = file_info["path"]
            description = file_info["description"]

            # Get existing code context if file exists
            existing_code = ""
            try:
                existing_code = get_file_contents.invoke({"file_path": file_path, "branch": "main"})
            except:
                pass

            # Generate code
            chain = CODE_GENERATION_PROMPT | get_coding_llm()
            response = chain.invoke(
                {
                    "task_description": f"Create {file_path}: {description}",
                    "implementation_plan": json.dumps(implementation_plan, indent=2),
                    "existing_code": existing_code or "// No existing code",
                }
            )

            # Extract code from response
            code_content = response.content
            if "```python" in code_content:
                code_content = code_content.split("```python")[1].split("```")[0].strip()
            elif "```" in code_content:
                code_content = code_content.split("```")[1].split("```")[0].strip()

            generated_code[file_path] = code_content

        # Generate modifications for existing files
        for file_info in implementation_plan.get("files_to_modify", []):
            file_path = file_info["path"]
            changes = file_info["changes"]

            existing_code = get_file_contents.invoke({"file_path": file_path, "branch": "main"})

            chain = CODE_GENERATION_PROMPT | get_coding_llm()
            response = chain.invoke(
                {
                    "task_description": f"Modify {file_path}: {changes}",
                    "implementation_plan": json.dumps(implementation_plan, indent=2),
                    "existing_code": existing_code,
                }
            )

            code_content = response.content
            if "```python" in code_content:
                code_content = code_content.split("```python")[1].split("```")[0].strip()
            elif "```" in code_content:
                code_content = code_content.split("```")[1].split("```")[0].strip()

            generated_code[file_path] = code_content

        state["generated_code"] = generated_code
        state["status"] = "validating"
        state["messages"].append(
            SystemMessage(content=f"Generated code for {len(generated_code)} files")
        )

        print(f"[Code Agent] Generated code for {len(generated_code)} files")

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to generate code: {e!s}"
        print(f"[Code Agent] Error: {state['error']}")

    return state


def validate_code_node(state: CodeAgentState) -> CodeAgentState:
    """Validate generated code"""
    print("[Code Agent] Validating generated code")

    try:
        # Join all generated code for validation
        all_code = "\n\n".join(
            [f"# {path}\n{code}" for path, code in state["generated_code"].items()]
        )

        chain = CODE_VALIDATION_PROMPT | get_review_llm()
        response = chain.invoke(
            {
                "requirements": json.dumps(state["requirements"], indent=2),
                "generated_code": all_code,
            }
        )

        validation_results = json.loads(response.content)
        state["validation_results"] = validation_results

        if validation_results.get("is_valid", False):
            state["status"] = "pr"
            print("[Code Agent] Code validation passed")
        else:
            print(
                f"[Code Agent] Code validation found {len(validation_results.get('issues', []))} issues"
            )
            # For now, proceed to PR anyway - reviewer will catch issues
            state["status"] = "pr"

    except Exception as e:
        print(f"[Code Agent] Validation warning: {e!s}")
        # Continue despite validation errors
        state["status"] = "pr"

    return state


def create_pr_node(state: CodeAgentState) -> CodeAgentState:
    """Create Pull Request with generated code"""
    print(f"[Code Agent] Creating PR for branch '{state['branch_name']}'")

    try:
        # Create branch
        branch_result = create_branch.invoke(
            {"branch_name": state["branch_name"], "source_branch": "main"}
        )
        print(f"[Code Agent] {branch_result}")

        # Commit files
        for file_path, content in state["generated_code"].items():
            commit_msg = (
                f"feat: implement {state['requirements'].get('title', 'feature')} - {file_path}"
            )
            update_file.invoke(
                {
                    "file_path": file_path,
                    "content": content,
                    "commit_message": commit_msg,
                    "branch": state["branch_name"],
                }
            )

        # Create PR
        pr_title = f"[Agent] {state['requirements'].get('title', 'Implementation')}"
        pr_body = f"""## Automated Implementation by Code Agent

### Issue
- **Issue #{state["issue_number"]}**

### Requirements
{json.dumps(state["requirements"], indent=2)}

### Implementation Plan
{json.dumps(state["implementation_plan"], indent=2)}

### Files Changed
{", ".join(state["generated_code"].keys())}

### Validation
{json.dumps(state.get("validation_results", {}), indent=2)}

---

This PR was created automatically by the Code Agent. Review and merge if approved.
"""

        pr_result = create_pr.invoke(
            {
                "branch_name": state["branch_name"],
                "title": pr_title,
                "body": pr_body,
                "base_branch": "main",
            }
        )

        state["pr_url"] = pr_result
        state["status"] = "done"
        print(f"[Code Agent] {pr_result}")

    except Exception as e:
        state["status"] = "error"
        state["error"] = f"Failed to create PR: {e!s}"
        print(f"[Code Agent] Error: {state['error']}")

    return state


def should_continue(state: CodeAgentState) -> Literal["continue", "end"]:
    """Determine if workflow should continue"""
    if state["status"] == "error":
        return "end"
    if state["status"] == "done":
        return "end"
    return "continue"


def create_code_agent_graph() -> StateGraph:
    """Create the Code Agent LangGraph workflow"""

    # Define workflow
    workflow = StateGraph(CodeAgentState)

    # Add nodes
    workflow.add_node("parse_issue", parse_issue_node)
    workflow.add_node("analyze_requirements", analyze_requirements_node)
    workflow.add_node("generate_code", generate_code_node)
    workflow.add_node("validate_code", validate_code_node)
    workflow.add_node("create_pr", create_pr_node)

    # Set entry point
    workflow.set_entry_point("parse_issue")

    # Add edges
    workflow.add_conditional_edges(
        "parse_issue",
        should_continue,
        {
            "continue": "analyze_requirements",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "analyze_requirements",
        should_continue,
        {
            "continue": "generate_code",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "generate_code",
        should_continue,
        {
            "continue": "validate_code",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "validate_code",
        should_continue,
        {
            "continue": "create_pr",
            "end": END,
        },
    )
    workflow.add_edge("create_pr", END)

    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


async def run_code_agent(
    issue_number: int,
    branch_name: str | None = None,
    max_iterations: int = 5,
) -> dict[str, Any]:
    """
    Run the Code Agent for a given issue.

    Args:
        issue_number: GitHub issue number
        branch_name: Branch name for changes (auto-generated if None)
        max_iterations: Maximum iteration limit

    Returns:
        Dictionary with execution results
    """
    if branch_name is None:
        branch_name = f"agent/issue-{issue_number}"

    # Initialize state
    initial_state: CodeAgentState = {
        "issue_number": issue_number,
        "branch_name": branch_name,
        "issue": "",
        "requirements": {},
        "implementation_plan": {},
        "current_code": {},
        "generated_code": {},
        "validation_results": {},
        "pr_url": "",
        "pr_number": 0,
        "feedback": [],
        "iteration": 1,
        "max_iterations": max_iterations,
        "status": "parsing",
        "error": None,
        "messages": [],
    }

    # Create and run graph
    graph = create_code_agent_graph()

    config = RunnableConfig(configurable={"thread_id": f"code-agent-issue-{issue_number}"})

    try:
        result = await graph.ainvoke(initial_state, config)

        return {
            "success": result["status"] == "done",
            "status": result["status"],
            "pr_url": result.get("pr_url", ""),
            "requirements": result.get("requirements", {}),
            "files_generated": list(result.get("generated_code", {}).keys()),
            "error": result.get("error"),
        }

    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "error": str(e),
        }


# Import for validation
from app.core.llm.openrouter import get_review_llm
