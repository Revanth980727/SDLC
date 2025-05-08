
# Bug Fix AI Agents

This directory contains the modular agent system for automatic bug fixing.

## Agents

### PlannerAgent
Analyzes JIRA bug tickets and identifies files that need to be modified.

### DeveloperAgent
Generates code fixes based on the planner's analysis using GPT-4.

### QAAgent
Runs tests on the fixed code to verify it works correctly.

### CommunicatorAgent
Updates JIRA with progress and creates Pull Requests in GitHub.

## Usage

Each agent can be run independently or orchestrated together using the AgentController.

### Example usage:

```python
from agents.agent_controller import AgentController

# Initialize the controller
controller = AgentController()

# Process a ticket
ticket_data = {
    "ticket_id": "PROJ-123",
    "title": "Bug: Application crashes when user clicks submit button",
    "description": "When a user fills out the form and clicks submit, the application crashes..."
}

# Run the full pipeline
result = await controller.process_ticket(ticket_data)
```

## Environment Variables

The agents require the following environment variables to be set:

- `OPENAI_API_KEY`: API key for OpenAI GPT-4
- `GITHUB_TOKEN`: GitHub personal access token
- `GITHUB_REPO_OWNER`: Owner of the GitHub repository
- `GITHUB_REPO_NAME`: Name of the GitHub repository
- `JIRA_URL`: URL of the JIRA instance
- `JIRA_USER`: JIRA username
- `JIRA_TOKEN`: JIRA API token
- `REPO_PATH`: Path to the local repository (default: /mnt/codebase)
- `TEST_COMMAND`: Command to run tests (default: pytest)
- `MAX_RETRIES`: Maximum number of fix attempts (default: 4)

## Logs

Logs are stored in the `logs/` directory and include:

- Agent activity logs
- Generated patches
- Test results
