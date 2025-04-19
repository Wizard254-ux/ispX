import os
import subprocess
from celery import shared_task
from config import Config


def generate_openvpn_config(provision_identity, output_path):
    pki_path = "/etc/openvpn/easy-rsa/pki"

    if not os.path.exists(pki_path):
        init_cmd = "sudo /etc/openvpn/easy-rsa/easyrsa init-pki"
        init_result = subprocess.run(init_cmd, shell=True, capture_output=True, text=True)

        if init_result.returncode != 0:
            raise Exception(f"Failed to initialize PKI: {init_result.stderr}")

    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate client certificate using sudo
        sudo_cmd = f"sudo /etc/openvpn/easy-rsa/easyrsa build-client-full {provision_identity} nopass"
        result = subprocess.run(sudo_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to generate client certificate: {result.stderr}")
        
        # Read certificate files using sudo
        ca_cert = subprocess.check_output("sudo cat /etc/openvpn/easy-rsa/pki/ca.crt", shell=True).decode().strip()
        client_cert = subprocess.check_output(f"sudo cat /etc/openvpn/easy-rsa/pki/issued/{provision_identity}.crt", shell=True).decode().strip()
        client_key = subprocess.check_output(f"sudo cat /etc/openvpn/easy-rsa/pki/private/{provision_identity}.key", shell=True).decode().strip()
        
        # Create client configuration
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
