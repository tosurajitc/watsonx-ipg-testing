from phase1.system_configuration.config_manager import ConfigManager
from phase1.system_configuration.integration_settings import CredentialManager
from flask import Flask, jsonify, request
import yaml

config_manager = ConfigManager()
cred_manager = CredentialManager()

app = Flask(__name__)

@app.route("/config/<key>", methods=["GET"])
def get_config_value(key):
    """Retrieve config settings dynamically."""
    value = config_manager.get_config(key)
    return jsonify({"key": key, "value": value}), 200

@app.route("/config/update", methods=["POST"])
def update_config():
    """Update configuration settings dynamically."""
    data = request.json
    with open(config_manager.config_file, "w") as file:
        yaml.safe_dump(data, file)
    return jsonify({"status": "Configuration updated!"}), 200

@app.route("/config/<service>/<key>", methods=["GET"])
def get_credentials(service, key):
    """Retrieve credentials securely."""
    value = cred_manager.get_credentials(service, key)
    return jsonify({"service": service, "config_key": key, "value": value}), 200

@app.route("/config/store", methods=["POST"])
def store_credentials():
    """Securely store credentials."""
    data = request.json
    cred_manager.store_credentials(data["service"], data["key"], data["value"])
    return jsonify({"status": "Credential stored securely!"}), 201