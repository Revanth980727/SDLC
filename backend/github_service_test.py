
#!/usr/bin/env python3
import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("github-service-test")

# Make sure we can import from the backend directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import our GitHub utilities
from github_utils import (
    authenticate_github, 
    get_repo, 
    create_branch, 
    commit_changes,
    create_pull_request,
    get_branch_commit_history
)
from env import verify_github_repo_settings

def main():
    """Test the GitHub service functionality"""
    load_dotenv()
    
    # Verify GitHub settings
    github_configured, message = verify_github_repo_settings()
    logger.info(message)
    if not github_configured:
        logger.error("GitHub is not properly configured. Check your .env file.")
        return
    
    # Test the authentication
    github_client = authenticate_github()
    if not github_client:
        logger.error("GitHub authentication failed.")
        return
    
    # Determine the repository name based on environment variables
    repo_owner = os.environ.get("GITHUB_REPO_OWNER")
    repo_name = os.environ.get("GITHUB_REPO_NAME")
    full_repo_name = f"{repo_owner}/{repo_name}" if repo_owner and repo_name else None
    
    if not full_repo_name:
        logger.error("Cannot determine repository name. Set GITHUB_REPO_OWNER and GITHUB_REPO_NAME.")
        return
    
    # Test creating a branch
    test_ticket_id = "TEST-123"
    branch_name = create_branch(full_repo_name, test_ticket_id)
    if not branch_name:
        logger.error("Failed to create branch.")
        return
    
    # Test committing changes
    test_file_changes = [
        {
            "filename": "README.md",
            "content": "# Test Repository\n\nThis is a test commit from the GitHub service."
        },
        {
            "filename": "test_file.txt",
            "content": f"This is a test file created by the GitHub service at {datetime.now().isoformat()}."
        }
    ]
    
    commit_success = commit_changes(
        full_repo_name, 
        branch_name, 
        test_file_changes,
        f"Test commit for {test_ticket_id}"
    )
    
    if not commit_success:
        logger.error("Failed to commit changes.")
        return
    
    # Test creating a PR
    pr_url = create_pull_request(
        full_repo_name,
        branch_name,
        test_ticket_id,
        "Test PR for GitHub service",
        "This is a test PR created by the GitHub service test script."
    )
    
    if not pr_url:
        logger.error("Failed to create PR.")
        return
    
    logger.info(f"Successfully created PR: {pr_url}")
    
    # Test getting branch history
    commits = get_branch_commit_history(full_repo_name, branch_name)
    logger.info(f"Branch {branch_name} has {len(commits)} commits:")
    for i, commit in enumerate(commits):
        logger.info(f"{i+1}. {commit['message']} ({commit['author']} on {commit['date']})")

if __name__ == "__main__":
    main()
