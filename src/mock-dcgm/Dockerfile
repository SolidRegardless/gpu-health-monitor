FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask==3.0.0

# Copy application
COPY mock_dcgm.py .

# Expose metrics port
EXPOSE 9400

# Run the mock DCGM exporter
CMD ["python", "mock_dcgm.py"]
