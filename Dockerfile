# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    openvpn \
    easy-rsa \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/static /app/templates /app/prometheus \
    /etc/openvpn/client /var/www/templates && \
    chown -R appuser:appuser /app /etc/openvpn/client /var/www/templates

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

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"] 