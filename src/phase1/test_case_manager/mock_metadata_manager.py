# File: src/phase1/test_case_manager/mock_metadata_manager.py (Part 1)

"""
Mock implementation of the MetadataManager for development without a database.

This module provides an in-memory storage implementation of the MetadataManager
class, allowing development to continue without an actual database connection.
"""

import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import uuid
import base64
from io import BytesIO

# Import custom exceptions if available
try:
    from src.common.exceptions.custom_exceptions import (
        MetadataError,
        DatabaseError,
        SchemaValidationError
    )
except ImportError:
    # Define fallback exceptions if common modules are not available
    class MetadataError(Exception):
        pass
    
    class DatabaseError(Exception):
        pass
    
    class SchemaValidationError(Exception):
        pass

# For DataFrame support
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Setup logger
logger = logging.getLogger(__name__)

class MockMetadataManager:
    """
    Mock implementation of the MetadataManager using in-memory storage.
    
    This class mimics the behavior of the real MetadataManager but uses
    dictionary-based storage instead of a database to store metadata.
    """
    
    # Default metadata schema (same as the real implementation)
    DEFAULT_SCHEMA = {
        "metadata_fields": {
            "TEST_CASE_ID": {
                "type": "string",
                "required": True,
                "description": "Unique identifier for the test case"
            },
            "OWNER": {
                "type": "string",
                "required": True,
                "description": "Person responsible for the test case"
            },
            "STATUS": {
                "type": "enum",
                "values": ["Active", "Under Maintenance", "Obsolete", "Draft"],
                "required": True,
                "default": "Draft",
                "description": "Current status of the test case"
            },
            "PRIORITY": {
                "type": "enum",
                "values": ["High", "Medium", "Low"],
                "required": True,
                "default": "Medium",
                "description": "Priority level of the test case"
            },
            "AUTOMATION_STATUS": {
                "type": "enum",
                "values": ["Automated", "Manual", "Candidate for Automation", "Under Development"],
                "required": True,
                "default": "Manual",
                "description": "Current automation status of the test case"
            },
            "CREATED_DATE": {
                "type": "date",
                "required": True,
                "description": "Date when the test case was created"
            },
            "MODIFIED_DATE": {
                "type": "date",
                "required": True,
                "description": "Date when the test case was last modified"
            },
            "CREATED_BY": {
                "type": "string",
                "required": False,
                "description": "Person who created the test case"
            },
            "MODIFIED_BY": {
                "type": "string",
                "required": False,
                "description": "Person who last modified the test case"
            },
            "TAGS": {
                "type": "array",
                "required": False,
                "description": "Tags or labels associated with the test case"
            },
            "MODULE": {
                "type": "string",
                "required": False,
                "description": "Module or component the test case belongs to"
            },
            "TEST_LEVEL": {
                "type": "enum",
                "values": ["Unit", "Integration", "System", "Acceptance"],
                "required": False,
                "description": "Testing level of the test case"
            },
            "TEST_TYPE": {
                "type": "enum",
                "values": ["Functional", "Performance", "Security", "Usability", "Regression"],
                "required": False,
                "default": "Functional",
                "description": "Type of testing covered by the test case"
            },
            "LAST_EXECUTION_DATE": {
                "type": "date",
                "required": False,
                "description": "Date when the test case was last executed"
            },
            "LAST_EXECUTION_RESULT": {
                "type": "enum",
                "values": ["Pass", "Fail", "Blocked", "Not Executed"],
                "required": False,
                "default": "Not Executed",
                "description": "Result of the last execution"
            },
            "TEST_CASE_CONTENT": {
                "type": "binary",
                "required": False,
                "description": "The actual content of the test case file (Excel, etc.)"
            },
            "FILE_NAME": {
                "type": "string",
                "required": False,
                "description": "Original file name of the test case"
            },
            "FILE_TYPE": {
                "type": "string",
                "required": False,
                "description": "File type/extension of the test case"
            }
        }
    }
    
    def __init__(self, schema_path: str = None, min_conn: int = 1, max_conn: int = 10, *args, **kwargs):
        """
        Initialize the MockMetadataManager with in-memory storage.
        
        Args:
            schema_path (str, optional): Path to metadata schema file.
            min_conn (int, optional): Ignored in mock implementation.
            max_conn (int, optional): Ignored in mock implementation.
        """
        self.schema_path = schema_path
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing MockMetadataManager with in-memory storage")
        
        # Load schema
        if schema_path and os.path.exists(schema_path):
            self._load_schema_from_file()
        else:
            self.schema = self.DEFAULT_SCHEMA
            self.logger.info("Using default metadata schema")
        
        # In-memory storage
        self._test_cases = {}  # Key: test_case_id, Value: metadata dict
        self._files = {}       # Key: test_case_id, Value: file info dict
        self._tags = {}        # Key: tag name, Value: tag id
        self._tag_associations = {}  # Key: test_case_id, Value: list of tag names
        self._history = []     # List of history records
        
        # Mock database connection information for compatibility
        self.db_config = {
            'host': 'mock-db',
            'port': '5432',
            'dbname': 'mock_database',
            'user': 'mock_user',
            'password': 'mock_password',
            'sslmode': 'disable'
        }
        
        # Load mock data file if it exists (for persistence between runs)
        self._load_mock_data()
    
    def _load_schema_from_file(self):
        """
        Load metadata schema from a JSON file.
        
        Raises:
            SchemaValidationError: If the schema file is invalid.
        """
        try:
            with open(self.schema_path, 'r') as f:
                schema = json.load(f)
            
            # Validate schema structure
            if "metadata_fields" not in schema:
                raise SchemaValidationError("Schema must contain 'metadata_fields' key")
            
            # Check that required fields are present
            required_fields = ["TEST_CASE_ID", "STATUS"]
            for field in required_fields:
                if field not in schema["metadata_fields"]:
                    raise SchemaValidationError(f"Required field '{field}' missing from schema")
            
            self.schema = schema
            self.logger.debug(f"Schema loaded from {self.schema_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load schema: {str(e)}")
            self.schema = self.DEFAULT_SCHEMA
            self.logger.warning(f"Using default schema instead")
    
    def _load_mock_data(self):
        """Load data from mock_data.json if available."""
        data_file = os.path.join(os.getcwd(), 'mock_data.json')
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    self._test_cases = data.get('test_cases', {})
                    self._files = data.get('files', {})
                    self._tags = data.get('tags', {})
                    self._tag_associations = data.get('tag_associations', {})
                    self._history = data.get('history', [])
                self.logger.info(f"Loaded mock data with {len(self._test_cases)} test cases")
            except Exception as e:
                self.logger.error(f"Error loading mock data: {str(e)}")
    
    def _save_mock_data(self):
        """Save current data to mock_data.json for persistence."""
        try:
            # Save only if we have data
            if not self._test_cases:
                return
                
            data = {
                'test_cases': self._test_cases,
                'files': self._files,
                'tags': self._tags,
                'tag_associations': self._tag_associations,
                'history': self._history
            }
            
            data_file = os.path.join(os.getcwd(), 'mock_data.json')
            with open(data_file, 'w') as f:
                json.dump(data, f, default=self._json_serializer)
            
            self.logger.debug("Saved mock data")
        except Exception as e:
            self.logger.error(f"Error saving mock data: {str(e)}")
    
    def _json_serializer(self, obj):
        """Handle special objects in JSON serialization."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate metadata against the schema.
        
        Args:
            metadata: The metadata to validate.
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check required fields
        for field_name, field_def in self.schema["metadata_fields"].items():
            if field_def.get("required", False) and field_name not in metadata:
                errors.append(f"Required field '{field_name}' is missing")
        
        # Validate field types and values (simplified for mock)
        for field_name, value in metadata.items():
            if field_name in self.schema["metadata_fields"]:
                field_def = self.schema["metadata_fields"][field_name]
                field_type = field_def["type"]
                
                # Skip validation for None values in non-required fields
                if value is None and not field_def.get("required", False):
                    continue
                
                # Enum validation
                if field_type == "enum" and "values" in field_def:
                    if value not in field_def["values"]:
                        errors.append(f"Value '{value}' for '{field_name}' must be one of: {field_def['values']}")
        
        return len(errors) == 0, errors
    
    def _apply_defaults(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values from schema for missing fields."""
        updated = metadata.copy()
        
        for field_name, field_def in self.schema["metadata_fields"].items():
            if field_name not in updated and "default" in field_def:
                updated[field_name] = field_def["default"]
        
        return updated
    
    # ====== Core CRUD Methods ======
    
    def create_test_case_metadata(self, test_case_data: Dict[str, Any], created_by: str = None) -> str:
        """
        Create metadata for a new test case in memory.
        
        Args:
            test_case_data: Test case metadata.
            created_by: Person creating the test case.
            
        Returns:
            str: The TEST_CASE_ID of the created metadata.
            
        Raises:
            MetadataError: If metadata creation fails.
        """
        try:
            # Extract TEST_CASE_ID or generate a new one
            test_case_id = test_case_data.get("TEST_CASE_ID") or test_case_data.get("TEST CASE NUMBER")
            
            if not test_case_id:
                test_case_id = f"TC-{uuid.uuid4().hex[:8].upper()}"
                self.logger.info(f"Generated new TEST_CASE_ID: {test_case_id}")
            
            # Extract owner
            owner = test_case_data.get("OWNER") or test_case_data.get("TEST USER ID/ROLE")
            
            if not owner:
                # Mock owner assignment
                owner = "Unassigned"
            
            # Build metadata
            now = datetime.now().isoformat()
            
            metadata = {
                "TEST_CASE_ID": test_case_id,
                "OWNER": owner,
                "STATUS": test_case_data.get("STATUS", "Draft"),
                "CREATED_DATE": now,
                "MODIFIED_DATE": now,
                "CREATED_BY": created_by or "System"
            }
            
            # Add all other fields from test_case_data
            for key, value in test_case_data.items():
                if key not in metadata:
                    metadata[key] = value
            
            # Apply defaults
            metadata = self._apply_defaults(metadata)
            
            # Validate metadata
            is_valid, errors = self._validate_metadata(metadata)
            if not is_valid:
                error_msg = f"Invalid metadata: {'; '.join(errors)}"
                self.logger.error(error_msg)
                raise MetadataError(error_msg)
            
            # Store metadata
            self._test_cases[test_case_id] = metadata
            
            # Handle tags if present
            if "TAGS" in metadata and metadata["TAGS"]:
                self._update_test_case_tags(test_case_id, metadata["TAGS"])
            
            # Save to disk
            self._save_mock_data()
            
            self.logger.info(f"Created metadata for test case {test_case_id}")
            return test_case_id
            
        except Exception as e:
            self.logger.error(f"Failed to create metadata: {str(e)}")
            raise MetadataError(f"Failed to create metadata: {str(e)}")

    def _update_test_case_tags(self, test_case_id: str, tags: List[str]) -> bool:
        """Update tags for a test case in memory."""
        try:
            # Convert to list if it's a string
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',')]
            elif tags is None:
                tags = []
            
            # Store tags and associations
            for tag in tags:
                if tag:  # Skip empty tags
                    # Add tag if it doesn't exist
                    if tag not in self._tags:
                        self._tags[tag] = len(self._tags) + 1
            
            # Store associations
            self._tag_associations[test_case_id] = tags
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update tags: {str(e)}")
            return False
        
# File: src/phase1/test_case_manager/mock_metadata_manager.py (Part 2)

    def get_test_case_metadata(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get metadata for a test case from memory.
        
        Args:
            test_case_id: The test case ID.
            
        Returns:
            Dict[str, Any]: The metadata, or None if not found.
        """
        try:
            if test_case_id in self._test_cases:
                # Get a copy of the metadata
                metadata = self._test_cases[test_case_id].copy()
                
                # Add tags if available
                if test_case_id in self._tag_associations:
                    metadata["TAGS"] = self._tag_associations[test_case_id]
                
                return metadata
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata: {str(e)}")
            return None

    def update_test_case_metadata(self, test_case_id: str, updates: Dict[str, Any], 
                                modified_by: str = None) -> Dict[str, Any]:
        """
        Update metadata for an existing test case in memory.
        
        Args:
            test_case_id: The test case ID.
            updates: Metadata fields to update.
            modified_by: Person making the updates.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If metadata update fails.
        """
        try:
            # Check if the test case exists
            if test_case_id not in self._test_cases:
                raise MetadataError(f"Test case {test_case_id} not found")
            
            # Get current metadata
            metadata = self._test_cases[test_case_id].copy()
            
            # Record history
            for key, new_value in updates.items():
                if key in metadata:
                    old_value = metadata[key]
                    self._history.append({
                        'test_case_id': test_case_id,
                        'field_name': key,
                        'old_value': old_value,
                        'new_value': new_value,
                        'changed_by': modified_by,
                        'changed_at': datetime.now().isoformat()
                    })
            
            # Handle steps separately if present
            if "STEPS" in updates:
                self.logger.warning("Step-level updates not fully supported in mock implementation")
                # Just log the steps for now, in a real implementation we'd store them properly
                metadata["STEPS"] = updates.pop("STEPS")
            
            # Update metadata
            for key, value in updates.items():
                metadata[key] = value
            
            # Update modification timestamp
            metadata["MODIFIED_DATE"] = datetime.now().isoformat()
            if modified_by:
                metadata["MODIFIED_BY"] = modified_by
            
            # Handle tags if present
            if "TAGS" in updates:
                self._update_test_case_tags(test_case_id, updates["TAGS"])
            
            # Store updated metadata
            self._test_cases[test_case_id] = metadata
            
            # Save to disk
            self._save_mock_data()
            
            # Return a copy of the updated metadata
            result = metadata.copy()
            if test_case_id in self._tag_associations:
                result["TAGS"] = self._tag_associations[test_case_id]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata: {str(e)}")
            raise MetadataError(f"Failed to update metadata: {str(e)}")

    def delete_test_case_metadata(self, test_case_id: str) -> bool:
        """
        Delete metadata for a test case from memory.
        
        Args:
            test_case_id: The test case ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Check if the test case exists
            if test_case_id not in self._test_cases:
                return False
            
            # Remove metadata
            del self._test_cases[test_case_id]
            
            # Remove associated files
            if test_case_id in self._files:
                del self._files[test_case_id]
            
            # Remove tag associations
            if test_case_id in self._tag_associations:
                del self._tag_associations[test_case_id]
            
            # Keep history for traceability
            
            # Save to disk
            self._save_mock_data()
            
            self.logger.info(f"Deleted metadata for test case {test_case_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete metadata: {str(e)}")
            return False

    def search_test_cases(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for test cases based on metadata criteria.
        
        Args:
            criteria: Search criteria.
            
        Returns:
            List[Dict[str, Any]]: List of matching test case metadata.
        """
        try:
            results = []
            
            for test_case_id, metadata in self._test_cases.items():
                # Check if all criteria match
                matches = True
                
                for field, criteria_value in criteria.items():
                    # Skip fields that don't exist in metadata
                    if field not in metadata:
                        # Special handling for TAGS
                        if field == "TAGS" and test_case_id in self._tag_associations:
                            if not self._match_tags(test_case_id, criteria_value):
                                matches = False
                                break
                        else:
                            matches = False
                            break
                    
                    # Handle complex criteria with operators
                    if isinstance(criteria_value, dict) and "op" in criteria_value:
                        op = criteria_value["op"].lower()
                        value = criteria_value["value"]
                        
                        if op == "equals" or op == "=":
                            if metadata[field] != value:
                                matches = False
                                break
                        elif op == "not equals" or op == "!=":
                            if metadata[field] == value:
                                matches = False
                                break
                        elif op == "contains" or op == "like":
                            if not self._contains_value(metadata[field], value):
                                matches = False
                                break
                        elif op == "in":
                            if metadata[field] not in value:
                                matches = False
                                break
                        elif op == "not in":
                            if metadata[field] in value:
                                matches = False
                                break
                        # Add support for other operators as needed
                    else:
                        # Simple equality match
                        if metadata[field] != criteria_value:
                            matches = False
                            break
                
                if matches:
                    # Return a copy with tags added
                    result = metadata.copy()
                    if test_case_id in self._tag_associations:
                        result["TAGS"] = self._tag_associations[test_case_id]
                    results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return []

    def _match_tags(self, test_case_id: str, tag_criteria: Any) -> bool:
        """Check if a test case's tags match the criteria."""
        if test_case_id not in self._tag_associations:
            return False
        
        case_tags = self._tag_associations[test_case_id]
        
        # Simple list/array of tags to match
        if isinstance(tag_criteria, (list, tuple)):
            # Check if all criteria tags are in case tags
            return all(tag in case_tags for tag in tag_criteria)
        
        # Single tag to match
        if isinstance(tag_criteria, str):
            return tag_criteria in case_tags
        
        # Complex criteria with operators
        if isinstance(tag_criteria, dict) and "op" in tag_criteria:
            op = tag_criteria["op"].lower()
            value = tag_criteria["value"]
            
            if op == "contains":
                # Check if any tag contains the value
                return any(value.lower() in tag.lower() for tag in case_tags)
            
            # Add support for other tag-specific operators as needed
        
        return False

    def _contains_value(self, field_value: Any, search_value: Any) -> bool:
        """Check if a field value contains a search value."""
        if isinstance(field_value, str) and isinstance(search_value, str):
            return search_value.lower() in field_value.lower()
        
        if isinstance(field_value, (list, tuple)) and not isinstance(search_value, (list, tuple)):
            return search_value in field_value
        
        # Default comparison
        return field_value == search_value

    def get_metadata_history(self, test_case_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of metadata changes for a test case.
        
        Args:
            test_case_id: The test case ID.
            
        Returns:
            List[Dict[str, Any]]: List of history entries, ordered by time.
        """
        try:
            # Filter history for the specific test case
            case_history = [h for h in self._history if h['test_case_id'] == test_case_id]
            
            # Sort by change time (descending)
            return sorted(case_history, key=lambda h: h['changed_at'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata history: {str(e)}")
            return []

    # ====== File Management Methods ======
    
    def store_test_case_file_content(self, test_case_id: str, file_name: str, 
                                    file_content: bytes, file_type: str = None,
                                    uploaded_by: str = None) -> bool:
        """
        Store the content of a test case file in memory.
        
        Args:
            test_case_id: The test case ID.
            file_name: The name of the file.
            file_content: The content of the file as bytes.
            file_type: The file type.
            uploaded_by: Person uploading the file.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Check if test case exists
            if test_case_id not in self._test_cases:
                raise MetadataError(f"Test case {test_case_id} not found")
            
            # Determine file type if not provided
            if not file_type and file_name:
                file_type = os.path.splitext(file_name)[1].lstrip('.')
            
            # Store file information
            self._files[test_case_id] = {
                'file_name': file_name,
                'file_type': file_type or 'unknown',
                'content': base64.b64encode(file_content).decode('utf-8'),  # Store as base64 string
                'uploaded_at': datetime.now().isoformat(),
                'uploaded_by': uploaded_by
            }
            
            # Update test case metadata
            self.update_test_case_metadata(
                test_case_id,
                {
                    'FILE_NAME': file_name,
                    'FILE_TYPE': file_type,
                },
                uploaded_by
            )
            
            # Save to disk
            self._save_mock_data()
            
            self.logger.info(f"Stored file '{file_name}' for test case {test_case_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store test case file: {str(e)}")
            return False

    def retrieve_test_case_file_content(self, test_case_id: str) -> Tuple[str, str, bytes]:
        """
        Retrieve the content of a test case file from memory.
        
        Args:
            test_case_id: The test case ID.
            
        Returns:
            Tuple[str, str, bytes]: (file_name, file_type, file_content)
        """
        try:
            if test_case_id not in self._files:
                self.logger.warning(f"No file found for test case {test_case_id}")
                return None, None, None
            
            file_info = self._files[test_case_id]
            
            # Decode content from base64
            file_content = base64.b64decode(file_info['content'])
            
            return file_info['file_name'], file_info['file_type'], file_content
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve test case file: {str(e)}")
            return None, None, None

    def file_exists_for_test_case(self, test_case_id: str) -> bool:
        """Check if a file exists for a test case."""
        return test_case_id in self._files

    def get_test_case_file_as_dataframe(self, test_case_id: str) -> Optional[Any]:
        """
        Retrieve a test case file as a pandas DataFrame from memory.
        
        Args:
            test_case_id: The test case ID.
            
        Returns:
            Optional[pd.DataFrame]: The test case data as a DataFrame or None.
        """
        if not HAS_PANDAS:
            self.logger.error("pandas is not installed")
            return None
        
        try:
            file_name, file_type, file_content = self.retrieve_test_case_file_content(test_case_id)
            
            if not file_content:
                return None
            
            # Create a BytesIO object from the file content
            file_obj = BytesIO(file_content)
            
            # Read as DataFrame based on file type
            file_type = file_type.lower() if file_type else ''
            
            if file_type in ['xlsx', 'xls']:
                # Read Excel file
                df = pd.read_excel(file_obj)
            elif file_type == 'csv':
                # Read CSV file
                df = pd.read_csv(file_obj)
            else:
                self.logger.error(f"Unsupported file type: {file_type}")
                return None
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to convert test case file to DataFrame: {str(e)}")
            return None
        

# File: src/phase1/test_case_manager/mock_metadata_manager.py (Part 2 - continued)

    # ====== Statistics and Utility Methods ======
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about test cases.
        
        Returns:
            Dict[str, Any]: Statistics including counts by status, type, etc.
        """
        try:
            stats = {
                "total_count": len(self._test_cases),
                "by_status": {},
                "by_type": {},
                "by_automation_status": {},
                "by_module": {},
                "recently_modified": []
            }
            
            # Count by status
            for metadata in self._test_cases.values():
                status = metadata.get('STATUS', 'Unknown')
                if status in stats['by_status']:
                    stats['by_status'][status] += 1
                else:
                    stats['by_status'][status] = 1
                
                # Count by type
                type_val = metadata.get('TYPE', metadata.get('TEST_TYPE', 'Unknown'))
                if type_val in stats['by_type']:
                    stats['by_type'][type_val] += 1
                else:
                    stats['by_type'][type_val] = 1
                
                # Count by automation status
                auto_status = metadata.get('AUTOMATION_STATUS', 'Unknown')
                if auto_status in stats['by_automation_status']:
                    stats['by_automation_status'][auto_status] += 1
                else:
                    stats['by_automation_status'][auto_status] = 1
                
                # Count by module
                module = metadata.get('MODULE', 'Unknown')
                if module in stats['by_module']:
                    stats['by_module'][module] += 1
                else:
                    stats['by_module'][module] = 1
            
            # Get recently modified
            sorted_cases = sorted(
                self._test_cases.values(),
                key=lambda x: x.get('MODIFIED_DATE', ''),
                reverse=True
            )
            
            # Take the 5 most recently modified
            stats['recently_modified'] = sorted_cases[:5]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {"total_count": 0}

    def get_all_tags(self) -> List[str]:
        """Get all unique tags used across all test cases."""
        return list(self._tags.keys())

    def get_test_cases_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        """Get all test cases owned by a specific person."""
        return self.search_test_cases({"OWNER": owner})

    def get_test_cases_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all test cases with a specific status."""
        return self.search_test_cases({"STATUS": status})

    def get_test_cases_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Get all test cases that have all the specified tags."""
        return self.search_test_cases({"TAGS": tags})

    def get_test_cases_by_module(self, module: str) -> List[Dict[str, Any]]:
        """Get all test cases for a specific module."""
        return self.search_test_cases({"MODULE": module})

    # ====== Convenience Methods for Common Updates ======
    
    def update_test_case_status(self, test_case_id: str, new_status: str, 
                              modified_by: str = None) -> Dict[str, Any]:
        """
        Update the status of a test case.
        
        Args:
            test_case_id: The test case ID.
            new_status: The new status.
            modified_by: Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
        """
        # Validate status
        if "STATUS" in self.schema["metadata_fields"]:
            field_def = self.schema["metadata_fields"]["STATUS"]
            if field_def["type"] == "enum" and "values" in field_def:
                if new_status not in field_def["values"]:
                    raise MetadataError(f"Invalid status: {new_status}. Must be one of: {field_def['values']}")
        
        # Update the status
        return self.update_test_case_metadata(
            test_case_id,
            {"STATUS": new_status},
            modified_by
        )

    def update_test_case_owner(self, test_case_id: str, new_owner: str, 
                             modified_by: str = None) -> Dict[str, Any]:
        """
        Update the owner of a test case.
        
        Args:
            test_case_id: The test case ID.
            new_owner: The new owner.
            modified_by: Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
        """
        return self.update_test_case_metadata(
            test_case_id,
            {"OWNER": new_owner},
            modified_by
        )

    def update_automation_status(self, test_case_id: str, new_status: str, 
                               modified_by: str = None) -> Dict[str, Any]:
        """
        Update the automation status of a test case.
        
        Args:
            test_case_id: The test case ID.
            new_status: The new automation status.
            modified_by: Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
        """
        # Validate automation status
        if "AUTOMATION_STATUS" in self.schema["metadata_fields"]:
            field_def = self.schema["metadata_fields"]["AUTOMATION_STATUS"]
            if field_def["type"] == "enum" and "values" in field_def:
                if new_status not in field_def["values"]:
                    raise MetadataError(
                        f"Invalid automation status: {new_status}. Must be one of: {field_def['values']}"
                    )
        
        # Update the automation status
        return self.update_test_case_metadata(
            test_case_id,
            {"AUTOMATION_STATUS": new_status},
            modified_by
        )

    def update_test_execution_result(self, test_case_id: str, result: str, 
                                   executed_by: str = None) -> Dict[str, Any]:
        """
        Update the test execution result for a test case.
        
        Args:
            test_case_id: The test case ID.
            result: The execution result.
            executed_by: Person who executed the test.
            
        Returns:
            Dict[str, Any]: The updated metadata.
        """
        # Validate result
        if "LAST_EXECUTION_RESULT" in self.schema["metadata_fields"]:
            field_def = self.schema["metadata_fields"]["LAST_EXECUTION_RESULT"]
            if field_def["type"] == "enum" and "values" in field_def:
                if result not in field_def["values"]:
                    raise MetadataError(f"Invalid result: {result}. Must be one of: {field_def['values']}")
        
        # Update the execution result and date
        return self.update_test_case_metadata(
            test_case_id,
            {
                "LAST_EXECUTION_RESULT": result,
                "LAST_EXECUTION_DATE": datetime.now().isoformat()
            },
            executed_by
        )

    def add_tags_to_test_case(self, test_case_id: str, tags: List[str], 
                            modified_by: str = None) -> Dict[str, Any]:
        """
        Add tags to a test case.
        
        Args:
            test_case_id: The test case ID.
            tags: Tags to add.
            modified_by: Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
        """
        # Get current tags
        current_tags = []
        if test_case_id in self._tag_associations:
            current_tags = self._tag_associations[test_case_id]
        
        # Add new tags (avoid duplicates)
        updated_tags = list(set(current_tags + tags))
        
        # Update tags
        return self.update_test_case_metadata(
            test_case_id,
            {"TAGS": updated_tags},
            modified_by
        )

    def remove_tags_from_test_case(self, test_case_id: str, tags: List[str], 
                                 modified_by: str = None) -> Dict[str, Any]:
        """
        Remove tags from a test case.
        
        Args:
            test_case_id: The test case ID.
            tags: Tags to remove.
            modified_by: Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
        """
        # Get current tags
        current_tags = []
        if test_case_id in self._tag_associations:
            current_tags = self._tag_associations[test_case_id]
        
        # Remove specified tags
        updated_tags = [tag for tag in current_tags if tag not in tags]
        
        # Update tags
        return self.update_test_case_metadata(
            test_case_id,
            {"TAGS": updated_tags},
            modified_by
        )

    # ====== Export and Import Methods ======
    
    def export_metadata_to_json(self, output_path: str, test_case_ids: List[str] = None) -> int:
        """
        Export metadata to a JSON file.
        
        Args:
            output_path: Path to save the JSON file.
            test_case_ids: Specific test cases to export.
            
        Returns:
            int: Number of test cases exported.
        """
        try:
            # Get metadata
            if test_case_ids:
                metadata_list = [self.get_test_case_metadata(tc_id) for tc_id in test_case_ids]
                metadata_list = [m for m in metadata_list if m]  # Filter out None values
            else:
                # Get all test cases
                metadata_list = [self.get_test_case_metadata(tc_id) for tc_id in self._test_cases.keys()]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(metadata_list, f, indent=2, default=self._json_serializer)
            
            self.logger.info(f"Exported {len(metadata_list)} test case metadata records to {output_path}")
            return len(metadata_list)
            
        except Exception as e:
            self.logger.error(f"Failed to export metadata: {str(e)}")
            return 0

    def import_metadata_from_json(self, input_path: str, overwrite: bool = False) -> int:
        """
        Import metadata from a JSON file.
        
        Args:
            input_path: Path to the JSON file.
            overwrite: Whether to overwrite existing metadata.
            
        Returns:
            int: Number of test cases imported.
        """
        try:
            # Read the file
            with open(input_path, 'r') as f:
                metadata_list = json.load(f)
            
            # Validate format
            if not isinstance(metadata_list, list):
                raise MetadataError("Invalid JSON format. Expected a list of metadata objects.")
            
            # Import each test case
            imported_count = 0
            
            for metadata in metadata_list:
                if not isinstance(metadata, dict) or "TEST_CASE_ID" not in metadata:
                    self.logger.warning("Skipping invalid metadata record (missing TEST_CASE_ID)")
                    continue
                
                test_case_id = metadata["TEST_CASE_ID"]
                existing = self.get_test_case_metadata(test_case_id)
                
                if existing and not overwrite:
                    self.logger.info(f"Skipping existing test case {test_case_id} (overwrite=False)")
                    continue
                
                if existing:
                    # Update existing
                    self.update_test_case_metadata(test_case_id, metadata)
                else:
                    # Create new
                    self.create_test_case_metadata(metadata)
                
                imported_count += 1
            
            # Save to disk
            self._save_mock_data()
            
            self.logger.info(f"Imported {imported_count} test case metadata records from {input_path}")
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Failed to import metadata: {str(e)}")
            return 0

    # ====== Mock Implementation of Database Methods ======
    
    def check_database_connection(self) -> bool:
        """
        Check if the database connection is working (mock version).
        
        Returns:
            bool: Always True for mock implementation.
        """
        return True

    def _init_database(self):
        """Mock implementation of database initialization."""
        self.logger.info("Mock database initialization - no action needed")
        return True

    def _get_db_connection(self):
        """Mock implementation of database connection method."""
        self.logger.debug("Mock database connection requested")
        return None

    def _return_db_connection(self, conn):
        """Mock implementation of database connection return method."""
        self.logger.debug("Mock database connection returned")
        return

    def _execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, 
                     fetch_all: bool = False, as_dict: bool = False) -> Any:
        """Mock implementation of database query execution."""
        self.logger.debug(f"Mock query execution: {query}")
        return None

    def _execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """Mock implementation of database transaction execution."""
        self.logger.debug(f"Mock transaction execution with {len(queries)} queries")
        return True

    def vacuum_database(self):
        """Mock implementation of database vacuum operation."""
        self.logger.info("Mock database vacuum - no action needed")
        return True

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the mock database.
        
        Returns:
            Dict[str, Any]: Mock database statistics.
        """
        return {
            "test_cases_count": len(self._test_cases),
            "files_count": len(self._files),
            "tags_count": len(self._tags),
            "history_count": len(self._history),
            "database_size": "Mock database",
            "table_sizes": []
        }

    def _close_connection_pool(self):
        """Mock implementation of database connection pool closure."""
        self.logger.info("Mock connection pool closed")
        return

    def __del__(self):
        """Ensure mock data is saved when the object is deleted."""
        self._save_mock_data()        