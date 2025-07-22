FROM rayproject/ray:2.5.0-gpu

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose service port
EXPOSE 8001

# Run the service
CMD ["python", "-m", "agent_factory.main"]