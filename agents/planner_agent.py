
import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import openai
from .utils.logger import Logger
from .utils.ticket_cleaner import TicketCleaner, StackTraceExtractor, RepositoryValidator

class PlannerAgent:
    """
    Enhanced Planner Agent responsible for analyzing JIRA bug tickets and creating structured plans
    for fixing bugs, with improved resilience for real-world ticket formats and validation.
    """
    
    def __init__(self):
        """Initialize the planner agent with additional utilities"""
        self.logger = Logger("planner_agent")
        
        # Get OpenAI API key from environment
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            self.logger.error("Missing OpenAI API key")
            raise EnvironmentError("Missing OPENAI_API_KEY environment variable")
        
        openai.api_key = self.api_key
        
        # Initialize repository validator
        self.repo_validator = RepositoryValidator()
        
        # Try to load repository structure if REPO_PATH is defined
        repo_path = os.environ.get("REPO_PATH")
        if repo_path:
            try:
                self.repo_validator.load_repo_structure(repo_path)
                self.logger.info(f"Loaded repository structure from {repo_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load repository structure: {str(e)}")
        
    def run(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a JIRA bug ticket and extract structured information
        
        Args:
            ticket_data: Dictionary containing ticket information with fields like
                         'ticket_id', 'title', 'description', 'labels', etc.
                         
        Returns:
            A structured analysis as a dictionary
        """
        self.logger.start_task(f"Planning for ticket {ticket_data.get('ticket_id', 'unknown')}")
        
        try:
            # Extract ticket information
            ticket_id = ticket_data.get("ticket_id", "unknown")
            title = ticket_data.get("title", "")
            
            # Fix for JIRA's complex description field - safely convert to string
            description = self._extract_description_text(ticket_data.get("description", ""))
            labels = ticket_data.get("labels", [])
            
            # Step 1: Clean the ticket description
            cleaned_description = TicketCleaner.clean_ticket(description)
            self.logger.info(f"Cleaned ticket description, removed {len(description) - len(cleaned_description)} characters of noise")
            
            # Step 2: Extract and highlight stack traces
            highlighted_description = StackTraceExtractor.highlight_stack_traces(cleaned_description)
            stack_traces = StackTraceExtractor.extract_stack_traces(cleaned_description)
            stack_trace_found = len(stack_traces) > 0
            
            if stack_trace_found:
                self.logger.info(f"Found {len(stack_traces)} stack traces in ticket {ticket_id}")
            
            # Step 3: Build enhanced prompt with multi-source ticket fields
            prompt = self._create_enhanced_planning_prompt(
                ticket_id, 
                title, 
                highlighted_description,
                labels=labels,
                has_stack_trace=stack_trace_found
            )
            
            # Step 4: Get analysis from GPT with retry mechanism
            self.logger.info(f"Sending ticket {ticket_id} to GPT for analysis")
            gpt_response = self._query_gpt_with_retry(prompt)
            
            # Step 5: Validate GPT response
            is_valid, parsed_data, error_message = self._validate_gpt_response(gpt_response)
            
            if is_valid and parsed_data:
                # Step 6: Validate affected files against repository structure
                affected_files = self._validate_affected_files(parsed_data.get("affected_files", []))
                
                # Log success
                self.logger.info(f"[PlannerAgent] Parsed ticket {ticket_id} | Valid JSON received | Bug Summary: \"{parsed_data['bug_summary']}\"")
                
                # Structure the response
                output = {
                    "ticket_id": ticket_id,
                    "bug_summary": parsed_data["bug_summary"],
                    "affected_files": affected_files,
                    "error_type": parsed_data["error_type"],
                    "using_fallback": False
                }
            else:
                # Log fallback trigger
                self.logger.warning(f"[PlannerAgent] Fallback triggered for {ticket_id} | Reason: {error_message}")
                
                # Use fallback mechanism
                output = self._generate_fallback_output(ticket_id, description)
            
            self.logger.info(f"Planning complete for ticket {ticket_id}")
            self.logger.end_task(f"Planning for ticket {ticket_id}", success=True)
            
            return output
            
        except Exception as e:
            self.logger.error(f"Planning failed: {str(e)}")
            self.logger.end_task(f"Planning for ticket {ticket_data.get('ticket_id', 'unknown')}", 
                                success=False)
            
            # Even in case of exception, return structured fallback output
            fallback_output = self._generate_fallback_output(
                ticket_data.get("ticket_id", "unknown"),
                self._extract_description_text(ticket_data.get("description", ""))
            )
            return fallback_output
    
    def _extract_description_text(self, description: Any) -> str:
        """
        Safely extract plain text from JIRA description field which may be a 
        string, dictionary, or other complex structure
        
        Args:
            description: The description field from JIRA ticket
            
        Returns:
            Plain text description as a string
        """
        # If it's already a string, just return it
        if isinstance(description, str):
            return description
            
        # If it's None, return empty string
        if description is None:
            return ""
            
        # If it's a dict with Atlassian Document Format structure
        if isinstance(description, dict):
            # Try common JIRA API formats
            if "content" in description:
                # Try to extract text from Atlassian Document Format
                try:
                    text_parts = []
                    
                    # Process content array if it exists
                    for content_item in description.get("content", []):
                        # Handle paragraph type
                        if content_item.get("type") == "paragraph":
                            for text_item in content_item.get("content", []):
                                if text_item.get("type") == "text":
                                    text_parts.append(text_item.get("text", ""))
                        # Handle code block type
                        elif content_item.get("type") == "codeBlock":
                            for text_item in content_item.get("content", []):
                                if text_item.get("type") == "text":
                                    text_parts.append(f"```\n{text_item.get('text', '')}\n```")
                        # Handle bullet list type
                        elif content_item.get("type") in ["bulletList", "orderedList"]:
                            for list_item in content_item.get("content", []):
                                for item_content in list_item.get("content", []):
                                    if item_content.get("type") == "paragraph":
                                        for text_item in item_content.get("content", []):
                                            if text_item.get("type") == "text":
                                                text_parts.append(f"- {text_item.get('text', '')}")
                    
                    return "\n".join(text_parts)
                except Exception as e:
                    self.logger.warning(f"Error extracting text from Atlassian Document Format: {str(e)}")
            
            # Try raw value if content extraction failed
            if "raw" in description:
                return description.get("raw", "")
                
            # If we can't extract structured content, convert the whole dict to string
            return str(description)
        
        # For any other type, convert to string
        return str(description)
        
    def _validate_affected_files(self, files: List[str]) -> List[Dict[str, Any]]:
        """
        Validate file paths against the repository structure
        
        Args:
            files: List of file paths
            
        Returns:
            List of dictionaries with file paths and validation status
        """
        validated_files = []
        
        for file_path in files:
            is_valid = self.repo_validator.validate_file(file_path)
            validated_files.append({
                "file": file_path,
                "valid": is_valid
            })
            
            if not is_valid:
                self.logger.warning(f"Invalid file path detected: {file_path}")
        
        return validated_files
            
    def _create_enhanced_planning_prompt(self, ticket_id: str, title: str, 
                                        description: str, labels: List[str] = None, 
                                        has_stack_trace: bool = False) -> str:
        """
        Create an enhanced structured prompt for GPT to analyze the bug ticket
        
        Args:
            ticket_id: The ticket identifier
            title: The ticket title
            description: The cleaned and highlighted ticket description
            labels: Optional list of ticket labels
            has_stack_trace: Whether stack traces were detected in the description
            
        Returns:
            A formatted prompt string
        """
        # Format labels if provided
        labels_text = ""
        if labels and len(labels) > 0:
            labels_text = f"\nLabels: {', '.join(labels)}"
        
        # Add special instruction for stack traces if detected
        stack_trace_instruction = ""
        if has_stack_trace:
            stack_trace_instruction = """
            IMPORTANT: Stack traces have been detected and are highlighted between [STACK TRACE START] and [STACK TRACE END] markers. 
            Pay special attention to these as they often point directly to affected files and error types.
            """
        
        return f"""
        You are a senior software developer analyzing a bug ticket. Your task is to extract key information from this ticket.
        
        Your response must be valid parsable JSON. No prose or extra text.
        {stack_trace_instruction}
        
        Respond ONLY in the following strict JSON format:
        {{
            "bug_summary": "Brief one or two sentence summary of the bug",
            "affected_files": ["file1.py", "module2.js", ...],
            "error_type": "TypeError or other appropriate error classification"
        }}
        
        Here's the bug ticket:
        
        Ticket ID: {ticket_id}
        Title: {title}{labels_text}
        
        Description:
        {description}
        """
        
    def _query_gpt_with_retry(self, prompt: str, max_retries: int = 1) -> str:
        """
        Query GPT with automatic retry on failure
        
        Args:
            prompt: The prompt to send to GPT
            max_retries: Maximum number of retries (default: 1)
            
        Returns:
            The GPT response text
        """
        attempts = 0
        max_attempts = max_retries + 1  # Initial attempt plus retries
        
        while attempts < max_attempts:
            try:
                self.logger.info(f"Querying GPT (attempt {attempts + 1}/{max_attempts})")
                response = self._query_gpt(prompt)
                
                # Check if response looks like valid JSON
                if response and ('{' in response and '}' in response):
                    return response
                
                self.logger.warning("GPT response doesn't appear to be valid JSON, retrying")
            except Exception as e:
                self.logger.error(f"Error querying GPT: {str(e)}")
            
            attempts += 1
            
            # If we've used all attempts, break out
            if attempts >= max_attempts:
                self.logger.warning("Maximum GPT query attempts reached")
                break
        
        # Return whatever we have after max attempts
        return response if 'response' in locals() else ""
        
    def _query_gpt(self, prompt: str) -> str:
        """Query GPT with the given prompt"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a senior software developer tasked with analyzing bug tickets and extracting structured information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error querying GPT: {str(e)}")
            raise
    
    def _extract_first_sentences(self, text: str, max_sentences: int = 2) -> str:
        """Extract the first 1-2 sentences from text for fallback summary"""
        # Simple sentence splitting by common endings
        sentence_endings = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_endings, text.strip())
        selected = sentences[:min(max_sentences, len(sentences))]
        return ' '.join(selected).strip()
    
    def _validate_gpt_response(self, response: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Validate the GPT response against our expected format
        Returns: (is_valid, parsed_json, error_message)
        """
        if not response:
            return False, None, "Empty response"
            
        # Extract JSON if wrapped in backticks or text
        json_content = response
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        else:
            # Try to find JSON object in free text
            json_match = re.search(r'({.*})', response, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
        
        try:
            data = json.loads(json_content)
            
            # Check required fields
            required_fields = ["bug_summary", "affected_files", "error_type"]
            for field in required_fields:
                if field not in data:
                    return False, None, f"Missing required field: {field}"
                    
            # Validate field types
            if not isinstance(data["bug_summary"], str):
                return False, None, "bug_summary must be a string"
                
            if not isinstance(data["affected_files"], list):
                return False, None, "affected_files must be a list"
                
            if not isinstance(data["error_type"], str):
                return False, None, "error_type must be a string"
                
            return True, data, "Valid JSON"
            
        except json.JSONDecodeError as e:
            return False, None, f"JSON parse error: {str(e)}"
        except Exception as e:
            return False, None, f"Validation error: {str(e)}"
            
    def _generate_fallback_output(self, ticket_id: str, description: str) -> Dict[str, Any]:
        """Generate fallback output when GPT response fails validation"""
        self.logger.warning(f"Generating fallback output for ticket {ticket_id}")
        
        # Extract first 1-2 sentences for bug summary
        bug_summary = self._extract_first_sentences(description)
        if len(bug_summary) > 150:  # Truncate if too long
            bug_summary = bug_summary[:147] + "..."
            
        return {
            "ticket_id": ticket_id,
            "bug_summary": bug_summary,
            "affected_files": [],  # Empty list since we couldn't identify files
            "error_type": "Unknown",
            "using_fallback": True
        }
