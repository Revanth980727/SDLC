FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y git curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs
RUN mkdir -p /app/code_repo && chmod 777 /app/code_repo

COPY . .

# Set up environment variables
ENV PYTHONPATH=/app

# Run the orchestrator with the correct Python module path
CMD ["python", "-m", "orchestrator.start_orchestrator"]