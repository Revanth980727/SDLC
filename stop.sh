
#!/bin/bash
echo "Stopping BugFix AI system..."

# Stop and remove containers, networks, and volumes
docker-compose down

if [ $? -eq 0 ]; then
  echo "System stopped successfully!"
else
  echo "Error stopping the system. You may need to manually stop containers."
fi
