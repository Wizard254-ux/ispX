import os
import subprocess
from config import Config

def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file using system certificates."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Paths to certificate files
        ca_path = "/etc/openvpn/easy-rsa/pki/ca.crt"
        cert_path = f"/etc/openvpn/easy-rsa/pki/issued/{provision_identity}.crt"
        key_path = f"/etc/openvpn/easy-rsa/pki/private/{provision_identity}.key"
        
        # Debug info
        print(f"Looking for CA at: {ca_path}")
        print(f"Looking for cert at: {cert_path}")
        print(f"Looking for key at: {key_path}")
        
        # Check if files exist
        if not os.path.exists(ca_path):
            print(f"CA file not found at: {ca_path}")
            # Try to find CA file
            try:
                find_cmd = "find /etc -name 'ca.crt' | head -1"
                ca_path = subprocess.check_output(find_cmd, shell=True).decode('utf-8').strip()
                print(f"Found CA at: {ca_path}")
            except Exception as e:
                print(f"Error finding CA: {str(e)}")
                
        if not os.path.exists(cert_path):
            print(f"Cert file not found at: {cert_path}")
            # Try to find cert file
            try:
                find_cmd = f"find /etc -name '{provision_identity}.crt'"
                cert_path = subprocess.check_output(find_cmd, shell=True).decode('utf-8').strip()
                print(f"Found cert at: {cert_path}")
            except Exception as e:
                print(f"Error finding cert: {str(e)}")
                
        if not os.path.exists(key_path):
            print(f"Key file not found at: {key_path}")
            # Try to find key file
            try:
                find_cmd = f"find /etc -name '{provision_identity}.key'"
                key_path = subprocess.check_output(find_cmd, shell=True).decode('utf-8').strip()
                print(f"Found key at: {key_path}")
            except Exception as e:
                print(f"Error finding key: {str(e)}")
        
        # Read certificate files
        try:
            with open(ca_path, 'r') as f:
                ca_content = f.read().strip()
            
            with open(cert_path, 'r') as f:
                cert_content = f.read().strip()
            
            with open(key_path, 'r') as f:
                key_content = f.read().strip()
        except Exception as e:
            print(f"Error reading certificate files directly: {str(e)}")
            # Fall back to using subprocess
            try:
                ca_content = subprocess.check_output(['cat', ca_path], stderr=subprocess.STDOUT).decode('utf-8').strip()
                cert_content = subprocess.check_output(['cat', cert_path], stderr=subprocess.STDOUT).decode('utf-8').strip()
                key_content = subprocess.check_output(['cat', key_path], stderr=subprocess.STDOUT).decode('utf-8').strip()
            except subprocess.CalledProcessError as e:
                print(f"Error reading files with cat: {e.output.decode('utf-8')}")
                raise
        
        # Create OpenVPN configuration
        config = f"""client
dev tun
proto tcp
remote 35.226.234.138 {Config.VPN_PORT}
resolv-retry infinite
remote-cert-tls server
nobind
persist-key
persist-tun
auth SHA256
cipher AES-256-CBC
data-ciphers AES-256-CBC
data-ciphers-fallback AES-256-CBC
verb 3
tls-client


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
        
        # Write configuration to file
        with open(output_path, 'w') as f:
            f.write(config)
        
        print(f"Successfully generated OpenVPN config at: {output_path}")
        return True
    except Exception as e:
        print(f"Failed to generate OpenVPN configuration: {str(e)}")
        return False