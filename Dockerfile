# GrantScout — Amazon Bedrock AgentCore Deployment Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project definition
COPY pyproject.toml ./

# Install python dependencies via uv
RUN uv pip install --system -e .

# Copy application source code
COPY backend/ ./backend/
COPY frontend/dist/ ./frontend/dist/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Expose backend API port
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
