import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import logging
from backend.github_service.github_service import GitHubService
from backend.config.env_loader import get_config

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_full_github_workflow():
    # Load GitHub config
    config = get_config().get_github_config()

    # Initialize GitHubService
    github = GitHubService(
        github_token=config["token"],
        repo_owner=config["owner"],
        repo_name=config["repo"],
        default_branch=config["default_branch"]
    )

    ticket_id = "TEST-123"  # Simulate a JIRA ticket
    base_branch = config["default_branch"]

    # Step 1: Create or reuse fix branch
    created, branch_name = github.create_fix_branch(ticket_id, base_branch)
    print(f"Branch created: {created}, Branch: {branch_name}")

    # Step 2: Simulate a file change
    changes = {
        "test.md": "# Test Markdown\n\nThis is a test change from the test script.\n"
    }
    commit_message = "Test commit from test_github_workflow script"
    file_changes = [{"filename": fname, "content": content} for fname, content in changes.items()]
    committed = github.commit_bug_fix(branch_name, file_changes, ticket_id, commit_message)

    print(f"Changes committed: {committed}")

    # Step 3: Create a pull request
    if committed:
        pr_url = github.create_fix_pr(branch_name, base_branch, "Test PR", "This is a test PR created by script.")
        print(f"Pull request created: {pr_url}")
    else:
        print("Skipping PR creation due to commit failure.")

if __name__ == "__main__":
    test_full_github_workflow()
