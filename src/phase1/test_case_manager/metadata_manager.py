#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Metadata Manager Module for the Watsonx IPG Testing platform.

This module manages test case metadata including ownership, status, priority,
and other attributes. It ensures consistency in metadata across test cases and
provides functionality to search and filter test cases based on metadata.
"""

import os
import pandas as pd
import logging
import json
from typing import Dict, List, Any, Tuple, Optional, Union, Set
from datetime import datetime
import re
import uuid
import sqlite3

# Import from src.common
from src.common.utils.file_utils import read_file, write_file
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    MetadataError,
    DatabaseError,
    SchemaValidationError
)

# Import from phase1
from src.phase1.system_configuration.rule_engine import get_assignment_rules

# Setup logger
logger = logging.getLogger(__name__)

class MetadataManager:
    """
    Class to manage test case metadata, enforce schema rules, and provide search functionality.
    """
    
    # Default metadata schema
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
            }
        }
    }
    
    def __init__(self, db_path: str = None, schema_path: str = None):
        """
        Initialize the MetadataManager with a database and schema.
        
        Args:
            db_path (str, optional): Path to the SQLite database for metadata storage.
                If None, uses a default path.
            schema_path (str, optional): Path to the metadata schema JSON file.
                If None, uses the default schema.
        """
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), "../../../storage/metadata/test_case_metadata.db"
        )
        self.schema_path = schema_path
        self.logger = logging.getLogger(__name__)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Load schema
        if schema_path and os.path.exists(schema_path):
            self._load_schema_from_file()
        else:
            self.schema = self.DEFAULT_SCHEMA
            self.logger.info("Using default metadata schema")
        
        # Initialize database
        self._init_database()
        
        self.logger.info(f"MetadataManager initialized with database at: {self.db_path}")
    
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
    
    def _init_database(self):
        """
        Initialize the SQLite database for metadata storage.
        
        Creates the necessary tables if they don't exist.
        
        Raises:
            DatabaseError: If database initialization fails.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create metadata table with dynamic columns based on schema
            columns = ["id INTEGER PRIMARY KEY"]
            
            for field_name, field_def in self.schema["metadata_fields"].items():
                field_type = field_def["type"]
                
                # Map schema types to SQLite types
                if field_type == "string":
                    sql_type = "TEXT"
                elif field_type == "enum":
                    sql_type = "TEXT"
                elif field_type == "date":
                    sql_type = "TEXT"  # Store dates as ISO format strings
                elif field_type == "number" or field_type == "integer":
                    sql_type = "INTEGER"
                elif field_type == "float" or field_type == "decimal":
                    sql_type = "REAL"
                elif field_type == "boolean":
                    sql_type = "INTEGER"  # 0 or 1
                elif field_type == "array":
                    sql_type = "TEXT"  # Store as JSON
                else:
                    sql_type = "TEXT"  # Default
                
                # Add column with NOT NULL if required
                not_null = "NOT NULL" if field_def.get("required", False) else ""
                columns.append(f"{field_name} {sql_type} {not_null}")
            
            # Create the main metadata table
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS test_case_metadata (
                {', '.join(columns)}
            )
            """
            cursor.execute(create_table_sql)
            
            # Create index on TEST_CASE_ID for fast lookups
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_case_id ON test_case_metadata (TEST_CASE_ID)")
            
            # Create a history table to track metadata changes
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_history (
                id INTEGER PRIMARY KEY,
                test_case_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (test_case_id) REFERENCES test_case_metadata (TEST_CASE_ID)
            )
            """)
            
            # Create index on test_case_id in history table
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_test_case_id ON metadata_history (test_case_id)")
            
            # Create a tags table for many-to-many relationship
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_case_tags (
                test_case_id TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (test_case_id, tag_id),
                FOREIGN KEY (test_case_id) REFERENCES test_case_metadata (TEST_CASE_ID),
                FOREIGN KEY (tag_id) REFERENCES tags (id)
            )
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.debug("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise DatabaseError(f"Failed to initialize metadata database: {str(e)}")
        
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate metadata against the schema.
        
        Args:
            metadata (Dict[str, Any]): The metadata to validate.
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check required fields
        for field_name, field_def in self.schema["metadata_fields"].items():
            if field_def.get("required", False) and field_name not in metadata:
                errors.append(f"Required field '{field_name}' is missing")
        
        # Validate field types and values
        for field_name, value in metadata.items():
            if field_name in self.schema["metadata_fields"]:
                field_def = self.schema["metadata_fields"][field_name]
                field_type = field_def["type"]
                
                # Skip validation for None values in non-required fields
                if value is None and not field_def.get("required", False):
                    continue
                
                # Validate based on type
                if field_type == "enum" and "values" in field_def:
                    if value not in field_def["values"]:
                        errors.append(f"Value '{value}' for '{field_name}' must be one of: {field_def['values']}")
                
                elif field_type == "date":
                    # Basic date format validation
                    if not isinstance(value, (str, datetime)):
                        errors.append(f"Value for '{field_name}' must be a date string or datetime object")
                    elif isinstance(value, str):
                        try:
                            datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            errors.append(f"Value '{value}' for '{field_name}' is not a valid date format")
                
                elif field_type == "number" or field_type == "integer":
                    if not isinstance(value, (int, float)) or (field_type == "integer" and not isinstance(value, int)):
                        errors.append(f"Value for '{field_name}' must be a {'integer' if field_type == 'integer' else 'number'}")
                
                elif field_type == "boolean":
                    if not isinstance(value, bool):
                        errors.append(f"Value for '{field_name}' must be a boolean")
                
                elif field_type == "array":
                    if not isinstance(value, (list, tuple, set)):
                        errors.append(f"Value for '{field_name}' must be an array")
        
        return len(errors) == 0, errors
    
    def _serialize_metadata_value(self, value, field_type: str) -> Any:
        """
        Serialize a metadata value for storage in the database.
        
        Args:
            value: The value to serialize.
            field_type (str): The type of the field.
            
        Returns:
            Any: The serialized value.
        """
        if value is None:
            return None
        
        if field_type == "date":
            if isinstance(value, datetime):
                return value.isoformat()
            return value
        
        elif field_type == "array":
            if isinstance(value, (list, tuple, set)):
                return json.dumps(list(value))
            return json.dumps([])
        
        elif field_type == "boolean":
            return 1 if value else 0
        
        return value
    
    def _deserialize_metadata_value(self, value, field_type: str) -> Any:
        """
        Deserialize a metadata value from the database.
        
        Args:
            value: The value to deserialize.
            field_type (str): The type of the field.
            
        Returns:
            Any: The deserialized value.
        """
        if value is None:
            return None
        
        if field_type == "date":
            return value  # Keep as ISO format string
        
        elif field_type == "array":
            try:
                return json.loads(value)
            except:
                return []
        
        elif field_type == "boolean":
            return bool(value)
        
        elif field_type == "integer":
            return int(value) if value is not None else None
        
        elif field_type == "number" or field_type == "float" or field_type == "decimal":
            return float(value) if value is not None else None
        
        return value
    
    def _apply_defaults(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values from schema for missing fields.
        
        Args:
            metadata (Dict[str, Any]): The metadata to update.
            
        Returns:
            Dict[str, Any]: Metadata with defaults applied.
        """
        updated = metadata.copy()
        
        for field_name, field_def in self.schema["metadata_fields"].items():
            if field_name not in updated and "default" in field_def:
                updated[field_name] = field_def["default"]
        
        return updated
    
    def create_test_case_metadata(self, test_case_data: Dict[str, Any], 
                                created_by: str = None) -> str:
        """
        Create metadata for a new test case.
        
        Args:
            test_case_data (Dict[str, Any]): Basic test case data, including at least:
                                         - TEST_CASE_ID: Unique identifier
                                         - Additional test case details
            created_by (str, optional): Person creating the test case.
            
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
            
            # Extract owner from test case data or assign based on rules
            owner = test_case_data.get("OWNER") or test_case_data.get("TEST USER ID/ROLE")
            
            if not owner:
                # Get owner from assignment rules
                try:
                    module = test_case_data.get("MODULE") or test_case_data.get("SUBJECT", "Unknown")
                    assignment_rules = get_assignment_rules()
                    owner = assignment_rules.get_owner_for_test_case(module)
                except Exception as e:
                    self.logger.warning(f"Failed to get owner from rules: {str(e)}")
                    owner = "Unassigned"
            
            # Build metadata
            now = datetime.now().isoformat()
            
            metadata = {
                "TEST_CASE_ID": test_case_id,
                "OWNER": owner,
                "STATUS": "Draft",
                "PRIORITY": test_case_data.get("PRIORITY", "Medium"),
                "AUTOMATION_STATUS": "Manual",  # Default to manual
                "CREATED_DATE": now,
                "MODIFIED_DATE": now,
                "CREATED_BY": created_by or "System",
                "MODIFIED_BY": created_by or "System",
                "MODULE": test_case_data.get("MODULE") or test_case_data.get("SUBJECT", "Unknown"),
                "TEST_TYPE": test_case_data.get("TEST_TYPE") or test_case_data.get("TYPE", "Functional"),
                "LAST_EXECUTION_RESULT": "Not Executed"
            }
            
            # Extract tags if present
            if "TAGS" in test_case_data:
                metadata["TAGS"] = test_case_data["TAGS"]
            
            # Apply default values from schema
            metadata = self._apply_defaults(metadata)
            
            # Validate metadata
            is_valid, errors = self._validate_metadata(metadata)
            
            if not is_valid:
                error_msg = f"Invalid metadata: {'; '.join(errors)}"
                self.logger.error(error_msg)
                raise MetadataError(error_msg)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prepare fields and values
            fields = []
            placeholders = []
            values = []
            
            for field_name, value in metadata.items():
                if field_name in self.schema["metadata_fields"]:
                    field_type = self.schema["metadata_fields"][field_name]["type"]
                    serialized_value = self._serialize_metadata_value(value, field_type)
                    
                    fields.append(field_name)
                    placeholders.append("?")
                    values.append(serialized_value)
            
            # Insert metadata
            insert_sql = f"""
            INSERT INTO test_case_metadata ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(insert_sql, values)
            
            # Handle tags if present
            if "TAGS" in metadata and metadata["TAGS"]:
                tags = metadata["TAGS"]
                if isinstance(tags, str):
                    # If it's a string, split by comma
                    tags = [tag.strip() for tag in tags.split(',')]
                
                for tag in tags:
                    # Insert tag if it doesn't exist
                    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    
                    # Get tag id
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_id = cursor.fetchone()[0]
                    
                    # Associate tag with test case
                    cursor.execute(
                        "INSERT INTO test_case_tags (test_case_id, tag_id) VALUES (?, ?)",
                        (test_case_id, tag_id)
                    )
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created metadata for test case {test_case_id}")
            return test_case_id
            
        except Exception as e:
            self.logger.error(f"Failed to create metadata: {str(e)}")
            raise MetadataError(f"Failed to create metadata: {str(e)}")
    
    def update_test_case_metadata(self, test_case_id: str, updates: Dict[str, Any], 
                             modified_by: str = None) -> Dict[str, Any]:
        """
        Update metadata for an existing test case.
        
        Args:
            test_case_id (str): The test case ID.
            updates (Dict[str, Any]): Metadata fields to update.
            modified_by (str, optional): Person making the updates.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If metadata update fails.
        """
        try:
            # Get current metadata
            current = self.get_test_case_metadata(test_case_id)
            
            if not current:
                raise MetadataError(f"Test case {test_case_id} not found")
            
            # Apply updates
            updated = current.copy()
            updated.update(updates)
            
            # Always update MODIFIED_DATE and MODIFIED_BY
            updated["MODIFIED_DATE"] = datetime.now().isoformat()
            if modified_by:
                updated["MODIFIED_BY"] = modified_by
            
            # Validate updated metadata
            is_valid, errors = self._validate_metadata(updated)
            
            if not is_valid:
                error_msg = f"Invalid metadata updates: {'; '.join(errors)}"
                self.logger.error(error_msg)
                raise MetadataError(error_msg)
            
            # Store updates in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prepare the UPDATE statement
            set_clauses = []
            values = []
            
            for field_name, value in updates.items():
                if field_name in self.schema["metadata_fields"]:
                    field_type = self.schema["metadata_fields"][field_name]["type"]
                    serialized_value = self._serialize_metadata_value(value, field_type)
                    
                    set_clauses.append(f"{field_name} = ?")
                    values.append(serialized_value)
            
            # Add modified date and modified by
            set_clauses.append("MODIFIED_DATE = ?")
            values.append(updated["MODIFIED_DATE"])
            
            if modified_by:
                set_clauses.append("MODIFIED_BY = ?")
                values.append(modified_by)
            
            # Add test case ID for WHERE clause
            values.append(test_case_id)
            
            # Execute update
            update_sql = f"""
            UPDATE test_case_metadata
            SET {', '.join(set_clauses)}
            WHERE TEST_CASE_ID = ?
            """
            
            cursor.execute(update_sql, values)
            
            # Record history
            for field_name, new_value in updates.items():
                if field_name in self.schema["metadata_fields"]:
                    old_value = current.get(field_name)
                    
                    # Skip if no change
                    if old_value == new_value:
                        continue
                    
                    # Serialize for storage
                    field_type = self.schema["metadata_fields"][field_name]["type"]
                    old_serialized = self._serialize_metadata_value(old_value, field_type)
                    new_serialized = self._serialize_metadata_value(new_value, field_type)
                    
                    # Convert to string for history
                    old_str = str(old_serialized) if old_serialized is not None else None
                    new_str = str(new_serialized) if new_serialized is not None else None
                    
                    # Record in history
                    cursor.execute("""
                    INSERT INTO metadata_history
                    (test_case_id, field_name, old_value, new_value, changed_by, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        test_case_id, field_name, old_str, new_str,
                        modified_by or "System", datetime.now().isoformat()
                    ))
            
            # Handle tags update if present
            if "TAGS" in updates:
                # Remove existing tag associations
                cursor.execute("DELETE FROM test_case_tags WHERE test_case_id = ?", (test_case_id,))
                
                # Add new tags
                tags = updates["TAGS"]
                if isinstance(tags, str):
                    # If it's a string, split by comma
                    tags = [tag.strip() for tag in tags.split(',')]
                elif tags is None:
                    tags = []
                
                for tag in tags:
                    # Insert tag if it doesn't exist
                    cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    
                    # Get tag id
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                    tag_id = cursor.fetchone()[0]
                    
                    # Associate tag with test case
                    cursor.execute(
                        "INSERT INTO test_case_tags (test_case_id, tag_id) VALUES (?, ?)",
                        (test_case_id, tag_id)
                    )
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated metadata for test case {test_case_id}")
            
            # Return the updated metadata
            return self.get_test_case_metadata(test_case_id)
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata: {str(e)}")
            raise MetadataError(f"Failed to update metadata: {str(e)}")    
        

    def get_test_case_metadata(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get metadata for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: The metadata, or None if not found.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            # Get metadata
            cursor.execute("SELECT * FROM test_case_metadata WHERE TEST_CASE_ID = ?", (test_case_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Convert to dict
            metadata = dict(row)
            
            # Remove the 'id' field (database primary key)
            if "id" in metadata:
                del metadata["id"]
            
            # Deserialize values
            for field_name, value in metadata.items():
                if field_name in self.schema["metadata_fields"]:
                    field_type = self.schema["metadata_fields"][field_name]["type"]
                    metadata[field_name] = self._deserialize_metadata_value(value, field_type)
            
            # Get tags
            cursor.execute("""
            SELECT t.name
            FROM tags t
            JOIN test_case_tags tct ON t.id = tct.tag_id
            WHERE tct.test_case_id = ?
            """, (test_case_id,))
            
            tags = [row[0] for row in cursor.fetchall()]
            metadata["TAGS"] = tags
            
            conn.close()
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata: {str(e)}")
            return None
    
    def delete_test_case_metadata(self, test_case_id: str) -> bool:
        """
        Delete metadata for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete tag associations
            cursor.execute("DELETE FROM test_case_tags WHERE test_case_id = ?", (test_case_id,))
            
            # Delete history
            cursor.execute("DELETE FROM metadata_history WHERE test_case_id = ?", (test_case_id,))
            
            # Delete metadata
            cursor.execute("DELETE FROM test_case_metadata WHERE TEST_CASE_ID = ?", (test_case_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Deleted metadata for test case {test_case_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete metadata: {str(e)}")
            return False
    
    def search_test_cases(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for test cases based on metadata criteria.
        
        Args:
            criteria (Dict[str, Any]): Search criteria, where:
                - Keys are field names
                - Values can be direct values or dicts with operators: 
                  {"op": "contains", "value": "partial"}, 
                  {"op": "in", "value": ["list", "of", "values"]},
                  {"op": ">", "value": 10}, etc.
            
        Returns:
            List[Dict[str, Any]]: List of matching test case metadata.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build the WHERE clause
            where_clauses = []
            params = []
            
            for field, criteria_value in criteria.items():
                if field == "TAGS":
                    # Special handling for tags
                    tag_values = criteria_value
                    if isinstance(criteria_value, dict) and "value" in criteria_value:
                        tag_values = criteria_value["value"]
                    
                    if not isinstance(tag_values, (list, tuple)):
                        tag_values = [tag_values]
                    
                    tag_placeholders = ", ".join(["?"] * len(tag_values))
                    
                    # Subquery to get test_case_ids that have all the specified tags
                    subquery = f"""
                    TEST_CASE_ID IN (
                        SELECT tct.test_case_id
                        FROM test_case_tags tct
                        JOIN tags t ON tct.tag_id = t.id
                        WHERE t.name IN ({tag_placeholders})
                        GROUP BY tct.test_case_id
                        HAVING COUNT(DISTINCT t.name) = ?
                    )
                    """
                    
                    where_clauses.append(subquery)
                    params.extend(tag_values)
                    params.append(len(tag_values))  # Ensure all tags are matched
                    
                elif field in self.schema["metadata_fields"]:
                    field_type = self.schema["metadata_fields"][field]["type"]
                    
                    if isinstance(criteria_value, dict) and "op" in criteria_value:
                        # Complex criteria with operator
                        op = criteria_value["op"].lower()
                        value = criteria_value["value"]
                        
                        if op == "equals" or op == "=":
                            where_clauses.append(f"{field} = ?")
                            params.append(self._serialize_metadata_value(value, field_type))
                            
                        elif op == "not equals" or op == "!=":
                            where_clauses.append(f"{field} != ? OR {field} IS NULL")
                            params.append(self._serialize_metadata_value(value, field_type))
                            
                        elif op == "contains" or op == "like":
                            where_clauses.append(f"{field} LIKE ?")
                            params.append(f"%{value}%")
                            
                        elif op == "in":
                            placeholders = ", ".join(["?"] * len(value))
                            where_clauses.append(f"{field} IN ({placeholders})")
                            params.extend([self._serialize_metadata_value(v, field_type) for v in value])
                            
                        elif op == "not in":
                            placeholders = ", ".join(["?"] * len(value))
                            where_clauses.append(f"{field} NOT IN ({placeholders}) OR {field} IS NULL")
                            params.extend([self._serialize_metadata_value(v, field_type) for v in value])
                            
                        elif op in [">", "<", ">=", "<="]:
                            where_clauses.append(f"{field} {op} ?")
                            params.append(self._serialize_metadata_value(value, field_type))
                            
                    else:
                        # Simple equality match
                        where_clauses.append(f"{field} = ?")
                        params.append(self._serialize_metadata_value(criteria_value, field_type))
            
            # Build the final query
            query = "SELECT * FROM test_case_metadata"
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Execute the query
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Process results
            results = []
            
            for row in rows:
                # Convert row to dict
                metadata = dict(row)
                
                # Remove the 'id' field
                if "id" in metadata:
                    del metadata["id"]
                
                # Deserialize values
                for field_name, value in metadata.items():
                    if field_name in self.schema["metadata_fields"]:
                        field_type = self.schema["metadata_fields"][field_name]["type"]
                        metadata[field_name] = self._deserialize_metadata_value(value, field_type)
                
                # Get tags
                cursor.execute("""
                SELECT t.name
                FROM tags t
                JOIN test_case_tags tct ON t.id = tct.tag_id
                WHERE tct.test_case_id = ?
                """, (metadata["TEST_CASE_ID"],))
                
                tags = [row[0] for row in cursor.fetchall()]
                metadata["TAGS"] = tags
                
                results.append(metadata)
            
            conn.close()
            return results
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return []
    
    def get_metadata_history(self, test_case_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of metadata changes for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            List[Dict[str, Any]]: List of history entries, ordered by time.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT * FROM metadata_history
            WHERE test_case_id = ?
            ORDER BY changed_at DESC
            """, (test_case_id,))
            
            history = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata history: {str(e)}")
            return []
    
    def get_test_cases_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        """
        Get all test cases owned by a specific person.
        
        Args:
            owner (str): The owner's name or ID.
            
        Returns:
            List[Dict[str, Any]]: List of test case metadata.
        """
        return self.search_test_cases({"OWNER": owner})
    
    def get_test_cases_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get all test cases with a specific status.
        
        Args:
            status (str): The status value.
            
        Returns:
            List[Dict[str, Any]]: List of test case metadata.
        """
        return self.search_test_cases({"STATUS": status})
    
    def get_test_cases_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """
        Get all test cases that have all the specified tags.
        
        Args:
            tags (List[str]): List of tags to match.
            
        Returns:
            List[Dict[str, Any]]: List of test case metadata.
        """
        return self.search_test_cases({"TAGS": tags})   


    def update_test_case_status(self, test_case_id: str, new_status: str, 
                           modified_by: str = None) -> Dict[str, Any]:
        """
        Update the status of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            new_status (str): The new status.
            modified_by (str, optional): Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If the update fails.
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
            test_case_id (str): The test case ID.
            new_owner (str): The new owner.
            modified_by (str, optional): Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If the update fails.
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
            test_case_id (str): The test case ID.
            new_status (str): The new automation status.
            modified_by (str, optional): Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If the update fails.
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
            test_case_id (str): The test case ID.
            result (str): The execution result (Pass, Fail, Blocked, etc.).
            executed_by (str, optional): Person who executed the test.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If the update fails.
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
            test_case_id (str): The test case ID.
            tags (List[str]): Tags to add.
            modified_by (str, optional): Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If the update fails.
        """
        # Get current tags
        metadata = self.get_test_case_metadata(test_case_id)
        
        if not metadata:
            raise MetadataError(f"Test case {test_case_id} not found")
        
        current_tags = metadata.get("TAGS", [])
        
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
            test_case_id (str): The test case ID.
            tags (List[str]): Tags to remove.
            modified_by (str, optional): Person making the update.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If the update fails.
        """
        # Get current tags
        metadata = self.get_test_case_metadata(test_case_id)
        
        if not metadata:
            raise MetadataError(f"Test case {test_case_id} not found")
        
        current_tags = set(metadata.get("TAGS", []))
        tags_to_remove = set(tags)
        
        # Remove specified tags
        updated_tags = list(current_tags - tags_to_remove)
        
        # Update tags
        return self.update_test_case_metadata(
            test_case_id,
            {"TAGS": updated_tags},
            modified_by
        )
    
    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags used across all test cases.
        
        Returns:
            List[str]: List of unique tags.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM tags ORDER BY name")
            tags = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return tags
            
        except Exception as e:
            self.logger.error(f"Failed to get all tags: {str(e)}")
            return []
    
    def export_metadata_to_json(self, output_path: str, test_case_ids: List[str] = None) -> int:
        """
        Export metadata to a JSON file.
        
        Args:
            output_path (str): Path to save the JSON file.
            test_case_ids (List[str], optional): Specific test cases to export.
                If None, exports all test cases.
            
        Returns:
            int: Number of test cases exported.
            
        Raises:
            MetadataError: If the export fails.
        """
        try:
            # Get metadata
            if test_case_ids:
                metadata_list = [self.get_test_case_metadata(tc_id) for tc_id in test_case_ids]
                metadata_list = [m for m in metadata_list if m]  # Filter out None values
            else:
                # Get all test cases
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT TEST_CASE_ID FROM test_case_metadata")
                test_case_ids = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                metadata_list = [self.get_test_case_metadata(tc_id) for tc_id in test_case_ids]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(metadata_list, f, indent=2)
            
            self.logger.info(f"Exported {len(metadata_list)} test case metadata records to {output_path}")
            return len(metadata_list)
            
        except Exception as e:
            self.logger.error(f"Failed to export metadata: {str(e)}")
            raise MetadataError(f"Failed to export metadata: {str(e)}")
    
    def import_metadata_from_json(self, input_path: str, overwrite: bool = False) -> int:
        """
        Import metadata from a JSON file.
        
        Args:
            input_path (str): Path to the JSON file.
            overwrite (bool, optional): Whether to overwrite existing metadata.
            
        Returns:
            int: Number of test cases imported.
            
        Raises:
            MetadataError: If the import fails.
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
            
            self.logger.info(f"Imported {imported_count} test case metadata records from {input_path}")
            return imported_count
            
        except Exception as e:
            self.logger.error(f"Failed to import metadata: {str(e)}")
            raise MetadataError(f"Failed to import metadata: {str(e)}")


# If running as a script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage test case metadata")
    parser.add_argument("--action", choices=["create", "update", "get", "delete", "search", 
                                        "export", "import"], required=True,
                      help="Action to perform")
    parser.add_argument("--test_case_id", help="Test case ID")
    parser.add_argument("--test_case_file", help="Path to test case file for metadata extraction")
    parser.add_argument("--owner", help="Owner for test case")
    parser.add_argument("--status", help="Status for test case")
    parser.add_argument("--field", help="Field name for update action")
    parser.add_argument("--value", help="Field value for update action")
    parser.add_argument("--json_file", help="Path to JSON file for export/import")
    parser.add_argument("--schema", help="Path to metadata schema file")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create metadata manager
    metadata_manager = MetadataManager(schema_path=args.schema)
    
    # Execute requested action
    if args.action == "create" and args.test_case_file:
        # Extract metadata from test case file
        try:
            # Load the test case file
            test_case_df = pd.read_excel(args.test_case_file)
            
            # Extract basic info
            test_case_data = {}
            
            if len(test_case_df) > 0:
                first_row = test_case_df.iloc[0]
                
                # Extract fields if they exist
                for source_field, target_field in [
                    ("TEST CASE NUMBER", "TEST_CASE_ID"),
                    ("TEST CASE", "TEST_CASE"),
                    ("SUBJECT", "MODULE"),
                    ("TEST USER ID/ROLE", "OWNER"),
                    ("TYPE", "TEST_TYPE")
                ]:
                    if source_field in test_case_df.columns:
                        test_case_data[target_field] = first_row.get(source_field)
            
            # Create metadata
            test_case_id = metadata_manager.create_test_case_metadata(test_case_data, created_by=args.owner)
            print(f"Created metadata for test case {test_case_id}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    elif args.action == "update" and args.test_case_id and args.field and args.value:
        try:
            updates = {args.field: args.value}
            metadata = metadata_manager.update_test_case_metadata(args.test_case_id, updates, args.owner)
            print(f"Updated metadata for test case {args.test_case_id}")
            print(f"Field {args.field} set to: {metadata.get(args.field)}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    elif args.action == "get" and args.test_case_id:
        metadata = metadata_manager.get_test_case_metadata(args.test_case_id)
        if metadata:
            print(f"\nMetadata for test case {args.test_case_id}:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        else:
            print(f"No metadata found for test case {args.test_case_id}")
    
    elif args.action == "delete" and args.test_case_id:
        success = metadata_manager.delete_test_case_metadata(args.test_case_id)
        if success:
            print(f"Deleted metadata for test case {args.test_case_id}")
        else:
            print(f"Failed to delete metadata for test case {args.test_case_id}")
    
    elif args.action == "search":
        criteria = {}
        
        if args.owner:
            criteria["OWNER"] = args.owner
        
        if args.status:
            criteria["STATUS"] = args.status
        
        if not criteria:
            print("Error: No search criteria provided")
        else:
            results = metadata_manager.search_test_cases(criteria)
            print(f"\nFound {len(results)} matching test cases:")
            
            for idx, metadata in enumerate(results, 1):
                print(f"\n{idx}. {metadata.get('TEST_CASE_ID')}: {metadata.get('TEST_CASE', 'Unnamed')}")
                print(f"   Owner: {metadata.get('OWNER', 'Unassigned')}")
                print(f"   Status: {metadata.get('STATUS', 'Unknown')}")
                print(f"   Type: {metadata.get('TEST_TYPE', 'Unknown')}")
    
    elif args.action == "export" and args.json_file:
        try:
            count = metadata_manager.export_metadata_to_json(args.json_file)
            print(f"Exported {count} test case metadata records to {args.json_file}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    elif args.action == "import" and args.json_file:
        try:
            count = metadata_manager.import_metadata_from_json(args.json_file)
            print(f"Imported {count} test case metadata records from {args.json_file}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    else:
        print("Error: Invalid combination of action and parameters") 