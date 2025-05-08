
import logging
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket-status")

# Global dict to keep track of active tickets
active_tickets = {}

def initialize_ticket(ticket_id: str, ticket_data: Dict[str, Any]) -> None:
    """Initialize a new ticket in the active tickets list"""
    active_tickets[ticket_id] = {
        "ticket_id": ticket_id,
        "title": ticket_data.get("title", ""),
        "description": ticket_data.get("description", ""),
        "status": "initializing",
        "start_time": datetime.now().isoformat(),
        "updated_time": datetime.now().isoformat(),
        "attempt": 0,
        "agents": {},
        "steps": []
    }
    
    logger.info(f"Initialized ticket {ticket_id}")

def update_ticket_status(ticket_id: str, status: str, details: Dict[str, Any] = None) -> None:
    """Update the status and details of an active ticket"""
    if ticket_id not in active_tickets:
        logger.warning(f"Attempted to update non-existent ticket {ticket_id}")
        return
    
    # Update basic status fields
    active_tickets[ticket_id]["status"] = status
    active_tickets[ticket_id]["updated_time"] = datetime.now().isoformat()
    
    # Add the status change to steps
    step = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "details": details
    }
    active_tickets[ticket_id]["steps"].append(step)
    
    # Update additional details if provided
    if details:
        for key, value in details.items():
            active_tickets[ticket_id][key] = value
    
    logger.info(f"Updated ticket {ticket_id} status to {status}")
    
    # Save the updated state
    save_ticket_state(ticket_id)

def save_ticket_state(ticket_id: str) -> None:
    """Save the current state of the ticket to a file"""
    if ticket_id not in active_tickets:
        return
    
    try:
        with open(f"logs/{ticket_id}/ticket_state.json", 'w') as f:
            json.dump(active_tickets[ticket_id], f, indent=2)
    except Exception as e:
        logger.error(f"Error saving ticket state for {ticket_id}: {str(e)}")

async def cleanup_old_tickets() -> None:
    """Remove completed tickets from memory after 24 hours"""
    now = datetime.now()
    tickets_to_remove = []
    
    for ticket_id, ticket_data in active_tickets.items():
        # Parse the updated_time string to datetime
        try:
            updated_time = datetime.fromisoformat(ticket_data.get("updated_time", ""))
            # If ticket is older than 24 hours, mark for removal
            if (now - updated_time) > timedelta(hours=24) and ticket_data["status"] in ["completed", "escalated", "error"]:
                tickets_to_remove.append(ticket_id)
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing timestamp for ticket {ticket_id}: {str(e)}")
    
    # Remove the old tickets
    for ticket_id in tickets_to_remove:
        # Save final state before removing
        save_ticket_state(ticket_id)
        del active_tickets[ticket_id]
        logger.info(f"Removed completed ticket {ticket_id} from active tickets")
