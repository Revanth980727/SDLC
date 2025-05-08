
#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
from agents.agent_controller import AgentController
from agents.utils.logger import Logger

# Load environment variables
load_dotenv()

async def process_example_ticket():
    """Example of processing a ticket with the agent system"""
    logger = Logger("example")
    
    # Sample ticket data
    ticket_data = {
        "ticket_id": "DEMO-123",
        "title": "Button click causes application to crash",
        "description": """
        When a user clicks on the 'Submit' button in the form, the application crashes with the following error:
        
        TypeError: Cannot read property 'value' of null
        
        Steps to reproduce:
        1. Go to the home page
        2. Fill out the form
        3. Click Submit
        
        Expected: Form submits successfully
        Actual: Application crashes with error
        """
    }
    
    logger.info(f"Processing example ticket {ticket_data['ticket_id']}")
    
    # Initialize the controller
    controller = AgentController()
    
    # Process the ticket
    try:
        result = await controller.process_ticket(ticket_data)
        
        # Print summary
        logger.info(f"Ticket processing completed with status: {result['status']}")
        
        if result['status'] == 'success':
            # Get the successful attempt
            successful_attempt = next(
                (a for a in result['fix_attempts'] if a.get('success', False)), 
                None
            )
            
            if successful_attempt:
                attempt_num = successful_attempt['attempt']
                pr_url = successful_attempt.get('communication', {}).get('output', {}).get('pr_url')
                
                logger.info(f"Bug fixed successfully on attempt {attempt_num}")
                if pr_url:
                    logger.info(f"Pull request created: {pr_url}")
        else:
            logger.info(f"Failed to fix bug: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error processing ticket: {str(e)}")

if __name__ == "__main__":
    # Run the example
    asyncio.run(process_example_ticket())
