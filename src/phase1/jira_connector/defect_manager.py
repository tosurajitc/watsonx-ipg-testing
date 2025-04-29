import requests

class DefectManager:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    def create_defect(self, project_key: str, summary: str, description: str, issue_type: str = "Bug", priority: str = "Medium"):
        """Create a new defect in JIRA"""
        url = f"{self.base_url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": summary,
                "description": description,
                "issuetype": {
                    "name": issue_type
                },
                "priority": {
                    "name": priority
                }
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create defect: {response.status_code}\n{response.text}")

    def update_defect(self, issue_id: str, fields: dict):
        """Update fields of an existing defect"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_id}"
        payload = {
            "fields": fields
        }

        response = requests.put(url, headers=self.headers, json=payload)

        if response.status_code == 204:
            return {"message": f"Issue {issue_id} updated successfully."}
        else:
            raise Exception(f"Failed to update defect: {response.status_code}\n{response.text}")

    def get_defect(self, issue_id: str):
        """Fetch current status of a defect"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_id}?fields=status"

        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            issue = response.json()
            return issue
        else:
            raise Exception(f"Failed to fetch defect status: {response.status_code}\n{response.text}")

