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

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Set up EasyRSA with proper permissions
RUN mkdir -p /etc/openvpn/easy-rsa && \
    cp -r /usr/share/easy-rsa/* /etc/openvpn/easy-rsa && \
    mkdir -p /etc/openvpn/client /var/www/templates && \
    chown -R appuser:appuser /etc/openvpn && \
    chmod -R 777 /etc/openvpn && \
    cd /etc/openvpn/easy-rsa && \
    sudo -u appuser ./easyrsa init-pki && \
    echo 'set_var EASYRSA_REQ_COUNTRY "US"\nset_var EASYRSA_REQ_PROVINCE "California"\nset_var EASYRSA_REQ_CITY "San Francisco"\nset_var EASYRSA_REQ_ORG "My Organization"\nset_var EASYRSA_REQ_EMAIL "admin@example.com"\nset_var EASYRSA_REQ_OU "My Organizational Unit"\nset_var EASYRSA_BATCH "1"' > /etc/openvpn/easy-rsa/pki/vars && \
    sudo -u appuser ./easyrsa build-ca nopass && \
    sudo -u appuser ./easyrsa gen-dh && \
    sudo -u appuser ./easyrsa build-server-full server nopass && \
    cp /etc/openvpn/easy-rsa/pki/ca.crt /etc/openvpn/ && \
    cp /etc/openvpn/easy-rsa/pki/issued/server.crt /etc/openvpn/ && \
    cp /etc/openvpn/easy-rsa/pki/private/server.key /etc/openvpn/ && \
    cp /etc/openvpn/easy-rsa/pki/dh.pem /etc/openvpn/ && \
    ln -s /etc/openvpn/easy-rsa/easyrsa /usr/local/bin/

# Create application directories
RUN mkdir -p /app/static /app/templates /app/prometheus && \
    chown -R appuser:appuser /app /var/www/templates

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_CONFIG=production
ENV PYTHONUNBUFFERED=1
ENV PATH="/etc/openvpn/easy-rsa:${PATH}"
ENV EASYRSA=/etc/openvpn/easy-rsa
ENV EASYRSA_PKI=/etc/openvpn/easy-rsa/pki

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--config", "gunicorn_config.py", "app:app"] 