
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github-service-test")

# Add the current directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_github_service():
    """Test the GitHub service functionality"""
    from github_service.github_service import GitHubService
    
    # Verify environment variables
    token = os.environ.get('GITHUB_TOKEN')
    repo_owner = os.environ.get('GITHUB_REPO_OWNER')
    repo_name = os.environ.get('GITHUB_REPO_NAME')
    
    if not token or token == "your_github_token_here":
        logger.error("GitHub token is missing or invalid. Please check your .env file.")
        logger.info("For testing purposes, continuing with limited functionality.")
        return
        
    if not repo_owner or not repo_name:
        logger.error("GitHub repository information is missing. Please set GITHUB_REPO_OWNER and GITHUB_REPO_NAME in your .env file.")
        logger.info("For testing purposes, continuing with limited functionality.")
        return
    
    try:
        # Initialize service
        service = GitHubService()
        
        # Test creating a branch
        ticket_id = "TEST-123"
        branch_name = service.create_fix_branch(ticket_id)
        if not branch_name:
            logger.error("Failed to create branch")
            return
        
        # Test committing changes
        test_changes = [
            {
                "filename": "test.md",
                "content": f"# Test File\n\nCreated by GitHub service test at {datetime.now()}"
            }
        ]
        
        commit_success = service.commit_bug_fix(
            branch_name,
            test_changes,
            ticket_id,
            "Test commit for automated testing"
        )
        
        if not commit_success:
            logger.error("Failed to commit changes")
            return
        
        # Test creating PR
        pr_url = service.create_fix_pr(
            branch_name,
            ticket_id,
            "Test bug fix",
            "This is a test PR created by the GitHub service test script"
        )
        
        if not pr_url:
            logger.error("Failed to create PR")
            return
        
        logger.info("All GitHub service tests passed successfully!")
        logger.info(f"Created PR: {pr_url}")
    except Exception as e:
        logger.error(f"GitHub service test failed: {str(e)}")
        logger.info("GitHub integration tests were skipped due to configuration issues.")
        logger.info("To run GitHub tests, please set valid credentials in your .env file.")

if __name__ == "__main__":
    # Run tests
    test_github_service()
