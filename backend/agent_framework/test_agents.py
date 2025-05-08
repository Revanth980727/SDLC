
import logging
from typing import Dict, Any

from agent_base import Agent, AgentStatus
from planner_agent import PlannerAgent
from developer_agent import DeveloperAgent
from qa_agent import QAAgent
from communicator_agent import CommunicatorAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agent_workflow():
    # Initialize agents
    planner = PlannerAgent()
    developer = DeveloperAgent()
    qa = QAAgent()
    communicator = CommunicatorAgent()
    
    # Test input
    ticket_data = {
        "ticket_id": "BUG-123",
        "title": "Test Bug",
        "description": "Test description"
    }
    
    # Run workflow
    try:
        # Planner analysis
        plan = planner.process(ticket_data)
        logger.info(f"Planner status: {planner.status}")
        logger.info(f"Planner output: {plan}")
        
        # Developer implementation
        # Make sure all relevant information from planner is passed to developer
        dev_input = {
            **plan,  # Include all planner output
            "ticket_id": ticket_data["ticket_id"],
            "title": ticket_data["title"],
            "description": ticket_data["description"]
        }
        dev_result = developer.process(dev_input)
        logger.info(f"Developer status: {developer.status}")
        
        # QA testing
        qa_result = qa.process(dev_result)
        logger.info(f"QA status: {qa.status}")
        
        # Communicator deployment
        comm_result = communicator.process(qa_result)
        logger.info(f"Communicator status: {communicator.status}")
        
        # Print reports
        for agent in [planner, developer, qa, communicator]:
            logger.info(f"\nReport for {agent.name}:")
            logger.info(agent.report())
            
    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}")

if __name__ == "__main__":
    test_agent_workflow()