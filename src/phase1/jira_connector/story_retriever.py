import requests

class StoryRetriever:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    def fetch_stories(self, jql_query: str, fields: list = None, max_results: int = 50):
        """
        Fetches issues from JIRA based on JQL query.

        Args:
            jql_query (str): JIRA Query Language statement
            fields (list): Fields to retrieve, e.g., ['summary', 'description']
            max_results (int): Number of issues to retrieve (default 50)

        Returns:
            dict: JSON response containing JIRA issues
        """
        search_url = f"{self.base_url}/rest/api/3/search"
        params = {
            "jql": jql_query,
            "maxResults": max_results,
            "fields": ",".join(fields) if fields else "*all"
        }

        response = requests.get(search_url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch issues: {response.status_code}\n{response.text}")


