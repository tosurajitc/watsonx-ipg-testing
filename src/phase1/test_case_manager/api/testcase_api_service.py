#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Case API Service Module for the Watsonx IPG Testing platform.

This module provides RESTful API endpoints for managing test cases, including
creation, retrieval, updating, and deletion operations. It serves as the interface
between the Test Case Manager Module and external systems or UIs.
"""

import os
import logging
import json
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import traceback

# Import Flask framework
from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
import pandas as pd
import tempfile

# Import from src.common
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    TestCaseNotFoundError,
    MetadataError,
    VersionControlError,
    InvalidVersionError
)

# Import from other modules
from src.phase1.test_case_manager.testcase_generator import TestCaseGenerator
from src.phase1.test_case_manager.testcase_refiner import TestCaseRefiner
from src.phase1.test_case_manager.version_controller import VersionController
from src.phase1.test_case_manager.metadata_manager import MetadataManager

# Setup logger
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize components
test_case_generator = None
test_case_refiner = None
version_controller = None
metadata_manager = None

def initialize_components():
    """Initialize all the components needed for the API service."""
    global test_case_generator, test_case_refiner, version_controller, metadata_manager
    
    try:
        # Initialize components with default configurations
        test_case_generator = TestCaseGenerator()
        test_case_refiner = TestCaseRefiner()
        version_controller = VersionController()
        metadata_manager = MetadataManager()
        
        logger.info("All components initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize components: {str(e)}")
        return False

# Error handler for API endpoints
def handle_error(error: Exception, status_code: int = 500) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized error response.
    
    Args:
        error (Exception): The exception that occurred.
        status_code (int, optional): HTTP status code. Defaults to 500.
        
    Returns:
        Tuple[Dict[str, Any], int]: Error response and status code.
    """
    error_type = error.__class__.__name__
    
    # Map certain exceptions to appropriate status codes
    if isinstance(error, TestCaseNotFoundError):
        status_code = 404  # Not Found
    elif isinstance(error, InvalidVersionError):
        status_code = 404  # Not Found
    elif isinstance(error, (MetadataError, VersionControlError)):
        status_code = 400  # Bad Request
    
    # Create error response
    response = {
        "status": "error",
        "error": {
            "type": error_type,
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Add stack trace in debug mode
    if app.debug:
        response["error"]["stack_trace"] = traceback.format_exc()
    
    return response, status_code

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check() -> Tuple[Dict[str, Any], int]:
    """
    Check the health of the API service.
    
    Returns:
        Tuple[Dict[str, Any], int]: Health status and HTTP status code.
    """
    # Check if all components are initialized
    is_healthy = (test_case_generator is not None and
                  test_case_refiner is not None and
                  version_controller is not None and
                  metadata_manager is not None)
    
    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "test_case_generator": test_case_generator is not None,
            "test_case_refiner": test_case_refiner is not None,
            "version_controller": version_controller is not None,
            "metadata_manager": metadata_manager is not None
        }
    }
    
    return response, 200 if is_healthy else 503

# Test Case Generator Endpoints
@app.route('/api/test-cases/generate', methods=['POST'])
def generate_test_case() -> Tuple[Dict[str, Any], int]:
    """
    Generate a test case from a scenario.
    
    Request body:
        - scenario (Dict): The test scenario data
        - output_path (str, optional): Path to save the generated test case
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'scenario' not in request_data:
            return {"status": "error", "message": "Missing scenario data"}, 400
        
        scenario = request_data['scenario']
        output_path = request_data.get('output_path')
        
        # Generate test case
        test_case_df = test_case_generator.generate_test_case_from_scenario(scenario)
        
        # Save to file if output path provided
        if output_path:
            output_path = test_case_generator.save_test_case_to_excel(test_case_df, output_path)
            
            # Create metadata for the test case
            test_case_id = None
            if len(test_case_df) > 0 and "TEST CASE NUMBER" in test_case_df.columns:
                test_case_id = test_case_df.iloc[0]["TEST CASE NUMBER"]
            
            if test_case_id:
                # Extract basic info for metadata
                test_case_data = {}
                
                if "TEST CASE" in test_case_df.columns:
                    test_case_data["TEST_CASE"] = test_case_df.iloc[0]["TEST CASE"]
                
                if "SUBJECT" in test_case_df.columns:
                    test_case_data["MODULE"] = test_case_df.iloc[0]["SUBJECT"]
                
                if "TEST USER ID/ROLE" in test_case_df.columns:
                    test_case_data["OWNER"] = test_case_df.iloc[0]["TEST USER ID/ROLE"]
                
                if "TYPE" in test_case_df.columns:
                    test_case_data["TEST_TYPE"] = test_case_df.iloc[0]["TYPE"]
                
                test_case_data["TEST_CASE_ID"] = test_case_id
                
                # Create metadata
                metadata_manager.create_test_case_metadata(test_case_data, created_by=request_data.get('created_by'))
        
        # Return the test case data
        return {
            "status": "success",
            "message": "Test case generated successfully",
            "data": {
                "test_case": test_case_df.to_dict('records'),
                "output_path": output_path
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/generate-batch', methods=['POST'])
def generate_test_cases_batch() -> Tuple[Dict[str, Any], int]:
    """
    Generate multiple test cases from scenarios.
    
    Request body:
        - scenarios (List[Dict]): List of test scenarios
        - output_dir (str, optional): Directory to save generated test cases
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'scenarios' not in request_data:
            return {"status": "error", "message": "Missing scenarios data"}, 400
        
        scenarios = request_data['scenarios']
        output_dir = request_data.get('output_dir')
        
        # Generate test cases
        test_cases = test_case_generator.generate_test_cases_batch(scenarios)
        
        # Save to files if output directory provided
        output_files = []
        if output_dir:
            for scenario_id, test_case_df in test_cases.items():
                output_filename = f"TestCase_{scenario_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                output_path = os.path.join(output_dir, output_filename)
                
                test_case_generator.save_test_case_to_excel(test_case_df, output_path)
                output_files.append(output_path)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Generated {len(test_cases)} test cases",
            "data": {
                "scenario_ids": list(test_cases.keys()),
                "output_files": output_files
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/process-scenario-file', methods=['POST'])
def process_scenario_file() -> Tuple[Dict[str, Any], int]:
    """
    Process a scenario file to generate test cases.
    
    Request body:
        - scenario_file_path (str): Path to the scenario file
        - output_dir (str, optional): Directory to save generated test cases
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'scenario_file_path' not in request_data:
            return {"status": "error", "message": "Missing scenario_file_path"}, 400
        
        scenario_file_path = request_data['scenario_file_path']
        output_dir = request_data.get('output_dir')
        
        # Process the scenario file
        output_files = test_case_generator.process_scenario_file(scenario_file_path, output_dir)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Generated {len(output_files)} test case files",
            "data": {
                "output_files": output_files
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

# Test Case Refiner Endpoints
@app.route('/api/test-cases/refine', methods=['POST'])
def refine_test_case() -> Tuple[Dict[str, Any], int]:
    """
    Analyze and refine a test case.
    
    Request body:
        - test_case_path (str): Path to the test case file
        - output_path (str, optional): Path to save analysis results
        
    Returns:
        Tuple[Dict[str, Any], int]: Refinement suggestions and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'test_case_path' not in request_data:
            return {"status": "error", "message": "Missing test_case_path"}, 400
        
        test_case_path = request_data['test_case_path']
        output_path = request_data.get('output_path')
        
        # Analyze the test case
        analysis_results = test_case_refiner.suggest_refinements(test_case_path)
        
        # Get summary
        summary = test_case_refiner.get_refinement_summary(analysis_results)
        
        # Save analysis results if output path provided
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(analysis_results, f, indent=2)
        
        # Return the analysis results
        return {
            "status": "success",
            "message": "Test case analyzed successfully",
            "data": {
                "test_case_info": analysis_results["test_case_info"],
                "summary": summary,
                "step_suggestions": analysis_results["step_suggestions"],
                "missing_test_variations": analysis_results["missing_test_variations"],
                "general_suggestions": analysis_results["general_suggestions"],
                "output_path": output_path
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/apply-refinements', methods=['POST'])
def apply_test_case_refinements() -> Tuple[Dict[str, Any], int]:
    """
    Apply refinements to a test case.
    
    Request body:
        - test_case_path (str): Path to the test case file
        - refinements (Dict): Refinement data to apply
        - output_path (str): Path to save the refined file
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'test_case_path' not in request_data or 'refinements' not in request_data:
            return {"status": "error", "message": "Missing required parameters"}, 400
        
        test_case_path = request_data['test_case_path']
        refinements = request_data['refinements']
        output_path = request_data.get('output_path')
        
        # Apply refinements
        refined_path = test_case_refiner.apply_refinements(test_case_path, refinements, output_path)
        
        # Return the result
        return {
            "status": "success",
            "message": "Refinements applied successfully",
            "data": {
                "refined_path": refined_path
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

# Version Controller Endpoints
@app.route('/api/test-cases/versions/check-in', methods=['POST'])
def check_in_new_version() -> Tuple[Dict[str, Any], int]:
    """
    Check in a new version of a test case.
    
    Request body:
        - test_case_path (str): Path to the test case file
        - change_comment (str, optional): Comment describing the changes
        - changed_by (str, optional): Name/ID of the person who made the changes
        - notify_owner (bool, optional): Whether to notify the test case owner
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'test_case_path' not in request_data:
            return {"status": "error", "message": "Missing test_case_path"}, 400
        
        test_case_path = request_data['test_case_path']
        change_comment = request_data.get('change_comment')
        changed_by = request_data.get('changed_by')
        notify_owner = request_data.get('notify_owner', True)
        
        # Check in the new version
        result = version_controller.check_in_new_version(
            test_case_path,
            change_comment=change_comment,
            changed_by=changed_by,
            notify_owner=notify_owner
        )
        
        # Return the result
        return {
            "status": "success",
            "message": "New version checked in successfully" if result["is_new_version"] else "No changes detected",
            "data": result
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/versions', methods=['GET'])
def get_version_history(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Get the version history for a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Returns:
        Tuple[Dict[str, Any], int]: Version history and HTTP status code.
    """
    try:
        # Get version history
        history = version_controller.get_version_history(test_case_id)
        
        # Return the history
        return {
            "status": "success",
            "data": history
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/versions/<version>', methods=['GET'])
def get_test_case_version(test_case_id: str, version: str) -> Response:
    """
    Get a specific version of a test case.
    
    Args:
        test_case_id (str): The test case ID.
        version (str): The version to retrieve.
        
    Returns:
        Response: Excel file response or error.
    """
    try:
        # Create a temporary file to store the Excel
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Get the test case version
        test_case_df = version_controller.get_test_case_version(test_case_id, version)
        
        # Save to the temporary file
        test_case_df.to_excel(temp_path, index=False)
        
        # Return the file
        return send_file(
            temp_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{test_case_id}_v{version}.xlsx"
        )
        
    except Exception as e:
        error_response, status_code = handle_error(e)
        return jsonify(error_response), status_code

@app.route('/api/test-cases/<test_case_id>/versions/compare', methods=['GET'])
def compare_versions(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Compare two versions of a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Query parameters:
        - version1 (str): First version to compare.
        - version2 (str): Second version to compare.
        
    Returns:
        Tuple[Dict[str, Any], int]: Comparison results and HTTP status code.
    """
    try:
        # Get query parameters
        version1 = request.args.get('version1')
        version2 = request.args.get('version2')
        
        if not version1 or not version2:
            return {"status": "error", "message": "Missing version parameters"}, 400
        
        # Compare versions
        comparison = version_controller.compare_versions(test_case_id, version1, version2)
        
        # Return the comparison results
        return {
            "status": "success",
            "data": comparison
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/sharepoint', methods=['POST'])
def upload_to_sharepoint(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Upload a test case version to SharePoint.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - version (str, optional): The version to upload.
        - sharepoint_folder (str, optional): The SharePoint folder path.
        
    Returns:
        Tuple[Dict[str, Any], int]: Upload result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json or {}
        
        version = request_data.get('version')
        sharepoint_folder = request_data.get('sharepoint_folder')
        
        # Upload to SharePoint
        result = version_controller.upload_to_sharepoint(
            test_case_id,
            version=version,
            sharepoint_folder=sharepoint_folder
        )
        
        # Return the result
        return {
            "status": "success",
            "message": f"Test case uploaded to SharePoint successfully",
            "data": result
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/status', methods=['PUT'])
def update_test_case_status(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update the status of a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - status (str): The new status ("Under Maintenance" or "Active").
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'status' not in request_data:
            return {"status": "error", "message": "Missing status"}, 400
        
        new_status = request_data['status']
        
        # Update status
        if new_status == "Under Maintenance":
            result = version_controller.mark_as_under_maintenance(test_case_id)
        elif new_status == "Active":
            result = version_controller.mark_as_active(test_case_id)
        else:
            return {"status": "error", "message": "Invalid status. Must be 'Under Maintenance' or 'Active'"}, 400
        
        # Return the result
        return {
            "status": "success",
            "message": f"Test case status updated to {new_status}",
            "data": result
        }, 200
        
    except Exception as e:
        return handle_error(e)

# Metadata Manager Endpoints
@app.route('/api/test-cases/metadata/<test_case_id>', methods=['GET'])
def get_test_case_metadata(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Get metadata for a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Returns:
        Tuple[Dict[str, Any], int]: Metadata and HTTP status code.
    """
    try:
        # Get metadata
        metadata = metadata_manager.get_test_case_metadata(test_case_id)
        
        if not metadata:
            return {"status": "error", "message": f"Test case {test_case_id} not found"}, 404
        
        # Return the metadata
        return {
            "status": "success",
            "data": metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/metadata', methods=['POST'])
def create_test_case_metadata() -> Tuple[Dict[str, Any], int]:
    """
    Create metadata for a new test case.
    
    Request body:
        - test_case_data (Dict): Basic test case data.
        - created_by (str, optional): Person creating the test case.
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'test_case_data' not in request_data:
            return {"status": "error", "message": "Missing test_case_data"}, 400
        
        test_case_data = request_data['test_case_data']
        created_by = request_data.get('created_by')
        
        # Create metadata
        test_case_id = metadata_manager.create_test_case_metadata(
            test_case_data,
            created_by=created_by
        )
        
        # Get the created metadata
        metadata = metadata_manager.get_test_case_metadata(test_case_id)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Metadata created for test case {test_case_id}",
            "data": metadata
        }, 201
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/metadata/<test_case_id>', methods=['PUT'])
def update_test_case_metadata(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update metadata for an existing test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - updates (Dict): Metadata fields to update.
        - modified_by (str, optional): Person making the updates.
        
    Returns:
        Tuple[Dict[str, Any], int]: Updated metadata and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'updates' not in request_data:
            return {"status": "error", "message": "Missing updates"}, 400
        
        updates = request_data['updates']
        modified_by = request_data.get('modified_by')
        
        # Update metadata
        updated_metadata = metadata_manager.update_test_case_metadata(
            test_case_id,
            updates,
            modified_by=modified_by
        )
        
        # Return the updated metadata
        return {
            "status": "success",
            "message": f"Metadata updated for test case {test_case_id}",
            "data": updated_metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/metadata/<test_case_id>', methods=['DELETE'])
def delete_test_case_metadata(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Delete metadata for a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Delete metadata
        success = metadata_manager.delete_test_case_metadata(test_case_id)
        
        if not success:
            return {"status": "error", "message": f"Failed to delete metadata for test case {test_case_id}"}, 500
        
        # Return the result
        return {
            "status": "success",
            "message": f"Metadata deleted for test case {test_case_id}"
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/search', methods=['POST'])
def search_test_cases() -> Tuple[Dict[str, Any], int]:
    """
    Search for test cases based on metadata criteria.
    
    Request body:
        - criteria (Dict): Search criteria.
        
    Returns:
        Tuple[Dict[str, Any], int]: Search results and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'criteria' not in request_data:
            return {"status": "error", "message": "Missing search criteria"}, 400
        
        criteria = request_data['criteria']
        
        # Search test cases
        results = metadata_manager.search_test_cases(criteria)
        
        # Return the results
        return {
            "status": "success",
            "message": f"Found {len(results)} matching test cases",
            "data": results
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/ownership', methods=['PUT'])
def update_test_case_owner(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update the owner of a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - owner (str): The new owner.
        - modified_by (str, optional): Person making the update.
        
    Returns:
        Tuple[Dict[str, Any], int]: Updated metadata and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'owner' not in request_data:
            return {"status": "error", "message": "Missing owner"}, 400
        
        new_owner = request_data['owner']
        modified_by = request_data.get('modified_by')
        
        # Update owner
        updated_metadata = metadata_manager.update_test_case_owner(
            test_case_id,
            new_owner,
            modified_by=modified_by
        )
        
        # Return the updated metadata
        return {
            "status": "success",
            "message": f"Owner updated for test case {test_case_id}",
            "data": updated_metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/automation-status', methods=['PUT'])
def update_automation_status(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update the automation status of a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - status (str): The new automation status.
        - modified_by (str, optional): Person making the update.
        
    Returns:
        Tuple[Dict[str, Any], int]: Updated metadata and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'status' not in request_data:
            return {"status": "error", "message": "Missing status"}, 400
        
        new_status = request_data['status']
        modified_by = request_data.get('modified_by')
        
        # Update automation status
        updated_metadata = metadata_manager.update_automation_status(
            test_case_id,
            new_status,
            modified_by=modified_by
        )
        
        # Return the updated metadata
        return {
            "status": "success",
            "message": f"Automation status updated for test case {test_case_id}",
            "data": updated_metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/execution-result', methods=['PUT'])
def update_execution_result(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Update the execution result for a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - result (str): The execution result.
        - executed_by (str, optional): Person who executed the test.
        
    Returns:
        Tuple[Dict[str, Any], int]: Updated metadata and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'result' not in request_data:
            return {"status": "error", "message": "Missing result"}, 400
        
        result = request_data['result']
        executed_by = request_data.get('executed_by')
        
        # Update execution result
        updated_metadata = metadata_manager.update_test_execution_result(
            test_case_id,
            result,
            executed_by=executed_by
        )
        
        # Return the updated metadata
        return {
            "status": "success",
            "message": f"Execution result updated for test case {test_case_id}",
            "data": updated_metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/tags', methods=['POST'])
def add_tags_to_test_case(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Add tags to a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - tags (List[str]): Tags to add.
        - modified_by (str, optional): Person making the update.
        
    Returns:
        Tuple[Dict[str, Any], int]: Updated metadata and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'tags' not in request_data:
            return {"status": "error", "message": "Missing tags"}, 400
        
        tags = request_data['tags']
        modified_by = request_data.get('modified_by')
        
        # Add tags
        updated_metadata = metadata_manager.add_tags_to_test_case(
            test_case_id,
            tags,
            modified_by=modified_by
        )
        
        # Return the updated metadata
        return {
            "status": "success",
            "message": f"Tags added to test case {test_case_id}",
            "data": updated_metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/<test_case_id>/tags', methods=['DELETE'])
def remove_tags_from_test_case(test_case_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Remove tags from a test case.
    
    Args:
        test_case_id (str): The test case ID.
        
    Request body:
        - tags (List[str]): Tags to remove.
        - modified_by (str, optional): Person making the update.
        
    Returns:
        Tuple[Dict[str, Any], int]: Updated metadata and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'tags' not in request_data:
            return {"status": "error", "message": "Missing tags"}, 400
        
        tags = request_data['tags']
        modified_by = request_data.get('modified_by')
        
        # Remove tags
        updated_metadata = metadata_manager.remove_tags_from_test_case(
            test_case_id,
            tags,
            modified_by=modified_by
        )
        
        # Return the updated metadata
        return {
            "status": "success",
            "message": f"Tags removed from test case {test_case_id}",
            "data": updated_metadata
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/tags', methods=['GET'])
def get_all_tags() -> Tuple[Dict[str, Any], int]:
    """
    Get all tags used across test cases.
    
    Returns:
        Tuple[Dict[str, Any], int]: List of tags and HTTP status code.
    """
    try:
        # Get all tags
        tags = metadata_manager.get_all_tags()
        
        # Return the tags
        return {
            "status": "success",
            "data": tags
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/metadata/export', methods=['POST'])
def export_metadata() -> Tuple[Dict[str, Any], int]:
    """
    Export test case metadata to a JSON file.
    
    Request body:
        - output_path (str): Path to save the JSON file.
        - test_case_ids (List[str], optional): Specific test cases to export.
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'output_path' not in request_data:
            return {"status": "error", "message": "Missing output_path"}, 400
        
        output_path = request_data['output_path']
        test_case_ids = request_data.get('test_case_ids')
        
        # Export metadata
        count = metadata_manager.export_metadata_to_json(output_path, test_case_ids)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Exported {count} test case metadata records to {output_path}",
            "data": {
                "count": count,
                "output_path": output_path
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

@app.route('/api/test-cases/metadata/import', methods=['POST'])
def import_metadata() -> Tuple[Dict[str, Any], int]:
    """
    Import test case metadata from a JSON file.
    
    Request body:
        - input_path (str): Path to the JSON file.
        - overwrite (bool, optional): Whether to overwrite existing metadata.
        
    Returns:
        Tuple[Dict[str, Any], int]: Result and HTTP status code.
    """
    try:
        # Get request data
        request_data = request.json
        
        if not request_data or 'input_path' not in request_data:
            return {"status": "error", "message": "Missing input_path"}, 400
        
        input_path = request_data['input_path']
        overwrite = request_data.get('overwrite', False)
        
        # Import metadata
        count = metadata_manager.import_metadata_from_json(input_path, overwrite)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Imported {count} test case metadata records from {input_path}",
            "data": {
                "count": count,
                "input_path": input_path
            }
        }, 200
        
    except Exception as e:
        return handle_error(e)

# Initialize components when module is loaded
initialize_components()

# Run the application if executed directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Test Case API Service")
    parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize components before starting the server
    if not initialize_components():
        logger.error("Failed to initialize components. Exiting.")
        exit(1)
    
    # Run the Flask app
    app.run(host=args.host, port=args.port, debug=args.debug)