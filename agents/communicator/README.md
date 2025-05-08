
# Communicator Agent

This agent handles updates to JIRA tickets and GitHub PRs.

## Setup

1. Ensure these credentials are set in Supabase secrets:
   - JIRA_API_TOKEN
   - JIRA_USER
   - JIRA_URL
   - GITHUB_TOKEN

2. Build the container:
   ```bash
   docker build -t bugfix-communicator .
   ```

## Configuration

The agent requires:
- JIRA API access
- GitHub API access
- Connection to the main backend service

See root README for full setup instructions.
