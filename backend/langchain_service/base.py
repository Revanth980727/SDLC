
import json
import logging
import re
from typing import Dict, Any, List, Union, Optional
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import AgentOutputParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langchain-base")

class OrchestratorOutputParser(AgentOutputParser):
    """Parser for orchestrator agent output"""
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        """Parse text into agent action or finish"""
        # Check if this is a final answer
        if "Final Answer:" in text:
            return AgentFinish(
                return_values={"output": text.split("Final Answer:")[-1].strip()},
                log=text,
            )
        
        # Parse out the action and action input
        regex = r"Action: (.*?)[\n]*Action Input: (.*)"
        match = re.search(regex, text, re.DOTALL)
        
        if not match:
            logger.warning(f"Could not parse LLM output: {text}")
            return AgentFinish(
                return_values={"output": "I couldn't determine what to do next. Please try again."},
                log=text,
            )
            
        action = match.group(1).strip()
        action_input = match.group(2).strip()
        
        # Some cleanup for JSON strings
        if action_input.startswith("```json"):
            action_input = action_input[7:-3].strip()
        elif action_input.startswith("```"):
            action_input = action_input[3:-3].strip()
            
        return AgentAction(tool=action, tool_input=action_input, log=text)


class TicketMemory:
    """In-memory storage for ticket processing data"""
    
    def __init__(self):
        self.memories = {}
        self.agent_results = {}
        
    def save_to_memory(self, ticket_id: str, source: str, message: str):
        """Save a message to the ticket's memory"""
        if ticket_id not in self.memories:
            self.memories[ticket_id] = []
            
        self.memories[ticket_id].append({
            "source": source,
            "message": message
        })
        
    def get_memory(self, ticket_id: str):
        """Get the memory buffer for a ticket"""
        if ticket_id not in self.memories:
            return None
            
        # Create a ConversationBufferMemory-like object
        class MemoryBuffer:
            def __init__(self, buffer):
                self.buffer = buffer
                
        buffer = "\n".join([f"{mem['source']}: {mem['message']}" for mem in self.memories[ticket_id]])
        return MemoryBuffer(buffer)
        
    def get_memory_context(self, ticket_id: str) -> List[Dict[str, str]]:
        """Get memory as a context list"""
        if ticket_id not in self.memories:
            return []
            
        return self.memories[ticket_id]
        
    def clear_memory(self, ticket_id: str):
        """Clear the memory for a ticket"""
        if ticket_id in self.memories:
            del self.memories[ticket_id]
    
    def save_agent_result(self, ticket_id: str, agent_type: str, result: Dict[str, Any]):
        """Save complete agent result for retrieval by other agents"""
        if ticket_id not in self.agent_results:
            self.agent_results[ticket_id] = {}
        
        # Store the complete result
        self.agent_results[ticket_id][agent_type] = result
        logger.info(f"Saved {agent_type} result for ticket {ticket_id} with keys: {list(result.keys())}")
    
    def get_agent_result(self, ticket_id: str, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get the stored result for a specific agent and ticket"""
        if ticket_id not in self.agent_results or agent_type not in self.agent_results[ticket_id]:
            logger.warning(f"No {agent_type} result found for ticket {ticket_id}")
            return None
        
        return self.agent_results[ticket_id][agent_type]


# Singleton instance of TicketMemory
ticket_memory = TicketMemory()