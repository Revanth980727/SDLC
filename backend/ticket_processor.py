
import logging
import asyncio
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from jira_utils import update_jira_ticket
from agent_utils import (
    call_planner_agent,
    call_developer_agent,
    call_qa_agent,
    call_communicator_agent
)
from env import MAX_RETRIES
from test_processor import process_qa_results
from ticket_status import (
    active_tickets,
    initialize_ticket,
    update_ticket_status,
    cleanup_old_tickets
)
from log_utils import (
    setup_ticket_logging,
    log_agent_input,
    log_agent_output,
    log_error
)
from analytics_tracker import get_analytics_tracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket-processor")

# Get retry delay from environment or default to 5 seconds
RETRY_DELAY_SECONDS = int(os.environ.get('RETRY_DELAY_SECONDS', '5'))
# Get confidence threshold from environment or default to 60%
CONFIDENCE_THRESHOLD = int(os.environ.get('CONFIDENCE_THRESHOLD', '60'))

async def process_ticket(ticket: Dict[str, Any]):
    """Process a single ticket through the enhanced agent workflow"""
    ticket_id = ticket["ticket_id"]
    
    try:
        # Setup logging and initialize ticket
        ticket_log_dir = setup_ticket_logging(ticket_id)
        initialize_ticket(ticket_id, ticket)
        
        # Log the input received
        with open(f"{ticket_log_dir}/controller_input.json", 'w') as f:
            json.dump(ticket, f, indent=2)
        
        logger.info(f"Starting processing for ticket {ticket_id}")
        
        # Update JIRA ticket to "In Progress"
        await update_jira_ticket(
            ticket_id, 
            "In Progress", 
            "BugFix AI has started working on this ticket."
        )
        
        # Step 1: Enhanced Planner Analysis
        logger.info(f"Sending ticket {ticket_id} to enhanced Planner agent")
        
        # Prepare enhanced input with additional ticket fields
        enhanced_ticket = ticket.copy()
        
        # Try to fetch additional fields if not already in ticket
        if 'jira_id' in ticket and ('labels' not in ticket or 'attachments' not in ticket):
            try:
                # This would fetch additional ticket data from JIRA in a real implementation
                logger.info(f"Would fetch additional JIRA fields for ticket {ticket_id}")
            except Exception as e:
                logger.warning(f"Could not fetch additional ticket data: {str(e)}")
        
        log_agent_input(ticket_id, "planner", enhanced_ticket)
        planner_analysis = await call_planner_agent(enhanced_ticket)
        
        if planner_analysis:
            log_agent_output(ticket_id, "planner", planner_analysis)
            
            # Log information about file validation results
            if 'affected_files' in planner_analysis and isinstance(planner_analysis['affected_files'], list):
                valid_files = 0
                invalid_files = 0
                
                for file_item in planner_analysis['affected_files']:
                    if isinstance(file_item, dict) and 'valid' in file_item:
                        if file_item['valid']:
                            valid_files += 1
                        else:
                            invalid_files += 1
                
                if valid_files > 0 or invalid_files > 0:
                    logger.info(f"Planner identified {valid_files} valid files and {invalid_files} invalid files")
            
            # Notify JIRA about planner completion
            await update_jira_ticket(
                ticket_id,
                "", 
                "BugFix AI: Planner analysis completed. Identified affected files and error type."
            )
            
            # Check if fallback was used
            if planner_analysis.get('using_fallback'):
                logger.warning(f"Planner used fallback mechanism for ticket {ticket_id}")
        else:
            log_error(ticket_id, "planner", "Planner analysis failed")
            update_ticket_status(ticket_id, "error")
            await update_jira_ticket(
                ticket_id,
                "",
                "BugFix AI: Planner analysis failed. Escalating to human review."
            )
            return
            
        update_ticket_status(ticket_id, "processing", {"planner_analysis": planner_analysis})
        
        # Step 2-4: Developer-QA Loop
        current_attempt = 1
        qa_passed = False
        retry_history = []  # Track retry history with QA results
        
        while current_attempt <= MAX_RETRIES and not qa_passed:
            logger.info(f"Sending ticket {ticket_id} to Developer agent (attempt {current_attempt}/{MAX_RETRIES})")
            update_ticket_status(ticket_id, "processing", {
                "current_attempt": current_attempt,
                "max_attempts": MAX_RETRIES
            })
            
            # Update JIRA
            if current_attempt == 1:
                await update_jira_ticket(ticket_id, "", "Developer generating patch")
            else:
                # Include detailed failure information from previous attempt for smart retries
                previous_failure = ""
                if retry_history and "failure_summary" in retry_history[-1].get("qa_results", {}):
                    previous_failure = f" based on previous failure: {retry_history[-1]['qa_results']['failure_summary']}"
                
                await update_jira_ticket(
                    ticket_id,
                    "",
                    f"Developer generating revised patch (attempt {current_attempt}/{MAX_RETRIES}){previous_failure}"
                )
            
            # Developer context with QA feedback from previous attempts for smart retries
            developer_context = {"previousAttempts": retry_history}
            
            # Call Developer
            developer_input = {
                "ticket_id": ticket_id,
                "plannerAnalysis": planner_analysis,
                "attempt": current_attempt,
                "maxAttempts": MAX_RETRIES,
                "context": developer_context
            }
            
            log_agent_input(ticket_id, "developer", developer_input)
            developer_response = await call_developer_agent(planner_analysis, current_attempt, developer_context)
            
            if developer_response:
                log_agent_output(ticket_id, "developer", developer_response)
                
                # Check for confidence score and consider early escalation
                confidence_score = developer_response.get("confidence_score")
                if confidence_score is not None and confidence_score < CONFIDENCE_THRESHOLD:
                    logger.warning(f"Low confidence score ({confidence_score}%) detected, considering early escalation")
                    
                    # Update ticket status
                    update_ticket_status(ticket_id, "escalated", {
                        "escalated": True,
                        "early_escalation": True,
                        "escalation_reason": f"Low confidence patch ({confidence_score}%)",
                        "confidence_score": confidence_score
                    })
                    
                    # Call communicator for early escalation
                    await call_communicator_agent(
                        ticket_id=ticket_id,
                        diffs=[],
                        test_results=None,
                        commit_message=None,
                        early_escalation=True,
                        early_escalation_reason=f"Low confidence patch ({confidence_score}%)",
                        retry_count=current_attempt,
                        max_retries=MAX_RETRIES,
                        confidence_score=confidence_score
                    )
                    
                    # Log analytics for early escalation due to confidence
                    analytics_tracker = get_analytics_tracker()
                    analytics_tracker.log_ticket_result(
                        ticket_id=ticket_id,
                        total_retries=current_attempt,
                        final_status="escalated",
                        confidence_score=confidence_score,
                        early_escalation=True,
                        escalation_reason=f"Low confidence patch ({confidence_score}%)"
                    )
                    
                    return
                    
                # Update JIRA with developed patch details
                await update_jira_ticket(
                    ticket_id,
                    "",
                    f"BugFix AI: Developer created patch (attempt {current_attempt}/{MAX_RETRIES})." +
                    (f" Confidence score: {confidence_score}%" if confidence_score is not None else "")
                )
                
                # Notify JIRA about developer patch
                await call_communicator_agent(
                    ticket_id=ticket_id,
                    diffs=developer_response.get("diffs", []),
                    test_results=None,
                    commit_message=None,
                    agent_type="developer",
                    retry_count=current_attempt,
                    max_retries=MAX_RETRIES
                )
            else:
                log_error(ticket_id, "developer", f"Developer patch generation failed on attempt {current_attempt}")
                update_ticket_status(ticket_id, "error")
                await update_jira_ticket(
                    ticket_id,
                    "",
                    f"BugFix AI: Developer patch generation failed on attempt {current_attempt}. Escalating to human review."
                )
                return
                
            update_ticket_status(ticket_id, "processing", {"developer_diffs": developer_response})
            
            # Call QA
            logger.info(f"Sending ticket {ticket_id} to QA agent (attempt {current_attempt})")
            await update_jira_ticket(ticket_id, "", f"QA testing fix (attempt {current_attempt})")
            
            qa_input = {
                "ticket_id": ticket_id,
                "diffs": developer_response["diffs"],
                "attempt": current_attempt
            }
            log_agent_input(ticket_id, "qa", qa_input)
            
            qa_response = await call_qa_agent(developer_response)
            qa_passed = process_qa_results(ticket_id, developer_response, qa_response)
            
            update_ticket_status(ticket_id, "processing", {"qa_results": qa_response})
            
            # Log retry status with improved format including failure summary
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            result_status = "PASS" if qa_passed else "FAIL"
            
            # Include failure summary in logs when tests fail
            failure_info = ""
            if not qa_passed and "failure_summary" in qa_response:
                failure_info = f" | Failure: {qa_response['failure_summary']}"
            
            log_message = f"[Ticket: {ticket_id}] Retry {current_attempt}/{MAX_RETRIES} | QA Result: {result_status}{failure_info} | {timestamp}"
            logger.info(log_message)
            
            # Update JIRA with QA results after each attempt
            qa_jira_comment = f"QA Test Results (Attempt {current_attempt}/{MAX_RETRIES}): {result_status}\n"
            
            if qa_passed:
                qa_jira_comment += "✅ All tests passed! Moving to PR creation."
            else:
                qa_jira_comment += f"❌ Tests failed. "
                if "failure_summary" in qa_response:
                    qa_jira_comment += f"Failure summary: {qa_response['failure_summary']}\n"
                
                if current_attempt < MAX_RETRIES:
                    qa_jira_comment += f"\nBugFix AI will attempt another fix (retry {current_attempt+1}/{MAX_RETRIES})."
                else:
                    qa_jira_comment += "\nMaximum retries reached. Escalating to human review."
                    
            # Post QA results to JIRA
            await update_jira_ticket(
                ticket_id, 
                "", 
                qa_jira_comment
            )
            
            # Store results for future retries - key for smart retry logic
            retry_entry = {
                "attempt": current_attempt,
                "patch_content": developer_response.get("diffs", []),
                "qa_results": qa_response
            }
            retry_history.append(retry_entry)
            
            # Update ticket status with retry information
            update_ticket_status(ticket_id, "processing", {
                "retry_history": retry_history,
                "current_attempt": current_attempt,
                "max_attempts": MAX_RETRIES
            })
            
            # Check for repeated failure patterns that might indicate we should escalate early
            if not qa_passed and current_attempt >= 2 and len(retry_history) >= 2:
                # Get the two most recent failure summaries
                latest_failure = qa_response.get("failure_summary", "")
                previous_failure = retry_history[-2]["qa_results"].get("failure_summary", "")
                
                # Simple check for similar failures - could be made more sophisticated
                if latest_failure and previous_failure and latest_failure[:50] == previous_failure[:50]:
                    logger.warning(f"Detected repeated failure pattern: '{latest_failure[:50]}...'")
                    
                    # Only escalate early if we've seen this pattern twice and have at least one more retry available
                    if current_attempt < MAX_RETRIES:
                        logger.warning(f"Early escalation due to repeated failure pattern")
                        
                        escalation_reason = "Repeated failure pattern detected"
                        
                        # Update ticket status
                        update_ticket_status(ticket_id, "escalated", {
                            "escalated": True,
                            "early_escalation": True,
                            "escalation_reason": escalation_reason,
                        })
                        
                        # Call communicator for early escalation
                        await call_communicator_agent(
                            ticket_id=ticket_id,
                            diffs=[],
                            test_results=qa_response.get("test_results", []),
                            commit_message=None,
                            early_escalation=True,
                            early_escalation_reason=f"Repeated failure pattern: {latest_failure[:100]}...",
                            retry_count=current_attempt,
                            max_retries=MAX_RETRIES,
                            failure_details=latest_failure
                        )
                        
                        # Log analytics for early escalation due to repeated failures
                        analytics_tracker = get_analytics_tracker()
                        analytics_tracker.log_ticket_result(
                            ticket_id=ticket_id,
                            total_retries=current_attempt,
                            final_status="escalated",
                            confidence_score=developer_response.get("confidence_score"),
                            early_escalation=True,
                            escalation_reason=escalation_reason,
                            qa_failure_summary=latest_failure
                        )
                        
                        return
            
            if not qa_passed and current_attempt >= MAX_RETRIES:
                # Max retries reached, escalate to human
                update_ticket_status(ticket_id, "escalated", {"escalated": True})
                
                # Include failure summary in escalation note
                failure_summary = qa_response.get("failure_summary", "Unknown error")
                escalation_reason = f"Maximum retries ({MAX_RETRIES}) reached with continued test failures"
                
                # Call communicator for escalation
                await call_communicator_agent(
                    ticket_id=ticket_id,
                    diffs=[],
                    test_results=qa_response.get("test_results", []),
                    commit_message=None,
                    escalated=True,
                    retry_count=current_attempt,
                    max_retries=MAX_RETRIES,
                    failure_details=failure_summary
                )
                
                # Log analytics for max retries escalation
                analytics_tracker = get_analytics_tracker()
                analytics_tracker.log_ticket_result(
                    ticket_id=ticket_id,
                    total_retries=current_attempt,
                    final_status="escalated",
                    confidence_score=developer_response.get("confidence_score"),
                    early_escalation=False,
                    escalation_reason=escalation_reason,
                    qa_failure_summary=failure_summary
                )
                
                return
            
            if not qa_passed:
                # Wait before trying again
                logger.info(f"Waiting {RETRY_DELAY_SECONDS} seconds before next retry")
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            
            current_attempt += 1
        
        if not qa_passed:
            return
        
        # Step 5: Communicator for successful fix
        logger.info(f"Sending ticket {ticket_id} to Communicator agent")
        
        commit_message = developer_response.get("commit_message", f"Fix bug {ticket_id}")
        if not commit_message.startswith(f"Fix {ticket_id}:"):
            commit_message = f"Fix {ticket_id}: {commit_message}"
        
        communicator_response = await call_communicator_agent(
            ticket_id=ticket_id,
            diffs=developer_response["diffs"],
            test_results=qa_response.get("test_results", []),
            commit_message=commit_message,
            test_passed=True,
            retry_count=current_attempt - 1  # -1 because we increment at end of loop
        )
        
        if communicator_response:
            log_agent_output(ticket_id, "communicator", communicator_response)
            update_ticket_status(ticket_id, "completed", {"communicator_result": communicator_response})
            logger.info(f"Completed processing for ticket {ticket_id}")
            
            # Log successful ticket completion in analytics
            analytics_tracker = get_analytics_tracker()
            analytics_tracker.log_ticket_result(
                ticket_id=ticket_id,
                total_retries=current_attempt - 1,
                final_status="success",
                confidence_score=developer_response.get("confidence_score"),
                early_escalation=False,
                additional_data={"retry_history": retry_history}
            )
        else:
            log_error(ticket_id, "communicator", "Failed to deploy fix")
            update_ticket_status(ticket_id, "error")
            await update_jira_ticket(
                ticket_id,
                "",
                "BugFix AI: Failed to deploy the fix. Escalating to human review."
            )
            
            # Log error in analytics
            analytics_tracker = get_analytics_tracker()
            analytics_tracker.log_ticket_result(
                ticket_id=ticket_id,
                total_retries=current_attempt - 1,
                final_status="failed",
                confidence_score=developer_response.get("confidence_score"),
                early_escalation=False,
                escalation_reason="Failed to deploy fix",
                additional_data={"retry_history": retry_history}
            )
        
        # Collate all logs for this ticket
        from controller import collate_logs
        collate_logs(ticket_id)
            
    except Exception as e:
        logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
        update_ticket_status(ticket_id, "error")
        log_error(ticket_id, "processor", f"Unhandled exception: {str(e)}")
        
        await update_jira_ticket(
            ticket_id,
            "",
            f"BugFix AI encountered an error: {str(e)}. Escalating to human review."
        )
        
        # Log error in analytics
        try:
            analytics_tracker = get_analytics_tracker()
            analytics_tracker.log_ticket_result(
                ticket_id=ticket_id,
                total_retries=0,
                final_status="error",
                escalation_reason=f"Unhandled exception: {str(e)}"
            )
        except Exception as analytics_error:
            logger.error(f"Error logging analytics: {str(analytics_error)}")
