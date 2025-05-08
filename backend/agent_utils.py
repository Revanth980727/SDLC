
import logging
import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-utils")

# Agent service URLs
PLANNER_URL = os.getenv("PLANNER_URL", "http://planner:8001")
DEVELOPER_URL = os.getenv("DEVELOPER_URL", "http://developer:8002")
QA_URL = os.getenv("QA_URL", "http://qa:8003")
COMMUNICATOR_URL = os.getenv("COMMUNICATOR_URL", "http://communicator:8004")

async def call_planner_agent(ticket: Dict[str, Any]):
    """Send ticket information to the enhanced Planner agent"""
    try:
        # Ensure ticket is not None and has required fields
        if not ticket or not isinstance(ticket, dict):
            logger.error("Ticket object is None or not a dictionary")
            return None
            
        # Validate required fields exist
        ticket_id = ticket.get("ticket_id", "")
        if not ticket_id:
            logger.error("Ticket missing required field: ticket_id")
            return None
        
        # Ensure description field is not None
        description = ticket.get("description", "")
        if description is None:
            description = ""
            logger.warning(f"Ticket {ticket_id} has None description, using empty string")
            
        # Create a request payload with all available ticket information
        payload = {
            "ticket_id": ticket_id,
            "title": ticket.get("title", ""),
            "description": description,
            "repository": ticket.get("repository", "main")
        }
        
        # Add labels if available
        if "labels" in ticket and ticket["labels"] is not None:
            payload["labels"] = ticket["labels"]
            
        # Add attachments if available
        if "attachments" in ticket and ticket["attachments"] is not None:
            payload["attachments"] = ticket["attachments"]
        
        logger.info(f"Calling Planner agent with payload: {payload}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{PLANNER_URL}/analyze",
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Planner agent error: {response.status_code}, {response.text}")
                return None
            
            # Safely parse JSON response
            try:
                result = response.json()
                logger.info(f"Planner agent returned: {result}")
                return result
            except Exception as json_error:
                logger.error(f"Failed to parse Planner agent response: {str(json_error)}")
                return None
    except Exception as e:
        logger.error(f"Error calling Planner agent: {str(e)}")
        return None

async def call_developer_agent(planner_analysis: Dict[str, Any], attempt: int, context: Dict[str, Any] = None):
    """Send planner analysis to Developer agent"""
    try:
        # Ensure planner_analysis is not None
        if not planner_analysis or not isinstance(planner_analysis, dict):
            logger.error("Planner analysis is None or not a dictionary")
            return None
            
        payload = {
            "analysis": planner_analysis,
            "attempt": attempt
        }
        
        # Add context information (like previous QA results) if available
        if context and isinstance(context, dict):
            payload["context"] = context
        
        logger.info(f"Calling Developer agent with payload: {payload}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{DEVELOPER_URL}/generate",
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Developer agent error: {response.status_code}, {response.text}")
                return None
            
            # Safely parse JSON response
            try:
                result = response.json()
                logger.info(f"Developer agent returned: {result}")
                return result
            except Exception as json_error:
                logger.error(f"Failed to parse Developer agent response: {str(json_error)}")
                return None
    except Exception as e:
        logger.error(f"Error calling Developer agent: {str(e)}")
        return None

async def call_qa_agent(developer_response: Dict[str, Any]):
    """Send developer's changes to QA agent"""
    try:
        # Ensure developer_response is not None
        if not developer_response or not isinstance(developer_response, dict):
            logger.error("Developer response is None or not a dictionary")
            return None
            
        logger.info(f"Calling QA agent with payload: {developer_response}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{QA_URL}/test",
                json=developer_response
            )
            
            if response.status_code != 200:
                logger.error(f"QA agent error: {response.status_code}, {response.text}")
                return None
            
            # Safely parse JSON response
            try:
                result = response.json()
                logger.info(f"QA agent returned: {result}")
                return result
            except Exception as json_error:
                logger.error(f"Failed to parse QA agent response: {str(json_error)}")
                return None
    except Exception as e:
        logger.error(f"Error calling QA agent: {str(e)}")
        return None

async def call_communicator_agent(
    ticket_id: str,
    diffs: List[Dict[str, Any]] = None,
    test_results: List[Dict[str, Any]] = None,
    commit_message: str = None,
    test_passed: bool = False,
    escalated: bool = False,
    early_escalation: bool = False,
    early_escalation_reason: str = None,
    retry_count: int = 0,
    max_retries: int = 4,
    failure_details: str = None,
    agent_type: str = None,
    confidence_score: int = None
):
    """Send results to Communicator agent with enhanced error handling"""
    try:
        # Validate ticket_id
        if not ticket_id:
            logger.error("Missing required parameter: ticket_id")
            return None
            
        # Handle default parameters
        if diffs is None:
            diffs = []
        if test_results is None:
            test_results = []
            
        # Build payload with all possible parameters
        payload = {
            "ticket_id": ticket_id,
            "diffs": diffs,
            "test_results": test_results,
            "repository": "main",  # This would be configurable in a real implementation
            "test_passed": test_passed
        }
        
        # Add optional parameters only if they have values
        if commit_message:
            payload["commit_message"] = commit_message
        if escalated:
            payload["escalated"] = escalated
        if early_escalation:
            payload["early_escalation"] = early_escalation
        if early_escalation_reason:
            payload["early_escalation_reason"] = early_escalation_reason
        if retry_count > 0:
            payload["retry_count"] = retry_count
        if max_retries > 0:
            payload["max_retries"] = max_retries
        if failure_details:
            payload["failure_details"] = str(failure_details)  # Ensure it's a string
        if agent_type:
            payload["agent_type"] = agent_type
        if confidence_score is not None:
            payload["confidence_score"] = confidence_score
        
        # Ensure payload is JSON serializable by removing any non-serializable objects
        payload = _ensure_json_serializable(payload)
                
        logger.info(f"Calling Communicator agent with payload: {payload}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{COMMUNICATOR_URL}/deploy",
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Communicator agent error: {response.status_code}, {response.text}")
                return None
            
            # Safely parse JSON response
            try:
                result = response.json()
                logger.info(f"Communicator agent returned: {result}")
                return result
            except Exception as json_error:
                logger.error(f"Failed to parse Communicator agent response: {str(json_error)}")
                return None
    except Exception as e:
        logger.error(f"Error calling Communicator agent: {str(e)}")
        return None

def _ensure_json_serializable(obj):
    """Recursively ensures that an object is JSON serializable"""
    if isinstance(obj, dict):
        return {k: _ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_ensure_json_serializable(i) for i in obj]
    elif hasattr(obj, '__await__'):  # Detect coroutines
        return f"[Coroutine: {type(obj).__name__}]"
    elif hasattr(obj, '__dict__'):  # Handle custom objects
        return str(obj)
    else:
        return obj