
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("developer-agent")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="BugFix AI Developer Agent")

class PlannerAnalysis(BaseModel):
    ticket_id: str
    affected_files: List[str]
    root_cause: str
    suggested_approach: str

class TicketDetails(BaseModel):
    description: str
    reproduction_steps: Optional[str]
    acceptance_criteria: Optional[str]

class FileDiff(BaseModel):
    filename: str
    diff: str
    lines_added: int
    lines_removed: int
    explanation: str

class DeveloperResponse(BaseModel):
    ticket_id: str
    diffs: List[FileDiff]
    commit_message: str
    timestamp: str = datetime.now().isoformat()
    attempt: int
    analysis_summary: str

def analyze_with_gpt4(analysis: PlannerAnalysis, ticket: TicketDetails, attempt: int) -> Dict[str, Any]:
    """Use GPT-4 to analyze the bug and generate a fix"""
    try:
        prompt = f"""
        Analyze this bug and generate a fix:

        Ticket ID: {analysis.ticket_id}
        Attempt: {attempt}

        Description:
        {ticket.description}

        Reproduction Steps:
        {ticket.reproduction_steps or 'Not provided'}

        Root Cause (from Planner):
        {analysis.root_cause}

        Affected Files:
        {', '.join(analysis.affected_files)}

        Suggested Approach:
        {analysis.suggested_approach}

        Generate:
        1. Precise code changes needed to fix the bug
        2. Clear explanation of what is being changed and why
        3. Ensure changes match the codebase style
        """

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert code reviewer and bug fixer. Generate minimal, precise code changes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        # Parse GPT-4's response to extract code changes and explanations
        solution = response.choices[0].message.content
        
        # Process the solution into structured diffs
        # This is a simplified version - in production you'd want more robust parsing
        diffs = []
        for file in analysis.affected_files:
            # Generate specific diff for each affected file
            file_prompt = f"Generate specific changes for file {file}:\n{solution}"
            file_response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Generate a precise git-style diff for the file."},
                    {"role": "user", "content": file_prompt}
                ],
                temperature=0.1
            )
            
            diff_content = file_response.choices[0].message.content
            # Count lines added/removed (simplified)
            lines_added = len([l for l in diff_content.split('\n') if l.startswith('+')])
            lines_removed = len([l for l in diff_content.split('\n') if l.startswith('-')])
            
            diffs.append(FileDiff(
                filename=file,
                diff=diff_content,
                lines_added=lines_added,
                lines_removed=lines_removed,
                explanation=f"Changes in {file} to address the root cause"
            ))

        return {
            "diffs": diffs,
            "analysis_summary": solution
        }
        
    except Exception as e:
        logger.error(f"GPT-4 analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GPT-4 analysis failed: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Developer Agent is running", "status": "healthy"}

@app.post("/generate-fix", response_model=DeveloperResponse)
async def generate_fix(analysis: PlannerAnalysis, ticket: TicketDetails, attempt: int = 1):
    logger.info(f"Generating fix for ticket {analysis.ticket_id} (attempt {attempt})")
    
    try:
        # Generate fix using GPT-4
        solution = analyze_with_gpt4(analysis, ticket, attempt)
        
        response = DeveloperResponse(
            ticket_id=analysis.ticket_id,
            diffs=solution["diffs"],
            commit_message=f"Fix for {analysis.ticket_id}: {analysis.root_cause}",
            attempt=attempt,
            analysis_summary=solution["analysis_summary"]
        )
        
        logger.info(f"Fix generated for ticket {analysis.ticket_id} (attempt {attempt})")
        return response
    
    except Exception as e:
        logger.error(f"Error generating fix for ticket {analysis.ticket_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating fix: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8002, reload=True)
