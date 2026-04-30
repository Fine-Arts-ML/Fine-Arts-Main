FROM python:3.11-slim

# Set working directory
WORKDIR /py-code

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY rag_search/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy RAG service code
COPY rag_search/ rag_search/

# Create directories for models and index
RUN mkdir -p /py-code/Models && mkdir -p /data/tfidf-index

# Expose port
EXPOSE 8079

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the service
CMD ["uvicorn", "rag_search.main:app", "--host", "0.0.0.0", "--port", "8079"]
