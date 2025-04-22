"""
This instance is hosted on a VPN server that will help to auto generate or provision new clients.
It returns certs for each client and also stores them for remote connection with Mikrotik
It wil be used by the main site (myisp.com) to generate new vpn clients for mikrotik connection
 and listen for a successful connection as well as sending mikrotik commands to perform specif jobs.
It will also be accessed with Mikrotik to fetch these certs and install them on behalf of the user
"""
import os
from flask import Flask, jsonify, send_file, send_from_directory
import openvpn_api
from celery.result import AsyncResult
from config import Config
from security import validate_provision_identity, generate_secret, require_secret
from tasks import generate_certificate,celery
from werkzeug.urls import url_quote

app = Flask(__name__)
app.config.from_object(Config)

# Initialize OpenVPN API
try:
    v = openvpn_api.VPN(Config.VPN_HOST, Config.VPN_PORT)
    # Test connection
    _ = v.get_status()
    print(f"Successfully connected to OpenVPN management at {Config.VPN_HOST}:{Config.VPN_PORT}")
except Exception as e:
    print(f"WARNING: Failed to connect to OpenVPN management interface: {str(e)}")
    print(f"Using host: {Config.VPN_HOST}, port: {Config.VPN_PORT}")
    v = None  # Set to None so we can check later

@app.route('/')
def hello_world():
    # REQUEST_COUNT.labels(method='GET', endpoint='/', status='401').inc()
    return jsonify({"status": "unauthorized"}), 401


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
    task_result = AsyncResult(task_id,app=celery)

    if task_result.ready():
        if task_result.successful():
            result = task_result.get()
            print('resultsss ',result)
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
            return jsonify({
                "status": "error",
                "message": str(task_result.result),
                "task_id": task_id,
                "state": "failed"
            }), 500
    else:
        return jsonify({
            "status": "pending",
            "message": "Certificate generation in progress",
            "task_id": task_id,
            "state": task_result.state
        }), 202


@app.route("/mikrotik/openvpn/<provision_identity>/<secret>")
@require_secret
def mtk_openvpn(provision_identity, secret):
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
    """Returning the IP address of the client"""
    try:
        print(f"Getting IP for provision_identity: {provision_identity}")
        # Get the status from OpenVPN
        if v is None:
            return jsonify({"error": "OpenVPN management interface not connected"}), 503
        
        try:
            status = v.get_status()
            print('OpenVPN status:', status)
        except Exception as e:
            print(f"Error getting OpenVPN status: {str(e)}")
            return jsonify({"error": "Failed to get OpenVPN status"}), 500

        # Find the client by its common name (provision_identity)
        if not hasattr(status, 'client_list'):
            print("No client_list in status")
            return jsonify({"error": "No clients connected"}), 404

        for client in status.client_list:
            print(f"Checking client: {client.common_name}")
            if client.common_name == provision_identity:
                print(f"Found client with IP: {client.real_address}")
                return jsonify({"ip": client.real_address}), 200
                
        print(f"No client found with provision_identity: {provision_identity}")
        return jsonify({"error": "Client not connected"}), 404
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


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


if __name__ == '__main__':
    app.run(debug=False)  # Set debug=False in production
