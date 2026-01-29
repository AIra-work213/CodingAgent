# Single-stage build for Coding Agents SDLC
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies to system location
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure /usr/local/bin is accessible and binaries are executable
RUN chmod -R 755 /usr/local/bin && \
    chmod +x /usr/local/bin/uvicorn /usr/local/bin/gunicorn 2>/dev/null || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
