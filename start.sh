
#!/bin/bash
echo "Starting BugFix AI system..."

# Create necessary directories if they don't exist
mkdir -p logs
mkdir -p code_repo

# Ensure directories have proper permissions
chmod 777 logs
chmod 777 code_repo

# Check if .env file exists at the root level
if [ ! -f ./.env ]; then
  echo "Error: .env file not found in the root directory!"
  echo "Please create an .env file based on .env.example before starting the system."
  exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker and try again."
  exit 1
fi

# Stop any existing containers first
echo "Stopping any existing containers..."
docker-compose down 

# Start the containers in detached mode with rebuilding
echo "Building and starting Docker containers..."
docker-compose build
docker-compose up -d

# Check if services started successfully
if [ $? -eq 0 ]; then
  echo "System started successfully! Frontend available at http://localhost:3000"
  echo "To view logs, run: ./logs.sh"
  echo "To stop the system, run: ./stop.sh"
  
  # Wait a bit for services to initialize
  echo "Waiting for services to initialize..."
  sleep 5
  
  # Show logs of all containers to verify startup
  echo "Checking initial container logs:"
  docker-compose logs --tail=20
  
  echo ""
  echo "For ongoing logs, run: docker-compose logs -f"
else
  echo "Error starting the system."
  echo "Running docker-compose logs to help diagnose the issue:"
  docker-compose logs
  echo "For more detailed logs of a specific service, run: docker-compose logs SERVICE_NAME"
  echo "For example: docker-compose logs backend"
  echo "To stop the system, run: ./stop.sh"
fi
