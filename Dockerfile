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

# Set up directory structure (but don't generate certificates)
RUN mkdir -p /etc/openvpn/easy-rsa/pki/issued \
    /etc/openvpn/easy-rsa/pki/private \
    /etc/openvpn/client \
    /var/www/templates

# Create non-root user and set permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/static /app/templates /app/prometheus && \
    chown -R appuser:appuser /app /etc/openvpn/client /var/www/templates && \
    chmod -R 755 /etc/openvpn/client

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
ENV PATH="/etc/openvpn/easy-rsa:${PATH}"
ENV EASYRSA=/etc/openvpn/easy-rsa
ENV EASYRSA_PKI=/etc/openvpn/easy-rsa/pki

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"]