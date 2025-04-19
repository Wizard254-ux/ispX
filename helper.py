import os
import subprocess
from celery import shared_task
from config import Config


def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate certificate on the host system using subprocess
        # Note: This requires the container to have appropriate permissions
        host_cmd = f"cd /etc/openvpn/easy-rsa && ./easyrsa build-client-full {provision_identity} nopass"
        
        # Use sudo if needed (this might require setting up passwordless sudo in the container)
        result = subprocess.run(host_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to generate client certificate: {result.stderr}")
        
        # Read certificate files
        with open('/etc/openvpn/easy-rsa/pki/ca.crt', 'r') as f:
            ca_cert = f.read().strip()
            
        with open(f'/etc/openvpn/easy-rsa/pki/issued/{provision_identity}.crt', 'r') as f:
            client_cert = f.read().strip()
            
        with open(f'/etc/openvpn/easy-rsa/pki/private/{provision_identity}.key', 'r') as f:
            client_key = f.read().strip()
        
        # Create client configuration with proper certificate verification options
        config = f"""client
dev tun
proto tcp
remote 34.60.44.191 {Config.VPN_PORT}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-CBC
data-ciphers AES-256-CBC
data-ciphers-fallback AES-256-CBC
verify-x509-name server name
verb 3

<ca>
{ca_cert}
</ca>
<cert>
{client_cert}
</cert>
<key>
{client_key}
</key>
"""
        
        # Write configuration to file
        with open(output_path, 'w') as f:
            f.write(config)
        
        return True
    except Exception as e:
        raise Exception(f"Failed to generate OpenVPN configuration: {str(e)}")