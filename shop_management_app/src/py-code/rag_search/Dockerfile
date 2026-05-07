FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory to parent of rag_search package
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy RAG service code into package directory
COPY . /app/rag_search

# Create directories for models and index
RUN mkdir -p /app/rag_search/Models && mkdir -p /app/rag_search/tfidf-index

# Expose port
EXPOSE 8079

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Run the service (using package module path for relative imports)
CMD ["uvicorn", "rag_search.main:app", "--host", "0.0.0.0", "--port", "8079"]
