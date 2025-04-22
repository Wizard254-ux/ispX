"""
This instance is hosted on a VPN server that will help to auto generate or provision new clients.
It returns certs for each client and also stores them for remote connection with Mikrotik
It wil be used by the main site (myisp.com) to generate new vpn clients for mikrotik connection
 and listen for a successful connection as well as sending mikrotik commands to perform specif jobs.
It will also be accessed with Mikrotik to fetch these certs and install them on behalf of the user
"""
import os
from flask import Flask, jsonify, send_file, send_from_directory,request
import openvpn_api
from celery.result import AsyncResult
from config import Config
from security import validate_provision_identity, generate_secret, require_secret
from tasks import generate_certificate,celery
from werkzeug.urls import url_quote
import redis
import json
from main import admin_routs

app = Flask(__name__)
app.config.from_object(Config)

# Initialize OpenVPN API
try:
    print(f"Attempting to connect to OpenVPN management at {Config.VPN_HOST}:{Config.VPN_PORT}")
    v = openvpn_api.VPN(Config.VPN_HOST, Config.VPN_PORT)
    # Test connection
    status = v.get_status()
    print(f"Successfully connected to OpenVPN management at {Config.VPN_HOST}:{Config.VPN_PORT}")
    print(f"OpenVPN server version: {status.version}")
    print(f"Connected clients: {len(status.client_list) if hasattr(status, 'client_list') else 0}")
except Exception as e:
    print(f"WARNING: Failed to connect to OpenVPN management interface: {str(e)}")
    print(f"Using host: {Config.VPN_HOST}, port: {Config.VPN_PORT}")
    print(f"Exception type: {type(e).__name__}")
    v = None  # Set to None so we can check later

@app.route('/mikrotik/openvpn/create_provision/<provision_identity>', methods=["POST"])
def mtk_create_new_provision(provision_identity):
    """Create a new openVPN client with given name.
    provision_identity: its just like name instance  (e.g client1,client2,...)
    """
    # with REQUEST_LATENCY.labels(endpoint='/create_provision').time():
    try:
        # Validate provision identity
        # validate_provision_identity(provision_identity)

        # Check if client already exists
        client_conf_path = f"{Config.VPN_CLIENT_DIR}/{provision_identity}.ovpn"
        if os.path.exists(client_conf_path):
            # REQUEST_COUNT.labels(method='POST', endpoint='/create_provision', status='400').inc()
            return jsonify({"error": "Client already exists"}), 400

        # Start async certificate generation
        task = generate_certificate.delay(provision_identity)

        # Generate and return the secret
        secret = generate_secret(provision_identity)

        # REQUEST_COUNT.labels(method='POST', endpoint='/create_provision', status='202').inc()
        return jsonify({
            "status": "processing",
            "task_id": task.id,
            "provision_identity": provision_identity,
            "secret": secret
        }), 202

    except ValueError as e:
        # REQUEST_COUNT.labels(method='POST', endpoint='/create_provision', status='400').inc()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # REQUEST_COUNT.labels(method='POST', endpoint='/create_provision', status='500').inc()
        return jsonify({"error": "Internal server error"}), 500


@app.route('/mikrotik/openvpn/task/<task_id>')
def get_task_status(task_id):
    """Get the status of a certificate generation task."""
    try:
        task_result = AsyncResult(task_id, app=celery)
        
        # Force result retrieval
        if task_result.ready():
            result = task_result.get()
            if result['status'] == 'success':
                return jsonify({
                    "status": "success",
                    "message": "Certificate generated successfully",
                    "provision_identity": result.get('provision_identity'),
                    "task_id": task_id,
                    "state": "completed"
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "message": result.get('message', 'Unknown error'),
                    "provision_identity": result.get('provision_identity'),
                    "task_id": task_id,
                    "state": "failed"
                }), 400
        else:
            # If not ready, check Redis directly
            r = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                password=Config.REDIS_PASSWORD,
                decode_responses=True
            )
            redis_key = f"celery-task-meta-{task_id}"
            if r.exists(redis_key):
                result = r.get(redis_key)
                result_data = json.loads(result)
                if result_data['status'] == 'SUCCESS':
                    return jsonify({
                        "status": "success",
                        "message": "Certificate generated successfully",
                        "provision_identity": result_data['result']['provision_identity'],
                        "task_id": task_id,
                        "state": "completed"
                    }), 200
                else:
                    return jsonify({
                        "status": "error",
                        "message": result_data.get('result', {}).get('message', 'Unknown error'),
                        "task_id": task_id,
                        "state": "failed"
                    }), 400
            
            return jsonify({
                "status": "pending",
                "message": "Certificate generation in progress",
                "task_id": task_id,
                "state": task_result.state
            }), 202
    except Exception as e:
        print(f"Error getting task status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error getting task status: {str(e)}",
            "task_id": task_id
        }), 500


@app.route("/mikrotik/openvpn/key")
@require_secret
def mtk_openvpn(provision_identity,secret):
    """Returning openVPN client of a given provision_identity"""
    try:
        path = f"{Config.VPN_CLIENT_DIR}/{provision_identity}.ovpn"
        if not os.path.exists(path):
            return jsonify({"error": "Configuration not found"}), 404
        return send_file(path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500


@app.route("/server/ip/")
@require_secret
def getIpAddress(provision_identity, secret):
    """Get client IP from OpenVPN status log file"""
    try:
        print(f"Getting IP for provision_identity: {provision_identity}")
        
        # Path to the OpenVPN status log file
        status_file = "/var/log/openvpn/openvpn-status.log"
        
        if not os.path.exists(status_file):
            print(f"OpenVPN status file not found at {status_file}")
            return jsonify({"error": "OpenVPN status file not found"}), 404
            
        # Read and parse the status file
        with open(status_file, 'r') as f:
            content = f.read()
            
        print("\nOpenVPN Status Log Content:")
        print("-" * 50)
        print(content)
        print("-" * 50)
        
        # Re-read for actual parsing
        with open(status_file, 'r') as f:
            lines = f.readlines()
        
        # Find both CLIENT_LIST and ROUTING_TABLE sections
        client_list_section = False
        routing_table_section = False
        headers = {}
        
        for line in lines:
            line = line.strip()
            
            # Detect section headers
            if line.startswith("HEADER,CLIENT_LIST,"):
                client_headers = line.split(',')[2:]  # Skip "HEADER" and "CLIENT_LIST"
                headers["CLIENT_LIST"] = client_headers
                client_list_section = True
                routing_table_section = False
                continue
                
            if line.startswith("HEADER,ROUTING_TABLE,"):
                routing_headers = line.split(',')[2:]  # Skip "HEADER" and "ROUTING_TABLE"
                headers["ROUTING_TABLE"] = routing_headers
                routing_table_section = True
                client_list_section = False
                continue
                
            # Process CLIENT_LIST entries
            if line.startswith("CLIENT_LIST,"):
                parts = line.split(',')
                if len(parts) > 1:
                    common_name = parts[1]
                    real_address = parts[2].split(':')[0] if len(parts) > 2 else None
                    virtual_address = parts[3] if len(parts) > 3 else None
                    
                    print(f"Client entry - Common Name: '{common_name}', Real Address: '{real_address}', Virtual: '{virtual_address}'")
                    
                    # Try to match by common name
                    if common_name == provision_identity:
                        ip = virtual_address if virtual_address and virtual_address.strip() else real_address
                        print(f"Found client match by common name: {provision_identity}, IP: {ip}")
                        return jsonify({"ip": ip}), 200
                        
            # Process ROUTING_TABLE entries
            if line.startswith("ROUTING_TABLE,"):
                parts = line.split(',')
                if len(parts) > 2:
                    virtual_address = parts[1]
                    common_name = parts[2]
                    
                    print(f"Routing entry - Virtual Address: '{virtual_address}', Common Name: '{common_name}'")
                    
                    # Try to match by common name
                    if common_name == provision_identity:
                        print(f"Found routing match by common name: {provision_identity}, IP: {virtual_address}")
                        return jsonify({"ip": virtual_address}), 200
        
        # If client is not found in the standard entries, let's check if there's any connection with a matching IP
        # This is a fallback for non-standard configurations
        for line in lines:
            line = line.strip()
            parts = line.split(',')
            
            # Look for any line that contains the provision identity
            if provision_identity in line:
                print(f"Found line containing '{provision_identity}': {line}")
                
                # Extract IP-like strings from the line
                import re
                ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                ips = re.findall(ip_pattern, line)
                
                if ips:
                    print(f"Found potential IP(s) in line containing '{provision_identity}': {ips}")
                    return jsonify({"ip": ips[0]}), 200
        
        print(f"\nNo client found with provision_identity: {provision_identity}")
        return jsonify({"error": "Client not connected"}), 404
        
    except Exception as e:
        print(f"Error reading status file: {str(e)}")
        return jsonify({"error": f"Error reading status file: {str(e)}"}), 500

@app.route("/mikrotik/hotspot/<provision_identity>/<secret>/<form>")
@require_secret
def mtk_hostpot_ui(provision_identity, secret, form):
    """Returning the hotspot login page.
        @:var form: Either login.html or rlogin.html
    """
    try:
        if form not in ["login.html", "rlogin.html"]:
            return jsonify({"error": "Form not found"}), 404
        return send_from_directory(Config.HOTSPOT_TEMPLATE_DIR, form)
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

admin_routs.init(app)

if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False in production
