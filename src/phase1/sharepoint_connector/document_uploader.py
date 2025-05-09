import os
from typing import Dict, List
import requests

class DocumentUploader:
    def upload_files(
    files: List[str],
    site_url: str,
    folder_path: str,
    token: str
    ) -> List[Dict]:
        """
        Uploads files to SharePoint document library folder.

        Args:
            files: List of file paths to upload.
            site_url: Base SharePoint site URL (e.g., https://yourtenant.sharepoint.com/sites/YourSite)
            folder_path: Server-relative folder path (e.g., /sites/YourSite/Shared Documents/Reports)
            token: OAuth access token for SharePoint

        Returns:
            List of dicts containing upload result and SharePoint URL for each file.
        """
        results = []

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;odata=verbose"
        }

        for file_path in files:
            try:
                if not os.path.isfile(file_path):
                    results.append({"file": file_path, "status": "File not found", "url": None})
                    continue

                file_name = os.path.basename(file_path)
                upload_url = f"{site_url}/_api/web/getfolderbyserverrelativeurl('{folder_path}')/files/add(overwrite=true, url='{file_name}')"

                with open(file_path, 'rb') as f:
                    file_content = f.read()

                response = requests.post(upload_url, headers={**headers, "Content-Type": "application/octet-stream"}, data=file_content)

                if response.status_code in [200, 201]:
                    data = response.json()['d']
                    file_url = data['ServerRelativeUrl']
                    results.append({"file": file_path, "status": "Uploaded", "url": f"{site_url}{file_url}"})
                else:
                    results.append({"file": file_path, "status": f"Error {response.status_code}", "url": None, "error": response.text})

            except Exception as e:
                results.append({"file": file_path, "status": "Exception", "url": None, "error": str(e)})

        return results
    
    # Asynchronous Chunked Upload Function
    def upload_large_file(UPLOAD_FILE_PATH,SHAREPOINT_SITE_ID, token ):
        file_size = os.path.getsize(UPLOAD_FILE_PATH)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Start upload session
        api_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:/{os.path.basename(UPLOAD_FILE_PATH)}:/createUploadSession"
        response = requests.post(api_url, headers=headers)
        
        if response.status_code == 200:
            upload_url = response.json()["uploadUrl"]
            chunk_size = 4 * 1024 * 1024  # 4 MB per chunk
            
            with open(UPLOAD_FILE_PATH, "rb") as file:
                chunk_start = 0
                while chunk_start < file_size:
                    chunk_end = min(chunk_start + chunk_size, file_size)
                    file_chunk = file.read(chunk_size)
                    
                    chunk_headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Length": str(chunk_end - chunk_start),
                        "Content-Range": f"bytes {chunk_start}-{chunk_end-1}/{file_size}"
                    }
                    
                    chunk_response = requests.put(upload_url, headers=chunk_headers, data=file_chunk)
                    if chunk_response.status_code in [200, 201]:
                        print(f"Chunk {chunk_start}-{chunk_end} uploaded successfully")
                    else:
                        raise Exception(f"Error uploading chunk: {chunk_response.text}")
                    
                    chunk_start = chunk_end
            
            print("✅ File uploaded successfully!")
        else:
            raise Exception(f"Error starting upload session: {response.text}")
