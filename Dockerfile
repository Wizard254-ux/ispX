# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install only necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    # openvpn \  # Still install the openvpn package for the client tools
    && rm -rf /var/lib/apt/lists/*


# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/static /app/templates /app/prometheus \
    /var/www/templates && \
    chown -R appuser:appuser /app /var/www/templates

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_CONFIG=production
ENV PYTHONUNBUFFERED=1
ENV REDIS_URL=redis://redis:6379/0

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]