
# BugFix AI System

An autonomous AI tool that fixes bugs in your codebase by analyzing JIRA tickets and generating code fixes.

## System Overview

BugFix AI is a containerized system that uses multiple specialized AI agents to automatically fix bugs in your codebase:

1. **Planner Agent** - Analyzes JIRA tickets and identifies affected code areas
2. **Developer Agent** - Generates code fixes based on the planner's analysis
3. **QA Agent** - Validates the fixes by running tests
4. **Communicator Agent** - Updates JIRA tickets and creates GitHub PRs

Each agent runs as a separate microservice and communicates through REST APIs. The main backend coordinates the workflow between agents, and a React frontend provides monitoring and control capabilities.

## Prerequisites

Before running this application, you'll need:

1. **Docker** and **Docker Compose** installed on your system
   - [Install Docker](https://docs.docker.com/get-docker/)
   - [Install Docker Compose](https://docs.docker.com/compose/install/)

2. **API Credentials**:
   - **GitHub**: A personal access token with repo permissions
     - Go to GitHub Settings > Developer Settings > Personal Access Tokens
     - Generate a new token with 'repo' scope
   
   - **JIRA**: API token and account email
     - Go to https://id.atlassian.com/manage-profile/security/api-tokens
     - Create an API token
     - Note your Atlassian account email and JIRA domain URL
   
   - **OpenAI**: API key for GPT-4
     - Go to https://platform.openai.com/account/api-keys
     - Create a new API key

## Setup Instructions

1. **Clone this repository**:
   ```bash
   git clone https://github.com/yourusername/bugfix-ai.git
   cd bugfix-ai
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your API credentials

3. **Start the system**:
   ```bash
   chmod +x start.sh stop.sh logs.sh
   ./start.sh
   ```

This will:
- Create necessary directories
- Build and start all Docker containers
- Make the frontend available at http://localhost:3000

## Using the System

### Web Interface

1. Open http://localhost:3000 in your browser
2. You'll see the dashboard with:
   - List of active tickets
   - Status of each ticket
   - Detailed view of agent outputs
   
3. **Manually trigger a fix**:
   - Enter a JIRA ticket ID in the form
   - Click "Fix Bug" to start the process

### Monitoring Logs

To view logs for all services:
```bash
./logs.sh
```

To view logs for a specific service:
```bash
./logs.sh backend
./logs.sh planner
./logs.sh developer
./logs.sh qa
./logs.sh communicator
```

### Stopping the System

```bash
./stop.sh
```

## System Architecture

### Agent System

The application uses a multi-agent architecture with four specialized AI agents:

1. **Planner Agent** - Analyzes tickets and identifies affected code areas
2. **Developer Agent** - Generates code fixes based on the planner's analysis
3. **QA Agent** - Validates the fixes by running tests
4. **Communicator Agent** - Updates JIRA tickets and creates GitHub PRs

### API Integration Clients

This system includes API client libraries for interacting with external services:

- **JIRA Client** (`agents/utils/jira_client.py`): Fetch and update JIRA tickets
- **GitHub Client** (`agents/utils/github_client.py`): Manage repository operations
- **OpenAI Client** (`agents/utils/openai_client.py`): Generate code fixes using GPT-4

## Docker Container Structure

- **frontend**: React web interface (port 3000)
- **backend**: Main orchestration API (port 8000)
- **planner**: Planner Agent microservice (port 8001)
- **developer**: Developer Agent microservice (port 8002)
- **qa**: QA Agent microservice (port 8003)
- **communicator**: Communicator Agent microservice (port 8004)
- **jira_service**: Background service monitoring JIRA
- **github_service**: Background service for GitHub operations

## Troubleshooting

### Common Issues

1. **Docker containers not starting**
   - Check if Docker daemon is running: `docker ps`
   - Verify port availability: make sure ports 3000, 8000-8004 are not in use
   - Check logs: `./logs.sh`

2. **API connectivity issues**
   - Verify API credentials in `.env` file
   - Check network connectivity to JIRA/GitHub
   - Look for 401/403 errors in logs

3. **Agent failures**
   - Check agent-specific logs: `./logs.sh [agent_name]`
   - Verify OpenAI API key is valid
   - Check if code repository path exists and is accessible

### Container Health Checks

To check the health of all containers:
```bash
docker-compose ps
```

Look for containers in an unhealthy state.

### Restarting Individual Services

To restart a specific service:
```bash
docker-compose restart [service_name]
```

Example: `docker-compose restart developer`

## Security Notes

- Never commit your `.env` file to version control
- Keep your API tokens secure and rotate them regularly
- The `.env` file is listed in .gitignore to prevent accidental commits

## License

MIT


# Test change for Jira GitHub link

