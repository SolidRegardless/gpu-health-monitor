FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for MLflow
RUN mkdir -p /mlflow/artifacts /mlflow/runs

# Expose MLflow UI port
EXPOSE 5000

# Start MLflow server with mlflow schema
CMD ["mlflow", "server", \
     "--backend-store-uri", "postgresql://gpu_monitor:gpu_monitor_secret@timescaledb:5432/gpu_health?options=-csearch_path%3Dmlflow,public", \
     "--default-artifact-root", "/mlflow/artifacts", \
     "--host", "0.0.0.0", \
     "--port", "5000"]
