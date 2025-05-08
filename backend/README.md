
# BugFix AI Backend

FastAPI backend service that coordinates the bug fix workflow.

## Environment Setup

1. Copy the environment template file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your credentials:
   - `GITHUB_TOKEN`: Your GitHub personal access token
   - `JIRA_TOKEN`: Your JIRA API token
   - `JIRA_USER`: Your JIRA email address
   - `JIRA_URL`: Your JIRA instance URL

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

## API Documentation

Once running, visit http://localhost:8000/docs for the OpenAPI documentation.

## Security Notes

- Never commit your `.env` file to version control
- Keep your API tokens secure and rotate them regularly
- The `.env` file is listed in .gitignore to prevent accidental commits

