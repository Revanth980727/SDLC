import json
import logging
import os
from typing import Dict, List, Any, Optional
from langchain.agents import Tool

# Use absolute imports instead of relative
from agent_framework.planner_agent import PlannerAgent
from agent_framework.developer_agent import DeveloperAgent
from agent_framework.qa_agent import QAAgent
from agent_framework.communicator_agent import CommunicatorAgent
from langchain_service.base import ticket_memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langchain-tools")

class AgentTools:
    """Tools for interacting with agents through LangChain"""
    
    def __init__(self):
        self.planner_agent = PlannerAgent()
        self.developer_agent = DeveloperAgent()
        self.qa_agent = QAAgent()
        self.communicator_agent = CommunicatorAgent()
    
    def run_planner_tool(self, input_string: str) -> str:
        """Run the planner agent to analyze the ticket"""
        try:
            # Parse the input as JSON
            input_data = json.loads(input_string)
            ticket_id = input_data.get("ticket_id")
            
            logger.info(f"Running planner agent for ticket {ticket_id}")
            
            # Run the planner agent
            result = self.planner_agent.process(input_data)
            
            # Store the result in memory
            ticket_memory.save_to_memory(
                ticket_id, 
                "Planner", 
                f"Analysis completed. Affected files: {result.get('affected_files', [])} Error type: {result.get('error_type', 'Unknown')}"
            )
            
            # Debug log the result
            logger.debug(f"Planner result: {json.dumps(result, indent=2)}")
            
            # Store complete result in memory for other agents to access
            ticket_memory.save_agent_result(ticket_id, "planner", result)
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error running planner agent: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def run_developer_tool(self, input_string: str) -> str:
        """Run the developer agent to generate a fix"""
        try:
            # Parse the input as JSON
            input_data = json.loads(input_string)
            ticket_id = input_data.get("ticket_id")
            attempt = input_data.get("attempt", 1)
            
            logger.info(f"Running developer agent for ticket {ticket_id} (attempt {attempt})")
            
            # Get context from memory if available
            memory_context = ticket_memory.get_memory_context(ticket_id)
            if memory_context and "context" not in input_data:
                input_data["context"] = {"memory": memory_context}
            
            # Run the developer agent
            result = self.developer_agent.process(input_data)
            
            # Debug: Write developer output to file for inspection
            debug_dir = "debug_logs"
            os.makedirs(debug_dir, exist_ok=True)
            with open(f"{debug_dir}/developer_output_{ticket_id}_{attempt}.json", "w") as f:
                json.dump(result, f, indent=2)
            
            # Store result in memory
            confidence = result.get("confidence_score", "Unknown")
            ticket_memory.save_to_memory(
                ticket_id,
                "Developer",
                f"Generated fix for attempt {attempt} with confidence score: {confidence}%"
            )
            
            # Store complete result in memory for QA agent to access
            ticket_memory.save_agent_result(ticket_id, "developer", result)
            
            # Log the keys in result for debugging
            logger.info(f"Developer result keys: {list(result.keys())}")
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error running developer agent: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def run_qa_tool(self, input_string: str) -> str:
        """Run the QA agent to test the fix"""
        try:
            # Parse the input as JSON
            input_data = json.loads(input_string)
            ticket_id = input_data.get("ticket_id")
            
            logger.info(f"Running QA agent for ticket {ticket_id}")
            logger.info(f"QA input keys: {list(input_data.keys())}")
            
            # Validate required fields in the input data
            missing_fields = []
            for required_field in ["patched_code", "confidence_score", "patched_files"]:
                if required_field not in input_data:
                    missing_fields.append(required_field)
                    logger.error(f"Missing {required_field} in developer output")
            
            # If required fields are missing, try to retrieve developer result from memory
            if missing_fields:
                developer_result = ticket_memory.get_agent_result(ticket_id, "developer")
                if developer_result:
                    logger.info(f"Found developer result in memory with keys: {list(developer_result.keys())}")
                    
                    # Merge developer result with QA input to ensure all data is passed
                    for key, value in developer_result.items():
                        if key not in input_data:
                            input_data[key] = value
                            
                    logger.info(f"Enhanced QA input now has keys: {list(input_data.keys())}")
                else:
                    logger.warning(f"No developer result found in memory for ticket {ticket_id}")
                    
                    # Still missing required fields?
                    missing_fields = []
                    for required_field in ["patched_code", "confidence_score", "patched_files"]:
                        if required_field not in input_data:
                            missing_fields.append(required_field)
                    
                    if missing_fields:
                        logger.error(f"Still missing required fields after memory lookup: {missing_fields}")
                        return json.dumps({
                            "error": f"Missing required developer output: {', '.join(missing_fields)}",
                            "passed": False
                        })
            
            # Debug: Write QA input to file for inspection
            debug_dir = "debug_logs"
            os.makedirs(debug_dir, exist_ok=True)
            with open(f"{debug_dir}/qa_input_{ticket_id}.json", "w") as f:
                json.dump(input_data, f, indent=2)
            
            # Run the QA agent
            result = self.qa_agent.process(input_data)
            
            # Store the result in memory
            passed = "PASSED" if result.get("passed", False) else "FAILED"
            failure_summary = result.get("failure_summary", "")
            message = f"QA tests {passed}. {failure_summary if failure_summary else ''}"
            ticket_memory.save_to_memory(ticket_id, "QA", message)
            
            # Store complete result in memory for other agents to access
            ticket_memory.save_agent_result(ticket_id, "qa", result)
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error running QA agent: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def run_communicator_tool(self, input_string: str) -> str:
        """Run the communicator agent to update JIRA and GitHub"""
        try:
            # Parse the input as JSON
            input_data = json.loads(input_string)
            ticket_id = input_data.get("ticket_id")
            
            logger.info(f"Running communicator agent for ticket {ticket_id}")
            logger.info(f"Communicator input keys: {list(input_data.keys())}")
            
            # Retrieve developer and QA results from memory to ensure communicator has complete data
            developer_result = ticket_memory.get_agent_result(ticket_id, "developer")
            qa_result = ticket_memory.get_agent_result(ticket_id, "qa")
            
            if developer_result:
                logger.info("Found developer result in memory")
                # Add developer result to input if not already present
                for key, value in developer_result.items():
                    if key not in input_data:
                        input_data[key] = value
                        
                # Ensure developer_result is available as a nested object too
                if "developer_result" not in input_data:
                    input_data["developer_result"] = developer_result
            
            if qa_result:
                logger.info("Found QA result in memory")
                # Add test results if not already present
                if "test_results" not in input_data and "test_results" in qa_result:
                    input_data["test_results"] = qa_result["test_results"]
                
                # Add test passed flag if not already present
                if "qa_passed" not in input_data:
                    input_data["qa_passed"] = qa_result.get("passed", False)
                    
                # Ensure qa_result is available as a nested object too
                if "qa_result" not in input_data:
                    input_data["qa_result"] = qa_result
            
            # Debug: Write communicator input to file for inspection
            debug_dir = "debug_logs"
            os.makedirs(debug_dir, exist_ok=True)
            with open(f"{debug_dir}/communicator_input_{ticket_id}.json", "w") as f:
                json.dump(input_data, f, indent=2)
            
            # Run the communicator agent
            result = self.communicator_agent.process(input_data)
            
            # Store the result in memory
            status = "succeeded" if result.get("communications_success", False) else "failed"
            ticket_memory.save_to_memory(ticket_id, "Communicator", f"Communications {status}")
            
            # Store complete result in memory
            ticket_memory.save_agent_result(ticket_id, "communicator", result)
            
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error running communicator agent: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def get_agent_tools(self) -> List[Tool]:
        """Get all tools for interacting with agents"""
        return [
            Tool(
                name="PlannerAgent",
                func=self.run_planner_tool,
                description="Analyzes the bug ticket to identify affected files and error type. Input should be a JSON string with ticket_id, title, and description."
            ),
            Tool(
                name="DeveloperAgent",
                func=self.run_developer_tool,
                description="Generates code fixes based on planner analysis. Input should be a JSON string with ticket_id, affected_files, error_type, attempt, and max_attempts."
            ),
            Tool(
                name="QAAgent",
                func=self.run_qa_tool,
                description="Tests code fixes by running tests. Input should be a JSON string with ticket_id and test_command."
            ),
            Tool(
                name="CommunicatorAgent",
                func=self.run_communicator_tool,
                description="Updates JIRA and GitHub with results. Input should be a JSON string with ticket_id, test_passed, github_pr_url, retry_count, and max_retries."
            )
        ]