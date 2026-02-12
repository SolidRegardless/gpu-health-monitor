FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alert_manager.py .

CMD ["python", "-u", "alert_manager.py"]
