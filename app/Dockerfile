# Production Dockerfile for Streamlit app
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy application code
COPY . .

# Copy Streamlit configuration
COPY .streamlit/ .streamlit/

# Create non-root user
RUN adduser --disabled-password --gecos '' streamlit-user && \
    chown -R streamlit-user:streamlit-user /app
USER streamlit-user

# Expose port 8080 for ALB
EXPOSE 8080

# Health check for ALB
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/app/health || exit 1

# Run Streamlit with config file
CMD ["streamlit", "run", "app.py"]