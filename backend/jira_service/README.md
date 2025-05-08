
# JIRA Service

This service monitors JIRA for new bug tickets and processes them through the BugFix AI workflow.

## Features

- Polls the JIRA API at regular intervals (default: 30 seconds)
- Fetches bug tickets with status "To Do" or "Open"
- Updates ticket status and adds comments as the ticket progresses
- Handles API failures with retries and exponential backoff
- Configurable through environment variables

## Environment Variables

Create a `.env` file with the following variables:

```
# JIRA Configuration
JIRA_URL=https://your-company.atlassian.net
JIRA_USERNAME=your_email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=YOUR_PROJECT
JIRA_POLL_INTERVAL=30

# Logging
LOG_LEVEL=INFO
```

## Running the Service

### Direct Execution

```bash
cd /path/to/project
python -m backend.jira_service.run_service
```

### Within Docker

The service is designed to be integrated into the docker-compose.yml configuration.

## Integration

This service is designed to integrate with the main BugFix AI workflow by:

1. Detecting new bug tickets in JIRA
2. Initiating the agent workflow for these tickets
3. Updating ticket status and comments as processing occurs
4. Completing the workflow with a resolution or escalation

## Logging

Logs are output to the console and can be configured with the LOG_LEVEL environment variable.
