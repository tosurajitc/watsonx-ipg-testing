import os

def search_files_for_string(root_dir, search_string):
    """
    Search for a string in all files recursively under the given directory.
    """
    found_files = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            # Skip very large files and binary files
            file_path = os.path.join(root, file)
            
            # Skip files that are likely binary based on extension
            _, ext = os.path.splitext(file)
            if ext.lower() in ['.exe', '.dll', '.pyc', '.pyd', '.so', '.bin', '.dat', '.jpg', '.png', '.gif']:
                continue
                
            try:
                # Try to open as text file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    line_number = 1
                    for line in f:
                        if search_string in line:
                            found_files.append((file_path, line_number, line.strip()))
                        line_number += 1
            except Exception as e:
                # Skip files that can't be read as text
                pass
    
    return found_files

# Set the root directory and search string
root_directory = r"C:\@Official\Automation\2025 Planning\Agentic AI Handson\IPG Testting\watsonx-ipg-testing"
search_for = "create_llm_prompt"

# Perform the search
print(f"Searching for '{search_for}' in all files under {root_directory}...")
results = search_files_for_string(root_directory, search_for)

# Print results
if results:
    print(f"\nFound {len(results)} occurrences:")
    for file_path, line_number, line in results:
        print(f"{file_path} (line {line_number}): {line}")
else:
    print("\nNo occurrences found.")