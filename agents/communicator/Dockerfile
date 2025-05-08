FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y git curl && \
    rm -rf /var/lib/apt/lists/*

COPY communicator/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent code and github utilities
COPY communicator/agent.py /app/
COPY utils /app/utils/


# Create necessary directories with proper permissions
RUN mkdir -p /app/utils
RUN mkdir -p /app/code_repo && chmod 777 /app/code_repo
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Make sure uvicorn is in the PATH
ENV PATH="/usr/local/bin:${PATH}"

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8004"]