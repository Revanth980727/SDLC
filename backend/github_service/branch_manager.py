
import logging
from typing import Optional, Tuple, Dict, Any
import re
import os
from datetime import datetime

# Import the environment validator
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.env_loader import get_config, get_env

class BranchManager:
    """Manager for Git branch operations with standardized naming and error handling"""
    
    def __init__(self, github_client=None):
        """Initialize with optional GitHub client"""
        self.logger = logging.getLogger("branch-manager")
        self.github_client = github_client
        self.env = get_config()
    
    def set_github_client(self, github_client):
        """Set the GitHub client instance"""
        self.github_client = github_client
    
    def _sanitize_branch_name(self, name: str) -> str:
        """
        Create a valid Git branch name from arbitrary string
        
        Args:
            name: Input string to sanitize
            
        Returns:
            Valid Git branch name
        """
        # Replace spaces and special chars with hyphens
        sanitized = re.sub(r'[^\w\-]', '-', name)
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        # Convert to lowercase
        sanitized = sanitized.lower()
        # Ensure it's not too long (Git has a 255 byte limit)
        if len(sanitized) > 60:  # Conservative limit
            sanitized = sanitized[:60]
        return sanitized
    
    def create_bugfix_branch(self, ticket_id: str, bug_description: str = None) -> Tuple[bool, str]:
        """
        Create a standardized branch name for a bugfix
        
        Args:
            ticket_id: JIRA ticket ID
            bug_description: Optional short description of the bug
            
        Returns:
            Tuple of (success, branch_name)
        """
        if not self.github_client:
            self.logger.error("GitHub client not set")
            return False, ""
        
        # Get default branch from environment
        default_branch = get_env("GITHUB_DEFAULT_BRANCH", "main")
        
        # Create branch name with format: fix/{ticket-id}-{short-description}
        branch_prefix = "fix"
        
        if bug_description:
            # Sanitize and include description in branch name
            desc_part = self._sanitize_branch_name(bug_description)
            # Only include first few words
            desc_words = desc_part.split('-')[:3]
            desc_part = '-'.join(desc_words)
            branch_name = f"{branch_prefix}/{ticket_id.upper()}-{desc_part}"
        else:
            # Just use ticket ID
            branch_name = f"{branch_prefix}/{ticket_id.upper()}"
        
        # Check if the branch already exists first
        if self.github_client.check_branch_exists(branch_name):
            self.logger.info(f"Branch {branch_name} already exists, reusing it")
            return True, branch_name
            
        # Create the branch
        success = self.github_client.create_branch(branch_name, default_branch)
        
        if success:
            self.logger.info(f"Created branch {branch_name} from {default_branch}")
            return True, branch_name
        else:
            self.logger.error(f"Failed to create branch {branch_name}")
            return False, ""
    
    def checkout_branch(self, ticket_id: str, bug_summary: str = None) -> Tuple[bool, str]:
        """
        Create and checkout a branch for fixing a bug
        
        This method creates a branch if it doesn't exist, or uses an existing branch
        with proper fallback handling.
        
        Args:
            ticket_id: JIRA ticket ID
            bug_summary: Optional bug summary for branch name
            
        Returns:
            Tuple of (success, branch_name)
        """
        # Try using the ticket ID and summary
        if bug_summary:
            success, branch_name = self.create_bugfix_branch(ticket_id, bug_summary)
            if success:
                return True, branch_name
                
            # If failed with summary, try just the ticket ID
            self.logger.info("Failed to create branch with summary, trying with just ticket ID")
        
        # Try using just the ticket ID
        success, branch_name = self.create_bugfix_branch(ticket_id)
        if success:
            return True, branch_name
        
        # Ultimate fallback: use ticket ID with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        fallback_branch = f"fix/{ticket_id.upper()}-{timestamp}"
        
        success = self.github_client.create_branch(fallback_branch)
        if success:
            self.logger.info(f"Created fallback branch {fallback_branch}")
            return True, fallback_branch
        
        self.logger.error("All attempts to create branch failed")
        return False, ""
    
    def find_existing_branch(self, ticket_id: str) -> Optional[str]:
        """
        Find existing branch for a ticket
        
        Args:
            ticket_id: JIRA ticket ID
            
        Returns:
            Branch name if found, None otherwise
        """
        if not self.github_client:
            self.logger.error("GitHub client not set")
            return None
        
        # Common branch prefixes to check
        prefixes = ["fix/", "bugfix/", "feature/", "hotfix/"]
        
        for prefix in prefixes:
            branch_name = f"{prefix}{ticket_id.upper()}"
            if self.github_client.check_branch_exists(branch_name):
                self.logger.info(f"Found existing branch {branch_name} for ticket {ticket_id}")
                return branch_name
                
            # Also check for branches with descriptions (truncated search)
            pattern = f"{prefix}{ticket_id.upper()}-"
            # Note: This is a simplified version - in a real implementation,
            # we would need to list all branches and filter by pattern
            # which requires more GitHub API functionality than shown here
        
        self.logger.info(f"No existing branch found for ticket {ticket_id}")
        return None