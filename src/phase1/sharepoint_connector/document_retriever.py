import requests
from typing import List, Dict
from diskcache import Cache

cache = Cache(directory='./sharepoint_cache')
 
class DocumentRetriever:
   
    def download_files(
        site_url: str,
        file_paths: List[str],
        token: str
    ) -> List[Dict]:
        """
        Downloads documents from SharePoint.

        Args:
            site_url: Base SharePoint site URL (e.g., https://yourtenant.sharepoint.com/sites/YourSite)
            file_paths: List of server-relative file paths (e.g., /sites/YourSite/Shared Documents/TestReports/report.xml)
            token: OAuth access token for SharePoint

        Returns:
            A list of dictionaries containing:
            - file_path: path requested
            - status: "Success" or error
            - content: binary file content (if successful)
        """
        results = []
        ttl = 300
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;odata=verbose"
        }

        for file_path in file_paths:
            cache_key = f"{site_url}:{file_path}"
            
            if cache_key in cache:
                print("✅ Loaded from cache.")
                return cache[cache_key]
                
            try:
                download_url = f"{site_url}/_api/web/getfilebyserverrelativeurl('{file_path}')/$value"
                response = requests.get(download_url, headers=headers)

                if response.status_code == 200:
                    results.append({
                        "file_path": file_path,
                        "status": "Success",
                        "content": response.content
                    })
                    cache.set(cache_key, results, expire=ttl)
                    print("📦 Cached document content.")
                else:
                    results.append({
                        "file_path": file_path,
                        "status": f"Failed ({response.status_code})",
                        "error": response.text
                    })

            except Exception as e:
                results.append({
                    "file_path": file_path,
                    "status": "Exception",
                    "error": str(e)
                })

        return results


    def search_sharepoint(access_token, tenant_name, site_name, keyword):
        """
        Performs a keyword search on a SharePoint site using the SharePoint Search REST API.

        :param access_token: OAuth2 access token (Bearer)
        :param tenant_name: e.g., 'yourtenant' in 'yourtenant.sharepoint.com'
        :param site_name: e.g., 'yoursite' in 'sharepoint.com/sites/yoursite'
        :param keyword: The search term to look for
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json;odata=verbose"
        }

        search_url = f"https://{tenant_name}.sharepoint.com/sites/{site_name}/_api/search/query"
        params = {
            "querytext": f"'{keyword}'",
            "selectproperties": "'Title,Path'",
            "rowlimit": "10"
        }

        response = requests.get(search_url, headers=headers, params=params)

        if response.status_code == 200:
            results = response.json()
            search_results = results.get("d", {}).get("query", {}).get("PrimaryQueryResult", {}).get("RelevantResults", {}).get("Table", {}).get("Rows", [])

            if not search_results:
                print("No results found.")
                return

            print(f"Top results for '{keyword}':\n")
            for row in search_results:
                cells = row.get("Cells", [])
                title = next((c["Value"] for c in cells if c["Key"] == "Title"), "No Title")
                path = next((c["Value"] for c in cells if c["Key"] == "Path"), "No Path")
                print(f"- {title}\n  {path}\n")

        else:
            print(f"Search failed. Status code: {response.status_code}")
            print(response.text)
