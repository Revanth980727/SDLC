import asyncio
import logging
import os
import json
import time
from datetime import datetime
import traceback
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Direct imports instead of relative imports
from agent_framework.planner_agent import PlannerAgent
from agent_framework.developer_agent import DeveloperAgent
from agent_framework.qa_agent import QAAgent 
from agent_framework.communicator_agent import CommunicatorAgent
from jira_service.jira_client import JiraClient
from github_service.github_service import GitHubService
from analytics_tracker import get_analytics_tracker
from env import MAX_RETRIES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/orchestrator_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("orchestrator")

# Constants and config
POLL_INTERVAL_SECONDS = int(os.environ.get('POLL_INTERVAL_SECONDS', '60'))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '4'))
REPO_PATH = os.environ.get('REPO_PATH', '/app/code_repo')
RETRY_DELAY_SECONDS = 5  # Delay between retries
LOW_CONFIDENCE_THRESHOLD = 60  # Threshold for early escalation


class Orchestrator:
    def __init__(self):
        """Initialize orchestrator and its dependencies"""
        self.jira_client = JiraClient()
        self.github_service = GitHubService()
        
        # Initialize agent instances
        self.planner_agent = PlannerAgent()
        self.developer_agent = DeveloperAgent()
        self.qa_agent = QAAgent()
        self.communicator_agent = CommunicatorAgent()
        
        # Get analytics tracker
        self.analytics_tracker = get_analytics_tracker()
        
        # Track active tickets
        self.active_tickets = {}
        
        # Track processed tickets to avoid duplicates with JIRA service
        self.processed_tickets = set()
        
        # Set up lock directory
        self.lock_dir = os.environ.get("TICKET_LOCK_DIR", "/tmp/bugfix_ai_locks")
        os.makedirs(self.lock_dir, exist_ok=True)
        
        logger.info("Orchestrator initialized")
        logger.info(f"Using lock directory: {self.lock_dir}")
    
    def _check_ticket_locked(self, ticket_id: str) -> bool:
        """Check if a ticket is locked by another service."""
        lock_file = os.path.join(self.lock_dir, f"{ticket_id}.lock")
        
        if not os.path.exists(lock_file):
            return False
            
        # Check if the lock is stale (older than 1 hour)
        lock_time = os.path.getmtime(lock_file)
        if time.time() - lock_time >= 3600:  # 1 hour in seconds
            logger.info(f"Found stale lock for ticket {ticket_id}, considering it unlocked")
            return False
            
        # Lock exists and is valid, check who owns it
        try:
            with open(lock_file, 'r') as f:
                lock_data = json.load(f)
                owner = lock_data.get('owner', 'unknown')
                pid = lock_data.get('pid', 0)
                timestamp = lock_data.get('timestamp', 0)
                
                # If we own the lock, it's not considered locked by another service
                if owner == "orchestrator" and pid == os.getpid():
                    return False
                    
                logger.info(f"Ticket {ticket_id} is locked by {owner} (PID: {pid}) since {time.ctime(timestamp)}")
                return True
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading lock file for ticket {ticket_id}: {str(e)}")
            # If we can't read the lock file, assume it's locked to be safe
            return True
    
    def _acquire_lock(self, ticket_id: str) -> bool:
        """Try to acquire a lock on the ticket."""
        lock_file = os.path.join(self.lock_dir, f"{ticket_id}.lock")
        
        try:
            # Check if locked by another service first
            if self._check_ticket_locked(ticket_id):
                return False
                
            # Create the lock file with our service info
            with open(lock_file, 'w') as f:
                lock_data = {
                    'owner': 'orchestrator',
                    'pid': os.getpid(),
                    'timestamp': time.time()
                }
                json.dump(lock_data, f)
            
            logger.info(f"Acquired lock for ticket {ticket_id}")
            return True
        except Exception as e:
            logger.error(f"Error acquiring lock for ticket {ticket_id}: {str(e)}")
            return False
            
    def _release_lock(self, ticket_id: str) -> bool:
        """Release our lock on a ticket."""
        lock_file = os.path.join(self.lock_dir, f"{ticket_id}.lock")
        
        try:
            if os.path.exists(lock_file):
                # Verify we own the lock before removing it
                try:
                    with open(lock_file, 'r') as f:
                        lock_data = json.load(f)
                        if lock_data.get('owner') == 'orchestrator' and lock_data.get('pid') == os.getpid():
                            os.remove(lock_file)
                            logger.info(f"Released lock for ticket {ticket_id}")
                            return True
                        else:
                            logger.warning(f"Lock for ticket {ticket_id} is owned by another process, not releasing")
                            return False
                except (json.JSONDecodeError, IOError):
                    # If we can't read the file, don't delete it
                    logger.error(f"Couldn't read lock file for ticket {ticket_id}")
                    return False
            return True  # No lock file exists
        except Exception as e:
            logger.error(f"Error releasing lock for ticket {ticket_id}: {str(e)}")
            return False
    
    async def fetch_eligible_tickets(self) -> List[Dict[str, Any]]:
        """Fetch eligible tickets from JIRA that need processing"""
        try:
            # Changed from fetch_tickets to fetch_bug_tickets to match the actual method name in JiraClient
            tickets = await self.jira_client.fetch_bug_tickets()
            
            if not tickets:
                return []
                
            # Filter tickets to process - now check lock status
            eligible_tickets = []
            
            for ticket in tickets:
                if not ticket or not isinstance(ticket, dict):
                    continue
                    
                ticket_id = ticket.get("ticket_id")
                if not ticket_id:
                    continue
                    
                status = ticket.get("status", "Unknown")
                
                # Skip tickets we're already processing
                if ticket_id in self.active_tickets:
                    continue
                    
                # Skip tickets we've already processed
                if ticket_id in self.processed_tickets:
                    continue
                    
                # Skip tickets locked by another service
                if self._check_ticket_locked(ticket_id):
                    logger.info(f"Ticket {ticket_id} is locked by another service, skipping")
                    continue
                    
                # Only process tickets that are "To Do" - let jira_service handle "In Progress"
                if status == "To Do":
                    eligible_tickets.append(ticket)
            
            return eligible_tickets
        
        except Exception as e:
            logger.error(f"Error fetching eligible tickets: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    async def process_ticket(self, ticket: Dict[str, Any]) -> None:
        """Process a single ticket through the AI agent pipeline"""
        # Validate ticket
        if not ticket or not isinstance(ticket, dict):
            logger.error("Invalid ticket object: not a dictionary or None")
            return
            
        ticket_id = ticket.get("ticket_id")
        if not ticket_id:
            logger.error("Invalid ticket: missing ticket_id")
            return
            
        # Try to acquire lock
        if not self._acquire_lock(ticket_id):
            logger.info(f"Could not acquire lock for ticket {ticket_id}, skipping")
            return
            
        try:
            # Check if already processed or active
            if ticket_id in self.processed_tickets:
                logger.info(f"Ticket {ticket_id} has already been processed. Skipping.")
                self._release_lock(ticket_id)
                return
                
            if ticket_id in self.active_tickets:
                logger.info(f"Ticket {ticket_id} is already being processed. Skipping.")
                self._release_lock(ticket_id)
                return
                
            # Add to processed tickets set
            self.processed_tickets.add(ticket_id)
            
            # Mark ticket as being processed
            self.active_tickets[ticket_id] = {
                "status": "processing",
                "start_time": datetime.now().isoformat(),
                "current_attempt": 0,
                "escalated": False,
                "retry_history": []  # Store retry history with QA errors
            }
            
            logger.info(f"Starting processing for ticket {ticket_id}")
            
            # Create log directory for this ticket
            log_dir = f"logs/{ticket_id}"
            os.makedirs(log_dir, exist_ok=True)
            
            # Set ticket to In Progress if it's not already
            current_status = ticket.get("status", "Unknown")
            if current_status != "In Progress":
                # Update JIRA ticket to In Progress
                comment = "BugFix AI has started processing this ticket. Agent workflow initiated."
                success = await self.jira_client.update_ticket(ticket_id, "In Progress", comment)
                if not success:
                    logger.error(f"Failed to update ticket {ticket_id} to In Progress. Continuing anyway.")
            
            # STEP 1: Run planner agent
            logger.info(f"Running PlannerAgent for ticket {ticket_id}")
            
            planner_input = {
                "ticket_id": ticket_id,
                "title": ticket.get("title", ""),
                "description": ticket.get("description", ""),
            }
            
            with open(f"{log_dir}/planner_input.json", 'w') as f:
                json.dump(planner_input, f, indent=2)
            
            planner_result = await self.run_agent(self.planner_agent, planner_input)
            
            if not planner_result or "error" in planner_result:
                error_msg = planner_result.get("error", "Unknown error") if planner_result else "No result"
                raise Exception(f"PlannerAgent failed: {error_msg}")
            
            with open(f"{log_dir}/planner_output.json", 'w') as f:
                json.dump(planner_result, f, indent=2)
            
            # Update ticket status
            self.active_tickets[ticket_id]["planner_result"] = planner_result
            
            # STEP 2-4: Developer-QA loop with retries
            await self.run_development_qa_loop(ticket_id, planner_result)
            
        except Exception as e:
            logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Update ticket as failed
            self.active_tickets[ticket_id]["status"] = "failed"
            self.active_tickets[ticket_id]["error"] = str(e)
            
            # Try to update JIRA with the failure
            try:
                await self.jira_client.update_ticket(
                    ticket_id, 
                    "Needs Review", 
                    f"Automatic bug fix process failed with error: {str(e)}"
                )
            except Exception as jira_error:
                logger.error(f"Failed to update JIRA for ticket {ticket_id}: {str(jira_error)}")
                
            # Log analytics for the failed ticket
            self.analytics_tracker.log_ticket_result(
                ticket_id=ticket_id,
                total_retries=self.active_tickets[ticket_id].get("current_attempt", 0),
                final_status="failed",
                escalation_reason=f"Process error: {str(e)}"
            )
        finally:
            # Release the lock when we're done
            self._release_lock(ticket_id)
    
    async def run_development_qa_loop(self, ticket_id: str, planner_result: Dict[str, Any]) -> None:
        """Run the developer-QA loop with retries"""
        max_retries = MAX_RETRIES
        current_attempt = 1
        success = False
        early_escalation = False
        escalation_reason = None
        confidence_score = None
        
        log_dir = f"logs/{ticket_id}"
        
        # Initialize retry history for this ticket
        retry_history = []
        
        while current_attempt <= max_retries and not success and not early_escalation:
            logger.info(f"Starting development attempt {current_attempt}/{max_retries} for ticket {ticket_id}")
            
            # Update ticket tracking
            self.active_tickets[ticket_id]["current_attempt"] = current_attempt
            
            try:
                # STEP 2: Run developer agent
                logger.info(f"Running DeveloperAgent for ticket {ticket_id} (attempt {current_attempt})")
                
                # Add context for retries with previous QA failures
                developer_context = {"previousAttempts": retry_history}
                
                developer_input = {
                    "ticket_id": ticket_id,
                    **planner_result,
                    "attempt": current_attempt,
                    "max_attempts": max_retries,
                    "context": developer_context
                }
                
                with open(f"{log_dir}/developer_input_{current_attempt}.json", 'w') as f:
                    json.dump(developer_input, f, indent=2)
                
                developer_result = await self.run_agent(self.developer_agent, developer_input)
                
                if not developer_result or "error" in developer_result:
                    raise Exception(f"DeveloperAgent failed: {developer_result.get('error', 'Unknown error')}")
                
                # Get confidence score from developer result
                confidence_score = developer_result.get("confidence_score")
                if confidence_score is not None:
                    logger.info(f"Developer confidence score: {confidence_score}% for ticket {ticket_id}")
                
                with open(f"{log_dir}/developer_output_{current_attempt}.json", 'w') as f:
                    json.dump(developer_result, f, indent=2)
                
                # Update ticket tracking
                self.active_tickets[ticket_id]["developer_result"] = developer_result
                self.active_tickets[ticket_id]["confidence_score"] = confidence_score
                
                # STEP 3: Run QA agent
                logger.info(f"Running QAAgent for ticket {ticket_id} (attempt {current_attempt})")
                
                qa_input = {
                    "ticket_id": ticket_id,
                    "test_command": "npm test",  # Default test command, could be customized
                }
                
                with open(f"{log_dir}/qa_input_{current_attempt}.json", 'w') as f:
                    json.dump(qa_input, f, indent=2)
                
                qa_result = await self.run_agent(self.qa_agent, qa_input)
                
                if not qa_result:
                    raise Exception(f"QAAgent failed with no result")
                
                with open(f"{log_dir}/qa_output_{current_attempt}.json", 'w') as f:
                    json.dump(qa_result, f, indent=2)
                
                # Update ticket tracking
                self.active_tickets[ticket_id]["qa_result"] = qa_result
                
                # Check if tests passed
                success = qa_result.get("passed", False)
                
                # Log the retry status with enhanced failure information
                timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                result_status = "PASS" if success else "FAIL"
                
                failure_summary = ""
                if not success and "failure_summary" in qa_result:
                    failure_summary = qa_result['failure_summary']
                    
                log_message = f"[Ticket: {ticket_id}] Retry {current_attempt}/{max_retries} | QA Result: {result_status}"
                if failure_summary:
                    log_message += f" | Failure: {failure_summary.replace(chr(10), ' ')}"
                log_message += f" | Confidence: {confidence_score}% | {timestamp}"
                logger.info(log_message)
                
                # Store the QA results in retry history for future attempts
                retry_entry = {
                    "attempt": current_attempt,
                    "patch_content": developer_result.get("patch_content", ""),
                    "qa_results": qa_result,
                    "confidence_score": confidence_score
                }
                
                retry_history.append(retry_entry)
                self.active_tickets[ticket_id]["retry_history"] = retry_history
                
                if success:
                    logger.info(f"QA tests passed for ticket {ticket_id} on attempt {current_attempt}")
                    
                    # Clear the QA failure history since we succeeded
                    retry_history = []
                    self.active_tickets[ticket_id]["retry_history"] = []
                    
                    # STEP 4: Create PR and update JIRA via communicator agent
                    await self.finalize_successful_fix(
                        ticket_id, 
                        current_attempt, 
                        developer_result, 
                        qa_result
                    )
                else:
                    logger.warning(f"QA tests failed for ticket {ticket_id} on attempt {current_attempt}")
                    
                    # Check for early escalation based on confidence score
                    # Only check on first attempt
                    if current_attempt == 1 and confidence_score is not None and confidence_score < LOW_CONFIDENCE_THRESHOLD:
                        early_escalation = True
                        escalation_reason = f"Low confidence score ({confidence_score}%) on first attempt"
                        logger.warning(f"Early escalation for ticket {ticket_id}: {escalation_reason}")
                        
                        # Escalate the ticket
                        await self.escalate_ticket(
                            ticket_id, 
                            current_attempt, 
                            qa_result, 
                            early=True, 
                            reason=escalation_reason,
                            confidence=confidence_score
                        )
                        break  # Exit retry loop after early escalation
                    
                    # Try again or escalate if max retries reached
                    elif current_attempt >= max_retries:
                        logger.warning(f"Maximum retries reached for ticket {ticket_id}, escalating")
                        await self.escalate_ticket(ticket_id, current_attempt, qa_result)
                        break  # Exit retry loop after escalation
                    else:
                        # Update JIRA with retry information and failure summary
                        failure_summary = qa_result.get("failure_summary", "Unknown failure")
                        await self.jira_client.update_ticket(
                            ticket_id,
                            "In Progress",
                            f"Attempt {current_attempt}/{max_retries} failed with errors: {failure_summary}. Retrying with improved fix..."
                        )
                        
                        # Add delay between retries to avoid hammering the system
                        logger.info(f"Waiting {RETRY_DELAY_SECONDS} seconds before next retry")
                        await asyncio.sleep(RETRY_DELAY_SECONDS)
            
            except Exception as e:
                logger.error(f"Error in development-QA loop for ticket {ticket_id}: {str(e)}")
                
                # If we've used all retries or it's a non-fixable error, escalate
                if current_attempt >= max_retries:
                    await self.escalate_ticket(
                        ticket_id, 
                        current_attempt, 
                        {"error": str(e), "passed": False}
                    )
                    break
                else:
                    # Record error in retry history
                    retry_entry = {
                        "attempt": current_attempt,
                        "error": str(e)
                    }
                    retry_history.append(retry_entry)
                    
                    # Add delay between retries
                    logger.info(f"Waiting {RETRY_DELAY_SECONDS} seconds before next retry")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
            
            current_attempt += 1
    
        # Log analytics at the end of the ticket journey
        if success:
            self.analytics_tracker.log_ticket_result(
                ticket_id=ticket_id,
                total_retries=current_attempt,
                final_status="success",
                confidence_score=confidence_score,
                early_escalation=early_escalation,
                additional_data={"final_qa_result": qa_result.get("passed", False)}
            )
        elif early_escalation:
            self.analytics_tracker.log_ticket_result(
                ticket_id=ticket_id,
                total_retries=current_attempt,
                final_status="escalated",
                confidence_score=confidence_score,
                escalation_reason=escalation_reason,
                early_escalation=True,
                qa_failure_summary=qa_result.get("failure_summary", "")
            )
    
    async def finalize_successful_fix(
        self, 
        ticket_id: str, 
        attempt: int,
        developer_result: Dict[str, Any],
        qa_result: Dict[str, Any]
    ) -> None:
        """Finalize a successful fix by creating PR and updating JIRA"""
        try:
            # In a real implementation, would create a PR here
            # For now, just simulate it with a fake URL
            pr_url = f"https://github.com/org/repo/pull/{ticket_id}"
            
            # Run communicator agent
            logger.info(f"Running CommunicatorAgent for successful fix of ticket {ticket_id}")
            
            # Get confidence score
            confidence_score = developer_result.get("confidence_score")
            
            communicator_input = {
                "ticket_id": ticket_id,
                "test_passed": True,
                "github_pr_url": pr_url,
                "retry_count": attempt,
                "max_retries": MAX_RETRIES,
                "confidence_score": confidence_score
            }
            
            log_dir = f"logs/{ticket_id}"
            with open(f"{log_dir}/communicator_input.json", 'w') as f:
                json.dump(communicator_input, f, indent=2)
            
            # FIXED: Await the coroutine before trying to use its result
            communicator_result = await self.run_agent(self.communicator_agent, communicator_input)
            
            # Write the result, not the coroutine
            with open(f"{log_dir}/communicator_output.json", 'w') as f:
                # Ensure the result is JSON serializable
                serializable_result = self._ensure_json_serializable(communicator_result)
                json.dump(serializable_result, f, indent=2)
            
            # Update ticket tracking
            self.active_tickets[ticket_id]["status"] = "completed"
            self.active_tickets[ticket_id]["pr_url"] = pr_url
            
            logger.info(f"Successfully completed fix for ticket {ticket_id}")
            
        except Exception as e:
            logger.error(f"Error finalizing successful fix for ticket {ticket_id}: {str(e)}")
            logger.error(traceback.format_exc())
            # Even if PR creation fails, we still have the fix locally
            # Mark as needing review
            await self.jira_client.update_ticket(
                ticket_id,
                "Needs Review",
                f"Fix was generated successfully but PR creation failed: {str(e)}"
            )
    
    async def escalate_ticket(
        self, 
        ticket_id: str, 
        attempt: int, 
        qa_result: Dict[str, Any],
        early: bool = False,
        reason: str = None,
        confidence: int = None
    ) -> None:
        """Escalate a ticket after failed attempts or due to early escalation"""
        try:
            # Mark ticket as escalated
            self.active_tickets[ticket_id]["status"] = "escalated"
            self.active_tickets[ticket_id]["escalated"] = True
            
            if early:
                self.active_tickets[ticket_id]["early_escalation"] = True
                self.active_tickets[ticket_id]["escalation_reason"] = reason
            
            # Extract failure summary for more informative escalation
            failure_summary = qa_result.get("failure_summary", "")
            if not failure_summary and "error" in qa_result:
                failure_summary = qa_result["error"]
            
            # Run communicator agent for escalation
            logger.info(f"Running CommunicatorAgent for escalation of ticket {ticket_id}")
            
            # Prepare communicator input - make sure it's JSON serializable
            communicator_input = {
                "ticket_id": ticket_id,
                "test_passed": False,
                "github_pr_url": None,
                "retry_count": attempt,
                "max_retries": MAX_RETRIES,
                "escalated": True,
                "early_escalation": early,
                "early_escalation_reason": reason if early else None,
                "confidence_score": confidence,
                "failure_summary": str(failure_summary)
            }
            
            log_dir = f"logs/{ticket_id}"
            os.makedirs(log_dir, exist_ok=True)
            
            with open(f"{log_dir}/communicator_escalation_input.json", 'w') as f:
                json.dump(communicator_input, f, indent=2)
            
            try:
                # FIXED: Await the coroutine before trying to use its result
                communicator_result = await self.run_agent(self.communicator_agent, communicator_input)
                
                # Ensure the result is serializable before writing
                serializable_result = self._ensure_json_serializable(communicator_result)
                
                with open(f"{log_dir}/communicator_output.json", 'w') as f:
                    json.dump(serializable_result, f, indent=2)
                    
                # Update JIRA with escalation
                await self.jira_client.update_ticket(
                    ticket_id,
                    "Needs Review",
                    f"BugFix AI was unable to fix this issue after {attempt} attempts. Human review needed. Failure details: {failure_summary}"
                )
                
            except Exception as e:
                logger.error(f"Error escalating ticket {ticket_id}: {str(e)}")
                logger.error(traceback.format_exc())
                # Try to update JIRA even if communicator fails
                await self.jira_client.update_ticket(
                    ticket_id,
                    "Needs Review",
                    f"BugFix AI was unable to fix this issue after {attempt} attempts. Human review needed."
                )
        except Exception as e:
            logger.error(f"Error escalating ticket {ticket_id}: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def run_agent(self, agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run an agent and ensure we get a usable result back
        
        This wrapper handles both regular functions and async functions (coroutines)
        """
        try:
            # Call the agent's run method
            if asyncio.iscoroutinefunction(agent.run):
                # If it's async, await it
                result = await agent.run(input_data)
            else:
                # If it's synchronous, just call it directly
                result = agent.run(input_data)
            
            return result
        except Exception as e:
            logger.error(f"Error running {agent.name if hasattr(agent, 'name') else 'unknown'} agent: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}
    
    def _ensure_json_serializable(self, obj):
        """Recursively ensures that an object is JSON serializable"""
        if isinstance(obj, dict):
            return {k: self._ensure_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_json_serializable(i) for i in obj]
        elif hasattr(obj, '__await__'):  # Detect coroutines
            return f"[Coroutine: {type(obj).__name__}]"
        elif hasattr(obj, '__dict__'):  # Handle custom objects
            return str(obj)
        else:
            return obj

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the orchestrator"""
        status = {
            "active_tickets": self.active_tickets,
            "agent_statuses": self.get_agent_statuses()
        }
        return status
    
    def get_agent_statuses(self) -> Dict[str, str]:
        """Get statuses of all agents for health check"""
        return {
            "planner": self.planner_agent.status.value,
            "developer": self.developer_agent.status.value,
            "qa": self.qa_agent.status.value,
            "communicator": self.communicator_agent.status.value
        }

    async def run_forever(self):
        """Run the orchestrator in an infinite loop, processing tickets"""
        logger.info("Starting orchestrator polling loop")
        
        while True:
            try:
                # Fetch eligible tickets
                tickets = await self.fetch_eligible_tickets()
                
                if tickets:
                    logger.info(f"Found {len(tickets)} eligible tickets to process")
                    
                    # Process each ticket
                    for ticket in tickets:
                        await self.process_ticket(ticket)
                else:
                    logger.debug("No eligible tickets found")
                
                # Wait for next poll interval
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"Error in orchestrator main loop: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Don't crash, just wait and try again
                await asyncio.sleep(POLL_INTERVAL_SECONDS)