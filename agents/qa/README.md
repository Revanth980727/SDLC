
# QA Agent

This agent runs tests to validate the generated fixes.

## Setup

1. Ensure OpenAI API key is set in Supabase secrets
2. Build the container:
   ```bash
   docker build -t bugfix-qa .
   ```

## Configuration

The agent requires:
- OpenAI API access
- Access to the code repository
- Connection to the main backend service

See root README for full setup instructions.
