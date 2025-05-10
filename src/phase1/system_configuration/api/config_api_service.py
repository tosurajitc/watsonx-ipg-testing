from phase1.system_configuration.config_manager import ConfigManager
from phase1.system_configuration.integration_settings import CredentialManager
from flask import Flask, jsonify, request
import yaml
from phase1.system_configuration.rule_engine import RuleEngine
from phase1.system_configuration.user_manager import UserManager

RULES = [
    {"test_priority": "High", "module": "Auth", "assigned_team": "Security QA"},
    {"test_priority": "Medium", "module": "Payment", "assigned_team": "Finance QA"},
    {"defect_severity": "Critical", "module": "Database", "assigned_team": "DB Admin"},
    {"defect_severity": "Minor", "module": "UI", "assigned_team": "Frontend QA"}
]

config_manager = ConfigManager()
cred_manager = CredentialManager()
user_manager = UserManager()
engine = RuleEngine(RULES)

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

@app.route("/config/<key>", methods=["GET"])
def get_config_from_DB(key):
    """Retrieve configuration setting."""
    value = config_manager.get_config_from_DB(key)
    return jsonify({"config_key": key, "config_value": value}), 200

@app.route("/config/update", methods=["POST"])
def update_config_to_DB():
    """Update configuration with version tracking."""
    data = request.json
    config_manager.update_config_to_DB(data["config_key"], data["config_value"])
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

@app.route("/register", methods=["POST"])
def register_user():
    try:
        data = request.json
        hashed_password = user_manager.hash_password(data["password"])
        user_manager.execute_query("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                                 (data["username"], hashed_password, data["role"]))
        return jsonify({"status": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        user = user_manager.fetch_one("SELECT password, role FROM users WHERE username=%s", (data["username"],))

        if user and user_manager.check_password(data["password"], user[0]):
            permissions = user_manager.get_permissions(user[1])
            return jsonify({"status": "Login successful", "permissions": permissions}), 200
        return jsonify({"error": "Invalid credentials"}), 403
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route("/assign", methods=["POST"])
def assign_task():
    """Returns assignment decisions based on rules."""
    data = request.json
    assigned_team = engine.evaluate_rule(data)
    return jsonify({"assigned_team": assigned_team}), 200

@app.route("/rules/add", methods=["POST"])
def add_rule():
    """Dynamically add rules to PostgreSQL."""
    data = request.json
    user_manager.execute_query(
        "INSERT INTO rule_definitions (test_priority, defect_severity, module, assigned_team) VALUES (%s, %s, %s, %s)",
        (data["test_priority"], data["defect_severity"], data["module"], data["assigned_team"])
    )
    user_manager.close()
    return jsonify({"status": "Rule added successfully"}), 200