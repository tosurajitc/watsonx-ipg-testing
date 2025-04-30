"""
Utility Functions for Requirements Ingestion Module

This module provides supporting functions for processing, 
validating, and managing requirements across different input methods.
"""

import re
import logging
from typing import Dict, List, Any, Optional
import magic  # For advanced file type detection
import hashlib
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class RequirementsUtilityManager:
    """
    Utility class for managing requirements-related operations
    """

    @staticmethod
    def validate_file_type(file_path: str) -> bool:
        """
        Validate file type using advanced file type detection.
        
        Args:
            file_path (str): Path to the file to validate
        
        Returns:
            bool: True if file type is supported, False otherwise
        """
        try:
            # Supported file types
            supported_types = [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/pdf',
                'text/plain'
            ]

            # Use python-magic for advanced file type detection
            file_mime = magic.Magic(mime=True).from_file(file_path)
            
            return file_mime in supported_types
        except Exception as e:
            logger.error(f"File type validation error: {str(e)}")
            return False

    @staticmethod
    def generate_requirement_hash(requirements_data: Dict[str, Any]) -> str:
        """
        Generate a unique hash for requirements to track changes.
        
        Args:
            requirements_data (Dict[str, Any]): Requirements data
        
        Returns:
            str: Unique hash representing the requirements
        """
        try:
            # Convert requirements to a standardized string
            requirements_str = str(sorted(requirements_data.items()))
            
            # Generate SHA-256 hash
            return hashlib.sha256(requirements_str.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Hash generation error: {str(e)}")
            return ""

    @staticmethod
    def extract_key_requirements(requirements_text: str) -> List[str]:
        """
        Extract key requirements from text using NLP-inspired patterns.
        
        Args:
            requirements_text (str): Input requirements text
        
        Returns:
            List[str]: List of extracted key requirements
        """
        try:
            # Patterns to identify requirements
            requirement_patterns = [
                r'should\s+(\w+)',
                r'must\s+(\w+)',
                r'shall\s+(\w+)',
                r'need(s)?\s+to\s+(\w+)',
                r'require(s)?\s+(\w+)'
            ]

            key_requirements = []
            for pattern in requirement_patterns:
                matches = re.findall(pattern, requirements_text, re.IGNORECASE)
                key_requirements.extend([match[-1] for match in matches])

            return list(set(key_requirements))
        except Exception as e:
            logger.error(f"Key requirements extraction error: {str(e)}")
            return []

    @staticmethod
    def sanitize_requirements_data(requirements_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize and clean requirements data.
        
        Args:
            requirements_data (Dict[str, Any]): Input requirements data
        
        Returns:
            Dict[str, Any]: Sanitized requirements data
        """
        try:
            sanitized_data = {}
            
            # Remove empty or None values
            for key, value in requirements_data.items():
                if value not in [None, '', {}]:
                    # Deep copy to prevent reference issues
                    sanitized_data[key] = value

            return sanitized_data
        except Exception as e:
            logger.error(f"Requirements data sanitization error: {str(e)}")
            return {}

    @staticmethod
    def generate_requirements_report(
        requirements_data: Dict[str, Any], 
        source: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive report for requirements.
        
        Args:
            requirements_data (Dict[str, Any]): Requirements data
            source (str): Source of requirements (manual/file/jira)
        
        Returns:
            Dict[str, Any]: Comprehensive requirements report
        """
        try:
            # Sanitize requirements
            sanitized_data = RequirementsUtilityManager.sanitize_requirements_data(requirements_data)
            
            # Generate hash
            data_hash = RequirementsUtilityManager.generate_requirement_hash(sanitized_data)
            
            # Extract key requirements
            text_content = str(sanitized_data)
            key_reqs = RequirementsUtilityManager.extract_key_requirements(text_content)

            return {
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "hash": data_hash,
                "key_requirements": key_reqs,
                "total_requirements": len(sanitized_data),
                "raw_data": sanitized_data
            }
        except Exception as e:
            logger.error(f"Requirements report generation error: {str(e)}")
            return {}

def validate_jira_connection(
    url: str, 
    project_key: str, 
    api_token: str
) -> Dict[str, Any]:
    """
    Validate JIRA connection parameters.
    
    Args:
        url (str): JIRA instance URL
        project_key (str): JIRA project key
        api_token (str): JIRA API token
    
    Returns:
        Dict[str, Any]: Validation result
    """
    validation_results = {
        "url_valid": False,
        "project_key_valid": False,
        "token_format_valid": False,
        "overall_valid": False
    }

    try:
        # URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        validation_results["url_valid"] = bool(url_pattern.match(url))

        # Project key validation
        validation_results["project_key_valid"] = bool(
            re.match(r'^[A-Z0-9]+-?[A-Z0-9]*$', project_key)
        )

        # Token format validation (basic check)
        validation_results["token_format_valid"] = (
            len(api_token) >= 20 and  # Minimum length
            any(char.isdigit() for char in api_token) and
            any(char.isupper() for char in api_token)
        )

        # Overall validation
        validation_results["overall_valid"] = all([
            validation_results["url_valid"],
            validation_results["project_key_valid"],
            validation_results["token_format_valid"]
        ])

        return validation_results

    except Exception as e:
        logger.error(f"JIRA connection validation error: {str(e)}")
        return validation_results