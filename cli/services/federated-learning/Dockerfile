FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY federated_learning/ ./federated_learning/

# Expose port
EXPOSE 8003

# Run the service
CMD ["python", "-m", "uvicorn", "federated_learning.main:app", "--host", "0.0.0.0", "--port", "8003"]