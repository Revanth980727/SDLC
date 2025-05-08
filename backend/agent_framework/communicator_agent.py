
import os
import logging
import json
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("communicator-agent")

class CommunicatorAgent:
    """Agent responsible for communicating results to external systems (JIRA, GitHub, etc.)"""
    
    def __init__(self):
        logger.info("Initializing CommunicatorAgent")
        # Get configuration from environment
        self.github_token = os.environ.get("GITHUB_TOKEN", "")
        self.jira_token = os.environ.get("JIRA_TOKEN", "")
        self.repo_url = os.environ.get("REPO_URL", "")
        
        # Check for git installation
        self._check_git_available()
    
    def _check_git_available(self):
        """Check if git is available in the system"""
        try:
            import subprocess
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            logger.info("Git is available")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"Git is not available: {str(e)}")
    
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run method compatible with the agent framework
        This is the main entry point for the agent
        """
        logger.info("CommunicatorAgent.run() called")
        return self.process(input_data)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming data and communicate results"""
        ticket_id = input_data.get("ticket_id", "unknown")
        logger.info(f"Processing communication request for ticket {ticket_id}")
        
        # Log input data for debugging
        logger.info(f"Communication input: {json.dumps(input_data, default=str)[:500]}...")
        
        # Create result with default values
        result = {
            "ticket_id": ticket_id,
            "communications_success": False,
            "pr_created": False,
            "jira_updated": False,
            "timestamp": time.time()
        }
        
        # Process based on update type
        update_type = input_data.get("update_type", "progress")
        
        if update_type == "early_escalation":
            logger.info(f"Processing early escalation for ticket {ticket_id}")
            result["early_escalation"] = True
            result["escalation_reason"] = input_data.get("escalation_reason", "Unknown reason")
            # Handle the early escalation
            try:
                self._update_jira_early_escalation(ticket_id, input_data)
                result["jira_updated"] = True
            except Exception as e:
                logger.error(f"Error updating JIRA for early escalation: {str(e)}")
                result["error"] = str(e)
        elif update_type == "progress":
            logger.info(f"Processing progress update for ticket {ticket_id}")
            # Handle the progress update
            try:
                self._update_jira_progress(ticket_id, input_data)
                result["jira_updated"] = True
            except Exception as e:
                logger.error(f"Error updating JIRA with progress: {str(e)}")
                result["error"] = str(e)
        else:
            # Default case - complete workflow
            test_passed = input_data.get("success", False)
            
            if test_passed:
                logger.info(f"Creating PR for successful fix for ticket {ticket_id}")
                try:
                    pr_url = self._create_github_pr(ticket_id, input_data)
                    result["pr_url"] = pr_url
                    result["pr_created"] = True
                except Exception as e:
                    logger.error(f"Error creating GitHub PR: {str(e)}")
                    result["pr_error"] = str(e)
            
            # Update JIRA
            try:
                self._update_jira_final(ticket_id, test_passed, result.get("pr_url"))
                result["jira_updated"] = True
            except Exception as e:
                logger.error(f"Error updating JIRA with final result: {str(e)}")
                result["jira_error"] = str(e)
        
        # Set overall success
        result["communications_success"] = result.get("jira_updated", False)
        
        logger.info(f"Communication completed for ticket {ticket_id}")
        return result
    
    def _create_github_pr(self, ticket_id: str, input_data: Dict[str, Any]) -> Optional[str]:
        """Create a GitHub PR with the fix"""
        logger.info(f"Would create GitHub PR for ticket {ticket_id}")
        # Simplified implementation for demo purposes
        return f"https://github.com/example/repo/pull/{ticket_id}"
    
    def _update_jira_early_escalation(self, ticket_id: str, input_data: Dict[str, Any]) -> None:
        """Update JIRA with early escalation information"""
        logger.info(f"Would update JIRA with early escalation for ticket {ticket_id}")
        # Simplified implementation for demo purposes
        escalation_reason = input_data.get("escalation_reason", "Unknown reason")
        attempt = input_data.get("attempt", 0)
        max_retries = input_data.get("max_retries", 0)
        logger.info(f"Escalation reason: {escalation_reason}")
        logger.info(f"Attempt: {attempt}/{max_retries}")
    
    def _update_jira_progress(self, ticket_id: str, input_data: Dict[str, Any]) -> None:
        """Update JIRA with progress information"""
        logger.info(f"Would update JIRA with progress for ticket {ticket_id}")
        # Simplified implementation for demo purposes
        success = input_data.get("success", False)
        attempt = input_data.get("attempt", 0)
        max_retries = input_data.get("max_retries", 0)
        failure_summary = input_data.get("failure_summary", "")
        logger.info(f"Success: {success}")
        logger.info(f"Attempt: {attempt}/{max_retries}")
        if not success and failure_summary:
            logger.info(f"Failure summary: {failure_summary}")
    
    def _update_jira_final(self, ticket_id: str, test_passed: bool, pr_url: Optional[str] = None) -> None:
        """Update JIRA with final result"""
        logger.info(f"Would update JIRA with final result for ticket {ticket_id}")
        # Simplified implementation for demo purposes
        if test_passed:
            logger.info(f"Tests passed, PR created: {pr_url}")
        else:
            logger.info("Tests failed, escalating to human")