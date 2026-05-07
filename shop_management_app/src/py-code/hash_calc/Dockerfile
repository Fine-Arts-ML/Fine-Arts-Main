FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy hash_calc service code
COPY . /app/hash_calc

# Expose port
EXPOSE 8078

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Run the service (using package module path for relative imports)
CMD ["uvicorn", "hash_calc.main:app", "--host", "0.0.0.0", "--port", "8078"]
