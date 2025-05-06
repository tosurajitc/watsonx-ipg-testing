import requests
from msal import ConfidentialClientApplication

class SharePointAuth:
    def __init__(self, tenant_id, client_id, client_secret, resource="https://yourtenant.sharepoint.com"):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.resource = resource
        self.token = None
        self.session = None

    def authenticate(self):
        """
        Performs OAuth 2.0 client_credentials flow and returns:
        - access_token (str)
        - authenticated requests.Session object
        """
        auth_url = f"https://accounts.accesscontrol.windows.net/{self.tenant_id}/tokens/OAuth/2"
        payload = {
            'grant_type': 'client_credentials',
            'client_id': f"{self.client_id}@{self.tenant_id}",
            'client_secret': self.client_secret,
            'resource': f"{self.resource}/{self.tenant_id}@{self.tenant_id}"
        }

        response = requests.post(auth_url, data=payload)
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.text}")

        data = response.json()
        self.token = data['access_token']

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json;odata=verbose'
        })

        return self.token, self.session
    
    def check_sharepoint_connection(self):
        
        # Check if session is active
        if self.session and self.token:
            try:
                # Ping SharePoint to verify token validity
                test_url = f"{self.resource}/_api/web"
                resp = self.session.get(test_url)
                if resp.status_code == 200:
                    return self.token, self.session
            except Exception as e:
                print(f"Session check failed: {e}")

        # Re-authenticate if session is missing or invalid
        #auth = SharePointAuth(tenant_id, client_id, client_secret, resource)
        self.token, self.session = self.authenticate()
        return self.token, self.session

    # Authentication Function Using Microsoft Graph API
    def get_access_token(self):
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = ConfidentialClientApplication(self.client_id, self.client_secret, authority=authority)
        
        token_response = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in token_response:
            return token_response["access_token"]
        else:
            raise Exception("Error obtaining access token")
