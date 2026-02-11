FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY health_scorer.py .

# Run the health scorer
CMD ["python", "-u", "health_scorer.py"]
