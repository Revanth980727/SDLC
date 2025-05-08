
#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
import json

# Add the parent directory to the path so we can import our package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("jira-service")

# Import using absolute imports
from jira_service.jira_service import main
from langchain_service.base import ticket_memory

if __name__ == "__main__":
    try:
        logger.info("Starting JIRA service")
        
        # Set environment variable to indicate we're in the JIRA service
        os.environ["SERVICE_NAME"] = "jira_service"
        
        # Ensure debug logs directory exists
        os.makedirs("debug_logs", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Initialize ticket memory system
        logger.info("Initializing ticket memory system")
        
        # Log that we're starting and what we have in memory
        try:
            memory_initialized = isinstance(ticket_memory, object)
            logger.info(f"Ticket memory initialized: {memory_initialized}")
            
            if memory_initialized:
                memory_stats = {
                    "num_tickets": len(ticket_memory.memories),
                    "tickets": list(ticket_memory.memories.keys()) if hasattr(ticket_memory, "memories") else [],
                    "has_agent_results": hasattr(ticket_memory, "agent_results"),
                    "num_agent_results": len(ticket_memory.agent_results) if hasattr(ticket_memory, "agent_results") else 0
                }
                logger.info(f"Memory statistics: {json.dumps(memory_stats)}")
        except Exception as memory_error:
            logger.error(f"Error checking memory: {memory_error}")
        
        # Run the service
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service stopped by user")
    except Exception as e:
        logging.error(f"Service failed with error: {e}")
        # Log detailed traceback for debugging
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)