
import re
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from .agent_base import Agent, AgentStatus

class PlannerAgent(Agent):
    def __init__(self):
        super().__init__(name="PlannerAgent")
        self.output_dir = os.path.join(os.path.dirname(__file__), "planner_outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    def _clean_ticket(self, text: str) -> str:
        """Clean a ticket description by removing noise elements"""
        if not text:
            return ""
            
        # Common patterns to clean
        signature_patterns = [
            r"Thanks(?:,| and regards,?|,? regards)?[\s\r\n]+[A-Za-z]+",
            r"Best regards,?[\s\r\n]+[A-Za-z]+",
            r"Regards,?[\s\r\n]+[A-Za-z]+",
            r"--[\s\r\n]+[A-Za-z]+[\s\r\n]+(?:.*?[\s\r\n]+)*?(?:Email|Tel|Phone|Mobile|www\.)",
            r"Sent from my (?:iPhone|Android|mobile device|tablet)",
        ]
        
        greeting_patterns = [
            r"^(?:Hi|Hello|Hey)(?:,| team| all| everyone| there)?(?:,|\.)?[\s\r\n]+",
            r"^Good (?:morning|afternoon|evening|day)(?:,| team| all| everyone| there)?(?:,|\.)?[\s\r\n]+",
            r"^Dear (?:team|support|all|everyone)(?:,|\.)?[\s\r\n]+"
        ]
        
        disclaimer_patterns = [
            r"DISCLAIMER[\s\r\n]+(?:.*?[\s\r\n]+)*?(?:confidential|intended|recipient)",
            r"This email (?:and any attachments )?(?:is|are) confidential",
            r"This message contains confidential information",
            r"This communication is intended solely for"
        ]
        
        headers_patterns = [
            r"^From:.*?[\r\n]+",
            r"^To:.*?[\r\n]+",
            r"^Date:.*?[\r\n]+",
            r"^Sent:.*?[\r\n]+",
            r"^Subject:.*?[\r\n]+"
        ]
        
        # Make a copy to work with
        cleaned_text = text
        
        # Remove signatures
        for pattern in signature_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Remove greetings
        for pattern in greeting_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Remove disclaimers
        for pattern in disclaimer_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Remove email headers
        for pattern in headers_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Clean excessive whitespace
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    def _extract_stack_traces(self, text: str) -> List[str]:
        """Extract stack traces from text"""
        stack_traces = []
        
        # Common stack trace patterns
        stack_trace_patterns = [
            # Python stack traces
            r"Traceback \(most recent call last\):\s+(?:.*\n)+?(?:.*Error:.*(?:\n\s+.*)*)",
            
            # Java stack traces
            r"(?:[a-zA-Z_$][a-zA-Z\d_$]*\.)*[a-zA-Z_$][a-zA-Z\d_$]*(?:Exception|Error).*?(?:\n\s+at .*)+",
            
            # JavaScript stack traces
            r"(?:Error|Exception|TypeError|ReferenceError).*\n(?:\s+at .*\n)+",
            
            # Generic stack trace patterns (line numbers, file paths)
            r"(?:in|at) .*?:[0-9]+(?:\n|$)"
        ]
        
        for pattern in stack_trace_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                stack_traces.append(match.group(0))
        
        return stack_traces
    
    def _highlight_stack_traces(self, text: str) -> str:
        """Highlight stack traces in the text by wrapping them in markers"""
        result = text
        stack_traces = self._extract_stack_traces(text)
        
        for trace in stack_traces:
            # Replace the trace with a highlighted version
            highlighted = f"\n[STACK TRACE START]\n{trace}\n[STACK TRACE END]\n"
            result = result.replace(trace, highlighted)
        
        return result

    def _create_enhanced_planning_prompt(self, ticket_id: str, title: str, 
                                       description: str, labels: List[str] = None, 
                                       has_stack_trace: bool = False) -> str:
        """Create an enhanced structured prompt for GPT to analyze the bug ticket"""
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
        self.log(f"Generating fallback output for ticket {ticket_id}")
        
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

    def _validate_affected_files(self, files: List[str], repo_files: List[str] = None) -> List[Dict[str, Any]]:
        """
        Validate file paths against a repository structure
        
        Args:
            files: List of file paths to validate
            repo_files: Optional list of valid repository files
            
        Returns:
            List of dictionaries with file info and validation status
        """
        validated_files = []
        
        # Simple validation if we don't have repo files
        if not repo_files:
            return [{"file": f, "valid": True} for f in files]
        
        # Convert repo_files to lowercase for case-insensitive matching
        repo_files_lower = [f.lower() for f in repo_files]
        
        for file_path in files:
            # Normalize path
            normalized = file_path.replace('\\', '/')
            # Remove leading slash if present
            if normalized.startswith('/'):
                normalized = normalized[1:]
            
            # Check if file exists in repo
            is_valid = normalized.lower() in repo_files_lower
            
            validated_files.append({
                "file": file_path,
                "valid": is_valid
            })
        
        return validated_files

    def _save_output(self, ticket_id: str, output_data: Dict[str, Any]) -> None:
        """Save the analysis output to a JSON file"""
        filename = f"planner_output_{ticket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(output_data, f, indent=2)
        self.log(f"Analysis output saved to {filepath}")

    def _query_gpt(self, prompt: str, max_retries: int = 1) -> str:
        """
        Query GPT-4 with the given prompt and retry on failure
        
        Args:
            prompt: The prompt to send to the API
            max_retries: Maximum number of retries (default: 1)
            
        Returns:
            The completion text
        """
        attempts = 0
        max_attempts = max_retries + 1  # Initial attempt plus retries
        
        while attempts < max_attempts:
            try:
                import openai
                
                # Get OpenAI API key from environment
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    self.log("Missing OpenAI API key")
                    raise EnvironmentError("Missing OPENAI_API_KEY environment variable")
                    
                openai.api_key = api_key
                
                self.log(f"Querying GPT (attempt {attempts + 1}/{max_attempts})")
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a senior software developer tasked with analyzing bug tickets and extracting structured information."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                result = response.choices[0].message.content
                
                # Check if result looks like valid JSON
                if result and ('{' in result and '}' in result):
                    return result
                    
                self.log("GPT response doesn't appear to be valid JSON")
                    
            except Exception as e:
                self.log(f"Error querying GPT-4: {str(e)}")
            
            attempts += 1
            
            # If we've used all attempts, break out
            if attempts >= max_attempts:
                self.log("Maximum GPT query attempts reached")
                break
        
        # Return whatever we have after max attempts
        return result if 'result' in locals() else ""

    def _extract_first_sentences(self, text: str, max_sentences: int = 2) -> str:
        """Extract the first 1-2 sentences from text for fallback summary"""
        # Simple sentence splitting by common endings
        sentence_endings = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_endings, text.strip())
        selected = sentences[:min(max_sentences, len(sentences))]
        return ' '.join(selected).strip()

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ticket and extract structured information with enhanced processing"""
        self.log("Starting enhanced ticket analysis")
        
        ticket_id = input_data.get("ticket_id", "")
        title = input_data.get("title", "")
        description = input_data.get("description", "")
        labels = input_data.get("labels", [])
        
        try:
            # Step 1: Clean the ticket description
            original_length = len(description)
            cleaned_description = self._clean_ticket(description)
            cleaned_length = len(cleaned_description)
            noise_removed = original_length - cleaned_length
            self.log(f"Cleaned ticket description, removed {noise_removed} characters of noise")
            
            # Step 2: Extract and highlight stack traces
            highlighted_description = self._highlight_stack_traces(cleaned_description)
            stack_traces = self._extract_stack_traces(cleaned_description)
            stack_trace_found = len(stack_traces) > 0
            
            if stack_trace_found:
                self.log(f"Found {len(stack_traces)} stack traces in ticket {ticket_id}")
            
            # Step 3: Create prompt for GPT with multi-source information
            prompt = self._create_enhanced_planning_prompt(
                ticket_id, 
                title, 
                highlighted_description,
                labels=labels,
                has_stack_trace=stack_trace_found
            )
            
            # Step 4: Get analysis from GPT with retry
            self.log(f"Sending ticket {ticket_id} to GPT for analysis with retry mechanism")
            gpt_response = self._query_gpt(prompt, max_retries=1)
            
            # Step 5: Validate GPT response
            is_valid, parsed_data, error_message = self._validate_gpt_response(gpt_response)
            
            if is_valid and parsed_data:
                # Step 6: Validate affected files against repository structure
                # In real implementation, we would have repo files available
                affected_files = self._validate_affected_files(parsed_data["affected_files"])
                
                # Add additional metadata to the output
                output = {
                    "ticket_id": ticket_id,
                    "bug_summary": parsed_data["bug_summary"],
                    "affected_files": affected_files,
                    "error_type": parsed_data["error_type"],
                    "using_fallback": False
                }
                
                self.log(f"[PlannerAgent] Parsed ticket {ticket_id} | Valid JSON received | Bug Summary: \"{parsed_data['bug_summary']}\"")
            else:
                # Use fallback if validation fails
                self.log(f"[PlannerAgent] Fallback triggered for {ticket_id} | Reason: {error_message}")
                output = self._generate_fallback_output(ticket_id, description)
            
            # Save output for debugging/inspection
            self._save_output(ticket_id, output)
            
            self.log("Enhanced analysis completed")
            return output
            
        except Exception as e:
            error_msg = f"Error during ticket analysis: {str(e)}"
            self.log(error_msg)
            
            # Even in case of exception, return structured output
            fallback_output = self._generate_fallback_output(ticket_id, description)
            self._save_output(ticket_id, fallback_output)
            
            return fallback_output
