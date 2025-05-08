
import os
import sys
import logging
from typing import Dict, Any, Optional, List, Tuple

class EnvironmentValidator:
    """Centralized environment variable loader and validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("env-validator")
        self.variables = {}
        self._load_variables()
    
    def _load_variables(self):
        """Load all environment variables into a dictionary"""
        # GitHub configuration
        self.variables["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN")
        self.variables["GITHUB_REPO_OWNER"] = os.getenv("GITHUB_REPO_OWNER")
        self.variables["GITHUB_REPO_NAME"] = os.getenv("GITHUB_REPO_NAME")
        self.variables["GITHUB_DEFAULT_BRANCH"] = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
        self.variables["GITHUB_USE_DEFAULT_BRANCH_ONLY"] = os.getenv("GITHUB_USE_DEFAULT_BRANCH_ONLY", "False").lower() == "true"
        
        # JIRA configuration
        self.variables["JIRA_API_TOKEN"] = os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_TOKEN")
        self.variables["JIRA_USERNAME"] = os.getenv("JIRA_USERNAME") or os.getenv("JIRA_USER")
        self.variables["JIRA_URL"] = os.getenv("JIRA_URL")
        self.variables["JIRA_PROJECT_KEY"] = os.getenv("JIRA_PROJECT_KEY", "")
        self.variables["JIRA_POLL_INTERVAL"] = int(os.getenv("JIRA_POLL_INTERVAL", "30"))
        
        # OpenAI configuration
        self.variables["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        self.variables["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # Application configuration
        self.variables["MAX_RETRIES"] = int(os.getenv("MAX_RETRIES", "4"))
        self.variables["RETRY_DELAY_SECONDS"] = int(os.getenv("RETRY_DELAY_SECONDS", "5"))
        self.variables["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
    
    def validate_environment(self, required_groups: List[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate that all required environment variables are set.
        
        Args:
            required_groups: List of groups to validate ('github', 'jira', 'openai', 'all')
            
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        missing_vars = []
        groups_to_check = required_groups or ["all"]
        
        # Define required variables by group
        requirements = {
            "github": ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"],
            "jira": ["JIRA_API_TOKEN", "JIRA_USERNAME", "JIRA_URL"],
            "openai": ["OPENAI_API_KEY"]
        }
        
        # Check all groups if 'all' is specified
        if "all" in groups_to_check:
            groups_to_check = ["github", "jira", "openai"]
        
        # Validate each group
        for group in groups_to_check:
            if group not in requirements:
                self.logger.warning(f"Unknown validation group: {group}")
                continue
                
            for var in requirements[group]:
                if not self.variables.get(var):
                    missing_vars.append(var)
        
        is_valid = len(missing_vars) == 0
        
        if not is_valid:
            self.logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        else:
            self.logger.info("All required environment variables are set")
        
        return is_valid, missing_vars
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key with optional default"""
        return self.variables.get(key, default)
    
    def get_github_config(self) -> Dict[str, Any]:
        """Get all GitHub configuration as a dictionary"""
        return {
            "token": self.variables.get("GITHUB_TOKEN"),
            "owner": self.variables.get("GITHUB_REPO_OWNER"),
            "repo": self.variables.get("GITHUB_REPO_NAME"),
            "default_branch": self.variables.get("GITHUB_DEFAULT_BRANCH"),
            "use_default_branch_only": self.variables.get("GITHUB_USE_DEFAULT_BRANCH_ONLY", False)
        }
    
    def get_jira_config(self) -> Dict[str, Any]:
        """Get all JIRA configuration as a dictionary"""
        return {
            "token": self.variables.get("JIRA_API_TOKEN"),
            "username": self.variables.get("JIRA_USERNAME"),
            "url": self.variables.get("JIRA_URL"),
            "project_key": self.variables.get("JIRA_PROJECT_KEY"),
            "poll_interval": self.variables.get("JIRA_POLL_INTERVAL")
        }

# Singleton instance
env_validator = EnvironmentValidator()

def get_config() -> EnvironmentValidator:
    """Get the singleton environment validator instance"""
    return env_validator

def validate_required_config(groups: List[str] = None) -> bool:
    """Validate that all required environment variables for specified groups are set"""
    valid, missing = env_validator.validate_environment(groups)
    if not valid:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Please check your .env file and ensure all required variables are set.")
        return False
    return True

# Convenience function for direct access to environment variables
def get_env(key: str, default: Any = None) -> Any:
    """Get a configuration value by key with optional default"""
    return env_validator.get(key, default)