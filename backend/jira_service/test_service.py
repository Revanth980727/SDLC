
#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import our package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.jira_service.jira_client import JiraClient
from backend.jira_service.config import setup_logging

logger = setup_logging()

async def test_fetch_tickets():
    """Test fetching tickets from JIRA"""
    try:
        client = JiraClient()
        tickets = await client.fetch_bug_tickets()
        
        if not tickets:
            logger.info("No bug tickets found")
            return
        
        logger.info(f"Found {len(tickets)} bug tickets:")
        for ticket in tickets:
            print(json.dumps(ticket, indent=2))
            
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")

async def test_update_ticket(ticket_id):
    """Test updating a ticket in JIRA"""
    if not ticket_id:
        logger.error("Please provide a ticket ID")
        return
        
    try:
        client = JiraClient()
        
        # Add a test comment
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = f"This is a test comment from the JIRA service at {timestamp}"
        
        logger.info(f"Adding comment to ticket {ticket_id}")
        success = await client.add_comment(ticket_id, comment)
        
        if success:
            logger.info(f"Successfully added comment to ticket {ticket_id}")
        else:
            logger.error(f"Failed to add comment to ticket {ticket_id}")
            
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")

async def main():
    """Test the JIRA client functionality"""
    if len(sys.argv) < 2:
        print("Usage: python test_service.py [fetch|update TICKET_ID]")
        return
        
    command = sys.argv[1].lower()
    
    if command == 'fetch':
        await test_fetch_tickets()
    elif command == 'update' and len(sys.argv) >= 3:
        await test_update_ticket(sys.argv[2])
    else:
        print("Invalid command. Use 'fetch' or 'update TICKET_ID'")

if __name__ == "__main__":
    asyncio.run(main())
