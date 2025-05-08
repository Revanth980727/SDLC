
import os
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from .utils.logger import Logger
from .planner_agent import PlannerAgent
from .developer_agent import DeveloperAgent
from .qa_agent import QAAgent
from .communicator_agent import CommunicatorAgent

class AgentController:
    """
    Controller class that orchestrates the execution of the bug fixing agents.
    Runs the agents in sequence: Planner -> Developer -> QA -> Communicator.
    """
    
    def __init__(self, max_retries: int = 4, confidence_threshold: int = 60):
        """
        Initialize the agent controller
        
        Args:
            max_retries: Maximum number of retry attempts for generating a successful fix
            confidence_threshold: Threshold below which a patch is considered low confidence
        """
        self.logger = Logger("agent_controller")
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
        self.logger.start_task(f"Processing ticket {ticket_id}")
        
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
            result.update(fix_result)
            
            # Final status
            result["end_time"] = time.time()
            result["duration"] = result["end_time"] - result["start_time"]
            
            self.logger.end_task(f"Processing ticket {ticket_id}", success=True)
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
            
            result["status"] = "failed"
            result["error"] = str(e)
            result["end_time"] = time.time()
            result["duration"] = result["end_time"] - result["start_time"]
            
            self.logger.end_task(f"Processing ticket {ticket_id}", success=False)
            return result
            
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
            
            # Get or estimate confidence score for this patch
            confidence_score = patch_data.get("confidence_score", 75)  # Default if not provided
            
            # Save confidence score to analytics
            result["analytics"]["confidence_scores"].append(confidence_score)
            attempt_result["confidence_score"] = confidence_score
            
            # Save developer results
            attempt_result["development"] = {
                "status": "completed",
                "output": patch_data
            }
            
            # Check for low confidence early escalation
            if confidence_score < self.confidence_threshold:
                self.logger.warning(f"Low confidence score ({confidence_score}%) detected, escalating early")
                
                # Update escalation details
                result["analytics"]["early_escalation"] = True
                result["analytics"]["escalation_reason"] = "low_confidence"
                attempt_result["early_escalation"] = True
                attempt_result["escalation_reason"] = "Low confidence patch"
                
                # Apply patch to local repo (even with low confidence, for reference)
                patch_applied = await self._run_agent(self.developer_agent.apply_patch, patch_data)
                
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
            
            # Apply patch to local repo
            patch_applied = await self._run_agent(self.developer_agent.apply_patch, patch_data)
            
            if not patch_applied:
                self.logger.error(f"Failed to apply patch for attempt {attempt}")
                attempt_result["status"] = "failed"
                attempt_result["error"] = "Failed to apply patch"
                result["fix_attempts"].append(attempt_result)
                
                # Update context for next attempt
                context["previous_attempts"].append({
                    "attempt": attempt,
                    "error": "Failed to apply patch",
                    "patch_content": patch_data.get("patch_content", "")
                })
                
                # Post JIRA update via communicator
                await self._run_communicator_update(
                    ticket_id,
                    attempt,
                    patch_data,
                    None,
                    False,
                    "Failed to apply patch"
                )
                
                attempt += 1
                continue
            
            # Step 3: QA Agent - Run tests
            self.logger.info(f"Running QAAgent for ticket {ticket_id} (attempt {attempt})")
            result["current_stage"] = "testing"
            
            qa_input = {
                "ticket_id": ticket_id,
                "test_command": os.environ.get("TEST_COMMAND", "pytest")
            }
            
            test_results = await self._run_agent(self.qa_agent, qa_input)
            
            # Save QA results
            attempt_result["testing"] = {
                "status": "completed",
                "output": test_results
            }
            
            # Check if tests passed
            success = test_results.get("passed", False)
            
            # Extract failure summary for pattern detection
            current_failure_summary = test_results.get("failure_summary", "") if not success else ""
            
            # Log test result with enhanced information
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            result_status = "PASS" if success else "FAIL"
            
            # Include failure summary in the log if tests failed
            failure_info = ""
            if not success and "failure_summary" in test_results:
                failure_info = f" | Failure: {test_results['failure_summary'].replace(chr(10), ' ')}"
                
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
            result["current_stage"] = "communication"
            
            communicator_input = {
                "ticket_id": ticket_id,
                "patch_data": patch_data,
                "test_results": test_results,
                "task_plan": task_plan,
                "attempt": attempt,
                "max_retries": self.max_retries,
                "confidence_score": confidence_score
            }
            
            communication_result = await self._run_agent(self.communicator_agent, communicator_input)
            
            # Save communicator results
            attempt_result["communication"] = {
                "status": "completed",
                "output": communication_result
            }
            
            # Record end time for this attempt
            attempt_result["end_time"] = time.time()
            attempt_result["duration"] = attempt_result["end_time"] - attempt_result["start_time"]
            attempt_result["success"] = success
            
            # Add attempt to results
            result["fix_attempts"].append(attempt_result)
            
            # Update context for next attempt if needed
            if not success:
                context["previous_attempts"].append({
                    "attempt": attempt,
                    "patch_content": patch_data.get("patch_content", ""),
                    "qa_results": test_results,
                    "confidence_score": confidence_score
                })
                
                # Update previous failure summary for pattern detection
                previous_failure_summary = current_failure_summary
            else:
                # If successful, clear the QA failure summaries
                context["previous_attempts"] = []
                previous_failure_summary = None
                
            attempt += 1
        
        # Update analytics totals
        result["analytics"]["total_attempts"] = attempt - 1
        
        # Update final status
        if success:
            result["status"] = "success"
            result["current_stage"] = "completed"
        else:
            result["status"] = "failed"
            result["error"] = f"Failed to fix after {self.max_retries} attempts"
            result["analytics"]["escalation_reason"] = "max_retries_reached"
            
        return result
        
    async def _run_communicator_update(
        self,
        ticket_id: str,
        attempt: int,
        patch_data: Dict[str, Any],
        test_results: Optional[Dict[str, Any]],
        success: bool,
        failure_summary: Optional[str]
    ) -> None:
        """Run communicator agent to post updates to JIRA"""
        try:
            # Prepare input for communicator with detailed progress information
            communicator_input = {
                "ticket_id": ticket_id,
                "update_type": "progress",
                "attempt": attempt,
                "max_retries": self.max_retries,
                "patch_data": patch_data,
                "test_results": test_results,
                "success": success,
                "failure_summary": failure_summary,
                "confidence_score": patch_data.get("confidence_score", 75)
            }
            
            # Run communicator agent
            await self._run_agent(self.communicator_agent, communicator_input)
            
        except Exception as e:
            self.logger.error(f"Error posting update to JIRA: {str(e)}")
    
    async def _run_communicator_early_escalation(
        self,
        ticket_id: str,
        attempt: int,
        patch_data: Dict[str, Any],
        reason: str
    ) -> None:
        """Run communicator agent to handle early escalation"""
        try:
            # Prepare input for communicator with escalation information
            communicator_input = {
                "ticket_id": ticket_id,
                "update_type": "early_escalation",
                "attempt": attempt,
                "max_retries": self.max_retries,
                "patch_data": patch_data,
                "escalation_reason": reason,
                "confidence_score": patch_data.get("confidence_score", 75)
            }
            
            # Run communicator agent
            await self._run_agent(self.communicator_agent, communicator_input)
            
        except Exception as e:
            self.logger.error(f"Error posting early escalation to JIRA: {str(e)}")
            
    def _is_similar_failure(self, failure1: str, failure2: str) -> bool:
        """
        Compare two failure summaries to determine if they represent the same issue
        This is a simple implementation that could be enhanced with more sophisticated comparison
        """
        # Simple check: if the error type and test name are the same
        # This could be improved with more advanced NLP techniques
        failure1 = failure1.lower().strip()
        failure2 = failure2.lower().strip()
        
        if not failure1 or not failure2:
            return False
        
        # Compare the first 50 chars which usually contain the test name and error type
        # This is a simple heuristic and could be improved
        return failure1[:50] == failure2[:50] or \
               (len(failure1) > 20 and len(failure2) > 20 and failure1[:20] == failure2[:20])
        
    async def _run_agent(self, agent: Any, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run an agent asynchronously"""
        try:
            # Use asyncio to run the agent in a thread pool
            return await asyncio.to_thread(agent.run, input_data)
        except AttributeError:
            # If the agent doesn't have a run method, try calling it directly
            return await asyncio.to_thread(agent, input_data)
