import os
import subprocess
import shutil
from config import Config

def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Instead of changing directory, run shell command directly with more debug info
        result = subprocess.run([
            'bash', '-c',
            'cd /etc/openvpn/easy-rsa && ls -la && whoami && ./easyrsa build-client-full ' + provision_identity + ' nopass'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"EasyRSA command failed: stdout={result.stdout}, stderr={result.stderr}")
        
        # Create OpenVPN configuration
        config = f"""client
dev tun
proto udp
remote {Config.VPN_HOST} {Config.VPN_PORT}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-CBC
verb 3
<ca>
{open('/etc/openvpn/ca.crt').read()}
</ca>
<cert>
{open(f'/etc/openvpn/easy-rsa/pki/issued/{provision_identity}.crt').read()}
</cert>
<key>
{open(f'/etc/openvpn/easy-rsa/pki/private/{provision_identity}.key').read()}
</key>
"""
        
        # Write configuration to file
        with open(output_path, 'w') as f:
            f.write(config)
            
        return True
    except Exception as e:
        raise Exception(f"Failed to generate OpenVPN configuration: {str(e)}") 