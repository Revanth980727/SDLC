
#!/bin/bash

if [ -z "$1" ]; then
  echo "Showing logs for all services. Press Ctrl+C to exit."
  docker-compose logs -f
else
  echo "Showing logs for $1. Press Ctrl+C to exit."
  docker-compose logs -f "$1"
fi

echo ""
echo "Usage: ./logs.sh [service_name]"
echo "Available services: frontend, backend, planner, developer, qa, communicator, jira_service, github_service"
