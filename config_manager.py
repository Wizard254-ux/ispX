import os
import json
from config import Config

class ConfigManager:
    @staticmethod
    def load_config(config_path):
        """Load configuration from a file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    @staticmethod
    def save_config(config_path, config_data):
        """Save configuration to a file."""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)

    @staticmethod
    def get_client_config(provision_identity):
        """Get client configuration path."""
        return os.path.join(Config.VPN_CLIENT_DIR, f"{provision_identity}.ovpn")

    @staticmethod
    def get_template_path(template_name):
        """Get template file path."""
        return os.path.join(Config.HOTSPOT_TEMPLATE_DIR, template_name) 