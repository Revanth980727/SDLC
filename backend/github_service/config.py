
import os
import logging
import sys
from dotenv import load_dotenv

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github-config")

# Load environment variables from root .env file
load_dotenv()

# GitHub configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')
GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME')
GITHUB_DEFAULT_BRANCH = os.getenv('GITHUB_DEFAULT_BRANCH', 'main')

def verify_config():
    """Verify that all required environment variables are set."""
    required_vars = {
        'GITHUB_TOKEN': GITHUB_TOKEN,
        'GITHUB_REPO_OWNER': GITHUB_REPO_OWNER,
        'GITHUB_REPO_NAME': GITHUB_REPO_NAME
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        error_msg = f"Missing required GitHub environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        logger.error("Please check your .env file and ensure all required variables are set.")
        return False
        
    # Check if token is a placeholder
    if GITHUB_TOKEN == "your_github_token_here":
        logger.error("GITHUB_TOKEN contains a placeholder value. Please set a valid GitHub token in your .env file.")
        return False

    logger.info("GitHub configuration validated successfully")
    return True
