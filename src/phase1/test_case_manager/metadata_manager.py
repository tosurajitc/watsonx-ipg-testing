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
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json
import dotenv
from io import BytesIO

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

# Load environment variables
dotenv.load_dotenv()

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
    
    def __init__(self, schema_path: str = None, min_conn: int = 1, max_conn: int = 10):
        """
        Initialize the MetadataManager with PostgreSQL connection pool and schema.
        
        Args:
            schema_path (str, optional): Path to the metadata schema JSON file.
                If None, uses the default schema.
            min_conn (int, optional): Minimum number of connections in the pool.
            max_conn (int, optional): Maximum number of connections in the pool.
        """
        self.schema_path = schema_path
        self.logger = logging.getLogger(__name__)
        
        # Load database configuration from environment variables
        self.db_config = {
            'host': os.getenv('DB_HOST', 'https://tldjlxdotaarczsdivav.supabase.co').replace('https://', ''),
            'port': os.getenv('DB_PORT', '5432'),
            'dbname': os.getenv('DB_NAME', 'watsonx_ipg_testing'),
            'user': os.getenv('DB_USER', 'tosurajitc'),
            'password': os.getenv('DB_PASSWORD', 'IpgTesting2025#'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
        
        # Alternative: use the DATABASE_URL if available
        self.db_url = os.getenv('DATABASE_URL')
        
        # Load schema
        if schema_path and os.path.exists(schema_path):
            self._load_schema_from_file()
        else:
            self.schema = self.DEFAULT_SCHEMA
            self.logger.info("Using default metadata schema")
        
        # Initialize connection pool
        try:
            if self.db_url:
                self.connection_pool = pool.ThreadedConnectionPool(
                    min_conn, max_conn, self.db_url
                )
                self.logger.info(f"Initialized connection pool using DATABASE_URL")
            else:
                self.connection_pool = pool.ThreadedConnectionPool(
                    min_conn, max_conn,
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    dbname=self.db_config['dbname'],
                    user=self.db_config['user'],
                    password=self.db_config['password'],
                    sslmode=self.db_config['sslmode']
                )
                self.logger.info(f"Initialized connection pool to PostgreSQL database: {self.db_config['dbname']}")
            
            # Initialize the database tables
            self._init_database()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL connection pool: {str(e)}")
            raise DatabaseError(f"Failed to connect to PostgreSQL database: {str(e)}")
    
    def _get_db_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            Connection: PostgreSQL connection from the pool
            
        Raises:
            DatabaseError: If unable to get a connection
        """
        try:
            conn = self.connection_pool.getconn()
            return conn
        except Exception as e:
            self.logger.error(f"Failed to get connection from pool: {str(e)}")
            raise DatabaseError(f"Failed to get database connection: {str(e)}")
    
    def _return_db_connection(self, conn):
        """
        Return a connection to the pool.
        
        Args:
            conn: The connection to return
        """
        try:
            self.connection_pool.putconn(conn)
        except Exception as e:
            self.logger.error(f"Failed to return connection to pool: {str(e)}")
            # Don't raise here, just log the error



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
        Initialize the PostgreSQL database for metadata storage.
        
        Connects to the existing 'test_cases' table instead of creating multiple tables.
        
        Raises:
            DatabaseError: If database initialization fails.
        """
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Check if the table exists
            cursor.execute("""
            SELECT * FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'test_cases';
            """)
            
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                # If table doesn't exist, create it (as a fallback)
                cursor.execute("""
                CREATE TABLE test_cases (
                    id SERIAL,
                    TEST_CASE_NUMBER VARCHAR(100) NOT NULL,
                    STEP_NO INTEGER NOT NULL,
                    SUBJECT VARCHAR(255),
                    TEST_CASE VARCHAR(255),
                    TEST_STEP_DESCRIPTION TEXT,
                    DATA TEXT,
                    REFERENCE_VALUES TEXT,
                    VALUES TEXT,
                    EXPECTED_RESULT TEXT,
                    TRANS_CODE VARCHAR(100),
                    TEST_USER_ID_ROLE VARCHAR(100),
                    STATUS VARCHAR(50),
                    TYPE VARCHAR(100),
                    CREATED_DATE TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    MODIFIED_DATE TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    
                    CONSTRAINT unique_test_case_step UNIQUE (TEST_CASE_NUMBER, STEP_NO)
                );
                
                CREATE INDEX idx_test_case_number ON test_cases (TEST_CASE_NUMBER);
                """)
                
                self.logger.debug("Created test_cases table in PostgreSQL database")
            
            conn.commit()
            self.logger.debug("PostgreSQL database connection verified successfully")
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise DatabaseError(f"Failed to initialize metadata database: {str(e)}")
        finally:
            if conn:
                self._return_db_connection(conn)

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
        Serialize a metadata value for storage in PostgreSQL.
        
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
                return value  # PostgreSQL can handle datetime objects directly
            elif isinstance(value, str):
                # Convert ISO string to datetime
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    # If conversion fails, return as is
                    return value
            return value
        
        elif field_type == "array":
            if isinstance(value, (list, tuple, set)):
                # PostgreSQL can handle lists directly for array types
                return list(value)
            elif isinstance(value, str):
                # If it's a JSON string, parse it
                try:
                    return json.loads(value)
                except:
                    # If parsing fails, treat as a single-item array
                    return [value]
            return []
        
        elif field_type == "boolean":
            return bool(value)
        
        elif field_type == "binary":
            # For binary data, ensure it's in bytes format
            if isinstance(value, bytes):
                return value
            elif isinstance(value, str):
                return value.encode('utf-8')
            return value
        
        return value

    def _deserialize_metadata_value(self, value, field_type: str) -> Any:
        """
        Deserialize a metadata value from PostgreSQL.
        
        Args:
            value: The value to deserialize.
            field_type (str): The type of the field.
            
        Returns:
            Any: The deserialized value.
        """
        if value is None:
            return None
        
        if field_type == "date":
            # PostgreSQL timestamps come back as datetime objects
            if isinstance(value, datetime):
                return value.isoformat()
            return value
        
        elif field_type == "array":
            # Handle PostgreSQL array types
            if isinstance(value, list):
                return value
            elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes, dict)):
                # Convert other iterable types to list
                return list(value)
            try:
                # Try to parse as JSON if it's a string
                return json.loads(value)
            except:
                return []
        
        elif field_type == "boolean":
            return bool(value)
        
        elif field_type == "integer":
            return int(value) if value is not None else None
        
        elif field_type == "number" or field_type == "float" or field_type == "decimal":
            return float(value) if value is not None else None
        
        elif field_type == "binary":
            # Binary data is already in bytes format from PostgreSQL
            return value
        
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

    def _execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, 
                    fetch_all: bool = False, as_dict: bool = False) -> Any:
        """
        Execute a database query with proper connection handling.
        
        Args:
            query (str): The SQL query to execute.
            params (tuple, optional): Query parameters.
            fetch_one (bool, optional): Whether to fetch one row.
            fetch_all (bool, optional): Whether to fetch all rows.
            as_dict (bool, optional): Whether to return results as dictionaries.
            
        Returns:
            Any: Query results if fetch_one or fetch_all is True, else None.
            
        Raises:
            DatabaseError: If query execution fails.
        """
        conn = None
        try:
            conn = self._get_db_connection()
            
            # Use RealDictCursor if dict results are requested
            cursor_factory = RealDictCursor if as_dict else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            
            # Execute query with parameters if provided
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch results if requested
            result = None
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                # For INSERT/UPDATE/DELETE, get affected row count
                result = cursor.rowcount
            
            conn.commit()
            return result
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Query execution failed: {str(e)}\nQuery: {query}\nParams: {params}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            if conn:
                self._return_db_connection(conn)

    def _execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """
        Execute multiple queries as a single transaction.
        
        Args:
            queries (List[Tuple[str, tuple]]): List of (query, params) tuples.
            
        Returns:
            bool: True if transaction succeeded, False otherwise.
            
        Raises:
            DatabaseError: If transaction execution fails.
        """
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Execute each query in the transaction
            for query, params in queries:
                cursor.execute(query, params)
            
            conn.commit()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Transaction execution failed: {str(e)}")
            raise DatabaseError(f"Transaction failed: {str(e)}")
        finally:
            if conn:
                self._return_db_connection(conn)

    def _store_test_case_file(self, test_case_id: str, file_name: str, file_content: bytes,
                            file_type: str = None) -> bool:
        """
        Store a test case file in the database.
        
        Args:
            test_case_id (str): The test case ID.
            file_name (str): Original file name.
            file_content (bytes): File content as bytes.
            file_type (str, optional): File type/extension. If None, extracted from file_name.
            
        Returns:
            bool: True if successful, False otherwise.
            
        Raises:
            DatabaseError: If file storage fails.
        """
        try:
            # Extract file type from file name if not provided
            if not file_type and file_name:
                file_type = os.path.splitext(file_name)[1].lstrip('.')
            
            # Ensure we have a file type
            file_type = file_type or 'unknown'
            
            # Insert or update file content
            query = """
            INSERT INTO test_case_files (test_case_id, file_name, file_type, content, uploaded_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (test_case_id) DO UPDATE
            SET file_name = EXCLUDED.file_name,
                file_type = EXCLUDED.file_type,
                content = EXCLUDED.content,
                uploaded_at = EXCLUDED.uploaded_at
            """
            
            params = (test_case_id, file_name, file_type, file_content, datetime.now())
            self._execute_query(query, params)
            
            self.logger.info(f"Stored file '{file_name}' for test case {test_case_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store test case file: {str(e)}")
            raise DatabaseError(f"Failed to store test case file: {str(e)}")

    def _retrieve_test_case_file(self, test_case_id: str) -> Tuple[str, str, bytes]:
        """
        Retrieve a test case file from the database.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Tuple[str, str, bytes]: (file_name, file_type, file_content)
            
        Raises:
            DatabaseError: If file retrieval fails.
        """
        try:
            query = """
            SELECT file_name, file_type, content
            FROM test_case_files
            WHERE test_case_id = %s
            """
            
            result = self._execute_query(query, (test_case_id,), fetch_one=True)
            
            if not result:
                self.logger.warning(f"No file found for test case {test_case_id}")
                return None, None, None
            
            file_name = result[0]
            file_type = result[1]
            file_content = result[2]
            
            return file_name, file_type, file_content
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve test case file: {str(e)}")
            raise DatabaseError(f"Failed to retrieve test case file: {str(e)}")
        

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
            now = datetime.now()

            metadata = {
                "TEST_CASE_NUMBER": test_case_id,
                "STEP_NO": 1,  # Starting with step 1
                "SUBJECT": test_case_data.get("SUBJECT", "Unknown"),
                "TEST_CASE": test_case_data.get("TEST_CASE", ""),
                "TEST_STEP_DESCRIPTION": "",  # Empty by default, will be filled later
                "DATA": "",  # Empty by default
                "REFERENCE_VALUES": "",  # Empty by default
                "VALUES": "",  # Empty by default
                "EXPECTED_RESULT": "",  # Empty by default
                "TRANS_CODE": "",  # Empty by default
                "TEST_USER_ID_ROLE": owner or test_case_data.get("TEST_USER_ID_ROLE", ""),
                "STATUS": "Draft",
                "TYPE": test_case_data.get("TYPE", "Functional"),
                "CREATED_DATE": now,
                "MODIFIED_DATE": now
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
            
            # Prepare fields and values
            fields = []
            placeholders = []
            values = []
            
            for field_name, value in metadata.items():
                if field_name in self.schema["metadata_fields"]:
                    field_type = self.schema["metadata_fields"][field_name]["type"]
                    serialized_value = self._serialize_metadata_value(value, field_type)
                    
                    fields.append(field_name)
                    placeholders.append(f"%s")
                    values.append(serialized_value)
            
            # Insert metadata using a single query
            insert_sql = f"""
            INSERT INTO test_case_metadata ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            """
            
            self._execute_query(insert_sql, tuple(values))
            
            # Handle tags if present
            if "TAGS" in metadata and metadata["TAGS"]:
                self._update_test_case_tags(test_case_id, metadata["TAGS"])
            
            self.logger.info(f"Created metadata for test case {test_case_id}")
            return test_case_id
            
        except Exception as e:
            self.logger.error(f"Failed to create metadata: {str(e)}")
            raise MetadataError(f"Failed to create metadata: {str(e)}")

    def _update_test_case_tags(self, test_case_id: str, tags: List[str]) -> bool:
        """
        Update tags for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            tags (List[str]): The list of tags.
            
        Returns:
            bool: True if successful.
            
        Raises:
            DatabaseError: If tag update fails.
        """
        try:
            # Convert to list if it's a string
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',')]
            elif tags is None:
                tags = []
            
            # Delete existing tag associations
            delete_query = "DELETE FROM test_case_tags WHERE test_case_id = %s"
            self._execute_query(delete_query, (test_case_id,))
            
            # Insert tags and create associations
            for tag in tags:
                if not tag:  # Skip empty tags
                    continue
                    
                # Insert tag if it doesn't exist
                insert_tag_query = """
                INSERT INTO tags (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
                """
                self._execute_query(insert_tag_query, (tag,))
                
                # Get tag id
                get_tag_query = "SELECT id FROM tags WHERE name = %s"
                tag_id = self._execute_query(get_tag_query, (tag,), fetch_one=True)[0]
                
                # Associate tag with test case
                insert_assoc_query = """
                INSERT INTO test_case_tags (test_case_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT (test_case_id, tag_id) DO NOTHING
                """
                self._execute_query(insert_assoc_query, (test_case_id, tag_id))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update tags: {str(e)}")
            raise DatabaseError(f"Failed to update tags: {str(e)}")

    def get_test_case_metadata(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get metadata for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: The metadata, or None if not found.
        """
        try:
            # Check if the test case exists
            query = """
            SELECT * FROM test_cases 
            WHERE TEST_CASE_NUMBER = %s
            ORDER BY STEP_NO ASC
            """
            
            results = self._execute_query(query, (test_case_id,), fetch_all=True, as_dict=True)
            
            if not results or len(results) == 0:
                return None
            
            # Construct a metadata structure from the query results
            # For now, we'll return the first step metadata plus an array of all steps
            first_step = results[0]
            
            # Basic metadata from the first step
            metadata = {
                "TEST_CASE_NUMBER": first_step.get("test_case_number"),
                "SUBJECT": first_step.get("subject"),
                "TEST_CASE": first_step.get("test_case"),
                "TEST_USER_ID_ROLE": first_step.get("test_user_id_role"),
                "STATUS": first_step.get("status"),
                "TYPE": first_step.get("type"),
                "CREATED_DATE": first_step.get("created_date"),
                "MODIFIED_DATE": first_step.get("modified_date"),
                # Add any additional fields that might be useful at the test case level
            }
            
            # Add steps array with all steps' information
            steps = []
            for row in results:
                step = {
                    "STEP_NO": row.get("step_no"),
                    "TEST_STEP_DESCRIPTION": row.get("test_step_description"),
                    "DATA": row.get("data"),
                    "REFERENCE_VALUES": row.get("reference_values"),
                    "VALUES": row.get("values"),
                    "EXPECTED_RESULT": row.get("expected_result"),
                    "TRANS_CODE": row.get("trans_code")
                }
                steps.append(step)
            
            metadata["STEPS"] = steps
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get metadata: {str(e)}")
            return None

    def update_test_case_metadata(self, test_case_id: str, updates: Dict[str, Any], 
                            modified_by: str = None) -> Dict[str, Any]:
        """
        Update metadata for an existing test case.
        
        Args:
            test_case_id (str): The test case ID (TEST_CASE_NUMBER).
            updates (Dict[str, Any]): Metadata fields to update.
            modified_by (str, optional): Person making the updates.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            MetadataError: If metadata update fails.
        """
        try:
            # First check if the test case exists
            existing_metadata = self.get_test_case_metadata(test_case_id)
            if not existing_metadata:
                raise MetadataError(f"Test case {test_case_id} not found")
            
            # Handle different update scenarios:
            
            # 1. If updates contain step-specific changes
            if "STEPS" in updates:
                steps_updates = updates.pop("STEPS")  # Remove steps from general updates
                
                # Process each step update
                for step_update in steps_updates:
                    if "STEP_NO" not in step_update:
                        self.logger.warning(f"Skipping step update without STEP_NO: {step_update}")
                        continue
                    
                    step_no = step_update.pop("STEP_NO")
                    
                    # Skip if no fields to update
                    if not step_update:
                        continue
                    
                    # Build the SET clause for SQL
                    set_clauses = []
                    values = []
                    
                    for field, value in step_update.items():
                        # Convert to database column names (lowercase)
                        db_field = field.lower()
                        set_clauses.append(f"{db_field} = %s")
                        values.append(value)
                    
                    # Add MODIFIED_DATE
                    set_clauses.append("modified_date = %s")
                    values.append(datetime.now())
                    
                    # Add WHERE clause parameters
                    values.append(test_case_id)
                    values.append(step_no)
                    
                    # Execute the update
                    update_sql = f"""
                    UPDATE test_cases
                    SET {', '.join(set_clauses)}
                    WHERE test_case_number = %s AND step_no = %s
                    """
                    
                    self._execute_query(update_sql, tuple(values))
            
            # 2. Handle test case level updates (will apply to all steps)
            if updates:
                # Build the SET clause for SQL
                set_clauses = []
                values = []
                
                for field, value in updates.items():
                    # Convert to database column names (lowercase)
                    db_field = field.lower()
                    set_clauses.append(f"{db_field} = %s")
                    values.append(value)
                
                # Add MODIFIED_DATE if not already included
                if "MODIFIED_DATE" not in updates:
                    set_clauses.append("modified_date = %s")
                    values.append(datetime.now())
                
                # Add WHERE clause parameter
                values.append(test_case_id)
                
                # Execute the update
                update_sql = f"""
                UPDATE test_cases
                SET {', '.join(set_clauses)}
                WHERE test_case_number = %s
                """
                
                self._execute_query(update_sql, tuple(values))
            
            # Get the updated metadata
            updated_metadata = self.get_test_case_metadata(test_case_id)
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata: {str(e)}")
            raise MetadataError(f"Failed to update metadata: {str(e)}")

    def delete_test_case_metadata(self, test_case_id: str) -> bool:
        """
        Delete metadata for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Setup a transaction to ensure all related data is deleted
            queries = [
                # Delete tag associations
                ("DELETE FROM test_case_tags WHERE test_case_id = %s", (test_case_id,)),
                
                # Delete history
                ("DELETE FROM metadata_history WHERE test_case_id = %s", (test_case_id,)),
                
                # Delete file content
                ("DELETE FROM test_case_files WHERE test_case_id = %s", (test_case_id,)),
                
                # Delete metadata
                ("DELETE FROM test_case_metadata WHERE TEST_CASE_ID = %s", (test_case_id,))
            ]
            
            # Execute transaction
            self._execute_transaction(queries)
            
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
            # Build the WHERE clause
            where_clauses = []
            params = []
            
            for field, criteria_value in criteria.items():
                # Convert field name to lowercase for DB column names
                db_field = field.lower()
                
                # Handle complex criteria with operators
                if isinstance(criteria_value, dict) and "op" in criteria_value:
                    op = criteria_value["op"].lower()
                    value = criteria_value["value"]
                    
                    if op == "equals" or op == "=":
                        where_clauses.append(f"{db_field} = %s")
                        params.append(value)
                        
                    elif op == "not equals" or op == "!=":
                        where_clauses.append(f"{db_field} != %s OR {db_field} IS NULL")
                        params.append(value)
                        
                    elif op == "contains" or op == "like":
                        # PostgreSQL ILIKE for case-insensitive search
                        where_clauses.append(f"{db_field} ILIKE %s")
                        params.append(f"%{value}%")
                        
                    elif op == "in":
                        placeholders = []
                        for v in value:
                            placeholders.append("%s")
                            params.append(v)
                        
                        where_clauses.append(f"{db_field} IN ({', '.join(placeholders)})")
                        
                    elif op == "not in":
                        placeholders = []
                        for v in value:
                            placeholders.append("%s")
                            params.append(v)
                        
                        where_clauses.append(f"{db_field} NOT IN ({', '.join(placeholders)}) OR {db_field} IS NULL")
                        
                    elif op in [">", "<", ">=", "<="]:
                        where_clauses.append(f"{db_field} {op} %s")
                        params.append(value)
                        
                    elif op == "between":
                        if isinstance(value, (list, tuple)) and len(value) == 2:
                            where_clauses.append(f"{db_field} BETWEEN %s AND %s")
                            params.append(value[0])
                            params.append(value[1])
                else:
                    # Simple equality match
                    where_clauses.append(f"{db_field} = %s")
                    params.append(criteria_value)
            
            # Build the query to get distinct test case numbers
            query = """
            SELECT DISTINCT test_case_number 
            FROM test_cases
            """
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Add ordering
            query += " ORDER BY test_case_number ASC"
            
            # Execute the query to get test case IDs
            results = self._execute_query(query, tuple(params), fetch_all=True)
            test_case_ids = [row[0] for row in results] if results else []
            
            # If no results, return empty list
            if not test_case_ids:
                return []
            
            # Get full metadata for each matching test case
            matching_test_cases = []
            for test_case_id in test_case_ids:
                metadata = self.get_test_case_metadata(test_case_id)
                if metadata:
                    matching_test_cases.append(metadata)
            
            return matching_test_cases
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise DatabaseError(f"Search operation failed: {str(e)}")

    def get_metadata_history(self, test_case_id: str) -> List[Dict[str, Any]]:
        """
        Get the history of metadata changes for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            List[Dict[str, Any]]: List of history entries, ordered by time.
        """
        try:
            query = """
            SELECT id, test_case_id, field_name, old_value, new_value, changed_by, changed_at
            FROM metadata_history
            WHERE test_case_id = %s
            ORDER BY changed_at DESC
            """
            
            history = self._execute_query(query, (test_case_id,), fetch_all=True, as_dict=True)
            
            # Convert timestamps to ISO format for consistency
            for entry in history:
                if entry["changed_at"] and isinstance(entry["changed_at"], datetime):
                    entry["changed_at"] = entry["changed_at"].isoformat()
            
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

    def get_test_cases_by_module(self, module: str) -> List[Dict[str, Any]]:
        """
        Get all test cases for a specific module.
        
        Args:
            module (str): The module name.
            
        Returns:
            List[Dict[str, Any]]: List of test case metadata.
        """
        return self.search_test_cases({"MODULE": module})

    def search_test_cases_by_content(self, search_text: str) -> List[Dict[str, Any]]:
        """
        Search for test cases containing specific text in the file content.
        
        Args:
            search_text (str): Text to search for in the test case content.
            
        Returns:
            List[Dict[str, Any]]: List of matching test case metadata.
            
        Note: This is a simplified implementation. PostgreSQL offers more advanced
            text search capabilities like full-text search that could be used here.
        """
        try:
            # First, get all test case IDs that have files with the search text in the filename
            file_query = """
            SELECT DISTINCT test_case_id 
            FROM test_case_files
            WHERE file_name ILIKE %s
            """
            
            file_results = self._execute_query(file_query, (f"%{search_text}%",), fetch_all=True)
            matching_ids = [row[0] for row in file_results] if file_results else []
            
            # If no matches in filenames, return empty list
            if not matching_ids:
                return []
            
            # Now get the full metadata for these test cases
            placeholders = []
            params = []
            for test_case_id in matching_ids:
                placeholders.append("%s")
                params.append(test_case_id)
            
            metadata_query = f"""
            SELECT * FROM test_case_metadata
            WHERE TEST_CASE_ID IN ({', '.join(placeholders)})
            ORDER BY MODIFIED_DATE DESC
            """
            
            results = self._execute_query(metadata_query, tuple(params), fetch_all=True, as_dict=True)
            
            # Process results (similar to search_test_cases)
            processed_results = []
            
            for row in results:
                # Remove the 'id' field
                if "id" in row:
                    del row["id"]
                
                # Deserialize values
                for field_name, value in dict(row).items():
                    if field_name in self.schema["metadata_fields"]:
                        field_type = self.schema["metadata_fields"][field_name]["type"]
                        row[field_name] = self._deserialize_metadata_value(value, field_type)
                
                # Get tags
                tags_query = """
                SELECT t.name
                FROM tags t
                JOIN test_case_tags tct ON t.id = tct.tag_id
                WHERE tct.test_case_id = %s
                """
                
                tags_result = self._execute_query(tags_query, (row["TEST_CASE_ID"],), fetch_all=True)
                row["TAGS"] = [tag_row[0] for tag_row in tags_result] if tags_result else []
                
                processed_results.append(row)
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Content search failed: {str(e)}")
            return []

    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags used across all test cases.
        
        Returns:
            List[str]: List of unique tags.
        """
        try:
            query = "SELECT name FROM tags ORDER BY name"
            result = self._execute_query(query, fetch_all=True)
            
            return [row[0] for row in result] if result else []
            
        except Exception as e:
            self.logger.error(f"Failed to get all tags: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about test cases.
        
        Returns:
            Dict[str, Any]: Statistics including counts by status, type, etc.
        """
        try:
            stats = {
                "total_count": 0,
                "by_status": {},
                "by_type": {},
                "by_automation_status": {},
                "by_module": {},
                "recently_modified": []
            }
            
            # Get total count
            count_query = "SELECT COUNT(*) FROM test_case_metadata"
            total_count = self._execute_query(count_query, fetch_one=True)[0]
            stats["total_count"] = total_count
            
            # Get counts by status
            status_query = """
            SELECT STATUS, COUNT(*) as count
            FROM test_case_metadata
            GROUP BY STATUS
            ORDER BY count DESC
            """
            status_results = self._execute_query(status_query, fetch_all=True)
            for row in status_results:
                stats["by_status"][row[0]] = row[1]
            
            # Get counts by type
            type_query = """
            SELECT TEST_TYPE, COUNT(*) as count
            FROM test_case_metadata
            GROUP BY TEST_TYPE
            ORDER BY count DESC
            """
            type_results = self._execute_query(type_query, fetch_all=True)
            for row in type_results:
                stats["by_type"][row[0] or "Unspecified"] = row[1]
            
            # Get counts by automation status
            auto_query = """
            SELECT AUTOMATION_STATUS, COUNT(*) as count
            FROM test_case_metadata
            GROUP BY AUTOMATION_STATUS
            ORDER BY count DESC
            """
            auto_results = self._execute_query(auto_query, fetch_all=True)
            for row in auto_results:
                stats["by_automation_status"][row[0]] = row[1]
            
            # Get counts by module
            module_query = """
            SELECT MODULE, COUNT(*) as count
            FROM test_case_metadata
            GROUP BY MODULE
            ORDER BY count DESC
            LIMIT 10
            """
            module_results = self._execute_query(module_query, fetch_all=True)
            for row in module_results:
                stats["by_module"][row[0] or "Unspecified"] = row[1]
            
            # Get recently modified test cases
            recent_query = """
            SELECT TEST_CASE_ID, TEST_TYPE, MODULE, STATUS, MODIFIED_DATE
            FROM test_case_metadata
            ORDER BY MODIFIED_DATE DESC
            LIMIT 5
            """
            recent_results = self._execute_query(recent_query, fetch_all=True, as_dict=True)
            
            # Format dates
            for row in recent_results:
                if "MODIFIED_DATE" in row and isinstance(row["MODIFIED_DATE"], datetime):
                    row["MODIFIED_DATE"] = row["MODIFIED_DATE"].isoformat()
            
            stats["recently_modified"] = recent_results
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {"total_count": 0}   


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
                "LAST_EXECUTION_DATE": datetime.now()
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

    def store_test_case_file_content(self, test_case_id: str, file_name: str, 
                            file_content: bytes, file_type: str = None,
                            uploaded_by: str = None) -> bool:
        """
        Store the content of a test case file in the database.
        
        Args:
            test_case_id (str): The test case ID.
            file_name (str): The name of the file.
            file_content (bytes): The content of the file as bytes.
            file_type (str, optional): The file type, if not provided, extracted from file_name.
            uploaded_by (str, optional): Person uploading the file.
            
        Returns:
            bool: True if successful, False otherwise.
            
        Raises:
            MetadataError: If the upload fails.
        """
        try:
            # Check if test case exists
            metadata = self.get_test_case_metadata(test_case_id)
            if not metadata:
                raise MetadataError(f"Test case {test_case_id} not found")
            
            # Determine file type if not provided
            if not file_type:
                file_type = os.path.splitext(file_name)[1].lstrip('.')
            
            # Store file in the database
            query = """
            INSERT INTO test_case_files (test_case_id, file_name, file_type, content, uploaded_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (test_case_id) DO UPDATE
            SET file_name = EXCLUDED.file_name,
                file_type = EXCLUDED.file_type,
                content = EXCLUDED.content,
                uploaded_at = EXCLUDED.uploaded_at
            """
            
            params = (test_case_id, file_name, file_type, file_content, datetime.now())
            self._execute_query(query, params)
            
            # Update metadata to indicate file storage
            self.update_test_case_metadata(
                test_case_id,
                {
                    "FILE_NAME": file_name,
                    "FILE_TYPE": file_type,
                    "MODIFIED_DATE": datetime.now()
                },
                uploaded_by
            )
            
            self.logger.info(f"Stored file '{file_name}' for test case {test_case_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store test case file: {str(e)}")
            raise MetadataError(f"Failed to store test case file: {str(e)}")

    def retrieve_test_case_file_content(self, test_case_id: str) -> Tuple[str, str, bytes]:
        """
        Retrieve the content of a test case file from the database.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Tuple[str, str, bytes]: (file_name, file_type, file_content)
            
        Raises:
            MetadataError: If the retrieval fails.
        """
        try:
            query = """
            SELECT file_name, file_type, content
            FROM test_case_files
            WHERE test_case_id = %s
            """
            
            result = self._execute_query(query, (test_case_id,), fetch_one=True)
            
            if not result:
                self.logger.warning(f"No file found for test case {test_case_id}")
                return None, None, None
            
            file_name = result[0]
            file_type = result[1]
            file_content = result[2]
            
            return file_name, file_type, file_content
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve test case file: {str(e)}")
            raise MetadataError(f"Failed to retrieve test case file: {str(e)}")

    def get_test_case_file_as_dataframe(self, test_case_id: str) -> pd.DataFrame:
        """
        Retrieve a test case file as a pandas DataFrame directly from database.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            pd.DataFrame: The test case data as a DataFrame.
            
        Raises:
            MetadataError: If the retrieval or conversion fails.
        """
        try:
            # Get file content directly from the database
            file_name, file_type, file_content = self.retrieve_test_case_file_content(test_case_id)
            
            if not file_content:
                raise MetadataError(f"No file content found for test case {test_case_id}")
            
            # Create a BytesIO object directly from the binary content
            file_obj = BytesIO(file_content)
            
            # Read as DataFrame based on file type without creating temporary files
            file_type = file_type.lower() if file_type else ''
            
            if file_type in ['xlsx', 'xls']:
                # Read Excel file directly from BytesIO
                df = pd.read_excel(file_obj, engine='openpyxl')
            elif file_type == 'csv':
                # Read CSV file directly from BytesIO
                df = pd.read_csv(file_obj)
            else:
                raise MetadataError(f"Unsupported file type: {file_type}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to convert test case file to DataFrame: {str(e)}")
            raise MetadataError(f"Failed to convert test case file to DataFrame: {str(e)}")

    def save_dataframe_as_test_case_file(self, test_case_id: str, df: pd.DataFrame, 
                                    file_name: str = None, file_type: str = 'xlsx',
                                    uploaded_by: str = None) -> bool:
        """
        Save a pandas DataFrame as a test case file directly in the database.
        
        Args:
            test_case_id (str): The test case ID.
            df (pd.DataFrame): The DataFrame to save.
            file_name (str, optional): The file name. If None, uses test_case_id.
            file_type (str, optional): The file type ('xlsx' or 'csv'). Default is 'xlsx'.
            uploaded_by (str, optional): Person uploading the file.
            
        Returns:
            bool: True if successful, False otherwise.
            
        Raises:
            MetadataError: If the save fails.
        """
        try:
            # Create file name if not provided
            if not file_name:
                file_name = f"{test_case_id}.{file_type}"
            
            # Create a BytesIO object to hold the file content
            file_obj = BytesIO()
            
            # Save DataFrame to the BytesIO object based on file type
            file_type = file_type.lower()
            
            if file_type in ['xlsx', 'xls']:
                # Save as Excel directly to BytesIO
                df.to_excel(file_obj, index=False, engine='openpyxl')
            elif file_type == 'csv':
                # Save as CSV directly to BytesIO
                df.to_csv(file_obj, index=False)
            else:
                raise MetadataError(f"Unsupported file type: {file_type}")
            
            # Get file content as bytes
            file_obj.seek(0)
            file_content = file_obj.getvalue()
            
            # Store file directly in the database
            result = self.store_test_case_file_content(
                test_case_id, file_name, file_content, file_type, uploaded_by
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to save DataFrame as test case file: {str(e)}")
            raise MetadataError(f"Failed to save DataFrame as test case file: {str(e)}")

    def file_exists_for_test_case(self, test_case_id: str) -> bool:
        """
        Check if a file exists for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            bool: True if a file exists, False otherwise.
        """
        try:
            query = """
            SELECT COUNT(*)
            FROM test_case_files
            WHERE test_case_id = %s
            """
            
            result = self._execute_query(query, (test_case_id,), fetch_one=True)
            
            return result[0] > 0
            
        except Exception as e:
            self.logger.error(f"Failed to check if file exists: {str(e)}")
            return False     
        


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
                query = "SELECT TEST_CASE_ID FROM test_case_metadata ORDER BY TEST_CASE_ID"
                result = self._execute_query(query, fetch_all=True)
                test_case_ids = [row[0] for row in result] if result else []
                
                metadata_list = [self.get_test_case_metadata(tc_id) for tc_id in test_case_ids]
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(metadata_list, f, indent=2, default=self._json_serialize)
            
            self.logger.info(f"Exported {len(metadata_list)} test case metadata records to {output_path}")
            return len(metadata_list)
            
        except Exception as e:
            self.logger.error(f"Failed to export metadata: {str(e)}")
            raise MetadataError(f"Failed to export metadata: {str(e)}")

    def _json_serialize(self, obj):
        """
        Custom JSON serializer for handling datetime objects.
        
        Args:
            obj: Object to serialize.
            
        Returns:
            str: Serialized representation.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

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

    def export_test_case_to_excel(self, test_case_id: str, output_path: str = None) -> Union[bool, BytesIO]:
        """
        Export a test case to an Excel file or return as in-memory buffer.
        
        Args:
            test_case_id (str): The test case ID.
            output_path (str, optional): Path to save the Excel file. If None, returns a BytesIO object.
            
        Returns:
            Union[bool, BytesIO]: True if saved to file path, BytesIO object if no path provided.
            
        Raises:
            MetadataError: If the export fails.
        """
        try:
            # Get test case as DataFrame
            df = self.get_test_case_file_as_dataframe(test_case_id)
            
            if df is None or df.empty:
                raise MetadataError(f"No file content found for test case {test_case_id}")
            
            # Create in-memory Excel file
            output_buffer = BytesIO()
            df.to_excel(output_buffer, index=False, engine='openpyxl')
            output_buffer.seek(0)
            
            # If output_path provided, save to file
            if output_path:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                
                # Write buffer to file
                with open(output_path, 'wb') as f:
                    f.write(output_buffer.getvalue())
                
                self.logger.info(f"Exported test case {test_case_id} to {output_path}")
                return True
            else:
                # Return the in-memory buffer for direct use
                return output_buffer
                
        except Exception as e:
            self.logger.error(f"Failed to export test case to Excel: {str(e)}")
            raise MetadataError(f"Failed to export test case to Excel: {str(e)}")

    def import_test_case_from_excel(self, file_path_or_content: Union[str, bytes], test_case_id: str = None,
                            uploaded_by: str = None) -> str:
        """
        Import a test case from an Excel file or file content.
        
        Args:
            file_path_or_content (Union[str, bytes]): Path to the Excel file or file content as bytes.
            test_case_id (str, optional): The test case ID. If None, extracted from file.
            uploaded_by (str, optional): Person uploading the file.
            
        Returns:
            str: The test case ID.
            
        Raises:
            MetadataError: If the import fails.
        """
        try:
            # Determine if input is a file path or file content
            file_name = None
            file_type = None
            file_content = None
            df = None
            
            if isinstance(file_path_or_content, str) and os.path.exists(file_path_or_content):
                # It's a file path
                file_path = file_path_or_content
                file_name = os.path.basename(file_path)
                file_type = os.path.splitext(file_name)[1].lstrip('.')
                
                # Read file content as bytes
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Read Excel directly to DataFrame
                file_io = BytesIO(file_content)
                df = pd.read_excel(file_io, engine='openpyxl')
            
            elif isinstance(file_path_or_content, bytes):
                # It's file content as bytes - assume Excel format
                file_content = file_path_or_content
                file_type = "xlsx"  # Default to xlsx
                
                # If test_case_id is provided, use it for the file name
                file_name = f"{test_case_id}.{file_type}" if test_case_id else f"imported_test_case.{file_type}"
                
                # Read Excel directly to DataFrame
                file_io = BytesIO(file_content)
                df = pd.read_excel(file_io, engine='openpyxl')
            
            else:
                raise MetadataError(f"Invalid input: must be a file path or file content as bytes")
            
            if df is None or df.empty:
                raise MetadataError(f"Empty Excel file: {file_name}")
            
            # Extract TEST_CASE_ID from file if not provided
            if not test_case_id:
                if "TEST CASE NUMBER" in df.columns and not df["TEST CASE NUMBER"].isna().all():
                    test_case_id = df["TEST CASE NUMBER"].iloc[0]
                else:
                    # Generate a new ID
                    test_case_id = f"TC-{uuid.uuid4().hex[:8].upper()}"
            
            # Extract test case metadata
            test_case_data = {}
            
            # Map fields from first row if available
            if len(df) > 0:
                first_row = df.iloc[0]
                
                # Map common fields
                field_mappings = {
                    "TEST CASE": "TEST_CASE",
                    "SUBJECT": "MODULE",
                    "TEST USER ID/ROLE": "OWNER",
                    "TYPE": "TEST_TYPE",
                    "TEST CASE NUMBER": "TEST_CASE_ID"
                }
                
                for source, target in field_mappings.items():
                    if source in df.columns and not pd.isna(first_row.get(source)):
                        test_case_data[target] = first_row.get(source)
            
            # Override with provided test_case_id
            test_case_data["TEST_CASE_ID"] = test_case_id
            
            # Create or update test case metadata
            if self.get_test_case_metadata(test_case_id):
                # Update existing
                self.update_test_case_metadata(test_case_id, test_case_data, uploaded_by)
            else:
                # Create new
                self.create_test_case_metadata(test_case_data, uploaded_by)
            
            # Store file content directly - no need to re-read from disk
            self.store_test_case_file_content(test_case_id, file_name, file_content, file_type, uploaded_by)
            
            self.logger.info(f"Imported test case with ID {test_case_id}")
            return test_case_id
            
        except Exception as e:
            self.logger.error(f"Failed to import test case from Excel: {str(e)}")
            raise MetadataError(f"Failed to import test case from Excel: {str(e)}")

    def bulk_export_test_cases(self, test_case_ids: List[str], output_dir: str,
                        include_metadata: bool = True) -> Dict[str, str]:
        """
        Export multiple test cases to files.
        
        Args:
            test_case_ids (List[str]): List of test case IDs to export.
            output_dir (str): Directory to save the files.
            include_metadata (bool, optional): Whether to include metadata in export.
            
        Returns:
            Dict[str, str]: Map of test case IDs to output file paths.
            
        Raises:
            MetadataError: If the export fails.
        """
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            result = {}
            
            # Export metadata if requested
            if include_metadata:
                metadata_path = os.path.join(output_dir, "metadata.json")
                self.export_metadata_to_json(metadata_path, test_case_ids)
            
            # Export each test case file
            for test_case_id in test_case_ids:
                try:
                    # Get file name and type
                    metadata = self.get_test_case_metadata(test_case_id)
                    if not metadata:
                        self.logger.warning(f"Test case not found: {test_case_id}")
                        continue
                    
                    # Check if file exists
                    if not self.file_exists_for_test_case(test_case_id):
                        self.logger.warning(f"No file found for test case: {test_case_id}")
                        continue
                    
                    # Get file name from metadata or use test case ID
                    file_name = metadata.get("FILE_NAME", f"{test_case_id}.xlsx")
                    file_type = metadata.get("FILE_TYPE", "xlsx")
                    
                    # Ensure file name has extension
                    if not os.path.splitext(file_name)[1]:
                        file_name = f"{file_name}.{file_type}"
                    
                    # Create output path
                    output_path = os.path.join(output_dir, file_name)
                    
                    # Export to file
                    self.export_test_case_to_excel(test_case_id, output_path)
                    
                    result[test_case_id] = output_path
                    
                except Exception as case_error:
                    self.logger.error(f"Failed to export test case {test_case_id}: {str(case_error)}")
                    # Continue with next test case
            
            self.logger.info(f"Exported {len(result)} test cases to {output_dir}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to bulk export test cases: {str(e)}")
            raise MetadataError(f"Failed to bulk export test cases: {str(e)}")

    def bulk_import_test_cases(self, file_paths: List[str], uploaded_by: str = None) -> List[str]:
        """
        Import multiple test cases from files.
        
        Args:
            file_paths (List[str]): List of file paths to import.
            uploaded_by (str, optional): Person uploading the files.
            
        Returns:
            List[str]: List of imported test case IDs.
            
        Raises:
            MetadataError: If the import fails.
        """
        try:
            imported_ids = []
            
            for file_path in file_paths:
                try:
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    if file_ext in ['.xlsx', '.xls']:
                        # Import Excel file
                        test_case_id = self.import_test_case_from_excel(file_path, None, uploaded_by)
                        imported_ids.append(test_case_id)
                    else:
                        self.logger.warning(f"Unsupported file type: {file_ext}")
                        # Skip this file
                    
                except Exception as file_error:
                    self.logger.error(f"Failed to import file {file_path}: {str(file_error)}")
                    # Continue with next file
            
            self.logger.info(f"Imported {len(imported_ids)} test cases")
            return imported_ids
            
        except Exception as e:
            self.logger.error(f"Failed to bulk import test cases: {str(e)}")
            raise MetadataError(f"Failed to bulk import test cases: {str(e)}")

    def export_test_cases_as_zip(self, test_case_ids: List[str], output_path: str,
                        include_metadata: bool = True) -> str:
        """
        Export multiple test cases as a ZIP file.
        
        Args:
            test_case_ids (List[str]): List of test case IDs to export.
            output_path (str): Path for the output ZIP file.
            include_metadata (bool, optional): Whether to include metadata in export.
            
        Returns:
            str: Path to the created ZIP file.
            
        Raises:
            MetadataError: If the export fails.
        """
        try:
            import zipfile
            import tempfile
            
            # Create a temporary directory for files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Export files to the temporary directory
                self.bulk_export_test_cases(test_case_ids, temp_dir, include_metadata)
                
                # Create ZIP file
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files from the temporary directory
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Calculate the relative path for the archive
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
            
            self.logger.info(f"Exported {len(test_case_ids)} test cases to ZIP file: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to export test cases as ZIP: {str(e)}")
            raise MetadataError(f"Failed to export test cases as ZIP: {str(e)}")    
        


    def _close_connection_pool(self):
        """
        Close the connection pool and release all resources.
        """
        try:
            if hasattr(self, 'connection_pool') and self.connection_pool:
                self.connection_pool.closeall()
                self.logger.info("PostgreSQL connection pool closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing connection pool: {str(e)}")

    def __del__(self):
        """
        Destructor to ensure connection pool is closed when object is deleted.
        """
        self._close_connection_pool()

    def vacuum_database(self):
        """
        Run VACUUM operation to reclaim storage and update statistics.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        conn = None
        try:
            # Get a connection directly (not from pool) for VACUUM
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                sslmode=self.db_config['sslmode']
            )
            
            # Set autocommit mode required for VACUUM
            conn.set_session(autocommit=True)
            
            cursor = conn.cursor()
            cursor.execute("VACUUM ANALYZE")
            
            self.logger.info("VACUUM ANALYZE completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to run VACUUM: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def check_database_connection(self) -> bool:
        """
        Check if the database connection is working.
        
        Returns:
            bool: True if connection is working, False otherwise.
        """
        try:
            query = "SELECT 1"
            result = self._execute_query(query, fetch_one=True)
            return result is not None and result[0] == 1
        except Exception as e:
            self.logger.error(f"Database connection check failed: {str(e)}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the database tables.
        
        Returns:
            Dict[str, Any]: Database statistics.
        """
        try:
            stats = {}
            
            # Table row counts
            tables = ["test_case_metadata", "metadata_history", "tags", "test_case_tags", "test_case_files"]
            
            for table in tables:
                query = f"SELECT COUNT(*) FROM {table}"
                count = self._execute_query(query, fetch_one=True)[0]
                stats[f"{table}_count"] = count
            
            # Database size
            size_query = """
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
            """
            db_size = self._execute_query(size_query, fetch_one=True)[0]
            stats["database_size"] = db_size
            
            # Table sizes
            table_sizes_query = """
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size
            FROM 
                pg_catalog.pg_statio_user_tables
            ORDER BY 
                pg_total_relation_size(relid) DESC
            """
            table_sizes = self._execute_query(table_sizes_query, fetch_all=True, as_dict=True)
            stats["table_sizes"] = table_sizes
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {"error": str(e)}

    def cleanup_orphaned_data(self) -> Dict[str, int]:
        """
        Clean up orphaned data (tags, files without associated test cases).
        
        Returns:
            Dict[str, int]: Count of cleaned items by type.
        """
        try:
            cleanup_stats = {
                "orphaned_tags": 0,
                "orphaned_files": 0,
                "unused_tags": 0
            }
            
            # Remove orphaned tag associations (where test case no longer exists)
            orphaned_tags_query = """
            DELETE FROM test_case_tags
            WHERE test_case_id NOT IN (
                SELECT TEST_CASE_ID FROM test_case_metadata
            )
            """
            orphaned_tags_count = self._execute_query(orphaned_tags_query)
            cleanup_stats["orphaned_tags"] = orphaned_tags_count
            
            # Remove orphaned files (where test case no longer exists)
            orphaned_files_query = """
            DELETE FROM test_case_files
            WHERE test_case_id NOT IN (
                SELECT TEST_CASE_ID FROM test_case_metadata
            )
            """
            orphaned_files_count = self._execute_query(orphaned_files_query)
            cleanup_stats["orphaned_files"] = orphaned_files_count
            
            # Remove unused tags (not associated with any test case)
            unused_tags_query = """
            DELETE FROM tags
            WHERE id NOT IN (
                SELECT tag_id FROM test_case_tags
            )
            """
            unused_tags_count = self._execute_query(unused_tags_query)
            cleanup_stats["unused_tags"] = unused_tags_count
            
            self.logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise DatabaseError(f"Database cleanup failed: {str(e)}")

    def migrate_from_sqlite(self, sqlite_db_path: str) -> Dict[str, int]:
        """
        Migrate data from SQLite database to PostgreSQL.
        
        Args:
            sqlite_db_path (str): Path to the SQLite database file.
            
        Returns:
            Dict[str, int]: Migration statistics.
            
        Raises:
            DatabaseError: If migration fails.
        """
        try:
            import sqlite3
            
            # Check if SQLite file exists
            if not os.path.exists(sqlite_db_path):
                raise DatabaseError(f"SQLite database file not found: {sqlite_db_path}")
            
            # Connect to SQLite database
            sqlite_conn = sqlite3.connect(sqlite_db_path)
            sqlite_conn.row_factory = sqlite3.Row
            
            # Statistics
            stats = {
                "test_cases_migrated": 0,
                "history_records_migrated": 0,
                "tags_migrated": 0,
                "tag_associations_migrated": 0
            }
            
            # Migrate test case metadata
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("SELECT * FROM test_case_metadata")
            test_cases = [dict(row) for row in sqlite_cursor.fetchall()]
            
            for tc in test_cases:
                # Remove SQLite rowid
                if "id" in tc:
                    del tc["id"]
                
                # Create in PostgreSQL
                try:
                    self.create_test_case_metadata(tc, "Migration")
                    stats["test_cases_migrated"] += 1
                except Exception as tc_error:
                    self.logger.error(f"Failed to migrate test case {tc.get('TEST_CASE_ID')}: {str(tc_error)}")
                    # Continue with next test case
            
            # Migrate tags
            sqlite_cursor.execute("SELECT * FROM tags")
            tags = [dict(row) for row in sqlite_cursor.fetchall()]
            
            tag_id_map = {}  # Map SQLite IDs to PostgreSQL IDs
            
            for tag in tags:
                tag_name = tag["name"]
                
                # Insert tag if it doesn't exist
                tag_query = """
                INSERT INTO tags (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
                """
                
                tag_result = self._execute_query(tag_query, (tag_name,), fetch_one=True)
                
                if tag_result:
                    new_id = tag_result[0]
                else:
                    # Get the ID if already exists
                    get_id_query = "SELECT id FROM tags WHERE name = %s"
                    new_id = self._execute_query(get_id_query, (tag_name,), fetch_one=True)[0]
                
                tag_id_map[tag["id"]] = new_id
                stats["tags_migrated"] += 1
            
            # Migrate tag associations
            sqlite_cursor.execute("SELECT * FROM test_case_tags")
            tag_assocs = [dict(row) for row in sqlite_cursor.fetchall()]
            
            for assoc in tag_assocs:
                test_case_id = assoc["test_case_id"]
                old_tag_id = assoc["tag_id"]
                
                if old_tag_id in tag_id_map:
                    new_tag_id = tag_id_map[old_tag_id]
                    
                    # Insert association
                    assoc_query = """
                    INSERT INTO test_case_tags (test_case_id, tag_id)
                    VALUES (%s, %s)
                    ON CONFLICT (test_case_id, tag_id) DO NOTHING
                    """
                    
                    self._execute_query(assoc_query, (test_case_id, new_tag_id))
                    stats["tag_associations_migrated"] += 1
            
            # Migrate history
            sqlite_cursor.execute("SELECT * FROM metadata_history")
            history = [dict(row) for row in sqlite_cursor.fetchall()]
            
            for record in history:
                # Remove SQLite rowid
                if "id" in record:
                    del record["id"]
                
                # Insert history record
                history_query = """
                INSERT INTO metadata_history
                (test_case_id, field_name, old_value, new_value, changed_by, changed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                history_params = (
                    record["test_case_id"],
                    record["field_name"],
                    record["old_value"],
                    record["new_value"],
                    record["changed_by"] or "Migration",
                    datetime.fromisoformat(record["changed_at"]) if "changed_at" in record else datetime.now()
                )
                
                self._execute_query(history_query, history_params)
                stats["history_records_migrated"] += 1
            
            sqlite_conn.close()
            self.logger.info(f"Migration completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise DatabaseError(f"Migration failed: {str(e)}")

    def restore_from_backup(self, backup_dir: str) -> Dict[str, int]:
        """
        Restore database from a backup directory containing JSON and file data.
        
        Args:
            backup_dir (str): Path to the backup directory.
            
        Returns:
            Dict[str, int]: Restoration statistics.
            
        Raises:
            DatabaseError: If restoration fails.
        """
        try:
            stats = {
                "metadata_restored": 0,
                "files_restored": 0
            }
            
            # Check if directory exists
            if not os.path.isdir(backup_dir):
                raise DatabaseError(f"Backup directory not found: {backup_dir}")
            
            # Check for metadata JSON file
            metadata_file = os.path.join(backup_dir, "metadata.json")
            if os.path.exists(metadata_file):
                # Import metadata
                metadata_count = self.import_metadata_from_json(metadata_file, overwrite=True)
                stats["metadata_restored"] = metadata_count
            
            # Check for files directory
            files_dir = os.path.join(backup_dir, "files")
            if os.path.isdir(files_dir):
                # Import each file
                for file_name in os.listdir(files_dir):
                    file_path = os.path.join(files_dir, file_name)
                    
                    # Skip directories
                    if os.path.isdir(file_path):
                        continue
                    
                    try:
                        # Extract test case ID from filename (assuming format: TC-XXXXX.xlsx)
                        test_case_id = os.path.splitext(file_name)[0]
                        
                        # Check if it's a valid test case ID
                        if not self.get_test_case_metadata(test_case_id):
                            # Try to parse test case ID from file content
                            self.import_test_case_from_excel(file_path, None, "Restoration")
                        else:
                            # Just restore the file
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                            
                            self.store_test_case_file_content(
                                test_case_id,
                                file_name,
                                file_content,
                                os.path.splitext(file_name)[1].lstrip('.')
                            )
                        
                        stats["files_restored"] += 1
                        
                    except Exception as file_error:
                        self.logger.error(f"Failed to restore file {file_name}: {str(file_error)}")
                        # Continue with next file
            
            self.logger.info(f"Restoration completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Restoration failed: {str(e)}")
            raise DatabaseError(f"Database restoration failed: {str(e)}")

    def create_backup(self, backup_dir: str, include_files: bool = True) -> Dict[str, int]:
        """
        Create a backup of the database.
        
        Args:
            backup_dir (str): Directory to store the backup.
            include_files (bool, optional): Whether to include test case files.
            
        Returns:
            Dict[str, int]: Backup statistics.
            
        Raises:
            DatabaseError: If backup fails.
        """
        try:
            stats = {
                "metadata_backed_up": 0,
                "files_backed_up": 0
            }
            
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup metadata
            metadata_file = os.path.join(backup_dir, "metadata.json")
            metadata_count = self.export_metadata_to_json(metadata_file)
            stats["metadata_backed_up"] = metadata_count
            
            # Backup files if requested
            if include_files:
                files_dir = os.path.join(backup_dir, "files")
                os.makedirs(files_dir, exist_ok=True)
                
                # Get all test case IDs
                query = "SELECT TEST_CASE_ID FROM test_case_metadata"
                result = self._execute_query(query, fetch_all=True)
                test_case_ids = [row[0] for row in result] if result else []
                
                # Backup each file
                for test_case_id in test_case_ids:
                    try:
                        file_name, file_type, file_content = self.retrieve_test_case_file_content(test_case_id)
                        
                        if file_content:
                            # Create file name if not present
                            if not file_name:
                                file_name = f"{test_case_id}.{file_type or 'xlsx'}"
                            
                            # Save file
                            file_path = os.path.join(files_dir, file_name)
                            with open(file_path, 'wb') as f:
                                f.write(file_content)
                            
                            stats["files_backed_up"] += 1
                            
                    except Exception as file_error:
                        self.logger.error(f"Failed to backup file for {test_case_id}: {str(file_error)}")
                        # Continue with next test case
            
            self.logger.info(f"Backup completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            raise DatabaseError(f"Database backup failed: {str(e)}")    