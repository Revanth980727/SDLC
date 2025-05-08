
from fastapi import FastAPI, HTTPException
import uvicorn
import asyncio
import json
from typing import Dict, Any
from pydantic import BaseModel
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.orchestrator import Orchestrator

app = FastAPI(title="BugFix AI Orchestrator API")

# Initialize orchestrator
orchestrator = Orchestrator()

# Start the background process
@app.on_event("startup")
async def startup_event():
    # Start orchestrator loop in background task
    asyncio.create_task(orchestrator.run_forever())


class TicketRequest(BaseModel):
    ticket_id: str
    title: str = ""
    description: str = ""


@app.get("/")
async def root():
    return {"message": "Orchestrator API is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": os.environ.get("VERSION", "development"),
        "services": {
            "orchestrator": "running",
            "agents": orchestrator.get_agent_statuses()
        }
    }


@app.get("/status")
async def get_status():
    """Get current status of the orchestrator"""
    return orchestrator.get_status()


@app.get("/tickets")
async def get_tickets():
    """Get list of all active tickets with their statuses"""
    tickets_data = orchestrator.get_status()["tickets"]
    
    # Transform to a more frontend-friendly format
    tickets = []
    for ticket_id, ticket_data in tickets_data.items():
        tickets.append({
            "id": ticket_id,
            "title": ticket_data.get("title", "Unknown"),
            "status": ticket_data.get("status", "unknown"),
            "current_attempt": ticket_data.get("current_attempt", 0),
            "max_attempts": int(os.environ.get("MAX_RETRIES", 4)),
            "escalated": ticket_data.get("escalated", False),
            "updated": ticket_data.get("updated_time", datetime.now().isoformat()),
            "created": ticket_data.get("start_time", datetime.now().isoformat()),
        })
    
    return tickets


@app.get("/tickets/{ticket_id}")
async def get_ticket_details(ticket_id: str):
    """Get detailed information for a specific ticket"""
    if ticket_id not in orchestrator.active_tickets:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket {ticket_id} not found"
        )
    
    ticket_data = orchestrator.active_tickets[ticket_id]
    
    # Transform to frontend format
    current_stage = "planning"
    if "qa_result" in ticket_data:
        if ticket_data.get("escalated", False):
            current_stage = "escalated"
        elif ticket_data.get("status") == "completed":
            current_stage = "completed"
        else:
            current_stage = "qa"
    elif "developer_result" in ticket_data:
        current_stage = "development"
    
    # Build agent outputs structure
    agent_outputs = {
        "planner": ticket_data.get("planner_result", {}),
        "developer": {
            "diffs": ticket_data.get("developer_result", {}).get("diffs", []),
            "attempt": ticket_data.get("current_attempt", 1),
            "maxAttempts": int(os.environ.get("MAX_RETRIES", 4))
        },
        "qa": ticket_data.get("qa_result", {}),
        "communicator": {
            "updates": ticket_data.get("communicator_result", {}).get("updates", []),
            "prUrl": ticket_data.get("pr_url"),
            "jiraUrl": f"https://jira.example.com/browse/{ticket_id}"  # Example URL
        }
    }
    
    return {
        "ticket": {
            "id": ticket_id,
            "title": ticket_data.get("title", "Unknown"),
            "description": ticket_data.get("description", ""),
            "status": ticket_data.get("status", "unknown"),
            "priority": "Medium",  # Default value
            "reporter": "JIRA",
            "assignee": "BugFix AI",
            "created": ticket_data.get("start_time", datetime.now().isoformat()),
            "updated": ticket_data.get("updated_time", datetime.now().isoformat()),
        },
        "agentOutputs": agent_outputs,
        "status": ticket_data.get("status", "processing"),
        "currentStage": current_stage,
        "escalated": ticket_data.get("escalated", False),
        "retryCount": ticket_data.get("current_attempt", 0),
        "maxRetries": int(os.environ.get("MAX_RETRIES", 4))
    }


@app.post("/process-ticket")
async def process_ticket(request: TicketRequest):
    """Manually trigger processing of a ticket"""
    # Convert to dict for processing
    ticket_dict = request.dict()
    
    # Check if ticket is already being processed
    if request.ticket_id in orchestrator.active_tickets:
        raise HTTPException(
            status_code=409, 
            detail=f"Ticket {request.ticket_id} is already being processed"
        )
    
    # Create task to process the ticket
    asyncio.create_task(orchestrator.process_ticket(ticket_dict))
    
    return {
        "message": f"Started processing ticket {request.ticket_id}",
        "status": "processing",
        "ticketId": request.ticket_id
    }


if __name__ == "__main__":
    uvicorn.run("orchestrator_api:app", host="0.0.0.0", port=8000, reload=True)
