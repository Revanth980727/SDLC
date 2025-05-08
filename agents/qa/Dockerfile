
FROM python:3.10-slim

WORKDIR /app

# Install git and other essential tools
RUN apt-get update && \
    apt-get install -y git curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent code to the correct location
COPY ./qa/agent.py /app/
COPY ./utils /app/utils/

# Create proper directories with permissions
RUN mkdir -p /app/code_repo && chmod 777 /app/code_repo
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Explicitly install pytest (use pip3 to ensure it installs to the correct Python version)
RUN pip install pytest==7.4.3 --upgrade && \
    pip list | grep pytest && \
    which pytest && \
    python -c "import sys; print(sys.path)" && \
    python -c "import pytest; print(f'pytest version: {pytest.__version__}')" || echo "Failed to import pytest"

# Set environment variables
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV TEST_COMMAND="python -m pytest"

# Print environment info for debugging
RUN echo "Python version:" && python --version
RUN echo "Pytest version:" && python -m pytest --version || echo "Failed to get pytest version"
RUN echo "PATH:" && echo $PATH
RUN echo "PYTHONPATH:" && echo $PYTHONPATH

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8003"]