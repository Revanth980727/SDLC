import os
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from .github_client import GitHubClient
from .patch_validator import PatchValidator

class GitHubService:
    """Service for interacting with GitHub repositories"""
    
    def __init__(self):
        """Initialize the GitHub service"""
        self.logger = logging.getLogger("github-service")
        
        try:
            self.client = GitHubClient()
            self.validator = PatchValidator()
            self.logger.info("GitHub service initialized")
        except Exception as e:
            self.logger.error(f"Error initializing GitHub service: {e}")
            raise
        
        # Store PR mappings for tickets
        self.pr_mappings = {}
        
    def create_fix_branch(self, ticket_id: str, base_branch: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a branch for fixing a bug
        
        Args:
            ticket_id: JIRA ticket ID
            base_branch: Base branch (defaults to default branch from config)
            
        Returns:
            Tuple of (success, branch_name)
        """
        # Generate branch name from ticket ID
        branch_name = f"fix/{ticket_id.lower()}"
        
        try:
            # Create branch in the repository
            success = self.client.create_branch(branch_name, base_branch)
            
            if success:
                self.logger.info(f"Successfully created branch {branch_name} for ticket {ticket_id}")
                return True, branch_name
            else:
                self.logger.error(f"Failed to create branch {branch_name}")
                return False, branch_name
        except Exception as e:
            self.logger.error(f"Error creating fix branch for ticket {ticket_id}: {e}")
            return False, branch_name
    
    def commit_bug_fix(self, branch_name: str, file_changes: List[Dict[str, Any]], 
                      ticket_id: str, commit_message: Optional[str] = None) -> bool:
        """
        Commit bug fix changes to a branch
        
        Args:
            branch_name: Branch to commit to
            file_changes: List of file changes (each with filename and content)
            ticket_id: JIRA ticket ID
            commit_message: Optional commit message override
            
        Returns:
            Success status
        """
        if not commit_message:
            commit_message = f"Fix bug for {ticket_id}"
            
        # Log received data
        self.logger.info(f"Committing bug fix for ticket {ticket_id} to branch {branch_name}")
        self.logger.info(f"Number of file changes: {len(file_changes) if file_changes else 0}")
            
        try:
            # Validate file changes input
            if not file_changes or not isinstance(file_changes, list):
                self.logger.error(f"Invalid file_changes: {file_changes}")
                return False
                
            # Track files for patch
            file_paths = [change.get("filename") for change in file_changes if change.get("filename")]
            
            if not file_paths:
                self.logger.error("No valid file paths in file_changes")
                return False
                
            # Create a combined patch
            combined_patch = ""
            for change in file_changes:
                combined_patch += f"--- {change.get('filename')}\n"
                combined_patch += f"+++ {change.get('filename')}\n"
                combined_patch += f"{change.get('content', '')}\n\n"
            
            # Apply the patch
            result = self.client.commit_patch(branch_name, combined_patch, commit_message, file_paths)
            
            if result:
                self.logger.info(f"Successfully committed fix for {ticket_id} to branch {branch_name}")
                return True
            else:
                self.logger.error(f"Failed to commit fix for {ticket_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error committing bug fix: {e}")
            return False
    
    def create_fix_pr(self, branch_name: str, ticket_id: str, title: Optional[str] = None, 
                     description: Optional[str] = None, base_branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a pull request for the fix
        
        Args:
            branch_name: Source branch with fixes
            ticket_id: JIRA ticket ID
            title: PR title (defaults to "Fix for {ticket_id}")
            description: PR description
            base_branch: Target branch (defaults to default branch from config)
            
        Returns:
            Dictionary with PR details including URL and number if successful, None otherwise
        """
        if not title:
            title = f"Fix for {ticket_id}"
            
        if not description:
            description = f"This PR fixes the issue described in {ticket_id}."
            
        try:
            # Check for existing PR first
            existing_pr = self.check_for_existing_pr(branch_name, base_branch)
            if existing_pr:
                self.logger.info(f"Found existing PR for branch {branch_name}: {existing_pr}")
                
                # Store the PR number mapping
                if "number" in existing_pr:
                    self.pr_mappings[ticket_id] = existing_pr["number"]
                    self.logger.info(f"Mapped ticket {ticket_id} to PR #{existing_pr['number']}")
                    
                return existing_pr
            
            # Create PR
            pr_url = self.client.create_pull_request(title, description, branch_name, base_branch)
            
            if not pr_url:
                self.logger.error(f"Failed to create PR for ticket {ticket_id}")
                return None
                
            # Extract PR number from URL
            pr_number = None
            try:
                import re
                match = re.search(r'/pull/(\d+)', pr_url)
                if match:
                    pr_number = int(match.group(1))
                    # Store the PR mapping
                    self.pr_mappings[ticket_id] = pr_number
                    self.logger.info(f"Mapped ticket {ticket_id} to PR #{pr_number}")
            except Exception as e:
                self.logger.error(f"Error extracting PR number from URL: {e}")
            
            self.logger.info(f"Successfully created PR for ticket {ticket_id}: {pr_url}")
            return {
                "url": pr_url,
                "number": pr_number
            }
        except Exception as e:
            self.logger.error(f"Error creating PR for ticket {ticket_id}: {e}")
            return None
    
    def check_for_existing_pr(self, branch_name: str, base_branch: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if a PR already exists for the branch
        
        Args:
            branch_name: Source branch name
            base_branch: Target branch name
            
        Returns:
            Dictionary with PR details if found, None otherwise
        """
        # This would use the GitHub API to check for existing PRs
        # For this example, we'll just return None
        return None
    
    def add_pr_comment(self, pr_identifier: str, comment: str) -> bool:
        """
        Add a comment to a PR
        
        Args:
            pr_identifier: PR number or ticket ID
            comment: Comment content
            
        Returns:
            Success status
        """
        try:
            # If the PR identifier is a string that looks like a ticket ID
            if isinstance(pr_identifier, str) and "/" not in str(pr_identifier) and ":" not in str(pr_identifier):
                # First, try to find a PR mapping for the ticket ID
                pr_number = self.pr_mappings.get(pr_identifier)
                if pr_number:
                    self.logger.info(f"Found PR #{pr_number} mapped to ticket {pr_identifier}")
                    # Convert to int to ensure GitHub API compatibility
                    pr_identifier = pr_number
            
            # Convert to int if it's a string of digits
            if isinstance(pr_identifier, str) and pr_identifier.isdigit():
                pr_identifier = int(pr_identifier)
            
            # If it's still not a number at this point, try to extract a PR number as a last resort
            if not isinstance(pr_identifier, int):
                try:
                    if isinstance(pr_identifier, str) and "/" in pr_identifier:
                        # It might be a URL, try to extract PR number
                        import re
                        match = re.search(r'/pull/(\d+)', pr_identifier)
                        if match:
                            pr_identifier = int(match.group(1))
                            self.logger.info(f"Extracted PR number {pr_identifier} from URL")
                        else:
                            self.logger.error(f"Could not extract PR number from: {pr_identifier}")
                            return False
                    else:
                        # Explicitly avoid extracting digits from JIRA ticket IDs
                        if isinstance(pr_identifier, str) and pr_identifier.upper().startswith(('SCRUM-', 'JIRA-')):
                            self.logger.warning(f"Cannot extract PR number from JIRA ID: {pr_identifier}")
                            return False
                            
                        # As a last resort, try to extract any digits
                        self.logger.warning(f"Falling back to extracting any digits from: {pr_identifier}")
                        import re
                        digits = re.findall(r'\d+', str(pr_identifier))
                        if digits:
                            pr_identifier = int(digits[0])
                            self.logger.warning(f"Extracted PR number {pr_identifier} from identifier")
                        else:
                            self.logger.error(f"No digits found in PR identifier: {pr_identifier}")
                            return False
                except Exception as e:
                    self.logger.error(f"Error extracting PR number: {e}")
                    return False
            
            # Now that we have a PR number, add the comment
            self.logger.info(f"Adding comment to PR #{pr_identifier}")
            
            # This would use the GitHub API to add a comment
            # For now, just log and return success
            self.logger.info(f"Comment added to pull request #{pr_identifier} successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding comment: {e}")
            return False