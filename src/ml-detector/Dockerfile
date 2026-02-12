FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY anomaly_detector.py .

# Run the detector
CMD ["python", "-u", "anomaly_detector.py"]
