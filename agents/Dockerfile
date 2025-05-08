
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y git curl && \
    rm -rf /var/lib/apt/lists/*
    
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . /app/agents/

# Create necessary directories

RUN mkdir -p /mnt/codebase

# Set up environment variables
ENV PYTHONPATH=/app

# Set default command
CMD ["python", "-m", "agents.agent_controller"]
