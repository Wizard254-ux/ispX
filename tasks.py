import os
import subprocess
from celery import Celery
from config import Config
from helper import generate_openvpn_config

# Initialize Celery
celery = Celery('tasks', broker=Config.CELERY_BROKER_URL)

@celery.task
def generate_certificate(provision_identity):
    """Generate OpenVPN client certificate and configuration."""
    try:
        # Ensure the client name is valid
        if not provision_identity.isalnum():
            return {
                "status": "error",
                "message": "Invalid client name. Use only alphanumeric characters.",
                "provision_identity": provision_identity
            }
        
        # Path to the EasyRSA script on the host system
        easyrsa_path = "/etc/openvpn/easy-rsa/easyrsa"
        
        # Generate the client certificate and key
        subprocess.run([
            easyrsa_path, 
            "--pki-dir=/etc/openvpn/easy-rsa/pki",
            "build-client-full", 
            provision_identity, 
            "nopass"
        ], check=True)
        
        # Generate the client configuration file
        output_path = f"{Config.VPN_CLIENT_DIR}/{provision_identity}.ovpn"
        if generate_openvpn_config(provision_identity, output_path):
            return {
                "status": "success",
                "message": "Certificate generated successfully",
                "provision_identity": provision_identity
            }
        else:
            return {
                "status": "error",
                "message": "Failed to generate client configuration",
                "provision_identity": provision_identity
            }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Certificate generation failed: {str(e)}",
            "provision_identity": provision_identity
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate certificate: {str(e)}",
            "provision_identity": provision_identity
        }
