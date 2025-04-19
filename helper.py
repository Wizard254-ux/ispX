import os
import subprocess
from config import Config

def generate_openvpn_config(provision_identity, output_path):
    """Generate OpenVPN client configuration file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate client certificate
        subprocess.run([
            'easyrsa', 'build-client-full', provision_identity, 'nopass'
        ], check=True)
        
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
{open(f'/etc/openvpn/ca.crt').read()}
</ca>
<cert>
{open(f'/etc/openvpn/pki/issued/{provision_identity}.crt').read()}
</cert>
<key>
{open(f'/etc/openvpn/pki/private/{provision_identity}.key').read()}
</key>
"""
        
        # Write configuration to file
        with open(output_path, 'w') as f:
            f.write(config)
            
        return True
    except Exception as e:
        raise Exception(f"Failed to generate OpenVPN configuration: {str(e)}") 