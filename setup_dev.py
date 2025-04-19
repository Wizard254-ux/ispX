import os
import subprocess
from config import Config

def setup_development_environment():
    """Set up development environment."""
    try:
        # Create necessary directories
        os.makedirs(Config.VPN_CLIENT_DIR, exist_ok=True)
        os.makedirs(Config.HOTSPOT_TEMPLATE_DIR, exist_ok=True)
        
        # Install OpenVPN if not present
        try:
            subprocess.run(['which', 'openvpn'], check=True)
        except subprocess.CalledProcessError:
            print("Installing OpenVPN...")
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'openvpn'], check=True)
        
        # Install EasyRSA if not present
        try:
            subprocess.run(['which', 'easyrsa'], check=True)
        except subprocess.CalledProcessError:
            print("Installing EasyRSA...")
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'easy-rsa'], check=True)
        
        print("Development environment setup complete!")
        
    except Exception as e:
        print(f"Error setting up development environment: {str(e)}")
        raise

if __name__ == '__main__':
    setup_development_environment() 