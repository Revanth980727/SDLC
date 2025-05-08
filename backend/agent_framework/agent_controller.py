
import os
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_controller")

from .planner_agent import PlannerAgent
from .developer_agent import DeveloperAgent
from .qa_agent import QAAgent
from .communicator_agent import CommunicatorAgent

class AgentController:
    """
    Controller class that orchestrates the execution of the bug fixing agents.
    Runs the agents in sequence: Planner -> Developer -> QA -> Communicator.
    """
    
    def __init__(self, max_retries: int = 4, confidence_threshold: int = 70):
        """
        Initialize the agent controller
        
        Args:
            max_retries: Maximum number of retry attempts for generating a successful fix
            confidence_threshold: Threshold below which a patch is considered low confidence
        """
        self.logger = logger
        self.max_retries = max_retries
        self.confidence_threshold = confidence_threshold
        
        # Initialize agents
        self.planner_agent = PlannerAgent()
        self.developer_agent = DeveloperAgent(max_retries=max_retries)
        self.qa_agent = QAAgent()
        self.communicator_agent = CommunicatorAgent()
        
        # Get repo path from environment
        self.repo_path = os.environ.get("REPO_PATH", "/mnt/codebase")
        
    async def process_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a JIRA ticket through the full bug fixing pipeline
        
        Args:
            ticket_data: Dictionary with ticket information with at least
                        'ticket_id', 'title', and 'description' keys
                        
        Returns:
            Dictionary with the results of the entire process
        """
        ticket_id = ticket_data.get("ticket_id", "unknown")
        self.logger.info(f"Processing ticket {ticket_id}")
        
        # Create result object to track progress and results
        result = {
            "ticket_id": ticket_id,
            "start_time": time.time(),
            "status": "started",
            "stages": {},
            "current_stage": "planning",
            "analytics": {
                "total_attempts": 0,
                "early_escalation": False,
                "escalation_reason": None,
                "confidence_scores": [],
            }
        }
        
        try:
            # Step 1: Planner Agent - Analyze the ticket and create a task plan
            self.logger.info(f"Running PlannerAgent for ticket {ticket_id}")
            result["current_stage"] = "planning"
            
            task_plan = await self._run_agent(self.planner_agent, ticket_data)
            
            # Validate planner output
            if not self._validate_planner_output(task_plan, ticket_id):
                self.logger.error(f"Invalid planner output for ticket {ticket_id}")
                result["status"] = "failed"
                result["error"] = "Invalid planner output"
                result["stages"]["planning"] = {
                    "status": "failed",
                    "output": task_plan,
                    "error": "Invalid planner output"
                }
                return result
            
            # Add ticket_id to task_plan for reference
            task_plan["ticket_id"] = ticket_id
            
            # Save task_plan to result
            result["stages"]["planning"] = {
                "status": "completed",
                "output": task_plan
            }
            
            # Step 2-4: Developer-QA loop with retries
            fix_result = await self._run_fix_loop(ticket_id, task_plan)
            
            # Add fix results to overall result
            for key, value in fix_result.items():
                result[key] = value
            
            # Final status
            result["end_time"] = time.time()
            result["duration"] = result["end_time"] - result["start_time"]
            
            self.logger.info(f"Processing ticket {ticket_id} completed with status: {result['status']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
            
            result["status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = time.time()
            result["duration"] = result["end_time"] - result["start_time"]
            
            return result
    
    def _validate_planner_output(self, task_plan: Dict[str, Any], ticket_id: str) -> bool:
        """
        Validate the planner output before proceeding
        
        Args:
            task_plan: Dictionary with planner output
            ticket_id: Ticket ID for reference
            
        Returns:
            Boolean indicating if output is valid
        """
        required_fields = ["summary", "affected_files", "affected_modules"]
        for field in required_fields:
            if field not in task_plan or not task_plan[field]:
                self.logger.error(f"Missing or empty required field in planner output: {field}")
                return False
                
        # Ensure root_cause is identified
        if "root_cause" not in task_plan or not task_plan["root_cause"]:
            self.logger.warning(f"Planner did not identify root cause for ticket {ticket_id}")
            
        return True
            
    async def _run_agent(self, agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run an agent with input data
        
        Args:
            agent: Agent instance to run
            input_data: Dictionary with input data for the agent
            
        Returns:
            Dictionary with agent output
        """
        # In a real async implementation, this would run the agent asynchronously
        # For this example, we'll run it synchronously
        return agent.process(input_data)
            
    async def _run_fix_loop(self, ticket_id: str, task_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Run the developer-QA-communicator loop with retries"""
        result = {
            "current_stage": "development",
            "status": "in_progress",
            "stages": {},
            "fix_attempts": [],
            "analytics": {
                "total_attempts": 0,
                "early_escalation": False,
                "escalation_reason": None,
                "confidence_scores": [],
            }
        }
        
        attempt = 1
        success = False
        
        # Context for tracking previous attempts
        context = {"previous_attempts": []}
        
        # Track previously seen QA failure patterns to detect repetition
        previous_failure_summary = None
        
        while attempt <= self.max_retries and not success:
            self.logger.info(f"Starting fix attempt {attempt}/{self.max_retries} for ticket {ticket_id}")
            
            attempt_result = {
                "attempt": attempt,
                "start_time": time.time()
            }
            
            # Step 2: Developer Agent - Generate code fix
            self.logger.info(f"Running DeveloperAgent for ticket {ticket_id} (attempt {attempt})")
            result["current_stage"] = "development"
            
            # Add attempt number to context
            context["attempt"] = attempt
            
            developer_input = {
                **task_plan,
                "context": context
            }
            
            patch_data = await self._run_agent(self.developer_agent, developer_input)
            
            # Save developer results
            attempt_result["development"] = {
                "status": "completed",
                "output": patch_data
            }
            
            # Get confidence score for this patch
            confidence_score = patch_data.get("confidence_score", 0)
            
            # Save confidence score to analytics
            result["analytics"]["confidence_scores"].append(confidence_score)
            attempt_result["confidence_score"] = confidence_score
            
            # Log structured output for validation
            self.logger.info(f"Developer output structure: {json.dumps({k: type(v).__name__ for k, v in patch_data.items()}, indent=2)}")
            
            # Check for valid patch_data output
            if not self._validate_developer_output(patch_data):
                self.logger.error("Invalid developer output, skipping QA and communicator stages")
                
                attempt_result["status"] = "failed"
                attempt_result["error"] = "Invalid developer output"
                
                # Add attempt to results
                attempt_result["end_time"] = time.time()
                attempt_result["duration"] = attempt_result["end_time"] - attempt_result["start_time"]
                result["fix_attempts"].append(attempt_result)
                
                # Update context for next attempt
                context["previous_attempts"].append({
                    "attempt": attempt,
                    "error": "Invalid developer output"
                })
                
                # Post JIRA update via communicator for failure
                await self._run_communicator_early_escalation(
                    ticket_id, 
                    attempt, 
                    patch_data, 
                    "Developer agent produced invalid output structure"
                )
                
                attempt += 1
                continue
            
            # Check for low confidence early escalation
            if confidence_score < self.confidence_threshold:
                self.logger.warning(f"Low confidence score ({confidence_score}%) detected, escalating early")
                
                # Update escalation details
                result["analytics"]["early_escalation"] = True
                result["analytics"]["escalation_reason"] = "low_confidence"
                attempt_result["early_escalation"] = True
                attempt_result["escalation_reason"] = "Low confidence patch"
                
                # Run communicator for early escalation
                await self._run_communicator_early_escalation(
                    ticket_id, 
                    attempt, 
                    patch_data, 
                    f"Low confidence patch ({confidence_score}%)"
                )
                
                # Add attempt to results
                attempt_result["end_time"] = time.time()
                attempt_result["duration"] = attempt_result["end_time"] - attempt_result["start_time"]
                attempt_result["success"] = False
                result["fix_attempts"].append(attempt_result)
                
                # Update final status
                result["status"] = "escalated"
                result["current_stage"] = "escalated"
                result["analytics"]["total_attempts"] = attempt
                
                return result
            
            # Apply patch to local repo - should have already been done by developer agent
            # but we keep this check for legacy reasons
            if patch_data.get("error"):
                self.logger.error(f"Developer agent reported error: {patch_data.get('error')}")
                attempt_result["status"] = "failed"
                attempt_result["error"] = patch_data.get("error")
                result["fix_attempts"].append(attempt_result)
                
                # Update context for next attempt
                context["previous_attempts"].append({
                    "attempt": attempt,
                    "error": patch_data.get("error"),
                })
                
                # Post JIRA update via communicator
                await self._run_communicator_update(
                    ticket_id,
                    attempt,
                    patch_data,
                    None,
                    False,
                    patch_data.get("error")
                )
                
                attempt += 1
                continue
            
            # Step 3: QA Agent - Run tests
            self.logger.info(f"Running QAAgent for ticket {ticket_id} (attempt {attempt})")
            result["current_stage"] = "testing"
            
            qa_input = {
                "ticket_id": ticket_id,
                "test_command": os.environ.get("TEST_COMMAND", "pytest"),
                **patch_data  # Pass all developer output to QA agent
            }
            
            test_results = await self._run_agent(self.qa_agent, qa_input)
            
            # Save QA results
            attempt_result["testing"] = {
                "status": "completed",
                "output": test_results
            }
            
            # Check if tests passed
            success = test_results.get("passed", False) and test_results.get("code_changes_detected", False)
            
            # Check specifically for the code changes check
            if not test_results.get("code_changes_detected", False):
                self.logger.error("QA Agent did not detect code changes")
                success = False
                test_results["error_message"] = test_results.get("error_message", "") + " No code changes detected."
            
            # Extract failure summary for pattern detection
            current_failure_summary = test_results.get("error_message", "") if not success else ""
            
            # Log test result with enhanced information
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            result_status = "PASS" if success else "FAIL"
            
            # Include failure summary in the log if tests failed
            failure_info = ""
            if not success and test_results.get("error_message"):
                failure_info = f" | Failure: {test_results.get('error_message').replace(chr(10), ' ')}"
                
            log_message = f"[Ticket: {ticket_id}] Retry {attempt}/{self.max_retries} | QA Result: {result_status} | Confidence: {confidence_score}%{failure_info} | Timestamp: {timestamp}"
            self.logger.info(log_message)
            
            # Post JIRA update via communicator regardless of test result
            await self._run_communicator_update(
                ticket_id,
                attempt,
                patch_data,
                test_results,
                success,
                current_failure_summary
            )
            
            # Check for repeated failure patterns (if this isn't the first attempt)
            if not success and previous_failure_summary and current_failure_summary:
                if self._is_similar_failure(previous_failure_summary, current_failure_summary):
                    self.logger.warning(f"Repeated failure pattern detected, escalating early")
                    
                    # Update escalation details
                    result["analytics"]["early_escalation"] = True
                    result["analytics"]["escalation_reason"] = "repeated_failure_pattern"
                    attempt_result["early_escalation"] = True
                    attempt_result["escalation_reason"] = "Repeated failure pattern"
                    
                    # Run communicator for early escalation
                    await self._run_communicator_early_escalation(
                        ticket_id, 
                        attempt, 
                        patch_data, 
                        f"Repeated failure pattern: {current_failure_summary}"
                    )
                    
                    # Add attempt to results
                    attempt_result["end_time"] = time.time()
                    attempt_result["duration"] = attempt_result["end_time"] - attempt_result["start_time"]
                    attempt_result["success"] = False
                    result["fix_attempts"].append(attempt_result)
                    
                    # Update final status
                    result["status"] = "escalated"
                    result["current_stage"] = "escalated"
                    result["analytics"]["total_attempts"] = attempt
                    
                    return result
            
            # Step 4: Communicator Agent - Update JIRA and create PR if successful
            self.logger.info(f"Running CommunicatorAgent for ticket {ticket_id} (attempt {attempt})")
            
            # Add attempt to results before proceeding
            attempt_result["end_time"] = time.time()
            attempt_result["duration"] = attempt_result["end_time"] - attempt_result["start_time"]
            attempt_result["success"] = success
            result["fix_attempts"].append(attempt_result)
            
            # Update statistics
            result["analytics"]["total_attempts"] = attempt
            
            # If successful, create PR and update JIRA
            if success:
                result["current_stage"] = "communication"
                
                # Only proceed to final communication if confidence meets threshold
                if confidence_score >= self.confidence_threshold:
                    communication_result = await self._run_final_communication(
                        ticket_id, patch_data, test_results, task_plan, attempt
                    )
                    
                    # Save communication results
                    attempt_result["communication"] = {
                        "status": "completed",
                        "output": communication_result
                    }
                    
                    # Check if PR was created
                    if communication_result.get("pr_created", False) and communication_result.get("pr_url"):
                        result["status"] = "fixed"
                        result["pr_url"] = communication_result.get("pr_url")
                    else:
                        result["status"] = "partial_success"
                        result["error"] = "Fix successful but PR could not be created"
                else:
                    # Confidence below threshold, partial success
                    result["status"] = "partial_success"
                    result["error"] = f"Fix successful but confidence score ({confidence_score}%) below threshold ({self.confidence_threshold}%)"
                    
                    # Notify about partial success
                    await self._run_communicator_early_escalation(
                        ticket_id,
                        attempt,
                        patch_data,
                        f"Fix successful but confidence score ({confidence_score}%) below threshold"
                    )
            else:
                # Update previous failure summary for next iteration
                previous_failure_summary = current_failure_summary
                
                # Update context for next attempt
                context["previous_attempts"].append({
                    "attempt": attempt,
                    "error": current_failure_summary,
                    "confidence_score": confidence_score
                })
                
                attempt += 1
                
            # If we've reached max attempts without success, mark as escalated
            if attempt > self.max_retries and not success:
                result["status"] = "escalated"
                result["error"] = f"Failed to fix after {self.max_retries} attempts"
                
                # Final escalation notification
                await self._run_communicator_early_escalation(
                    ticket_id,
                    self.max_retries,
                    patch_data,
                    f"Max retry limit reached ({self.max_retries} attempts)"
                )
                
        return result
    
    def _validate_developer_output(self, patch_data: Dict[str, Any]) -> bool:
        """
        Validate developer output structure before proceeding to QA
        
        Args:
            patch_data: Dictionary with developer output
            
        Returns:
            Boolean indicating if output is valid
        """
        # Check required fields
        required_fields = ["patched_code", "patched_files", "patch_content", "confidence_score", "commit_message"]
        for field in required_fields:
            if field not in patch_data:
                self.logger.error(f"Missing required field in developer output: {field}")
                return False
        
        # Check confidence score
        if not isinstance(patch_data["confidence_score"], (int, float)) or patch_data["confidence_score"] <= 0:
            self.logger.error(f"Invalid confidence score: {patch_data.get('confidence_score', 0)}")
            return False
            
        # Check patched_code - must be a non-empty dictionary
        if not isinstance(patch_data["patched_code"], dict) or not patch_data["patched_code"]:
            self.logger.error("patched_code must be a non-empty dictionary")
            return False
            
        # Check patched_files - must be a non-empty list
        if not isinstance(patch_data["patched_files"], list) or not patch_data["patched_files"]:
            self.logger.error("patched_files must be a non-empty list")
            return False
            
        # Check patch_content - must be a non-empty string
        if not isinstance(patch_data["patch_content"], str) or not patch_data["patch_content"].strip():
            self.logger.error("patch_content must be a non-empty string")
            return False
            
        return True
        
    async def _run_communicator_update(
        self,
        ticket_id: str,
        attempt: int,
        patch_data: Dict[str, Any],
        test_results: Optional[Dict[str, Any]],
        success: bool,
        failure_summary: str
    ) -> Dict[str, Any]:
        """
        Run communicator agent to update JIRA with progress
        
        Args:
            ticket_id: Ticket ID
            attempt: Current attempt number
            patch_data: Dictionary with patch data
            test_results: Dictionary with test results
            success: Whether tests passed
            failure_summary: Summary of failure if tests failed
            
        Returns:
            Dictionary with communicator result
        """
        self.logger.info(f"Updating JIRA with progress for ticket {ticket_id}")
        
        communication_task = {
            "ticket_id": ticket_id,
            "update_type": "progress",
            "patch_data": patch_data,
            "test_results": test_results,
            "success": success,
            "failure_summary": failure_summary,
            "attempt": attempt,
            "max_retries": self.max_retries,
            "confidence_score": patch_data.get("confidence_score", 0)
        }
        
        return await self._run_agent(self.communicator_agent, communication_task)
        
    async def _run_communicator_early_escalation(
        self,
        ticket_id: str,
        attempt: int,
        patch_data: Dict[str, Any],
        escalation_reason: str
    ) -> Dict[str, Any]:
        """
        Run communicator agent to update JIRA with early escalation
        
        Args:
            ticket_id: Ticket ID
            attempt: Current attempt number
            patch_data: Dictionary with patch data
            escalation_reason: Reason for early escalation
            
        Returns:
            Dictionary with communicator result
        """
        self.logger.info(f"Updating JIRA with early escalation for ticket {ticket_id}")
        
        communication_task = {
            "ticket_id": ticket_id,
            "update_type": "early_escalation",
            "patch_data": patch_data,
            "escalation_reason": escalation_reason,
            "attempt": attempt,
            "max_retries": self.max_retries,
            "confidence_score": patch_data.get("confidence_score", 0)
        }
        
        return await self._run_agent(self.communicator_agent, communication_task)
        
    async def _run_final_communication(
        self,
        ticket_id: str,
        patch_data: Dict[str, Any],
        test_results: Dict[str, Any],
        task_plan: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """
        Run communicator agent to create PR and update JIRA with success
        
        Args:
            ticket_id: Ticket ID
            patch_data: Dictionary with patch data
            test_results: Dictionary with test results
            task_plan: Dictionary with task plan
            attempt: Current attempt number
            
        Returns:
            Dictionary with communicator result
        """
        self.logger.info(f"Creating PR and updating JIRA for ticket {ticket_id}")
        
        communication_task = {
            "ticket_id": ticket_id,
            "update_type": "final",
            "patch_data": patch_data,
            "test_results": test_results,
            "task_plan": task_plan,
            "attempt": attempt,
            "max_retries": self.max_retries,
            "success": True,
            "confidence_score": patch_data.get("confidence_score", 0)
        }
        
        return await self._run_agent(self.communicator_agent, communication_task)
        
    def _is_similar_failure(self, previous_failure: str, current_failure: str) -> bool:
        """
        Check if two failure patterns are similar
        
        Args:
            previous_failure: Previous failure message
            current_failure: Current failure message
            
        Returns:
            Boolean indicating if failures are similar
        """
        # Simple string comparison for now
        # In a real system, this would use more sophisticated comparison
        if not previous_failure or not current_failure:
            return False
            
        # Compare the first 50 chars to catch similar error messages
        return previous_failure[:50].lower() == current_failure[:50].lower()