import requests

class DocumentRetriever:
    import requests
from typing import List, Dict

def download_files_from_sharepoint(
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

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;odata=verbose"
    }

    for file_path in file_paths:
        try:
            download_url = f"{site_url}/_api/web/getfilebyserverrelativeurl('{file_path}')/$value"
            response = requests.get(download_url, headers=headers)

            if response.status_code == 200:
                results.append({
                    "file_path": file_path,
                    "status": "Success",
                    "content": response.content
                })
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


# Example usage
if __name__ == "__main__":
    # Example input
    access_token = "your-access-token"
    site_url = "https://yourtenant.sharepoint.com/sites/TestPortal"
    file_relative_url = "/sites/TestPortal/Shared Documents/TestReports/test_report.pdf"

    result = DocumentRetriever.download_file_from_sharepoint(site_url, file_relative_url, access_token)

    if result['status'] == 'Success':
        with open(result['filename'], 'wb') as f:
            f.write(result['content'])
        print(f"✅ Downloaded and saved: {result['filename']}")
    else:
        print(f"❌ Download failed: {result['error']}")
