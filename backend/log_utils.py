
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("log-utils")

def setup_ticket_logging(ticket_id: str) -> str:
    """Setup logging directory for a ticket and return the path"""
    ticket_log_dir = f"logs/{ticket_id}"
    os.makedirs(ticket_log_dir, exist_ok=True)
    
    # Create structured log file for the ticket
    structured_log_path = f"{ticket_log_dir}/ticket_log.jsonl"
    if not os.path.exists(structured_log_path):
        with open(structured_log_path, 'w') as f:
            f.write("")
            
    return ticket_log_dir

def log_action(ticket_id: str, agent: str, action: str, output: Optional[Dict[str, Any]] = None) -> None:
    """Log an action with structured data"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "ticket_id": ticket_id,
        "agent": agent,
        "action": action,
        "output": output
    }
    
    ticket_log_dir = f"logs/{ticket_id}"
    with open(f"{ticket_log_dir}/ticket_log.jsonl", 'a') as f:
        f.write(json.dumps(log_entry) + "\n")

def log_agent_input(ticket_id: str, agent: str, data: Dict[str, Any]) -> None:
    """Log input data sent to an agent"""
    log_action(ticket_id, agent, "input", data)
    ticket_log_dir = f"logs/{ticket_id}"
    with open(f"{ticket_log_dir}/{agent}_input.json", 'w') as f:
        json.dump(data, f, indent=2)

def log_agent_output(ticket_id: str, agent: str, data: Dict[str, Any]) -> None:
    """Log output received from an agent"""
    log_action(ticket_id, agent, "output", data)
    ticket_log_dir = f"logs/{ticket_id}"
    with open(f"{ticket_log_dir}/{agent}_output.json", 'w') as f:
        json.dump(data, f, indent=2)

def log_error(ticket_id: str, agent: str, error_message: str) -> None:
    """Log an error for a specific agent"""
    log_action(ticket_id, agent, "error", {"message": error_message})
    error_log = {
        "timestamp": datetime.now().isoformat(),
        "message": error_message
    }
    
    ticket_log_dir = f"logs/{ticket_id}"
    with open(f"{ticket_log_dir}/{agent}_errors.json", 'a') as f:
        f.write(json.dumps(error_log) + "\n")

