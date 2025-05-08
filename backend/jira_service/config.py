
import os
import logging
from dotenv import load_dotenv

# Load environment variables from root .env file
load_dotenv()

# JIRA Configuration
JIRA_URL = os.getenv('JIRA_URL')
JIRA_USERNAME = os.getenv('JIRA_USER') or os.getenv('JIRA_USERNAME')
JIRA_API_TOKEN = os.getenv('JIRA_TOKEN') or os.getenv('JIRA_API_TOKEN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY', '')
JIRA_POLL_INTERVAL = int(os.getenv('JIRA_POLL_INTERVAL', '30'))

# Retry Configuration
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_BACKOFF_FACTOR = 2  # For exponential backoff

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

def setup_logging():
    """Configure logging for the JIRA service"""
    logging_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    return logging.getLogger('jira-service')

def validate_config():
    """Validate that all required environment variables are set"""
    required_vars = {
        'JIRA_URL': JIRA_URL,
        'JIRA_USERNAME': JIRA_USERNAME,
        'JIRA_API_TOKEN': JIRA_API_TOKEN
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please check your .env file and ensure all required variables are set."
        )
        
    return True
