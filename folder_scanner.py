import os
import argparse
from pathlib import Path
import json

def scan_directory(root_path):
    """
    Scan the directory structure starting from root_path and return a dictionary
    representing the folder structure with files.
    """
    structure = {}
    
    for item in os.listdir(root_path):
        item_path = os.path.join(root_path, item)
        
        if os.path.isdir(item_path):
            # If it's a directory, recursively scan it
            structure[item] = scan_directory(item_path)
        else:
            # If it's a file, just add it to the structure
            structure[item] = None
            
    return structure

def create_text_representation(structure, indent=0):
    """
    Create a text representation of the folder structure.
    """
    result = []
    
    for name, contents in sorted(structure.items()):
        if contents is None:  # File
            result.append("│   " * indent + "├── " + name)
        else:  # Directory
            result.append("│   " * indent + "├── " + name + "/")
            result.extend(create_text_representation(contents, indent + 1))
            
    return result

def save_structure(structure, output_format="text", output_file="folder_structure"):
    """
    Save the folder structure in the specified format.
    """
    if output_format == "json":
        with open(f"{output_file}.json", "w") as f:
            json.dump(structure, f, indent=2)
            
    elif output_format == "text":
        text_representation = ["./"] + create_text_representation(structure)
        with open(f"{output_file}.txt", "w") as f:
            f.write("\n".join(text_representation))

def main():
    parser = argparse.ArgumentParser(description="Generate folder structure representation")
    parser.add_argument("--root", default=".", help="Root directory to scan (default: current directory)")
    parser.add_argument("--format", choices=["text", "json"], default="text", 
                        help="Output format (default: text)")
    parser.add_argument("--output", default="folder_structure", 
                        help="Output file name without extension (default: folder_structure)")
    parser.add_argument("--max-depth", type=int, default=None, 
                        help="Maximum depth to scan (default: no limit)")
    
    args = parser.parse_args()
    
    root_path = os.path.abspath(args.root)
    print(f"Scanning directory: {root_path}")
    
    structure = scan_directory(root_path)
    save_structure(structure, args.format, args.output)
    
    print(f"Folder structure saved to {args.output}.{args.format}")

if __name__ == "__main__":
    main()