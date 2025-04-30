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




#################### Testing blocl

import streamlit as st
import pandas as pd
import time
from ui_utils import show_info_message, show_success_message, show_error_message
from state_management import add_notification, add_test_case
import mock_services

def show_test_generation():
    """Display the test generation and refinement module UI."""
    st.header("Test Generation & Refinement Module")
    
    # Create tabs for different functions
    tabs = st.tabs(["Generate Detailed Test Cases", "Review & Refine Test Case"])
    
    with tabs[0]:
        show_test_generation_tab()
    
    with tabs[1]:
        show_test_refinement_tab()

def show_test_generation_tab():
    """Display the test generation tab."""
    st.subheader("Generate Detailed Test Cases")
    
    # Check if we came from requirements selection
    if "generated_from_requirements" in st.session_state:
        st.info(f"Generating test cases from selected requirements: {', '.join(st.session_state['generated_from_requirements'])}")
        
        # Show the processing status
        with st.spinner("Processing requirements and generating test cases..."):
            # Simulate processing time
            time.sleep(3)
            
            # Use mock data for generated test cases
            generated_test_cases = mock_services.generate_test_cases_from_requirements(
                st.session_state["generated_from_requirements"]
            )
            st.session_state["generated_test_cases"] = generated_test_cases
        
        # Clear the flag
        del st.session_state["generated_from_requirements"]
    
    # Input methods for test generation
    st.subheader("Input for Test Generation")
    
    input_method = st.radio(
        "Select Input Method",
        ["From Processed Requirements", "Direct Prompt"]
    )
    
    if input_method == "From Processed Requirements":
        # Check if requirements exist
        if "requirements" in st.session_state and st.session_state.requirements:
            # Multi-select for requirements
            selected_reqs = st.multiselect(
                "Select Requirements",
                options=[req["id"] for req in st.session_state.requirements],
                format_func=lambda x: f"{x}: {next((req['title'] for req in st.session_state.requirements if req['id'] == x), '')}"
            )
            
            if selected_reqs:
                if st.button("Generate Test Cases", key="gen_from_reqs_button"):
                    with st.spinner("Generating test cases from requirements..."):
                        # Simulate processing time
                        time.sleep(3)
                        
                        # Use mock data for generated test cases
                        generated_test_cases = mock_services.generate_test_cases_from_requirements(selected_reqs)
                        st.session_state["generated_test_cases"] = generated_test_cases
                        
                        show_success_message("Test cases generated successfully!")
                        add_notification("Generated test cases from requirements", "success")
        else:
            st.warning("No requirements available. Please process requirements first in the Requirements Module.")
    else:  # Direct Prompt
        # Text area for direct prompt
        prompt = st.text_area(
            "Enter Test Case Generation Prompt",
            placeholder="E.g., Generate login tests for admin user",
            height=100
        )
        
        # Configuration options
        st.subheader("Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            detail_level = st.select_slider(
                "Detail Level",
                options=["Low", "Medium", "High"],
                value="Medium"
            )
        
        with col2:
            format_type = st.selectbox(
                "Output Format",
                ["Standard", "Gherkin", "Detailed"]
            )
        
        if prompt:
            if st.button("Generate Test Cases", key="gen_from_prompt_button"):
                with st.spinner("Generating test cases from prompt..."):
                    # Simulate processing time
                    time.sleep(3)
                    
                    # Use mock data for generated test cases (simplified for direct prompt)
                    generated_test_cases = [{
                        "id": f"TC-{1000 + i}",
                        "title": f"Test case {i+1} for {prompt[:30]}{'...' if len(prompt) > 30 else ''}",
                        "status": "New",
                        "owner": "AI Generated",
                        "type": "Manual",
                        "steps": [
                            {"step_no": 1, "description": "Setup test environment", "expected": "Environment ready"},
                            {"step_no": 2, "description": f"Execute {prompt[:20]}...", "expected": "Test executed"},
                            {"step_no": 3, "description": "Verify results", "expected": "Results verified"},
                        ],
                    } for i in range(3)]
                    
                    st.session_state["generated_test_cases"] = generated_test_cases
                    
                    show_success_message("Test cases generated successfully!")
                    add_notification("Generated test cases from prompt", "success")
    
    # Display generated test cases if available
    if "generated_test_cases" in st.session_state and st.session_state["generated_test_cases"]:
        st.markdown("---")
        st.subheader("Generated Test Cases")
        
        # Display test cases in a prettier format
        for i, test_case in enumerate(st.session_state["generated_test_cases"]):
            with st.expander(f"{test_case['id']}: {test_case['title']}", expanded=i == 0):
                st.write(f"**Status:** {test_case['status']}")
                st.write(f"**Owner:** {test_case['owner']}")
                st.write(f"**Type:** {test_case['type']}")
                
                st.subheader("Steps")
                steps_df = pd.DataFrame(test_case["steps"])
                st.dataframe(steps_df, use_container_width=True)
        
        # Actions for generated test cases
        st.markdown("---")
        st.subheader("Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export to Excel", key="export_button"):
                with st.spinner("Exporting to Excel..."):
                    # Simulate processing time
                    time.sleep(1)
                    show_success_message("Test cases exported to Excel successfully!")
                    st.download_button(
                        label="Download Excel File",
                        data=b"Mock Excel Data",  # Just a placeholder
                        file_name="test_cases_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with col2:
            if st.button("Compare with Repository", key="compare_button"):
                with st.spinner("Comparing with repository..."):
                    # Simulate processing time
                    time.sleep(2)
                    
                    # Store for repository module to use
                    st.session_state["compare_result"] = True
                    
                    show_success_message("Comparison completed! Navigating to Repository module...")
                    add_notification("Compared generated test cases with repository", "success")
                    
                    # Navigate to repository module
                    st.session_state["page"] = "Test Repository"
                    st.experimental_rerun()

def show_test_refinement_tab():
    """Display the test refinement tab."""
    st.subheader("Review & Refine Test Case")
    
    # File upload for existing test case
    uploaded_file = st.file_uploader(
        "Upload Existing Test Case File",
        type=["xlsx", "docx"],
        help="Upload an existing test case in Excel or Word format"
    )
    
    if uploaded_file is not None:
        st.write(f"File name: {uploaded_file.name}")
        st.write(f"File size: {uploaded_file.size} bytes")
        
        # Process button
        if st.button("Analyze & Suggest Refinements", key="analyze_button"):
            with st.spinner("Analyzing test case and generating refinements..."):
                # Simulate processing time
                time.sleep(3)
                
                # Use mock data - select a random test case to refine
                if mock_services.get_test_cases():
                    test_case_id = mock_services.get_test_cases()[0]["id"]
                    original_test_case = mock_services.get_test_case_by_id(test_case_id)
                    refined_test_case = mock_services.refine_test_case(test_case_id)
                    
                    st.session_state["original_test_case"] = original_test_case
                    st.session_state["refined_test_case"] = refined_test_case
                    
                    show_success_message("Analysis complete! Review the suggested refinements below.")
    
    # Display comparison if available
    if "original_test_case" in st.session_state and "refined_test_case" in st.session_state:
        st.markdown("---")
        st.subheader("Test Case Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Original Test Case")
            original_tc = st.session_state["original_test_case"]
            st.write(f"**ID:** {original_tc['id']}")
            st.write(f"**Title:** {original_tc['title']}")
            st.write(f"**Status:** {original_tc['status']}")
            st.write(f"**Owner:** {original_tc['owner']}")
            st.write(f"**Type:** {original_tc['type']}")
            
            st.markdown("#### Steps")
            original_steps_df = pd.DataFrame(original_tc["steps"])
            st.dataframe(original_steps_df, use_container_width=True)
        
        with col2:
            st.markdown("### Refined Test Case")
            refined_tc = st.session_state["refined_test_case"]
            st.write(f"**ID:** {refined_tc['id']}")
            st.write(f"**Title:** {refined_tc['title']}")
            st.write(f"**Status:** {refined_tc['status']}")
            st.write(f"**Owner:** {refined_tc['owner']}")
            st.write(f"**Type:** {refined_tc['type']}")
            
            st.markdown("#### Steps")
            refined_steps_df = pd.DataFrame(refined_tc["steps"])
            st.dataframe(refined_steps_df, use_container_width=True)
        
        # AI suggestions
        st.markdown("---")
        st.subheader("AI Suggestions")
        
        suggestion_box = st.container()
        with suggestion_box:
            st.info("""
            **Suggested Changes:**
            
            1. Added an additional validation step to ensure more thorough testing
            2. Expanded expected results with more specific success criteria
            3. Added test data references for better traceability
            
            These changes will improve test coverage and make the test case more robust.
            """)
        
        # Actions
        st.markdown("---")
        st.subheader("Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Accept Suggestions & Update Repository", key="accept_button"):
                with st.spinner("Updating repository..."):
                    # Simulate processing time
                    time.sleep(2)
                    show_success_message("Test case updated in repository successfully!")
                    add_notification(f"Updated test case {refined_tc['id']} with refinements", "success")
                    # Add to session state
                    add_test_case(refined_tc)
            
            if st.button("Notify Owner of Suggestions", key="notify_button"):
                with st.spinner("Sending notification..."):
                    # Simulate processing time
                    time.sleep(1)
                    show_success_message(f"Notification sent to {original_tc['owner']} successfully!")
                    add_notification(f"Sent refinement suggestions for {original_tc['id']} to owner", "info")
        
        with col2:
            if st.button("Mark as Obsolete", key="obsolete_button"):
                confirm = st.checkbox("Confirm marking as obsolete", key="confirm_obsolete")
                if confirm:
                    with st.spinner("Marking as obsolete..."):
                        # Simulate processing time
                        time.sleep(1)
                        show_success_message(f"Test case {original_tc['id']} marked as obsolete!")
                        add_notification(f"Marked test case {original_tc['id']} as obsolete", "warning")
            
            if st.button("Discard Suggestions", key="discard_button"):
                with st.spinner("Discarding suggestions..."):
                    # Simulate processing time
                    time.sleep(1)
                    # Clear session state
                    del st.session_state["original_test_case"]
                    del st.session_state["refined_test_case"]
                    show_info_message("Suggestions discarded.")
                    st.experimental_rerun()

################### Testing block endss here


class TestCaseAPIService:
    """
    Class to provide programmatic access to the Test Case Management API functionality.
    
    This class serves as a direct interface for other programs to interact with
    the Test Case Manager Module without going through HTTP requests.
    """
    
    def __init__(self):
        """Initialize the TestCaseAPIService with all required components."""
        self.test_case_generator = TestCaseGenerator()
        self.test_case_refiner = TestCaseRefiner()
        self.version_controller = VersionController()
        self.metadata_manager = MetadataManager()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("TestCaseAPIService initialized successfully")
    
    # Test Case Generator Methods
    def generate_test_case(self, scenario: Dict[str, Any], output_path: str = None, 
                           created_by: str = None) -> Dict[str, Any]:
        """
        Generate a test case from a scenario.
        
        Args:
            scenario (Dict[str, Any]): The test scenario data.
            output_path (str, optional): Path to save the generated test case.
            created_by (str, optional): Person creating the test case.
            
        Returns:
            Dict[str, Any]: Result containing test case data and output path.
            
        Raises:
            Exception: If test case generation fails.
        """
        try:
            # Generate test case
            test_case_df = self.test_case_generator.generate_test_case_from_scenario(scenario)
            
            result = {
                "test_case": test_case_df.to_dict('records'),
                "output_path": None
            }
            
            # Save to file if output path provided
            if output_path:
                output_path = self.test_case_generator.save_test_case_to_excel(test_case_df, output_path)
                result["output_path"] = output_path
                
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
                    self.metadata_manager.create_test_case_metadata(test_case_data, created_by=created_by)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate test case: {str(e)}")
            raise
    
    def generate_test_cases_batch(self, scenarios: List[Dict[str, Any]], 
                                 output_dir: str = None) -> Dict[str, Any]:
        """
        Generate multiple test cases from scenarios.
        
        Args:
            scenarios (List[Dict[str, Any]]): List of test scenarios.
            output_dir (str, optional): Directory to save generated test cases.
            
        Returns:
            Dict[str, Any]: Result containing scenario IDs and output files.
            
        Raises:
            Exception: If batch generation fails.
        """
        try:
            # Generate test cases
            test_cases = self.test_case_generator.generate_test_cases_batch(scenarios)
            
            result = {
                "scenario_ids": list(test_cases.keys()),
                "output_files": []
            }
            
            # Save to files if output directory provided
            if output_dir:
                output_files = []
                for scenario_id, test_case_df in test_cases.items():
                    output_filename = f"TestCase_{scenario_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    self.test_case_generator.save_test_case_to_excel(test_case_df, output_path)
                    output_files.append(output_path)
                
                result["output_files"] = output_files
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate test cases batch: {str(e)}")
            raise
    
    def process_scenario_file(self, scenario_file_path: str, 
                            output_dir: str = None) -> Dict[str, Any]:
        """
        Process a scenario file to generate test cases.
        
        Args:
            scenario_file_path (str): Path to the scenario file.
            output_dir (str, optional): Directory to save generated test cases.
            
        Returns:
            Dict[str, Any]: Result containing output files.
            
        Raises:
            Exception: If processing fails.
        """
        try:
            # Process the scenario file
            output_files = self.test_case_generator.process_scenario_file(scenario_file_path, output_dir)
            
            return {
                "output_files": output_files
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process scenario file: {str(e)}")
            raise


    # Test Case Refiner Methods
    def refine_test_case(self, test_case_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Analyze and refine a test case.
        
        Args:
            test_case_path (str): Path to the test case file.
            output_path (str, optional): Path to save analysis results.
            
        Returns:
            Dict[str, Any]: Refinement suggestions and analysis results.
            
        Raises:
            Exception: If refinement fails.
        """
        try:
            # Analyze the test case
            analysis_results = self.test_case_refiner.suggest_refinements(test_case_path)
            
            # Get summary
            summary = self.test_case_refiner.get_refinement_summary(analysis_results)
            
            # Save analysis results if output path provided
            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(analysis_results, f, indent=2)
            
            return {
                "test_case_info": analysis_results["test_case_info"],
                "summary": summary,
                "step_suggestions": analysis_results["step_suggestions"],
                "missing_test_variations": analysis_results["missing_test_variations"],
                "general_suggestions": analysis_results["general_suggestions"],
                "output_path": output_path
            }
            
        except Exception as e:
            self.logger.error(f"Failed to refine test case: {str(e)}")
            raise
    
    def apply_refinements(self, test_case_path: str, refinements: Dict[str, Any], 
                        output_path: str = None) -> Dict[str, Any]:
        """
        Apply refinements to a test case.
        
        Args:
            test_case_path (str): Path to the test case file.
            refinements (Dict[str, Any]): Refinement data to apply.
            output_path (str, optional): Path to save the refined file.
            
        Returns:
            Dict[str, Any]: Result containing refined file path.
            
        Raises:
            Exception: If applying refinements fails.
        """
        try:
            # Apply refinements
            refined_path = self.test_case_refiner.apply_refinements(test_case_path, refinements, output_path)
            
            return {
                "refined_path": refined_path
            }
            
        except Exception as e:
            self.logger.error(f"Failed to apply refinements: {str(e)}")
            raise
    
    # Version Controller Methods
    def check_in_new_version(self, test_case_path: str, change_comment: str = None, 
                          changed_by: str = None, notify_owner: bool = True) -> Dict[str, Any]:
        """
        Check in a new version of a test case.
        
        Args:
            test_case_path (str): Path to the test case file.
            change_comment (str, optional): Comment describing the changes.
            changed_by (str, optional): Name/ID of the person who made the changes.
            notify_owner (bool, optional): Whether to notify the test case owner.
            
        Returns:
            Dict[str, Any]: Result of the check-in operation.
            
        Raises:
            Exception: If check-in fails.
        """
        try:
            # Check in the new version
            result = self.version_controller.check_in_new_version(
                test_case_path,
                change_comment=change_comment,
                changed_by=changed_by,
                notify_owner=notify_owner
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to check in new version: {str(e)}")
            raise
    
    def get_version_history(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get the version history for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: Version history for the test case.
            
        Raises:
            Exception: If retrieving history fails.
        """
        try:
            # Get version history
            history = self.version_controller.get_version_history(test_case_id)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get version history: {str(e)}")
            raise
    
    def get_test_case_version(self, test_case_id: str, version: str = None) -> pd.DataFrame:
        """
        Get a specific version of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            version (str, optional): The version to retrieve. If None, gets the current version.
            
        Returns:
            pd.DataFrame: The test case DataFrame for the specified version.
            
        Raises:
            Exception: If retrieving version fails.
        """
        try:
            # Get the test case version
            test_case_df = self.version_controller.get_test_case_version(test_case_id, version)
            
            return test_case_df
            
        except Exception as e:
            self.logger.error(f"Failed to get test case version: {str(e)}")
            raise
    
    def compare_versions(self, test_case_id: str, version1: str, version2: str) -> Dict[str, Any]:
        """
        Compare two versions of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            version1 (str): First version to compare.
            version2 (str): Second version to compare.
            
        Returns:
            Dict[str, Any]: Comparison results.
            
        Raises:
            Exception: If comparison fails.
        """
        try:
            # Compare versions
            comparison = self.version_controller.compare_versions(test_case_id, version1, version2)
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare versions: {str(e)}")
            raise
    
    def upload_to_sharepoint(self, test_case_id: str, version: str = None, 
                          sharepoint_folder: str = None) -> Dict[str, Any]:
        """
        Upload a test case version to SharePoint.
        
        Args:
            test_case_id (str): The test case ID.
            version (str, optional): The version to upload.
            sharepoint_folder (str, optional): The SharePoint folder path.
            
        Returns:
            Dict[str, Any]: Upload result.
            
        Raises:
            Exception: If upload fails.
        """
        try:
            # Upload to SharePoint
            result = self.version_controller.upload_to_sharepoint(
                test_case_id,
                version=version,
                sharepoint_folder=sharepoint_folder
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to upload to SharePoint: {str(e)}")
            raise
    
    def update_test_case_status(self, test_case_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update the status of a test case.
        
        Args:
            test_case_id (str): The test case ID.
            new_status (str): The new status ("Under Maintenance" or "Active").
            
        Returns:
            Dict[str, Any]: Result of the status update.
            
        Raises:
            Exception: If update fails.
        """
        try:
            # Update status
            if new_status == "Under Maintenance":
                result = self.version_controller.mark_as_under_maintenance(test_case_id)
            elif new_status == "Active":
                result = self.version_controller.mark_as_active(test_case_id)
            else:
                raise ValueError("Invalid status. Must be 'Under Maintenance' or 'Active'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to update test case status: {str(e)}")
            raise

    # Metadata Manager Methods
    def get_test_case_metadata(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get metadata for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            Dict[str, Any]: The metadata, or None if not found.
            
        Raises:
            Exception: If retrieving metadata fails.
        """
        try:
            # Get metadata
            metadata = self.metadata_manager.get_test_case_metadata(test_case_id)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to get test case metadata: {str(e)}")
            raise
    
    def create_test_case_metadata(self, test_case_data: Dict[str, Any], 
                                created_by: str = None) -> str:
        """
        Create metadata for a new test case.
        
        Args:
            test_case_data (Dict[str, Any]): Basic test case data.
            created_by (str, optional): Person creating the test case.
            
        Returns:
            str: The TEST_CASE_ID of the created metadata.
            
        Raises:
            Exception: If metadata creation fails.
        """
        try:
            # Create metadata
            test_case_id = self.metadata_manager.create_test_case_metadata(
                test_case_data,
                created_by=created_by
            )
            
            return test_case_id
            
        except Exception as e:
            self.logger.error(f"Failed to create test case metadata: {str(e)}")
            raise
    
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
            Exception: If metadata update fails.
        """
        try:
            # Update metadata
            updated_metadata = self.metadata_manager.update_test_case_metadata(
                test_case_id,
                updates,
                modified_by=modified_by
            )
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to update test case metadata: {str(e)}")
            raise
    
    def delete_test_case_metadata(self, test_case_id: str) -> bool:
        """
        Delete metadata for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            
        Returns:
            bool: True if successful, False otherwise.
            
        Raises:
            Exception: If metadata deletion fails.
        """
        try:
            # Delete metadata
            success = self.metadata_manager.delete_test_case_metadata(test_case_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete test case metadata: {str(e)}")
            raise
    
    def search_test_cases(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for test cases based on metadata criteria.
        
        Args:
            criteria (Dict[str, Any]): Search criteria.
            
        Returns:
            List[Dict[str, Any]]: List of matching test case metadata.
            
        Raises:
            Exception: If search fails.
        """
        try:
            # Search test cases
            results = self.metadata_manager.search_test_cases(criteria)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search test cases: {str(e)}")
            raise
    
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
            Exception: If update fails.
        """
        try:
            # Update owner
            updated_metadata = self.metadata_manager.update_test_case_owner(
                test_case_id,
                new_owner,
                modified_by=modified_by
            )
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to update test case owner: {str(e)}")
            raise
    
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
            Exception: If update fails.
        """
        try:
            # Update automation status
            updated_metadata = self.metadata_manager.update_automation_status(
                test_case_id,
                new_status,
                modified_by=modified_by
            )
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to update automation status: {str(e)}")
            raise
    
    def update_test_execution_result(self, test_case_id: str, result: str, 
                               executed_by: str = None) -> Dict[str, Any]:
        """
        Update the test execution result for a test case.
        
        Args:
            test_case_id (str): The test case ID.
            result (str): The execution result.
            executed_by (str, optional): Person who executed the test.
            
        Returns:
            Dict[str, Any]: The updated metadata.
            
        Raises:
            Exception: If update fails.
        """
        try:
            # Update execution result
            updated_metadata = self.metadata_manager.update_test_execution_result(
                test_case_id,
                result,
                executed_by=executed_by
            )
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to update execution result: {str(e)}")
            raise
    
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
            Exception: If update fails.
        """
        try:
            # Add tags
            updated_metadata = self.metadata_manager.add_tags_to_test_case(
                test_case_id,
                tags,
                modified_by=modified_by
            )
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to add tags to test case: {str(e)}")
            raise
    
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
            Exception: If update fails.
        """
        try:
            # Remove tags
            updated_metadata = self.metadata_manager.remove_tags_from_test_case(
                test_case_id,
                tags,
                modified_by=modified_by
            )
            
            return updated_metadata
            
        except Exception as e:
            self.logger.error(f"Failed to remove tags from test case: {str(e)}")
            raise
    
    def get_all_tags(self) -> List[str]:
        """
        Get all tags used across test cases.
        
        Returns:
            List[str]: List of unique tags.
            
        Raises:
            Exception: If retrieving tags fails.
        """
        try:
            # Get all tags
            tags = self.metadata_manager.get_all_tags()
            
            return tags
            
        except Exception as e:
            self.logger.error(f"Failed to get all tags: {str(e)}")
            raise
    
    def export_metadata_to_json(self, output_path: str, 
                             test_case_ids: List[str] = None) -> int:
        """
        Export test case metadata to a JSON file.
        
        Args:
            output_path (str): Path to save the JSON file.
            test_case_ids (List[str], optional): Specific test cases to export.
            
        Returns:
            int: Number of test cases exported.
            
        Raises:
            Exception: If export fails.
        """
        try:
            # Export metadata
            count = self.metadata_manager.export_metadata_to_json(output_path, test_case_ids)
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to export metadata to JSON: {str(e)}")
            raise
    
    def import_metadata_from_json(self, input_path: str, overwrite: bool = False) -> int:
        """
        Import test case metadata from a JSON file.
        
        Args:
            input_path (str): Path to the JSON file.
            overwrite (bool, optional): Whether to overwrite existing metadata.
            
        Returns:
            int: Number of test cases imported.
            
        Raises:
            Exception: If import fails.
        """
        try:
            # Import metadata
            count = self.metadata_manager.import_metadata_from_json(input_path, overwrite)
            
            return count
            
        except Exception as e:
            self.logger.error(f"Failed to import metadata from JSON: {str(e)}")
            raise

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

# Create a global API service instance that can be used by external code
api_service = None

def get_api_service():
    """
    Get the API service instance.
    
    Returns:
        TestCaseAPIService: The API service instance.
    """
    global api_service
    
    if api_service is None:
        api_service = TestCaseAPIService()
    
    return api_service

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
    try:
        # Try to get the API service to check if components can be initialized
        service = get_api_service()
        is_healthy = service is not None
        
        response = {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "test_case_generator": hasattr(service, "test_case_generator") and service.test_case_generator is not None,
                "test_case_refiner": hasattr(service, "test_case_refiner") and service.test_case_refiner is not None,
                "version_controller": hasattr(service, "version_controller") and service.version_controller is not None,
                "metadata_manager": hasattr(service, "metadata_manager") and service.metadata_manager is not None
            }
        }
        
        return response, 200 if is_healthy else 503
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503

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
        created_by = request_data.get('created_by')
        
        # Generate test case using the API service
        service = get_api_service()
        result = service.generate_test_case(scenario, output_path, created_by)
        
        # Return the test case data
        return {
            "status": "success",
            "message": "Test case generated successfully",
            "data": result
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
        
        # Generate test cases using the API service
        service = get_api_service()
        result = service.generate_test_cases_batch(scenarios, output_dir)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Generated {len(result['scenario_ids'])} test cases",
            "data": result
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
        
        # Process the scenario file using the API service
        service = get_api_service()
        result = service.process_scenario_file(scenario_file_path, output_dir)
        
        # Return the result
        return {
            "status": "success",
            "message": f"Generated {len(result['output_files'])} test case files",
            "data": result
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
        
        # Analyze the test case using the API service
        service = get_api_service()
        result = service.refine_test_case(test_case_path, output_path)
        
        # Return the analysis results
        return {
            "status": "success",
            "message": "Test case analyzed successfully",
            "data": result
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
        
        # Apply refinements using the API service
        service = get_api_service()
        result = service.apply_refinements(test_case_path, refinements, output_path)
        
        # Return the result
        return {
            "status": "success",
            "message": "Refinements applied successfully",
            "data": result
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
        
        # Check in the new version using the API service
        service = get_api_service()
        result = service.check_in_new_version(
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
        # Get version history using the API service
        service = get_api_service()
        history = service.get_version_history(test_case_id)
        
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
        
        # Get the test case version using the API service
        service = get_api_service()
        test_case_df = service.get_test_case_version(test_case_id, version)
        
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
