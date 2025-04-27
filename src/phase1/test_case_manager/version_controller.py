#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Version Controller Module for the Watsonx IPG Testing platform.

This module handles versioning of test cases, tracking changes between versions,
and maintains a history of test case modifications over time.
"""

import os
import pandas as pd
import logging
import json
import difflib
import hashlib
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import shutil
import re

# Import from src.common
from src.common.utils.file_utils import read_file, write_file
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    TestCaseNotFoundError,
    VersionControlError,
    InvalidVersionError
)

# Import from phase1
from src.phase1.sharepoint_connector.document_uploader import upload_document
from src.phase1.notification_service.notification_manager import send_notification

# Setup logger
logger = logging.getLogger(__name__)

class VersionController:
    """
    Class to manage test case versions, track changes, and maintain version history.
    """
    
    def __init__(self, version_store_path: str = None):
        """
        Initialize the VersionController with a version store path.
        
        Args:
            version_store_path (str, optional): Path to the version store directory.
                If None, uses a default path in the current directory.
        """
        self.version_store_path = version_store_path or os.path.join(
            os.path.dirname(__file__), "../../../storage/test_case_versions"
        )
        self.logger = logging.getLogger(__name__)
        
        # Create version store directory if it doesn't exist
        os.makedirs(self.version_store_path, exist_ok=True)
        
        self.logger.info(f"VersionController initialized with store at: {self.version_store_path}")
    
    def _get_test_case_id_from_df(self, test_case_df: pd.DataFrame) -> str:
        """
        Extract the test case ID from a test case DataFrame.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame.
            
        Returns:
            str: The test case ID.
            
        Raises:
            VersionControlError: If the test case ID can't be extracted.
        """
        # Try to get test case number from the first row
        if len(test_case_df) > 0:
            if "TEST CASE NUMBER" in test_case_df.columns:
                test_case_id = str(test_case_df.iloc[0]["TEST CASE NUMBER"])
                
                # Clean the ID to ensure it's valid for filenames
                test_case_id = re.sub(r'[^\w\-]', '_', test_case_id)
                
                if test_case_id:
                    return test_case_id
        
        # If we can't extract a valid ID, raise an error
        raise VersionControlError("Could not extract a valid test case ID from the DataFrame")
    
    def _get_test_case_hash(self, test_case_df: pd.DataFrame) -> str:
        """
        Calculate a hash for the test case content to detect changes.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame.
            
        Returns:
            str: Hash string representing the test case content.
        """
        # Convert DataFrame to string and calculate SHA-256 hash
        try:
            # Sort columns to ensure consistent order
            sorted_df = test_case_df.sort_index(axis=1)
            
            # Concat values to a single string and calculate hash
            content_str = sorted_df.to_string(index=False)
            return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not calculate hash accurately: {str(e)}")
            
            # Fallback - just hash column names and row count as a basic check
            cols = ','.join(sorted(test_case_df.columns))
            return hashlib.sha256(f"{cols}:{len(test_case_df)}".encode('utf-8')).hexdigest()
    
    def _get_version_history_path(self, test_case_id: str) -> str:
        """
        Get the path to the version history file for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            str: Path to the version history JSON file.
        """
        return os.path.join(self.version_store_path, f"{test_case_id}_version_history.json")
    
    def _get_version_directory(self, test_case_id: str) -> str:
        """
        Get the directory path for storing versions of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            str: Path to the version directory.
        """
        version_dir = os.path.join(self.version_store_path, test_case_id)
        os.makedirs(version_dir, exist_ok=True)
        return version_dir
    
    def _load_version_history(self, test_case_id: str) -> Dict[str, Any]:
        """
        Load the version history for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: The version history data.
        """
        history_path = self._get_version_history_path(test_case_id)
        
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load version history: {str(e)}")
                # Return a new empty history if file is corrupted
                return self._create_new_version_history(test_case_id)
        else:
            # Create a new version history if none exists
            return self._create_new_version_history(test_case_id)
    
    def _save_version_history(self, test_case_id: str, history: Dict[str, Any]) -> None:
        """
        Save the version history for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            history (Dict[str, Any]): The version history data.
        """
        history_path = self._get_version_history_path(test_case_id)
        
        try:
            with open(history_path, 'w') as f:
                json.dump(history, f, indent=2)
            
            self.logger.debug(f"Version history saved for {test_case_id}")
        except Exception as e:
            self.logger.error(f"Failed to save version history: {str(e)}")
            raise VersionControlError(f"Failed to save version history: {str(e)}")
    
    def _create_new_version_history(self, test_case_id: str) -> Dict[str, Any]:
        """
        Create a new version history structure for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: New version history structure.
        """
        return {
            "test_case_id": test_case_id,
            "created_at": datetime.now().isoformat(),
            "current_version": None,
            "versions": []
        }
    
    def _get_test_case_version_path(self, test_case_id: str, version: str) -> str:
        """
        Get the path to a specific version of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            version (str): The version identifier.
            
        Returns:
            str: Path to the version file.
        """
        version_dir = self._get_version_directory(test_case_id)
        return os.path.join(version_dir, f"{version}.xlsx")
    
    def load_test_case(self, file_path: str) -> pd.DataFrame:
        """
        Load a test case from an Excel file.
        
        Args:
            file_path (str): Path to the test case file.
            
        Returns:
            pd.DataFrame: The test case as a DataFrame.
            
        Raises:
            TestCaseNotFoundError: If the file doesn't exist.
            VersionControlError: If the file format is unsupported or invalid.
        """
        if not os.path.exists(file_path):
            error_msg = f"Test case file not found: {file_path}"
            self.logger.error(error_msg)
            raise TestCaseNotFoundError(error_msg)
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext in ['.xlsx', '.xls']:
                # Load Excel file
                df = pd.read_excel(file_path)
                
                # Verify it has expected columns
                if not all(col in df.columns for col in ["TEST CASE NUMBER", "TEST STEP DESCRIPTION"]):
                    raise VersionControlError(f"File does not appear to be a valid test case format: {file_path}")
                
                return df
            else:
                raise VersionControlError(f"Unsupported file format: {file_ext}")
                
        except VersionControlError:
            raise
        except Exception as e:
            error_msg = f"Failed to load test case file: {str(e)}"
            self.logger.error(error_msg)
            raise VersionControlError(error_msg)
    
    # Renamed from check_in_new_version to create_new_version
    def create_new_version(self, test_case_path: str, 
                      change_comment: str = None, 
                      changed_by: str = None,
                      notify_owner: bool = True) -> Dict[str, Any]:
        """
        Register a new version of a test case.
        
        Args:
            test_case_path (str): Path to the test case file.
            change_comment (str, optional): Comment describing the changes.
            changed_by (str, optional): Name/ID of the person who made the changes.
            notify_owner (bool): Whether to notify the test case owner.
            
        Returns:
            Dict[str, Any]: Information about the new version.
            
        Raises:
            TestCaseNotFoundError: If the file doesn't exist.
            VersionControlError: If version control operations fail.
        """
        # Load the test case
        test_case_df = self.load_test_case(test_case_path)
        
        # Extract test case ID and owner
        test_case_id = self._get_test_case_id_from_df(test_case_df)
        
        # Try to find the owner from the test case data
        owner = None
        if "TEST USER ID/ROLE" in test_case_df.columns and len(test_case_df) > 0:
            owner = test_case_df.iloc[0]["TEST USER ID/ROLE"]
        
        # Calculate content hash
        content_hash = self._get_test_case_hash(test_case_df)
        
        # Load version history
        history = self._load_version_history(test_case_id)
        
        # Check if this is identical to the current version
        is_new_version = True
        current_version = history.get("current_version")
        
        if current_version:
            # Find the current version in the history
            for version in history["versions"]:
                if version["version"] == current_version:
                    if version["content_hash"] == content_hash:
                        is_new_version = False
                        self.logger.info(f"Test case {test_case_id} content matches current version {current_version}")
                        
                        # Return current version info
                        return {
                            "test_case_id": test_case_id,
                            "version": current_version,
                            "is_new_version": False,
                            "timestamp": version["timestamp"],
                            "message": "Test case content is identical to current version"
                        }
                    break
        
        # Generate new version number
        if not history["versions"]:
            # First version is 1.0
            new_version = "1.0"
        else:
            # Increment the last version
            last_version = history["versions"][-1]["version"]
            major, minor = map(int, last_version.split('.'))
            
            # For now, just increment the minor version
            # Could implement logic to determine major vs minor changes
            new_version = f"{major}.{minor + 1}"
        
        # Create new version entry
        timestamp = datetime.now().isoformat()
        version_entry = {
            "version": new_version,
            "timestamp": timestamp,
            "content_hash": content_hash,
            "changed_by": changed_by or "System",
            "comment": change_comment or "No comment provided",
            "file_name": os.path.basename(test_case_path),
            "owner": owner
        }
        
        # Save the file to version storage
        version_path = self._get_test_case_version_path(test_case_id, new_version)
        try:
            test_case_df.to_excel(version_path, index=False)
            self.logger.info(f"Version {new_version} of test case {test_case_id} saved to {version_path}")
        except Exception as e:
            self.logger.error(f"Failed to save version file: {str(e)}")
            raise VersionControlError(f"Failed to save version file: {str(e)}")
        
        # Update history
        history["versions"].append(version_entry)
        history["current_version"] = new_version
        
        # Save updated history
        self._save_version_history(test_case_id, history)
        
        # Notify owner if requested
        if notify_owner and owner:
            try:
                notification_data = {
                    "recipient": owner,
                    "subject": f"Test Case {test_case_id} Updated to Version {new_version}",
                    "message": f"A new version ({new_version}) of Test Case {test_case_id} has been created.\n\n"
                               f"Comment: {change_comment or 'No comment provided'}\n"
                               f"Changed by: {changed_by or 'System'}\n"
                               f"Timestamp: {timestamp}"
                }
                send_notification(notification_data)
                self.logger.info(f"Notification sent to owner ({owner}) of test case {test_case_id}")
            except Exception as e:
                self.logger.warning(f"Failed to send notification to owner: {str(e)}")
        
        # Return new version info
        return {
            "test_case_id": test_case_id,
            "version": new_version,
            "is_new_version": True,
            "timestamp": timestamp,
            "file_path": version_path
        }
    
    # Keep the old method name as an alias for backward compatibility
    def check_in_new_version(self, test_case_path: str, 
                        change_comment: str = None, 
                        changed_by: str = None,
                        notify_owner: bool = True) -> Dict[str, Any]:
        """
        Alias for create_new_version.
        """
        return self.create_new_version(test_case_path, change_comment, changed_by, notify_owner)
    
    def get_version_history(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get the version history for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: The version history data.
            
        Raises:
            VersionControlError: If the history can't be loaded.
        """
        try:
            history = self._load_version_history(test_case_id)
            return history
        except Exception as e:
            self.logger.error(f"Failed to get version history: {str(e)}")
            raise VersionControlError(f"Failed to get version history: {str(e)}")
    
    def get_test_case_version(self, test_case_id: str, version: str = None) -> pd.DataFrame:
        """
        Get a specific version of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            version (str, optional): The version to retrieve. If None, gets the current version.
            
        Returns:
            pd.DataFrame: The test case DataFrame for the specified version.
            
        Raises:
            InvalidVersionError: If the requested version doesn't exist.
        """
        # Load history
        history = self._load_version_history(test_case_id)
        
        # Determine which version to get
        target_version = version or history.get("current_version")
        
        if not target_version:
            raise InvalidVersionError(f"No version found for test case {test_case_id}")
        
        # Verify the version exists
        version_exists = False
        for ver in history["versions"]:
            if ver["version"] == target_version:
                version_exists = True
                break
        
        if not version_exists:
            raise InvalidVersionError(f"Version {target_version} not found for test case {test_case_id}")
        
        # Get the path to the version file
        version_path = self._get_test_case_version_path(test_case_id, target_version)
        
        if not os.path.exists(version_path):
            raise InvalidVersionError(f"Version file for {target_version} not found at {version_path}")
        
        # Load the test case
        try:
            test_case_df = pd.read_excel(version_path)
            return test_case_df
        except Exception as e:
            self.logger.error(f"Failed to load version file: {str(e)}")
            raise VersionControlError(f"Failed to load version file: {str(e)}")
    
    def export_version_to_file(self, test_case_id: str, output_path: str, version: str = None) -> str:
        """
        Export a specific version of a test case to a file.
        
        Args:
            test_case_id (str): The test case ID.
            output_path (str): Path to save the file.
            version (str, optional): The version to export. If None, exports the current version.
            
        Returns:
            str: Path to the exported file.
            
        Raises:
            InvalidVersionError: If the requested version doesn't exist.
        """
        # Get the test case version
        test_case_df = self.get_test_case_version(test_case_id, version)
        
        # Get the version history to determine the version number exported
        history = self._load_version_history(test_case_id)
        version_exported = version or history.get("current_version", "unknown")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Save the file
        try:
            test_case_df.to_excel(output_path, index=False)
            self.logger.info(f"Version {version_exported} of test case {test_case_id} exported to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to export version to file: {str(e)}")
            raise VersionControlError(f"Failed to export version to file: {str(e)}")
    
    def compare_versions(self, test_case_id: str, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare two versions of a test case and identify differences.
        
        Args:
            test_case_id (str): The test case ID.
            version1 (str): First version to compare.
            version2 (str): Second version to compare.
            
        Returns:
            Dict[str, Any]: Comparison results with differences.
            
        Raises:
            InvalidVersionError: If either requested version doesn't exist.
        """
        # Load both versions
        df1 = self.get_test_case_version(test_case_id, version1)
        df2 = self.get_test_case_version(test_case_id, version2)
        
        # Initialize results
        comparison = {
            "test_case_id": test_case_id,
            "version1": version1,
            "version2": version2,
            "added_steps": [],
            "removed_steps": [],
            "modified_steps": [],
            "summary": {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
        }
        
        # Compare basic structure
        if len(df1) != len(df2):
            self.logger.info(f"Different number of steps: {len(df1)} vs {len(df2)}")
        
        # Create dictionaries of steps by step number for easy comparison
        steps1 = {}
        steps2 = {}
        
        for _, row in df1.iterrows():
            step_no = row.get("STEP NO")
            if step_no is not None:
                steps1[step_no] = row.to_dict()
        
        for _, row in df2.iterrows():
            step_no = row.get("STEP NO")
            if step_no is not None:
                steps2[step_no] = row.to_dict()
        
        # Find added, removed, and common steps
        all_step_numbers = sorted(set(list(steps1.keys()) + list(steps2.keys())))
        
        for step_no in all_step_numbers:
            if step_no in steps1 and step_no not in steps2:
                # Step was removed in version2
                comparison["removed_steps"].append({
                    "step_no": step_no,
                    "details": steps1[step_no]
                })
                comparison["summary"]["removed"] += 1
                
            elif step_no not in steps1 and step_no in steps2:
                # Step was added in version2
                comparison["added_steps"].append({
                    "step_no": step_no,
                    "details": steps2[step_no]
                })
                comparison["summary"]["added"] += 1
                
            else:
                # Step exists in both versions - check for differences
                step1 = steps1[step_no]
                step2 = steps2[step_no]
                
                differences = {}
                
                # Compare each field
                for field in set(list(step1.keys()) + list(step2.keys())):
                    value1 = step1.get(field, "")
                    value2 = step2.get(field, "")
                    
                    # Convert to string for comparison
                    value1_str = str(value1)
                    value2_str = str(value2)
                    
                    if value1_str != value2_str:
                        differences[field] = {
                            "from": value1_str,
                            "to": value2_str
                        }
                
                if differences:
                    # Step was modified
                    comparison["modified_steps"].append({
                        "step_no": step_no,
                        "differences": differences
                    })
                    comparison["summary"]["modified"] += 1
                else:
                    # Step is unchanged
                    comparison["summary"]["unchanged"] += 1
        
        return comparison

    def upload_to_sharepoint(self, test_case_id: str, version: str = None, 
                          sharepoint_folder: str = None) -> Dict[str, Any]:
        """
        Upload a specific version of a test case to SharePoint.
        
        Args:
            test_case_id (str): The test case ID.
            version (str, optional): The version to upload. If None, uploads the current version.
            sharepoint_folder (str, optional): The SharePoint folder path. If None, uses a default path.
            
        Returns:
            Dict[str, Any]: Upload result with SharePoint URL.
            
        Raises:
            InvalidVersionError: If the requested version doesn't exist.
            VersionControlError: If the upload fails.
        """
        # Create a temporary file to upload
        temp_dir = os.path.join(os.path.dirname(__file__), "../../../temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, f"{test_case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        # Export the version to the temporary file
        self.export_version_to_file(test_case_id, temp_path, version)
        
        # Get the version number for the file name
        history = self._load_version_history(test_case_id)
        version_uploaded = version or history.get("current_version", "unknown")
        
        # Set default SharePoint folder if not provided
        if not sharepoint_folder:
            sharepoint_folder = "Test Cases"
        
        # Upload to SharePoint
        try:
            # Get test case name for a better filename
            test_case_df = pd.read_excel(temp_path)
            test_case_name = "Unknown"
            
            if len(test_case_df) > 0 and "TEST CASE" in test_case_df.columns:
                test_case_name = str(test_case_df.iloc[0]["TEST CASE"])
            
            # Create a clean file name
            clean_name = re.sub(r'[^\w\-\. ]', '_', test_case_name)
            sharepoint_filename = f"{clean_name}_{test_case_id}_v{version_uploaded}.xlsx"
            
            # Upload the file
            upload_result = upload_document(temp_path, sharepoint_folder, sharepoint_filename)
            
            # Update version history with SharePoint info
            for v in history["versions"]:
                if v["version"] == version_uploaded:
                    v["sharepoint_url"] = upload_result.get("url", "Unknown")
                    v["sharepoint_path"] = f"{sharepoint_folder}/{sharepoint_filename}"
                    break
            
            self._save_version_history(test_case_id, history)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return {
                "test_case_id": test_case_id,
                "version": version_uploaded,
                "sharepoint_url": upload_result.get("url", "Unknown"),
                "sharepoint_path": f"{sharepoint_folder}/{sharepoint_filename}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to upload to SharePoint: {str(e)}")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            raise VersionControlError(f"Failed to upload to SharePoint: {str(e)}")
    
    # Renamed from mark_as_under_maintenance to mark_under_maintenance
    def mark_under_maintenance(self, test_case_id: str) -> Dict[str, Any]:
        """
        Mark a test case as "Under Maintenance" in its version history.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: Result of the operation.
            
        Raises:
            VersionControlError: If the operation fails.
        """
        try:
            # Load history
            history = self._load_version_history(test_case_id)
            
            # Mark as under maintenance
            history["status"] = "Under Maintenance"
            history["maintenance_started"] = datetime.now().isoformat()
            
            # Save updated history
            self._save_version_history(test_case_id, history)
            
            self.logger.info(f"Test case {test_case_id} marked as Under Maintenance")
            
            return {
                "test_case_id": test_case_id,
                "status": "Under Maintenance",
                "timestamp": history["maintenance_started"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to mark as under maintenance: {str(e)}")
            raise VersionControlError(f"Failed to mark as under maintenance: {str(e)}")
    
    # Keep the old method name as an alias for backward compatibility
    def mark_as_under_maintenance(self, test_case_id: str) -> Dict[str, Any]:
        """
        Alias for mark_under_maintenance.
        """
        return self.mark_under_maintenance(test_case_id)
    
    def mark_as_active(self, test_case_id: str) -> Dict[str, Any]:
        """
        Mark a test case as "Active" (no longer under maintenance) in its version history.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: Result of the operation.
            
        Raises:
            VersionControlError: If the operation fails.
        """
        try:
            # Load history
            history = self._load_version_history(test_case_id)
            
            # Mark as active
            history["status"] = "Active"
            if "maintenance_started" in history:
                history["maintenance_ended"] = datetime.now().isoformat()
            
            # Save updated history
            self._save_version_history(test_case_id, history)
            
            self.logger.info(f"Test case {test_case_id} marked as Active")
            
            return {
                "test_case_id": test_case_id,
                "status": "Active",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to mark as active: {str(e)}")
            raise VersionControlError(f"Failed to mark as active: {str(e)}")

# If running as a script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage test case versions")
    parser.add_argument("--test_case", help="Path to the test case file")
    parser.add_argument("--action", choices=["create", "export", "history", "compare", "upload"],
                      required=True, help="Action to perform")
    parser.add_argument("--test_case_id", help="Test case ID (required for some actions)")
    parser.add_argument("--version", help="Version number (for export, compare, upload)")
    parser.add_argument("--version2", help="Second version number (for compare)")
    parser.add_argument("--output", help="Output file path (for export)")
    parser.add_argument("--comment", help="Change comment (for create)")
    parser.add_argument("--changed_by", help="Name of person who made changes (for create)")
    parser.add_argument("--sharepoint_folder", help="SharePoint folder path (for upload)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create version controller
    version_controller = VersionController()
    
    # Execute requested action
    if args.action == "create":
        if not args.test_case:
            print("Error: --test_case is required for create action")
            exit(1)
        
        result = version_controller.create_new_version(
            args.test_case, 
            change_comment=args.comment,
            changed_by=args.changed_by
        )
        
        if result["is_new_version"]:
            print(f"New version {result['version']} created for test case {result['test_case_id']}")
        else:
            print(f"No changes detected. Current version is still {result['version']}")
    
    elif args.action == "export":
        if not args.test_case_id or not args.output:
            print("Error: --test_case_id and --output are required for export action")
            exit(1)
        
        output_path = version_controller.export_version_to_file(
            args.test_case_id,
            args.output,
            version=args.version
        )
        
        print(f"Test case exported to {output_path}")
    
    elif args.action == "history":
        if not args.test_case_id:
            print("Error: --test_case_id is required for history action")
            exit(1)
        
        history = version_controller.get_version_history(args.test_case_id)
        
        print(f"\nVersion History for Test Case {args.test_case_id}:")
        print(f"Current Version: {history.get('current_version', 'None')}")
        print(f"Total Versions: {len(history.get('versions', []))}")
        
        for idx, version in enumerate(history.get("versions", []), 1):
            print(f"\n{idx}. Version {version.get('version')}:")
            print(f"   Timestamp: {version.get('timestamp')}")
            print(f"   Changed by: {version.get('changed_by', 'Unknown')}")
            print(f"   Comment: {version.get('comment', 'No comment')}")
            if "sharepoint_url" in version:
                print(f"   SharePoint URL: {version.get('sharepoint_url')}")
    
    elif args.action == "compare":
        if not args.test_case_id or not args.version or not args.version2:
            print("Error: --test_case_id, --version, and --version2 are required for compare action")
            exit(1)
        
        comparison = version_controller.compare_versions(
            args.test_case_id,
            args.version,
            args.version2
        )
        
        print(f"\nComparison between versions {args.version} and {args.version2} of Test Case {args.test_case_id}:")
        print(f"Summary: {comparison['summary']['added']} added, {comparison['summary']['removed']} removed, "
              f"{comparison['summary']['modified']} modified, {comparison['summary']['unchanged']} unchanged")
        
        if comparison["added_steps"]:
            print("\nAdded Steps:")
            for step in comparison["added_steps"]:
                print(f"  Step {step['step_no']}: {step['details'].get('TEST STEP DESCRIPTION', 'No description')}")
        
        if comparison["removed_steps"]:
            print("\nRemoved Steps:")
            for step in comparison["removed_steps"]:
                print(f"  Step {step['step_no']}: {step['details'].get('TEST STEP DESCRIPTION', 'No description')}")
        
        if comparison["modified_steps"]:
            print("\nModified Steps:")
            for step in comparison["modified_steps"]:
                print(f"  Step {step['step_no']}:")
                for field, change in step["differences"].items():
                    print(f"    {field}: '{change['from']}' -> '{change['to']}'")
    
    elif args.action == "upload":
        if not args.test_case_id:
            print("Error: --test_case_id is required for upload action")
            exit(1)
        
        result = version_controller.upload_to_sharepoint(
            args.test_case_id,
            version=args.version,
            sharepoint_folder=args.sharepoint_folder
        )
        
        print(f"Test case {args.test_case_id} version {result['version']} uploaded to SharePoint")
        print(f"SharePoint URL: {result['sharepoint_url']}")
        print(f"SharePoint Path: {result['sharepoint_path']}")