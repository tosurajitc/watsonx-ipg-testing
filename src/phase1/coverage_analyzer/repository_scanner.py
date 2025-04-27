#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repository Scanner Module for the Watsonx IPG Testing platform.

This module scans existing test case repositories (SharePoint, JIRA, ALM) 
to identify and retrieve test cases for comparison and analysis.
"""

import os
import logging
import pandas as pd
import json
from typing import Dict, List, Any, Tuple, Optional, Union, Set
import re
from datetime import datetime

# Import from src.common
from src.common.utils.file_utils import read_file, write_file
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    RepositoryScanError,
    AuthenticationError,
    ConnectionError
)

# Import from src.phase1
from src.phase1.sharepoint_connector.sharepoint_auth import SharePointAuth
from src.phase1.sharepoint_connector.document_retriever import DocumentRetriever
from src.phase1.sharepoint_connector.sharepoint_api_service import SharePointApiService
from src.phase1.test_case_manager.metadata_manager import MetadataManager

# Setup logger
logger = logging.getLogger(__name__)

class RepositoryScanner:
    """
    Class to scan test case repositories for existing test cases.
    
    This class provides functionality to:
    1. Connect to different repositories (SharePoint, JIRA, ALM)
    2. Scan for test cases using various criteria
    3. Build and maintain an index of test cases for efficient searching
    4. Retrieve test cases for comparison
    """
    
    def __init__(self, config_path: str = None, metadata_manager: MetadataManager = None):
        """
        Initialize the RepositoryScanner with configuration.
        
        Args:
            config_path (str, optional): Path to configuration file.
            metadata_manager (MetadataManager, optional): Instance of MetadataManager.
                If None, a new instance will be created.
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize metadata manager
        self.metadata_manager = metadata_manager or MetadataManager()
        
        # Initialize connectors based on configuration
        self._init_connectors()
        
        # Initialize the test case index
        self.test_case_index = {}
        self.index_last_updated = None
        
        self.logger.info("Repository Scanner initialized")
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path (str, optional): Path to configuration file.
            
        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        default_config = {
            "repositories": {
                "sharepoint": {
                    "enabled": True,
                    "sites": [
                        {
                            "name": "Test Repository",
                            "url": "https://example.sharepoint.com/sites/TestRepository",
                            "library": "Test Cases",
                            "folder_path": "/Test Cases"
                        }
                    ],
                    "file_types": [".xlsx", ".xls", ".docx", ".doc", ".pdf"]
                },
                "jira": {
                    "enabled": False,
                    "url": "https://example.atlassian.net",
                    "project_keys": ["TEST", "QA"],
                    "issue_types": ["Test"]
                },
                "alm": {
                    "enabled": False,
                    "url": "https://alm.example.com",
                    "domains": ["Default"],
                    "projects": ["TestProject"]
                }
            },
            "indexing": {
                "auto_refresh_interval_hours": 24,
                "index_file_path": "storage/indexes/test_case_index.json"
            },
            "scanning": {
                "batch_size": 100,
                "max_concurrent_connections": 5
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                
                # Merge configurations
                for key, value in user_config.items():
                    if key in default_config and isinstance(value, dict) and isinstance(default_config[key], dict):
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
                
                self.logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                self.logger.error(f"Failed to load configuration from {config_path}: {str(e)}")
                self.logger.warning("Using default configuration")
        else:
            self.logger.info("Using default configuration")
        
        return default_config
    
    def _init_connectors(self):
        """
        Initialize repository connectors based on configuration.
        """
        self.connectors = {}
        
        # Initialize SharePoint connector if enabled
        if self.config["repositories"]["sharepoint"]["enabled"]:
            try:
                # For SharePoint we'll use document_retriever from the SharePoint connector
                sharepoint_auth = SharePointAuth()
                self.connectors["sharepoint"] = DocumentRetriever(sharepoint_auth)
                self.logger.info("SharePoint connector initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize SharePoint connector: {str(e)}")
        
        # Initialize JIRA connector if enabled
        if self.config["repositories"]["jira"]["enabled"]:
            try:
                # This would be implemented when JIRA connector is available
                self.logger.info("JIRA connector initialization skipped - not implemented yet")
                # self.connectors["jira"] = JiraConnector(...)
            except Exception as e:
                self.logger.error(f"Failed to initialize JIRA connector: {str(e)}")
        
        # Initialize ALM connector if enabled
        if self.config["repositories"]["alm"]["enabled"]:
            try:
                # This would be implemented when ALM connector is available
                self.logger.info("ALM connector initialization skipped - not implemented yet")
                # self.connectors["alm"] = AlmConnector(...)
            except Exception as e:
                self.logger.error(f"Failed to initialize ALM connector: {str(e)}")
    
    def scan_repositories(self, force_refresh: bool = False) -> int:
        """
        Scan all enabled repositories and build an index of test cases.
        
        Args:
            force_refresh (bool, optional): Force a full refresh of the index.
                Default is False.
                
        Returns:
            int: Number of test cases indexed.
            
        Raises:
            RepositoryScanError: If scanning fails.
        """
        try:
            total_indexed = 0
            
            # Check if index needs refresh
            if not force_refresh and self.index_last_updated:
                hours_since_update = (datetime.now() - self.index_last_updated).total_seconds() / 3600
                
                if hours_since_update < self.config["indexing"]["auto_refresh_interval_hours"]:
                    self.logger.info(f"Using existing index (last updated {self.index_last_updated.isoformat()})")
                    return len(self.test_case_index)
            
            # Clear existing index if forcing refresh
            if force_refresh:
                self.test_case_index = {}
                self.logger.info("Clearing existing index for full refresh")
            
            # Scan SharePoint repositories
            if "sharepoint" in self.connectors:
                sharepoint_count = self._scan_sharepoint_repositories()
                total_indexed += sharepoint_count
                self.logger.info(f"Indexed {sharepoint_count} test cases from SharePoint")
            
            # Scan JIRA repositories (would be implemented when JIRA connector is available)
            if "jira" in self.connectors:
                jira_count = 0  # self._scan_jira_repositories()
                total_indexed += jira_count
                self.logger.info(f"Indexed {jira_count} test cases from JIRA")
            
            # Scan ALM repositories (would be implemented when ALM connector is available)
            if "alm" in self.connectors:
                alm_count = 0  # self._scan_alm_repositories()
                total_indexed += alm_count
                self.logger.info(f"Indexed {alm_count} test cases from ALM")
            
            # Update the last updated timestamp
            self.index_last_updated = datetime.now()
            
            # Save the index to file for persistence
            self._save_index()
            
            return total_indexed
            
        except Exception as e:
            self.logger.error(f"Repository scanning failed: {str(e)}")
            raise RepositoryScanError(f"Failed to scan repositories: {str(e)}")
    
    def _scan_sharepoint_repositories(self) -> int:
        """
        Scan SharePoint repositories for test cases.
        
        Returns:
            int: Number of test cases indexed from SharePoint.
            
        Raises:
            RepositoryScanError: If scanning SharePoint fails.
        """
        try:
            total_indexed = 0
            
            # Get SharePoint connector
            document_retriever = self.connectors.get("sharepoint")
            
            if not document_retriever:
                self.logger.warning("SharePoint connector not initialized, skipping scan")
                return 0
            
            # Scan each configured SharePoint site
            for site_config in self.config["repositories"]["sharepoint"]["sites"]:
                site_name = site_config["name"]
                site_url = site_config["url"]
                library = site_config["library"]
                folder_path = site_config["folder_path"]
                
                self.logger.info(f"Scanning SharePoint site: {site_name}, library: {library}")
                
                # Get list of files in the document library
                try:
                    file_list = document_retriever.list_files(
                        site_url=site_url,
                        library_name=library,
                        folder_path=folder_path
                    )
                    
                    self.logger.info(f"Found {len(file_list)} files in {library}/{folder_path}")
                    
                    # Filter by file type
                    allowed_extensions = self.config["repositories"]["sharepoint"]["file_types"]
                    filtered_files = [
                        f for f in file_list 
                        if any(f["Name"].lower().endswith(ext.lower()) for ext in allowed_extensions)
                    ]
                    
                    self.logger.info(f"Found {len(filtered_files)} test case files with allowed extensions")
                    
                    # Process files in batches
                    batch_size = self.config["scanning"]["batch_size"]
                    
                    for i in range(0, len(filtered_files), batch_size):
                        batch = filtered_files[i:i + batch_size]
                        
                        for file_info in batch:
                            file_name = file_info["Name"]
                            file_path = f"{folder_path}/{file_name}"
                            file_url = file_info.get("ServerRelativeUrl", "")
                            
                            try:
                                # Index the file
                                indexed = self._index_sharepoint_file(
                                    site_url=site_url,
                                    library_name=library,
                                    file_path=file_path,
                                    file_url=file_url,
                                    file_name=file_name,
                                    document_retriever=document_retriever
                                )
                                
                                if indexed:
                                    total_indexed += indexed
                                    
                            except Exception as e:
                                self.logger.error(f"Error indexing file {file_path}: {str(e)}")
                                continue
                    
                except Exception as e:
                    self.logger.error(f"Error listing files in {library}/{folder_path}: {str(e)}")
                    continue
            
            return total_indexed
            
        except Exception as e:
            self.logger.error(f"SharePoint repository scanning failed: {str(e)}")
            raise RepositoryScanError(f"Failed to scan SharePoint repositories: {str(e)}")
    
    def _index_sharepoint_file(self, site_url: str, library_name: str, file_path: str, 
                             file_url: str, file_name: str, document_retriever) -> int:
        """
        Index a single SharePoint file.
        
        Args:
            site_url (str): SharePoint site URL.
            library_name (str): Document library name.
            file_path (str): Path to the file in SharePoint.
            file_url (str): Server-relative URL of the file.
            file_name (str): Name of the file.
            document_retriever: Document retriever instance.
            
        Returns:
            int: Number of test cases indexed from this file.
            
        Raises:
            Exception: If indexing fails.
        """
        # Check file extension to determine how to process it
        file_extension = os.path.splitext(file_name.lower())[1]
        
        # Check if file is already indexed and unchanged
        file_key = f"sharepoint:{site_url}:{file_path}"
        
        if file_key in self.test_case_index:
            # Check if file has been modified
            try:
                file_metadata = document_retriever.get_file_metadata(
                    site_url=site_url,
                    library_name=library_name,
                    file_path=file_path
                )
                
                current_modified = file_metadata.get("Modified", "")
                indexed_modified = self.test_case_index[file_key].get("modified_date", "")
                
                if current_modified == indexed_modified:
                    self.logger.debug(f"File {file_path} already indexed and unchanged")
                    return 0
                
                self.logger.info(f"File {file_path} has been modified, re-indexing")
                
            except Exception as e:
                self.logger.warning(f"Failed to check modification status for {file_path}: {str(e)}")
                # Continue with indexing to be safe
        
        # Process based on file type
        test_cases = []
        
        try:
            if file_extension in ['.xlsx', '.xls']:
                # Excel format
                file_content = document_retriever.download_file(
                    site_url=site_url,
                    library_name=library_name,
                    file_path=file_path
                )
                
                # Extract test cases from Excel
                test_cases = self._extract_test_cases_from_excel(file_content, file_name)
                
            elif file_extension in ['.docx', '.doc']:
                # Word format
                file_content = document_retriever.download_file(
                    site_url=site_url,
                    library_name=library_name,
                    file_path=file_path
                )
                
                # Extract test cases from Word
                test_cases = self._extract_test_cases_from_word(file_content, file_name)
                
            elif file_extension == '.pdf':
                # PDF format
                file_content = document_retriever.download_file(
                    site_url=site_url,
                    library_name=library_name,
                    file_path=file_path
                )
                
                # Extract test cases from PDF
                test_cases = self._extract_test_cases_from_pdf(file_content, file_name)
            
            else:
                self.logger.warning(f"Unsupported file type: {file_extension} for {file_path}")
                return 0
            
            # Index extracted test cases
            if test_cases:
                # Get file metadata for indexing
                file_metadata = document_retriever.get_file_metadata(
                    site_url=site_url,
                    library_name=library_name,
                    file_path=file_path
                )
                
                modified_date = file_metadata.get("Modified", "")
                created_date = file_metadata.get("Created", "")
                created_by = file_metadata.get("CreatedBy", "")
                
                # Store in index
                self.test_case_index[file_key] = {
                    "repository": "sharepoint",
                    "site_url": site_url,
                    "library_name": library_name,
                    "file_path": file_path,
                    "file_url": file_url,
                    "file_name": file_name,
                    "file_type": file_extension,
                    "created_date": created_date,
                    "modified_date": modified_date,
                    "created_by": created_by,
                    "test_cases": test_cases
                }
                
                self.logger.info(f"Indexed {len(test_cases)} test cases from {file_path}")
                return len(test_cases)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to index {file_path}: {str(e)}")
            raise Exception(f"Failed to index {file_path}: {str(e)}")
    
    def _extract_test_cases_from_excel(self, file_content: bytes, file_name: str) -> List[Dict[str, Any]]:
        """
        Extract test cases from an Excel file.
        
        Args:
            file_content (bytes): Content of the Excel file.
            file_name (str): Name of the file.
            
        Returns:
            List[Dict[str, Any]]: List of extracted test cases.
        """
        test_cases = []
        
        try:
            # Read Excel file
            df = pd.read_excel(file_content, sheet_name=None)
            
            # Process each sheet
            for sheet_name, sheet_df in df.items():
                # Skip empty sheets
                if sheet_df.empty:
                    continue
                
                # Check if this sheet contains test cases
                # Look for common test case headers
                headers = sheet_df.columns.tolist()
                
                test_case_indicators = [
                    "TEST CASE ID", "TEST_CASE_ID", "TC ID", "Test Case Number",
                    "TEST STEPS", "TEST_STEPS", "Steps", "Test Steps",
                    "EXPECTED RESULT", "EXPECTED_RESULT", "Expected Results"
                ]
                
                is_test_case_sheet = any(indicator in str(header).upper() for header in headers 
                                      for indicator in test_case_indicators)
                
                if not is_test_case_sheet:
                    continue
                
                # Process rows as test cases
                for index, row in sheet_df.iterrows():
                    test_case = {}
                    
                    # Extract test case data based on known column patterns
                    for col in headers:
                        col_upper = str(col).upper()
                        value = row.get(col)
                        
                        # Skip empty values
                        if pd.isna(value) or value == "" or value is None:
                            continue
                        
                        # Map common column names to standardized fields
                        if any(id_field in col_upper for id_field in ["TEST CASE ID", "TEST_CASE_ID", "TC ID", "TEST CASE NUMBER"]):
                            test_case["TEST_CASE_ID"] = str(value)
                        
                        elif any(step_field in col_upper for step_field in ["TEST STEPS", "TEST_STEPS", "STEPS", "TEST STEP"]):
                            test_case["TEST_STEPS"] = str(value)
                        
                        elif any(result_field in col_upper for result_field in ["EXPECTED RESULT", "EXPECTED_RESULT", "EXPECTED RESULTS"]):
                            test_case["EXPECTED_RESULTS"] = str(value)
                        
                        elif any(desc_field in col_upper for desc_field in ["DESCRIPTION", "TEST DESCRIPTION", "TEST_DESCRIPTION"]):
                            test_case["DESCRIPTION"] = str(value)
                        
                        elif any(priority_field in col_upper for priority_field in ["PRIORITY", "TEST PRIORITY", "TEST_PRIORITY"]):
                            test_case["PRIORITY"] = str(value)
                        
                        elif any(owner_field in col_upper for owner_field in ["OWNER", "TEST OWNER", "TEST_OWNER", "ASSIGNED TO"]):
                            test_case["OWNER"] = str(value)
                        
                        else:
                            # Store other fields as is
                            test_case[str(col)] = str(value)
                    
                    # Only include rows that have at least a test case ID or steps
                    if test_case and ("TEST_CASE_ID" in test_case or "TEST_STEPS" in test_case):
                        # Add metadata
                        test_case["_source_file"] = file_name
                        test_case["_source_sheet"] = sheet_name
                        test_case["_source_row"] = index
                        
                        # Generate a test case ID if missing
                        if "TEST_CASE_ID" not in test_case:
                            # Create a unique ID based on file name and row
                            test_case["TEST_CASE_ID"] = f"{os.path.splitext(file_name)[0]}-{sheet_name}-{index}"
                        
                        test_cases.append(test_case)
            
            self.logger.info(f"Extracted {len(test_cases)} test cases from Excel file {file_name}")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Failed to extract test cases from Excel file {file_name}: {str(e)}")
            return []
    
    def _extract_test_cases_from_word(self, file_content: bytes, file_name: str) -> List[Dict[str, Any]]:
        """
        Extract test cases from a Word document.
        
        Args:
            file_content (bytes): Content of the Word document.
            file_name (str): Name of the file.
            
        Returns:
            List[Dict[str, Any]]: List of extracted test cases.
        """
        # This is a placeholder method that would need to be implemented
        # using libraries like python-docx to parse Word documents
        self.logger.warning(f"Word document parsing not fully implemented for {file_name}")
        
        # Return an empty list for now
        return []
    
    def _extract_test_cases_from_pdf(self, file_content: bytes, file_name: str) -> List[Dict[str, Any]]:
        """
        Extract test cases from a PDF document.
        
        Args:
            file_content (bytes): Content of the PDF document.
            file_name (str): Name of the file.
            
        Returns:
            List[Dict[str, Any]]: List of extracted test cases.
        """
        # This is a placeholder method that would need to be implemented
        # using libraries like PyPDF2 or pdfminer to parse PDF documents
        self.logger.warning(f"PDF document parsing not fully implemented for {file_name}")
        
        # Return an empty list for now
        return []
    
    def _save_index(self):
        """
        Save the test case index to a file.
        """
        try:
            index_file_path = self.config["indexing"]["index_file_path"]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(index_file_path), exist_ok=True)
            
            # Convert datetime objects to strings for serialization
            serialized_index = {}
            
            for key, value in self.test_case_index.items():
                serialized_value = value.copy()
                
                # Convert any datetime objects to ISO format strings
                for field, field_value in serialized_value.items():
                    if isinstance(field_value, datetime):
                        serialized_value[field] = field_value.isoformat()
                
                serialized_index[key] = serialized_value
            
            # Save to file
            with open(index_file_path, 'w') as f:
                json.dump(serialized_index, f, indent=2)
            
            self.logger.info(f"Saved test case index to {index_file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save test case index: {str(e)}")
    
    def _load_index(self):
        """
        Load the test case index from a file.
        
        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        try:
            index_file_path = self.config["indexing"]["index_file_path"]
            
            if not os.path.exists(index_file_path):
                self.logger.info(f"No existing index file found at {index_file_path}")
                return False
            
            with open(index_file_path, 'r') as f:
                serialized_index = json.load(f)
            
            # Parse datetime strings back to datetime objects
            for key, value in serialized_index.items():
                for field in ["created_date", "modified_date"]:
                    if field in value and value[field]:
                        try:
                            value[field] = datetime.fromisoformat(value[field])
                        except ValueError:
                            # Keep as string if parsing fails
                            pass
            
            self.test_case_index = serialized_index
            self.index_last_updated = datetime.now()
            
            self.logger.info(f"Loaded test case index from {index_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load test case index: {str(e)}")
            return False
    
    def search_test_cases(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for test cases in the index based on criteria.
        
        Args:
            criteria (Dict[str, Any]): Search criteria.
                Keys can be any test case field, with special handling for:
                - 'repository': 'sharepoint', 'jira', 'alm'
                - 'file_type': '.xlsx', '.docx', etc.
                - 'text': Full text search across all fields
            
        Returns:
            List[Dict[str, Any]]: List of matching test cases with source information.
        """
        try:
            # Load index if not already loaded
            if not self.test_case_index:
                if not self._load_index():
                    # Perform a scan if no index exists
                    self.scan_repositories()
            
            # Prepare results list
            results = []
            
            # Extract special criteria
            repository = criteria.pop('repository', None)
            file_type = criteria.pop('file_type', None)
            text_search = criteria.pop('text', None)
            
            # Iterate through indexed test cases
            for file_key, file_info in self.test_case_index.items():
                # Filter by repository if specified
                if repository and file_info.get('repository') != repository:
                    continue
                
                # Filter by file type if specified
                if file_type and file_info.get('file_type') != file_type:
                    continue
                
                # Process test cases in this file
                for test_case in file_info.get('test_cases', []):
                    match = True
                    
                    # Check each criteria against the test case
                    for field, value in criteria.items():
                        if field not in test_case or test_case[field] != value:
                            match = False
                            break
                    
                    # Full text search if specified
                    if text_search and match:
                        text_match = False
                        search_term = text_search.lower()
                        
                        # Search across all text fields
                        for field_name, field_value in test_case.items():
                            if isinstance(field_value, str) and search_term in field_value.lower():
                                text_match = True
                                break
                        
                        if not text_match:
                            match = False
                    
                    # Add to results if all criteria match
                    if match:
                        # Include file information with the test case
                        result = test_case.copy()
                        result['_repository'] = file_info.get('repository')
                        result['_file_name'] = file_info.get('file_name')
                        result['_file_path'] = file_info.get('file_path')
                        result['_site_url'] = file_info.get('site_url')
                        result['_library_name'] = file_info.get('library_name')
                        result['_file_url'] = file_info.get('file_url')
                        
                        results.append(result)
            
            self.logger.info(f"Found {len(results)} test cases matching criteria")
            return results
            
        except Exception as e:
            self.logger.error(f"Test case search failed: {str(e)}")
            return []
    
    def get_test_case_by_id(self, test_case_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific test case by ID.
        
        Args:
            test_case_id (str): The test case ID to retrieve.
            
        Returns:
            Dict[str, Any]: The test case data with source information,
                or None if not found.
        """
        results = self.search_test_cases({"TEST_CASE_ID": test_case_id})
        
        if results:
            return results[0]
        
        return None
    
    def get_test_case_content(self, test_case_id: str) -> Tuple[Dict[str, Any], bytes]:
        """
        Retrieve a test case by ID along with its source file content.
        
        This is useful for comparison engines that need to examine the
        full content of the original file.
        
        Args:
            test_case_id (str): The test case ID to retrieve.
            
        Returns:
            Tuple[Dict[str, Any], bytes]: The test case data and the content
                of its source file, or (None, None) if not found.
        """
        # First, find the test case
        test_case = self.get_test_case_by_id(test_case_id)
        
        if not test_case:
            return None, None
        
        # Get repository information
        repository = test_case.get('_repository')
        
        if repository == 'sharepoint':
            site_url = test_case.get('_site_url')
            library_name = test_case.get('_library_name')
            file_path = test_case.get('_file_path')
            
            try:
                # Download the file
                document_retriever = self.connectors.get('sharepoint')
                
                if document_retriever:
                    file_content = document_retriever.download_file(
                        site_url=site_url,
                        library_name=library_name,
                        file_path=file_path
                    )
                    
                    return test_case, file_content
                
            except Exception as e:
                self.logger.error(f"Failed to retrieve test case file content: {str(e)}")
                return test_case, None
                
        # For other repository types (to be implemented)
        self.logger.warning(f"Retrieving content from {repository} not implemented")
        return test_case, None
    
    def get_test_cases_for_module(self, module: str) -> List[Dict[str, Any]]:
        """
        Get all test cases for a specific module or component.
        
        Args:
            module (str): Module name to search for.
            
        Returns:
            List[Dict[str, Any]]: List of test cases for the module.
        """
        return self.search_test_cases({
            "MODULE": module
        })
    
    def get_test_cases_by_type(self, test_type: str) -> List[Dict[str, Any]]:
        """
        Get all test cases of a specific type.
        
        Args:
            test_type (str): Test type to search for (e.g., 'Functional', 'Performance').
            
        Returns:
            List[Dict[str, Any]]: List of test cases of the specified type.
        """
        # Search for multiple field names that might contain test type
        results = []
        
        # Try different field names that might contain test type
        for field in ["TEST_TYPE", "Type", "TEST TYPE"]:
            cases = self.search_test_cases({field: test_type})
            for case in cases:
                if case not in results:  # Avoid duplicates
                    results.append(case)
        
        return results
    
    def get_test_cases_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Get all test cases with a specific tag.
        
        Args:
            tag (str): Tag to search for.
            
        Returns:
            List[Dict[str, Any]]: List of test cases with the specified tag.
        """
        # This assumes that the tag information has been extracted during indexing
        return self.search_test_cases({
            "TAGS": {"op": "contains", "value": tag}
        })
    
    def get_test_cases_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """
        Get all test cases with a specific priority.
        
        Args:
            priority (str): Priority to search for (e.g., 'High', 'Medium', 'Low').
            
        Returns:
            List[Dict[str, Any]]: List of test cases with the specified priority.
        """
        # Search for multiple field names that might contain priority
        results = []
        
        # Try different field names that might contain priority
        for field in ["PRIORITY", "Priority", "TEST PRIORITY"]:
            cases = self.search_test_cases({field: priority})
            for case in cases:
                if case not in results:  # Avoid duplicates
                    results.append(case)
        
        return results
    
    def get_all_test_cases(self) -> List[Dict[str, Any]]:
        """
        Get all indexed test cases.
        
        Returns:
            List[Dict[str, Any]]: List of all test cases.
        """
        return self.search_test_cases({})
    
    def get_test_case_count(self) -> Dict[str, int]:
        """
        Get counts of test cases by repository and file type.
        
        Returns:
            Dict[str, int]: Dictionary with count statistics.
        """
        stats = {
            "total": 0,
            "repositories": {},
            "file_types": {}
        }
        
        # Count test cases
        for file_key, file_info in self.test_case_index.items():
            test_case_count = len(file_info.get('test_cases', []))
            
            # Update total
            stats["total"] += test_case_count
            
            # Update repository count
            repository = file_info.get('repository')
            if repository:
                stats["repositories"][repository] = stats["repositories"].get(repository, 0) + test_case_count
            
            # Update file type count
            file_type = file_info.get('file_type')
            if file_type:
                stats["file_types"][file_type] = stats["file_types"].get(file_type, 0) + test_case_count
        
        return stats


# If running as a script
if __name__ == "__main__":
    import argparse
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Scan test case repositories")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--scan", action="store_true", help="Scan repositories")
    parser.add_argument("--refresh", action="store_true", help="Force refresh of the index")
    parser.add_argument("--search", help="Search for test cases (JSON criteria)")
    parser.add_argument("--get", help="Get test case by ID")
    parser.add_argument("--stats", action="store_true", help="Get test case statistics")
    
    args = parser.parse_args()
    
    # Create repository scanner
    scanner = RepositoryScanner(config_path=args.config)
    
    # Execute requested action
    if args.scan or args.refresh:
        count = scanner.scan_repositories(force_refresh=args.refresh)
        print(f"Indexed {count} test cases")
    
    elif args.search:
        try:
            criteria = json.loads(args.search)
            results = scanner.search_test_cases(criteria)
            print(f"Found {len(results)} matching test cases:")
            
            for idx, test_case in enumerate(results, 1):
                print(f"\n{idx}. {test_case.get('TEST_CASE_ID', 'Unknown ID')}")
                print(f"   File: {test_case.get('_file_name', 'Unknown')}")
                print(f"   Repository: {test_case.get('_repository', 'Unknown')}")
                
                # Print first few fields
                for field, value in test_case.items():
                    if not field.startswith('_') and field not in ['TEST_CASE_ID']:
                        print(f"   {field}: {value}")
                        # Limit to first 3 fields
                        if field == list(filter(lambda f: not f.startswith('_') and f != 'TEST_CASE_ID', 
                                           test_case.keys()))[2]:
                            break
                
                # Add ellipsis if there are more fields
                if len([f for f in test_case.keys() if not f.startswith('_') 
                     and f != 'TEST_CASE_ID']) > 3:
                    print("   ...")
                    
        except json.JSONDecodeError:
            print("Error: Search criteria must be valid JSON")
    
    elif args.get:
        test_case = scanner.get_test_case_by_id(args.get)
        
        if test_case:
            print(f"\nTest Case: {test_case.get('TEST_CASE_ID', 'Unknown ID')}")
            print(f"File: {test_case.get('_file_name', 'Unknown')}")
            print(f"Repository: {test_case.get('_repository', 'Unknown')}")
            print("\nFields:")
            
            for field, value in test_case.items():
                if not field.startswith('_'):
                    print(f"  {field}: {value}")
        else:
            print(f"Test case {args.get} not found")
    
    elif args.stats:
        stats = scanner.get_test_case_count()
        
        print("\nTest Case Statistics:")
        print(f"Total test cases: {stats['total']}")
        
        print("\nBy Repository:")
        for repo, count in stats.get('repositories', {}).items():
            print(f"  {repo}: {count}")
        
        print("\nBy File Type:")
        for file_type, count in stats.get('file_types', {}).items():
            print(f"  {file_type}: {count}")
    
    else:
        parser.print_help()