"""
Database Utilities for the Watsonx IPG Testing Platform.

This module provides database connectivity and operations for both PostgreSQL
relational database and IBM Cloud Object Storage/MinIO. It handles connection pooling,
query execution, transaction management, and object storage operations.

The utilities support all platform integrations including JIRA, SharePoint, ALM, 
UFT systems, and RPA (Blue Prism) by providing consistent data access 
patterns and storage solutions.

Dependencies:
    - psycopg2-binary: PostgreSQL database adapter
    - sqlalchemy: SQL toolkit and ORM
    - ibm-boto3: IBM COS
    - minio: MinIO Python client

Environment variables required:
    For PostgreSQL:
        - DB_HOST: Database host
        - DB_PORT: Database port
        - DB_NAME: Database name
        - DB_USER: Database user
        - DB_PASSWORD: Database password
        - DB_SSL_MODE: SSL mode (disable, require, verify-ca, verify-full)
        
    For IBM Cloud Object Storage:
        - COS_ENDPOINT: COS endpoint URL
        - COS_API_KEY: IBM Cloud API key
        - COS_INSTANCE_CRN: COS instance CRN
        - COS_AUTH_ENDPOINT: IAM authentication endpoint
        
    For MinIO (alternative to IBM COS):
        - MINIO_ENDPOINT: MinIO endpoint URL
        - MINIO_ACCESS_KEY: MinIO access key
        - MINIO_SECRET_KEY: MinIO secret key
        - MINIO_SECURE: Use HTTPS (True/False)
"""

import os
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps

# PostgreSQL libraries
import psycopg2
from psycopg2 import pool, extras
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

# Object storage libraries (will be used in Part 3)
import ibm_boto3
from ibm_botocore.client import Config
from minio import Minio
from minio.error import S3Error

# Configure logger
logger = logging.getLogger(__name__)

# Constants
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.0  # seconds
CONNECTION_POOL_MIN_CONN = 1
CONNECTION_POOL_MAX_CONN = 10
CONNECTION_TIMEOUT = 30  # seconds
QUERY_TIMEOUT = 120  # seconds
DEFAULT_BUCKET = "watsonx-ipg-testing"
DEFAULT_REGION = "us-south"  # Default IBM Cloud region

# ------------- Part 1: PostgreSQL Connection Management -------------

class DatabasePool:
    """
    Singleton class to manage PostgreSQL connection pooling.
    """
    _instance = None
    _connection_pool = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
            cls._instance._init_pool()
        return cls._instance

    def _init_pool(self):
        """Initialize connection pool for PostgreSQL."""
        try:
            # Get database configuration from environment variables
            db_config = {
                'host': os.environ.get('DB_HOST', 'localhost'),
                'port': os.environ.get('DB_PORT', '5432'),
                'dbname': os.environ.get('DB_NAME', 'watsonx_ipg_db'),
                'user': os.environ.get('DB_USER', 'postgres'),
                'password': os.environ.get('DB_PASSWORD', ''),
                'sslmode': os.environ.get('DB_SSL_MODE', 'require')
            }
            
            # Create connection pool with psycopg2
            self._connection_pool = pool.ThreadedConnectionPool(
                CONNECTION_POOL_MIN_CONN,
                CONNECTION_POOL_MAX_CONN,
                **db_config,
                connect_timeout=CONNECTION_TIMEOUT
            )
            
            # Create SQLAlchemy engine for ORM operations
            db_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
            self._engine = create_engine(
                db_url,
                pool_size=CONNECTION_POOL_MAX_CONN,
                max_overflow=2,
                pool_timeout=CONNECTION_TIMEOUT,
                pool_recycle=1800  # Recycle connections after 30 minutes
            )
            
            self._session_factory = scoped_session(sessionmaker(bind=self._engine))
            
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {str(e)}")
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        if not self._connection_pool:
            self._init_pool()
        return self._connection_pool.getconn()

    def release_connection(self, conn):
        """Return a connection to the pool."""
        if self._connection_pool:
            self._connection_pool.putconn(conn)

    def get_engine(self):
        """Get SQLAlchemy engine."""
        if not self._engine:
            self._init_pool()
        return self._engine

    def get_session(self):
        """Get SQLAlchemy session."""
        if not self._session_factory:
            self._init_pool()
        return self._session_factory()

    def close_all(self):
        """Close all connections in the pool."""
        if self._connection_pool:
            self._connection_pool.closeall()
        if self._session_factory:
            self._session_factory.remove()
        logger.info("All database connections closed")


# Initialize the database pool as a global object
_db_pool = DatabasePool()


@contextmanager
def get_db_connection():
    """
    Context manager for getting and automatically releasing database connections.
    
    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_cases")
    """
    conn = None
    try:
        conn = _db_pool.get_connection()
        yield conn
    finally:
        if conn:
            _db_pool.release_connection(conn)


@contextmanager
def get_db_session():
    """
    Context manager for SQLAlchemy session handling.
    
    Example:
        with get_db_session() as session:
            result = session.execute("SELECT * FROM test_cases")
    """
    session = _db_pool.get_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def retry_on_db_error(func):
    """
    Decorator to retry database operations on failure.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                return func(*args, **kwargs)
            except (psycopg2.OperationalError, SQLAlchemyError) as e:
                last_error = e
                if attempt < RETRY_ATTEMPTS - 1:
                    logger.warning(f"Database operation failed, retrying ({attempt+1}/{RETRY_ATTEMPTS}): {str(e)}")
                    time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Database operation failed after {RETRY_ATTEMPTS} attempts: {str(e)}")
        raise last_error
    return wrapper


@retry_on_db_error
def connect_to_database():
    """
    Establish a connection to the PostgreSQL database.
    
    Returns:
        psycopg2.extensions.connection: A database connection
    
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        conn = _db_pool.get_connection()
        logger.debug("Database connection established successfully")
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise


def close_database_connections():
    """
    Close all database connections when application is shutting down.
    """
    _db_pool.close_all()
    logger.info("All database connections closed")


def is_database_healthy():
    """
    Check if the database is healthy by executing a simple query.
    
    Returns:
        bool: True if database is healthy
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as healthy")
                result = cursor.fetchone()
                return result[0] == 1
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False

# End of Part 1: PostgreSQL Connection Management

# ------------- Part 2: Basic Database Operations -------------

@retry_on_db_error
def query_database(
    query: str,
    params: Optional[Union[Dict, List, Tuple]] = None,
    fetch_one: bool = False,
    as_dict: bool = True
) -> Union[List[Dict[str, Any]], Dict[str, Any], List[Tuple], Tuple, None]:
    """
    Execute a SELECT query on the database.
    
    Args:
        query: SQL query string
        params: Parameters to bind to the query
        fetch_one: If True, fetch only one result
        as_dict: If True, return results as dictionaries, otherwise as tuples
    
    Returns:
        Query results as specified by fetch_one and as_dict parameters
        
    Raises:
        psycopg2.Error: If query execution fails
    """
    with get_db_connection() as conn:
        cursor_factory = extras.RealDictCursor if as_dict else None
        with conn.cursor(cursor_factory=cursor_factory) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
                
            # Convert result to list if it's not None
            if result is not None and not fetch_one and not isinstance(result, list):
                result = list(result)
                
            return result


@retry_on_db_error
def update_database(
    query: str,
    params: Optional[Union[Dict, List, Tuple]] = None,
    return_id: bool = False,
    commit: bool = True
) -> Optional[Any]:
    """
    Execute an INSERT, UPDATE, or DELETE query on the database.
    
    Args:
        query: SQL query string
        params: Parameters to bind to the query
        return_id: If True, return the ID of the inserted row
        commit: If True, commit the transaction
    
    Returns:
        If return_id is True, the ID of the inserted row
        Otherwise, the number of affected rows
        
    Raises:
        psycopg2.Error: If query execution fails
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            
            inserted_id = None
            if return_id:
                inserted_id = cursor.fetchone()[0]
                
            if commit:
                conn.commit()
                
            affected_rows = cursor.rowcount
            logger.debug(f"Query affected {affected_rows} rows")
            
            return inserted_id if return_id else affected_rows


@retry_on_db_error
def batch_update_database(
    query: str,
    params_list: List[Union[Dict, List, Tuple]],
    commit: bool = True
) -> int:
    """
    Execute batch INSERT, UPDATE, or DELETE operations on the database.
    
    Args:
        query: SQL query string
        params_list: List of parameters for batch operation
        commit: If True, commit the transaction
    
    Returns:
        int: Number of affected rows
        
    Raises:
        psycopg2.Error: If query execution fails
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            extras.execute_batch(cursor, query, params_list)
            
            if commit:
                conn.commit()
                
            affected_rows = cursor.rowcount
            logger.debug(f"Batch query affected {affected_rows} rows")
            
            return affected_rows


@retry_on_db_error
def execute_transaction(
    queries_params: List[Tuple[str, Optional[Union[Dict, List, Tuple]]]]
) -> bool:
    """
    Execute multiple queries as a single transaction.
    
    Args:
        queries_params: List of (query, params) tuples
    
    Returns:
        bool: True if transaction was successful
        
    Raises:
        psycopg2.Error: If transaction fails
    """
    with get_db_connection() as conn:
        try:
            with conn.cursor() as cursor:
                for query, params in queries_params:
                    cursor.execute(query, params)
                conn.commit()
                logger.debug("Transaction executed successfully")
                return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed and was rolled back: {str(e)}")
            raise


@retry_on_db_error
def execute_procedure(
    procedure_name: str,
    params: Optional[Union[Dict, List, Tuple]] = None,
    fetch_results: bool = False
) -> Optional[List[Dict[str, Any]]]:
    """
    Execute a stored procedure.
    
    Args:
        procedure_name: Name of the stored procedure
        params: Parameters to pass to the procedure
        fetch_results: Whether to fetch and return results
    
    Returns:
        Optional results from the procedure if fetch_results is True
        
    Raises:
        psycopg2.Error: If procedure execution fails
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cursor:
            # Build parameter placeholders
            if params:
                if isinstance(params, dict):
                    placeholders = ", ".join([f"%({k})s" for k in params.keys()])
                else:
                    placeholders = ", ".join(["%s"] * len(params))
                query = f"CALL {procedure_name}({placeholders});"
            else:
                query = f"CALL {procedure_name}();"
            
            cursor.execute(query, params)
            
            if fetch_results:
                return cursor.fetchall()
            
            return None


def table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        table_name: Name of the table
    
    Returns:
        bool: True if the table exists
    """
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name = %s
    );
    """
    result = query_database(query, (table_name,), fetch_one=True)
    return result['exists'] if result else False


@retry_on_db_error
def execute_sql_file(file_path: str, parameterized: bool = False, params: Dict = None) -> bool:
    """
    Execute SQL statements from a file.
    
    Args:
        file_path: Path to the SQL file
        parameterized: Whether the SQL contains parameters
        params: Parameters to bind to the SQL if parameterized
    
    Returns:
        bool: True if execution was successful
    """
    try:
        with open(file_path, 'r') as f:
            sql = f.read()
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if parameterized and params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
        
        logger.info(f"Successfully executed SQL file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to execute SQL file {file_path}: {str(e)}")
        raise


def get_column_info(table_name: str) -> List[Dict[str, Any]]:
    """
    Get information about columns in a table.
    
    Args:
        table_name: Name of the table
    
    Returns:
        List[Dict]: Information about each column
    """
    query = """
    SELECT 
        column_name,
        data_type,
        character_maximum_length,
        column_default,
        is_nullable
    FROM 
        information_schema.columns 
    WHERE 
        table_schema = 'public' 
        AND table_name = %s
    ORDER BY 
        ordinal_position;
    """
    
    columns = query_database(query, (table_name,))
    return columns


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique ID for test cases, executions, etc.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        str: Unique ID
    """
    import uuid
    unique_id = str(uuid.uuid4()).replace('-', '')
    
    if prefix:
        return f"{prefix}_{unique_id}"
    
    return unique_id


def init_database_tables() -> bool:
    """
    Initialize database tables if they don't exist.
    
    Returns:
        bool: True if successful
    """
    # List of table creation queries
    table_queries = [
        # Test Cases Table
        """
        CREATE TABLE IF NOT EXISTS test_cases (
            id VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            version VARCHAR(50) NOT NULL,
            storage_path VARCHAR(512) NOT NULL,
            format VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP,
            PRIMARY KEY (id, version)
        )
        """,
        
        # Test Executions Table
        """
        CREATE TABLE IF NOT EXISTS test_executions (
            execution_id VARCHAR(255) NOT NULL PRIMARY KEY,
            test_case_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            result_path VARCHAR(512) NOT NULL,
            execution_time INTEGER,
            screenshots JSONB,
            executed_at TIMESTAMP NOT NULL,
            notes TEXT
        )
        """,
        
        # Defects Table
        """
        CREATE TABLE IF NOT EXISTS defects (
            id SERIAL PRIMARY KEY,
            test_case_id VARCHAR(255) NOT NULL,
            execution_id VARCHAR(255),
            defect_id VARCHAR(255),  -- External defect ID (e.g., JIRA)
            summary VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            severity VARCHAR(50) NOT NULL,
            assigned_to VARCHAR(255),
            status VARCHAR(50) NOT NULL,
            resolution TEXT,
            steps_to_reproduce TEXT,
            screenshots JSONB,
            comments TEXT,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP
        )
        """,
        
        # Test Data Table
        """
        CREATE TABLE IF NOT EXISTS test_data (
            id SERIAL PRIMARY KEY,
            test_case_id VARCHAR(255) NOT NULL,
            data_type VARCHAR(50) NOT NULL,
            storage_path VARCHAR(512) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP
        )
        """,
        
        # Integration Credentials Table
        """
        CREATE TABLE IF NOT EXISTS integration_credentials (
            id SERIAL PRIMARY KEY,
            system_type VARCHAR(50) NOT NULL,
            credentials TEXT NOT NULL,
            encrypted BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP
        )
        """,
        
        # SharePoint Documents Table
        """
        CREATE TABLE IF NOT EXISTS sharepoint_documents (
            id SERIAL PRIMARY KEY,
            file_name VARCHAR(255) NOT NULL,
            storage_path VARCHAR(512) NOT NULL,
            content_type VARCHAR(255) NOT NULL,
            sync_status VARCHAR(50) NOT NULL,
            sharepoint_url VARCHAR(512),
            created_at TIMESTAMP NOT NULL,
            synced_at TIMESTAMP
        )
        """,
        
        # Blue Prism Jobs Table
        """
        CREATE TABLE IF NOT EXISTS blueprism_jobs (
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(255) NOT NULL,
            test_case_id VARCHAR(255),
            controller_file VARCHAR(512) NOT NULL,
            status VARCHAR(50) NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            result VARCHAR(50),
            error_message TEXT,
            logs_path VARCHAR(512)
        )
        """
    ]
    
    try:
        for query in table_queries:
            update_database(query)
            
        logger.info("Database tables initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {str(e)}")
        raise


def get_database_info() -> Dict[str, Any]:
    """
    Get information about the database, including table counts.
    
    Returns:
        Dict: Database information
    """
    tables = [
        'test_cases', 'test_executions', 'defects', 'test_data',
        'integration_credentials', 'sharepoint_documents', 'blueprism_jobs'
    ]
    
    db_info = {
        'tables': {},
        'version': None
    }
    
    # Get PostgreSQL version
    version_query = "SELECT version();"
    version_result = query_database(version_query, fetch_one=True)
    if version_result:
        db_info['version'] = version_result['version']
    
    # Get row counts for each table
    for table in tables:
        if table_exists(table):
            count_query = f"SELECT COUNT(*) as count FROM {table};"
            count_result = query_database(count_query, fetch_one=True)
            if count_result:
                db_info['tables'][table] = {
                    'exists': True,
                    'row_count': count_result['count']
                }
        else:
            db_info['tables'][table] = {
                'exists': False,
                'row_count': 0
            }
    
    logger.info("Retrieved database information")
    return db_info

# End of Part 2: Basic Database Operations


# ------------- Part 3: Object Storage Framework -------------

class ObjectStorageClient:
    """
    Class to handle object storage operations for both IBM Cloud Object Storage and MinIO.
    Implements the adapter pattern to provide a unified interface for both storage solutions.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ObjectStorageClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance
    
    def _init_client(self):
        """
        Initialize the appropriate object storage client based on environment configuration.
        Prioritizes IBM Cloud Object Storage if credentials are available.
        """
        # Check if IBM COS credentials are available
        cos_endpoint = os.environ.get('COS_ENDPOINT')
        cos_api_key = os.environ.get('COS_API_KEY')
        cos_instance_crn = os.environ.get('COS_INSTANCE_CRN')
        
        if cos_endpoint and cos_api_key and cos_instance_crn:
            self._init_ibm_cos_client()
            self.client_type = 'ibm_cos'
            logger.info("IBM Cloud Object Storage client initialized")
        else:
            # Fall back to MinIO client
            minio_endpoint = os.environ.get('MINIO_ENDPOINT')
            minio_access_key = os.environ.get('MINIO_ACCESS_KEY')
            minio_secret_key = os.environ.get('MINIO_SECRET_KEY')
            
            if minio_endpoint and minio_access_key and minio_secret_key:
                self._init_minio_client()
                self.client_type = 'minio'
                logger.info("MinIO client initialized")
            else:
                logger.error("No object storage credentials found")
                raise ValueError("Missing object storage credentials")
    
    def _init_ibm_cos_client(self):
        """Initialize IBM Cloud Object Storage client."""
        cos_endpoint = os.environ.get('COS_ENDPOINT')
        cos_api_key = os.environ.get('COS_API_KEY')
        cos_instance_crn = os.environ.get('COS_INSTANCE_CRN')
        cos_auth_endpoint = os.environ.get('COS_AUTH_ENDPOINT', 'https://iam.cloud.ibm.com/identity/token')
        
        self.client = ibm_boto3.resource(
            's3',
            endpoint_url=cos_endpoint,
            ibm_api_key_id=cos_api_key,
            ibm_service_instance_id=cos_instance_crn,
            ibm_auth_endpoint=cos_auth_endpoint,
            config=Config(signature_version='oauth'),
            region_name=DEFAULT_REGION
        )
        
        # Also create a boto3 client for operations not supported by resource
        self.boto_client = ibm_boto3.client(
            's3',
            endpoint_url=cos_endpoint,
            ibm_api_key_id=cos_api_key,
            ibm_service_instance_id=cos_instance_crn,
            ibm_auth_endpoint=cos_auth_endpoint,
            config=Config(signature_version='oauth'),
            region_name=DEFAULT_REGION
        )
    
    def _init_minio_client(self):
        """Initialize MinIO client."""
        minio_endpoint = os.environ.get('MINIO_ENDPOINT')
        minio_access_key = os.environ.get('MINIO_ACCESS_KEY')
        minio_secret_key = os.environ.get('MINIO_SECRET_KEY')
        minio_secure = os.environ.get('MINIO_SECURE', 'True').lower() in ('true', '1', 't')
        
        self.client = Minio(
            minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=minio_secure
        )
        
        # For API compatibility with IBM COS
        self.boto_client = None
    
    def bucket_exists(self, bucket_name: str = DEFAULT_BUCKET) -> bool:
        """
        Check if a bucket exists.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            bool: True if the bucket exists
        """
        try:
            if self.client_type == 'ibm_cos':
                # IBM COS
                bucket = self.client.Bucket(bucket_name)
                bucket.load()  # Will raise exception if bucket doesn't exist
                return True
            else:
                # MinIO
                return self.client.bucket_exists(bucket_name)
        except Exception as e:
            logger.debug(f"Bucket {bucket_name} does not exist: {str(e)}")
            return False
    
    def create_bucket(self, bucket_name: str = DEFAULT_BUCKET) -> bool:
        """
        Create a new bucket.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            bool: True if bucket was created or already exists
        """
        try:
            if not self.bucket_exists(bucket_name):
                if self.client_type == 'ibm_cos':
                    # IBM COS
                    self.client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': DEFAULT_REGION}
                    )
                else:
                    # MinIO
                    self.client.make_bucket(bucket_name)
                logger.info(f"Bucket {bucket_name} created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {str(e)}")
            raise
    
    def upload_file(
        self,
        file_path: str,
        object_name: str = None,
        bucket_name: str = DEFAULT_BUCKET,
        metadata: Dict[str, str] = None
    ) -> bool:
        """
        Upload a file to object storage.
        
        Args:
            file_path: Path to the local file
            object_name: Name to give the object in storage (default: basename of file_path)
            bucket_name: Name of the bucket
            metadata: Optional metadata dict
            
        Returns:
            bool: True if upload was successful
        """
        if not object_name:
            object_name = os.path.basename(file_path)
            
        metadata = metadata or {}
        
        try:
            # Ensure bucket exists
            if not self.bucket_exists(bucket_name):
                self.create_bucket(bucket_name)
                
            # Upload file
            if self.client_type == 'ibm_cos':
                # IBM COS
                self.client.Object(bucket_name, object_name).upload_file(
                    Filename=file_path,
                    ExtraArgs={'Metadata': metadata}
                )
            else:
                # MinIO
                self.client.fput_object(
                    bucket_name,
                    object_name,
                    file_path,
                    metadata=metadata
                )
                
            logger.info(f"File {file_path} uploaded to {bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file {file_path} to {bucket_name}/{object_name}: {str(e)}")
            raise
    
    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        bucket_name: str = DEFAULT_BUCKET,
        metadata: Dict[str, str] = None,
        content_type: str = None
    ) -> bool:
        """
        Upload bytes data to object storage.
        
        Args:
            data: Bytes to upload
            object_name: Name to give the object in storage
            bucket_name: Name of the bucket
            metadata: Optional metadata dict
            content_type: Optional content type
            
        Returns:
            bool: True if upload was successful
        """
        metadata = metadata or {}
        
        try:
            # Ensure bucket exists
            if not self.bucket_exists(bucket_name):
                self.create_bucket(bucket_name)
                
            # Upload data
            if self.client_type == 'ibm_cos':
                # IBM COS
                extra_args = {'Metadata': metadata}
                if content_type:
                    extra_args['ContentType'] = content_type
                
                self.client.Object(bucket_name, object_name).put(
                    Body=data,
                    **extra_args
                )
            else:
                # MinIO
                from io import BytesIO
                self.client.put_object(
                    bucket_name,
                    object_name,
                    BytesIO(data),
                    length=len(data),
                    content_type=content_type or 'application/octet-stream',
                    metadata=metadata
                )
                
            logger.info(f"Data uploaded to {bucket_name}/{object_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload data to {bucket_name}/{object_name}: {str(e)}")
            raise
    
    def download_file(
        self,
        object_name: str,
        file_path: str,
        bucket_name: str = DEFAULT_BUCKET
    ) -> bool:
        """
        Download an object to a local file.
        
        Args:
            object_name: Name of the object in storage
            file_path: Path to save the downloaded file
            bucket_name: Name of the bucket
            
        Returns:
            bool: True if download was successful
        """
        try:
            if self.client_type == 'ibm_cos':
                # IBM COS
                self.client.Object(bucket_name, object_name).download_file(file_path)
            else:
                # MinIO
                self.client.fget_object(bucket_name, object_name, file_path)
                
            logger.info(f"Object {bucket_name}/{object_name} downloaded to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download object {bucket_name}/{object_name} to {file_path}: {str(e)}")
            raise
    
    def download_bytes(
        self,
        object_name: str,
        bucket_name: str = DEFAULT_BUCKET
    ) -> bytes:
        """
        Download an object as bytes.
        
        Args:
            object_name: Name of the object in storage
            bucket_name: Name of the bucket
            
        Returns:
            bytes: The object data
        """
        try:
            if self.client_type == 'ibm_cos':
                # IBM COS
                response = self.client.Object(bucket_name, object_name).get()
                data = response['Body'].read()
            else:
                # MinIO
                response = self.client.get_object(bucket_name, object_name)
                data = response.read()
                response.close()
                response.release_conn()
                
            logger.info(f"Object {bucket_name}/{object_name} downloaded as bytes")
            return data
        except Exception as e:
            logger.error(f"Failed to download object {bucket_name}/{object_name} as bytes: {str(e)}")
            raise
    
    def delete_object(
        self,
        object_name: str,
        bucket_name: str = DEFAULT_BUCKET
    ) -> bool:
        """
        Delete an object from storage.
        
        Args:
            object_name: Name of the object in storage
            bucket_name: Name of the bucket
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            if self.client_type == 'ibm_cos':
                # IBM COS
                self.client.Object(bucket_name, object_name).delete()
            else:
                # MinIO
                self.client.remove_object(bucket_name, object_name)
                
            logger.info(f"Object {bucket_name}/{object_name} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete object {bucket_name}/{object_name}: {str(e)}")
            raise
    
    def list_objects(
        self,
        prefix: str = "",
        bucket_name: str = DEFAULT_BUCKET
    ) -> List[Dict[str, Any]]:
        """
        List objects in a bucket with optional prefix.
        
        Args:
            prefix: Prefix to filter objects
            bucket_name: Name of the bucket
            
        Returns:
            List[Dict]: List of object metadata
        """
        try:
            objects = []
            
            if self.client_type == 'ibm_cos':
                # IBM COS
                for obj in self.client.Bucket(bucket_name).objects.filter(Prefix=prefix):
                    objects.append({
                        'name': obj.key,
                        'size': obj.size,
                        'last_modified': obj.last_modified
                    })
            else:
                # MinIO
                for obj in self.client.list_objects(bucket_name, prefix=prefix, recursive=True):
                    objects.append({
                        'name': obj.object_name,
                        'size': obj.size,
                        'last_modified': obj.last_modified
                    })
                    
            return objects
        except Exception as e:
            logger.error(f"Failed to list objects in bucket {bucket_name} with prefix {prefix}: {str(e)}")
            raise
    
    def get_object_metadata(
        self,
        object_name: str,
        bucket_name: str = DEFAULT_BUCKET
    ) -> Dict[str, Any]:
        """
        Get metadata for an object.
        
        Args:
            object_name: Name of the object in storage
            bucket_name: Name of the bucket
            
        Returns:
            Dict[str, Any]: Object metadata
        """
        try:
            if self.client_type == 'ibm_cos':
                # IBM COS
                obj = self.client.Object(bucket_name, object_name)
                response = obj.get()
                
                metadata = {
                    'size': response['ContentLength'],
                    'last_modified': response['LastModified'],
                    'content_type': response.get('ContentType', 'application/octet-stream'),
                    'metadata': response.get('Metadata', {})
                }
            else:
                # MinIO
                stat = self.client.stat_object(bucket_name, object_name)
                
                metadata = {
                    'size': stat.size,
                    'last_modified': stat.last_modified,
                    'content_type': stat.content_type,
                    'metadata': stat.metadata
                }
                
            return metadata
        except Exception as e:
            logger.error(f"Failed to get metadata for object {bucket_name}/{object_name}: {str(e)}")
            raise
    
    def get_presigned_url(
        self,
        object_name: str,
        bucket_name: str = DEFAULT_BUCKET,
        expiration: int = 3600,
        http_method: str = 'GET'
    ) -> str:
        """
        Generate a presigned URL for object access.
        
        Args:
            object_name: Name of the object in storage
            bucket_name: Name of the bucket
            expiration: URL expiration time in seconds
            http_method: HTTP method ('GET', 'PUT')
            
        Returns:
            str: Presigned URL
        """
        try:
            if self.client_type == 'ibm_cos':
                # IBM COS - Requires boto3 client
                if not self.boto_client:
                    raise ValueError("IBM COS client not properly initialized for presigned URLs")
                    
                url = self.boto_client.generate_presigned_url(
                    ClientMethod=f'{http_method.lower()}_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': object_name
                    },
                    ExpiresIn=expiration
                )
            else:
                # MinIO
                if http_method.upper() == 'GET':
                    url = self.client.presigned_get_object(bucket_name, object_name, expires=timedelta(seconds=expiration))
                elif http_method.upper() == 'PUT':
                    url = self.client.presigned_put_object(bucket_name, object_name, expires=timedelta(seconds=expiration))
                else:
                    raise ValueError(f"Unsupported HTTP method: {http_method}")
                    
            logger.info(f"Generated presigned URL for {bucket_name}/{object_name} with method {http_method}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {bucket_name}/{object_name}: {str(e)}")
            raise

    def copy_object(
        self,
        source_bucket: str,
        source_object: str,
        dest_bucket: str,
        dest_object: str
    ) -> bool:
        """
        Copy an object from one location to another.
        
        Args:
            source_bucket: Source bucket name
            source_object: Source object name
            dest_bucket: Destination bucket name
            dest_object: Destination object name
            
        Returns:
            bool: True if copy was successful
        """
        try:
            # Ensure destination bucket exists
            if not self.bucket_exists(dest_bucket):
                self.create_bucket(dest_bucket)
                
            if self.client_type == 'ibm_cos':
                # IBM COS
                copy_source = {
                    'Bucket': source_bucket,
                    'Key': source_object
                }
                self.client.Object(dest_bucket, dest_object).copy(copy_source)
            else:
                # MinIO
                # MinIO requires downloading and re-uploading
                data = self.download_bytes(source_object, source_bucket)
                
                # Get source metadata to preserve it
                try:
                    metadata = self.get_object_metadata(source_object, source_bucket).get('metadata', {})
                    content_type = self.get_object_metadata(source_object, source_bucket).get('content_type')
                except:
                    metadata = {}
                    content_type = None
                    
                # Upload to destination
                self.upload_bytes(data, dest_object, dest_bucket, metadata, content_type)
                
            logger.info(f"Copied object from {source_bucket}/{source_object} to {dest_bucket}/{dest_object}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy object from {source_bucket}/{source_object} to {dest_bucket}/{dest_object}: {str(e)}")
            raise
    
    def is_object_storage_healthy(self) -> bool:
        """
        Check if object storage is healthy.
        
        Returns:
            bool: True if object storage is healthy
        """
        try:
            # Create a test bucket if it doesn't exist
            test_bucket = f"{DEFAULT_BUCKET}-health-check"
            self.create_bucket(test_bucket)
            
            # Create a test object
            test_object = "health-check.txt"
            test_data = b"Object storage health check"
            
            # Upload test object
            self.upload_bytes(test_data, test_object, test_bucket)
            
            # Download and verify test object
            downloaded_data = self.download_bytes(test_object, test_bucket)
            if downloaded_data != test_data:
                logger.error(f"Health check failed: Data mismatch")
                return False
                
            # Delete test object
            self.delete_object(test_object, test_bucket)
            
            logger.info("Object storage health check passed")
            return True
        except Exception as e:
            logger.error(f"Object storage health check failed: {str(e)}")
            return False


# Initialize the object storage client as a global object
_obj_storage = ObjectStorageClient()


def upload_file_to_storage(
    file_path: str,
    object_name: str = None,
    bucket_name: str = DEFAULT_BUCKET,
    metadata: Dict[str, str] = None
) -> str:
    """
    Upload a file to object storage.
    
    Args:
        file_path: Path to the local file
        object_name: Name to give the object in storage (default: basename of file_path)
        bucket_name: Name of the bucket
        metadata: Optional metadata dict
        
    Returns:
        str: Object name in storage
    """
    if not object_name:
        object_name = os.path.basename(file_path)
        
    _obj_storage.upload_file(file_path, object_name, bucket_name, metadata)
    return object_name


def upload_data_to_storage(
    data: bytes,
    object_name: str,
    bucket_name: str = DEFAULT_BUCKET,
    metadata: Dict[str, str] = None,
    content_type: str = None
) -> str:
    """
    Upload bytes data to object storage.
    
    Args:
        data: Bytes to upload
        object_name: Name to give the object in storage
        bucket_name: Name of the bucket
        metadata: Optional metadata dict
        content_type: Optional content type
        
    Returns:
        str: Object name in storage
    """
    _obj_storage.upload_bytes(data, object_name, bucket_name, metadata, content_type)
    return object_name


def download_file_from_storage(
    object_name: str,
    file_path: str,
    bucket_name: str = DEFAULT_BUCKET
) -> bool:
    """
    Download an object from storage to a local file.
    
    Args:
        object_name: Name of the object in storage
        file_path: Path to save the downloaded file
        bucket_name: Name of the bucket
        
    Returns:
        bool: True if download was successful
    """
    return _obj_storage.download_file(object_name, file_path, bucket_name)


def download_data_from_storage(
    object_name: str,
    bucket_name: str = DEFAULT_BUCKET
) -> bytes:
    """
    Download an object as bytes.
    
    Args:
        object_name: Name of the object in storage
        bucket_name: Name of the bucket
        
    Returns:
        bytes: The object data
    """
    return _obj_storage.download_bytes(object_name, bucket_name)


def delete_from_storage(
    object_name: str,
    bucket_name: str = DEFAULT_BUCKET
) -> bool:
    """
    Delete an object from storage.
    
    Args:
        object_name: Name of the object in storage
        bucket_name: Name of the bucket
        
    Returns:
        bool: True if deletion was successful
    """
    return _obj_storage.delete_object(object_name, bucket_name)


def list_storage_objects(
    prefix: str = "",
    bucket_name: str = DEFAULT_BUCKET
) -> List[Dict[str, Any]]:
    """
    List objects in storage with optional prefix filter.
    
    Args:
        prefix: Prefix to filter objects
        bucket_name: Name of the bucket
        
    Returns:
        List[Dict]: List of object metadata
    """
    return _obj_storage.list_objects(prefix, bucket_name)


def get_storage_object_url(
    object_name: str,
    bucket_name: str = DEFAULT_BUCKET,
    expiration: int = 3600
) -> str:
    """
    Generate a presigned URL for object access.
    
    Args:
        object_name: Name of the object in storage
        bucket_name: Name of the bucket
        expiration: URL expiration time in seconds
        
    Returns:
        str: Presigned URL
    """
    return _obj_storage.get_presigned_url(object_name, bucket_name, expiration)


def is_storage_healthy() -> bool:
    """
    Check if object storage is healthy.
    
    Returns:
        bool: True if object storage is healthy
    """
    return _obj_storage.is_object_storage_healthy()


def create_backup(
    source_path: str,
    backup_name: str = None,
    metadata: Dict[str, str] = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Create a backup of a file or directory in object storage.
    
    Args:
        source_path: Path to the file or directory to backup
        backup_name: Optional name for the backup (default: timestamped basename)
        metadata: Optional metadata for the backup
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the backup in storage
    """
    import tempfile
    import shutil
    import zipfile
    
    if not backup_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = os.path.basename(source_path)
        backup_name = f"{basename}_{timestamp}.zip"
    
    # Ensure backup name has .zip extension
    if not backup_name.endswith('.zip'):
        backup_name += '.zip'
    
    # Create metadata if not provided
    if not metadata:
        metadata = {
            'source_path': source_path,
            'created_at': datetime.now().isoformat(),
            'backup_type': 'file' if os.path.isfile(source_path) else 'directory'
        }
    
    # Create temporary zip file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isfile(source_path):
                # Add single file to zip
                zipf.write(source_path, os.path.basename(source_path))
            else:
                # Add directory contents to zip
                for root, _, files in os.walk(source_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                        zipf.write(file_path, arcname)
        
        # Upload to object storage
        upload_file_to_storage(
            file_path=temp_path,
            object_name=backup_name,
            bucket_name=bucket_name,
            metadata=metadata
        )
        
        logger.info(f"Created backup of {source_path} as {backup_name} in bucket {bucket_name}")
        return backup_name
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {temp_path}: {str(e)}")


def restore_backup(
    backup_name: str,
    destination_path: str,
    bucket_name: str = DEFAULT_BUCKET
) -> bool:
    """
    Restore a backup from object storage.
    
    Args:
        backup_name: Name of the backup object in storage
        destination_path: Path where to restore the backup
        bucket_name: Name of the bucket
        
    Returns:
        bool: True if restore was successful
    """
    import tempfile
    import zipfile
    
    # Create temporary file for the backup
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Download backup from object storage
        download_file_from_storage(
            object_name=backup_name,
            file_path=temp_path,
            bucket_name=bucket_name
        )
        
        # Ensure destination directory exists
        os.makedirs(destination_path, exist_ok=True)
        
        # Extract files from backup
        with zipfile.ZipFile(temp_path, 'r') as zipf:
            zipf.extractall(destination_path)
        
        logger.info(f"Restored backup {backup_name} to {destination_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to restore backup {backup_name}: {str(e)}")
        raise
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {temp_path}: {str(e)}")

# End of Part 3: Object Storage Framework

# ------------- Part 4: Test Case & Requirements Management -------------

def store_test_case_file(
    test_case_data: Dict[str, Any],
    format_type: str = 'excel',
    file_name: str = None,
    bucket_name: str = DEFAULT_BUCKET,
    version: str = '1.0'
) -> str:
    """
    Store test case data in object storage.
    
    Args:
        test_case_data: Dictionary containing test case data
        format_type: Format of the test case ('excel', 'json', 'xml')
        file_name: Optional file name (default: generates a name based on test case ID)
        bucket_name: Name of the bucket
        version: Version of the test case
        
    Returns:
        str: Object name of the stored test case file
    """
    test_case_id = test_case_data.get('id', str(int(time.time())))
    
    if not file_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"test_case_{test_case_id}_{timestamp}.json"
    
    # Add metadata
    test_case_data['metadata'] = {
        'version': version,
        'created_at': datetime.now().isoformat(),
        'format': format_type
    }
    
    # Convert test case data to JSON
    json_data = json.dumps(test_case_data, indent=2)
    
    # Store JSON in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'test-case',
        'test-case-id': test_case_id,
        'version': version,
        'format': format_type
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Also store reference in database for quick lookup
    query = """
    INSERT INTO test_cases (id, name, description, version, storage_path, format, status, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id, version) 
    DO UPDATE SET 
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        storage_path = EXCLUDED.storage_path,
        format = EXCLUDED.format,
        status = EXCLUDED.status,
        updated_at = NOW()
    """
    
    update_database(
        query=query,
        params=(
            test_case_id,
            test_case_data.get('name', f"Test Case {test_case_id}"),
            test_case_data.get('description', ''),
            version,
            f"{bucket_name}/{file_name}",
            format_type,
            test_case_data.get('status', 'active'),
            datetime.now()
        )
    )
    
    logger.info(f"Test case {test_case_id} stored as {file_name} in bucket {bucket_name}")
    return file_name


def get_test_case_by_id(
    test_case_id: str,
    version: str = None
) -> Dict[str, Any]:
    """
    Retrieve a test case by ID and optionally version.
    
    Args:
        test_case_id: ID of the test case
        version: Optional version (default: latest version)
        
    Returns:
        Dict: Test case data
    """
    if version:
        query = """
        SELECT id, name, description, version, storage_path, format, status, created_at, updated_at
        FROM test_cases
        WHERE id = %s AND version = %s
        """
        params = (test_case_id, version)
    else:
        query = """
        SELECT id, name, description, version, storage_path, format, status, created_at, updated_at
        FROM test_cases
        WHERE id = %s
        ORDER BY version DESC
        LIMIT 1
        """
        params = (test_case_id,)
    
    result = query_database(
        query=query,
        params=params,
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Test case {test_case_id} not found")
        raise ValueError(f"Test case {test_case_id} not found")
    
    # Get the full test case data from object storage
    storage_path = result['storage_path']
    bucket_name, object_name = storage_path.split('/', 1)
    
    data_bytes = download_data_from_storage(
        object_name=object_name,
        bucket_name=bucket_name
    )
    
    # Parse JSON
    test_case_data = json.loads(data_bytes.decode('utf-8'))
    
    # Add database metadata
    test_case_data['db_metadata'] = {
        'id': result['id'],
        'name': result['name'],
        'description': result['description'],
        'version': result['version'],
        'format': result['format'],
        'status': result['status'],
        'created_at': result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at'],
        'updated_at': result['updated_at'].isoformat() if isinstance(result['updated_at'], datetime) else result['updated_at']
    }
    
    logger.info(f"Retrieved test case {test_case_id} (version: {result['version']})")
    return test_case_data


def get_test_cases(
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    search_term: str = None
) -> List[Dict[str, Any]]:
    """
    Retrieve test cases with optional filtering.
    
    Args:
        status: Optional status filter ('active', 'under_maintenance', 'obsolete')
        limit: Maximum number of test cases to return
        offset: Offset for pagination
        search_term: Optional search term for name/description
        
    Returns:
        List[Dict]: List of test case metadata (not full test case data)
    """
    base_query = """
    SELECT id, name, description, version, storage_path, format, status, created_at, updated_at
    FROM test_cases
    WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if status:
        base_query += " AND status = %s"
        params.append(status)
    
    if search_term:
        base_query += " AND (name ILIKE %s OR description ILIKE %s)"
        search_pattern = f"%{search_term}%"
        params.append(search_pattern)
        params.append(search_pattern)
    
    # Add sorting and pagination
    base_query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
    params.append(limit)
    params.append(offset)
    
    results = query_database(
        query=base_query,
        params=params
    )
    
    status_filter = f" with status '{status}'" if status else ""
    search_filter = f" matching '{search_term}'" if search_term else ""
    logger.info(f"Retrieved {len(results)} test cases{status_filter}{search_filter}")
    return results


def update_test_case_status(
    test_case_id: str,
    status: str,
    version: str = None
) -> bool:
    """
    Update the status of a test case.
    
    Args:
        test_case_id: ID of the test case
        status: New status ('active', 'under_maintenance', 'obsolete')
        version: Optional version (default: all versions)
        
    Returns:
        bool: True if update was successful
    """
    if version:
        query = """
        UPDATE test_cases
        SET status = %s, updated_at = NOW()
        WHERE id = %s AND version = %s
        """
        params = (status, test_case_id, version)
    else:
        query = """
        UPDATE test_cases
        SET status = %s, updated_at = NOW()
        WHERE id = %s
        """
        params = (status, test_case_id)
    
    affected_rows = update_database(
        query=query,
        params=params
    )
    
    if affected_rows == 0:
        logger.warning(f"No test cases were updated for ID {test_case_id}")
        return False
    
    version_info = f" (version: {version})" if version else ""
    logger.info(f"Updated status of test case {test_case_id}{version_info} to '{status}'")
    return True


def create_test_case_version(
    test_case_id: str,
    new_version: str,
    test_case_data: Dict[str, Any] = None,
    base_version: str = None
) -> str:
    """
    Create a new version of a test case.
    
    Args:
        test_case_id: ID of the test case
        new_version: Version string for the new version
        test_case_data: Optional updated test case data
        base_version: Optional base version (default: latest version)
        
    Returns:
        str: Storage path of the new version
    """
    # Get the base test case if data not provided
    if not test_case_data:
        base_test_case = get_test_case_by_id(test_case_id, base_version)
        test_case_data = base_test_case
        
        # Remove db_metadata from the base test case
        if 'db_metadata' in test_case_data:
            del test_case_data['db_metadata']
    
    # Update version in test case data
    if 'metadata' in test_case_data:
        test_case_data['metadata']['version'] = new_version
    else:
        test_case_data['metadata'] = {'version': new_version}
    
    # Store the new version
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"test_case_{test_case_id}_{new_version}_{timestamp}.json"
    
    format_type = test_case_data.get('metadata', {}).get('format', 'json')
    
    # Store the new version
    file_name = store_test_case_file(
        test_case_data=test_case_data,
        format_type=format_type,
        file_name=file_name,
        version=new_version
    )
    
    logger.info(f"Created version {new_version} of test case {test_case_id}")
    
    # Return the storage path
    bucket_name = DEFAULT_BUCKET
    return f"{bucket_name}/{file_name}"


def delete_test_case(
    test_case_id: str,
    version: str = None,
    force: bool = False
) -> bool:
    """
    Delete a test case, either a specific version or all versions.
    
    Args:
        test_case_id: ID of the test case
        version: Optional version (default: all versions)
        force: If True, physically delete from storage, otherwise just mark as obsolete
        
    Returns:
        bool: True if deletion was successful
    """
    if not force:
        # Just mark as obsolete
        return update_test_case_status(test_case_id, 'obsolete', version)
    
    # Physical deletion
    if version:
        query = """
        SELECT storage_path
        FROM test_cases
        WHERE id = %s AND version = %s
        """
        params = (test_case_id, version)
    else:
        query = """
        SELECT storage_path
        FROM test_cases
        WHERE id = %s
        """
        params = (test_case_id,)
    
    # Get storage paths for all matching test cases
    results = query_database(
        query=query,
        params=params
    )
    
    if not results:
        logger.warning(f"No test cases found for ID {test_case_id}")
        return False
    
    # Delete files from storage
    for result in results:
        storage_path = result['storage_path']
        bucket_name, object_name = storage_path.split('/', 1)
        
        try:
            delete_from_storage(
                object_name=object_name,
                bucket_name=bucket_name
            )
        except Exception as e:
            logger.error(f"Failed to delete test case file {storage_path}: {str(e)}")
    
    # Delete database records
    if version:
        delete_query = """
        DELETE FROM test_cases
        WHERE id = %s AND version = %s
        """
        delete_params = (test_case_id, version)
    else:
        delete_query = """
        DELETE FROM test_cases
        WHERE id = %s
        """
        delete_params = (test_case_id,)
    
    affected_rows = update_database(
        query=delete_query,
        params=delete_params
    )
    
    version_info = f" (version: {version})" if version else ""
    logger.info(f"Physically deleted test case {test_case_id}{version_info}")
    return affected_rows > 0


def store_requirement(
    requirement_data: Dict[str, Any],
    source: str = 'manual',
    source_id: str = None,
    file_name: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store a requirement in the database and optionally in object storage.
    
    Args:
        requirement_data: Dictionary containing requirement data
        source: Source of the requirement ('jira', 'file', 'manual')
        source_id: ID in source system (e.g., JIRA ticket)
        file_name: Optional file name for storage
        bucket_name: Name of the bucket
        
    Returns:
        str: ID of the stored requirement
    """
    # Generate ID if not provided
    requirement_id = requirement_data.get('id')
    if not requirement_id:
        requirement_id = f"REQ_{generate_unique_id()}"
        requirement_data['id'] = requirement_id
    
    # Store in object storage if content is large
    storage_path = None
    if 'description' in requirement_data and len(requirement_data['description']) > 1000:
        if not file_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"requirement_{requirement_id}_{timestamp}.json"
        
        # Add metadata
        requirement_data['metadata'] = {
            'source': source,
            'source_id': source_id,
            'created_at': datetime.now().isoformat()
        }
        
        # Convert to JSON
        json_data = json.dumps(requirement_data, indent=2)
        
        # Store in object storage
        metadata = {
            'content-type': 'application/json',
            'source': 'watsonx-ipg-testing',
            'type': 'requirement',
            'requirement-id': requirement_id,
            'requirement-source': source,
            'source-id': source_id or ''
        }
        
        upload_data_to_storage(
            data=json_data.encode('utf-8'),
            object_name=file_name,
            bucket_name=bucket_name,
            metadata=metadata,
            content_type='application/json'
        )
        
        storage_path = f"{bucket_name}/{file_name}"
    
    # Store in database
    query = """
    INSERT INTO requirements 
    (id, source, source_id, title, description, status, storage_path, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) 
    DO UPDATE SET 
        source = EXCLUDED.source,
        source_id = EXCLUDED.source_id,
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        status = EXCLUDED.status,
        storage_path = EXCLUDED.storage_path,
        updated_at = NOW()
    """
    
    # Truncate description if it's too long for the database and not stored in object storage
    description = requirement_data.get('description', '')
    if storage_path is None and len(description) > 1000:
        description = description[:997] + '...'
    
    update_database(
        query=query,
        params=(
            requirement_id,
            source,
            source_id,
            requirement_data.get('title', f"Requirement {requirement_id}"),
            description,
            requirement_data.get('status', 'active'),
            storage_path,
            datetime.now()
        )
    )
    
    logger.info(f"Stored requirement {requirement_id} from source {source}")
    return requirement_id


def get_requirement_by_id(requirement_id: str) -> Dict[str, Any]:
    """
    Retrieve a requirement by ID.
    
    Args:
        requirement_id: ID of the requirement
        
    Returns:
        Dict: Requirement data
    """
    query = """
    SELECT id, source, source_id, title, description, status, storage_path, created_at, updated_at
    FROM requirements
    WHERE id = %s
    """
    
    result = query_database(
        query=query,
        params=(requirement_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Requirement {requirement_id} not found")
        raise ValueError(f"Requirement {requirement_id} not found")
    
    # Check if full data is stored in object storage
    storage_path = result['storage_path']
    if storage_path:
        bucket_name, object_name = storage_path.split('/', 1)
        
        data_bytes = download_data_from_storage(
            object_name=object_name,
            bucket_name=bucket_name
        )
        
        # Parse JSON
        requirement_data = json.loads(data_bytes.decode('utf-8'))
    else:
        # Create from database record
        requirement_data = {
            'id': result['id'],
            'title': result['title'],
            'description': result['description'],
            'status': result['status'],
            'metadata': {
                'source': result['source'],
                'source_id': result['source_id'],
                'created_at': result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at']
            }
        }
    
    # Add database metadata
    requirement_data['db_metadata'] = {
        'id': result['id'],
        'source': result['source'],
        'source_id': result['source_id'],
        'title': result['title'],
        'status': result['status'],
        'created_at': result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at'],
        'updated_at': result['updated_at'].isoformat() if isinstance(result['updated_at'], datetime) else result['updated_at']
    }
    
    logger.info(f"Retrieved requirement {requirement_id}")
    return requirement_data


def get_requirements(
    source: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    search_term: str = None
) -> List[Dict[str, Any]]:
    """
    Retrieve requirements with optional filtering.
    
    Args:
        source: Optional source filter ('jira', 'file', 'manual')
        status: Optional status filter
        limit: Maximum number of requirements to return
        offset: Offset for pagination
        search_term: Optional search term for title/description
        
    Returns:
        List[Dict]: List of requirement metadata
    """
    base_query = """
    SELECT id, source, source_id, title, 
           CASE 
               WHEN storage_path IS NOT NULL THEN 'See storage'
               ELSE description 
           END as description,
           status, storage_path, created_at, updated_at
    FROM requirements
    WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if source:
        base_query += " AND source = %s"
        params.append(source)
    
    if status:
        base_query += " AND status = %s"
        params.append(status)
    
    if search_term:
        base_query += " AND (title ILIKE %s OR description ILIKE %s)"
        search_pattern = f"%{search_term}%"
        params.append(search_pattern)
        params.append(search_pattern)
    
    # Add sorting and pagination
    base_query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
    params.append(limit)
    params.append(offset)
    
    results = query_database(
        query=base_query,
        params=params
    )
    
    source_filter = f" from source '{source}'" if source else ""
    status_filter = f" with status '{status}'" if status else ""
    search_filter = f" matching '{search_term}'" if search_term else ""
    logger.info(f"Retrieved {len(results)} requirements{source_filter}{status_filter}{search_filter}")
    return results


def link_test_case_to_requirement(
    test_case_id: str,
    requirement_id: str,
    test_case_version: str = None
) -> bool:
    """
    Link a test case to a requirement.
    
    Args:
        test_case_id: ID of the test case
        requirement_id: ID of the requirement
        test_case_version: Optional test case version (default: latest version)
        
    Returns:
        bool: True if link was created
    """
    # Get test case version if not provided
    if not test_case_version:
        query = """
        SELECT version
        FROM test_cases
        WHERE id = %s
        ORDER BY version DESC
        LIMIT 1
        """
        
        result = query_database(
            query=query,
            params=(test_case_id,),
            fetch_one=True
        )
        
        if not result:
            logger.error(f"Test case {test_case_id} not found")
            raise ValueError(f"Test case {test_case_id} not found")
        
        test_case_version = result['version']
    
    # Check if requirement exists
    query = """
    SELECT id
    FROM requirements
    WHERE id = %s
    """
    
    result = query_database(
        query=query,
        params=(requirement_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Requirement {requirement_id} not found")
        raise ValueError(f"Requirement {requirement_id} not found")
    
    # Create link
    query = """
    INSERT INTO test_case_requirements 
    (test_case_id, test_case_version, requirement_id, created_at)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (test_case_id, test_case_version, requirement_id) 
    DO NOTHING
    """
    
    affected_rows = update_database(
        query=query,
        params=(
            test_case_id,
            test_case_version,
            requirement_id,
            datetime.now()
        )
    )
    
    if affected_rows == 0:
        logger.info(f"Link between test case {test_case_id} and requirement {requirement_id} already exists")
    else:
        logger.info(f"Linked test case {test_case_id} (version: {test_case_version}) to requirement {requirement_id}")
    
    return True


def unlink_test_case_from_requirement(
    test_case_id: str,
    requirement_id: str,
    test_case_version: str = None
) -> bool:
    """
    Remove a link between a test case and a requirement.
    
    Args:
        test_case_id: ID of the test case
        requirement_id: ID of the requirement
        test_case_version: Optional test case version (default: all versions)
        
    Returns:
        bool: True if link was removed
    """
    if test_case_version:
        query = """
        DELETE FROM test_case_requirements
        WHERE test_case_id = %s AND test_case_version = %s AND requirement_id = %s
        """
        params = (test_case_id, test_case_version, requirement_id)
    else:
        query = """
        DELETE FROM test_case_requirements
        WHERE test_case_id = %s AND requirement_id = %s
        """
        params = (test_case_id, requirement_id)
    
    affected_rows = update_database(
        query=query,
        params=params
    )
    
    version_info = f" (version: {test_case_version})" if test_case_version else " (all versions)"
    if affected_rows == 0:
        logger.warning(f"No link found between test case {test_case_id}{version_info} and requirement {requirement_id}")
        return False
    
    logger.info(f"Unlinked test case {test_case_id}{version_info} from requirement {requirement_id}")
    return True


def get_requirements_for_test_case(
    test_case_id: str,
    test_case_version: str = None
) -> List[Dict[str, Any]]:
    """
    Get requirements linked to a test case.
    
    Args:
        test_case_id: ID of the test case
        test_case_version: Optional test case version (default: latest version)
        
    Returns:
        List[Dict]: List of linked requirements
    """
    if not test_case_version:
        query = """
        SELECT version
        FROM test_cases
        WHERE id = %s
        ORDER BY version DESC
        LIMIT 1
        """
        
        result = query_database(
            query=query,
            params=(test_case_id,),
            fetch_one=True
        )
        
        if not result:
            logger.error(f"Test case {test_case_id} not found")
            raise ValueError(f"Test case {test_case_id} not found")
        
        test_case_version = result['version']
    
    query = """
    SELECT r.id, r.source, r.source_id, r.title, 
           CASE 
               WHEN r.storage_path IS NOT NULL THEN 'See storage'
               ELSE r.description 
           END as description,
           r.status, r.created_at, r.updated_at
    FROM requirements r
    JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
    WHERE tcr.test_case_id = %s AND tcr.test_case_version = %s
    ORDER BY r.updated_at DESC
    """
    
    results = query_database(
        query=query,
        params=(test_case_id, test_case_version)
    )
    
    logger.info(f"Retrieved {len(results)} requirements for test case {test_case_id} (version: {test_case_version})")
    return results


def get_test_cases_for_requirement(
    requirement_id: str,
    status: str = None
) -> List[Dict[str, Any]]:
    """
    Get test cases linked to a requirement.
    
    Args:
        requirement_id: ID of the requirement
        status: Optional test case status filter
        
    Returns:
        List[Dict]: List of linked test cases
    """
    base_query = """
    SELECT tc.id, tc.name, tc.description, tc.version, tc.format, tc.status, tc.created_at, tc.updated_at
    FROM test_cases tc
    JOIN test_case_requirements tcr ON tc.id = tcr.test_case_id AND tc.version = tcr.test_case_version
    WHERE tcr.requirement_id = %s
    """
    
    params = [requirement_id]
    
    if status:
        base_query += " AND tc.status = %s"
        params.append(status)
    
    base_query += " ORDER BY tc.updated_at DESC"
    
    results = query_database(
        query=base_query,
        params=params
    )
    
    status_filter = f" with status '{status}'" if status else ""
    logger.info(f"Retrieved {len(results)} test cases for requirement {requirement_id}{status_filter}")
    return results


def get_requirements_coverage_statistics() -> Dict[str, Any]:
    """
    Get statistics about requirements coverage by test cases.
    
    Returns:
        Dict: Statistics about requirements coverage
    """
    # Base query for requirements
    req_query = """
    SELECT COUNT(*) as total_requirements,
           COUNT(CASE WHEN status = 'active' THEN 1 END) as active_requirements,
           COUNT(CASE WHEN status = 'deprecated' THEN 1 END) as deprecated_requirements,
           COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_requirements
    FROM requirements
    """
    
    # Execute query
    req_stats = query_database(req_query, fetch_one=True)
    
    # Query for covered requirements
    covered_query = """
    SELECT COUNT(DISTINCT requirement_id) as covered_requirements
    FROM test_case_requirements tcr
    JOIN test_cases tc ON tcr.test_case_id = tc.id AND tcr.test_case_version = tc.version
    WHERE tc.status = 'active'
    """
    
    # Execute query
    covered_stats = query_database(covered_query, fetch_one=True)
    
    # Combine stats
    stats = {
        'total_requirements': req_stats['total_requirements'],
        'active_requirements': req_stats['active_requirements'],
        'deprecated_requirements': req_stats['deprecated_requirements'],
        'completed_requirements': req_stats['completed_requirements'],
        'covered_requirements': covered_stats['covered_requirements']
    }
    
    # Calculate coverage percentage
    if stats['active_requirements'] > 0:
        stats['coverage_percentage'] = (stats['covered_requirements'] / stats['active_requirements']) * 100
    else:
        stats['coverage_percentage'] = 0
    
    # Get requirements with most test cases
    most_test_cases_query = """
    SELECT r.id, r.title, COUNT(tcr.test_case_id) as test_case_count
    FROM requirements r
    JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
    JOIN test_cases tc ON tcr.test_case_id = tc.id AND tcr.test_case_version = tc.version
    WHERE tc.status = 'active'
    GROUP BY r.id, r.title
    ORDER BY test_case_count DESC
    LIMIT 10
    """
    
    # Execute query
    most_test_cases = query_database(most_test_cases_query)
    
    # Add to statistics
    stats['most_test_cases'] = most_test_cases
    
    # Get requirements with no test cases
    no_test_cases_query = """
    SELECT r.id, r.title, r.status
    FROM requirements r
    LEFT JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
    WHERE tcr.requirement_id IS NULL
    AND r.status = 'active'
    LIMIT 100
    """
    
    # Execute query
    no_test_cases = query_database(no_test_cases_query)
    
    # Add to statistics
    stats['no_test_cases'] = no_test_cases
    
    logger.info(f"Retrieved requirements coverage statistics: {stats['coverage_percentage']:.2f}% covered")
    return stats


def get_test_case_versions(test_case_id: str) -> List[Dict[str, Any]]:
    """
    Get all versions of a test case.
    
    Args:
        test_case_id: ID of the test case
        
    Returns:
        List[Dict]: List of test case versions
    """
    query = """
    SELECT id, name, description, version, format, status, created_at, updated_at
    FROM test_cases
    WHERE id = %s
    ORDER BY version DESC
    """
    
    results = query_database(
        query=query,
        params=(test_case_id,)
    )
    
    logger.info(f"Retrieved {len(results)} versions for test case {test_case_id}")
    return results


def compare_test_case_versions(
    test_case_id: str,
    version1: str,
    version2: str
) -> Dict[str, Any]:
    """
    Compare two versions of a test case.
    
    Args:
        test_case_id: ID of the test case
        version1: First version to compare
        version2: Second version to compare
        
    Returns:
        Dict: Comparison results
    """
    # Get both versions
    test_case1 = get_test_case_by_id(test_case_id, version1)
    test_case2 = get_test_case_by_id(test_case_id, version2)
    
    # Compare basic metadata
    comparison = {
        'test_case_id': test_case_id,
        'version1': version1,
        'version2': version2,
        'differences': {}
    }
    
    # Compare name and description
    if test_case1.get('name') != test_case2.get('name'):
        comparison['differences']['name'] = {
            'version1': test_case1.get('name'),
            'version2': test_case2.get('name')
        }
    
    if test_case1.get('description') != test_case2.get('description'):
        comparison['differences']['description'] = {
            'version1': test_case1.get('description'),
            'version2': test_case2.get('description')
        }
    
    # Compare steps if present
    if 'steps' in test_case1 and 'steps' in test_case2:
        steps1 = test_case1['steps']
        steps2 = test_case2['steps']
        
        if len(steps1) != len(steps2):
            comparison['differences']['steps_count'] = {
                'version1': len(steps1),
                'version2': len(steps2)
            }
        
        # Compare each step
        step_differences = []
        for i in range(min(len(steps1), len(steps2))):
            step1 = steps1[i]
            step2 = steps2[i]
            
            step_diff = {}
            for key in set(list(step1.keys()) + list(step2.keys())):
                if key not in step1:
                    step_diff[key] = {'added_in_version2': step2[key]}
                elif key not in step2:
                    step_diff[key] = {'removed_in_version2': step1[key]}
                elif step1[key] != step2[key]:
                    step_diff[key] = {
                        'version1': step1[key],
                        'version2': step2[key]
                    }
            
            if step_diff:
                step_differences.append({
                    'step_index': i,
                    'differences': step_diff
                })
        
        # Add any additional steps
        if len(steps1) < len(steps2):
            for i in range(len(steps1), len(steps2)):
                step_differences.append({
                    'step_index': i,
                    'differences': {'entire_step': {'added_in_version2': steps2[i]}}
                })
        elif len(steps1) > len(steps2):
            for i in range(len(steps2), len(steps1)):
                step_differences.append({
                    'step_index': i,
                    'differences': {'entire_step': {'removed_in_version2': steps1[i]}}
                })
        
        if step_differences:
            comparison['differences']['steps'] = step_differences
    
    # Compare expected results if present
    if 'expected_results' in test_case1 and 'expected_results' in test_case2:
        if test_case1['expected_results'] != test_case2['expected_results']:
            comparison['differences']['expected_results'] = {
                'version1': test_case1['expected_results'],
                'version2': test_case2['expected_results']
            }
    
    # Add creation/modification dates
    comparison['version1_created'] = test_case1.get('db_metadata', {}).get('created_at')
    comparison['version2_created'] = test_case2.get('db_metadata', {}).get('created_at')
    
    logger.info(f"Compared versions {version1} and {version2} of test case {test_case_id}")
    return comparison


def import_test_cases_from_excel(
    file_path: str,
    source: str = 'import'
) -> Dict[str, Any]:
    """
    Import test cases from an Excel file.
    
    Args:
        file_path: Path to the Excel file
        source: Source identifier for the import
        
    Returns:
        Dict: Import statistics
    """
    try:
        import pandas as pd
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Validate required columns
        required_columns = ['ID', 'Name', 'Description']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in Excel file")
        
        # Import statistics
        stats = {
            'total': len(df),
            'imported': 0,
            'updated': 0,
            'failed': 0,
            'failed_ids': []
        }
        
        # Process each row
        for _, row in df.iterrows():
            try:
                test_case_id = row['ID']
                test_case_data = {
                    'id': test_case_id,
                    'name': row['Name'],
                    'description': row['Description'],
                    'status': 'active'
                }
                
                # Add any additional columns as properties
                for col in df.columns:
                    if col not in ['ID', 'Name', 'Description'] and not pd.isna(row[col]):
                        test_case_data[col.lower()] = row[col]
                
                # Check if test case exists
                existing = False
                try:
                    get_test_case_by_id(test_case_id)
                    existing = True
                except ValueError:
                    pass
                
                # Store test case
                version = '1.0' if not existing else f"1.{int(time.time())}"
                store_test_case_file(
                    test_case_data=test_case_data,
                    format_type='excel',
                    version=version
                )
                
                if existing:
                    stats['updated'] += 1
                else:
                    stats['imported'] += 1
                
            except Exception as e:
                logger.error(f"Failed to import test case: {str(e)}")
                stats['failed'] += 1
                stats['failed_ids'].append(row.get('ID', 'Unknown'))
        
        logger.info(f"Imported {stats['imported']} test cases, updated {stats['updated']}, failed {stats['failed']}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to import test cases from Excel: {str(e)}")
        raise


def export_test_cases_to_excel(
    test_case_ids: List[str] = None,
    status: str = 'active',
    output_file: str = None
) -> str:
    """
    Export test cases to an Excel file.
    
    Args:
        test_case_ids: Optional list of test case IDs to export (default: all matching status)
        status: Status filter for test cases when test_case_ids not provided
        output_file: Path for the output Excel file (default: generate temp file)
        
    Returns:
        str: Path to the created Excel file
    """
    try:
        import pandas as pd
        from tempfile import NamedTemporaryFile
        
        # Get test cases
        test_cases = []
        
        if test_case_ids:
            for test_case_id in test_case_ids:
                try:
                    test_case = get_test_case_by_id(test_case_id)
                    test_cases.append(test_case)
                except ValueError:
                    logger.warning(f"Test case {test_case_id} not found")
        else:
            # Get all test cases with matching status
            results = get_test_cases(status=status, limit=1000)
            for result in results:
                try:
                    test_case = get_test_case_by_id(result['id'])
                    test_cases.append(test_case)
                except ValueError:
                    logger.warning(f"Test case {result['id']} not found")
        
        # Create DataFrame
        rows = []
        columns = ['ID', 'Name', 'Description', 'Version', 'Status', 'Created Date']
        
        for test_case in test_cases:
            metadata = test_case.get('db_metadata', {})
            row = {
                'ID': metadata.get('id', test_case.get('id')),
                'Name': metadata.get('name', test_case.get('name')),
                'Description': metadata.get('description', test_case.get('description')),
                'Version': metadata.get('version', test_case.get('metadata', {}).get('version')),
                'Status': metadata.get('status', test_case.get('status')),
                'Created Date': metadata.get('created_at', test_case.get('metadata', {}).get('created_at'))
            }
            
            # Add any steps if present
            if 'steps' in test_case:
                for i, step in enumerate(test_case['steps']):
                    row[f'Step {i+1}'] = step.get('description', '')
                    if 'expected_result' in step:
                        row[f'Expected Result {i+1}'] = step['expected_result']
                    
                    # Add new columns to the columns list if needed
                    if f'Step {i+1}' not in columns:
                        columns.append(f'Step {i+1}')
                    if 'expected_result' in step and f'Expected Result {i+1}' not in columns:
                        columns.append(f'Expected Result {i+1}')
            
            rows.append(row)
        
        # Create DataFrame with ordered columns
        df = pd.DataFrame(rows)
        if not df.empty:
            # Reorder columns - ensure core columns come first
            all_columns = [col for col in columns if col in df.columns]
            remaining_columns = [col for col in df.columns if col not in all_columns]
            df = df[all_columns + remaining_columns]
        
        # Create Excel file
        if not output_file:
            with NamedTemporaryFile(suffix='.xlsx', delete=False) as temp:
                output_file = temp.name
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Test Cases')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Test Cases']
            for i, column in enumerate(df.columns):
                max_length = df[column].astype(str).str.len().max()
                max_length = max(max_length, len(column)) + 2
                worksheet.column_dimensions[chr(65 + i)].width = min(max_length, 50)
        
        logger.info(f"Exported {len(rows)} test cases to {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to export test cases to Excel: {str(e)}")
        raise


def analyze_requirements_coverage() -> Dict[str, Any]:
    """
    Analyze requirements coverage and generate statistics and recommendations.
    
    Returns:
        Dict: Analysis results
    """
    # Get basic coverage statistics
    coverage_stats = get_requirements_coverage_statistics()
    
    # Get requirements with no test cases
    uncovered_query = """
    SELECT r.id, r.title, r.source, r.source_id, r.status
    FROM requirements r
    LEFT JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
    WHERE tcr.requirement_id IS NULL
    AND r.status = 'active'
    """
    
    uncovered_requirements = query_database(uncovered_query)
    
    # Get test cases with no requirements
    unlinked_query = """
    SELECT tc.id, tc.name, tc.version, tc.status
    FROM test_cases tc
    LEFT JOIN test_case_requirements tcr ON tc.id = tcr.test_case_id AND tc.version = tcr.test_case_version
    WHERE tcr.test_case_id IS NULL
    AND tc.status = 'active'
    """
    
    unlinked_test_cases = query_database(unlinked_query)
    
    # Get requirements test case count distribution
    distribution_query = """
    SELECT COUNT(tcr.test_case_id) as test_case_count, COUNT(DISTINCT r.id) as requirement_count
    FROM requirements r
    JOIN test_case_requirements tcr ON r.id = tcr.requirement_id
    GROUP BY test_case_count
    ORDER BY test_case_count
    """
    
    distribution = query_database(distribution_query)
    
    # Build analysis results
    analysis = {
        'coverage_percentage': coverage_stats['coverage_percentage'],
        'total_requirements': coverage_stats['total_requirements'],
        'active_requirements': coverage_stats['active_requirements'],
        'covered_requirements': coverage_stats['covered_requirements'],
        'uncovered_requirements': uncovered_requirements,
        'unlinked_test_cases': unlinked_test_cases,
        'coverage_distribution': distribution,
        'recommendations': []
    }
    
    # Generate recommendations
    if len(uncovered_requirements) > 0:
        analysis['recommendations'].append({
            'type': 'uncovered_requirements',
            'description': f"There are {len(uncovered_requirements)} active requirements with no test cases.",
            'action': "Create test cases for these requirements to improve coverage."
        })
    
    if len(unlinked_test_cases) > 0:
        analysis['recommendations'].append({
            'type': 'unlinked_test_cases',
            'description': f"There are {len(unlinked_test_cases)} active test cases not linked to any requirements.",
            'action': "Link these test cases to relevant requirements or review if they are still needed."
        })
    
    if analysis['coverage_percentage'] < 80:
        analysis['recommendations'].append({
            'type': 'low_coverage',
            'description': f"Overall requirements coverage is {analysis['coverage_percentage']:.1f}%, which is below the recommended 80%.",
            'action': "Focus on creating test cases for uncovered requirements to improve overall coverage."
        })
    
    logger.info(f"Completed requirements coverage analysis: {analysis['coverage_percentage']:.1f}% coverage")
    return analysis

# End of Part 4: Test Case & Requirements Management

# ------------- Part 5: Test Execution & Results -------------

def store_test_result(
    test_case_id: str,
    execution_id: str,
    result_data: Dict[str, Any],
    screenshots: List[bytes] = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store test execution results in object storage.
    
    Args:
        test_case_id: ID of the executed test case
        execution_id: Unique execution ID
        result_data: Dictionary containing result data
        screenshots: Optional list of screenshot image data
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored result file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file_name = f"result_{test_case_id}_{execution_id}_{timestamp}.json"
    
    # Add metadata
    result_data['metadata'] = {
        'test_case_id': test_case_id,
        'execution_id': execution_id,
        'timestamp': datetime.now().isoformat(),
        'has_screenshots': bool(screenshots)
    }
    
    # Convert result data to JSON
    json_data = json.dumps(result_data, indent=2)
    
    # Store JSON in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'test-result',
        'test-case-id': test_case_id,
        'execution-id': execution_id
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=result_file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Store screenshots if provided
    screenshot_paths = []
    if screenshots:
        for i, screenshot in enumerate(screenshots):
            screenshot_name = f"screenshot_{test_case_id}_{execution_id}_{timestamp}_{i}.png"
            
            upload_data_to_storage(
                data=screenshot,
                object_name=screenshot_name,
                bucket_name=bucket_name,
                metadata={
                    'content-type': 'image/png',
                    'source': 'watsonx-ipg-testing',
                    'type': 'test-screenshot',
                    'test-case-id': test_case_id,
                    'execution-id': execution_id,
                    'index': str(i)
                },
                content_type='image/png'
            )
            
            screenshot_paths.append(screenshot_name)
    
    # Update database with result summary
    query = """
    INSERT INTO test_executions 
    (execution_id, test_case_id, status, result_path, execution_time, screenshots, executed_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    update_database(
        query=query,
        params=(
            execution_id,
            test_case_id,
            result_data.get('status', 'unknown'),
            f"{bucket_name}/{result_file_name}",
            result_data.get('execution_time', 0),
            json.dumps(screenshot_paths) if screenshot_paths else None,
            datetime.now()
        )
    )
    
    logger.info(f"Test result for test case {test_case_id} (execution {execution_id}) stored as {result_file_name}")
    return result_file_name


def get_test_execution(execution_id: str) -> Dict[str, Any]:
    """
    Retrieve a test execution by ID.
    
    Args:
        execution_id: ID of the test execution
        
    Returns:
        Dict: Test execution data
    """
    query = """
    SELECT execution_id, test_case_id, status, result_path, execution_time, screenshots, executed_at, notes
    FROM test_executions
    WHERE execution_id = %s
    """
    
    result = query_database(
        query=query,
        params=(execution_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Test execution {execution_id} not found")
        raise ValueError(f"Test execution {execution_id} not found")
    
    # Get the full result data from object storage
    storage_path = result['result_path']
    bucket_name, object_name = storage_path.split('/', 1)
    
    data_bytes = download_data_from_storage(
        object_name=object_name,
        bucket_name=bucket_name
    )
    
    # Parse JSON
    execution_data = json.loads(data_bytes.decode('utf-8'))
    
    # Add database metadata
    execution_data['db_metadata'] = {
        'execution_id': result['execution_id'],
        'test_case_id': result['test_case_id'],
        'status': result['status'],
        'execution_time': result['execution_time'],
        'executed_at': result['executed_at'].isoformat() if isinstance(result['executed_at'], datetime) else result['executed_at'],
        'notes': result['notes']
    }
    
    # Add screenshot URLs if available
    if result['screenshots']:
        screenshot_paths = json.loads(result['screenshots'])
        execution_data['screenshots'] = []
        
        for screenshot_path in screenshot_paths:
            screenshot_url = get_storage_object_url(
                object_name=screenshot_path,
                bucket_name=bucket_name,
                expiration=3600  # 1 hour
            )
            execution_data['screenshots'].append({
                'path': screenshot_path,
                'url': screenshot_url
            })
    
    logger.info(f"Retrieved test execution {execution_id}")
    return execution_data


def get_test_executions(
    test_case_id: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    start_date: datetime = None,
    end_date: datetime = None
) -> List[Dict[str, Any]]:
    """
    Retrieve test executions with optional filtering.
    
    Args:
        test_case_id: Optional test case ID filter
        status: Optional status filter
        limit: Maximum number of executions to return
        offset: Offset for pagination
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        List[Dict]: List of test execution metadata
    """
    base_query = """
    SELECT execution_id, test_case_id, status, result_path, execution_time, executed_at, notes
    FROM test_executions
    WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if test_case_id:
        base_query += " AND test_case_id = %s"
        params.append(test_case_id)
    
    if status:
        base_query += " AND status = %s"
        params.append(status)
    
    if start_date:
        base_query += " AND executed_at >= %s"
        params.append(start_date)
    
    if end_date:
        base_query += " AND executed_at <= %s"
        params.append(end_date)
    
    # Add sorting and pagination
    base_query += " ORDER BY executed_at DESC LIMIT %s OFFSET %s"
    params.append(limit)
    params.append(offset)
    
    results = query_database(
        query=base_query,
        params=params
    )
    
    test_case_filter = f" for test case '{test_case_id}'" if test_case_id else ""
    status_filter = f" with status '{status}'" if status else ""
    logger.info(f"Retrieved {len(results)} test executions{test_case_filter}{status_filter}")
    return results


def get_latest_execution(test_case_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest execution for a test case.
    
    Args:
        test_case_id: ID of the test case
        
    Returns:
        Optional[Dict]: Latest execution data or None if no executions
    """
    query = """
    SELECT execution_id, test_case_id, status, result_path, execution_time, executed_at, notes
    FROM test_executions
    WHERE test_case_id = %s
    ORDER BY executed_at DESC
    LIMIT 1
    """
    
    result = query_database(
        query=query,
        params=(test_case_id,),
        fetch_one=True
    )
    
    if not result:
        logger.info(f"No executions found for test case {test_case_id}")
        return None
    
    # Return full execution data
    return get_test_execution(result['execution_id'])


def update_test_execution_notes(
    execution_id: str,
    notes: str
) -> bool:
    """
    Update notes for a test execution.
    
    Args:
        execution_id: ID of the test execution
        notes: Notes to add
        
    Returns:
        bool: True if update was successful
    """
    query = """
    UPDATE test_executions
    SET notes = %s
    WHERE execution_id = %s
    """
    
    affected_rows = update_database(
        query=query,
        params=(notes, execution_id)
    )
    
    if affected_rows == 0:
        logger.warning(f"No test execution found with ID {execution_id}")
        return False
    
    logger.info(f"Updated notes for test execution {execution_id}")
    return True


def store_test_data(
    test_case_id: str,
    data_type: str,
    data: Dict[str, Any],
    file_name: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store test data for a test case.
    
    Args:
        test_case_id: ID of the test case
        data_type: Type of test data ('input', 'expected_output', 'config')
        data: Test data dictionary
        file_name: Optional file name
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored test data
    """
    if not file_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"testdata_{test_case_id}_{data_type}_{timestamp}.json"
    
    # Convert data to JSON
    json_data = json.dumps(data, indent=2)
    
    # Store in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'test-data',
        'test-case-id': test_case_id,
        'data-type': data_type
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Record in database
    query = """
    INSERT INTO test_data 
    (test_case_id, data_type, storage_path, created_at)
    VALUES (%s, %s, %s, %s)
    """
    
    update_database(
        query=query,
        params=(
            test_case_id,
            data_type,
            f"{bucket_name}/{file_name}",
            datetime.now()
        )
    )
    
    logger.info(f"Stored {data_type} test data for test case {test_case_id} as {file_name}")
    return file_name


def get_test_data(
    test_case_id: str,
    data_type: str = None
) -> List[Dict[str, Any]]:
    """
    Get test data for a test case.
    
    Args:
        test_case_id: ID of the test case
        data_type: Optional type filter
        
    Returns:
        List[Dict]: List of test data items
    """
    if data_type:
        query = """
        SELECT id, test_case_id, data_type, storage_path, created_at, updated_at
        FROM test_data
        WHERE test_case_id = %s AND data_type = %s
        ORDER BY created_at DESC
        """
        params = (test_case_id, data_type)
    else:
        query = """
        SELECT id, test_case_id, data_type, storage_path, created_at, updated_at
        FROM test_data
        WHERE test_case_id = %s
        ORDER BY data_type, created_at DESC
        """
        params = (test_case_id,)
    
    results = query_database(
        query=query,
        params=params
    )
    
    data_items = []
    for result in results:
        storage_path = result['storage_path']
        bucket_name, object_name = storage_path.split('/', 1)
        
        try:
            data_bytes = download_data_from_storage(
                object_name=object_name,
                bucket_name=bucket_name
            )
            
            # Parse JSON
            data = json.loads(data_bytes.decode('utf-8'))
            
            # Add metadata
            data_item = {
                'id': result['id'],
                'test_case_id': result['test_case_id'],
                'data_type': result['data_type'],
                'created_at': result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at'],
                'data': data
            }
            
            data_items.append(data_item)
        except Exception as e:
            logger.error(f"Failed to load test data {storage_path}: {str(e)}")
    
    data_type_filter = f" of type '{data_type}'" if data_type else ""
    logger.info(f"Retrieved {len(data_items)} test data items{data_type_filter} for test case {test_case_id}")
    return data_items


def delete_test_data(test_data_id: int) -> bool:
    """
    Delete test data.
    
    Args:
        test_data_id: ID of the test data record
        
    Returns:
        bool: True if deletion was successful
    """
    # Get storage path first
    query = """
    SELECT storage_path
    FROM test_data
    WHERE id = %s
    """
    
    result = query_database(
        query=query,
        params=(test_data_id,),
        fetch_one=True
    )
    
    if not result:
        logger.warning(f"No test data found with ID {test_data_id}")
        return False
    
    # Delete from object storage
    storage_path = result['storage_path']
    bucket_name, object_name = storage_path.split('/', 1)
    
    try:
        delete_from_storage(
            object_name=object_name,
            bucket_name=bucket_name
        )
    except Exception as e:
        logger.error(f"Failed to delete test data file {storage_path}: {str(e)}")
    
    # Delete database record
    delete_query = """
    DELETE FROM test_data
    WHERE id = %s
    """
    
    affected_rows = update_database(
        query=delete_query,
        params=(test_data_id,)
    )
    
    logger.info(f"Deleted test data with ID {test_data_id}")
    return affected_rows > 0


def start_test_execution(
    test_case_id: str,
    execution_id: str = None,
    environment: str = 'default',
    input_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Start a new test execution.
    
    Args:
        test_case_id: ID of the test case to execute
        execution_id: Optional execution ID (default: generate new ID)
        environment: Environment name for the execution
        input_data: Optional input data for the test
        
    Returns:
        Dict: Execution details
    """
    # Generate execution ID if not provided
    if not execution_id:
        execution_id = f"exec_{generate_unique_id()}"
    
    # Get test case
    test_case = get_test_case_by_id(test_case_id)
    
    # Store input data if provided
    if input_data:
        store_test_data(
            test_case_id=test_case_id,
            data_type='execution_input',
            data={
                'execution_id': execution_id,
                'environment': environment,
                'data': input_data
            }
        )
    
    # Create execution record
    start_time = datetime.now()
    
    # Create metrics record
    metrics_query = """
    INSERT INTO execution_metrics
    (execution_id, test_case_id, start_time, status, environment, executed_by)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    update_database(
        query=metrics_query,
        params=(
            execution_id,
            test_case_id,
            start_time,
            'running',
            environment,
            os.environ.get('USER', 'watsonx-ipg-testing')
        )
    )
    
    # Create initial execution result
    initial_result = {
        'status': 'running',
        'start_time': start_time.isoformat(),
        'test_case_id': test_case_id,
        'test_case_name': test_case.get('name', ''),
        'environment': environment,
        'execution_steps': []
    }
    
    store_test_result(
        test_case_id=test_case_id,
        execution_id=execution_id,
        result_data=initial_result
    )
    
    logger.info(f"Started test execution {execution_id} for test case {test_case_id}")
    
    return {
        'execution_id': execution_id,
        'test_case_id': test_case_id,
        'start_time': start_time.isoformat(),
        'status': 'running',
        'environment': environment
    }


def update_test_execution_step(
    execution_id: str,
    step_index: int,
    status: str,
    output: str = None,
    screenshot: bytes = None
) -> bool:
    """
    Update a step in an ongoing test execution.
    
    Args:
        execution_id: ID of the test execution
        step_index: Index of the step to update
        status: Status of the step ('passed', 'failed', 'skipped')
        output: Optional step output
        screenshot: Optional screenshot of the step
        
    Returns:
        bool: True if update was successful
    """
    # Get current execution
    try:
        execution = get_test_execution(execution_id)
    except ValueError:
        logger.error(f"Execution {execution_id} not found")
        return False
    
    # Update step in execution data
    steps = execution.get('execution_steps', [])
    
    # Add empty steps if needed
    while len(steps) <= step_index:
        steps.append({
            'step_index': len(steps),
            'status': 'pending',
            'start_time': datetime.now().isoformat()
        })
    
    # Update the step
    steps[step_index].update({
        'status': status,
        'end_time': datetime.now().isoformat()
    })
    
    if output:
        steps[step_index]['output'] = output
    
    execution['execution_steps'] = steps
    
    # Store updated result
    screenshots = [screenshot] if screenshot else None
    store_test_result(
        test_case_id=execution['metadata']['test_case_id'],
        execution_id=execution_id,
        result_data=execution,
        screenshots=screenshots
    )
    
    logger.info(f"Updated step {step_index} with status '{status}' for execution {execution_id}")
    return True


def complete_test_execution(
    execution_id: str,
    status: str,
    summary: str = None,
    metrics: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Complete a test execution.
    
    Args:
        execution_id: ID of the test execution
        status: Final status of the execution ('passed', 'failed', 'blocked', 'error')
        summary: Optional execution summary
        metrics: Optional execution metrics
        
    Returns:
        Dict: Final execution details
    """
    # Get current execution
    try:
        execution = get_test_execution(execution_id)
    except ValueError:
        logger.error(f"Execution {execution_id} not found")
        raise ValueError(f"Execution {execution_id} not found")
    
    test_case_id = execution['metadata']['test_case_id']
    
    # Update execution data
    execution['status'] = status
    execution['end_time'] = datetime.now().isoformat()
    
    if summary:
        execution['summary'] = summary
    
    # Calculate duration
    start_time = datetime.fromisoformat(execution.get('start_time', datetime.now().isoformat()))
    end_time = datetime.fromisoformat(execution['end_time'])
    duration_seconds = int((end_time - start_time).total_seconds())
    execution['execution_time'] = duration_seconds
    
    # Add execution metrics
    if metrics:
        execution['metrics'] = metrics
    
    # Count step statuses
    steps = execution.get('execution_steps', [])
    passed_steps = sum(1 for step in steps if step.get('status') == 'passed')
    failed_steps = sum(1 for step in steps if step.get('status') == 'failed')
    skipped_steps = sum(1 for step in steps if step.get('status') == 'skipped')
    
    # Store final result
    store_test_result(
        test_case_id=test_case_id,
        execution_id=execution_id,
        result_data=execution
    )
    
    # Update metrics record
    metrics_query = """
    UPDATE execution_metrics
    SET 
        end_time = %s,
        duration = %s,
        status = %s,
        pass_count = %s,
        fail_count = %s,
        skip_count = %s,
        metrics = %s
    WHERE execution_id = %s
    """
    
    update_database(
        query=metrics_query,
        params=(
            end_time,
            duration_seconds,
            status,
            passed_steps,
            failed_steps,
            skipped_steps,
            json.dumps(metrics) if metrics else None,
            execution_id
        )
    )
    
    logger.info(f"Completed test execution {execution_id} with status '{status}'")
    
    return {
        'execution_id': execution_id,
        'test_case_id': test_case_id,
        'status': status,
        'execution_time': duration_seconds,
        'passed_steps': passed_steps,
        'failed_steps': failed_steps,
        'skipped_steps': skipped_steps
    }


def get_test_execution_statistics(
    start_date: datetime = None,
    end_date: datetime = None,
    test_case_id: str = None,
    environment: str = None
) -> Dict[str, Any]:
    """
    Get statistics for test executions.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        test_case_id: Optional test case ID filter
        environment: Optional environment filter
        
    Returns:
        Dict: Statistics about test executions
    """
    # Base query
    base_query = """
    SELECT 
        COUNT(*) as total_executions,
        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
        AVG(duration) as avg_duration,
        MIN(duration) as min_duration,
        MAX(duration) as max_duration
    FROM execution_metrics
    WHERE end_time IS NOT NULL
    """
    
    params = []
    
    # Add filters
    if start_date:
        base_query += " AND start_time >= %s"
        params.append(start_date)
    
    if end_date:
        base_query += " AND start_time <= %s"
        params.append(end_date)
    
    if test_case_id:
        base_query += " AND test_case_id = %s"
        params.append(test_case_id)
    
    if environment:
        base_query += " AND environment = %s"
        params.append(environment)
    
    # Execute query
    stats = query_database(base_query, params, fetch_one=True)
    
    # Calculate pass rate
    if stats and stats['total_executions'] > 0:
        completed_execs = (stats['passed'] + stats['failed'] + stats['blocked'] + stats['error'])
        if completed_execs > 0:
            stats['pass_rate'] = (stats['passed'] / completed_execs) * 100
        else:
            stats['pass_rate'] = 0
    else:
        stats = {
            'total_executions': 0,
            'passed': 0,
            'failed': 0,
            'blocked': 0,
            'error': 0,
            'running': 0,
            'pass_rate': 0,
            'avg_duration': 0,
            'min_duration': 0,
            'max_duration': 0
        }
    
    # Get trend data (daily executions)
    trend_query = """
    SELECT 
        DATE(start_time) as date,
        COUNT(*) as executions,
        SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
        SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error
    FROM execution_metrics
    WHERE end_time IS NOT NULL
    """
    
    trend_params = []
    
    # Add filters
    if start_date:
        trend_query += " AND start_time >= %s"
        trend_params.append(start_date)
    
    if end_date:
        trend_query += " AND start_time <= %s"
        trend_params.append(end_date)
    
    if test_case_id:
        trend_query += " AND test_case_id = %s"
        trend_params.append(test_case_id)
    
    if environment:
        trend_query += " AND environment = %s"
        trend_params.append(environment)
    
    trend_query += " GROUP BY DATE(start_time) ORDER BY DATE(start_time)"
    
    # Execute trend query
    trend_data = query_database(trend_query, trend_params)
    
    # Format dates in trend data
    for item in trend_data:
        if isinstance(item['date'], datetime):
            item['date'] = item['date'].strftime('%Y-%m-%d')
    
    # Add trend data to statistics
    stats['trend'] = trend_data
    
    # Get top failing test cases
    if not test_case_id:
        failing_query = """
        SELECT 
            test_case_id,
            COUNT(*) as execution_count,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
            (SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)::float / COUNT(*)::float) * 100 as failure_rate
        FROM execution_metrics
        WHERE end_time IS NOT NULL
        """
        
        failing_params = []
        
        # Add filters
        if start_date:
            failing_query += " AND start_time >= %s"
            failing_params.append(start_date)
        
        if end_date:
            failing_query += " AND start_time <= %s"
            failing_params.append(end_date)
        
        if environment:
            failing_query += " AND environment = %s"
            failing_params.append(environment)
        
        failing_query += """
        GROUP BY test_case_id
        HAVING COUNT(*) >= 5  -- Only include test cases with at least 5 executions
        ORDER BY failure_rate DESC
        LIMIT 10
        """
        
        # Execute query
        failing_test_cases = query_database(failing_query, failing_params)
        
        # Add to statistics
        stats['top_failing_test_cases'] = failing_test_cases
    
    logger.info(f"Retrieved test execution statistics with {stats['total_executions']} total executions")
    return stats


def store_blueprism_job(
    job_id: str,
    controller_file: str,
    test_case_id: str = None
) -> int:
    """
    Store Blue Prism RPA job information.
    
    Args:
        job_id: Blue Prism job ID
        controller_file: Path to the controller file
        test_case_id: Optional test case ID
        
    Returns:
        int: Database record ID
    """
    query = """
    INSERT INTO blueprism_jobs
    (job_id, test_case_id, controller_file, status, started_at)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
    """
    
    job_db_id = update_database(
        query=query,
        params=(
            job_id,
            test_case_id,
            controller_file,
            'started',
            datetime.now()
        ),
        return_id=True
    )
    
    logger.info(f"Created Blue Prism job record for job ID {job_id} with database ID {job_db_id}")
    return job_db_id


def update_blueprism_job_status(
    job_id: str,
    status: str,
    result: str = None,
    error_message: str = None,
    logs_path: str = None
) -> bool:
    """
    Update the status of a Blue Prism RPA job.
    
    Args:
        job_id: Blue Prism job ID
        status: New status ('completed', 'failed', 'aborted')
        result: Optional result value
        error_message: Optional error message
        logs_path: Optional path to logs
        
    Returns:
        bool: True if update was successful
    """
    query = """
    UPDATE blueprism_jobs
    SET status = %s, completed_at = %s, result = %s, error_message = %s, logs_path = %s
    WHERE job_id = %s
    """
    
    affected_rows = update_database(
        query=query,
        params=(
            status,
            datetime.now() if status in ('completed', 'failed', 'aborted') else None,
            result,
            error_message,
            logs_path,
            job_id
        )
    )
    
    if affected_rows == 0:
        logger.warning(f"No Blue Prism job found with ID {job_id}")
        return False
    
    logger.info(f"Updated Blue Prism job {job_id} with status '{status}'")
    return True


def get_blueprism_job(job_id: str) -> Dict[str, Any]:
    """
    Get information for a Blue Prism RPA job.
    
    Args:
        job_id: Blue Prism job ID
        
    Returns:
        Dict: Job information
    """
    query = """
    SELECT id, job_id, test_case_id, controller_file, status, started_at, completed_at, result, error_message, logs_path
    FROM blueprism_jobs
    WHERE job_id = %s
    """
    
    result = query_database(
        query=query,
        params=(job_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Blue Prism job {job_id} not found")
        raise ValueError(f"Blue Prism job {job_id} not found")
    
    # Format datetime objects
    if result['started_at']:
        result['started_at'] = result['started_at'].isoformat() if isinstance(result['started_at'], datetime) else result['started_at']
    
    if result['completed_at']:
        result['completed_at'] = result['completed_at'].isoformat() if isinstance(result['completed_at'], datetime) else result['completed_at']
    
    # Calculate duration if applicable
    if result['started_at'] and result['completed_at']:
        started = datetime.fromisoformat(result['started_at'])
        completed = datetime.fromisoformat(result['completed_at'])
        duration_seconds = int((completed - started).total_seconds())
        result['duration_seconds'] = duration_seconds
    
    logger.info(f"Retrieved Blue Prism job {job_id}")
    return result


def get_blueprism_jobs(
    test_case_id: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get Blue Prism RPA jobs with optional filtering.
    
    Args:
        test_case_id: Optional test case ID filter
        status: Optional status filter
        limit: Maximum number of jobs to return
        offset: Offset for pagination
        
    Returns:
        List[Dict]: List of job information
    """
    base_query = """
    SELECT id, job_id, test_case_id, controller_file, status, started_at, completed_at, result
    FROM blueprism_jobs
    WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if test_case_id:
        base_query += " AND test_case_id = %s"
        params.append(test_case_id)
    
    if status:
        base_query += " AND status = %s"
        params.append(status)
    
    # Add sorting and pagination
    base_query += " ORDER BY started_at DESC LIMIT %s OFFSET %s"
    params.append(limit)
    params.append(offset)
    
    results = query_database(
        query=base_query,
        params=params
    )
    
    # Format datetime objects
    for result in results:
        if result['started_at']:
            result['started_at'] = result['started_at'].isoformat() if isinstance(result['started_at'], datetime) else result['started_at']
        
        if result['completed_at']:
            result['completed_at'] = result['completed_at'].isoformat() if isinstance(result['completed_at'], datetime) else result['completed_at']
    
    test_case_filter = f" for test case '{test_case_id}'" if test_case_id else ""
    status_filter = f" with status '{status}'" if status else ""
    logger.info(f"Retrieved {len(results)} Blue Prism jobs{test_case_filter}{status_filter}")
    return results


def store_uft_job(
    job_id: str,
    script_path: str,
    test_case_id: str = None
) -> int:
    """
    Store UFT job information.
    
    Args:
        job_id: UFT job ID
        script_path: Path to the UFT script
        test_case_id: Optional test case ID
        
    Returns:
        int: Database record ID
    """
    query = """
    INSERT INTO uft_jobs
    (job_id, test_case_id, script_path, status, started_at)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
    """
    
    job_db_id = update_database(
        query=query,
        params=(
            job_id,
            test_case_id,
            script_path,
            'started',
            datetime.now()
        ),
        return_id=True
    )
    
    logger.info(f"Created UFT job record for job ID {job_id} with database ID {job_db_id}")
    return job_db_id


def update_uft_job_status(
    job_id: str,
    status: str,
    result: str = None,
    error_message: str = None,
    logs_path: str = None
) -> bool:
    """
    Update the status of a UFT job.
    
    Args:
        job_id: UFT job ID
        status: New status ('completed', 'failed', 'aborted')
        result: Optional result value
        error_message: Optional error message
        logs_path: Optional path to logs
        
    Returns:
        bool: True if update was successful
    """
    query = """
    UPDATE uft_jobs
    SET status = %s, completed_at = %s, result = %s, error_message = %s, logs_path = %s
    WHERE job_id = %s
    """
    
    affected_rows = update_database(
        query=query,
        params=(
            status,
            datetime.now() if status in ('completed', 'failed', 'aborted') else None,
            result,
            error_message,
            logs_path,
            job_id
        )
    )
    
    if affected_rows == 0:
        logger.warning(f"No UFT job found with ID {job_id}")
        return False
    
    logger.info(f"Updated UFT job {job_id} with status '{status}'")
    return True


def get_uft_job(job_id: str) -> Dict[str, Any]:
    """
    Get information for a UFT job.
    
    Args:
        job_id: UFT job ID
        
    Returns:
        Dict: Job information
    """
    query = """
    SELECT id, job_id, test_case_id, script_path, status, started_at, completed_at, result, error_message, logs_path
    FROM uft_jobs
    WHERE job_id = %s
    """
    
    result = query_database(
        query=query,
        params=(job_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"UFT job {job_id} not found")
        raise ValueError(f"UFT job {job_id} not found")
    
    # Format datetime objects
    if result['started_at']:
        result['started_at'] = result['started_at'].isoformat() if isinstance(result['started_at'], datetime) else result['started_at']
    
    if result['completed_at']:
        result['completed_at'] = result['completed_at'].isoformat() if isinstance(result['completed_at'], datetime) else result['completed_at']
    
    # Calculate duration if applicable
    if result['started_at'] and result['completed_at']:
        started = datetime.fromisoformat(result['started_at'])
        completed = datetime.fromisoformat(result['completed_at'])
        duration_seconds = int((completed - started).total_seconds())
        result['duration_seconds'] = duration_seconds
    
    logger.info(f"Retrieved UFT job {job_id}")
    return result


def store_rpa_controller_file(
    controller_data: Dict[str, Any],
    file_name: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store RPA controller data for Blue Prism integration.
    
    Args:
        controller_data: Dictionary containing controller configuration
        file_name: Optional file name (default: generates a timestamped name)
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored controller file
    """
    if not file_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"blueprism_controller_{timestamp}.json"
    
    # Convert controller data to JSON
    controller_json = json.dumps(controller_data, indent=2)
    
    # Store JSON in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'rpa-controller',
        'rpa-type': 'blueprism'
    }
    
    upload_data_to_storage(
        data=controller_json.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    logger.info(f"Blue Prism controller file stored as {file_name} in bucket {bucket_name}")
    return file_name


def get_rpa_controller_file(
    file_name: str,
    bucket_name: str = DEFAULT_BUCKET
) -> Dict[str, Any]:
    """
    Retrieve Blue Prism controller data from object storage.
    
    Args:
        file_name: Name of the controller file
        bucket_name: Name of the bucket
        
    Returns:
        Dict: Controller data as a dictionary
    """
    try:
        # Download JSON from object storage
        data_bytes = download_data_from_storage(
            object_name=file_name,
            bucket_name=bucket_name
        )
        
        # Parse JSON
        controller_data = json.loads(data_bytes.decode('utf-8'))
        logger.info(f"Blue Prism controller file {file_name} retrieved successfully")
        return controller_data
    except Exception as e:
        logger.error(f"Failed to retrieve Blue Prism controller file {file_name}: {str(e)}")
        raise


def update_rpa_execution_flag(
    test_case_id: str,
    flag_value: bool = True,
    controller_file: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Update execution flag for a test case in the Blue Prism controller file.
    
    Args:
        test_case_id: ID of the test case to update
        flag_value: Value to set for the execution flag (True/False)
        controller_file: Name of the controller file (default: use the latest)
        bucket_name: Name of the bucket
        
    Returns:
        str: Name of the updated controller file
    """
    # If no controller file specified, find the latest
    if not controller_file:
        objects = list_storage_objects(
            prefix="blueprism_controller_",
            bucket_name=bucket_name
        )
        
        if not objects:
            raise ValueError("No Blue Prism controller files found")
            
        # Sort by last_modified and get the most recent
        latest_obj = sorted(objects, key=lambda x: x['last_modified'], reverse=True)[0]
        controller_file = latest_obj['name']
    
    # Get current controller data
    controller_data = get_rpa_controller_file(controller_file, bucket_name)
    
    # Update execution flag for the specified test case
    updated = False
    if 'test_cases' in controller_data:
        for test_case in controller_data['test_cases']:
            if test_case.get('id') == test_case_id:
                test_case['execute'] = flag_value
                updated = True
                break
    
    if not updated:
        # Test case not found, add it
        if 'test_cases' not in controller_data:
            controller_data['test_cases'] = []
            
        controller_data['test_cases'].append({
            'id': test_case_id,
            'execute': flag_value,
            'added_date': datetime.now().isoformat()
        })
    
    # Store updated controller data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_file_name = f"blueprism_controller_{timestamp}.json"
    
    store_rpa_controller_file(
        controller_data=controller_data,
        file_name=new_file_name,
        bucket_name=bucket_name
    )
    
    logger.info(f"Updated execution flag for test case {test_case_id} to {flag_value} in {new_file_name}")
    return new_file_name


def analyze_test_execution_trends(
    days: int = 30,
    test_case_id: str = None,
    environment: str = None
) -> Dict[str, Any]:
    """
    Analyze trends in test executions over time.
    
    Args:
        days: Number of days to analyze
        test_case_id: Optional test case ID filter
        environment: Optional environment filter
        
    Returns:
        Dict: Trend analysis results
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Get basic statistics for the period
    stats = get_test_execution_statistics(
        start_date=start_date,
        test_case_id=test_case_id,
        environment=environment
    )
    
    # Prepare analysis results
    analysis = {
        'period_days': days,
        'total_executions': stats['total_executions'],
        'pass_rate': stats['pass_rate'],
        'daily_trend': stats['trend'],
        'insights': []
    }
    
    # Add average executions per day
    if analysis['daily_trend']:
        analysis['avg_executions_per_day'] = analysis['total_executions'] / len(analysis['daily_trend'])
    else:
        analysis['avg_executions_per_day'] = 0
    
    # Calculate week-over-week change in pass rate
    if len(analysis['daily_trend']) >= 14:
        # Last 7 days
        last_week_data = analysis['daily_trend'][-7:]
        last_week_executions = sum(day['executions'] for day in last_week_data)
        last_week_passed = sum(day['passed'] for day in last_week_data)
        
        # Previous 7 days
        prev_week_data = analysis['daily_trend'][-14:-7]
        prev_week_executions = sum(day['executions'] for day in prev_week_data)
        prev_week_passed = sum(day['passed'] for day in prev_week_data)
        
        # Calculate pass rates
        last_week_pass_rate = (last_week_passed / last_week_executions * 100) if last_week_executions > 0 else 0
        prev_week_pass_rate = (prev_week_passed / prev_week_executions * 100) if prev_week_executions > 0 else 0
        
        # Calculate change
        pass_rate_change = last_week_pass_rate - prev_week_pass_rate
        
        analysis['week_over_week'] = {
            'last_week_pass_rate': last_week_pass_rate,
            'prev_week_pass_rate': prev_week_pass_rate,
            'pass_rate_change': pass_rate_change
        }
        
        # Add insight
        if abs(pass_rate_change) >= 5:
            direction = "improved" if pass_rate_change > 0 else "declined"
            analysis['insights'].append({
                'type': 'pass_rate_change',
                'message': f"Pass rate has {direction} by {abs(pass_rate_change):.1f}% compared to the previous week."
            })
    
    # Identify patterns in failures
    if 'top_failing_test_cases' in stats and stats['top_failing_test_cases']:
        high_failure_cases = [tc for tc in stats['top_failing_test_cases'] if tc['failure_rate'] > 30]
        if high_failure_cases:
            analysis['insights'].append({
                'type': 'high_failure_rate',
                'message': f"Found {len(high_failure_cases)} test cases with failure rates above 30%.",
                'test_cases': high_failure_cases
            })
    
    # Check for trends in execution times
    if stats['avg_duration']:
        analysis['avg_duration'] = stats['avg_duration']
        
        # Get execution time trend
        time_trend_query = """
        SELECT 
            DATE(start_time) as date,
            AVG(duration) as avg_duration
        FROM execution_metrics
        WHERE end_time IS NOT NULL
        AND start_time >= %s
        """
        
        params = [start_date]
        
        if test_case_id:
            time_trend_query += " AND test_case_id = %s"
            params.append(test_case_id)
        
        if environment:
            time_trend_query += " AND environment = %s"
            params.append(environment)
        
        time_trend_query += " GROUP BY DATE(start_time) ORDER BY DATE(start_time)"
        
        time_trend = query_database(time_trend_query, params)
        
        # Format dates in time trend
        for item in time_trend:
            if isinstance(item['date'], datetime):
                item['date'] = item['date'].strftime('%Y-%m-%d')
        
        analysis['duration_trend'] = time_trend
        
        # Check for significant increases in execution time
        if len(time_trend) >= 7:
            recent_avg = sum(item['avg_duration'] for item in time_trend[-3:]) / 3 if time_trend[-3:] else 0
            earlier_avg = sum(item['avg_duration'] for item in time_trend[-7:-3]) / 4 if time_trend[-7:-3] else 0
            
            if recent_avg > 0 and earlier_avg > 0:
                time_change_pct = ((recent_avg - earlier_avg) / earlier_avg) * 100
                
                if abs(time_change_pct) >= 20:
                    direction = "increased" if time_change_pct > 0 else "decreased"
                    analysis['insights'].append({
                        'type': 'execution_time_change',
                        'message': f"Average execution time has {direction} by {abs(time_change_pct):.1f}% in the last 3 days."
                    })
    
    logger.info(f"Completed test execution trend analysis over {days} days")
    return analysis

# End of Part 5: Test Execution & Results

# ------------- Part 6: Integration System Connectors -------------

def store_integration_credentials(
    system_type: str,
    credentials: Dict[str, Any],
    encrypted: bool = True
) -> int:
    """
    Store integration system credentials in the database.
    For security, actual credentials are encrypted before storage.
    
    Args:
        system_type: Type of system ('jira', 'sharepoint', 'alm', 'blueprism', 'uft')
        credentials: Dictionary containing credentials
        encrypted: Whether to encrypt credentials (should be True in production)
        
    Returns:
        int: ID of the stored credentials
    """
    # In production, we would encrypt the credentials before storage
    # For this implementation, we'll just convert to JSON
    if encrypted:
        try:
            from cryptography.fernet import Fernet
            # Get encryption key from environment variable or generate one
            encryption_key = os.environ.get('ENCRYPTION_KEY')
            if not encryption_key:
                logger.warning("No encryption key found in environment. Using default key.")
                encryption_key = b'EE11CBB19052E40B07AAC0CA060C23EE11CBB19052E40B07AAC0CA060C23EE'
            
            # Convert dict to JSON string
            creds_json = json.dumps(credentials)
            
            # Encrypt the JSON string
            f = Fernet(encryption_key)
            encrypted_creds = f.encrypt(creds_json.encode('utf-8'))
            
            # Store the encrypted bytes as base64 string
            creds_to_store = encrypted_creds.decode('utf-8')
        except ImportError:
            logger.warning("Cryptography package not available. Storing credentials as JSON.")
            encrypted = False
            creds_to_store = json.dumps(credentials)
    else:
        creds_to_store = json.dumps(credentials)
    
    query = """
    INSERT INTO integration_credentials 
    (system_type, credentials, encrypted, created_at)
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """
    
    cred_id = update_database(
        query=query,
        params=(
            system_type,
            creds_to_store,
            encrypted,
            datetime.now()
        ),
        return_id=True
    )
    
    logger.info(f"Credentials for {system_type} system stored with ID {cred_id}")
    return cred_id


def get_integration_credentials(
    system_type: str,
    decrypt: bool = True
) -> Dict[str, Any]:
    """
    Retrieve integration system credentials from the database.
    
    Args:
        system_type: Type of system ('jira', 'sharepoint', 'alm', 'blueprism', 'uft')
        decrypt: Whether to decrypt credentials (should be True in production)
        
    Returns:
        Dict: Credentials as a dictionary
    """
    query = """
    SELECT id, credentials, encrypted, updated_at
    FROM integration_credentials
    WHERE system_type = %s
    ORDER BY updated_at DESC
    LIMIT 1
    """
    
    result = query_database(
        query=query,
        params=(system_type,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"No credentials found for {system_type} system")
        raise ValueError(f"No credentials found for {system_type} system")
    
    credentials_str = result['credentials']
    is_encrypted = result['encrypted']
    
    # Decrypt if necessary
    if is_encrypted and decrypt:
        try:
            from cryptography.fernet import Fernet
            # Get encryption key from environment variable
            encryption_key = os.environ.get('ENCRYPTION_KEY')
            if not encryption_key:
                logger.warning("No encryption key found in environment. Using default key.")
                encryption_key = b'EE11CBB19052E40B07AAC0CA060C23EE11CBB19052E40B07AAC0CA060C23EE'
            
            # Decrypt the credentials
            f = Fernet(encryption_key)
            decrypted_creds = f.decrypt(credentials_str.encode('utf-8'))
            
            # Parse the JSON
            credentials = json.loads(decrypted_creds.decode('utf-8'))
        except (ImportError, Exception) as e:
            logger.error(f"Failed to decrypt credentials: {str(e)}")
            raise ValueError("Could not decrypt credentials. Encryption key may be invalid.")
    else:
        # Parse the JSON
        credentials = json.loads(credentials_str)
    
    logger.info(f"Retrieved credentials for {system_type} system (ID: {result['id']})")
    return credentials


def delete_integration_credentials(
    credential_id: int
) -> bool:
    """
    Delete integration system credentials.
    
    Args:
        credential_id: ID of the credentials to delete
        
    Returns:
        bool: True if deletion was successful
    """
    query = """
    DELETE FROM integration_credentials
    WHERE id = %s
    """
    
    affected_rows = update_database(
        query=query,
        params=(credential_id,)
    )
    
    if affected_rows == 0:
        logger.warning(f"No credentials found with ID {credential_id}")
        return False
    
    logger.info(f"Deleted credentials with ID {credential_id}")
    return True


def validate_integration_connection(
    system_type: str,
    credentials: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Validate connection to an integration system.
    
    Args:
        system_type: Type of system ('jira', 'sharepoint', 'alm', 'blueprism', 'uft')
        credentials: Optional credentials (default: retrieve from database)
        
    Returns:
        Dict: Connection status and details
    """
    # Get credentials if not provided
    if not credentials:
        try:
            credentials = get_integration_credentials(system_type)
        except ValueError as e:
            return {
                'connected': False,
                'error': str(e),
                'details': 'No credentials found in database'
            }
    
    result = {
        'connected': False,
        'system_type': system_type,
        'timestamp': datetime.now().isoformat()
    }
    
    # Validate connection based on system type
    try:
        if system_type == 'jira':
            # Validate JIRA connection
            if 'url' not in credentials or 'username' not in credentials or 'api_token' not in credentials:
                return {**result, 'error': 'Missing required credentials'}
            
            # Use requests to validate connection
            import requests
            url = f"{credentials['url']}/rest/api/2/myself"
            auth = (credentials['username'], credentials['api_token'])
            
            response = requests.get(url, auth=auth, timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                result['connected'] = True
                result['details'] = {
                    'username': user_data.get('name'),
                    'display_name': user_data.get('displayName'),
                    'url': credentials['url']
                }
            else:
                result['error'] = f"Failed to connect to JIRA: HTTP {response.status_code}"
                result['details'] = response.text[:500] if response.text else None
        
        elif system_type == 'sharepoint':
            # Validate SharePoint connection
            if 'tenant_id' not in credentials or 'client_id' not in credentials or 'client_secret' not in credentials:
                return {**result, 'error': 'Missing required credentials'}
            
            # Use requests to validate connection and get token
            import requests
            
            token_url = f"https://login.microsoftonline.com/{credentials['tenant_id']}/oauth2/v2.0/token"
            scope = "https://graph.microsoft.com/.default"
            
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': credentials['client_id'],
                'client_secret': credentials['client_secret'],
                'scope': scope
            }
            
            response = requests.post(token_url, data=token_data, timeout=10)
            if response.status_code == 200:
                token_info = response.json()
                result['connected'] = True
                result['details'] = {
                    'token_type': token_info.get('token_type'),
                    'expires_in': token_info.get('expires_in'),
                    'site_url': credentials.get('site_url', 'Not specified')
                }
            else:
                result['error'] = f"Failed to connect to SharePoint: HTTP {response.status_code}"
                result['details'] = response.text[:500] if response.text else None
        
        elif system_type == 'alm':
            # Validate ALM connection
            if 'url' not in credentials or 'username' not in credentials or 'password' not in credentials:
                return {**result, 'error': 'Missing required credentials'}
            
            # Use requests to validate connection
            import requests
            
            # ALM requires authentication cookies
            session = requests.Session()
            
            # First request to get LWSSO_COOKIE_KEY
            auth_url = f"{credentials['url']}/qcbin/authentication-point/authenticate"
            auth_headers = {
                'Authorization': f"Basic {base64.b64encode(f'{credentials['username']}:{credentials['password']}'.encode()).decode()}"
            }
            
            auth_response = session.get(auth_url, headers=auth_headers, timeout=10)
            
            if auth_response.status_code == 200:
                # Now check if we can access ALM
                site_session_url = f"{credentials['url']}/qcbin/rest/site-session"
                site_response = session.post(site_session_url, timeout=10)
                
                if site_response.status_code == 201 or site_response.status_code == 200:
                    result['connected'] = True
                    result['details'] = {
                        'url': credentials['url'],
                        'username': credentials['username'],
                        'domain': credentials.get('domain', 'DEFAULT'),
                        'project': credentials.get('project', 'Not specified')
                    }
                else:
                    result['error'] = f"Failed to create ALM site session: HTTP {site_response.status_code}"
                    result['details'] = site_response.text[:500] if site_response.text else None
            else:
                result['error'] = f"Failed to authenticate to ALM: HTTP {auth_response.status_code}"
                result['details'] = auth_response.text[:500] if auth_response.text else None
        
        elif system_type == 'blueprism':
            # Validate Blue Prism connection
            if 'url' not in credentials or 'username' not in credentials or 'password' not in credentials:
                return {**result, 'error': 'Missing required credentials'}
            
            # Blue Prism validation - typically would use BP API or direct DB connection
            # This is a simplified example
            import requests
            
            # Attempt to connect to Blue Prism API (assuming REST API is available)
            # The actual endpoint would depend on your BP configuration
            api_url = f"{credentials['url']}/api/v1/sessions"
            auth_data = {
                'username': credentials['username'],
                'password': credentials['password']
            }
            
            try:
                response = requests.post(api_url, json=auth_data, timeout=10)
                if response.status_code == 200 or response.status_code == 201:
                    token_info = response.json()
                    result['connected'] = True
                    result['details'] = {
                        'url': credentials['url'],
                        'username': credentials['username'],
                        'token_expires': token_info.get('expires', 'Unknown')
                    }
                else:
                    result['error'] = f"Failed to connect to Blue Prism: HTTP {response.status_code}"
                    result['details'] = response.text[:500] if response.text else None
            except requests.exceptions.RequestException as e:
                # Handle connection errors
                result['error'] = f"Failed to connect to Blue Prism: {str(e)}"
        
        elif system_type == 'uft':
            # Validate UFT connection
            if 'host' not in credentials or 'port' not in credentials:
                return {**result, 'error': 'Missing required credentials'}
            
            # UFT validation - would typically use UFT API
            # This is a simplified check to see if the host/port is reachable
            import socket
            
            host = credentials['host']
            port = int(credentials['port'])
            
            # Try to create a socket connection to the host:port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            try:
                sock.connect((host, port))
                result['connected'] = True
                result['details'] = {
                    'host': host,
                    'port': port,
                    'connection': 'Established'
                }
            except Exception as e:
                result['error'] = f"Failed to connect to UFT host: {str(e)}"
            finally:
                sock.close()
        
        else:
            result['error'] = f"Unsupported system type: {system_type}"
    
    except ImportError as e:
        result['error'] = f"Missing required package: {str(e)}"
    except Exception as e:
        result['error'] = f"Validation failed: {str(e)}"
    
    logger.info(f"Validated connection to {system_type}: {'Connected' if result['connected'] else 'Failed'}")
    return result


def store_sharepoint_document(
    document_data: bytes,
    file_name: str,
    content_type: str,
    metadata: Dict[str, str] = None,
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store document in object storage before uploading to SharePoint.
    Provides a temporary storage location for documents that will be synced to SharePoint.
    
    Args:
        document_data: Document content as bytes
        file_name: Name of the file
        content_type: MIME type of the document
        metadata: Optional metadata for the document
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name in storage
    """
    object_name = f"sharepoint/{datetime.now().strftime('%Y%m%d')}/{file_name}"
    
    # Prepare metadata
    doc_metadata = {
        'content-type': content_type,
        'source': 'watsonx-ipg-testing',
        'type': 'sharepoint-document',
        'sync-status': 'pending'
    }
    
    # Add additional metadata if provided
    if metadata:
        doc_metadata.update(metadata)
    
    # Upload to object storage
    upload_data_to_storage(
        data=document_data,
        object_name=object_name,
        bucket_name=bucket_name,
        metadata=doc_metadata,
        content_type=content_type
    )
    
    # Record in database for tracking
    query = """
    INSERT INTO sharepoint_documents 
    (file_name, storage_path, content_type, sync_status, created_at)
    VALUES (%s, %s, %s, %s, %s)
    """
    
    update_database(
        query=query,
        params=(
            file_name,
            f"{bucket_name}/{object_name}",
            content_type,
            'pending',
            datetime.now()
        )
    )
    
    logger.info(f"Document stored as {object_name} in bucket {bucket_name} for SharePoint sync")
    return object_name


def upload_document_to_sharepoint(
    document_id: int,
    folder_path: str = None
) -> Dict[str, Any]:
    """
    Upload a document from object storage to SharePoint.
    
    Args:
        document_id: ID of the document record in the database
        folder_path: Optional folder path in SharePoint (default: root of document library)
        
    Returns:
        Dict: Upload status and details
    """
    # Get document record
    query = """
    SELECT id, file_name, storage_path, content_type, sync_status
    FROM sharepoint_documents
    WHERE id = %s
    """
    
    document = query_database(
        query=query,
        params=(document_id,),
        fetch_one=True
    )
    
    if not document:
        logger.error(f"Document with ID {document_id} not found")
        return {
            'status': 'error',
            'error': f"Document with ID {document_id} not found"
        }
    
    # Check if already synced
    if document['sync_status'] == 'synced':
        logger.info(f"Document {document_id} already synced to SharePoint")
        return {
            'status': 'success',
            'message': 'Document already synced',
            'document_id': document_id,
            'file_name': document['file_name']
        }
    
    # Get SharePoint credentials
    try:
        credentials = get_integration_credentials('sharepoint')
    except ValueError as e:
        logger.error(f"Failed to get SharePoint credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'SharePoint credentials not found'
        }
    
    # Get document from object storage
    storage_path = document['storage_path']
    bucket_name, object_name = storage_path.split('/', 1)
    
    try:
        document_data = download_data_from_storage(
            object_name=object_name,
            bucket_name=bucket_name
        )
    except Exception as e:
        logger.error(f"Failed to download document from storage: {str(e)}")
        return {
            'status': 'error',
            'error': f"Failed to download document from storage: {str(e)}"
        }
    
    # Upload to SharePoint
    try:
        import requests
        
        # Get MS Graph auth token
        token_url = f"https://login.microsoftonline.com/{credentials['tenant_id']}/oauth2/v2.0/token"
        scope = "https://graph.microsoft.com/.default"
        
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': credentials['client_id'],
            'client_secret': credentials['client_secret'],
            'scope': scope
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=30)
        if token_response.status_code != 200:
            logger.error(f"Failed to get Microsoft Graph token: {token_response.text}")
            return {
                'status': 'error',
                'error': f"Authentication failed: {token_response.status_code}"
            }
        
        token_info = token_response.json()
        access_token = token_info['access_token']
        
        # Prepare upload URL
        site_id = credentials.get('site_id', '')
        drive_id = credentials.get('drive_id', '')
        
        if not site_id or not drive_id:
            logger.error("Site ID and Drive ID are required in SharePoint credentials")
            return {
                'status': 'error',
                'error': "Site ID and Drive ID are required in SharePoint credentials"
            }
        
        file_name = document['file_name']
        
        # Build the folder path
        path_component = ""
        if folder_path:
            # URL encode folder path
            from urllib.parse import quote
            encoded_path = quote(folder_path)
            path_component = f"/{encoded_path}:"
        
        # URL encode filename
        from urllib.parse import quote
        encoded_file_name = quote(file_name)
        
        # Create upload URL
        upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root{path_component}/{encoded_file_name}:/content"
        
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': document['content_type']
        }
        
        # Upload the file
        upload_response = requests.put(upload_url, headers=headers, data=document_data, timeout=60)
        
        if upload_response.status_code >= 200 and upload_response.status_code < 300:
            # Success
            file_info = upload_response.json()
            sharepoint_url = file_info.get('webUrl', '')
            
            # Update database record
            update_query = """
            UPDATE sharepoint_documents
            SET sync_status = 'synced', sharepoint_url = %s, synced_at = %s
            WHERE id = %s
            """
            
            update_database(
                query=update_query,
                params=(
                    sharepoint_url,
                    datetime.now(),
                    document_id
                )
            )
            
            logger.info(f"Document {document_id} ({file_name}) uploaded to SharePoint successfully")
            return {
                'status': 'success',
                'document_id': document_id,
                'file_name': file_name,
                'sharepoint_url': sharepoint_url,
                'item_id': file_info.get('id', '')
            }
        else:
            logger.error(f"Failed to upload to SharePoint: {upload_response.status_code} - {upload_response.text}")
            return {
                'status': 'error',
                'error': f"Upload failed: {upload_response.status_code}",
                'details': upload_response.text[:500] if upload_response.text else None
            }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"SharePoint upload failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"SharePoint upload failed: {str(e)}"
        }


def get_pending_sharepoint_documents(
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get documents pending upload to SharePoint.
    
    Args:
        limit: Maximum number of documents to return
        
    Returns:
        List[Dict]: List of pending documents
    """
    query = """
    SELECT id, file_name, storage_path, content_type, created_at
    FROM sharepoint_documents
    WHERE sync_status = 'pending'
    ORDER BY created_at ASC
    LIMIT %s
    """
    
    results = query_database(
        query=query,
        params=(limit,)
    )
    
    logger.info(f"Retrieved {len(results)} pending SharePoint documents")
    return results


def create_jira_issue(
    issue_type: str,
    summary: str,
    description: str,
    project_key: str,
    fields: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create an issue in JIRA.
    
    Args:
        issue_type: Type of issue ('Bug', 'Story', etc.)
        summary: Issue summary
        description: Issue description
        project_key: JIRA project key
        fields: Optional additional fields
        
    Returns:
        Dict: Issue creation status and details
    """
    # Get JIRA credentials
    try:
        credentials = get_integration_credentials('jira')
    except ValueError as e:
        logger.error(f"Failed to get JIRA credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'JIRA credentials not found'
        }
    
    try:
        import requests
        
        # Prepare issue data
        issue_data = {
            'fields': {
                'project': {
                    'key': project_key
                },
                'summary': summary,
                'description': description,
                'issuetype': {
                    'name': issue_type
                }
            }
        }
        
        # Add any additional fields
        if fields:
            for key, value in fields.items():
                issue_data['fields'][key] = value
        
        # Create issue
        url = f"{credentials['url']}/rest/api/2/issue"
        auth = (credentials['username'], credentials['api_token'])
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(
            url,
            json=issue_data,
            auth=auth,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in (200, 201):
            issue_info = response.json()
            logger.info(f"Created JIRA issue {issue_info['key']}")
            return {
                'status': 'success',
                'issue_key': issue_info['key'],
                'issue_id': issue_info['id'],
                'issue_url': f"{credentials['url']}/browse/{issue_info['key']}"
            }
        else:
            logger.error(f"Failed to create JIRA issue: {response.status_code} - {response.text}")
            return {
                'status': 'error',
                'error': f"Creation failed: {response.status_code}",
                'details': response.text[:500] if response.text else None
            }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"JIRA issue creation failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"JIRA issue creation failed: {str(e)}"
        }


def update_jira_issue(
    issue_key: str,
    fields: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update a JIRA issue.
    
    Args:
        issue_key: JIRA issue key
        fields: Fields to update
        
    Returns:
        Dict: Update status and details
    """
    # Get JIRA credentials
    try:
        credentials = get_integration_credentials('jira')
    except ValueError as e:
        logger.error(f"Failed to get JIRA credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'JIRA credentials not found'
        }
    
    try:
        import requests
        
        # Prepare update data
        update_data = {
            'fields': fields
        }
        
        # Update issue
        url = f"{credentials['url']}/rest/api/2/issue/{issue_key}"
        auth = (credentials['username'], credentials['api_token'])
        headers = {'Content-Type': 'application/json'}
        
        response = requests.put(
            url,
            json=update_data,
            auth=auth,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 204:
            logger.info(f"Updated JIRA issue {issue_key}")
            return {
                'status': 'success',
                'issue_key': issue_key,
                'issue_url': f"{credentials['url']}/browse/{issue_key}"
            }
        else:
            logger.error(f"Failed to update JIRA issue: {response.status_code} - {response.text}")
            return {
                'status': 'error',
                'error': f"Update failed: {response.status_code}",
                'details': response.text[:500] if response.text else None
            }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"JIRA issue update failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"JIRA issue update failed: {str(e)}"
        }


def get_jira_issue(
    issue_key: str
) -> Dict[str, Any]:
    """
    Get a JIRA issue.
    
    Args:
        issue_key: JIRA issue key
        
    Returns:
        Dict: Issue details
    """
    # Get JIRA credentials
    try:
        credentials = get_integration_credentials('jira')
    except ValueError as e:
        logger.error(f"Failed to get JIRA credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'JIRA credentials not found'
        }
    
    try:
        import requests
        
        # Get issue
        url = f"{credentials['url']}/rest/api/2/issue/{issue_key}"
        auth = (credentials['username'], credentials['api_token'])
        
        response = requests.get(
            url,
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            issue_data = response.json()
            
            # Extract important fields
            fields = issue_data['fields']
            issue_info = {
                'key': issue_data['key'],
                'id': issue_data['id'],
                'summary': fields.get('summary', ''),
                'status': fields.get('status', {}).get('name', ''),
                'issue_type': fields.get('issuetype', {}).get('name', ''),
                'priority': fields.get('priority', {}).get('name', ''),
                'assignee': fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else None,
                'reporter': fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else None,
                'created': fields.get('created', ''),
                'updated': fields.get('updated', ''),
                'description': fields.get('description', ''),
                'url': f"{credentials['url']}/browse/{issue_data['key']}"
            }
            
            logger.info(f"Retrieved JIRA issue {issue_key}")
            return {
                'status': 'success',
                'issue': issue_info
            }
        else:
            logger.error(f"Failed to get JIRA issue: {response.status_code} - {response.text}")
            return {
                'status': 'error',
                'error': f"Retrieval failed: {response.status_code}",
                'details': response.text[:500] if response.text else None
            }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"JIRA issue retrieval failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"JIRA issue retrieval failed: {str(e)}"
        }


def add_attachment_to_jira_issue(
    issue_key: str,
    file_data: bytes,
    file_name: str
) -> Dict[str, Any]:
    """
    Add an attachment to a JIRA issue.
    
    Args:
        issue_key: JIRA issue key
        file_data: File content as bytes
        file_name: Name of the file
        
    Returns:
        Dict: Attachment status and details
    """
    # Get JIRA credentials
    try:
        credentials = get_integration_credentials('jira')
    except ValueError as e:
        logger.error(f"Failed to get JIRA credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'JIRA credentials not found'
        }
    
    try:
        import requests
        
        # Prepare attachment
        url = f"{credentials['url']}/rest/api/2/issue/{issue_key}/attachments"
        auth = (credentials['username'], credentials['api_token'])
        headers = {'X-Atlassian-Token': 'no-check'}
        
        files = {
            'file': (file_name, file_data)
        }
        
        response = requests.post(
            url,
            auth=auth,
            headers=headers,
            files=files,
            timeout=60
        )
        
        if response.status_code in (200, 201):
            attachment_info = response.json()
            logger.info(f"Added attachment {file_name} to JIRA issue {issue_key}")
            return {
                'status': 'success',
                'issue_key': issue_key,
                'file_name': file_name,
                'attachment_id': attachment_info[0]['id'] if attachment_info else None,
                'attachment_url': attachment_info[0]['content'] if attachment_info else None
            }
        else:
            logger.error(f"Failed to add attachment: {response.status_code} - {response.text}")
            return {
                'status': 'error',
                'error': f"Attachment failed: {response.status_code}",
                'details': response.text[:500] if response.text else None
            }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"JIRA attachment failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"JIRA attachment failed: {str(e)}"
        }


def import_jira_requirements(
    project_key: str,
    issue_type: str = 'Story',
    jql: str = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """
    Import requirements from JIRA issues.
    
    Args:
        project_key: JIRA project key
        issue_type: Type of issue to import as requirements
        jql: Optional JQL filter (default: project={project_key} AND issuetype={issue_type})
        max_results: Maximum number of issues to import
        
    Returns:
        Dict: Import status and statistics
    """
    # Get JIRA credentials
    try:
        credentials = get_integration_credentials('jira')
    except ValueError as e:
        logger.error(f"Failed to get JIRA credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'JIRA credentials not found'
        }
    
    try:
        import requests
        
        # Build JQL query if not provided
        if not jql:
            jql = f"project = {project_key} AND issuetype = '{issue_type}'"
        
        # Prepare search request
        url = f"{credentials['url']}/rest/api/2/search"
        auth = (credentials['username'], credentials['api_token'])
        params = {
            'jql': jql,
            'maxResults': max_results,
            'fields': 'summary,description,status,customfield_*'
        }
        
        response = requests.get(
            url,
            auth=auth,
            params=params,
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to search JIRA issues: {response.status_code} - {response.text}")
            return {
                'status': 'error',
                'error': f"Search failed: {response.status_code}",
                'details': response.text[:500] if response.text else None
            }
        
        search_data = response.json()
        issues = search_data.get('issues', [])
        
        # Import statistics
        stats = {
            'total': len(issues),
            'imported': 0,
            'updated': 0,
            'failed': 0,
            'issues': []
        }
        
        # Process each issue
        for issue in issues:
            issue_key = issue.get('key')
            fields = issue.get('fields', {})
            
            try:
                # Create requirement data
                requirement_data = {
                    'id': f"JIRA_{issue_key}",
                    'title': fields.get('summary', f"JIRA Issue {issue_key}"),
                    'description': fields.get('description', ''),
                    'status': fields.get('status', {}).get('name', 'active').lower(),
                    'jira_data': {
                        'issue_key': issue_key,
                        'issue_id': issue.get('id'),
                        'issue_type': issue_type,
                        'project_key': project_key,
                        'url': f"{credentials['url']}/browse/{issue_key}"
                    }
                }
                
                # Check if requirement already exists
                existing = False
                try:
                    get_requirement_by_id(requirement_data['id'])
                    existing = True
                except ValueError:
                    pass
                
                # Store requirement
                store_requirement(
                    requirement_data=requirement_data,
                    source='jira',
                    source_id=issue_key
                )
                
                if existing:
                    stats['updated'] += 1
                else:
                    stats['imported'] += 1
                
                stats['issues'].append({
                    'issue_key': issue_key,
                    'status': 'updated' if existing else 'imported',
                    'requirement_id': requirement_data['id']
                })
                
            except Exception as e:
                logger.error(f"Failed to import JIRA issue {issue_key}: {str(e)}")
                stats['failed'] += 1
                stats['issues'].append({
                    'issue_key': issue_key,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Imported {stats['imported']} requirements from JIRA, updated {stats['updated']}, failed {stats['failed']}")
        return {
            'status': 'success',
            'stats': stats
        }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"JIRA import failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"JIRA import failed: {str(e)}"
        }


def create_alm_defect(
    test_case_id: str,
    execution_id: str,
    summary: str,
    description: str,
    severity: str = 'Medium',
    attachments: List[Tuple[str, bytes]] = None
) -> Dict[str, Any]:
    """
    Create a defect in HP ALM.
    
    Args:
        test_case_id: ID of the test case
        execution_id: ID of the test execution
        summary: Defect summary
        description: Defect description
        severity: Defect severity ('Critical', 'High', 'Medium', 'Low')
        attachments: Optional list of (file_name, file_content) tuples
        
    Returns:
        Dict: Defect creation status and details
    """
    # Get ALM credentials
    try:
        credentials = get_integration_credentials('alm')
    except ValueError as e:
        logger.error(f"Failed to get ALM credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'ALM credentials not found'
        }
    
    try:
        import requests
        import base64
        
        # Establish ALM session
        session = requests.Session()
        
        # Authenticate to ALM
        auth_url = f"{credentials['url']}/qcbin/authentication-point/authenticate"
        auth_headers = {
            'Authorization': f"Basic {base64.b64encode(f'{credentials['username']}:{credentials['password']}'.encode()).decode()}"
        }
        
        auth_response = session.get(auth_url, headers=auth_headers, timeout=30)
        
        if auth_response.status_code != 200:
            logger.error(f"Failed to authenticate to ALM: {auth_response.status_code} - {auth_response.text}")
            return {
                'status': 'error',
                'error': f"Authentication failed: {auth_response.status_code}",
                'details': auth_response.text[:500] if auth_response.text else None
            }
        
        # Create site session
        site_session_url = f"{credentials['url']}/qcbin/rest/site-session"
        site_response = session.post(site_session_url, timeout=30)
        
        if site_response.status_code not in (200, 201):
            logger.error(f"Failed to create ALM site session: {site_response.status_code} - {site_response.text}")
            return {
                'status': 'error',
                'error': f"Site session failed: {site_response.status_code}",
                'details': site_response.text[:500] if site_response.text else None
            }
        
        # Set domain and project context
        domain = credentials.get('domain', 'DEFAULT')
        project = credentials.get('project', 'DEFAULT')
        
        context_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}"
        context_response = session.post(context_url, timeout=30)
        
        if context_response.status_code not in (200, 201):
            logger.error(f"Failed to set ALM context: {context_response.status_code} - {context_response.text}")
            return {
                'status': 'error',
                'error': f"Context setting failed: {context_response.status_code}",
                'details': context_response.text[:500] if context_response.text else None
            }
        
        # Prepare defect data
        defect_data = {
            'Fields': [
                {'Name': 'name', 'values': [{'value': summary}]},
                {'Name': 'description', 'values': [{'value': description}]},
                {'Name': 'severity', 'values': [{'value': severity}]},
                {'Name': 'detected-by', 'values': [{'value': credentials['username']}]},
                {'Name': 'detection-date', 'values': [{'value': datetime.now().strftime('%Y-%m-%d')}]},
                {'Name': 'user-template-08', 'values': [{'value': test_case_id}]},  # Custom field for test case ID
                {'Name': 'user-template-09', 'values': [{'value': execution_id}]}   # Custom field for execution ID
            ]
        }
        
        # Create defect
        defect_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}/defects"
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        
        defect_response = session.post(
            defect_url,
            json=defect_data,
            headers=headers,
            timeout=60
        )
        
        if defect_response.status_code not in (200, 201):
            logger.error(f"Failed to create ALM defect: {defect_response.status_code} - {defect_response.text}")
            return {
                'status': 'error',
                'error': f"Defect creation failed: {defect_response.status_code}",
                'details': defect_response.text[:500] if defect_response.text else None
            }
        
        # Get defect ID from response
        defect_info = defect_response.json()
        defect_id = defect_info.get('Fields', [{}])[0].get('values', [{}])[0].get('value')
        
        # Upload attachments if provided
        attachment_results = []
        if attachments and defect_id:
            for file_name, file_content in attachments:
                try:
                    attachment_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}/defects/{defect_id}/attachments"
                    attachment_headers = {
                        'Content-Type': 'application/octet-stream',
                        'Slug': file_name
                    }
                    
                    attachment_response = session.post(
                        attachment_url,
                        data=file_content,
                        headers=attachment_headers,
                        timeout=60
                    )
                    
                    if attachment_response.status_code in (200, 201):
                        attachment_results.append({
                            'file_name': file_name,
                            'status': 'success'
                        })
                    else:
                        attachment_results.append({
                            'file_name': file_name,
                            'status': 'error',
                            'error': f"Upload failed: {attachment_response.status_code}"
                        })
                except Exception as e:
                    attachment_results.append({
                        'file_name': file_name,
                        'status': 'error',
                        'error': str(e)
                    })
        
        # Create defect record in our database
        db_defect_id = create_defect(
            test_case_id=test_case_id,
            execution_id=execution_id,
            summary=summary,
            description=description,
            severity=severity.lower(),
            external_defect_id=defect_id
        )
        
        logger.info(f"Created ALM defect {defect_id} and database record {db_defect_id}")
        return {
            'status': 'success',
            'defect_id': defect_id,
            'db_defect_id': db_defect_id,
            'attachments': attachment_results
        }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"ALM defect creation failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"ALM defect creation failed: {str(e)}"
        }


def export_test_results_to_alm(
    execution_id: str
) -> Dict[str, Any]:
    """
    Export test execution results to HP ALM.
    
    Args:
        execution_id: ID of the test execution
        
    Returns:
        Dict: Export status and details
    """
    # Get test execution
    try:
        execution = get_test_execution(execution_id)
    except ValueError as e:
        logger.error(f"Failed to get test execution {execution_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Execution not found: {str(e)}"
        }
    
    test_case_id = execution['metadata']['test_case_id']
    
    # Get ALM credentials
    try:
        credentials = get_integration_credentials('alm')
    except ValueError as e:
        logger.error(f"Failed to get ALM credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'ALM credentials not found'
        }
    
    try:
        import requests
        import base64
        
        # Establish ALM session
        session = requests.Session()
        
        # Authenticate to ALM
        auth_url = f"{credentials['url']}/qcbin/authentication-point/authenticate"
        auth_headers = {
            'Authorization': f"Basic {base64.b64encode(f'{credentials['username']}:{credentials['password']}'.encode()).decode()}"
        }
        
        auth_response = session.get(auth_url, headers=auth_headers, timeout=30)
        
        if auth_response.status_code != 200:
            logger.error(f"Failed to authenticate to ALM: {auth_response.status_code} - {auth_response.text}")
            return {
                'status': 'error',
                'error': f"Authentication failed: {auth_response.status_code}",
                'details': auth_response.text[:500] if auth_response.text else None
            }
        
        # Create site session
        site_session_url = f"{credentials['url']}/qcbin/rest/site-session"
        site_response = session.post(site_session_url, timeout=30)
        
        if site_response.status_code not in (200, 201):
            logger.error(f"Failed to create ALM site session: {site_response.status_code} - {site_response.text}")
            return {
                'status': 'error',
                'error': f"Site session failed: {site_response.status_code}",
                'details': site_response.text[:500] if site_response.text else None
            }
        
        # Set domain and project context
        domain = credentials.get('domain', 'DEFAULT')
        project = credentials.get('project', 'DEFAULT')
        
        context_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}"
        context_response = session.post(context_url, timeout=30)
        
        if context_response.status_code not in (200, 201):
            logger.error(f"Failed to set ALM context: {context_response.status_code} - {context_response.text}")
            return {
                'status': 'error',
                'error': f"Context setting failed: {context_response.status_code}",
                'details': context_response.text[:500] if context_response.text else None
            }
        
        # Find test case in ALM
        # Often requires mapping between internal IDs and ALM IDs
        # Use a custom field or naming convention to find the test
        test_name = execution.get('test_case_name', f"Test Case {test_case_id}")
        
        query = f"name='{test_name}'"
        test_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}/tests?query={query}"
        
        test_response = session.get(test_url, timeout=30)
        if test_response.status_code != 200:
            logger.error(f"Failed to find test in ALM: {test_response.status_code} - {test_response.text}")
            return {
                'status': 'error',
                'error': f"Test lookup failed: {test_response.status_code}",
                'details': test_response.text[:500] if test_response.text else None
            }
        
        test_data = test_response.json()
        entities = test_data.get('entities', [])
        
        if not entities:
            logger.error(f"Test '{test_name}' not found in ALM")
            return {
                'status': 'error',
                'error': f"Test '{test_name}' not found in ALM"
            }
        
        # Get ALM test ID
        test_entity = entities[0]
        alm_test_id = test_entity.get('Fields', [{}])[0].get('values', [{}])[0].get('value')
        
        if not alm_test_id:
            logger.error("Failed to get ALM test ID")
            return {
                'status': 'error',
                'error': "Failed to get ALM test ID"
            }
        
        # Create test run
        run_data = {
            'Fields': [
                {'Name': 'test-id', 'values': [{'value': alm_test_id}]},
                {'Name': 'name', 'values': [{'value': f"Run of {test_name} - {execution_id}"}]},
                {'Name': 'status', 'values': [{'value': execution['status'].upper()}]},
                {'Name': 'owner', 'values': [{'value': credentials['username']}]},
                {'Name': 'execution-date', 'values': [{'value': datetime.now().strftime('%Y-%m-%d')}]},
                {'Name': 'execution-time', 'values': [{'value': datetime.now().strftime('%H:%M:%S')}]},
                {'Name': 'user-template-01', 'values': [{'value': execution_id}]}  # Custom field for execution ID
            ]
        }
        
        run_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}/runs"
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        
        run_response = session.post(
            run_url,
            json=run_data,
            headers=headers,
            timeout=60
        )
        
        if run_response.status_code not in (200, 201):
            logger.error(f"Failed to create ALM test run: {run_response.status_code} - {run_response.text}")
            return {
                'status': 'error',
                'error': f"Run creation failed: {run_response.status_code}",
                'details': run_response.text[:500] if run_response.text else None
            }
        
        # Get run ID
        run_info = run_response.json()
        run_id = run_info.get('Fields', [{}])[0].get('values', [{}])[0].get('value')
        
        # Upload execution steps if available
        steps = execution.get('execution_steps', [])
        step_results = []
        
        for i, step in enumerate(steps, 1):
            try:
                step_status = step.get('status', 'pending').upper()
                step_description = step.get('description', f"Step {i}")
                
                step_data = {
                    'Fields': [
                        {'Name': 'run-id', 'values': [{'value': run_id}]},
                        {'Name': 'name', 'values': [{'value': f"Step {i}"}]},
                        {'Name': 'description', 'values': [{'value': step_description}]},
                        {'Name': 'status', 'values': [{'value': step_status}]},
                        {'Name': 'execution-time', 'values': [{'value': datetime.now().strftime('%H:%M:%S')}]}
                    ]
                }
                
                step_url = f"{credentials['url']}/qcbin/rest/domains/{domain}/projects/{project}/run-steps"
                
                step_response = session.post(
                    step_url,
                    json=step_data,
                    headers=headers,
                    timeout=30
                )
                
                if step_response.status_code in (200, 201):
                    step_results.append({
                        'step': i,
                        'status': 'success'
                    })
                else:
                    step_results.append({
                        'step': i,
                        'status': 'error',
                        'error': f"Creation failed: {step_response.status_code}"
                    })
            except Exception as e:
                step_results.append({
                    'step': i,
                    'status': 'error',
                    'error': str(e)
                })
        
        logger.info(f"Exported test execution {execution_id} to ALM as run {run_id}")
        return {
            'status': 'success',
            'execution_id': execution_id,
            'alm_test_id': alm_test_id,
            'alm_run_id': run_id,
            'steps': step_results
        }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"ALM export failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"ALM export failed: {str(e)}"
        }


def execute_uft_test(
    test_path: str,
    input_parameters: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Execute a UFT test.
    
    Args:
        test_path: Path to the UFT test
        input_parameters: Optional input parameters for the test
        
    Returns:
        Dict: Execution status and details
    """
    # Get UFT credentials
    try:
        credentials = get_integration_credentials('uft')
    except ValueError as e:
        logger.error(f"Failed to get UFT credentials: {str(e)}")
        return {
            'status': 'error',
            'error': 'UFT credentials not found'
        }
    
    try:
        import requests
        
        # Generate job ID
        job_id = f"uft_{generate_unique_id()}"
        
        # Store job in database
        db_job_id = store_uft_job(
            job_id=job_id,
            script_path=test_path
        )
        
        # Prepare execution request
        host = credentials['host']
        port = credentials['port']
        
        execution_url = f"http://{host}:{port}/api/v1/tests/run"
        
        execution_data = {
            'testPath': test_path,
            'jobId': job_id
        }
        
        if input_parameters:
            execution_data['inputParameters'] = input_parameters
        
        headers = {'Content-Type': 'application/json'}
        
        # Execute test
        response = requests.post(
            execution_url,
            json=execution_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code not in (200, 201, 202):
            logger.error(f"Failed to execute UFT test: {response.status_code} - {response.text}")
            
            # Update job status
            update_uft_job_status(
                job_id=job_id,
                status='failed',
                error_message=f"API error: {response.status_code} - {response.text[:500] if response.text else 'No response'}"
            )
            
            return {
                'status': 'error',
                'error': f"Execution failed: {response.status_code}",
                'details': response.text[:500] if response.text else None,
                'job_id': job_id
            }
        
        # Get execution details
        execution_info = response.json()
        execution_status = execution_info.get('status', 'unknown')
        
        # For asynchronous execution, status will be 'running'
        if execution_status.lower() == 'running':
            logger.info(f"UFT test execution {job_id} started successfully")
            return {
                'status': 'success',
                'job_id': job_id,
                'execution_status': 'running',
                'message': 'Test execution started successfully'
            }
        else:
            # For synchronous execution, update job status
            update_uft_job_status(
                job_id=job_id,
                status='completed',
                result=execution_status,
                logs_path=execution_info.get('resultsPath')
            )
            
            logger.info(f"UFT test execution {job_id} completed with status {execution_status}")
            return {
                'status': 'success',
                'job_id': job_id,
                'execution_status': execution_status,
                'results_path': execution_info.get('resultsPath')
            }
    
    except ImportError:
        logger.error("Requests package not available")
        return {
            'status': 'error',
            'error': "Requests package not available"
        }
    except Exception as e:
        logger.error(f"UFT test execution failed: {str(e)}")
        
        # Try to update job status
        try:
            if job_id:
                update_uft_job_status(
                    job_id=job_id,
                    status='failed',
                    error_message=str(e)
                )
        except:
            pass
        
        return {
            'status': 'error',
            'error': f"UFT test execution failed: {str(e)}"
        }

# End of Part 6: Integration System Connectors
# ------------- Part 7: Defect Management & Reporting -------------

def create_defect(
    test_case_id: str,
    execution_id: str,
    summary: str,
    description: str,
    severity: str,
    assigned_to: str = None,
    status: str = 'open',
    steps_to_reproduce: str = None,
    screenshots: List[str] = None,
    external_defect_id: str = None
) -> int:
    """
    Create a defect record in the database.
    
    Args:
        test_case_id: ID of the test case
        execution_id: ID of the test execution
        summary: Defect summary
        description: Defect description
        severity: Defect severity ('critical', 'high', 'medium', 'low')
        assigned_to: User to assign the defect to
        status: Initial status (default: 'open')
        steps_to_reproduce: Steps to reproduce the defect
        screenshots: List of screenshot object names
        external_defect_id: ID of the defect in external system (e.g., JIRA)
        
    Returns:
        int: ID of the created defect
    """
    query = """
    INSERT INTO defects 
    (test_case_id, execution_id, defect_id, summary, description, severity, 
     assigned_to, status, steps_to_reproduce, screenshots, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    
    defect_id = update_database(
        query=query,
        params=(
            test_case_id,
            execution_id,
            external_defect_id,
            summary,
            description,
            severity,
            assigned_to,
            status,
            steps_to_reproduce,
            json.dumps(screenshots) if screenshots else None,
            datetime.now()
        ),
        return_id=True
    )
    
    logger.info(f"Created defect for test case {test_case_id} with ID {defect_id}")
    return defect_id


def get_defect(defect_id: int) -> Dict[str, Any]:
    """
    Get defect details.
    
    Args:
        defect_id: ID of the defect
        
    Returns:
        Dict: Defect details
    """
    query = """
    SELECT id, test_case_id, execution_id, defect_id as external_defect_id, 
           summary, description, severity, assigned_to, status, resolution,
           steps_to_reproduce, screenshots, comments, created_at, updated_at
    FROM defects
    WHERE id = %s
    """
    
    result = query_database(
        query=query,
        params=(defect_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Defect {defect_id} not found")
        raise ValueError(f"Defect {defect_id} not found")
    
    # Format datetime fields
    if result['created_at']:
        result['created_at'] = result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at']
    
    if result['updated_at']:
        result['updated_at'] = result['updated_at'].isoformat() if isinstance(result['updated_at'], datetime) else result['updated_at']
    
    # Parse screenshots
    if result['screenshots']:
        try:
            result['screenshots'] = json.loads(result['screenshots'])
            
            # Add URLs for screenshots
            screenshot_urls = []
            for screenshot_path in result['screenshots']:
                try:
                    # Extract bucket and object name
                    parts = screenshot_path.split('/')
                    if len(parts) >= 2:
                        bucket_name = DEFAULT_BUCKET  # Assume default bucket
                        object_name = screenshot_path
                        
                        # Generate URL
                        url = get_storage_object_url(object_name, bucket_name, 3600)
                        screenshot_urls.append({
                            'path': screenshot_path,
                            'url': url
                        })
                except Exception as e:
                    logger.warning(f"Failed to generate URL for screenshot {screenshot_path}: {str(e)}")
            
            result['screenshot_urls'] = screenshot_urls
        except Exception as e:
            logger.warning(f"Failed to parse screenshots JSON: {str(e)}")
    
    # Get test case details
    try:
        test_case = get_test_case_by_id(result['test_case_id'])
        result['test_case'] = {
            'id': test_case['db_metadata']['id'],
            'name': test_case['db_metadata']['name'],
            'version': test_case['db_metadata']['version']
        }
    except Exception as e:
        logger.warning(f"Failed to get test case details: {str(e)}")
        result['test_case'] = {
            'id': result['test_case_id']
        }
    
    # Get execution details if available
    if result['execution_id']:
        try:
            execution = get_test_execution(result['execution_id'])
            result['execution'] = {
                'id': result['execution_id'],
                'status': execution['db_metadata']['status'],
                'executed_at': execution['db_metadata']['executed_at']
            }
        except Exception as e:
            logger.warning(f"Failed to get execution details: {str(e)}")
            result['execution'] = {
                'id': result['execution_id']
            }
    
    logger.info(f"Retrieved defect {defect_id}")
    return result


def get_defects(
    test_case_id: str = None,
    status: str = None,
    severity: str = None,
    assigned_to: str = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get defects with optional filtering.
    
    Args:
        test_case_id: Optional test case ID filter
        status: Optional status filter
        severity: Optional severity filter
        assigned_to: Optional assignee filter
        limit: Maximum number of defects to return
        offset: Offset for pagination
        
    Returns:
        List[Dict]: List of defects
    """
    base_query = """
    SELECT id, test_case_id, execution_id, defect_id as external_defect_id, 
           summary, description, severity, assigned_to, status, resolution,
           created_at, updated_at
    FROM defects
    WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if test_case_id:
        base_query += " AND test_case_id = %s"
        params.append(test_case_id)
    
    if status:
        base_query += " AND status = %s"
        params.append(status)
    
    if severity:
        base_query += " AND severity = %s"
        params.append(severity)
    
    if assigned_to:
        base_query += " AND assigned_to = %s"
        params.append(assigned_to)
    
    # Add sorting and pagination
    base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.append(limit)
    params.append(offset)
    
    results = query_database(
        query=base_query,
        params=params
    )
    
    # Format datetime fields
    for result in results:
        if result['created_at']:
            result['created_at'] = result['created_at'].isoformat() if isinstance(result['created_at'], datetime) else result['created_at']
        
        if result['updated_at']:
            result['updated_at'] = result['updated_at'].isoformat() if isinstance(result['updated_at'], datetime) else result['updated_at']
    
    filters = []
    if test_case_id:
        filters.append(f"test case '{test_case_id}'")
    if status:
        filters.append(f"status '{status}'")
    if severity:
        filters.append(f"severity '{severity}'")
    if assigned_to:
        filters.append(f"assigned to '{assigned_to}'")
    
    filter_info = f" for {' and '.join(filters)}" if filters else ""
    logger.info(f"Retrieved {len(results)} defects{filter_info}")
    return results


def update_defect_status(
    defect_id: int,
    status: str,
    resolution: str = None,
    comments: str = None
) -> bool:
    """
    Update the status of a defect.
    
    Args:
        defect_id: ID of the defect
        status: New status ('open', 'in_progress', 'resolved', 'closed')
        resolution: Optional resolution information
        comments: Optional comments
        
    Returns:
        bool: True if update was successful
    """
    query = """
    UPDATE defects
    SET status = %s, resolution = %s, comments = %s, updated_at = NOW()
    WHERE id = %s
    """
    
    affected_rows = update_database(
        query=query,
        params=(status, resolution, comments, defect_id)
    )
    
    if affected_rows == 0:
        logger.warning(f"No defect was updated for ID {defect_id}")
        return False
    
    logger.info(f"Updated status of defect {defect_id} to '{status}'")
    return True


def assign_defect(
    defect_id: int,
    assigned_to: str
) -> bool:
    """
    Assign a defect to a user.
    
    Args:
        defect_id: ID of the defect
        assigned_to: User to assign the defect to
        
    Returns:
        bool: True if assignment was successful
    """
    query = """
    UPDATE defects
    SET assigned_to = %s, updated_at = NOW()
    WHERE id = %s
    """
    
    affected_rows = update_database(
        query=query,
        params=(assigned_to, defect_id)
    )
    
    if affected_rows == 0:
        logger.warning(f"No defect was updated for ID {defect_id}")
        return False
    
    logger.info(f"Assigned defect {defect_id} to {assigned_to}")
    return True


def add_defect_comment(
    defect_id: int,
    comment: str
) -> bool:
    """
    Add a comment to a defect.
    
    Args:
        defect_id: ID of the defect
        comment: Comment text
        
    Returns:
        bool: True if comment was added successfully
    """
    # First get existing comments
    query = """
    SELECT comments
    FROM defects
    WHERE id = %s
    """
    
    result = query_database(
        query=query,
        params=(defect_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Defect {defect_id} not found")
        return False
    
    # Parse existing comments or create new array
    existing_comments = []
    if result['comments']:
        try:
            existing_comments = json.loads(result['comments'])
        except:
            logger.warning(f"Failed to parse existing comments for defect {defect_id}")
    
    # Add new comment with timestamp
    new_comment = {
        'text': comment,
        'timestamp': datetime.now().isoformat(),
        'user': os.environ.get('USER', 'system')
    }
    
    existing_comments.append(new_comment)
    
    # Update defect with new comments
    update_query = """
    UPDATE defects
    SET comments = %s, updated_at = NOW()
    WHERE id = %s
    """
    
    affected_rows = update_database(
        query=update_query,
        params=(json.dumps(existing_comments), defect_id)
    )
    
    if affected_rows == 0:
        logger.warning(f"Failed to add comment to defect {defect_id}")
        return False
    
    logger.info(f"Added comment to defect {defect_id}")
    return True


def link_defect_to_requirement(
    defect_id: int,
    requirement_id: str
) -> bool:
    """
    Link a defect to a requirement.
    
    Args:
        defect_id: ID of the defect
        requirement_id: ID of the requirement
        
    Returns:
        bool: True if link was created
    """
    # Check if requirement exists
    try:
        get_requirement_by_id(requirement_id)
    except ValueError:
        logger.error(f"Requirement {requirement_id} not found")
        return False
    
    # Add relationship data in defect record
    query = """
    SELECT linked_requirements
    FROM defects
    WHERE id = %s
    """
    
    result = query_database(
        query=query,
        params=(defect_id,),
        fetch_one=True
    )
    
    if not result:
        logger.error(f"Defect {defect_id} not found")
        return False
    
    # Parse existing links or create new array
    existing_links = []
    if result.get('linked_requirements'):
        try:
            existing_links = json.loads(result['linked_requirements'])
        except:
            logger.warning(f"Failed to parse existing links for defect {defect_id}")
    
    # Check if already linked
    if requirement_id in existing_links:
        logger.info(f"Defect {defect_id} already linked to requirement {requirement_id}")
        return True
    
    # Add new link
    existing_links.append(requirement_id)
    
    # Update defect with new links
    update_query = """
    UPDATE defects
    SET linked_requirements = %s, updated_at = NOW()
    WHERE id = %s
    """
    
    affected_rows = update_database(
        query=update_query,
        params=(json.dumps(existing_links), defect_id)
    )
    
    if affected_rows == 0:
        logger.warning(f"Failed to update defect {defect_id}")
        return False
    
    logger.info(f"Linked defect {defect_id} to requirement {requirement_id}")
    return True


def get_defect_statistics(
    start_date: datetime = None,
    end_date: datetime = None
) -> Dict[str, Any]:
    """
    Get statistics for defects.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        Dict: Statistics about defects
    """
    # Base query
    base_query = """
    SELECT 
        COUNT(*) as total_defects,
        SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_defects,
        SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_defects,
        SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved_defects,
        SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_defects,
        SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical_defects,
        SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high_defects,
        SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium_defects,
        SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low_defects
    FROM defects
    WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if start_date:
        base_query += " AND created_at >= %s"
        params.append(start_date)
    
    if end_date:
        base_query += " AND created_at <= %s"
        params.append(end_date)
    
    # Execute query
    stats = query_database(base_query, params, fetch_one=True)
    
    # Get defects by test case
    by_test_case_query = """
    SELECT 
        test_case_id,
        COUNT(*) as defect_count
    FROM defects
    WHERE 1=1
    """
    
    by_test_case_params = []
    
    # Add filters
    if start_date:
        by_test_case_query += " AND created_at >= %s"
        by_test_case_params.append(start_date)
    
    if end_date:
        by_test_case_query += " AND created_at <= %s"
        by_test_case_params.append(end_date)
    
    by_test_case_query += " GROUP BY test_case_id ORDER BY defect_count DESC LIMIT 10"
    
    # Execute by test case query
    by_test_case = query_database(by_test_case_query, by_test_case_params)
    
    # Add to statistics
    stats['by_test_case'] = by_test_case
    
    # Get trend data (daily defects)
    trend_query = """
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as defects,
        SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
        SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high
    FROM defects
    WHERE 1=1
    """
    
    trend_params = []
    
    # Add filters
    if start_date:
        trend_query += " AND created_at >= %s"
        trend_params.append(start_date)
    
    if end_date:
        trend_query += " AND created_at <= %s"
        trend_params.append(end_date)
    
    trend_query += " GROUP BY DATE(created_at) ORDER BY DATE(created_at)"
    
    # Execute trend query
    trend_data = query_database(trend_query, trend_params)
    
    # Format dates in trend data
    for item in trend_data:
        if isinstance(item['date'], datetime):
            item['date'] = item['date'].strftime('%Y-%m-%d')
    
    # Add trend data to statistics
    stats['trend'] = trend_data
    
    # Calculate age metrics for open defects
    age_query = """
    SELECT 
        EXTRACT(DAY FROM NOW() - created_at) as age_days,
        COUNT(*) as count
    FROM defects
    WHERE status IN ('open', 'in_progress')
    GROUP BY age_days
    ORDER BY age_days
    """
    
    age_data = query_database(age_query)
    
    # Categorize by age
    age_distribution = {
        '0-7': 0,
        '8-14': 0,
        '15-30': 0,
        '31-60': 0,
        '60+': 0
    }
    
    for item in age_data:
        age = item['age_days']
        count = item['count']
        
        if age <= 7:
            age_distribution['0-7'] += count
        elif age <= 14:
            age_distribution['8-14'] += count
        elif age <= 30:
            age_distribution['15-30'] += count
        elif age <= 60:
            age_distribution['31-60'] += count
        else:
            age_distribution['60+'] += count
    
    stats['age_distribution'] = age_distribution
    
    # Get average resolution time
    resolution_query = """
    SELECT AVG(EXTRACT(EPOCH FROM updated_at - created_at)) as avg_resolution_time
    FROM defects
    WHERE status IN ('resolved', 'closed')
    """
    
    resolution_data = query_database(resolution_query, fetch_one=True)
    
    if resolution_data and resolution_data['avg_resolution_time']:
        # Convert seconds to days
        stats['avg_resolution_days'] = resolution_data['avg_resolution_time'] / (60 * 60 * 24)
    else:
        stats['avg_resolution_days'] = 0
    
    logger.info(f"Retrieved defect statistics with {stats['total_defects']} total defects")
    return stats


def analyze_defect_trends(
    days: int = 90
) -> Dict[str, Any]:
    """
    Analyze defect trends and patterns.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Dict: Trend analysis and insights
    """
    start_date = datetime.now() - timedelta(days=days)
    
    # Get basic statistics for the period
    stats = get_defect_statistics(start_date=start_date)
    
    # Prepare analysis results
    analysis = {
        'period_days': days,
        'total_defects': stats['total_defects'],
        'open_defects': stats['open_defects'],
        'critical_high_defects': stats['critical_defects'] + stats['high_defects'],
        'trend_data': stats['trend'],
        'insights': []
    }
    
    # Analyze defect injection rate trend
    if len(stats['trend']) >= 7:
        # Calculate 7-day moving average
        trend_data = stats['trend']
        moving_averages = []
        
        for i in range(len(trend_data) - 6):
            window = trend_data[i:i+7]
            avg = sum(item['defects'] for item in window) / 7
            date = window[-1]['date']
            moving_averages.append({
                'date': date,
                'average': avg
            })
        
        analysis['moving_average'] = moving_averages
        
        # Check for significant increase in defect rate
        if len(moving_averages) >= 2:
            recent_avg = moving_averages[-1]['average']
            previous_avg = moving_averages[-2]['average']
            
            if recent_avg > 0 and previous_avg > 0:
                change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
                
                if change_pct >= 20:
                    analysis['insights'].append({
                        'type': 'defect_rate_increase',
                        'message': f"Defect rate has increased by {change_pct:.1f}% in the last 7 days.",
                        'severity': 'warning'
                    })
    
    # Analyze critical/high defect trends
    critical_high_ratio = (stats['critical_defects'] + stats['high_defects']) / stats['total_defects'] * 100 if stats['total_defects'] > 0 else 0
    
    if critical_high_ratio >= 30:
        analysis['insights'].append({
            'type': 'high_critical_defects',
            'message': f"{critical_high_ratio:.1f}% of defects are Critical or High severity.",
            'severity': 'warning'
        })
    
    # Analyze defect age
    if stats['age_distribution']['31-60'] + stats['age_distribution']['60+'] >= 5:
        old_defects = stats['age_distribution']['31-60'] + stats['age_distribution']['60+']
        analysis['insights'].append({
            'type': 'aging_defects',
            'message': f"There are {old_defects} open defects older than 30 days.",
            'severity': 'warning'
        })
    
    # Analyze test cases with most defects
    if stats['by_test_case'] and len(stats['by_test_case']) > 0:
        top_test_case = stats['by_test_case'][0]
        if top_test_case['defect_count'] >= 3:
            analysis['insights'].append({
                'type': 'problematic_test_case',
                'message': f"Test case {top_test_case['test_case_id']} has {top_test_case['defect_count']} defects.",
                'severity': 'info',
                'test_case_id': top_test_case['test_case_id']
            })
    
    # Calculate defect resolution rate
    if stats['total_defects'] > 0:
        resolution_rate = (stats['resolved_defects'] + stats['closed_defects']) / stats['total_defects'] * 100
        analysis['resolution_rate'] = resolution_rate
        
        if resolution_rate < 50:
            analysis['insights'].append({
                'type': 'low_resolution_rate',
                'message': f"Only {resolution_rate:.1f}% of defects have been resolved or closed.",
                'severity': 'warning'
            })
    
    logger.info(f"Completed defect trend analysis over {days} days")
    return analysis


def generate_defect_report(
    start_date: datetime = None,
    end_date: datetime = None,
    test_case_id: str = None,
    format_type: str = 'json'
) -> Dict[str, Any]:
    """
    Generate a defect report.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        test_case_id: Optional test case ID filter
        format_type: Report format ('json', 'html', 'csv')
        
    Returns:
        Dict: Report data and metadata
    """
    # If no dates provided, use last 30 days
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
    elif not end_date:
        end_date = datetime.now()
    elif not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Build query
    base_query = """
    SELECT 
        d.id, d.test_case_id, d.execution_id, d.defect_id as external_defect_id,
        d.summary, d.description, d.severity, d.assigned_to, d.status, d.resolution,
        d.created_at, d.updated_at,
        tc.name as test_case_name
    FROM defects d
    LEFT JOIN test_cases tc ON d.test_case_id = tc.id AND tc.status = 'active'
    WHERE d.created_at BETWEEN %s AND %s
    """
    
    params = [start_date, end_date]
    
    if test_case_id:
        base_query += " AND d.test_case_id = %s"
        params.append(test_case_id)
    
    base_query += " ORDER BY d.created_at DESC"
    
    # Execute query
    defects = query_database(base_query, params)
    
    # Format dates
    for defect in defects:
        if defect['created_at']:
            defect['created_at'] = defect['created_at'].isoformat() if isinstance(defect['created_at'], datetime) else defect['created_at']
        
        if defect['updated_at']:
            defect['updated_at'] = defect['updated_at'].isoformat() if isinstance(defect['updated_at'], datetime) else defect['updated_at']
    
    # Get statistics
    stats = get_defect_statistics(start_date, end_date)
    
    # Set up report metadata
    report = {
        'metadata': {
            'report_type': 'defect',
            'generated_at': datetime.now().isoformat(),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'test_case_id': test_case_id,
            'format': format_type
        },
        'summary': {
            'total_defects': stats['total_defects'],
            'open_defects': stats['open_defects'],
            'in_progress_defects': stats['in_progress_defects'],
            'resolved_defects': stats['resolved_defects'],
            'closed_defects': stats['closed_defects'],
            'critical_defects': stats['critical_defects'],
            'high_defects': stats['high_defects'],
            'medium_defects': stats['medium_defects'],
            'low_defects': stats['low_defects'],
            'avg_resolution_days': stats['avg_resolution_days']
        },
        'defects': defects,
        'trend': stats['trend'],
        'by_test_case': stats['by_test_case'],
        'age_distribution': stats['age_distribution']
    }
    
    # Generate formatted output if not JSON
    if format_type == 'html':
        try:
            # Simple HTML template for the report
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Defect Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .summary {{ display: flex; flex-wrap: wrap; }}
                    .stat-box {{ margin: 10px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; width: 200px; }}
                    .stat-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                    .critical {{ color: #d9534f; }}
                    .high {{ color: #f0ad4e; }}
                    .medium {{ color: #5bc0de; }}
                    .low {{ color: #5cb85c; }}
                </style>
            </head>
            <body>
                <h1>Defect Report</h1>
                <p>Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
                
                <h2>Summary</h2>
                <div class="summary">
                    <div class="stat-box">
                        <div>Total Defects</div>
                        <div class="stat-value">{stats['total_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Open</div>
                        <div class="stat-value">{stats['open_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>In Progress</div>
                        <div class="stat-value">{stats['in_progress_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Resolved</div>
                        <div class="stat-value">{stats['resolved_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Closed</div>
                        <div class="stat-value">{stats['closed_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Critical</div>
                        <div class="stat-value critical">{stats['critical_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>High</div>
                        <div class="stat-value high">{stats['high_defects']}</div>
                    </div>
                </div>
                
                <h2>Defects by Severity</h2>
                <table>
                    <tr>
                        <th>Severity</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
                    <tr>
                        <td>Critical</td>
                        <td>{stats['critical_defects']}</td>
                        <td>{stats['critical_defects'] / stats['total_defects'] * 100:.1f}% if stats['total_defects'] > 0 else 0}</td>
                    </tr>
                    <tr>
                        <td>High</td>
                        <td>{stats['high_defects']}</td>
                        <td>{stats['high_defects'] / stats['total_defects'] * 100:.1f}% if stats['total_defects'] > 0 else 0}</td>
                    </tr>
                    <tr>
                        <td>Medium</td>
                        <td>{stats['medium_defects']}</td>
                        <td>{stats['medium_defects'] / stats['total_defects'] * 100:.1f}% if stats['total_defects'] > 0 else 0}</td>
                    </tr>
                    <tr>
                        <td>Low</td>
                        <td>{stats['low_defects']}</td>
                        <td>{stats['low_defects'] / stats['total_defects'] * 100:.1f}% if stats['total_defects'] > 0 else 0}</td>
                    </tr>
                </table>
                
                <h2>Defects by Age (Open and In Progress)</h2>
                <table>
                    <tr>
                        <th>Age Range (days)</th>
                        <th>Count</th>
                    </tr>
                    <tr>
                        <td>0-7</td>
                        <td>{stats['age_distribution']['0-7']}</td>
                    </tr>
                    <tr>
                        <td>8-14</td>
                        <td>{stats['age_distribution']['8-14']}</td>
                    </tr>
                    <tr>
                        <td>15-30</td>
                        <td>{stats['age_distribution']['15-30']}</td>
                    </tr>
                    <tr>
                        <td>31-60</td>
                        <td>{stats['age_distribution']['31-60']}</td>
                    </tr>
                    <tr>
                        <td>60+</td>
                        <td>{stats['age_distribution']['60+']}</td>
                    </tr>
                </table>
                
                <h2>Top Test Cases with Defects</h2>
                <table>
                    <tr>
                        <th>Test Case ID</th>
                        <th>Defect Count</th>
                    </tr>
                    {''.join(f"<tr><td>{tc['test_case_id']}</td><td>{tc['defect_count']}</td></tr>" for tc in stats['by_test_case'][:5])}
                </table>
                
                <h2>Defect Details</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Summary</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Test Case</th>
                        <th>Created</th>
                    </tr>
                    {''.join(f"<tr><td>{d['id']}</td><td>{d['summary']}</td><td>{d['severity']}</td><td>{d['status']}</td><td>{d.get('test_case_name', d['test_case_id'])}</td><td>{d['created_at'][:10] if d['created_at'] else ''}</td></tr>" for d in defects[:50])}
                </table>
            </body>
            </html>
            """
            
            # Store HTML report in object storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"defect_report_{timestamp}.html"
            
            upload_data_to_storage(
                data=html_content.encode('utf-8'),
                object_name=report_filename,
                bucket_name=DEFAULT_BUCKET,
                content_type='text/html'
            )
            
            # Add URL to the report
            report['html_url'] = get_storage_object_url(report_filename, DEFAULT_BUCKET, 86400)  # 24 hours
            report['html_filename'] = report_filename
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {str(e)}")
            report['error'] = f"Failed to generate HTML report: {str(e)}"
    
    elif format_type == 'csv':
        try:
            import csv
            import io
            
            # Create CSV for defects
            output = io.StringIO()
            
            # Define columns to include
            fieldnames = ['id', 'summary', 'severity', 'status', 'assigned_to', 'test_case_id', 'test_case_name', 'created_at']
            
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for defect in defects:
                writer.writerow(defect)
            
            csv_content = output.getvalue()
            
            # Store CSV report in object storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"defect_report_{timestamp}.csv"
            
            upload_data_to_storage(
                data=csv_content.encode('utf-8'),
                object_name=report_filename,
                bucket_name=DEFAULT_BUCKET,
                content_type='text/csv'
            )
            
            # Add URL to the report
            report['csv_url'] = get_storage_object_url(report_filename, DEFAULT_BUCKET, 86400)  # 24 hours
            report['csv_filename'] = report_filename
            
        except Exception as e:
            logger.error(f"Failed to generate CSV report: {str(e)}")
            report['error'] = f"Failed to generate CSV report: {str(e)}"
    
    logger.info(f"Generated defect report with {len(defects)} defects")
    return report


def generate_test_summary_report(
    start_date: datetime = None,
    end_date: datetime = None,
    format_type: str = 'json'
) -> Dict[str, Any]:
    """
    Generate a comprehensive test summary report.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        format_type: Report format ('json', 'html', 'csv')
        
    Returns:
        Dict: Report data and metadata
    """
    # If no dates provided, use last 30 days
    if not start_date and not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
    elif not end_date:
        end_date = datetime.now()
    elif not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get execution statistics
    execution_stats = get_test_execution_statistics(start_date, end_date)
    
    # Get defect statistics
    defect_stats = get_defect_statistics(start_date, end_date)
    
    # Get requirement coverage statistics
    coverage_stats = get_requirements_coverage_statistics()
    
    # Build report
    report = {
        'metadata': {
            'report_type': 'test_summary',
            'generated_at': datetime.now().isoformat(),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'format': format_type
        },
        'execution_summary': {
            'total_executions': execution_stats['total_executions'],
            'passed': execution_stats['passed'],
            'failed': execution_stats['failed'],
            'blocked': execution_stats['blocked'],
            'error': execution_stats.get('error', 0),
            'pass_rate': execution_stats['pass_rate'],
            'avg_duration': execution_stats['avg_duration'],
            'execution_trend': execution_stats['trend']
        },
        'defect_summary': {
            'total_defects': defect_stats['total_defects'],
            'open_defects': defect_stats['open_defects'],
            'in_progress_defects': defect_stats['in_progress_defects'],
            'resolved_defects': defect_stats['resolved_defects'],
            'closed_defects': defect_stats['closed_defects'],
            'critical_defects': defect_stats['critical_defects'],
            'high_defects': defect_stats['high_defects'],
            'medium_defects': defect_stats['medium_defects'],
            'low_defects': defect_stats['low_defects'],
            'defect_trend': defect_stats['trend'],
            'by_test_case': defect_stats['by_test_case']
        },
        'coverage_summary': {
            'total_requirements': coverage_stats['total_requirements'],
            'covered_requirements': coverage_stats['covered_requirements'],
            'coverage_percentage': coverage_stats['coverage_percentage'],
            'most_test_cases': coverage_stats['most_test_cases']
        }
    }
    
    # Get test cases with most failures
    failure_query = """
    SELECT 
        tc.id as test_case_id, 
        tc.name as test_case_name,
        COUNT(te.execution_id) as execution_count,
        SUM(CASE WHEN te.status = 'failed' THEN 1 ELSE 0 END) as fail_count,
        (SUM(CASE WHEN te.status = 'failed' THEN 1 ELSE 0 END) * 100.0 / COUNT(te.execution_id)) as failure_rate
    FROM test_cases tc
    JOIN test_executions te ON tc.id = te.test_case_id
    WHERE te.executed_at BETWEEN %s AND %s
    GROUP BY tc.id, tc.name
    HAVING COUNT(te.execution_id) >= 3
    ORDER BY failure_rate DESC
    LIMIT 10
    """
    
    failure_data = query_database(failure_query, (start_date, end_date))
    report['failing_test_cases'] = failure_data
    
    # Calculate overall quality score (simple weighted formula)
    total_score = 0
    max_score = 0
    
    # Pass rate (40% weight)
    pass_rate_score = min(execution_stats['pass_rate'] / 100 * 40, 40)
    total_score += pass_rate_score
    max_score += 40
    
    # Coverage (30% weight)
    coverage_score = min(coverage_stats['coverage_percentage'] / 100 * 30, 30)
    total_score += coverage_score
    max_score += 30
    
    # Defect resolution (20% weight)
    if defect_stats['total_defects'] > 0:
        resolution_rate = (defect_stats['resolved_defects'] + defect_stats['closed_defects']) / defect_stats['total_defects'] * 100
        resolution_score = min(resolution_rate / 100 * 20, 20)
        total_score += resolution_score
        max_score += 20
    
    # Critical defects (10% weight)
    if defect_stats['total_defects'] > 0:
        critical_rate = (defect_stats['critical_defects'] + defect_stats['high_defects']) / defect_stats['total_defects'] * 100
        critical_score = min((100 - critical_rate) / 100 * 10, 10)  # Inverse - fewer critical issues is better
        total_score += critical_score
        max_score += 10
    
    # Calculate final score
    quality_score = (total_score / max_score) * 100 if max_score > 0 else 0
    
    report['quality_score'] = {
        'score': round(quality_score, 1),
        'components': {
            'pass_rate': round(pass_rate_score, 1),
            'coverage': round(coverage_score, 1),
            'resolution': round(resolution_score, 1) if 'resolution_score' in locals() else 0,
            'critical_defects': round(critical_score, 1) if 'critical_score' in locals() else 0
        }
    }
    
    # Generate formatted output if not JSON
    if format_type == 'html':
        try:
            # Simple HTML template for the report
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Summary Report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .summary {{ display: flex; flex-wrap: wrap; }}
                    .stat-box {{ margin: 10px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; width: 200px; }}
                    .stat-value {{ font-size: 24px; font-weight: bold; margin: 10px 0; }}
                    .quality-score {{ font-size: 36px; text-align: center; margin: 20px 0; }}
                    .quality-score-box {{ padding: 20px; border-radius: 10px; margin: 20px auto; width: 200px; text-align: center; }}
                    .good {{ background-color: #dff0d8; color: #3c763d; }}
                    .average {{ background-color: #fcf8e3; color: #8a6d3b; }}
                    .poor {{ background-color: #f2dede; color: #a94442; }}
                </style>
            </head>
            <body>
                <h1>Test Summary Report</h1>
                <p>Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>
                
                <div class="quality-score-box {
                        'good' if quality_score >= 80 else 
                        'average' if quality_score >= 60 else 
                        'poor'
                    }">
                    <div>Overall Quality Score</div>
                    <div class="quality-score">{round(quality_score, 1)}%</div>
                </div>
                
                <h2>Test Execution Summary</h2>
                <div class="summary">
                    <div class="stat-box">
                        <div>Total Executions</div>
                        <div class="stat-value">{execution_stats['total_executions']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Pass Rate</div>
                        <div class="stat-value">{execution_stats['pass_rate']:.1f}%</div>
                    </div>
                    <div class="stat-box">
                        <div>Passed</div>
                        <div class="stat-value">{execution_stats['passed']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Failed</div>
                        <div class="stat-value">{execution_stats['failed']}</div>
                    </div>
                </div>
                
                <h2>Requirements Coverage</h2>
                <div class="summary">
                    <div class="stat-box">
                        <div>Total Requirements</div>
                        <div class="stat-value">{coverage_stats['total_requirements']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Covered Requirements</div>
                        <div class="stat-value">{coverage_stats['covered_requirements']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Coverage Percentage</div>
                        <div class="stat-value">{coverage_stats['coverage_percentage']:.1f}%</div>
                    </div>
                </div>
                
                <h2>Defect Summary</h2>
                <div class="summary">
                    <div class="stat-box">
                        <div>Total Defects</div>
                        <div class="stat-value">{defect_stats['total_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Open Defects</div>
                        <div class="stat-value">{defect_stats['open_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>Critical Defects</div>
                        <div class="stat-value">{defect_stats['critical_defects']}</div>
                    </div>
                    <div class="stat-box">
                        <div>High Defects</div>
                        <div class="stat-value">{defect_stats['high_defects']}</div>
                    </div>
                </div>
                
                <h2>Top Failing Test Cases</h2>
                <table>
                    <tr>
                        <th>Test Case</th>
                        <th>Executions</th>
                        <th>Failures</th>
                        <th>Failure Rate</th>
                    </tr>
                    {''.join(f"<tr><td>{tc['test_case_name'] or tc['test_case_id']}</td><td>{tc['execution_count']}</td><td>{tc['fail_count']}</td><td>{tc['failure_rate']:.1f}%</td></tr>" for tc in failure_data[:5])}
                </table>
                
                <h2>Top Test Cases with Defects</h2>
                <table>
                    <tr>
                        <th>Test Case ID</th>
                        <th>Defect Count</th>
                    </tr>
                    {''.join(f"<tr><td>{tc['test_case_id']}</td><td>{tc['defect_count']}</td></tr>" for tc in defect_stats['by_test_case'][:5])}
                </table>
            </body>
            </html>
            """
            
            # Store HTML report in object storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"test_summary_report_{timestamp}.html"
            
            upload_data_to_storage(
                data=html_content.encode('utf-8'),
                object_name=report_filename,
                bucket_name=DEFAULT_BUCKET,
                content_type='text/html'
            )
            
            # Add URL to the report
            report['html_url'] = get_storage_object_url(report_filename, DEFAULT_BUCKET, 86400)  # 24 hours
            report['html_filename'] = report_filename
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {str(e)}")
            report['error'] = f"Failed to generate HTML report: {str(e)}"
    
    logger.info(f"Generated test summary report from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    return report


def send_report_email(
    report_type: str,
    report_data: Dict[str, Any],
    recipients: List[str],
    subject: str = None
) -> Dict[str, Any]:
    """
    Send a report via email.
    
    Args:
        report_type: Type of report ('defect', 'test_summary')
        report_data: Report data dictionary
        recipients: List of email recipients
        subject: Optional email subject
        
    Returns:
        Dict: Email sending status and details
    """
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        # Get email configuration from environment
        smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', 25))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        sender_email = os.environ.get('SENDER_EMAIL', 'watsonx-ipg-testing@example.com')
        
        # Create message
        msg = MIMEMultipart('alternative')
        
        # Set subject
        if not subject:
            if report_type == 'defect':
                subject = f"Defect Report: {report_data['metadata']['start_date'][:10]} to {report_data['metadata']['end_date'][:10]}"
            elif report_type == 'test_summary':
                subject = f"Test Summary Report: {report_data['metadata']['start_date'][:10]} to {report_data['metadata']['end_date'][:10]}"
            else:
                subject = f"Testing Report: {datetime.now().strftime('%Y-%m-%d')}"
        
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)
        
        # Build email content
        if report_type == 'defect':
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <h1>Defect Report</h1>
                <p>Period: {report_data['metadata']['start_date'][:10]} to {report_data['metadata']['end_date'][:10]}</p>
                
                <h2>Summary</h2>
                <table>
                    <tr>
                        <th>Total Defects</th>
                        <td>{report_data['summary']['total_defects']}</td>
                    </tr>
                    <tr>
                        <th>Open Defects</th>
                        <td>{report_data['summary']['open_defects']}</td>
                    </tr>
                    <tr>
                        <th>Critical Defects</th>
                        <td>{report_data['summary']['critical_defects']}</td>
                    </tr>
                    <tr>
                        <th>High Defects</th>
                        <td>{report_data['summary']['high_defects']}</td>
                    </tr>
                </table>
                
                <p>Please find the complete report attached or view it online using the link below:</p>
                
                {'<p><a href="' + report_data['html_url'] + '">View Full Report</a></p>' if 'html_url' in report_data else ''}
            </body>
            </html>
            """
        elif report_type == 'test_summary':
            # Calculate quality score class
            quality_score = report_data['quality_score']['score']
            score_class = 'good' if quality_score >= 80 else 'average' if quality_score >= 60 else 'poor'
            score_color = '#3c763d' if quality_score >= 80 else '#8a6d3b' if quality_score >= 60 else '#a94442'
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .quality-score {{ font-size: 24px; color: {score_color}; text-align: center; padding: 10px; }}
                </style>
            </head>
            <body>
                <h1>Test Summary Report</h1>
                <p>Period: {report_data['metadata']['start_date'][:10]} to {report_data['metadata']['end_date'][:10]}</p>
                
                <div class="quality-score">
                    Overall Quality Score: {quality_score:.1f}%
                </div>
                
                <h2>Test Execution Summary</h2>
                <table>
                    <tr>
                        <th>Total Executions</th>
                        <td>{report_data['execution_summary']['total_executions']}</td>
                    </tr>
                    <tr>
                        <th>Pass Rate</th>
                        <td>{report_data['execution_summary']['pass_rate']:.1f}%</td>
                    </tr>
                    <tr>
                        <th>Passed Tests</th>
                        <td>{report_data['execution_summary']['passed']}</td>
                    </tr>
                    <tr>
                        <th>Failed Tests</th>
                        <td>{report_data['execution_summary']['failed']}</td>
                    </tr>
                </table>
                
                <h2>Requirements Coverage</h2>
                <table>
                    <tr>
                        <th>Coverage Percentage</th>
                        <td>{report_data['coverage_summary']['coverage_percentage']:.1f}%</td>
                    </tr>
                    <tr>
                        <th>Total Requirements</th>
                        <td>{report_data['coverage_summary']['total_requirements']}</td>
                    </tr>
                    <tr>
                        <th>Covered Requirements</th>
                        <td>{report_data['coverage_summary']['covered_requirements']}</td>
                    </tr>
                </table>
                
                <p>Please find the complete report attached or view it online using the link below:</p>
                
                {'<p><a href="' + report_data['html_url'] + '">View Full Report</a></p>' if 'html_url' in report_data else ''}
            </body>
            </html>
            """
        else:
            html_content = f"""
            <html>
            <body>
                <h1>Testing Report</h1>
                <p>Please find the complete report attached or view it online.</p>
                
                {'<p><a href="' + report_data['html_url'] + '">View Full Report</a></p>' if 'html_url' in report_data else ''}
            </body>
            </html>
            """
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if smtp_user and smtp_password:
                server.starttls()
                server.login(smtp_user, smtp_password)
            
            server.send_message(msg)
        
        logger.info(f"Sent {report_type} report email to {len(recipients)} recipients")
        return {
            'status': 'success',
            'recipients': recipients,
            'subject': subject
        }
        
    except ImportError as e:
        logger.error(f"Missing required package for email: {str(e)}")
        return {
            'status': 'error',
            'error': f"Missing required package: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return {
            'status': 'error',
            'error': f"Failed to send email: {str(e)}"
        }

# End of Part 7: Defect Management & Reporting

# ------------- Part 8: AI/LLM & Advanced Features -------------

def store_llm_generation_result(
    requirement_id: str,
    generated_content: Dict[str, Any],
    model_name: str = "llama",
    content_type: str = "test_scenarios",
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store LLM-generated content in object storage.
    
    Args:
        requirement_id: ID of the requirement that triggered generation
        generated_content: Dictionary containing generated content
        model_name: Name of the LLM model used
        content_type: Type of content ('test_scenarios', 'test_cases', 'analysis')
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored result
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"llm_{content_type}_{requirement_id}_{timestamp}.json"
    
    # Add metadata
    generated_content['metadata'] = {
        'requirement_id': requirement_id,
        'model_name': model_name,
        'content_type': content_type,
        'generated_at': datetime.now().isoformat()
    }
    
    # Convert to JSON
    json_data = json.dumps(generated_content, indent=2)
    
    # Store in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'llm-generation',
        'model-name': model_name,
        'content-type': content_type,
        'requirement-id': requirement_id
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Record in database if it's a test scenario
    if content_type == "test_scenarios":
        # For each scenario in the generated content
        for scenario in generated_content.get('scenarios', []):
            query = """
            INSERT INTO test_scenarios
            (requirement_id, scenario_name, description, generated_by, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            update_database(
                query=query,
                params=(
                    requirement_id,
                    scenario.get('name', f"Scenario for {requirement_id}"),
                    scenario.get('description', ''),
                    f"watsonx-{model_name}",
                    'draft',
                    datetime.now()
                )
            )
    
    logger.info(f"Stored LLM generation result for requirement {requirement_id} as {file_name}")
    return file_name


def get_llm_generations_by_requirement(
    requirement_id: str,
    content_type: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> List[Dict[str, Any]]:
    """
    Retrieve LLM-generated content for a requirement.
    
    Args:
        requirement_id: ID of the requirement
        content_type: Optional content type filter
        bucket_name: Name of the bucket
        
    Returns:
        List[Dict]: List of generated content
    """
    prefix = f"llm_"
    if content_type:
        prefix += f"{content_type}_"
    prefix += f"{requirement_id}_"
    
    objects = list_storage_objects(
        prefix=prefix,
        bucket_name=bucket_name
    )
    
    results = []
    for obj in objects:
        data_bytes = download_data_from_storage(
            object_name=obj['name'],
            bucket_name=bucket_name
        )
        
        # Parse JSON
        content = json.loads(data_bytes.decode('utf-8'))
        results.append(content)
    
    logger.info(f"Retrieved {len(results)} LLM generations for requirement {requirement_id}")
    return results


def generate_test_scenarios_from_requirement(
    requirement_id: str,
    model_name: str = "llama",
    num_scenarios: int = 5,
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate test scenarios from a requirement using watsonx.ai.
    
    Args:
        requirement_id: ID of the requirement
        model_name: LLM model to use
        num_scenarios: Number of scenarios to generate
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    # Get requirement details
    try:
        requirement = get_requirement_by_id(requirement_id)
    except ValueError as e:
        logger.error(f"Failed to get requirement {requirement_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Requirement not found: {str(e)}"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test scenario generator expert. Based on the following requirement, 
        generate {num_scenarios} distinct test scenarios. For each scenario, include:
        
        1. A descriptive name
        2. A detailed description
        3. Preconditions
        4. Steps to execute
        5. Expected results
        6. Priority (High, Medium, Low)
        
        Requirement:
        Title: {title}
        Description: {description}
        
        Generate varied scenarios that cover different aspects of the requirement,
        including positive tests, negative tests, boundary conditions, and edge cases.
        """
    
    # Format prompt
    prompt = prompt_template.format(
        num_scenarios=num_scenarios,
        title=requirement.get('title', f"Requirement {requirement_id}"),
        description=requirement.get('description', '')
    )
    
    try:
        # In a real implementation, this would call the watsonx.ai API
        # For this example, we'll simulate the response
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock response with generated scenarios
        scenarios = []
        for i in range(num_scenarios):
            scenario = {
                'name': f"Test Scenario {i+1} for {requirement_id}",
                'description': f"This scenario tests a specific aspect of the requirement {requirement_id}.",
                'preconditions': [
                    f"Precondition 1 for scenario {i+1}",
                    f"Precondition 2 for scenario {i+1}"
                ],
                'steps': [
                    f"Step 1: Perform action A for scenario {i+1}",
                    f"Step 2: Verify result B for scenario {i+1}",
                    f"Step 3: Perform action C for scenario {i+1}"
                ],
                'expected_results': [
                    f"Expected result 1 for scenario {i+1}",
                    f"Expected result 2 for scenario {i+1}"
                ],
                'priority': 'High' if i < 2 else 'Medium' if i < 4 else 'Low'
            }
            scenarios.append(scenario)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_id': requirement_id,
            'requirement_title': requirement.get('title', ''),
            'scenarios': scenarios,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=requirement_id,
            generated_content=result,
            model_name=model_name,
            content_type='test_scenarios'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {num_scenarios} test scenarios for requirement {requirement_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test scenarios: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def generate_test_cases_from_scenarios(
    scenarios: List[Dict[str, Any]],
    model_name: str = "llama",
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate detailed test cases from test scenarios using watsonx.ai.
    
    Args:
        scenarios: List of scenario dictionaries
        model_name: LLM model to use
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    if not scenarios:
        logger.error("No scenarios provided")
        return {
            'status': 'error',
            'error': "No scenarios provided"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test case generation expert. Based on the following test scenario,
        create a detailed test case with specific test steps, test data, and expected results.
        
        Test Scenario:
        Name: {name}
        Description: {description}
        Preconditions: {preconditions}
        Steps: {steps}
        Expected Results: {expected_results}
        Priority: {priority}
        
        Generate a test case that includes:
        1. Specific test data values to use
        2. Detailed step-by-step test procedure
        3. Specific expected results for each step
        4. Validation points
        5. Any notes or special considerations
        """
    
    test_cases = []
    requirement_ids = set()
    
    try:
        for i, scenario in enumerate(scenarios):
            # Extract requirement ID if available
            requirement_id = scenario.get('requirement_id', f"REQ_{int(time.time())}")
            requirement_ids.add(requirement_id)
            
            # Format scenario details for prompt
            scenario_details = {
                'name': scenario.get('name', f"Scenario {i+1}"),
                'description': scenario.get('description', ''),
                'preconditions': '\n'.join(scenario.get('preconditions', [])),
                'steps': '\n'.join(scenario.get('steps', [])),
                'expected_results': '\n'.join(scenario.get('expected_results', [])),
                'priority': scenario.get('priority', 'Medium')
            }
            
            # Format prompt for this scenario
            prompt = prompt_template.format(**scenario_details)
            
            # Simulate API call delay
            import time
            time.sleep(0.5)
            
            # Mock test case generation
            test_case = {
                'id': f"TC_{int(time.time())}_{i}",
                'name': f"Test Case for {scenario_details['name']}",
                'description': f"Detailed test case for {scenario_details['name']}",
                'requirement_id': requirement_id,
                'scenario_name': scenario_details['name'],
                'priority': scenario_details['priority'],
                'test_data': {
                    'input1': 'Sample input value 1',
                    'input2': 'Sample input value 2'
                },
                'steps': [
                    {
                        'number': 1,
                        'description': 'Perform specific action A with test data',
                        'expected_result': 'System should respond with X'
                    },
                    {
                        'number': 2,
                        'description': 'Verify specific condition B',
                        'expected_result': 'Condition B should be true'
                    },
                    {
                        'number': 3,
                        'description': 'Perform specific action C',
                        'expected_result': 'System should update with Y'
                    }
                ],
                'validation_points': [
                    'Validate that X appears correctly',
                    'Validate that Y contains the expected data'
                ],
                'notes': 'This test case covers the main positive flow'
            }
            
            test_cases.append(test_case)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_ids': list(requirement_ids),
            'test_cases': test_cases,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=list(requirement_ids)[0] if requirement_ids else "multiple",
            generated_content=result,
            model_name=model_name,
            content_type='test_cases'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {len(test_cases)} test cases from {len(scenarios)} scenarios")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test cases: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def analyze_test_failure(
    execution_id: str,
    model_name: str = "llama",
    include_similar_failures: bool = True
) -> Dict[str, Any]:
    """
    Analyze a test failure using watsonx.ai to determine potential causes and solutions.
    
    Args:
        execution_id: ID of the failed test execution
        model_name: LLM model to use
        include_similar_failures: Whether to include similar historical failures
        
    Returns:
        Dict: Analysis results and recommendations
    """
    # Get execution details
    try:
        execution = get_test_execution(execution_id)
    except ValueError as e:
        logger.error(f"Failed to get execution {execution_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Execution not found: {str(e)}"
        }
    
    # Check if execution is failed
    if execution.get('status', '').lower() != 'failed':
        logger.warning(f"Execution {execution_id} is not failed (status: {execution.get('status')})")
        return {
            'status': 'error',
            'error': f"Execution is not failed (status: {execution.get('status')})"
        }
    
    # Get test case details
    test_case_id = execution['metadata']['test_case_id']
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError:
        test_case = {'id': test_case_id}  # Minimal info if test case not found
    
    # Find the failed steps
    steps = execution.get('execution_steps', [])
    failed_steps = [step for step in steps if step.get('status', '').lower() == 'failed']
    
    if not failed_steps:
        logger.warning(f"No failed steps found in execution {execution_id}")
        return {
            'status': 'warning',
            'warning': "No failed steps found in execution",
            'execution_id': execution_id
        }
    
    # Get similar failures if requested
    similar_failures = []
    if include_similar_failures:
        # Query for similar failures
        query = """
        SELECT e.execution_id, e.test_case_id, e.status, e.executed_at
        FROM test_executions e
        WHERE e.test_case_id = %s 
        AND e.status = 'failed'
        AND e.execution_id != %s
        ORDER BY e.executed_at DESC
        LIMIT 5
        """
        
        similar_results = query_database(
            query=query,
            params=(test_case_id, execution_id)
        )
        
        for result in similar_results:
            try:
                similar_execution = get_test_execution(result['execution_id'])
                similar_failures.append(similar_execution)
            except ValueError:
                pass
    
    try:
        # Prepare analysis context
        analysis_context = {
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'execution_time': execution.get('execution_time', 0),
            'failed_steps': failed_steps,
            'similar_failures': len(similar_failures)
        }
        
        # Build prompt for watsonx.ai
        prompt = f"""
        Analyze the following test failure and provide potential causes and solutions.
        
        Test Case: {test_case.get('name', test_case_id)}
        Execution ID: {execution_id}
        
        Failed Steps:
        {json.dumps(failed_steps, indent=2)}
        
        Similar Failures: {len(similar_failures)} recent failures of this test case.
        
        Provide:
        1. Most likely causes of failure
        2. Recommended troubleshooting steps
        3. Potential fixes
        4. Is this likely a defect in the application or an issue with the test?
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock analysis results
        analysis_results = {
            'potential_causes': [
                {
                    'description': 'Data inconsistency in test environment',
                    'probability': 'High',
                    'explanation': 'The error message indicates a mismatch between expected and actual data values'
                },
                {
                    'description': 'Timing issue - operation not completed before verification',
                    'probability': 'Medium',
                    'explanation': 'The failure occurs during a verification step that may be executing too soon'
                },
                {
                    'description': 'Application defect in data processing logic',
                    'probability': 'Medium',
                    'explanation': 'The specific error pattern matches known issues in the data processing component'
                }
            ],
            'troubleshooting_steps': [
                'Verify test data is consistent with current environment state',
                'Add appropriate wait condition before verification step',
                'Review application logs for exceptions around the time of failure',
                'Compare with previous successful executions to identify changes'
            ],
            'potential_fixes': [
                {
                    'type': 'Test Update',
                    'description': 'Introduce a wait mechanism before verification',
                    'difficulty': 'Low'
                },
                {
                    'type': 'Environment Fix',
                    'description': 'Refresh test data to ensure consistency',
                    'difficulty': 'Medium'
                },
                {
                    'type': 'Application Fix',
                    'description': 'Review and correct data processing logic in the application',
                    'difficulty': 'High'
                }
            ],
            'defect_assessment': {
                'likely_application_defect': True,
                'confidence': 70,
                'explanation': 'Based on the error patterns and similar failures, there is a 70% probability this is an application defect rather than a test issue.'
            }
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'analysis_context': analysis_context,
            'analysis_results': analysis_results,
            'similar_failure_count': len(similar_failures),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='failure_analysis'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Completed failure analysis for execution {execution_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze test failure: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def suggest_test_case_improvements(
    test_case_id: str,
    model_name: str = "llama"
) -> Dict[str, Any]:
    """
    Use watsonx.ai to suggest improvements for an existing test case.
    
    Args:
        test_case_id: ID of the test case to improve
        model_name: LLM model to use
        
    Returns:
        Dict: Improvement suggestions and metadata
    """
    # Get test case details
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError as e:
        logger.error(f"Failed to get test case {test_case_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Test case not found: {str(e)}"
        }
    
    # Get test execution history
    query = """
    SELECT status, COUNT(*) as count
    FROM test_executions
    WHERE test_case_id = %s
    GROUP BY status
    """
    
    execution_stats = query_database(query, (test_case_id,))
    execution_history = {row['status']: row['count'] for row in execution_stats}
    
    # Get defects associated with this test case
    defects = get_defects(test_case_id=test_case_id)
    
    try:
        # Build prompt for watsonx.ai
        prompt = f"""
        Review the following test case and suggest improvements to make it more robust and effective.
        
        Test Case: {test_case.get('name', test_case_id)}
        Description: {test_case.get('description', '')}
        
        Current Test Steps:
        {json.dumps(test_case.get('steps', []), indent=2)}
        
        Execution History:
        {json.dumps(execution_history, indent=2)}
        
        Associated Defects: {len(defects)}
        
        Provide:
        1. Overall assessment of the test case
        2. Specific improvement suggestions
        3. Additional test scenarios that should be covered
        4. Recommendations for better test data
        5. Any validation points that should be added
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock improvement suggestions
        improvement_suggestions = {
            'overall_assessment': {
                'quality_score': 7,  # 1-10 scale
                'strengths': [
                    'Good coverage of main functionality',
                    'Clear step descriptions'
                ],
                'weaknesses': [
                    'Limited validation points',
                    'Missing boundary condition tests',
                    'No negative test scenarios'
                ]
            },
            'specific_improvements': [
                {
                    'step_index': 2,
                    'current': test_case.get('steps', [])[2] if len(test_case.get('steps', [])) > 2 else {},
                    'suggestion': 'Add specific validation for the returned data format',
                    'rationale': 'Current step only verifies presence but not structure'
                },
                {
                    'type': 'Add Step',
                    'suggestion': 'Add verification step after data submission',
                    'rationale': 'Should verify successful data processing before proceeding'
                },
                {
                    'type': 'Modify Test Data',
                    'suggestion': 'Use more diverse test data including boundary values',
                    'rationale': 'Current test data only covers happy path'
                }
            ],
            'additional_scenarios': [
                {
                    'name': 'Negative Test - Invalid Input',
                    'description': 'Test behavior when invalid data is provided',
                    'steps': [
                        'Attempt to submit invalid data format',
                        'Verify appropriate error message is displayed',
                        'Verify no data corruption occurs'
                    ]
                },
                {
                    'name': 'Boundary Test - Maximum Values',
                    'description': 'Test behavior with maximum allowed values',
                    'steps': [
                        'Submit form with maximum length strings',
                        'Verify data is accepted and processed correctly',
                        'Verify display handles long values appropriately'
                    ]
                }
            ],
            'test_data_recommendations': [
                'Include null values for optional fields',
                'Add test case with maximum length strings',
                'Include special characters in text fields',
                'Test with minimum and maximum numeric values'
            ],
            'validation_points': [
                'Verify response times are within acceptable limits',
                'Check both UI updates and backend data consistency',
                'Validate error message content for clarity and correctness',
                'Ensure no unnecessary database queries are triggered'
            ]
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'improvement_suggestions': improvement_suggestions,
            'execution_history': execution_history,
            'defect_count': len(defects),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='test_improvement'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated improvement suggestions for test case {test_case_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test case improvements: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def create_database_backup(
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> str:
    """
    Create a backup of database tables in JSON format.
    
    Args:
        bucket_name: Name of the bucket
        tables: List of tables to backup (default: all tables)
        
    Returns:
        str: Object name of the backup file
    """
    if not tables:
        # Get all tables
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
        results = query_database(query)
        tables = [row['table_name'] for row in results]
    
    backup_data = {}
    
    for table in tables:
        query = f"SELECT * FROM {table};"
        results = query_database(query)
        
        # Convert datetime objects to ISO format
        for row in results:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
        
        backup_data[table] = results
    
    # Create backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"database_backup_{timestamp}.json"
    
    json_data = json.dumps(backup_data, indent=2)
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=backup_file_name,
        bucket_name=bucket_name,
        metadata={
            'content-type': 'application/json',
            'source': 'watsonx-ipg-testing',
            'type': 'database-backup',
            'tables': ','.join(tables)
        },
        content_type='application/json'
    )
    
    logger.info(f"Created database backup of {len(tables)} tables as {backup_file_name}")
    return backup_file_name


def restore_database_from_backup(
    backup_file_name: str,
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> Dict[str, Any]:
    """
    Restore database tables from a backup file.
    
    Args:
        backup_file_name: Name of the backup file
        bucket_name: Name of the bucket
        tables: Optional list of specific tables to restore
        
    Returns:
        Dict: Restoration status and details
    """
    try:
        # Download backup file
        data_bytes = download_data_from_storage(
            object_name=backup_file_name,
            bucket_name=bucket_name
        )
        
        # Parse JSON
        backup_data = json.loads(data_bytes.decode('utf-8'))
        
        # Determine which tables to restore
        tables_to_restore = tables or list(backup_data.keys())
        
        # Verify tables exist in backup
        missing_tables = [table for table in tables_to_restore if table not in backup_data]
        if missing_tables:
            logger.error(f"Tables not found in backup: {', '.join(missing_tables)}")
            return {
                'status': 'error',
                'error': f"Tables not found in backup: {', '.join(missing_tables)}"
            }
        
        # Restore each table
        restoration_results = {}
        for table in tables_to_restore:
            try:
                # Delete existing data
                delete_query = f"DELETE FROM {table};"
                update_database(delete_query)
                
                # Insert backup data
                rows = backup_data[table]
                if not rows:
                    restoration_results[table] = {
                        'status': 'success',
                        'rows_restored': 0
                    }
                    continue
                
                # Build insert query
                columns = list(rows[0].keys())
                placeholders = ", ".join(["%s"] * len(columns))
                column_list = ", ".join(columns)
                
                insert_query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                
                # Prepare params for batch insert
                params_list = []
                for row in rows:
                    # Ensure row values are in the same order as columns
                    row_values = [row[col] for col in columns]
                    params_list.append(row_values)
                
                # Perform batch insert
                affected_rows = batch_update_database(
                    query=insert_query,
                    params_list=params_list
                )
                
                restoration_results[table] = {
                    'status': 'success',
                    'rows_restored': affected_rows
                }
                
            except Exception as e:
                logger.error(f"Failed to restore table {table}: {str(e)}")
                restoration_results[table] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check overall status
        success_count = sum(1 for result in restoration_results.values() if result['status'] == 'success')
        
        logger.info(f"Restored {success_count} of {len(tables_to_restore)} tables from backup {backup_file_name}")
        return {
            'status': 'success' if success_count == len(tables_to_restore) else 'partial',
            'tables_restored': success_count,
            'total_tables': len(tables_to_restore),
            'details': restoration_results
        }
        
    except Exception as e:
        logger.error(f"Failed to restore from backup {backup_file_name}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Restoration failed: {str(e)}"
        }


def cleanup_old_data(
    retention_days: int = 90,
    data_types: List[str] = None
) -> Dict[str, int]:
    """
    Clean up old data based on retention policy.
    
    Args:
        retention_days: Number of days to retain data
        data_types: Types of data to clean up (default: all)
        
    Returns:
        Dict: Number of records deleted by type
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deletion_counts = {}
    
    # Define data types and their cleanup queries
    cleanup_queries = {
        'test_executions': """
            DELETE FROM test_executions
            WHERE executed_at < %s
            """,
        'defects': """
            DELETE FROM defects
            WHERE status = 'closed'
            AND updated_at < %s
            """,
        'sharepoint_documents': """
            DELETE FROM sharepoint_documents
            WHERE sync_status = 'synced'
            AND created_at < %s
            """,
        'blueprism_jobs': """
            DELETE FROM blueprism_jobs
            WHERE completed_at < %s
            """,
        'uft_jobs': """
            DELETE FROM uft_jobs
            WHERE completed_at < %s
            """
    }
    
    # Determine which data types to clean up
    types_to_clean = data_types or list(cleanup_queries.keys())
    
    # Execute cleanup for each type
    for data_type in types_to_clean:
        if data_type in cleanup_queries:
            query = cleanup_queries[data_type]
            try:
                affected_rows = update_database(
                    query=query,
                    params=(cutoff_date,)
                )
                deletion_counts[data_type] = affected_rows
                logger.info(f"Deleted {affected_rows} old records from {data_type}")
            except Exception as e:
                logger.error(f"Failed to clean up {data_type}: {str(e)}")
                deletion_counts[data_type] = 0
    
    # Cleanup old files in object storage
    try:
        prefix = ""  # Clean up all prefixes
        objects = list_storage_objects(prefix=prefix)
        
        deleted_objects = 0
        for obj in objects:
            # Skip recent objects
            if datetime.now() - obj['last_modified'] < timedelta(days=retention_days):
                continue
            
            # Skip backup files and important artifacts
            if 'backup' in obj['name'] or 'archive' in obj['name']:
                continue
            
            # Delete old object
            try:
                delete_from_storage(obj['name'])
                deleted_objects += 1
            except:
                pass
        
        deletion_counts['object_storage'] = deleted_objects
        logger.info(f"Deleted {deleted_objects} old objects from storage")
    except Exception as e:
        logger.error(f"Failed to clean up object storage: {str(e)}")
        deletion_counts['object_storage'] = 0
    
    return deletion_counts


# ------------- Cache Management -------------

_cache = {}  # Simple in-memory cache

def cache_result(key: str, value: Any, ttl_seconds: int = 300):
    """
    Cache a result in memory.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl_seconds: Time to live in seconds
    """
    expiry = time.time() + ttl_seconds
    _cache[key] = (value, expiry)


def get_cached_result(key: str) -> Optional[Any]:
    """
    Get a result from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Optional[Any]: Cached value or None if expired/not found
    """
    if key in _cache:
        value, expiry = _cache[key]
        if time.time() < expiry:
            return value
        
        # Expired
        del _cache[key]
    
    return None


def clear_cache():
    """Clear the entire cache."""
    _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the cache.
    
    Returns:
        Dict: Cache statistics
    """
    now = time.time()
    total_items = len(_cache)
    expired_items = sum(1 for _, expiry in _cache.values() if now >= expiry)
    valid_items = total_items - expired_items
    
    # Calculate memory usage (approximate)
    import sys
    memory_usage = sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in _cache.items())
    
    return {
        'total_items': total_items,
        'valid_items': valid_items,
        'expired_items': expired_items,
        'memory_usage_bytes': memory_usage
    }


# ------------- Health Check Functions -------------

def perform_health_check() -> Dict[str, Any]:
    """
    Perform a health check on all database components.
    
    Returns:
        Dict: Health status for each component
    """
    health = {
        'database': is_database_healthy(),
        'object_storage': is_storage_healthy(),
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Check table existence and row counts
    tables = [
        'test_cases', 'test_executions', 'defects', 'test_data',
        'integration_credentials', 'sharepoint_documents', 'blueprism_jobs'
    ]
    
    for table in tables:
        try:
            exists = table_exists(table)
            
            if exists:
                count_query = f"SELECT COUNT(*) as count FROM {table};"
                count_result = query_database(count_query, fetch_one=True)
                row_count = count_result['count'] if count_result else 0
            else:
                row_count = 0
            
            health['components'][table] = {
                'exists': exists,
                'row_count': row_count,
                'status': 'healthy' if exists else 'missing'
            }
        except Exception as e:
            health['components'][table] = {
                'exists': False,
                'status': 'error',
                'error': str(e)
            }
    
    # Check connection to integration systems
    integration_systems = [
        'jira', 'sharepoint', 'alm', 'blueprism', 'uft'
    ]
    
    for system in integration_systems:
        try:
            # Check if credentials exist
            has_credentials = False
            try:
                get_integration_credentials(system, decrypt=False)
                has_credentials = True
            except ValueError:
                pass
            
            health['components'][f"{system}_integration"] = {
                'credentials_exist': has_credentials,
                'status': 'configured' if has_credentials else 'not_configured'
            }
        except Exception as e:
            health['components'][f"{system}_integration"] = {
                'status': 'error',
                'error': str(e)
            }
    
    # Overall status
    critical_components = ['database', 'object_storage']
    critical_status = all(health[component] for component in critical_components)
    health['overall_status'] = 'healthy' if critical_status else 'degraded'
    
    logger.info(f"Health check completed: {health['overall_status']}")
    return health


def analyze_database_performance() -> Dict[str, Any]:
    """
    Analyze database performance metrics.
    
    Returns:
        Dict: Performance analysis results
    """
    try:
        # Query for database statistics
        stats_queries = {
            'table_stats': """
                SELECT 
                    relname as table_name, 
                    n_live_tup as row_count,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """,
            'index_stats': """
                SELECT
                    indexrelname as index_name,
                    relname as table_name,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
            """,
            'table_io_stats': """
                SELECT
                    relname as table_name,
                    heap_blks_read as disk_reads,
                    heap_blks_hit as cache_hits,
                    CASE WHEN heap_blks_read + heap_blks_hit > 0 
                        THEN heap_blks_hit::float / (heap_blks_read + heap_blks_hit) * 100
                        ELSE 0 
                    END as cache_hit_ratio
                FROM pg_statio_user_tables
                ORDER BY heap_blks_read + heap_blks_hit DESC
            """
        }
        
        # Execute queries
        stats_results = {}
        for key, query in stats_queries.items():
            stats_results[key] = query_database(query)
        
        # Calculate overall statistics
        total_rows = sum(table['row_count'] for table in stats_results['table_stats'])
        total_dead_rows = sum(table['dead_rows'] for table in stats_results['table_stats'])
        dead_row_ratio = (total_dead_rows / total_rows * 100) if total_rows > 0 else 0
        
        total_disk_reads = sum(table['disk_reads'] for table in stats_results['table_io_stats'])
        total_cache_hits = sum(table['cache_hits'] for table in stats_results['table_io_stats'])
        overall_cache_hit_ratio = (total_cache_hits / (total_disk_reads + total_cache_hits) * 100) if (total_disk_reads + total_cache_hits) > 0 else 0
        
        # Identify tables that might need vacuuming (high dead row ratio)
        vacuum_candidates = [
            {
                'table_name': table['table_name'],
                'dead_rows': table['dead_rows'],
                'row_count': table['row_count'],
                'dead_row_ratio': (table['dead_rows'] / table['row_count'] * 100) if table['row_count'] > 0 else 0,
                'last_vacuum': table['last_vacuum'].isoformat() if table['last_vacuum'] else None
            }
            for table in stats_results['table_stats']
            if table['row_count'] > 0 and (table['dead_rows'] / table['row_count']) >= 0.2  # 20% or more dead rows
        ]
        
        # Identify unused indexes
        unused_indexes = [
            {
                'index_name': index['index_name'],
                'table_name': index['table_name'],
                'index_scans': index['index_scans']
            }
            for index in stats_results['index_stats']
            if index['index_scans'] == 0
        ]
        
        # Identify tables with low cache hit ratio
        low_cache_hit_tables = [
            {
                'table_name': table['table_name'],
                'disk_reads': table['disk_reads'],
                'cache_hits': table['cache_hits'],
                'cache_hit_ratio': table['cache_hit_ratio']
            }
            for table in stats_results['table_io_stats']
            if table['cache_hit_ratio'] < 90 and (table['disk_reads'] + table['cache_hits']) > 100  # Less than 90% cache hits and significant I/O
        ]
        
        # Prepare recommendations
        recommendations = []
        
        if vacuum_candidates:
            recommendations.append({
                'type': 'vacuum',
                'message': f"Consider running VACUUM on {len(vacuum_candidates)} tables with high dead row ratios",
                'tables': [table['table_name'] for table in vacuum_candidates]
            })
        
        if unused_indexes:
            recommendations.append({
                'type': 'unused_indexes',
                'message': f"Consider removing {len(unused_indexes)} unused indexes to improve write performance",
                'indexes': [f"{index['table_name']}.{index['index_name']}" for index in unused_indexes]
            })
        
        if low_cache_hit_tables:
            recommendations.append({
                'type': 'cache_optimization',
                'message': f"{len(low_cache_hit_tables)} tables have low cache hit ratios, consider increasing shared_buffers",
                'tables': [table['table_name'] for table in low_cache_hit_tables]
            })
        
        # Final analysis result
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tables': len(stats_results['table_stats']),
                'total_indexes': len(stats_results['index_stats']),
                'total_rows': total_rows,
                'dead_row_ratio': dead_row_ratio,
                'overall_cache_hit_ratio': overall_cache_hit_ratio
            },
            'top_tables_by_size': stats_results['table_stats'][:5],
            'vacuum_candidates': vacuum_candidates,
            'unused_indexes': unused_indexes,
            'low_cache_hit_tables': low_cache_hit_tables,
            'recommendations': recommendations
        }
        
        logger.info(f"Database performance analysis completed with {len(recommendations)} recommendations")
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze database performance: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def optimize_database() -> Dict[str, Any]:
    """
    Perform database optimization operations.
    
    Returns:
        Dict: Optimization results
    """
    try:
        # Analyze tables
        analyze_query = "ANALYZE;"
        update_database(analyze_query)
        
        # Get tables that need vacuuming
        vacuum_query = """
        SELECT 
            relname as table_name,
            n_dead_tup as dead_rows,
            n_live_tup as row_count,
            CASE WHEN n_live_tup > 0 
                THEN n_dead_tup::float / n_live_tup 
                ELSE 0 
            END as dead_ratio
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        AND n_dead_tup > 0
        AND (n_dead_tup::float / n_live_tup) >= 0.2
        ORDER BY dead_ratio DESC
        """
        
        vacuum_candidates = query_database(vacuum_query)
        
        # Vacuum each table
        vacuum_results = []
        for table in vacuum_candidates:
            table_name = table['table_name']
            try:
                vacuum_table_query = f"VACUUM ANALYZE {table_name};"
                update_database(vacuum_table_query)
                vacuum_results.append({
                    'table_name': table_name,
                    'status': 'success',
                    'dead_rows_before': table['dead_rows']
                })
                logger.info(f"Vacuumed table {table_name} with {table['dead_rows']} dead rows")
            except Exception as e:
                vacuum_results.append({
                    'table_name': table_name,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Failed to vacuum table {table_name}: {str(e)}")
        
        # Get unused indexes
        unused_index_query = """
        SELECT
            indexrelname as index_name,
            relname as table_name,
            idx_scan as index_scans
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        AND indexrelname NOT IN (
            SELECT indexrelname
            FROM pg_constraint c
            JOIN pg_index i ON c.conindid = i.indexrelid
            JOIN pg_stat_user_indexes s ON s.indexrelid = i.indexrelid
            WHERE c.contype = 'p'
        )
        ORDER BY pg_relation_size(indexrelid) DESC
        """
        
        unused_indexes = query_database(unused_index_query)
        
        # Don't automatically drop indexes, just report them
        
        # Reindex important tables
        important_tables = [
            'test_cases', 'test_executions', 'defects'
        ]
        
        reindex_results = []
        for table in important_tables:
            try:
                if table_exists(table):
                    reindex_query = f"REINDEX TABLE {table};"
                    update_database(reindex_query)
                    reindex_results.append({
                        'table_name': table,
                        'status': 'success'
                    })
                    logger.info(f"Reindexed table {table}")
                else:
                    reindex_results.append({
                        'table_name': table,
                        'status': 'skipped',
                        'reason': 'table does not exist'
                    })
            except Exception as e:
                reindex_results.append({
                    'table_name': table,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Failed to reindex table {table}: {str(e)}")
        
        # Final optimization result
        result = {
            'timestamp': datetime.now().isoformat(),
            'tables_vacuumed': len([r for r in vacuum_results if r['status'] == 'success']),
            'tables_reindexed': len([r for r in reindex_results if r['status'] == 'success']),
            'unused_indexes_found': len(unused_indexes),
            'vacuum_results': vacuum_results,
            'reindex_results': reindex_results,
            'unused_indexes': unused_indexes
        }
        
        logger.info(f"Database optimization completed: {result['tables_vacuumed']} tables vacuumed, {result['tables_reindexed']} tables reindexed")
        return result
        
    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"Optimization failed: {str(e)}"
        }


def validate_database_schema() -> Dict[str, Any]:
    """
    Validate the database schema against the expected schema.
    
    Returns:
        Dict: Validation results
    """
    # Define expected tables and their required columns
    expected_schema = {
        'test_cases': [
            'id', 'name', 'description', 'version', 'storage_path', 
            'format', 'status', 'created_at', 'updated_at'
        ],
        'test_executions': [
            'execution_id', 'test_case_id', 'status', 'result_path', 
            'execution_time', 'screenshots', 'executed_at', 'notes'
        ],
        'defects': [
            'id', 'test_case_id', 'execution_id', 'defect_id', 
            'summary', 'description', 'severity', 'assigned_to', 
            'status', 'resolution', 'created_at', 'updated_at'
        ],
        'test_data': [
            'id', 'test_case_id', 'data_type', 'storage_path', 
            'created_at', 'updated_at'
        ],
        'integration_credentials': [
            'id', 'system_type', 'credentials', 'encrypted', 
            'created_at', 'updated_at'
        ],
        'sharepoint_documents': [
            'id', 'file_name', 'storage_path', 'content_type', 
            'sync_status', 'created_at', 'synced_at'
        ],
        'blueprism_jobs': [
            'id', 'job_id', 'test_case_id', 'controller_file', 
            'status', 'started_at', 'completed_at', 'result'
        ],
        'execution_metrics': [
            'id', 'execution_id', 'test_case_id', 'start_time', 
            'end_time', 'duration', 'status', 'environment'
        ]
    }
    
    validation_results = {}
    missing_tables = []
    schema_issues = []
    
    # Check each expected table
    for table, expected_columns in expected_schema.items():
        if not table_exists(table):
            missing_tables.append(table)
            validation_results[table] = {
                'exists': False,
                'status': 'missing'
            }
            continue
        
        # Get actual columns
        actual_columns = get_column_info(table)
        actual_column_names = [col['column_name'] for col in actual_columns]
        
        # Check for missing columns
        missing_columns = [col for col in expected_columns if col not in actual_column_names]
        
        if missing_columns:
            schema_issues.append({
                'table': table,
                'issue': 'missing_columns',
                'columns': missing_columns
            })
            validation_results[table] = {
                'exists': True,
                'status': 'incomplete',
                'missing_columns': missing_columns
            }
        else:
            validation_results[table] = {
                'exists': True,
                'status': 'valid',
                'columns': len(actual_columns)
            }
    
    # Overall validation result
    status = 'valid'
    if missing_tables:
        status = 'missing_tables'
    elif schema_issues:
        status = 'schema_issues'
    
    result = {
        'status': status,
        'missing_tables': missing_tables,
        'schema_issues': schema_issues,
        'tables_validated': len(validation_results),
        'valid_tables': len([r for r in validation_results.values() if r['status'] == 'valid']),
        'details': validation_results
    }
    
    logger.info(f"Database schema validation completed: {result['status']}")
    return result


def upgrade_database_schema(
    version: str = None
) -> Dict[str, Any]:
    """
    Upgrade the database schema to a specified version.
    
    Args:
        version: Target schema version (default: latest)
        
    Returns:
        Dict: Upgrade results
    """
    # Check current schema version
    current_version = "0.0.0"
    try:
        version_query = "SELECT value FROM system_config WHERE key = 'schema_version';"
        version_result = query_database(version_query, fetch_one=True)
        if version_result:
            current_version = version_result['value']
    except:
        # Table might not exist yet
        pass
    
    # Define schema upgrades with version numbers
    schema_upgrades = {
        "1.0.0": [
            # Initial schema creation
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """,
            """
            INSERT INTO system_config (key, value, updated_at)
            VALUES ('schema_version', '1.0.0', NOW())
            ON CONFLICT (key) DO UPDATE SET value = '1.0.0', updated_at = NOW()
            """
        ],
        "1.1.0": [
            # Add new fields to test_cases
            """
            ALTER TABLE test_cases
            ADD COLUMN IF NOT EXISTS priority VARCHAR(20)
            """,
            """
            ALTER TABLE test_cases
            ADD COLUMN IF NOT EXISTS estimated_duration INTEGER
            """,
            """
            UPDATE system_config SET value = '1.1.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ],
        "1.2.0": [
            # Add test_scenarios table
            """
            CREATE TABLE IF NOT EXISTS test_scenarios (
                id SERIAL PRIMARY KEY,
                requirement_id VARCHAR(255) NOT NULL,
                scenario_name VARCHAR(255) NOT NULL,
                description TEXT,
                generated_by VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                test_case_ids JSONB,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP
            )
            """,
            """
            UPDATE system_config SET value = '1.2.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ],
        "1.3.0": [
            # Add indexes for better performance
            """
            CREATE INDEX IF NOT EXISTS idx_test_executions_test_case_id
            ON test_executions(test_case_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_defects_test_case_id
            ON defects(test_case_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_test_cases_status
            ON test_cases(status)
            """,
            """
            UPDATE system_config SET value = '1.3.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ]
    }
    
    # Determine target version
    if not version:
        available_versions = sorted(list(schema_upgrades.keys()))
        if not available_versions:
            return {
                'status': 'no_upgrades',
                'current_version': current_version
            }
        target_version = available_versions[-1]  # Latest version
    else:
        if version not in schema_upgrades:
            return {
                'status': 'error',
                'error': f"Unknown version: {version}",
                'available_versions': list(schema_upgrades.keys())
            }
        target_version = version
    
    # Check if upgrade is needed
    from packaging import version as pkg_version
    if pkg_version.parse(current_version) >= pkg_version.parse(target_version):
        return {
            'status': 'already_current',
            'current_version': current_version,
            'target_version': target_version
        }
    
    # Sort versions for sequential upgrade
    versions_to_apply = [v for v in sorted(schema_upgrades.keys()) 
                        if pkg_version.parse(v) > pkg_version.parse(current_version)
                        and pkg_version.parse(v) <= pkg_version.parse(target_version)]
    
    # Apply upgrades in sequence
    results = []
    for upgrade_version in versions_to_apply:
        version_result = {
            'version': upgrade_version,
            'status': 'pending',
            'queries': []
        }
        
        try:
            # Execute each upgrade query
            for i, query in enumerate(schema_upgrades[upgrade_version]):
                try:
                    update_database(query)
                    version_result['queries'].append({
                        'index': i,
                        'status': 'success'
                    })
                except Exception as e:
                    version_result['queries'].append({
                        'index': i,
                        'status': 'error',
                        'error': str(e)
                    })
                    raise
            
            version_result['status'] = 'success'
            
        except Exception as e:
            version_result['status'] = 'error'
            version_result['error'] = str(e)
            results.append(version_result)
            break
        
        results.append(version_result)
    
    # Get final schema version
    final_version = current_version
    try:
        version_query = "SELECT value FROM system_config WHERE key = 'schema_version';"
        version_result = query_database(version_query, fetch_one=True)# ------------- Part 8: AI/LLM & Advanced Features -------------

def store_llm_generation_result(
    requirement_id: str,
    generated_content: Dict[str, Any],
    model_name: str = "llama",
    content_type: str = "test_scenarios",
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store LLM-generated content in object storage.
    
    Args:
        requirement_id: ID of the requirement that triggered generation
        generated_content: Dictionary containing generated content
        model_name: Name of the LLM model used
        content_type: Type of content ('test_scenarios', 'test_cases', 'analysis')
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored result
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"llm_{content_type}_{requirement_id}_{timestamp}.json"
    
    # Add metadata
    generated_content['metadata'] = {
        'requirement_id': requirement_id,
        'model_name': model_name,
        'content_type': content_type,
        'generated_at': datetime.now().isoformat()
    }
    
    # Convert to JSON
    json_data = json.dumps(generated_content, indent=2)
    
    # Store in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'llm-generation',
        'model-name': model_name,
        'content-type': content_type,
        'requirement-id': requirement_id
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Record in database if it's a test scenario
    if content_type == "test_scenarios":
        # For each scenario in the generated content
        for scenario in generated_content.get('scenarios', []):
            query = """
            INSERT INTO test_scenarios
            (requirement_id, scenario_name, description, generated_by, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            update_database(
                query=query,
                params=(
                    requirement_id,
                    scenario.get('name', f"Scenario for {requirement_id}"),
                    scenario.get('description', ''),
                    f"watsonx-{model_name}",
                    'draft',
                    datetime.now()
                )
            )
    
    logger.info(f"Stored LLM generation result for requirement {requirement_id} as {file_name}")
    return file_name


def get_llm_generations_by_requirement(
    requirement_id: str,
    content_type: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> List[Dict[str, Any]]:
    """
    Retrieve LLM-generated content for a requirement.
    
    Args:
        requirement_id: ID of the requirement
        content_type: Optional content type filter
        bucket_name: Name of the bucket
        
    Returns:
        List[Dict]: List of generated content
    """
    prefix = f"llm_"
    if content_type:
        prefix += f"{content_type}_"
    prefix += f"{requirement_id}_"
    
    objects = list_storage_objects(
        prefix=prefix,
        bucket_name=bucket_name
    )
    
    results = []
    for obj in objects:
        data_bytes = download_data_from_storage(
            object_name=obj['name'],
            bucket_name=bucket_name
        )
        
        # Parse JSON
        content = json.loads(data_bytes.decode('utf-8'))
        results.append(content)
    
    logger.info(f"Retrieved {len(results)} LLM generations for requirement {requirement_id}")
    return results


def generate_test_scenarios_from_requirement(
    requirement_id: str,
    model_name: str = "llama",
    num_scenarios: int = 5,
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate test scenarios from a requirement using watsonx.ai.
    
    Args:
        requirement_id: ID of the requirement
        model_name: LLM model to use
        num_scenarios: Number of scenarios to generate
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    # Get requirement details
    try:
        requirement = get_requirement_by_id(requirement_id)
    except ValueError as e:
        logger.error(f"Failed to get requirement {requirement_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Requirement not found: {str(e)}"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test scenario generator expert. Based on the following requirement, 
        generate {num_scenarios} distinct test scenarios. For each scenario, include:
        
        1. A descriptive name
        2. A detailed description
        3. Preconditions
        4. Steps to execute
        5. Expected results
        6. Priority (High, Medium, Low)
        
        Requirement:
        Title: {title}
        Description: {description}
        
        Generate varied scenarios that cover different aspects of the requirement,
        including positive tests, negative tests, boundary conditions, and edge cases.
        """
    
    # Format prompt
    prompt = prompt_template.format(
        num_scenarios=num_scenarios,
        title=requirement.get('title', f"Requirement {requirement_id}"),
        description=requirement.get('description', '')
    )
    
    try:
        # In a real implementation, this would call the watsonx.ai API
        # For this example, we'll simulate the response
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock response with generated scenarios
        scenarios = []
        for i in range(num_scenarios):
            scenario = {
                'name': f"Test Scenario {i+1} for {requirement_id}",
                'description': f"This scenario tests a specific aspect of the requirement {requirement_id}.",
                'preconditions': [
                    f"Precondition 1 for scenario {i+1}",
                    f"Precondition 2 for scenario {i+1}"
                ],
                'steps': [
                    f"Step 1: Perform action A for scenario {i+1}",
                    f"Step 2: Verify result B for scenario {i+1}",
                    f"Step 3: Perform action C for scenario {i+1}"
                ],
                'expected_results': [
                    f"Expected result 1 for scenario {i+1}",
                    f"Expected result 2 for scenario {i+1}"
                ],
                'priority': 'High' if i < 2 else 'Medium' if i < 4 else 'Low'
            }
            scenarios.append(scenario)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_id': requirement_id,
            'requirement_title': requirement.get('title', ''),
            'scenarios': scenarios,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=requirement_id,
            generated_content=result,
            model_name=model_name,
            content_type='test_scenarios'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {num_scenarios} test scenarios for requirement {requirement_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test scenarios: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def generate_test_cases_from_scenarios(
    scenarios: List[Dict[str, Any]],
    model_name: str = "llama",
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate detailed test cases from test scenarios using watsonx.ai.
    
    Args:
        scenarios: List of scenario dictionaries
        model_name: LLM model to use
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    if not scenarios:
        logger.error("No scenarios provided")
        return {
            'status': 'error',
            'error': "No scenarios provided"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test case generation expert. Based on the following test scenario,
        create a detailed test case with specific test steps, test data, and expected results.
        
        Test Scenario:
        Name: {name}
        Description: {description}
        Preconditions: {preconditions}
        Steps: {steps}
        Expected Results: {expected_results}
        Priority: {priority}
        
        Generate a test case that includes:
        1. Specific test data values to use
        2. Detailed step-by-step test procedure
        3. Specific expected results for each step
        4. Validation points
        5. Any notes or special considerations
        """
    
    test_cases = []
    requirement_ids = set()
    
    try:
        for i, scenario in enumerate(scenarios):
            # Extract requirement ID if available
            requirement_id = scenario.get('requirement_id', f"REQ_{int(time.time())}")
            requirement_ids.add(requirement_id)
            
            # Format scenario details for prompt
            scenario_details = {
                'name': scenario.get('name', f"Scenario {i+1}"),
                'description': scenario.get('description', ''),
                'preconditions': '\n'.join(scenario.get('preconditions', [])),
                'steps': '\n'.join(scenario.get('steps', [])),
                'expected_results': '\n'.join(scenario.get('expected_results', [])),
                'priority': scenario.get('priority', 'Medium')
            }
            
            # Format prompt for this scenario
            prompt = prompt_template.format(**scenario_details)
            
            # Simulate API call delay
            import time
            time.sleep(0.5)
            
            # Mock test case generation
            test_case = {
                'id': f"TC_{int(time.time())}_{i}",
                'name': f"Test Case for {scenario_details['name']}",
                'description': f"Detailed test case for {scenario_details['name']}",
                'requirement_id': requirement_id,
                'scenario_name': scenario_details['name'],
                'priority': scenario_details['priority'],
                'test_data': {
                    'input1': 'Sample input value 1',
                    'input2': 'Sample input value 2'
                },
                'steps': [
                    {
                        'number': 1,
                        'description': 'Perform specific action A with test data',
                        'expected_result': 'System should respond with X'
                    },
                    {
                        'number': 2,
                        'description': 'Verify specific condition B',
                        'expected_result': 'Condition B should be true'
                    },
                    {
                        'number': 3,
                        'description': 'Perform specific action C',
                        'expected_result': 'System should update with Y'
                    }
                ],
                'validation_points': [
                    'Validate that X appears correctly',
                    'Validate that Y contains the expected data'
                ],
                'notes': 'This test case covers the main positive flow'
            }
            
            test_cases.append(test_case)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_ids': list(requirement_ids),
            'test_cases': test_cases,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=list(requirement_ids)[0] if requirement_ids else "multiple",
            generated_content=result,
            model_name=model_name,
            content_type='test_cases'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {len(test_cases)} test cases from {len(scenarios)} scenarios")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test cases: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def analyze_test_failure(
    execution_id: str,
    model_name: str = "llama",
    include_similar_failures: bool = True
) -> Dict[str, Any]:
    """
    Analyze a test failure using watsonx.ai to determine potential causes and solutions.
    
    Args:
        execution_id: ID of the failed test execution
        model_name: LLM model to use
        include_similar_failures: Whether to include similar historical failures
        
    Returns:
        Dict: Analysis results and recommendations
    """
    # Get execution details
    try:
        execution = get_test_execution(execution_id)
    except ValueError as e:
        logger.error(f"Failed to get execution {execution_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Execution not found: {str(e)}"
        }
    
    # Check if execution is failed
    if execution.get('status', '').lower() != 'failed':
        logger.warning(f"Execution {execution_id} is not failed (status: {execution.get('status')})")
        return {
            'status': 'error',
            'error': f"Execution is not failed (status: {execution.get('status')})"
        }
    
    # Get test case details
    test_case_id = execution['metadata']['test_case_id']
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError:
        test_case = {'id': test_case_id}  # Minimal info if test case not found
    
    # Find the failed steps
    steps = execution.get('execution_steps', [])
    failed_steps = [step for step in steps if step.get('status', '').lower() == 'failed']
    
    if not failed_steps:
        logger.warning(f"No failed steps found in execution {execution_id}")
        return {
            'status': 'warning',
            'warning': "No failed steps found in execution",
            'execution_id': execution_id
        }
    
    # Get similar failures if requested
    similar_failures = []
    if include_similar_failures:
        # Query for similar failures
        query = """
        SELECT e.execution_id, e.test_case_id, e.status, e.executed_at
        FROM test_executions e
        WHERE e.test_case_id = %s 
        AND e.status = 'failed'
        AND e.execution_id != %s
        ORDER BY e.executed_at DESC
        LIMIT 5
        """
        
        similar_results = query_database(
            query=query,
            params=(test_case_id, execution_id)
        )
        
        for result in similar_results:
            try:
                similar_execution = get_test_execution(result['execution_id'])
                similar_failures.append(similar_execution)
            except ValueError:
                pass
    
    try:
        # Prepare analysis context
        analysis_context = {
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'execution_time': execution.get('execution_time', 0),
            'failed_steps': failed_steps,
            'similar_failures': len(similar_failures)
        }
        
        # Build prompt for watsonx.ai
        prompt = f"""
        Analyze the following test failure and provide potential causes and solutions.
        
        Test Case: {test_case.get('name', test_case_id)}
        Execution ID: {execution_id}
        
        Failed Steps:
        {json.dumps(failed_steps, indent=2)}
        
        Similar Failures: {len(similar_failures)} recent failures of this test case.
        
        Provide:
        1. Most likely causes of failure
        2. Recommended troubleshooting steps
        3. Potential fixes
        4. Is this likely a defect in the application or an issue with the test?
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock analysis results
        analysis_results = {
            'potential_causes': [
                {
                    'description': 'Data inconsistency in test environment',
                    'probability': 'High',
                    'explanation': 'The error message indicates a mismatch between expected and actual data values'
                },
                {
                    'description': 'Timing issue - operation not completed before verification',
                    'probability': 'Medium',
                    'explanation': 'The failure occurs during a verification step that may be executing too soon'
                },
                {
                    'description': 'Application defect in data processing logic',
                    'probability': 'Medium',
                    'explanation': 'The specific error pattern matches known issues in the data processing component'
                }
            ],
            'troubleshooting_steps': [
                'Verify test data is consistent with current environment state',
                'Add appropriate wait condition before verification step',
                'Review application logs for exceptions around the time of failure',
                'Compare with previous successful executions to identify changes'
            ],
            'potential_fixes': [
                {
                    'type': 'Test Update',
                    'description': 'Introduce a wait mechanism before verification',
                    'difficulty': 'Low'
                },
                {
                    'type': 'Environment Fix',
                    'description': 'Refresh test data to ensure consistency',
                    'difficulty': 'Medium'
                },
                {
                    'type': 'Application Fix',
                    'description': 'Review and correct data processing logic in the application',
                    'difficulty': 'High'
                }
            ],
            'defect_assessment': {
                'likely_application_defect': True,
                'confidence': 70,
                'explanation': 'Based on the error patterns and similar failures, there is a 70% probability this is an application defect rather than a test issue.'
            }
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'analysis_context': analysis_context,
            'analysis_results': analysis_results,
            'similar_failure_count': len(similar_failures),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='failure_analysis'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Completed failure analysis for execution {execution_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze test failure: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def suggest_test_case_improvements(
    test_case_id: str,
    model_name: str = "llama"
) -> Dict[str, Any]:
    """
    Use watsonx.ai to suggest improvements for an existing test case.
    
    Args:
        test_case_id: ID of the test case to improve
        model_name: LLM model to use
        
    Returns:
        Dict: Improvement suggestions and metadata
    """
    # Get test case details
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError as e:
        logger.error(f"Failed to get test case {test_case_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Test case not found: {str(e)}"
        }
    
    # Get test execution history
    query = """
    SELECT status, COUNT(*) as count
    FROM test_executions
    WHERE test_case_id = %s
    GROUP BY status
    """
    
    execution_stats = query_database(query, (test_case_id,))
    execution_history = {row['status']: row['count'] for row in execution_stats}
    
    # Get defects associated with this test case
    defects = get_defects(test_case_id=test_case_id)
    
    try:
        # Build prompt for watsonx.ai
        prompt = f"""
        Review the following test case and suggest improvements to make it more robust and effective.
        
        Test Case: {test_case.get('name', test_case_id)}
        Description: {test_case.get('description', '')}
        
        Current Test Steps:
        {json.dumps(test_case.get('steps', []), indent=2)}
        
        Execution History:
        {json.dumps(execution_history, indent=2)}
        
        Associated Defects: {len(defects)}
        
        Provide:
        1. Overall assessment of the test case
        2. Specific improvement suggestions
        3. Additional test scenarios that should be covered
        4. Recommendations for better test data
        5. Any validation points that should be added
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock improvement suggestions
        improvement_suggestions = {
            'overall_assessment': {
                'quality_score': 7,  # 1-10 scale
                'strengths': [
                    'Good coverage of main functionality',
                    'Clear step descriptions'
                ],
                'weaknesses': [
                    'Limited validation points',
                    'Missing boundary condition tests',
                    'No negative test scenarios'
                ]
            },
            'specific_improvements': [
                {
                    'step_index': 2,
                    'current': test_case.get('steps', [])[2] if len(test_case.get('steps', [])) > 2 else {},
                    'suggestion': 'Add specific validation for the returned data format',
                    'rationale': 'Current step only verifies presence but not structure'
                },
                {
                    'type': 'Add Step',
                    'suggestion': 'Add verification step after data submission',
                    'rationale': 'Should verify successful data processing before proceeding'
                },
                {
                    'type': 'Modify Test Data',
                    'suggestion': 'Use more diverse test data including boundary values',
                    'rationale': 'Current test data only covers happy path'
                }
            ],
            'additional_scenarios': [
                {
                    'name': 'Negative Test - Invalid Input',
                    'description': 'Test behavior when invalid data is provided',
                    'steps': [
                        'Attempt to submit invalid data format',
                        'Verify appropriate error message is displayed',
                        'Verify no data corruption occurs'
                    ]
                },
                {
                    'name': 'Boundary Test - Maximum Values',
                    'description': 'Test behavior with maximum allowed values',
                    'steps': [
                        'Submit form with maximum length strings',
                        'Verify data is accepted and processed correctly',
                        'Verify display handles long values appropriately'
                    ]
                }
            ],
            'test_data_recommendations': [
                'Include null values for optional fields',
                'Add test case with maximum length strings',
                'Include special characters in text fields',
                'Test with minimum and maximum numeric values'
            ],
            'validation_points': [
                'Verify response times are within acceptable limits',
                'Check both UI updates and backend data consistency',
                'Validate error message content for clarity and correctness',
                'Ensure no unnecessary database queries are triggered'
            ]
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'improvement_suggestions': improvement_suggestions,
            'execution_history': execution_history,
            'defect_count': len(defects),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='test_improvement'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated improvement suggestions for test case {test_case_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test case improvements: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def create_database_backup(
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> str:
    """
    Create a backup of database tables in JSON format.
    
    Args:
        bucket_name: Name of the bucket
        tables: List of tables to backup (default: all tables)
        
    Returns:
        str: Object name of the backup file
    """
    if not tables:
        # Get all tables
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
        results = query_database(query)
        tables = [row['table_name'] for row in results]
    
    backup_data = {}
    
    for table in tables:
        query = f"SELECT * FROM {table};"
        results = query_database(query)
        
        # Convert datetime objects to ISO format
        for row in results:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
        
        backup_data[table] = results
    
    # Create backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"database_backup_{timestamp}.json"
    
    json_data = json.dumps(backup_data, indent=2)
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=backup_file_name,
        bucket_name=bucket_name,
        metadata={
            'content-type': 'application/json',
            'source': 'watsonx-ipg-testing',
            'type': 'database-backup',
            'tables': ','.join(tables)
        },
        content_type='application/json'
    )
    
    logger.info(f"Created database backup of {len(tables)} tables as {backup_file_name}")
    return backup_file_name


def restore_database_from_backup(
    backup_file_name: str,
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> Dict[str, Any]:
    """
    Restore database tables from a backup file.
    
    Args:
        backup_file_name: Name of the backup file
        bucket_name: Name of the bucket
        tables: Optional list of specific tables to restore
        
    Returns:
        Dict: Restoration status and details
    """
    try:
        # Download backup file
        data_bytes = download_data_from_storage(
            object_name=backup_file_name,
            bucket_name=bucket_name
        )
        
        # Parse JSON
        backup_data = json.loads(data_bytes.decode('utf-8'))
        
        # Determine which tables to restore
        tables_to_restore = tables or list(backup_data.keys())
        
        # Verify tables exist in backup
        missing_tables = [table for table in tables_to_restore if table not in backup_data]
        if missing_tables:
            logger.error(f"Tables not found in backup: {', '.join(missing_tables)}")
            return {
                'status': 'error',
                'error': f"Tables not found in backup: {', '.join(missing_tables)}"
            }
        
        # Restore each table
        restoration_results = {}
        for table in tables_to_restore:
            try:
                # Delete existing data
                delete_query = f"DELETE FROM {table};"
                update_database(delete_query)
                
                # Insert backup data
                rows = backup_data[table]
                if not rows:
                    restoration_results[table] = {
                        'status': 'success',
                        'rows_restored': 0
                    }
                    continue
                
                # Build insert query
                columns = list(rows[0].keys())
                placeholders = ", ".join(["%s"] * len(columns))
                column_list = ", ".join(columns)
                
                insert_query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                
                # Prepare params for batch insert
                params_list = []
                for row in rows:
                    # Ensure row values are in the same order as columns
                    row_values = [row[col] for col in columns]
                    params_list.append(row_values)
                
                # Perform batch insert
                affected_rows = batch_update_database(
                    query=insert_query,
                    params_list=params_list
                )
                
                restoration_results[table] = {
                    'status': 'success',
                    'rows_restored': affected_rows
                }
                
            except Exception as e:
                logger.error(f"Failed to restore table {table}: {str(e)}")
                restoration_results[table] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check overall status
        success_count = sum(1 for result in restoration_results.values() if result['status'] == 'success')
        
        logger.info(f"Restored {success_count} of {len(tables_to_restore)} tables from backup {backup_file_name}")
        return {
            'status': 'success' if success_count == len(tables_to_restore) else 'partial',
            'tables_restored': success_count,
            'total_tables': len(tables_to_restore),
            'details': restoration_results
        }
        
    except Exception as e:
        logger.error(f"Failed to restore from backup {backup_file_name}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Restoration failed: {str(e)}"
        }


def cleanup_old_data(
    retention_days: int = 90,
    data_types: List[str] = None
) -> Dict[str, int]:
    """
    Clean up old data based on retention policy.
    
    Args:
        retention_days: Number of days to retain data
        data_types: Types of data to clean up (default: all)
        
    Returns:
        Dict: Number of records deleted by type
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deletion_counts = {}
    
    # Define data types and their cleanup queries
    cleanup_queries = {
        'test_executions': """
            DELETE FROM test_executions
            WHERE executed_at < %s
            """,
        'defects': """
            DELETE FROM defects
            WHERE status = 'closed'
            AND updated_at < %s
            """,
        'sharepoint_documents': """
            DELETE FROM sharepoint_documents
            WHERE sync_status = 'synced'
            AND created_at < %s
            """,
        'blueprism_jobs': """
            DELETE FROM blueprism_jobs
            WHERE completed_at < %s
            """,
        'uft_jobs': """
            DELETE FROM uft_jobs
            WHERE completed_at < %s
            """
    }
    
    # Determine which data types to clean up
    types_to_clean = data_types or list(cleanup_queries.keys())
    
    # Execute cleanup for each type
    for data_type in types_to_clean:
        if data_type in cleanup_queries:
            query = cleanup_queries[data_type]
            try:
                affected_rows = update_database(
                    query=query,
                    params=(cutoff_date,)
                )
                deletion_counts[data_type] = affected_rows
                logger.info(f"Deleted {affected_rows} old records from {data_type}")
            except Exception as e:
                logger.error(f"Failed to clean up {data_type}: {str(e)}")
                deletion_counts[data_type] = 0
    
    # Cleanup old files in object storage
    try:
        prefix = ""  # Clean up all prefixes
        objects = list_storage_objects(prefix=prefix)
        
        deleted_objects = 0
        for obj in objects:
            # Skip recent objects
            if datetime.now() - obj['last_modified'] < timedelta(days=retention_days):
                continue
            
            # Skip backup files and important artifacts
            if 'backup' in obj['name'] or 'archive' in obj['name']:
                continue
            
            # Delete old object
            try:
                delete_from_storage(obj['name'])
                deleted_objects += 1
            except:
                pass
        
        deletion_counts['object_storage'] = deleted_objects
        logger.info(f"Deleted {deleted_objects} old objects from storage")
    except Exception as e:
        logger.error(f"Failed to clean up object storage: {str(e)}")
        deletion_counts['object_storage'] = 0
    
    return deletion_counts


# ------------- Cache Management -------------

_cache = {}  # Simple in-memory cache

def cache_result(key: str, value: Any, ttl_seconds: int = 300):
    """
    Cache a result in memory.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl_seconds: Time to live in seconds
    """
    expiry = time.time() + ttl_seconds
    _cache[key] = (value, expiry)


def get_cached_result(key: str) -> Optional[Any]:
    """
    Get a result from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Optional[Any]: Cached value or None if expired/not found
    """
    if key in _cache:
        value, expiry = _cache[key]
        if time.time() < expiry:
            return value
        
        # Expired
        del _cache[key]
    
    return None


def clear_cache():
    """Clear the entire cache."""
    _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the cache.
    
    Returns:
        Dict: Cache statistics
    """
    now = time.time()
    total_items = len(_cache)
    expired_items = sum(1 for _, expiry in _cache.values() if now >= expiry)
    valid_items = total_items - expired_items
    
    # Calculate memory usage (approximate)
    import sys
    memory_usage = sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in _cache.items())
    
    return {
        'total_items': total_items,
        'valid_items': valid_items,
        'expired_items': expired_items,
        'memory_usage_bytes': memory_usage
    }


# ------------- Health Check Functions -------------

def perform_health_check() -> Dict[str, Any]:
    """
    Perform a health check on all database components.
    
    Returns:
        Dict: Health status for each component
    """
    health = {
        'database': is_database_healthy(),
        'object_storage': is_storage_healthy(),
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Check table existence and row counts
    tables = [
        'test_cases', 'test_executions', 'defects', 'test_data',
        'integration_credentials', 'sharepoint_documents', 'blueprism_jobs'
    ]
    
    for table in tables:
        try:
            exists = table_exists(table)
            
            if exists:
                count_query = f"SELECT COUNT(*) as count FROM {table};"
                count_result = query_database(count_query, fetch_one=True)
                row_count = count_result['count'] if count_result else 0
            else:
                row_count = 0
            
            health['components'][table] = {
                'exists': exists,
                'row_count': row_count,
                'status': 'healthy' if exists else 'missing'
            }
        except Exception as e:
            health['components'][table] = {
                'exists': False,
                'status': 'error',
                'error': str(e)
            }
    
    # Check connection to integration systems
    integration_systems = [
        'jira', 'sharepoint', 'alm', 'blueprism', 'uft'
    ]
    
    for system in integration_systems:
        try:
            # Check if credentials exist
            has_credentials = False
            try:
                get_integration_credentials(system, decrypt=False)
                has_credentials = True
            except ValueError:
                pass
            
            health['components'][f"{system}_integration"] = {
                'credentials_exist': has_credentials,
                'status': 'configured' if has_credentials else 'not_configured'
            }
        except Exception as e:
            health['components'][f"{system}_integration"] = {
                'status': 'error',
                'error': str(e)
            }
    
    # Overall status
    critical_components = ['database', 'object_storage']
    critical_status = all(health[component] for component in critical_components)
    health['overall_status'] = 'healthy' if critical_status else 'degraded'
    
    logger.info(f"Health check completed: {health['overall_status']}")
    return health


def analyze_database_performance() -> Dict[str, Any]:
    """
    Analyze database performance metrics.
    
    Returns:
        Dict: Performance analysis results
    """
    try:
        # Query for database statistics
        stats_queries = {
            'table_stats': """
                SELECT 
                    relname as table_name, 
                    n_live_tup as row_count,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """,
            'index_stats': """
                SELECT
                    indexrelname as index_name,
                    relname as table_name,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
            """,
            'table_io_stats': """
                SELECT
                    relname as table_name,
                    heap_blks_read as disk_reads,
                    heap_blks_hit as cache_hits,
                    CASE WHEN heap_blks_read + heap_blks_hit > 0 
                        THEN heap_blks_hit::float / (heap_blks_read + heap_blks_hit) * 100
                        ELSE 0 
                    END as cache_hit_ratio
                FROM pg_statio_user_tables
                ORDER BY heap_blks_read + heap_blks_hit DESC
            """
        }
        
        # Execute queries
        stats_results = {}
        for key, query in stats_queries.items():
            stats_results[key] = query_database(query)
        
        # Calculate overall statistics
        total_rows = sum(table['row_count'] for table in stats_results['table_stats'])
        total_dead_rows = sum(table['dead_rows'] for table in stats_results['table_stats'])
        dead_row_ratio = (total_dead_rows / total_rows * 100) if total_rows > 0 else 0
        
        total_disk_reads = sum(table['disk_reads'] for table in stats_results['table_io_stats'])
        total_cache_hits = sum(table['cache_hits'] for table in stats_results['table_io_stats'])
        overall_cache_hit_ratio = (total_cache_hits / (total_disk_reads + total_cache_hits) * 100) if (total_disk_reads + total_cache_hits) > 0 else 0
        
        # Identify tables that might need vacuuming (high dead row ratio)
        vacuum_candidates = [
            {
                'table_name': table['table_name'],
                'dead_rows': table['dead_rows'],
                'row_count': table['row_count'],
                'dead_row_ratio': (table['dead_rows'] / table['row_count'] * 100) if table['row_count'] > 0 else 0,
                'last_vacuum': table['last_vacuum'].isoformat() if table['last_vacuum'] else None
            }
            for table in stats_results['table_stats']
            if table['row_count'] > 0 and (table['dead_rows'] / table['row_count']) >= 0.2  # 20% or more dead rows
        ]
        
        # Identify unused indexes
        unused_indexes = [
            {
                'index_name': index['index_name'],
                'table_name': index['table_name'],
                'index_scans': index['index_scans']
            }
            for index in stats_results['index_stats']
            if index['index_scans'] == 0
        ]
        
        # Identify tables with low cache hit ratio
        low_cache_hit_tables = [
            {
                'table_name': table['table_name'],
                'disk_reads': table['disk_reads'],
                'cache_hits': table['cache_hits'],
                'cache_hit_ratio': table['cache_hit_ratio']
            }
            for table in stats_results['table_io_stats']
            if table['cache_hit_ratio'] < 90 and (table['disk_reads'] + table['cache_hits']) > 100  # Less than 90% cache hits and significant I/O
        ]
        
        # Prepare recommendations
        recommendations = []
        
        if vacuum_candidates:
            recommendations.append({
                'type': 'vacuum',
                'message': f"Consider running VACUUM on {len(vacuum_candidates)} tables with high dead row ratios",
                'tables': [table['table_name'] for table in vacuum_candidates]
            })
        
        if unused_indexes:
            recommendations.append({
                'type': 'unused_indexes',
                'message': f"Consider removing {len(unused_indexes)} unused indexes to improve write performance",
                'indexes': [f"{index['table_name']}.{index['index_name']}" for index in unused_indexes]
            })
        
        if low_cache_hit_tables:
            recommendations.append({
                'type': 'cache_optimization',
                'message': f"{len(low_cache_hit_tables)} tables have low cache hit ratios, consider increasing shared_buffers",
                'tables': [table['table_name'] for table in low_cache_hit_tables]
            })
        
        # Final analysis result
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tables': len(stats_results['table_stats']),
                'total_indexes': len(stats_results['index_stats']),
                'total_rows': total_rows,
                'dead_row_ratio': dead_row_ratio,
                'overall_cache_hit_ratio': overall_cache_hit_ratio
            },
            'top_tables_by_size': stats_results['table_stats'][:5],
            'vacuum_candidates': vacuum_candidates,
            'unused_indexes': unused_indexes,
            'low_cache_hit_tables': low_cache_hit_tables,
            'recommendations': recommendations
        }
        
        logger.info(f"Database performance analysis completed with {len(recommendations)} recommendations")
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze database performance: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def optimize_database() -> Dict[str, Any]:
    """
    Perform database optimization operations.
    
    Returns:
        Dict: Optimization results
    """
    try:
        # Analyze tables
        analyze_query = "ANALYZE;"
        update_database(analyze_query)
        
        # Get tables that need vacuuming
        vacuum_query = """
        SELECT 
            relname as table_name,
            n_dead_tup as dead_rows,
            n_live_tup as row_count,
            CASE WHEN n_live_tup > 0 
                THEN n_dead_tup::float / n_live_tup 
                ELSE 0 
            END as dead_ratio
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        AND n_dead_tup > 0
        AND (n_dead_tup::float / n_live_tup) >= 0.2
        ORDER BY dead_ratio DESC
        """
        
        vacuum_candidates = query_database(vacuum_query)
        
        # Vacuum each table
        vacuum_results = []
        for table in vacuum_candidates:
            table_name = table['table_name']
            try:
                vacuum_table_query = f"VACUUM ANALYZE {table_name};"
                update_database(vacuum_table_query)
                vacuum_results.append({
                    'table_name': table_name,
                    'status': 'success',
                    'dead_rows_before': table['dead_rows']
                })
                logger.info(f"Vacuumed table {table_name} with {table['dead_rows']} dead rows")
            except Exception as e:
                vacuum_results.append({
                    'table_name': table_name,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Failed to vacuum table {table_name}: {str(e)}")
        
        # Get unused indexes
        unused_index_query = """
        SELECT
            indexrelname as index_name,
            relname as table_name,
            idx_scan as index_scans
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        AND indexrelname NOT IN (
            SELECT indexrelname
            FROM pg_constraint c
            JOIN pg_index i ON c.conindid = i.indexrelid
            JOIN pg_stat_user_indexes s ON s.indexrelid = i.indexrelid
            WHERE c.contype = 'p'
        )
        ORDER BY pg_relation_size(indexrelid) DESC
        """
        
        unused_indexes = query_database(unused_index_query)
        
        # Don't automatically drop indexes, just report them
        
        # Reindex important tables
        important_tables = [
            'test_cases', 'test_executions', 'defects'
        ]
        
        reindex_results = []
        for table in important_tables:
            try:
                if table_exists(table):
                    reindex_query = f"REINDEX TABLE {table};"
                    update_database(reindex_query)
                    reindex_results.append({
                        'table_name': table,
                        'status': 'success'
                    })
                    logger.info(f"Reindexed table {table}")
                else:
                    reindex_results.append({
                        'table_name': table,
                        'status': 'skipped',
                        'reason': 'table does not exist'
                    })
            except Exception as e:
                reindex_results.append({
                    'table_name': table,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Failed to reindex table {table}: {str(e)}")
        
        # Final optimization result
        result = {
            'timestamp': datetime.now().isoformat(),
            'tables_vacuumed': len([r for r in vacuum_results if r['status'] == 'success']),
            'tables_reindexed': len([r for r in reindex_results if r['status'] == 'success']),
            'unused_indexes_found': len(unused_indexes),
            'vacuum_results': vacuum_results,
            'reindex_results': reindex_results,
            'unused_indexes': unused_indexes
        }
        
        logger.info(f"Database optimization completed: {result['tables_vacuumed']} tables vacuumed, {result['tables_reindexed']} tables reindexed")
        return result
        
    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"Optimization failed: {str(e)}"
        }


def validate_database_schema() -> Dict[str, Any]:
    """
    Validate the database schema against the expected schema.
    
    Returns:
        Dict: Validation results
    """
    # Define expected tables and their required columns
    expected_schema = {
        'test_cases': [
            'id', 'name', 'description', 'version', 'storage_path', 
            'format', 'status', 'created_at', 'updated_at'
        ],
        'test_executions': [
            'execution_id', 'test_case_id', 'status', 'result_path', 
            'execution_time', 'screenshots', 'executed_at', 'notes'
        ],
        'defects': [
            'id', 'test_case_id', 'execution_id', 'defect_id', 
            'summary', 'description', 'severity', 'assigned_to', 
            'status', 'resolution', 'created_at', 'updated_at'
        ],
        'test_data': [
            'id', 'test_case_id', 'data_type', 'storage_path', 
            'created_at', 'updated_at'
        ],
        'integration_credentials': [
            'id', 'system_type', 'credentials', 'encrypted', 
            'created_at', 'updated_at'
        ],
        'sharepoint_documents': [
            'id', 'file_name', 'storage_path', 'content_type', 
            'sync_status', 'created_at', 'synced_at'
        ],
        'blueprism_jobs': [
            'id', 'job_id', 'test_case_id', 'controller_file', 
            'status', 'started_at', 'completed_at', 'result'
        ],
        'execution_metrics': [
            'id', 'execution_id', 'test_case_id', 'start_time', 
            'end_time', 'duration', 'status', 'environment'
        ]
    }
    
    validation_results = {}
    missing_tables = []
    schema_issues = []
    
    # Check each expected table
    for table, expected_columns in expected_schema.items():
        if not table_exists(table):
            missing_tables.append(table)
            validation_results[table] = {
                'exists': False,
                'status': 'missing'
            }
            continue
        
        # Get actual columns
        actual_columns = get_column_info(table)
        actual_column_names = [col['column_name'] for col in actual_columns]
        
        # Check for missing columns
        missing_columns = [col for col in expected_columns if col not in actual_column_names]
        
        if missing_columns:
            schema_issues.append({
                'table': table,
                'issue': 'missing_columns',
                'columns': missing_columns
            })
            validation_results[table] = {
                'exists': True,
                'status': 'incomplete',
                'missing_columns': missing_columns
            }
        else:
            validation_results[table] = {
                'exists': True,
                'status': 'valid',
                'columns': len(actual_columns)
            }
    
    # Overall validation result
    status = 'valid'
    if missing_tables:
        status = 'missing_tables'
    elif schema_issues:
        status = 'schema_issues'
    
    result = {
        'status': status,
        'missing_tables': missing_tables,
        'schema_issues': schema_issues,
        'tables_validated': len(validation_results),
        'valid_tables': len([r for r in validation_results.values() if r['status'] == 'valid']),
        'details': validation_results
    }
    
    logger.info(f"Database schema validation completed: {result['status']}")
    return result


def upgrade_database_schema(
    version: str = None
) -> Dict[str, Any]:
    """
    Upgrade the database schema to a specified version.
    
    Args:
        version: Target schema version (default: latest)
        
    Returns:
        Dict: Upgrade results
    """
    # Check current schema version
    current_version = "0.0.0"
    try:
        version_query = "SELECT value FROM system_config WHERE key = 'schema_version';"
        version_result = query_database(version_query, fetch_one=True)
        if version_result:
            final_version = version_result['value']
    except:
        pass
    
    # Determine overall status
    successful_upgrades = [r for r in results if r['status'] == 'success']
    all_success = len(successful_upgrades) == len(versions_to_apply)
    
    result = {
        'status': 'success' if all_success else 'partial',
        'initial_version': current_version,
        'target_version': target_version,
        'final_version': final_version,
        'versions_applied': len(successful_upgrades),
        'total_versions': len(versions_to_apply),
        'details': results
    }
    
    logger.info(f"Database schema upgrade from {current_version} to {final_version} completed with status {result['status']}")
    return result


def analyze_system_health() -> Dict[str, Any]:
    """
    Perform a comprehensive system health analysis.
    
    Returns:
        Dict: System health analysis and recommendations
    """
    # Collect health information from various components
    health_results = {
        'database': perform_health_check(),
        'db_performance': analyze_database_performance(),
        'schema': validate_database_schema(),
        'cache': get_cache_stats(),
        'timestamp': datetime.now().isoformat()
    }
    
    # Determine system status
    if not health_results['database']['database']:
        status = 'critical'
        primary_issue = 'Database connection failure'
    elif not health_results['database']['object_storage']:
        status = 'critical'
        primary_issue = 'Object storage connection failure'
    elif health_results['schema']['status'] != 'valid':
        status = 'warning'
        primary_issue = 'Database schema issues detected'
    elif health_results['db_performance'].get('error'):
        status = 'warning'
        primary_issue = 'Unable to analyze database performance'
    elif len(health_results['db_performance'].get('recommendations', [])) > 0:
        status = 'needs_optimization'
        primary_issue = 'Database optimization recommended'
    else:
        status = 'healthy'
        primary_issue = None
    
    # Compile recommendations
    recommendations = []
    
    # Add database performance recommendations
    if 'recommendations' in health_results['db_performance']:
        for rec in health_results['db_performance']['recommendations']:
            recommendations.append({
                'category': 'database',
                'priority': 'medium',
                'message': rec['message'],
                'details': rec
            })
    
    # Add schema recommendations
    if health_results['schema']['status'] == 'missing_tables':
        recommendations.append({
            'category': 'schema',
            'priority': 'high',
            'message': f"Missing tables: {', '.join(health_results['schema']['missing_tables'])}",
            'action': 'Run database initialization or schema upgrade'
        })
    elif health_results['schema']['status'] == 'schema_issues':
        recommendations.append({
            'category': 'schema',
            'priority': 'medium',
            'message': f"Schema issues detected in {len(health_results['schema']['schema_issues'])} tables",
            'action': 'Run schema upgrade to fix missing columns'
        })
    
    # Add overall system health result
    result = {
        'status': status,
        'primary_issue': primary_issue,
        'timestamp': datetime.now().isoformat(),
        'recommendations': recommendations,
        'components': {
            'database': health_results['database']['overall_status'],
            'schema': health_results['schema']['status'],
            'performance': 'issue' if len(health_results['db_performance'].get('recommendations', [])) > 0 else 'good'
        },
        'details': health_results
    }
    
    logger.info(f"System health analysis completed: {status}")
    return result

# End of Part 8: AI/LLM & Advanced Features
        if version_result:
            current_version = version_result['value']
    except:
        # Table might not exist yet
        pass
    
    # Define schema upgrades with version numbers
    schema_upgrades = {
        "1.0.0": [
            # Initial schema creation
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """,
            """
            INSERT INTO system_config (key, value, updated_at)
            VALUES ('schema_version', '1.0.0', NOW())
            ON CONFLICT (key) DO UPDATE SET value = '1.0.0', updated_at = NOW()
            """
        ],
        "1.1.0": [
            # Add new fields to test_cases
            """
            ALTER TABLE test_cases
            ADD COLUMN IF NOT EXISTS priority VARCHAR(20)
            """,
            """
            ALTER TABLE test_cases
            ADD COLUMN IF NOT EXISTS estimated_duration INTEGER
            """,
            """
            UPDATE system_config SET value = '1.1.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ],
        "1.2.0": [
            # Add test_scenarios table
            """
            CREATE TABLE IF NOT EXISTS test_scenarios (
                id SERIAL PRIMARY KEY,
                requirement_id VARCHAR(255) NOT NULL,
                scenario_name VARCHAR(255) NOT NULL,
                description TEXT,
                generated_by VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                test_case_ids JSONB,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP
            )
            """,
            """
            UPDATE system_config SET value = '1.2.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ],
        "1.3.0": [
            # Add indexes for better performance
            """
            CREATE INDEX IF NOT EXISTS idx_test_executions_test_case_id
            ON test_executions(test_case_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_defects_test_case_id
            ON defects(test_case_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_test_cases_status
            ON test_cases(status)
            """,
            """
            UPDATE system_config SET value = '1.3.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ]
    }
    
    # Determine target version
    if not version:
        available_versions = sorted(list(schema_upgrades.keys()))
        if not available_versions:
            return {
                'status': 'no_upgrades',
                'current_version': current_version
            }
        target_version = available_versions[-1]  # Latest version
    else:
        if version not in schema_upgrades:
            return {
                'status': 'error',
                'error': f"Unknown version: {version}",
                'available_versions': list(schema_upgrades.keys())
            }
        target_version = version
    
    # Check if upgrade is needed
    from packaging import version as pkg_version
    if pkg_version.parse(current_version) >= pkg_version.parse(target_version):
        return {
            'status': 'already_current',
            'current_version': current_version,
            'target_version': target_version
        }
    
    # Sort versions for sequential upgrade
    versions_to_apply = [v for v in sorted(schema_upgrades.keys()) 
                        if pkg_version.parse(v) > pkg_version.parse(current_version)
                        and pkg_version.parse(v) <= pkg_version.parse(target_version)]
    
    # Apply upgrades in sequence
    results = []
    for upgrade_version in versions_to_apply:
        version_result = {
            'version': upgrade_version,
            'status': 'pending',
            'queries': []
        }
        
        try:
            # Execute each upgrade query
            for i, query in enumerate(schema_upgrades[upgrade_version]):
                try:
                    update_database(query)
                    version_result['queries'].append({
                        'index': i,
                        'status': 'success'
                    })
                except Exception as e:
                    version_result['queries'].append({
                        'index': i,
                        'status': 'error',
                        'error': str(e)
                    })
                    raise
            
            version_result['status'] = 'success'
            
        except Exception as e:
            version_result['status'] = 'error'
            version_result['error'] = str(e)
            results.append(version_result)
            break
        
        results.append(version_result)
    
    # Get final schema version
    final_version = current_version
    try:
        version_query = "SELECT value FROM system_config WHERE key = 'schema_version';"
        version_result = query_database(version_query, fetch_one=True)# ------------- Part 8: AI/LLM & Advanced Features -------------

def store_llm_generation_result(
    requirement_id: str,
    generated_content: Dict[str, Any],
    model_name: str = "llama",
    content_type: str = "test_scenarios",
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store LLM-generated content in object storage.
    
    Args:
        requirement_id: ID of the requirement that triggered generation
        generated_content: Dictionary containing generated content
        model_name: Name of the LLM model used
        content_type: Type of content ('test_scenarios', 'test_cases', 'analysis')
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored result
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"llm_{content_type}_{requirement_id}_{timestamp}.json"
    
    # Add metadata
    generated_content['metadata'] = {
        'requirement_id': requirement_id,
        'model_name': model_name,
        'content_type': content_type,
        'generated_at': datetime.now().isoformat()
    }
    
    # Convert to JSON
    json_data = json.dumps(generated_content, indent=2)
    
    # Store in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'llm-generation',
        'model-name': model_name,
        'content-type': content_type,
        'requirement-id': requirement_id
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Record in database if it's a test scenario
    if content_type == "test_scenarios":
        # For each scenario in the generated content
        for scenario in generated_content.get('scenarios', []):
            query = """
            INSERT INTO test_scenarios
            (requirement_id, scenario_name, description, generated_by, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            update_database(
                query=query,
                params=(
                    requirement_id,
                    scenario.get('name', f"Scenario for {requirement_id}"),
                    scenario.get('description', ''),
                    f"watsonx-{model_name}",
                    'draft',
                    datetime.now()
                )
            )
    
    logger.info(f"Stored LLM generation result for requirement {requirement_id} as {file_name}")
    return file_name


def get_llm_generations_by_requirement(
    requirement_id: str,
    content_type: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> List[Dict[str, Any]]:
    """
    Retrieve LLM-generated content for a requirement.
    
    Args:
        requirement_id: ID of the requirement
        content_type: Optional content type filter
        bucket_name: Name of the bucket
        
    Returns:
        List[Dict]: List of generated content
    """
    prefix = f"llm_"
    if content_type:
        prefix += f"{content_type}_"
    prefix += f"{requirement_id}_"
    
    objects = list_storage_objects(
        prefix=prefix,
        bucket_name=bucket_name
    )
    
    results = []
    for obj in objects:
        data_bytes = download_data_from_storage(
            object_name=obj['name'],
            bucket_name=bucket_name
        )
        
        # Parse JSON
        content = json.loads(data_bytes.decode('utf-8'))
        results.append(content)
    
    logger.info(f"Retrieved {len(results)} LLM generations for requirement {requirement_id}")
    return results


def generate_test_scenarios_from_requirement(
    requirement_id: str,
    model_name: str = "llama",
    num_scenarios: int = 5,
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate test scenarios from a requirement using watsonx.ai.
    
    Args:
        requirement_id: ID of the requirement
        model_name: LLM model to use
        num_scenarios: Number of scenarios to generate
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    # Get requirement details
    try:
        requirement = get_requirement_by_id(requirement_id)
    except ValueError as e:
        logger.error(f"Failed to get requirement {requirement_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Requirement not found: {str(e)}"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test scenario generator expert. Based on the following requirement, 
        generate {num_scenarios} distinct test scenarios. For each scenario, include:
        
        1. A descriptive name
        2. A detailed description
        3. Preconditions
        4. Steps to execute
        5. Expected results
        6. Priority (High, Medium, Low)
        
        Requirement:
        Title: {title}
        Description: {description}
        
        Generate varied scenarios that cover different aspects of the requirement,
        including positive tests, negative tests, boundary conditions, and edge cases.
        """
    
    # Format prompt
    prompt = prompt_template.format(
        num_scenarios=num_scenarios,
        title=requirement.get('title', f"Requirement {requirement_id}"),
        description=requirement.get('description', '')
    )
    
    try:
        # In a real implementation, this would call the watsonx.ai API
        # For this example, we'll simulate the response
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock response with generated scenarios
        scenarios = []
        for i in range(num_scenarios):
            scenario = {
                'name': f"Test Scenario {i+1} for {requirement_id}",
                'description': f"This scenario tests a specific aspect of the requirement {requirement_id}.",
                'preconditions': [
                    f"Precondition 1 for scenario {i+1}",
                    f"Precondition 2 for scenario {i+1}"
                ],
                'steps': [
                    f"Step 1: Perform action A for scenario {i+1}",
                    f"Step 2: Verify result B for scenario {i+1}",
                    f"Step 3: Perform action C for scenario {i+1}"
                ],
                'expected_results': [
                    f"Expected result 1 for scenario {i+1}",
                    f"Expected result 2 for scenario {i+1}"
                ],
                'priority': 'High' if i < 2 else 'Medium' if i < 4 else 'Low'
            }
            scenarios.append(scenario)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_id': requirement_id,
            'requirement_title': requirement.get('title', ''),
            'scenarios': scenarios,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=requirement_id,
            generated_content=result,
            model_name=model_name,
            content_type='test_scenarios'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {num_scenarios} test scenarios for requirement {requirement_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test scenarios: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def generate_test_cases_from_scenarios(
    scenarios: List[Dict[str, Any]],
    model_name: str = "llama",
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate detailed test cases from test scenarios using watsonx.ai.
    
    Args:
        scenarios: List of scenario dictionaries
        model_name: LLM model to use
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    if not scenarios:
        logger.error("No scenarios provided")
        return {
            'status': 'error',
            'error': "No scenarios provided"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test case generation expert. Based on the following test scenario,
        create a detailed test case with specific test steps, test data, and expected results.
        
        Test Scenario:
        Name: {name}
        Description: {description}
        Preconditions: {preconditions}
        Steps: {steps}
        Expected Results: {expected_results}
        Priority: {priority}
        
        Generate a test case that includes:
        1. Specific test data values to use
        2. Detailed step-by-step test procedure
        3. Specific expected results for each step
        4. Validation points
        5. Any notes or special considerations
        """
    
    test_cases = []
    requirement_ids = set()
    
    try:
        for i, scenario in enumerate(scenarios):
            # Extract requirement ID if available
            requirement_id = scenario.get('requirement_id', f"REQ_{int(time.time())}")
            requirement_ids.add(requirement_id)
            
            # Format scenario details for prompt
            scenario_details = {
                'name': scenario.get('name', f"Scenario {i+1}"),
                'description': scenario.get('description', ''),
                'preconditions': '\n'.join(scenario.get('preconditions', [])),
                'steps': '\n'.join(scenario.get('steps', [])),
                'expected_results': '\n'.join(scenario.get('expected_results', [])),
                'priority': scenario.get('priority', 'Medium')
            }
            
            # Format prompt for this scenario
            prompt = prompt_template.format(**scenario_details)
            
            # Simulate API call delay
            import time
            time.sleep(0.5)
            
            # Mock test case generation
            test_case = {
                'id': f"TC_{int(time.time())}_{i}",
                'name': f"Test Case for {scenario_details['name']}",
                'description': f"Detailed test case for {scenario_details['name']}",
                'requirement_id': requirement_id,
                'scenario_name': scenario_details['name'],
                'priority': scenario_details['priority'],
                'test_data': {
                    'input1': 'Sample input value 1',
                    'input2': 'Sample input value 2'
                },
                'steps': [
                    {
                        'number': 1,
                        'description': 'Perform specific action A with test data',
                        'expected_result': 'System should respond with X'
                    },
                    {
                        'number': 2,
                        'description': 'Verify specific condition B',
                        'expected_result': 'Condition B should be true'
                    },
                    {
                        'number': 3,
                        'description': 'Perform specific action C',
                        'expected_result': 'System should update with Y'
                    }
                ],
                'validation_points': [
                    'Validate that X appears correctly',
                    'Validate that Y contains the expected data'
                ],
                'notes': 'This test case covers the main positive flow'
            }
            
            test_cases.append(test_case)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_ids': list(requirement_ids),
            'test_cases': test_cases,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=list(requirement_ids)[0] if requirement_ids else "multiple",
            generated_content=result,
            model_name=model_name,
            content_type='test_cases'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {len(test_cases)} test cases from {len(scenarios)} scenarios")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test cases: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def analyze_test_failure(
    execution_id: str,
    model_name: str = "llama",
    include_similar_failures: bool = True
) -> Dict[str, Any]:
    """
    Analyze a test failure using watsonx.ai to determine potential causes and solutions.
    
    Args:
        execution_id: ID of the failed test execution
        model_name: LLM model to use
        include_similar_failures: Whether to include similar historical failures
        
    Returns:
        Dict: Analysis results and recommendations
    """
    # Get execution details
    try:
        execution = get_test_execution(execution_id)
    except ValueError as e:
        logger.error(f"Failed to get execution {execution_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Execution not found: {str(e)}"
        }
    
    # Check if execution is failed
    if execution.get('status', '').lower() != 'failed':
        logger.warning(f"Execution {execution_id} is not failed (status: {execution.get('status')})")
        return {
            'status': 'error',
            'error': f"Execution is not failed (status: {execution.get('status')})"
        }
    
    # Get test case details
    test_case_id = execution['metadata']['test_case_id']
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError:
        test_case = {'id': test_case_id}  # Minimal info if test case not found
    
    # Find the failed steps
    steps = execution.get('execution_steps', [])
    failed_steps = [step for step in steps if step.get('status', '').lower() == 'failed']
    
    if not failed_steps:
        logger.warning(f"No failed steps found in execution {execution_id}")
        return {
            'status': 'warning',
            'warning': "No failed steps found in execution",
            'execution_id': execution_id
        }
    
    # Get similar failures if requested
    similar_failures = []
    if include_similar_failures:
        # Query for similar failures
        query = """
        SELECT e.execution_id, e.test_case_id, e.status, e.executed_at
        FROM test_executions e
        WHERE e.test_case_id = %s 
        AND e.status = 'failed'
        AND e.execution_id != %s
        ORDER BY e.executed_at DESC
        LIMIT 5
        """
        
        similar_results = query_database(
            query=query,
            params=(test_case_id, execution_id)
        )
        
        for result in similar_results:
            try:
                similar_execution = get_test_execution(result['execution_id'])
                similar_failures.append(similar_execution)
            except ValueError:
                pass
    
    try:
        # Prepare analysis context
        analysis_context = {
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'execution_time': execution.get('execution_time', 0),
            'failed_steps': failed_steps,
            'similar_failures': len(similar_failures)
        }
        
        # Build prompt for watsonx.ai
        prompt = f"""
        Analyze the following test failure and provide potential causes and solutions.
        
        Test Case: {test_case.get('name', test_case_id)}
        Execution ID: {execution_id}
        
        Failed Steps:
        {json.dumps(failed_steps, indent=2)}
        
        Similar Failures: {len(similar_failures)} recent failures of this test case.
        
        Provide:
        1. Most likely causes of failure
        2. Recommended troubleshooting steps
        3. Potential fixes
        4. Is this likely a defect in the application or an issue with the test?
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock analysis results
        analysis_results = {
            'potential_causes': [
                {
                    'description': 'Data inconsistency in test environment',
                    'probability': 'High',
                    'explanation': 'The error message indicates a mismatch between expected and actual data values'
                },
                {
                    'description': 'Timing issue - operation not completed before verification',
                    'probability': 'Medium',
                    'explanation': 'The failure occurs during a verification step that may be executing too soon'
                },
                {
                    'description': 'Application defect in data processing logic',
                    'probability': 'Medium',
                    'explanation': 'The specific error pattern matches known issues in the data processing component'
                }
            ],
            'troubleshooting_steps': [
                'Verify test data is consistent with current environment state',
                'Add appropriate wait condition before verification step',
                'Review application logs for exceptions around the time of failure',
                'Compare with previous successful executions to identify changes'
            ],
            'potential_fixes': [
                {
                    'type': 'Test Update',
                    'description': 'Introduce a wait mechanism before verification',
                    'difficulty': 'Low'
                },
                {
                    'type': 'Environment Fix',
                    'description': 'Refresh test data to ensure consistency',
                    'difficulty': 'Medium'
                },
                {
                    'type': 'Application Fix',
                    'description': 'Review and correct data processing logic in the application',
                    'difficulty': 'High'
                }
            ],
            'defect_assessment': {
                'likely_application_defect': True,
                'confidence': 70,
                'explanation': 'Based on the error patterns and similar failures, there is a 70% probability this is an application defect rather than a test issue.'
            }
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'analysis_context': analysis_context,
            'analysis_results': analysis_results,
            'similar_failure_count': len(similar_failures),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='failure_analysis'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Completed failure analysis for execution {execution_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze test failure: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def suggest_test_case_improvements(
    test_case_id: str,
    model_name: str = "llama"
) -> Dict[str, Any]:
    """
    Use watsonx.ai to suggest improvements for an existing test case.
    
    Args:
        test_case_id: ID of the test case to improve
        model_name: LLM model to use
        
    Returns:
        Dict: Improvement suggestions and metadata
    """
    # Get test case details
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError as e:
        logger.error(f"Failed to get test case {test_case_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Test case not found: {str(e)}"
        }
    
    # Get test execution history
    query = """
    SELECT status, COUNT(*) as count
    FROM test_executions
    WHERE test_case_id = %s
    GROUP BY status
    """
    
    execution_stats = query_database(query, (test_case_id,))
    execution_history = {row['status']: row['count'] for row in execution_stats}
    
    # Get defects associated with this test case
    defects = get_defects(test_case_id=test_case_id)
    
    try:
        # Build prompt for watsonx.ai
        prompt = f"""
        Review the following test case and suggest improvements to make it more robust and effective.
        
        Test Case: {test_case.get('name', test_case_id)}
        Description: {test_case.get('description', '')}
        
        Current Test Steps:
        {json.dumps(test_case.get('steps', []), indent=2)}
        
        Execution History:
        {json.dumps(execution_history, indent=2)}
        
        Associated Defects: {len(defects)}
        
        Provide:
        1. Overall assessment of the test case
        2. Specific improvement suggestions
        3. Additional test scenarios that should be covered
        4. Recommendations for better test data
        5. Any validation points that should be added
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock improvement suggestions
        improvement_suggestions = {
            'overall_assessment': {
                'quality_score': 7,  # 1-10 scale
                'strengths': [
                    'Good coverage of main functionality',
                    'Clear step descriptions'
                ],
                'weaknesses': [
                    'Limited validation points',
                    'Missing boundary condition tests',
                    'No negative test scenarios'
                ]
            },
            'specific_improvements': [
                {
                    'step_index': 2,
                    'current': test_case.get('steps', [])[2] if len(test_case.get('steps', [])) > 2 else {},
                    'suggestion': 'Add specific validation for the returned data format',
                    'rationale': 'Current step only verifies presence but not structure'
                },
                {
                    'type': 'Add Step',
                    'suggestion': 'Add verification step after data submission',
                    'rationale': 'Should verify successful data processing before proceeding'
                },
                {
                    'type': 'Modify Test Data',
                    'suggestion': 'Use more diverse test data including boundary values',
                    'rationale': 'Current test data only covers happy path'
                }
            ],
            'additional_scenarios': [
                {
                    'name': 'Negative Test - Invalid Input',
                    'description': 'Test behavior when invalid data is provided',
                    'steps': [
                        'Attempt to submit invalid data format',
                        'Verify appropriate error message is displayed',
                        'Verify no data corruption occurs'
                    ]
                },
                {
                    'name': 'Boundary Test - Maximum Values',
                    'description': 'Test behavior with maximum allowed values',
                    'steps': [
                        'Submit form with maximum length strings',
                        'Verify data is accepted and processed correctly',
                        'Verify display handles long values appropriately'
                    ]
                }
            ],
            'test_data_recommendations': [
                'Include null values for optional fields',
                'Add test case with maximum length strings',
                'Include special characters in text fields',
                'Test with minimum and maximum numeric values'
            ],
            'validation_points': [
                'Verify response times are within acceptable limits',
                'Check both UI updates and backend data consistency',
                'Validate error message content for clarity and correctness',
                'Ensure no unnecessary database queries are triggered'
            ]
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'improvement_suggestions': improvement_suggestions,
            'execution_history': execution_history,
            'defect_count': len(defects),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='test_improvement'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated improvement suggestions for test case {test_case_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test case improvements: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def create_database_backup(
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> str:
    """
    Create a backup of database tables in JSON format.
    
    Args:
        bucket_name: Name of the bucket
        tables: List of tables to backup (default: all tables)
        
    Returns:
        str: Object name of the backup file
    """
    if not tables:
        # Get all tables
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
        results = query_database(query)
        tables = [row['table_name'] for row in results]
    
    backup_data = {}
    
    for table in tables:
        query = f"SELECT * FROM {table};"
        results = query_database(query)
        
        # Convert datetime objects to ISO format
        for row in results:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
        
        backup_data[table] = results
    
    # Create backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"database_backup_{timestamp}.json"
    
    json_data = json.dumps(backup_data, indent=2)
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=backup_file_name,
        bucket_name=bucket_name,
        metadata={
            'content-type': 'application/json',
            'source': 'watsonx-ipg-testing',
            'type': 'database-backup',
            'tables': ','.join(tables)
        },
        content_type='application/json'
    )
    
    logger.info(f"Created database backup of {len(tables)} tables as {backup_file_name}")
    return backup_file_name


def restore_database_from_backup(
    backup_file_name: str,
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> Dict[str, Any]:
    """
    Restore database tables from a backup file.
    
    Args:
        backup_file_name: Name of the backup file
        bucket_name: Name of the bucket
        tables: Optional list of specific tables to restore
        
    Returns:
        Dict: Restoration status and details
    """
    try:
        # Download backup file
        data_bytes = download_data_from_storage(
            object_name=backup_file_name,
            bucket_name=bucket_name
        )
        
        # Parse JSON
        backup_data = json.loads(data_bytes.decode('utf-8'))
        
        # Determine which tables to restore
        tables_to_restore = tables or list(backup_data.keys())
        
        # Verify tables exist in backup
        missing_tables = [table for table in tables_to_restore if table not in backup_data]
        if missing_tables:
            logger.error(f"Tables not found in backup: {', '.join(missing_tables)}")
            return {
                'status': 'error',
                'error': f"Tables not found in backup: {', '.join(missing_tables)}"
            }
        
        # Restore each table
        restoration_results = {}
        for table in tables_to_restore:
            try:
                # Delete existing data
                delete_query = f"DELETE FROM {table};"
                update_database(delete_query)
                
                # Insert backup data
                rows = backup_data[table]
                if not rows:
                    restoration_results[table] = {
                        'status': 'success',
                        'rows_restored': 0
                    }
                    continue
                
                # Build insert query
                columns = list(rows[0].keys())
                placeholders = ", ".join(["%s"] * len(columns))
                column_list = ", ".join(columns)
                
                insert_query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                
                # Prepare params for batch insert
                params_list = []
                for row in rows:
                    # Ensure row values are in the same order as columns
                    row_values = [row[col] for col in columns]
                    params_list.append(row_values)
                
                # Perform batch insert
                affected_rows = batch_update_database(
                    query=insert_query,
                    params_list=params_list
                )
                
                restoration_results[table] = {
                    'status': 'success',
                    'rows_restored': affected_rows
                }
                
            except Exception as e:
                logger.error(f"Failed to restore table {table}: {str(e)}")
                restoration_results[table] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check overall status
        success_count = sum(1 for result in restoration_results.values() if result['status'] == 'success')
        
        logger.info(f"Restored {success_count} of {len(tables_to_restore)} tables from backup {backup_file_name}")
        return {
            'status': 'success' if success_count == len(tables_to_restore) else 'partial',
            'tables_restored': success_count,
            'total_tables': len(tables_to_restore),
            'details': restoration_results
        }
        
    except Exception as e:
        logger.error(f"Failed to restore from backup {backup_file_name}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Restoration failed: {str(e)}"
        }str(e)}"
        }


def cleanup_old_data(
    retention_days: int = 90,
    data_types: List[str] = None
) -> Dict[str, int]:
    """
    Clean up old data based on retention policy.
    
    Args:
        retention_days: Number of days to retain data
        data_types: Types of data to clean up (default: all)
        
    Returns:
        Dict: Number of records deleted by type
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deletion_counts = {}
    
    # Define data types and their cleanup queries
    cleanup_queries = {
        'test_executions': """
            DELETE FROM test_executions
            WHERE executed_at < %s
            """,
        'defects': """
            DELETE FROM defects
            WHERE status = 'closed'
            AND updated_at < %s
            """,
        'sharepoint_documents': """
            DELETE FROM sharepoint_documents
            WHERE sync_status = 'synced'
            AND created_at < %s
            """,
        'blueprism_jobs': """
            DELETE FROM blueprism_jobs
            WHERE completed_at < %s
            """,
        'uft_jobs': """
            DELETE FROM uft_jobs
            WHERE completed_at < %s
            """
    }
    
    # Determine which data types to clean up
    types_to_clean = data_types or list(cleanup_queries.keys())
    
    # Execute cleanup for each type
    for data_type in types_to_clean:
        if data_type in cleanup_queries:
            query = cleanup_queries[data_type]
            try:
                affected_rows = update_database(
                    query=query,
                    params=(cutoff_date,)
                )
                deletion_counts[data_type] = affected_rows
                logger.info(f"Deleted {affected_rows} old records from {data_type}")
            except Exception as e:
                logger.error(f"Failed to clean up {data_type}: {str(e)}")
                deletion_counts[data_type] = 0
    
    # Cleanup old files in object storage
    try:
        prefix = ""  # Clean up all prefixes
        objects = list_storage_objects(prefix=prefix)
        
        deleted_objects = 0
        for obj in objects:
            # Skip recent objects
            if datetime.now() - obj['last_modified'] < timedelta(days=retention_days):
                continue
            
            # Skip backup files and important artifacts
            if 'backup' in obj['name'] or 'archive' in obj['name']:
                continue
            
            # Delete old object
            try:
                delete_from_storage(obj['name'])
                deleted_objects += 1
            except:
                pass
        
        deletion_counts['object_storage'] = deleted_objects
        logger.info(f"Deleted {deleted_objects} old objects from storage")
    except Exception as e:
        logger.error(f"Failed to clean up object storage: {str(e)}")
        deletion_counts['object_storage'] = 0
    
    return deletion_counts


# ------------- Cache Management -------------

_cache = {}  # Simple in-memory cache

def cache_result(key: str, value: Any, ttl_seconds: int = 300):
    """
    Cache a result in memory.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl_seconds: Time to live in seconds
    """
    expiry = time.time() + ttl_seconds
    _cache[key] = (value, expiry)


def get_cached_result(key: str) -> Optional[Any]:
    """
    Get a result from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Optional[Any]: Cached value or None if expired/not found
    """
    if key in _cache:
        value, expiry = _cache[key]
        if time.time() < expiry:
            return value
        
        # Expired
        del _cache[key]
    
    return None


def clear_cache():
    """Clear the entire cache."""
    _cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the cache.
    
    Returns:
        Dict: Cache statistics
    """
    now = time.time()
    total_items = len(_cache)
    expired_items = sum(1 for _, expiry in _cache.values() if now >= expiry)
    valid_items = total_items - expired_items
    
    # Calculate memory usage (approximate)
    import sys
    memory_usage = sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in _cache.items())
    
    return {
        'total_items': total_items,
        'valid_items': valid_items,
        'expired_items': expired_items,
        'memory_usage_bytes': memory_usage
    }


# ------------- Health Check Functions -------------

def perform_health_check() -> Dict[str, Any]:
    """
    Perform a health check on all database components.
    
    Returns:
        Dict: Health status for each component
    """
    health = {
        'database': is_database_healthy(),
        'object_storage': is_storage_healthy(),
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Check table existence and row counts
    tables = [
        'test_cases', 'test_executions', 'defects', 'test_data',
        'integration_credentials', 'sharepoint_documents', 'blueprism_jobs'
    ]
    
    for table in tables:
        try:
            exists = table_exists(table)
            
            if exists:
                count_query = f"SELECT COUNT(*) as count FROM {table};"
                count_result = query_database(count_query, fetch_one=True)
                row_count = count_result['count'] if count_result else 0
            else:
                row_count = 0
            
            health['components'][table] = {
                'exists': exists,
                'row_count': row_count,
                'status': 'healthy' if exists else 'missing'
            }
        except Exception as e:
            health['components'][table] = {
                'exists': False,
                'status': 'error',
                'error': str(e)
            }
    
    # Check connection to integration systems
    integration_systems = [
        'jira', 'sharepoint', 'alm', 'blueprism', 'uft'
    ]
    
    for system in integration_systems:
        try:
            # Check if credentials exist
            has_credentials = False
            try:
                get_integration_credentials(system, decrypt=False)
                has_credentials = True
            except ValueError:
                pass
            
            health['components'][f"{system}_integration"] = {
                'credentials_exist': has_credentials,
                'status': 'configured' if has_credentials else 'not_configured'
            }
        except Exception as e:
            health['components'][f"{system}_integration"] = {
                'status': 'error',
                'error': str(e)
            }
    
    # Overall status
    critical_components = ['database', 'object_storage']
    critical_status = all(health[component] for component in critical_components)
    health['overall_status'] = 'healthy' if critical_status else 'degraded'
    
    logger.info(f"Health check completed: {health['overall_status']}")
    return health


def analyze_database_performance() -> Dict[str, Any]:
    """
    Analyze database performance metrics.
    
    Returns:
        Dict: Performance analysis results
    """
    try:
        # Query for database statistics
        stats_queries = {
            'table_stats': """
                SELECT 
                    relname as table_name, 
                    n_live_tup as row_count,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_analyze
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """,
            'index_stats': """
                SELECT
                    indexrelname as index_name,
                    relname as table_name,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
            """,
            'table_io_stats': """
                SELECT
                    relname as table_name,
                    heap_blks_read as disk_reads,
                    heap_blks_hit as cache_hits,
                    CASE WHEN heap_blks_read + heap_blks_hit > 0 
                        THEN heap_blks_hit::float / (heap_blks_read + heap_blks_hit) * 100
                        ELSE 0 
                    END as cache_hit_ratio
                FROM pg_statio_user_tables
                ORDER BY heap_blks_read + heap_blks_hit DESC
            """
        }
        
        # Execute queries
        stats_results = {}
        for key, query in stats_queries.items():
            stats_results[key] = query_database(query)
        
        # Calculate overall statistics
        total_rows = sum(table['row_count'] for table in stats_results['table_stats'])
        total_dead_rows = sum(table['dead_rows'] for table in stats_results['table_stats'])
        dead_row_ratio = (total_dead_rows / total_rows * 100) if total_rows > 0 else 0
        
        total_disk_reads = sum(table['disk_reads'] for table in stats_results['table_io_stats'])
        total_cache_hits = sum(table['cache_hits'] for table in stats_results['table_io_stats'])
        overall_cache_hit_ratio = (total_cache_hits / (total_disk_reads + total_cache_hits) * 100) if (total_disk_reads + total_cache_hits) > 0 else 0
        
        # Identify tables that might need vacuuming (high dead row ratio)
        vacuum_candidates = [
            {
                'table_name': table['table_name'],
                'dead_rows': table['dead_rows'],
                'row_count': table['row_count'],
                'dead_row_ratio': (table['dead_rows'] / table['row_count'] * 100) if table['row_count'] > 0 else 0,
                'last_vacuum': table['last_vacuum'].isoformat() if table['last_vacuum'] else None
            }
            for table in stats_results['table_stats']
            if table['row_count'] > 0 and (table['dead_rows'] / table['row_count']) >= 0.2  # 20% or more dead rows
        ]
        
        # Identify unused indexes
        unused_indexes = [
            {
                'index_name': index['index_name'],
                'table_name': index['table_name'],
                'index_scans': index['index_scans']
            }
            for index in stats_results['index_stats']
            if index['index_scans'] == 0
        ]
        
        # Identify tables with low cache hit ratio
        low_cache_hit_tables = [
            {
                'table_name': table['table_name'],
                'disk_reads': table['disk_reads'],
                'cache_hits': table['cache_hits'],
                'cache_hit_ratio': table['cache_hit_ratio']
            }
            for table in stats_results['table_io_stats']
            if table['cache_hit_ratio'] < 90 and (table['disk_reads'] + table['cache_hits']) > 100  # Less than 90% cache hits and significant I/O
        ]
        
        # Prepare recommendations
        recommendations = []
        
        if vacuum_candidates:
            recommendations.append({
                'type': 'vacuum',
                'message': f"Consider running VACUUM on {len(vacuum_candidates)} tables with high dead row ratios",
                'tables': [table['table_name'] for table in vacuum_candidates]
            })
        
        if unused_indexes:
            recommendations.append({
                'type': 'unused_indexes',
                'message': f"Consider removing {len(unused_indexes)} unused indexes to improve write performance",
                'indexes': [f"{index['table_name']}.{index['index_name']}" for index in unused_indexes]
            })
        
        if low_cache_hit_tables:
            recommendations.append({
                'type': 'cache_optimization',
                'message': f"{len(low_cache_hit_tables)} tables have low cache hit ratios, consider increasing shared_buffers",
                'tables': [table['table_name'] for table in low_cache_hit_tables]
            })
        
        # Final analysis result
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tables': len(stats_results['table_stats']),
                'total_indexes': len(stats_results['index_stats']),
                'total_rows': total_rows,
                'dead_row_ratio': dead_row_ratio,
                'overall_cache_hit_ratio': overall_cache_hit_ratio
            },
            'top_tables_by_size': stats_results['table_stats'][:5],
            'vacuum_candidates': vacuum_candidates,
            'unused_indexes': unused_indexes,
            'low_cache_hit_tables': low_cache_hit_tables,
            'recommendations': recommendations
        }
        
        logger.info(f"Database performance analysis completed with {len(recommendations)} recommendations")
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze database performance: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def optimize_database() -> Dict[str, Any]:
    """
    Perform database optimization operations.
    
    Returns:
        Dict: Optimization results
    """
    try:
        # Analyze tables
        analyze_query = "ANALYZE;"
        update_database(analyze_query)
        
        # Get tables that need vacuuming
        vacuum_query = """
        SELECT 
            relname as table_name,
            n_dead_tup as dead_rows,
            n_live_tup as row_count,
            CASE WHEN n_live_tup > 0 
                THEN n_dead_tup::float / n_live_tup 
                ELSE 0 
            END as dead_ratio
        FROM pg_stat_user_tables
        WHERE n_live_tup > 0
        AND n_dead_tup > 0
        AND (n_dead_tup::float / n_live_tup) >= 0.2
        ORDER BY dead_ratio DESC
        """
        
        vacuum_candidates = query_database(vacuum_query)
        
        # Vacuum each table
        vacuum_results = []
        for table in vacuum_candidates:
            table_name = table['table_name']
            try:
                vacuum_table_query = f"VACUUM ANALYZE {table_name};"
                update_database(vacuum_table_query)
                vacuum_results.append({
                    'table_name': table_name,
                    'status': 'success',
                    'dead_rows_before': table['dead_rows']
                })
                logger.info(f"Vacuumed table {table_name} with {table['dead_rows']} dead rows")
            except Exception as e:
                vacuum_results.append({
                    'table_name': table_name,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Failed to vacuum table {table_name}: {str(e)}")
        
        # Get unused indexes
        unused_index_query = """
        SELECT
            indexrelname as index_name,
            relname as table_name,
            idx_scan as index_scans
        FROM pg_stat_user_indexes
        WHERE idx_scan = 0
        AND indexrelname NOT IN (
            SELECT indexrelname
            FROM pg_constraint c
            JOIN pg_index i ON c.conindid = i.indexrelid
            JOIN pg_stat_user_indexes s ON s.indexrelid = i.indexrelid
            WHERE c.contype = 'p'
        )
        ORDER BY pg_relation_size(indexrelid) DESC
        """
        
        unused_indexes = query_database(unused_index_query)
        
        # Don't automatically drop indexes, just report them
        
        # Reindex important tables
        important_tables = [
            'test_cases', 'test_executions', 'defects'
        ]
        
        reindex_results = []
        for table in important_tables:
            try:
                if table_exists(table):
                    reindex_query = f"REINDEX TABLE {table};"
                    update_database(reindex_query)
                    reindex_results.append({
                        'table_name': table,
                        'status': 'success'
                    })
                    logger.info(f"Reindexed table {table}")
                else:
                    reindex_results.append({
                        'table_name': table,
                        'status': 'skipped',
                        'reason': 'table does not exist'
                    })
            except Exception as e:
                reindex_results.append({
                    'table_name': table,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"Failed to reindex table {table}: {str(e)}")
        
        # Final optimization result
        result = {
            'timestamp': datetime.now().isoformat(),
            'tables_vacuumed': len([r for r in vacuum_results if r['status'] == 'success']),
            'tables_reindexed': len([r for r in reindex_results if r['status'] == 'success']),
            'unused_indexes_found': len(unused_indexes),
            'vacuum_results': vacuum_results,
            'reindex_results': reindex_results,
            'unused_indexes': unused_indexes
        }
        
        logger.info(f"Database optimization completed: {result['tables_vacuumed']} tables vacuumed, {result['tables_reindexed']} tables reindexed")
        return result
        
    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        return {
            'status': 'error',
            'error': f"Optimization failed: {str(e)}"
        }


def validate_database_schema() -> Dict[str, Any]:
    """
    Validate the database schema against the expected schema.
    
    Returns:
        Dict: Validation results
    """
    # Define expected tables and their required columns
    expected_schema = {
        'test_cases': [
            'id', 'name', 'description', 'version', 'storage_path', 
            'format', 'status', 'created_at', 'updated_at'
        ],
        'test_executions': [
            'execution_id', 'test_case_id', 'status', 'result_path', 
            'execution_time', 'screenshots', 'executed_at', 'notes'
        ],
        'defects': [
            'id', 'test_case_id', 'execution_id', 'defect_id', 
            'summary', 'description', 'severity', 'assigned_to', 
            'status', 'resolution', 'created_at', 'updated_at'
        ],
        'test_data': [
            'id', 'test_case_id', 'data_type', 'storage_path', 
            'created_at', 'updated_at'
        ],
        'integration_credentials': [
            'id', 'system_type', 'credentials', 'encrypted', 
            'created_at', 'updated_at'
        ],
        'sharepoint_documents': [
            'id', 'file_name', 'storage_path', 'content_type', 
            'sync_status', 'created_at', 'synced_at'
        ],
        'blueprism_jobs': [
            'id', 'job_id', 'test_case_id', 'controller_file', 
            'status', 'started_at', 'completed_at', 'result'
        ],
        'execution_metrics': [
            'id', 'execution_id', 'test_case_id', 'start_time', 
            'end_time', 'duration', 'status', 'environment'
        ]
    }
    
    validation_results = {}
    missing_tables = []
    schema_issues = []
    
    # Check each expected table
    for table, expected_columns in expected_schema.items():
        if not table_exists(table):
            missing_tables.append(table)
            validation_results[table] = {
                'exists': False,
                'status': 'missing'
            }
            continue
        
        # Get actual columns
        actual_columns = get_column_info(table)
        actual_column_names = [col['column_name'] for col in actual_columns]
        
        # Check for missing columns
        missing_columns = [col for col in expected_columns if col not in actual_column_names]
        
        if missing_columns:
            schema_issues.append({
                'table': table,
                'issue': 'missing_columns',
                'columns': missing_columns
            })
            validation_results[table] = {
                'exists': True,
                'status': 'incomplete',
                'missing_columns': missing_columns
            }
        else:
            validation_results[table] = {
                'exists': True,
                'status': 'valid',
                'columns': len(actual_columns)
            }
    
    # Overall validation result
    status = 'valid'
    if missing_tables:
        status = 'missing_tables'
    elif schema_issues:
        status = 'schema_issues'
    
    result = {
        'status': status,
        'missing_tables': missing_tables,
        'schema_issues': schema_issues,
        'tables_validated': len(validation_results),
        'valid_tables': len([r for r in validation_results.values() if r['status'] == 'valid']),
        'details': validation_results
    }
    
    logger.info(f"Database schema validation completed: {result['status']}")
    return result


def upgrade_database_schema(
    version: str = None
) -> Dict[str, Any]:
    """
    Upgrade the database schema to a specified version.
    
    Args:
        version: Target schema version (default: latest)
        
    Returns:
        Dict: Upgrade results
    """
    # Check current schema version
    current_version = "0.0.0"
    try:
        version_query = "SELECT value FROM system_config WHERE key = 'schema_version';"
        version_result = query_database(version_query, fetch_one=True)
        if version_result:
            final_version = version_result['value']
    except:
        pass
    
    # Determine overall status
    successful_upgrades = [r for r in results if r['status'] == 'success']
    all_success = len(successful_upgrades) == len(versions_to_apply)
    
    result = {
        'status': 'success' if all_success else 'partial',
        'initial_version': current_version,
        'target_version': target_version,
        'final_version': final_version,
        'versions_applied': len(successful_upgrades),
        'total_versions': len(versions_to_apply),
        'details': results
    }
    
    logger.info(f"Database schema upgrade from {current_version} to {final_version} completed with status {result['status']}")
    return result


def analyze_system_health() -> Dict[str, Any]:
    """
    Perform a comprehensive system health analysis.
    
    Returns:
        Dict: System health analysis and recommendations
    """
    # Collect health information from various components
    health_results = {
        'database': perform_health_check(),
        'db_performance': analyze_database_performance(),
        'schema': validate_database_schema(),
        'cache': get_cache_stats(),
        'timestamp': datetime.now().isoformat()
    }
    
    # Determine system status
    if not health_results['database']['database']:
        status = 'critical'
        primary_issue = 'Database connection failure'
    elif not health_results['database']['object_storage']:
        status = 'critical'
        primary_issue = 'Object storage connection failure'
    elif health_results['schema']['status'] != 'valid':
        status = 'warning'
        primary_issue = 'Database schema issues detected'
    elif health_results['db_performance'].get('error'):
        status = 'warning'
        primary_issue = 'Unable to analyze database performance'
    elif len(health_results['db_performance'].get('recommendations', [])) > 0:
        status = 'needs_optimization'
        primary_issue = 'Database optimization recommended'
    else:
        status = 'healthy'
        primary_issue = None
    
    # Compile recommendations
    recommendations = []
    
    # Add database performance recommendations
    if 'recommendations' in health_results['db_performance']:
        for rec in health_results['db_performance']['recommendations']:
            recommendations.append({
                'category': 'database',
                'priority': 'medium',
                'message': rec['message'],
                'details': rec
            })
    
    # Add schema recommendations
    if health_results['schema']['status'] == 'missing_tables':
        recommendations.append({
            'category': 'schema',
            'priority': 'high',
            'message': f"Missing tables: {', '.join(health_results['schema']['missing_tables'])}",
            'action': 'Run database initialization or schema upgrade'
        })
    elif health_results['schema']['status'] == 'schema_issues':
        recommendations.append({
            'category': 'schema',
            'priority': 'medium',
            'message': f"Schema issues detected in {len(health_results['schema']['schema_issues'])} tables",
            'action': 'Run schema upgrade to fix missing columns'
        })
    
    # Add overall system health result
    result = {
        'status': status,
        'primary_issue': primary_issue,
        'timestamp': datetime.now().isoformat(),
        'recommendations': recommendations,
        'components': {
            'database': health_results['database']['overall_status'],
            'schema': health_results['schema']['status'],
            'performance': 'issue' if len(health_results['db_performance'].get('recommendations', [])) > 0 else 'good'
        },
        'details': health_results
    }
    
    logger.info(f"System health analysis completed: {status}")
    return result

# End of Part 8: AI/LLM & Advanced Features
        if version_result:
            current_version = version_result['value']
    except:
        # Table might not exist yet
        pass
    
    # Define schema upgrades with version numbers
    schema_upgrades = {
        "1.0.0": [
            # Initial schema creation
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """,
            """
            INSERT INTO system_config (key, value, updated_at)
            VALUES ('schema_version', '1.0.0', NOW())
            ON CONFLICT (key) DO UPDATE SET value = '1.0.0', updated_at = NOW()
            """
        ],
        "1.1.0": [
            # Add new fields to test_cases
            """
            ALTER TABLE test_cases
            ADD COLUMN IF NOT EXISTS priority VARCHAR(20)
            """,
            """
            ALTER TABLE test_cases
            ADD COLUMN IF NOT EXISTS estimated_duration INTEGER
            """,
            """
            UPDATE system_config SET value = '1.1.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ],
        "1.2.0": [
            # Add test_scenarios table
            """
            CREATE TABLE IF NOT EXISTS test_scenarios (
                id SERIAL PRIMARY KEY,
                requirement_id VARCHAR(255) NOT NULL,
                scenario_name VARCHAR(255) NOT NULL,
                description TEXT,
                generated_by VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                test_case_ids JSONB,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP
            )
            """,
            """
            UPDATE system_config SET value = '1.2.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ],
        "1.3.0": [
            # Add indexes for better performance
            """
            CREATE INDEX IF NOT EXISTS idx_test_executions_test_case_id
            ON test_executions(test_case_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_defects_test_case_id
            ON defects(test_case_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_test_cases_status
            ON test_cases(status)
            """,
            """
            UPDATE system_config SET value = '1.3.0', updated_at = NOW()
            WHERE key = 'schema_version'
            """
        ]
    }
    
    # Determine target version
    if not version:
        available_versions = sorted(list(schema_upgrades.keys()))
        if not available_versions:
            return {
                'status': 'no_upgrades',
                'current_version': current_version
            }
        target_version = available_versions[-1]  # Latest version
    else:
        if version not in schema_upgrades:
            return {
                'status': 'error',
                'error': f"Unknown version: {version}",
                'available_versions': list(schema_upgrades.keys())
            }
        target_version = version
    
    # Check if upgrade is needed
    from packaging import version as pkg_version
    if pkg_version.parse(current_version) >= pkg_version.parse(target_version):
        return {
            'status': 'already_current',
            'current_version': current_version,
            'target_version': target_version
        }
    
    # Sort versions for sequential upgrade
    versions_to_apply = [v for v in sorted(schema_upgrades.keys()) 
                        if pkg_version.parse(v) > pkg_version.parse(current_version)
                        and pkg_version.parse(v) <= pkg_version.parse(target_version)]
    
    # Apply upgrades in sequence
    results = []
    for upgrade_version in versions_to_apply:
        version_result = {
            'version': upgrade_version,
            'status': 'pending',
            'queries': []
        }
        
        try:
            # Execute each upgrade query
            for i, query in enumerate(schema_upgrades[upgrade_version]):
                try:
                    update_database(query)
                    version_result['queries'].append({
                        'index': i,
                        'status': 'success'
                    })
                except Exception as e:
                    version_result['queries'].append({
                        'index': i,
                        'status': 'error',
                        'error': str(e)
                    })
                    raise
            
            version_result['status'] = 'success'
            
        except Exception as e:
            version_result['status'] = 'error'
            version_result['error'] = str(e)
            results.append(version_result)
            break
        
        results.append(version_result)
    
    # Get final schema version
    final_version = current_version
    try:
        version_query = "SELECT value FROM system_config WHERE key = 'schema_version';"
        version_result = query_database(version_query, fetch_one=True)# ------------- Part 8: AI/LLM & Advanced Features -------------

def store_llm_generation_result(
    requirement_id: str,
    generated_content: Dict[str, Any],
    model_name: str = "llama",
    content_type: str = "test_scenarios",
    bucket_name: str = DEFAULT_BUCKET
) -> str:
    """
    Store LLM-generated content in object storage.
    
    Args:
        requirement_id: ID of the requirement that triggered generation
        generated_content: Dictionary containing generated content
        model_name: Name of the LLM model used
        content_type: Type of content ('test_scenarios', 'test_cases', 'analysis')
        bucket_name: Name of the bucket
        
    Returns:
        str: Object name of the stored result
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"llm_{content_type}_{requirement_id}_{timestamp}.json"
    
    # Add metadata
    generated_content['metadata'] = {
        'requirement_id': requirement_id,
        'model_name': model_name,
        'content_type': content_type,
        'generated_at': datetime.now().isoformat()
    }
    
    # Convert to JSON
    json_data = json.dumps(generated_content, indent=2)
    
    # Store in object storage
    metadata = {
        'content-type': 'application/json',
        'source': 'watsonx-ipg-testing',
        'type': 'llm-generation',
        'model-name': model_name,
        'content-type': content_type,
        'requirement-id': requirement_id
    }
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=file_name,
        bucket_name=bucket_name,
        metadata=metadata,
        content_type='application/json'
    )
    
    # Record in database if it's a test scenario
    if content_type == "test_scenarios":
        # For each scenario in the generated content
        for scenario in generated_content.get('scenarios', []):
            query = """
            INSERT INTO test_scenarios
            (requirement_id, scenario_name, description, generated_by, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            update_database(
                query=query,
                params=(
                    requirement_id,
                    scenario.get('name', f"Scenario for {requirement_id}"),
                    scenario.get('description', ''),
                    f"watsonx-{model_name}",
                    'draft',
                    datetime.now()
                )
            )
    
    logger.info(f"Stored LLM generation result for requirement {requirement_id} as {file_name}")
    return file_name


def get_llm_generations_by_requirement(
    requirement_id: str,
    content_type: str = None,
    bucket_name: str = DEFAULT_BUCKET
) -> List[Dict[str, Any]]:
    """
    Retrieve LLM-generated content for a requirement.
    
    Args:
        requirement_id: ID of the requirement
        content_type: Optional content type filter
        bucket_name: Name of the bucket
        
    Returns:
        List[Dict]: List of generated content
    """
    prefix = f"llm_"
    if content_type:
        prefix += f"{content_type}_"
    prefix += f"{requirement_id}_"
    
    objects = list_storage_objects(
        prefix=prefix,
        bucket_name=bucket_name
    )
    
    results = []
    for obj in objects:
        data_bytes = download_data_from_storage(
            object_name=obj['name'],
            bucket_name=bucket_name
        )
        
        # Parse JSON
        content = json.loads(data_bytes.decode('utf-8'))
        results.append(content)
    
    logger.info(f"Retrieved {len(results)} LLM generations for requirement {requirement_id}")
    return results


def generate_test_scenarios_from_requirement(
    requirement_id: str,
    model_name: str = "llama",
    num_scenarios: int = 5,
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate test scenarios from a requirement using watsonx.ai.
    
    Args:
        requirement_id: ID of the requirement
        model_name: LLM model to use
        num_scenarios: Number of scenarios to generate
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    # Get requirement details
    try:
        requirement = get_requirement_by_id(requirement_id)
    except ValueError as e:
        logger.error(f"Failed to get requirement {requirement_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Requirement not found: {str(e)}"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test scenario generator expert. Based on the following requirement, 
        generate {num_scenarios} distinct test scenarios. For each scenario, include:
        
        1. A descriptive name
        2. A detailed description
        3. Preconditions
        4. Steps to execute
        5. Expected results
        6. Priority (High, Medium, Low)
        
        Requirement:
        Title: {title}
        Description: {description}
        
        Generate varied scenarios that cover different aspects of the requirement,
        including positive tests, negative tests, boundary conditions, and edge cases.
        """
    
    # Format prompt
    prompt = prompt_template.format(
        num_scenarios=num_scenarios,
        title=requirement.get('title', f"Requirement {requirement_id}"),
        description=requirement.get('description', '')
    )
    
    try:
        # In a real implementation, this would call the watsonx.ai API
        # For this example, we'll simulate the response
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock response with generated scenarios
        scenarios = []
        for i in range(num_scenarios):
            scenario = {
                'name': f"Test Scenario {i+1} for {requirement_id}",
                'description': f"This scenario tests a specific aspect of the requirement {requirement_id}.",
                'preconditions': [
                    f"Precondition 1 for scenario {i+1}",
                    f"Precondition 2 for scenario {i+1}"
                ],
                'steps': [
                    f"Step 1: Perform action A for scenario {i+1}",
                    f"Step 2: Verify result B for scenario {i+1}",
                    f"Step 3: Perform action C for scenario {i+1}"
                ],
                'expected_results': [
                    f"Expected result 1 for scenario {i+1}",
                    f"Expected result 2 for scenario {i+1}"
                ],
                'priority': 'High' if i < 2 else 'Medium' if i < 4 else 'Low'
            }
            scenarios.append(scenario)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_id': requirement_id,
            'requirement_title': requirement.get('title', ''),
            'scenarios': scenarios,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=requirement_id,
            generated_content=result,
            model_name=model_name,
            content_type='test_scenarios'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {num_scenarios} test scenarios for requirement {requirement_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test scenarios: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def generate_test_cases_from_scenarios(
    scenarios: List[Dict[str, Any]],
    model_name: str = "llama",
    prompt_template: str = None
) -> Dict[str, Any]:
    """
    Generate detailed test cases from test scenarios using watsonx.ai.
    
    Args:
        scenarios: List of scenario dictionaries
        model_name: LLM model to use
        prompt_template: Optional custom prompt template
        
    Returns:
        Dict: Generation results and metadata
    """
    if not scenarios:
        logger.error("No scenarios provided")
        return {
            'status': 'error',
            'error': "No scenarios provided"
        }
    
    # Default prompt template
    if not prompt_template:
        prompt_template = """
        You are a test case generation expert. Based on the following test scenario,
        create a detailed test case with specific test steps, test data, and expected results.
        
        Test Scenario:
        Name: {name}
        Description: {description}
        Preconditions: {preconditions}
        Steps: {steps}
        Expected Results: {expected_results}
        Priority: {priority}
        
        Generate a test case that includes:
        1. Specific test data values to use
        2. Detailed step-by-step test procedure
        3. Specific expected results for each step
        4. Validation points
        5. Any notes or special considerations
        """
    
    test_cases = []
    requirement_ids = set()
    
    try:
        for i, scenario in enumerate(scenarios):
            # Extract requirement ID if available
            requirement_id = scenario.get('requirement_id', f"REQ_{int(time.time())}")
            requirement_ids.add(requirement_id)
            
            # Format scenario details for prompt
            scenario_details = {
                'name': scenario.get('name', f"Scenario {i+1}"),
                'description': scenario.get('description', ''),
                'preconditions': '\n'.join(scenario.get('preconditions', [])),
                'steps': '\n'.join(scenario.get('steps', [])),
                'expected_results': '\n'.join(scenario.get('expected_results', [])),
                'priority': scenario.get('priority', 'Medium')
            }
            
            # Format prompt for this scenario
            prompt = prompt_template.format(**scenario_details)
            
            # Simulate API call delay
            import time
            time.sleep(0.5)
            
            # Mock test case generation
            test_case = {
                'id': f"TC_{int(time.time())}_{i}",
                'name': f"Test Case for {scenario_details['name']}",
                'description': f"Detailed test case for {scenario_details['name']}",
                'requirement_id': requirement_id,
                'scenario_name': scenario_details['name'],
                'priority': scenario_details['priority'],
                'test_data': {
                    'input1': 'Sample input value 1',
                    'input2': 'Sample input value 2'
                },
                'steps': [
                    {
                        'number': 1,
                        'description': 'Perform specific action A with test data',
                        'expected_result': 'System should respond with X'
                    },
                    {
                        'number': 2,
                        'description': 'Verify specific condition B',
                        'expected_result': 'Condition B should be true'
                    },
                    {
                        'number': 3,
                        'description': 'Perform specific action C',
                        'expected_result': 'System should update with Y'
                    }
                ],
                'validation_points': [
                    'Validate that X appears correctly',
                    'Validate that Y contains the expected data'
                ],
                'notes': 'This test case covers the main positive flow'
            }
            
            test_cases.append(test_case)
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'requirement_ids': list(requirement_ids),
            'test_cases': test_cases,
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=list(requirement_ids)[0] if requirement_ids else "multiple",
            generated_content=result,
            model_name=model_name,
            content_type='test_cases'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated {len(test_cases)} test cases from {len(scenarios)} scenarios")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test cases: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def analyze_test_failure(
    execution_id: str,
    model_name: str = "llama",
    include_similar_failures: bool = True
) -> Dict[str, Any]:
    """
    Analyze a test failure using watsonx.ai to determine potential causes and solutions.
    
    Args:
        execution_id: ID of the failed test execution
        model_name: LLM model to use
        include_similar_failures: Whether to include similar historical failures
        
    Returns:
        Dict: Analysis results and recommendations
    """
    # Get execution details
    try:
        execution = get_test_execution(execution_id)
    except ValueError as e:
        logger.error(f"Failed to get execution {execution_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Execution not found: {str(e)}"
        }
    
    # Check if execution is failed
    if execution.get('status', '').lower() != 'failed':
        logger.warning(f"Execution {execution_id} is not failed (status: {execution.get('status')})")
        return {
            'status': 'error',
            'error': f"Execution is not failed (status: {execution.get('status')})"
        }
    
    # Get test case details
    test_case_id = execution['metadata']['test_case_id']
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError:
        test_case = {'id': test_case_id}  # Minimal info if test case not found
    
    # Find the failed steps
    steps = execution.get('execution_steps', [])
    failed_steps = [step for step in steps if step.get('status', '').lower() == 'failed']
    
    if not failed_steps:
        logger.warning(f"No failed steps found in execution {execution_id}")
        return {
            'status': 'warning',
            'warning': "No failed steps found in execution",
            'execution_id': execution_id
        }
    
    # Get similar failures if requested
    similar_failures = []
    if include_similar_failures:
        # Query for similar failures
        query = """
        SELECT e.execution_id, e.test_case_id, e.status, e.executed_at
        FROM test_executions e
        WHERE e.test_case_id = %s 
        AND e.status = 'failed'
        AND e.execution_id != %s
        ORDER BY e.executed_at DESC
        LIMIT 5
        """
        
        similar_results = query_database(
            query=query,
            params=(test_case_id, execution_id)
        )
        
        for result in similar_results:
            try:
                similar_execution = get_test_execution(result['execution_id'])
                similar_failures.append(similar_execution)
            except ValueError:
                pass
    
    try:
        # Prepare analysis context
        analysis_context = {
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'execution_time': execution.get('execution_time', 0),
            'failed_steps': failed_steps,
            'similar_failures': len(similar_failures)
        }
        
        # Build prompt for watsonx.ai
        prompt = f"""
        Analyze the following test failure and provide potential causes and solutions.
        
        Test Case: {test_case.get('name', test_case_id)}
        Execution ID: {execution_id}
        
        Failed Steps:
        {json.dumps(failed_steps, indent=2)}
        
        Similar Failures: {len(similar_failures)} recent failures of this test case.
        
        Provide:
        1. Most likely causes of failure
        2. Recommended troubleshooting steps
        3. Potential fixes
        4. Is this likely a defect in the application or an issue with the test?
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock analysis results
        analysis_results = {
            'potential_causes': [
                {
                    'description': 'Data inconsistency in test environment',
                    'probability': 'High',
                    'explanation': 'The error message indicates a mismatch between expected and actual data values'
                },
                {
                    'description': 'Timing issue - operation not completed before verification',
                    'probability': 'Medium',
                    'explanation': 'The failure occurs during a verification step that may be executing too soon'
                },
                {
                    'description': 'Application defect in data processing logic',
                    'probability': 'Medium',
                    'explanation': 'The specific error pattern matches known issues in the data processing component'
                }
            ],
            'troubleshooting_steps': [
                'Verify test data is consistent with current environment state',
                'Add appropriate wait condition before verification step',
                'Review application logs for exceptions around the time of failure',
                'Compare with previous successful executions to identify changes'
            ],
            'potential_fixes': [
                {
                    'type': 'Test Update',
                    'description': 'Introduce a wait mechanism before verification',
                    'difficulty': 'Low'
                },
                {
                    'type': 'Environment Fix',
                    'description': 'Refresh test data to ensure consistency',
                    'difficulty': 'Medium'
                },
                {
                    'type': 'Application Fix',
                    'description': 'Review and correct data processing logic in the application',
                    'difficulty': 'High'
                }
            ],
            'defect_assessment': {
                'likely_application_defect': True,
                'confidence': 70,
                'explanation': 'Based on the error patterns and similar failures, there is a 70% probability this is an application defect rather than a test issue.'
            }
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'analysis_context': analysis_context,
            'analysis_results': analysis_results,
            'similar_failure_count': len(similar_failures),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='failure_analysis'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Completed failure analysis for execution {execution_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze test failure: {str(e)}")
        return {
            'status': 'error',
            'error': f"Analysis failed: {str(e)}"
        }


def suggest_test_case_improvements(
    test_case_id: str,
    model_name: str = "llama"
) -> Dict[str, Any]:
    """
    Use watsonx.ai to suggest improvements for an existing test case.
    
    Args:
        test_case_id: ID of the test case to improve
        model_name: LLM model to use
        
    Returns:
        Dict: Improvement suggestions and metadata
    """
    # Get test case details
    try:
        test_case = get_test_case_by_id(test_case_id)
    except ValueError as e:
        logger.error(f"Failed to get test case {test_case_id}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Test case not found: {str(e)}"
        }
    
    # Get test execution history
    query = """
    SELECT status, COUNT(*) as count
    FROM test_executions
    WHERE test_case_id = %s
    GROUP BY status
    """
    
    execution_stats = query_database(query, (test_case_id,))
    execution_history = {row['status']: row['count'] for row in execution_stats}
    
    # Get defects associated with this test case
    defects = get_defects(test_case_id=test_case_id)
    
    try:
        # Build prompt for watsonx.ai
        prompt = f"""
        Review the following test case and suggest improvements to make it more robust and effective.
        
        Test Case: {test_case.get('name', test_case_id)}
        Description: {test_case.get('description', '')}
        
        Current Test Steps:
        {json.dumps(test_case.get('steps', []), indent=2)}
        
        Execution History:
        {json.dumps(execution_history, indent=2)}
        
        Associated Defects: {len(defects)}
        
        Provide:
        1. Overall assessment of the test case
        2. Specific improvement suggestions
        3. Additional test scenarios that should be covered
        4. Recommendations for better test data
        5. Any validation points that should be added
        """
        
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Mock improvement suggestions
        improvement_suggestions = {
            'overall_assessment': {
                'quality_score': 7,  # 1-10 scale
                'strengths': [
                    'Good coverage of main functionality',
                    'Clear step descriptions'
                ],
                'weaknesses': [
                    'Limited validation points',
                    'Missing boundary condition tests',
                    'No negative test scenarios'
                ]
            },
            'specific_improvements': [
                {
                    'step_index': 2,
                    'current': test_case.get('steps', [])[2] if len(test_case.get('steps', [])) > 2 else {},
                    'suggestion': 'Add specific validation for the returned data format',
                    'rationale': 'Current step only verifies presence but not structure'
                },
                {
                    'type': 'Add Step',
                    'suggestion': 'Add verification step after data submission',
                    'rationale': 'Should verify successful data processing before proceeding'
                },
                {
                    'type': 'Modify Test Data',
                    'suggestion': 'Use more diverse test data including boundary values',
                    'rationale': 'Current test data only covers happy path'
                }
            ],
            'additional_scenarios': [
                {
                    'name': 'Negative Test - Invalid Input',
                    'description': 'Test behavior when invalid data is provided',
                    'steps': [
                        'Attempt to submit invalid data format',
                        'Verify appropriate error message is displayed',
                        'Verify no data corruption occurs'
                    ]
                },
                {
                    'name': 'Boundary Test - Maximum Values',
                    'description': 'Test behavior with maximum allowed values',
                    'steps': [
                        'Submit form with maximum length strings',
                        'Verify data is accepted and processed correctly',
                        'Verify display handles long values appropriately'
                    ]
                }
            ],
            'test_data_recommendations': [
                'Include null values for optional fields',
                'Add test case with maximum length strings',
                'Include special characters in text fields',
                'Test with minimum and maximum numeric values'
            ],
            'validation_points': [
                'Verify response times are within acceptable limits',
                'Check both UI updates and backend data consistency',
                'Validate error message content for clarity and correctness',
                'Ensure no unnecessary database queries are triggered'
            ]
        }
        
        # Prepare result
        result = {
            'status': 'success',
            'model': model_name,
            'test_case_id': test_case_id,
            'test_case_name': test_case.get('name', ''),
            'improvement_suggestions': improvement_suggestions,
            'execution_history': execution_history,
            'defect_count': len(defects),
            'generated_at': datetime.now().isoformat()
        }
        
        # Store the result
        file_name = store_llm_generation_result(
            requirement_id=test_case_id,  # Use test case ID as reference
            generated_content=result,
            model_name=model_name,
            content_type='test_improvement'
        )
        
        result['file_name'] = file_name
        
        logger.info(f"Generated improvement suggestions for test case {test_case_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate test case improvements: {str(e)}")
        return {
            'status': 'error',
            'error': f"Generation failed: {str(e)}"
        }


def create_database_backup(
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> str:
    """
    Create a backup of database tables in JSON format.
    
    Args:
        bucket_name: Name of the bucket
        tables: List of tables to backup (default: all tables)
        
    Returns:
        str: Object name of the backup file
    """
    if not tables:
        # Get all tables
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
        results = query_database(query)
        tables = [row['table_name'] for row in results]
    
    backup_data = {}
    
    for table in tables:
        query = f"SELECT * FROM {table};"
        results = query_database(query)
        
        # Convert datetime objects to ISO format
        for row in results:
            for key, value in row.items():
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
        
        backup_data[table] = results
    
    # Create backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_name = f"database_backup_{timestamp}.json"
    
    json_data = json.dumps(backup_data, indent=2)
    
    upload_data_to_storage(
        data=json_data.encode('utf-8'),
        object_name=backup_file_name,
        bucket_name=bucket_name,
        metadata={
            'content-type': 'application/json',
            'source': 'watsonx-ipg-testing',
            'type': 'database-backup',
            'tables': ','.join(tables)
        },
        content_type='application/json'
    )
    
    logger.info(f"Created database backup of {len(tables)} tables as {backup_file_name}")
    return backup_file_name


def restore_database_from_backup(
    backup_file_name: str,
    bucket_name: str = DEFAULT_BUCKET,
    tables: List[str] = None
) -> Dict[str, Any]:
    """
    Restore database tables from a backup file.
    
    Args:
        backup_file_name: Name of the backup file
        bucket_name: Name of the bucket
        tables: Optional list of specific tables to restore
        
    Returns:
        Dict: Restoration status and details
    """
    try:
        # Download backup file
        data_bytes = download_data_from_storage(
            object_name=backup_file_name,
            bucket_name=bucket_name
        )
        
        # Parse JSON
        backup_data = json.loads(data_bytes.decode('utf-8'))
        
        # Determine which tables to restore
        tables_to_restore = tables or list(backup_data.keys())
        
        # Verify tables exist in backup
        missing_tables = [table for table in tables_to_restore if table not in backup_data]
        if missing_tables:
            logger.error(f"Tables not found in backup: {', '.join(missing_tables)}")
            return {
                'status': 'error',
                'error': f"Tables not found in backup: {', '.join(missing_tables)}"
            }
        
        # Restore each table
        restoration_results = {}
        for table in tables_to_restore:
            try:
                # Delete existing data
                delete_query = f"DELETE FROM {table};"
                update_database(delete_query)
                
                # Insert backup data
                rows = backup_data[table]
                if not rows:
                    restoration_results[table] = {
                        'status': 'success',
                        'rows_restored': 0
                    }
                    continue
                
                # Build insert query
                columns = list(rows[0].keys())
                placeholders = ", ".join(["%s"] * len(columns))
                column_list = ", ".join(columns)
                
                insert_query = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                
                # Prepare params for batch insert
                params_list = []
                for row in rows:
                    # Ensure row values are in the same order as columns
                    row_values = [row[col] for col in columns]
                    params_list.append(row_values)
                
                # Perform batch insert
                affected_rows = batch_update_database(
                    query=insert_query,
                    params_list=params_list
                )
                
                restoration_results[table] = {
                    'status': 'success',
                    'rows_restored': affected_rows
                }
                
            except Exception as e:
                logger.error(f"Failed to restore table {table}: {str(e)}")
                restoration_results[table] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Check overall status
        success_count = sum(1 for result in restoration_results.values() if result['status'] == 'success')
        
        logger.info(f"Restored {success_count} of {len(tables_to_restore)} tables from backup {backup_file_name}")
        return {
            'status': 'success' if success_count == len(tables_to_restore) else 'partial',
            'tables_restored': success_count,
            'total_tables': len(tables_to_restore),
            'details': restoration_results
        }
        
    except Exception as e:
        logger.error(f"Failed to restore from backup {backup_file_name}: {str(e)}")
        return {
            'status': 'error',
            'error': f"Restoration failed: {str(e)}"
        }