# Use the official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir fastapi[all] pydantic sqlalchemy psycopg2-binary

# Copy application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Command to keep API running
CMD ["uvicorn", "app.endpoint:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
