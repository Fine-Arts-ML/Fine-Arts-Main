# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Build argument for version
ARG APP_VERSION=1.0.0

# Set environment variable for the version
ENV APP_VERSION=${APP_VERSION}

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy application code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Set application label
LABEL version="${APP_VERSION}"
LABEL description="Shop Management Streamlit App"

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
