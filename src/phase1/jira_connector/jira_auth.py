import os
import requests
from requests.auth import HTTPBasicAuth

# -------------------------------
# Authentication Functions
# -------------------------------

class JiraAuth:
    def get_jira_auth_token():
        """Authenticate using API Token and return Basic Auth object"""
        jira_email = os.getenv("JIRA_EMAIL")
        jira_api_token = os.getenv("JIRA_API_TOKEN")
        
        if not jira_email or not jira_api_token:
            raise Exception("Missing JIRA_EMAIL or JIRA_API_TOKEN environment variables.")
        
        return HTTPBasicAuth(jira_email, jira_api_token)

    def get_jira_oauth_access_token():
        """Authenticate using OAuth and return Bearer access token"""
        client_id = os.getenv("JIRA_CLIENT_ID")
        client_secret = os.getenv("JIRA_CLIENT_SECRET")
        auth_code = os.getenv("JIRA_AUTH_CODE")  # Received after user consent
        redirect_uri = os.getenv("JIRA_REDIRECT_URI")

        if not all([client_id, client_secret, auth_code, redirect_uri]):
            raise Exception("Missing OAuth environment variables.")

        token_url = "https://auth.atlassian.com/oauth/token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "redirect_uri": redirect_uri
        }

        response = requests.post(token_url, json=payload)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch access token: {response.status_code}\n{response.text}")

        tokens = response.json()
        return tokens.get("access_token")

    
