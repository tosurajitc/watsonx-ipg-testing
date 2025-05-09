from flask import Flask, request, jsonify
from io import BytesIO

from phase1.sharepoint_connector.document_retriever import DocumentRetriever
from phase1.sharepoint_connector.document_uploader import DocumentUploader
from phase1.sharepoint_connector.sharepoint_auth import SharePointAuth
from phase1.sharepoint_connector.sharepoint_version_manager import VersionManager

app = Flask(__name__)

# -----------------------------
# Authentication Endpoint
# -----------------------------
@app.route('/auth', methods=['POST'])
def auth():
    try:
        tenant_id = "your-tenant-id"
        client_id = "your-client-id"
        client_secret = "your-client-secret"
        resource = "https://yourtenant.sharepoint.com"

        auth = SharePointAuth(tenant_id, client_id, client_secret, resource)
        token, session = auth.check_sharepoint_connection(auth)

        print("Token acquired successfully.")
        return token, session
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------------------
# Upload Document
# -----------------------------
@app.route('/upload', methods=['POST'])
def upload():
    try:
        token = request.headers.get('Authorization')
        file = request.files['file']
        site_url = request.form['site_url']
        folder_path = request.form['folder_path']

        #Need to check the size of the document and if document size is more than 10 MB, 
        #upload using chunked method.
        result = DocumentUploader().upload_files(file, site_url, folder_path, token)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------------------
# Download Document
# -----------------------------
@app.route('/download', methods=['GET'])
def download():
    try:
        token = request.headers.get('Authorization')
        site_url = request.args.get('site_url')
        file_url = request.args.get('file_url')

        results = DocumentRetriever().download_files(site_url, file_url, token)

        if isinstance(results, dict) and results.get("error"):
            return jsonify(results), 400

        for result in results:
            if result["status"] == "Success":
                print(f"Downloaded {result['file_path']} ({len(result['content'])} bytes)")
            else:
                print(f"Failed to retrieve {result['file_path']}: {result.get('error')}")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------------------
# Version Manager
# -----------------------------
@app.route('/version', methods=['POST'])
def version():
    try:
        data = request.json

        required_fields = ["site_url", "token", "document_path", "action"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        site_url = data["site_url"]
        token = data["token"]
        document_path = data["document_path"]
        action = data["action"]
        version_id = data.get("version_id")  # optional for get

        manager = VersionManager(site_url, token)
        result = manager.manage_version(document_path, {"action": action, "version_id": version_id})

        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -----------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)
