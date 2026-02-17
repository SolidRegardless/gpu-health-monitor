FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service script
COPY market_price_fetcher.py .

CMD ["python", "-u", "market_price_fetcher.py"]
