import os
import subprocess
from config import Config
def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file using system certificates."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create OpenVPN configuration using system certificates
        common = "/etc/openvpn/server/client-common.txt"
        ca_path = "/etc/openvpn/server/easy-rsa/pki/ca.crt"
        cert_path = f"/etc/openvpn/server/easy-rsa/pki/issued/{provision_identity}.crt"
        key_path = f"/etc/openvpn/server/easy-rsa/pki/private/{provision_identity}.key"
        
        # Read certificate files
        try:
            with open(common, 'r') as f:
                common_content = f.read().strip()
            with open(ca_path, 'r') as f:
                ca_content = f.read().strip()
            
            with open(cert_path, 'r') as f:
                cert_content = f.read().strip()
            
            with open(key_path, 'r') as f:
                key_content = f.read().strip()
        except PermissionError:
            # If permission error, try using sudo cat
            ca_content = subprocess.check_output(['cat', ca_path]).decode('utf-8').strip()
            cert_content = subprocess.check_output(['cat', cert_path]).decode('utf-8').strip()
            key_content = subprocess.check_output(['cat', key_path]).decode('utf-8').strip()
        
        # Create OpenVPN configuration
        config = f"""{common_content}
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
            
        return True
    except Exception as e:
        print(f"Failed to generate OpenVPN configuration: {str(e)}")
        return False