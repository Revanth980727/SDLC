
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("planner-agent")

# Import our enhanced planner utilities
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ticket_cleaner import TicketCleaner, StackTraceExtractor, RepositoryValidator

app = FastAPI(title="BugFix AI Planner Agent")

class FileInfo(BaseModel):
    file: str
    valid: bool = True
    reason: Optional[str] = None

class TicketRequest(BaseModel):
    ticket_id: str
    title: str
    description: str
    repository: str
    labels: Optional[List[str]] = None
    attachments: Optional[List[str]] = None

class PlannerResponse(BaseModel):
    ticket_id: str
    bug_summary: str
    affected_files: List[Dict[str, Any]]
    error_type: str
    using_fallback: bool = False
    timestamp: str = datetime.now().isoformat()

def create_enhanced_planning_prompt(ticket_id: str, title: str, 
                                  description: str, labels: List[str] = None, 
                                  has_stack_trace: bool = False) -> str:
    """Create an enhanced structured prompt for GPT"""
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

def extract_first_sentences(text: str, max_sentences: int = 2) -> str:
    """Extract the first 1-2 sentences from text for fallback summary"""
    # Simple sentence splitting by common endings
    import re
    sentence_endings = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_endings, text.strip())
    selected = sentences[:min(max_sentences, len(sentences))]
    return ' '.join(selected).strip()

def generate_fallback_output(ticket_id: str, description: str) -> Dict[str, Any]:
    """Generate fallback output when GPT response fails validation"""
    logger.warning(f"Generating fallback output for ticket {ticket_id}")
    
    # Extract first 1-2 sentences for bug summary
    bug_summary = extract_first_sentences(description)
    if len(bug_summary) > 150:  # Truncate if too long
        bug_summary = bug_summary[:147] + "..."
        
    return {
        "ticket_id": ticket_id,
        "bug_summary": bug_summary,
        "affected_files": [],  # Return empty list for fallback
        "error_type": "Unknown",
        "using_fallback": True
    }

@app.get("/")
async def root():
    return {"message": "Enhanced Planner Agent is running", "status": "healthy"}

@app.post("/analyze", response_model=PlannerResponse)
async def analyze_ticket(request: TicketRequest):
    logger.info(f"Analyzing ticket {request.ticket_id}: {request.title}")
    
    try:
        # Step 1: Clean the ticket description
        cleaned_description = TicketCleaner.clean_ticket(request.description)
        logger.info(f"Cleaned ticket description, removed {len(request.description) - len(cleaned_description)} characters of noise")
        
        # Step 2: Extract and highlight stack traces
        highlighted_description = StackTraceExtractor.highlight_stack_traces(cleaned_description)
        stack_traces = StackTraceExtractor.extract_stack_traces(cleaned_description)
        stack_trace_found = len(stack_traces) > 0
        
        if stack_trace_found:
            logger.info(f"Found {len(stack_traces)} stack traces in ticket {request.ticket_id}")
        
        # Initialize repository validator if we have repo info
        repo_validator = RepositoryValidator()
        
        # In production, this would use OpenAI API to analyze the ticket
        # For now, we'll simulate the response with more realistic data
        
        # Simulate validated affected files (in production, validate against real repo)
        affected_files = [
            {"file": "src/components/auth/login.js", "valid": True},
            {"file": "src/api/userService.js", "valid": True},
            {"file": "src/utils/validation.js", "valid": True},
            {"file": "nonexistent/file.js", "valid": False}  # Simulate an invalid file
        ]
        
        # For the demo, we'll return a valid structured response
        mock_response = {
            "ticket_id": request.ticket_id,
            "bug_summary": "Login functionality fails when special characters are used in passwords because the validation function doesn't properly handle these cases.",
            "affected_files": affected_files,
            "error_type": "ValidationError",
            "using_fallback": False
        }
        
        logger.info(f"Analysis completed for ticket {request.ticket_id}")
        return PlannerResponse(**mock_response)
    
    except Exception as e:
        logger.error(f"Error analyzing ticket {request.ticket_id}: {str(e)}")
        
        # Generate fallback response even in case of exception
        fallback = generate_fallback_output(request.ticket_id, request.description)
        return PlannerResponse(**fallback)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8001, reload=True)
