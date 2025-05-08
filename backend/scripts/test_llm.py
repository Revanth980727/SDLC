import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from github_service.github_service import GitHubService
from config.env_loader import get_config
from agent_framework.developer_agent import DeveloperAgent

logging.basicConfig(level=logging.INFO)

def test_llm_patch_line_update():
    ticket = {
        "ticket_id": "SCRUM-2",
        "title": "Fix import error",
        "description": "GraphRAG.py fails with an ImportError due to a malformed import statement for networkx",
        "status": "To Do"
    }

    config = get_config()  # Correct way to get dict-like config

    github = GitHubService(
    github_token=config.get("GITHUB_TOKEN"),
    repo_owner=config.get("GITHUB_REPO_OWNER"),
    repo_name=config.get("GITHUB_REPO_NAME"),
    default_branch=config.get("GITHUB_DEFAULT_BRANCH")
    )

    agent = DeveloperAgent()
    result = agent.run(ticket)
    print("Developer Agent Result:", result)

    if not result.get("patched_code"):
        print("No patch returned by LLM.")
        return

    created, branch_name = github.create_fix_branch(ticket["ticket_id"])
    print("Branch created:", created, "Branch:", branch_name)

    changes = [{"filename": path, "content": content} for path, content in result["patched_code"].items()]
    commit_message = result.get("bug_summary", "Patch import error in GraphRAG.py")
    committed = github.commit_bug_fix(branch_name, changes, ticket["ticket_id"], commit_message)
    print("Changes committed:", committed)

    if not committed:
        print("Failed to commit. Exiting.")
        return

    pr_url = github.create_fix_pr(branch_name, ticket["ticket_id"], commit_message, "Auto-generated fix by DeveloperAgent.")
    print("Pull request URL:", pr_url)

if __name__ == "__main__":
    test_llm_patch_line_update()
