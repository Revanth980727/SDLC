
# Planner Agent

This agent analyzes JIRA tickets and identifies affected code areas.

## Setup

1. Ensure OpenAI API key is set in Supabase secrets
2. Build the container:
   ```bash
   docker build -t bugfix-planner .
   ```

## Configuration

The agent requires:
- OpenAI API access
- Access to the code repository
- Connection to the main backend service

See root README for full setup instructions.
