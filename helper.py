import os
import subprocess
from config import Config

def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file using system certificates."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create OpenVPN configuration using system certificates
        ca_path = "/etc/openvpn/easy-rsa/pki/ca.crt"
        cert_path = f"/etc/openvpn/easy-rsa/pki/issued/{provision_identity}.crt"
        key_path = f"/etc/openvpn/easy-rsa/pki/private/{provision_identity}.key"
        tls_auth_path = "/etc/openvpn/server/ta.key"  # TLS auth key path
        
        # Read certificate files
        try:
            with open(ca_path, 'r') as f:
                ca_content = f.read().strip()
            
            with open(cert_path, 'r') as f:
                cert_content = f.read().strip()
            
            with open(key_path, 'r') as f:
                key_content = f.read().strip()
                
            # Try to read TLS auth key if it exists
            tls_auth_content = ""
            if os.path.exists(tls_auth_path):
                with open(tls_auth_path, 'r') as f:
                    tls_auth_content = f.read().strip()
        except PermissionError:
            # If permission error, try using sudo cat
            ca_content = subprocess.check_output(['sudo', 'cat', ca_path]).decode('utf-8').strip()
            cert_content = subprocess.check_output(['sudo', 'cat', cert_path]).decode('utf-8').strip()
            key_content = subprocess.check_output(['sudo', 'cat', key_path]).decode('utf-8').strip()
            
            # Try to read TLS auth key if it exists
            tls_auth_content = ""
            if os.path.exists(tls_auth_path):
                tls_auth_content = subprocess.check_output(['sudo', 'cat', tls_auth_path]).decode('utf-8').strip()
        
        # Create OpenVPN configuration
        config = f"""client
dev tun
proto tcp
remote 35.226.234.138 {Config.VPN_PORT}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-CBC
data-ciphers AES-256-CBC
data-ciphers-fallback AES-256-CBC
tls-client
key-direction 1
verb 3

<ca>
{ca_content}
</ca>

<cert>
{cert_content}
</cert>

<key>
{key_content}
</key>
"""

        # Add TLS auth if available
        if tls_auth_content:
            config += f"""
<tls-auth>
{tls_auth_content}
</tls-auth>
"""
        
        # Write configuration to file
        with open(output_path, 'w') as f:
            f.write(config)
            
        return True
    except Exception as e:
        print(f"Failed to generate OpenVPN configuration: {str(e)}")
        return False