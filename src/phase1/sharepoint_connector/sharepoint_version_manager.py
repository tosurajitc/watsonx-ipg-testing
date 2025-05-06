import requests

class VersionManager:
    def __init__(self, site_url: str, token: str):
        self.site_url = site_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json;odata=verbose",
            "Content-Type": "application/json"
        }

    def manage_version(self, document_path: str, version_info: dict):
        """
        Manage SharePoint document versions.

        Args:
            document_path: Server-relative path to the document.
            version_info: Dictionary with keys:
                - action: "get", "delete", "restore"
                - version_id: optional, for delete/restore

        Returns:
            JSON response with status and version data if applicable.
        """
        try:
            action = version_info.get("action")
            version_id = version_info.get("version_id")  # Format: '1.0', '2.1', etc.

            if action == "get":
                url = f"{self.site_url}/_api/web/getfilebyserverrelativeurl('{document_path}')/versions"
                resp = requests.get(url, headers=self.headers)
                if resp.status_code == 200:
                    return {"status": "success", "versions": resp.json()['d']['results']}
                else:
                    return {"status": "error", "code": resp.status_code, "message": resp.text}

            elif action == "delete":
                if not version_id:
                    return {"status": "error", "message": "Missing version_id for delete"}
                url = f"{self.site_url}/_api/web/getfilebyserverrelativeurl('{document_path}')/versions('{version_id}')"
                resp = requests.post(url, headers={**self.headers, "X-HTTP-Method": "DELETE"})
                if resp.status_code == 200 or resp.status_code == 204:
                    return {"status": "deleted", "version": version_id}
                else:
                    return {"status": "error", "code": resp.status_code, "message": resp.text}

            elif action == "restore":
                if not version_id:
                    return {"status": "error", "message": "Missing version_id for restore"}
                url = f"{self.site_url}/_api/web/getfilebyserverrelativeurl('{document_path}')/versions('{version_id}')/restoreversion"
                resp = requests.post(url, headers=self.headers)
                if resp.status_code == 200 or resp.status_code == 204:
                    return {"status": "restored", "version": version_id}
                else:
                    return {"status": "error", "code": resp.status_code, "message": resp.text}

            else:
                return {"status": "error", "message": f"Unsupported action '{action}'"}

        except Exception as e:
            return {"status": "exception", "message": str(e)}
