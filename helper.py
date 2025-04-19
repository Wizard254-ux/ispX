import os
import subprocess
from celery import shared_task
from config import Config


def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Change to the EasyRSA directory
        os.chdir('/etc/openvpn/easy-rsa')
        
        # Generate client certificate
        subprocess.run([
            './easyrsa', 'build-client-full', provision_identity, 'nopass'
        ], check=True)
        
        # Create enhanced OpenVPN configuration
        config = f"""client
dev tun
proto tcp
remote 34.60.44.191 {Config.VPN_PORT}
resolv-retry infinite
nobind
persist-key
persist-tun
auth SHA1
cipher AES-256-CBC
data-ciphers AES-256-CBC
data-ciphers-fallback AES-256-CBC
verb 3

<ca>
{open('/etc/openvpn/ca.crt').read().strip()}
</ca>
<cert>
{open(f'/etc/openvpn/easy-rsa/pki/issued/{provision_identity}.crt').read().strip()}
</cert>
<key>
{open(f'/etc/openvpn/easy-rsa/pki/private/{provision_identity}.key').read().strip()}
</key>
"""
        
        # Write configuration to file
        with open(output_path, 'w') as f:
            f.write(config)
            
        return True
    except Exception as e:
        raise Exception(f"Failed to generate OpenVPN configuration: {str(e)}")