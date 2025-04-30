"""
Test Execution Module for watsonx-ipg-testing platform.

This module provides a Streamlit UI for initiating and monitoring test executions.
Key features:
- Select test cases for execution from SharePoint or local upload
- Choose execution mode (manual/automated) and execution engine (RPA/UFT)
- Configure automated execution options
- Set up manual execution assignments
- Display execution dashboard with status
- Allow actions on execution runs (view details, abort, analyze)
- Provide interface for uploading manual test results

Author: Development Team
Date: April 27, 2025
"""

import os
import io
import datetime
import uuid
import json
import pandas as pd
import streamlit as st
import requests
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Tuple, Optional

# Import modules that will be developed separately
# These imports will work once those modules are implemented
try:
    # SharePoint connector
    from src.phase1.sharepoint_connector.sharepoint_auth import SharePointAuth, check_sharepoint_connection
    from src.phase1.sharepoint_connector.document_retriever import DocumentRetriever
    from src.phase1.sharepoint_connector.document_uploader import DocumentUploader
    
    # API integration modules
    from src.phase2.uft_controller.api.uft_api_integrator import UFTApiIntegrator
    from src.phase2.rpa_controller.api.rpa_api_service import RPAApiIntegrator
    
    # Notification service
    from src.phase1.notification_service.notification_manager import NotificationManager
    
    # Database utilities
    from src.common.database.db_utils import connect_to_database, query_database, update_database
    
    # Execution logger
    from src.phase2.execution_logger.execution_tracker import ExecutionTracker
    
    modules_imported = True
except ImportError:
    modules_imported = False
    st.warning("Some modules are not yet implemented. Limited functionality will be available.")




#################### Testing blocl

import streamlit as st
import pandas as pd
import time
import random
from ui_utils import show_info_message, show_success_message, show_error_message
from state_management import add_notification
import mock_services

def show_execution():
    """Display the test execution module UI."""
    st.header("Test Execution Module")
    
    # Create tabs for different functions
    tabs = st.tabs(["Initiate Execution", "Execution Dashboard", "Upload Manual Results"])
    
    with tabs[0]:
        show_initiate_execution()
    
    with tabs[1]:
        show_execution_dashboard()
    
    with tabs[2]:
        show_upload_manual_results()

def show_initiate_execution():
    """Display the initiate execution tab."""
    st.subheader("Initiate Execution")
    
    # Test case selection
    st.markdown("### Select Test Cases")
    
    # Get test cases from session state or mock
    test_cases = st.session_state.get("current_test_cases", mock_services.get_test_cases())
    
    # Create a selection dataframe
    selection_data = [{
        "ID": tc["id"],
        "Title": tc["title"],
        "Type": tc["type"],
        "Owner": tc["owner"],
        "Status": tc["status"]
    } for tc in test_cases if tc["status"] != "Obsolete"]
    
    selection_df = pd.DataFrame(selection_data)
    
    # Display the selection dataframe
    st.dataframe(selection_df, use_container_width=True)
    
    # Multi-select for test cases
    selected_test_cases = st.multiselect(
        "Select Test Cases for Execution",
        options=[tc["id"] for tc in test_cases if tc["status"] != "Obsolete"],
        format_func=lambda x: f"{x}: {next((tc['title'] for tc in test_cases if tc['id'] == x), '')}"
    )
    
    if selected_test_cases:
        st.write(f"Selected {len(selected_test_cases)} test cases for execution.")
        
        # Execution mode selection
        st.markdown("### Execution Mode")
        execution_mode = st.radio(
            "Select Execution Mode",
            ["Automated", "Manual"]
        )
        
        if execution_mode == "Automated":
            st.markdown("### Automated Execution Options")
            
            # Display target controller file
            st.info("Target Controller File: **TestExecutionController.xlsx**")
            st.write("This controller file will be updated with the selected test cases and execution flags.")
            
            # Execute button
            if st.button("Prepare & Run Automated Tests", key="run_automated_button"):
                with st.spinner("Preparing and running automated tests..."):
                    # Simulate processing time
                    time.sleep(3)
                    
                    # Use mock function to simulate execution
                    execution_run = mock_services.execute_test_cases(selected_test_cases, "Automated")
                    
                    # Add to session state for tracking
                    if "execution_runs" not in st.session_state:
                        st.session_state["execution_runs"] = []
                    st.session_state["execution_runs"].append(execution_run)
                    
                    show_success_message(f"Automated test execution initiated! Run ID: {execution_run['id']}")
                    add_notification(f"Started automated execution {execution_run['id']} for {len(selected_test_cases)} test cases", "success")
                    
                    # Navigate to dashboard tab
                    st.session_state["active_execution_tab"] = 1
                    st.experimental_rerun()
        
        else:  # Manual execution
            st.markdown("### Manual Execution Options")
            
            # Tester assignment
            st.write("Assign Tester:")
            tester_options = ["John Doe", "Jane Smith", "Mark Johnson", "Selected Test Case Owners"]
            assigned_tester = st.selectbox("Select Tester", tester_options)
            
            # Notify button
            if st.button("Notify Tester(s) for Manual Execution", key="notify_tester_button"):
                with st.spinner("Sending notifications to testers..."):
                    # Simulate processing time
                    time.sleep(2)
                    
                    # Use mock function to simulate execution setup
                    execution_run = mock_services.execute_test_cases(selected_test_cases, "Manual")
                    
                    # Add to session state for tracking
                    if "execution_runs" not in st.session_state:
                        st.session_state["execution_runs"] = []
                    st.session_state["execution_runs"].append(execution_run)
                    
                    if assigned_tester == "Selected Test Case Owners":
                        show_success_message("Notifications sent to all test case owners for manual execution!")
                    else:
                        show_success_message(f"Notifications sent to {assigned_tester} for manual execution!")
                    
                    add_notification(f"Requested manual execution for {len(selected_test_cases)} test cases", "info")
                    
                    # Navigate to dashboard tab
                    st.session_state["active_execution_tab"] = 1
                    st.experimental_rerun()
    else:
        st.info("Please select at least one test case to execute.")

def show_execution_dashboard():
    """Display the execution dashboard tab."""
    st.subheader("Execution Dashboard")
    
    # Check if we should be on this tab
    if "active_execution_tab" in st.session_state and st.session_state["active_execution_tab"] == 1:
        del st.session_state["active_execution_tab"]
    
    # Get execution runs from session state or mock
    execution_runs = st.session_state.get("execution_runs", mock_services.get_execution_runs())
    
    if execution_runs:
        # Create a dataframe for display
        execution_data = []
        for run in execution_runs:
            execution_data.append({
                "Run ID": run["id"],
                "Status": run["status"],
                "Start Time": run["start_time"][:16].replace("T", " ") if run["start_time"] else "N/A",
                "End Time": run["end_time"][:16].replace("T", " ") if run["end_time"] else "N/A",
                "Progress": "100%" if run["status"] == "Completed" else "Failed" if run["status"] == "Failed" else "In Progress",
                "Pass": run["pass_count"],
                "Fail": run["fail_count"],
                "Blocked": run["blocked_count"]
            })
        
        execution_df = pd.DataFrame(execution_data)
        st.dataframe(execution_df, use_container_width=True)
        
        # Select a run for actions
        selected_run = st.selectbox(
            "Select a Run for Actions",
            options=[run["id"] for run in execution_runs],
            format_func=lambda x: f"{x} ({next((run['status'] for run in execution_runs if run['id'] == x), '')})"
        )
        
        if selected_run:
            st.markdown("### Actions")
            
            selected_run_data = next((run for run in execution_runs if run["id"] == selected_run), None)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("View Details", key="view_details_button"):
                    with st.spinner("Loading execution details..."):
                        # Simulate processing time
                        time.sleep(1)
                        
                        st.session_state["selected_run_details"] = selected_run_data
                        show_info_message("Showing execution details below.")
            
            with col2:
                if selected_run_data["status"] == "In Progress":
                    if st.button("Abort Run", key="abort_run_button"):
                        with st.spinner("Aborting execution run..."):
                            # Simulate processing time
                            time.sleep(2)
                            
                            # Update status
                            for run in execution_runs:
                                if run["id"] == selected_run:
                                    run["status"] = "Aborted"
                            
                            show_success_message(f"Execution run {selected_run} aborted successfully!")
                            add_notification(f"Aborted execution run {selected_run}", "warning")
                            st.experimental_rerun()
                else:
                    st.write("Run is not in progress")
            
            with col3:
                if selected_run_data["status"] in ["Completed", "Failed"]:
                    if selected_run_data["fail_count"] > 0:
                        if st.button("Analyze Failures", key="analyze_failures_button"):
                            with st.spinner("Analyzing failures..."):
                                # Simulate processing time
                                time.sleep(2)
                                
                                st.session_state["analyze_run_id"] = selected_run
                                st.session_state["page"] = "Analysis & Defects"
                                st.experimental_rerun()
                    
                    if st.button("View Report", key="view_report_button"):
                        with st.spinner("Generating report..."):
                            # Simulate processing time
                            time.sleep(2)
                            
                            st.session_state["report_run_id"] = selected_run
                            st.session_state["page"] = "Reporting"
                            st.experimental_rerun()
        
        # Display selected run details if available
        if "selected_run_details" in st.session_state:
            st.markdown("---")
            st.subheader(f"Details for Run: {st.session_state['selected_run_details']['id']}")
            
            # Create some mock detailed results
            detailed_results = []
            run_details = st.session_state["selected_run_details"]
            total_cases = run_details["pass_count"] + run_details["fail_count"] + run_details["blocked_count"]
            
            test_cases = st.session_state.get("current_test_cases", mock_services.get_test_cases())
            
            for i in range(min(total_cases, len(test_cases))):
                tc = test_cases[i]
                
                # Determine result based on counts
                if i < run_details["pass_count"]:
                    result = "Pass"
                elif i < run_details["pass_count"] + run_details["fail_count"]:
                    result = "Fail"
                else:
                    result = "Blocked"
                
                detailed_results.append({
                    "Test Case ID": tc["id"],
                    "Title": tc["title"],
                    "Result": result,
                    "Duration (s)": random.randint(1, 60),
                    "Executed By": "Automation" if tc["type"] == "Automated" else tc["owner"],
                    "Notes": f"Test {result.lower()}ed" if result != "Blocked" else "Test was blocked"
                })
            
            detailed_df = pd.DataFrame(detailed_results)
            st.dataframe(detailed_df, use_container_width=True)
            
            # Clear button
            if st.button("Clear Details", key="clear_details_button"):
                del st.session_state["selected_run_details"]
                st.experimental_rerun()
    else:
        st.info("No execution runs available. Initiate a test execution first.")

def show_upload_manual_results():
    """Display the upload manual results tab."""
    st.subheader("Upload Manual Results")
    
    # Run ID selection
    execution_runs = st.session_state.get("execution_runs", mock_services.get_execution_runs())
    manual_runs = [run for run in execution_runs if "Manual" in run.get("id", "")]
    
    if manual_runs:
        selected_run_id = st.selectbox(
            "Select the Corresponding Test Run ID",
            options=[run["id"] for run in manual_runs],
            format_func=lambda x: f"{x} ({next((run['status'] for run in manual_runs if run['id'] == x), '')})"
        )
        
        # File upload area
        uploaded_files = st.file_uploader(
            "Upload Test Execution Reports",
            type=["xlsx", "pdf", "jpg", "png"],
            accept_multiple_files=True,
            help="Upload Excel reports, PDFs, or screenshots of test results"
        )
        
        if uploaded_files:
            st.write(f"Uploaded {len(uploaded_files)} files:")
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size} bytes)")
            
            # Upload button
            if st.button("Upload Results to SharePoint", key="upload_results_button"):
                with st.spinner("Uploading results to SharePoint..."):
                    # Simulate processing time
                    time.sleep(3)
                    
                    # Update run status
                    for run in execution_runs:
                        if run["id"] == selected_run_id:
                            run["status"] = "Completed"
                            run["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                            # Random results
                            total = sum([run["pass_count"], run["fail_count"], run["blocked_count"]])
                            run["pass_count"] = random.randint(0, total)
                            run["fail_count"] = random.randint(0, total - run["pass_count"])
                            run["blocked_count"] = total - run["pass_count"] - run["fail_count"]
                    
                    show_success_message("Results uploaded to SharePoint successfully!")
                    add_notification(f"Uploaded manual test results for {selected_run_id}", "success")
        else:
            st.info("Please upload at least one file containing test results.")
    else:
        st.info("No manual execution runs available. Initiate a manual test execution first.")

################### Testing block endss here



class ExecutionUI:
    """Main class for the Test Execution UI module."""
    
    def __init__(self):
        """Initialize the ExecutionUI class."""
        load_dotenv()  # Load environment variables from .env file
        
        # SharePoint configuration
        self.sharepoint_url = os.getenv("SHAREPOINT_URL")
        self.sharepoint_client_id = os.getenv("SHAREPOINT_CLIENT_ID")
        self.sharepoint_client_secret = os.getenv("SHAREPOINT_CLIENT_SECRET")
        
        # RPA API configuration
        self.rpa_api_url = os.getenv("RPA_API_URL", "https://rpa-api.example.com")
        self.rpa_api_key = os.getenv("RPA_API_KEY", "")
        
        # UFT API configuration
        self.uft_api_url = os.getenv("UFT_API_URL", "https://uft-api.example.com")
        self.uft_api_key = os.getenv("UFT_API_KEY", "")
        
        # Initialize connections to other modules if they are available
        if modules_imported:
            # SharePoint connector
            self.sp_auth = SharePointAuth(self.sharepoint_url, self.sharepoint_client_id, self.sharepoint_client_secret)
            self.document_retriever = DocumentRetriever(self.sp_auth)
            self.document_uploader = DocumentUploader(self.sp_auth)
            
            # API integration
            self.uft_api = UFTApiIntegrator(self.uft_api_url, self.uft_api_key)
            self.rpa_api = RPAApiIntegrator(self.rpa_api_url, self.rpa_api_key)
            
            # Notification service
            self.notification_manager = NotificationManager()
            
            # Execution tracker
            self.execution_tracker = ExecutionTracker()
        else:
            # Mock API clients for demonstration
            self.uft_api = self._create_mock_uft_api()
            self.rpa_api = self._create_mock_rpa_api()
            
        # Set up session state if not already initialized
        self._initialize_session_state()
    
    def _create_mock_uft_api(self):
        """Create a mock UFT API client for demonstration purposes."""
        class MockUFTApi:
            def create_test_set(self, execution_id, test_cases):
                st.info(f"[MOCK] Creating UFT test set with {len(test_cases)} test cases for execution {execution_id}")
                return True
                
            def add_test_cases_to_queue(self, test_cases, execution_id):
                st.info(f"[MOCK] Adding {len(test_cases)} test cases to UFT queue for execution {execution_id}")
                return True
                
            def execute_tests(self, execution_id):
                st.info(f"[MOCK] Executing UFT tests for execution {execution_id}")
                return True
                
            def abort_execution(self, execution_id):
                st.info(f"[MOCK] Aborting UFT execution {execution_id}")
                return True
                
            def get_execution_status(self, execution_id):
                st.info(f"[MOCK] Getting UFT execution status for {execution_id}")
                return {"status": "In Progress", "progress": 50, "passed": 3, "failed": 1, "pending": 4}
                
            def get_test_results(self, execution_id):
                st.info(f"[MOCK] Getting UFT test results for {execution_id}")
                return {"results": "Mock UFT test results"}
        
        return MockUFTApi()
    
    def _create_mock_rpa_api(self):
        """Create a mock RPA API client for demonstration purposes."""
        class MockRPAApi:
            def update_controller_file(self, controller_file_path, test_cases):
                st.info(f"[MOCK] Updating RPA controller file with {len(test_cases)} test cases")
                return True
                
            def add_test_cases_to_queue(self, test_cases, execution_id):
                st.info(f"[MOCK] Adding {len(test_cases)} test cases to RPA queue for execution {execution_id}")
                return True
                
            def execute_driver_script(self, driver_script_path, execution_id):
                st.info(f"[MOCK] Executing RPA driver script for execution {execution_id}")
                return True
                
            def abort_execution(self, execution_id):
                st.info(f"[MOCK] Aborting RPA execution {execution_id}")
                return True
                
            def get_execution_status(self, execution_id):
                st.info(f"[MOCK] Getting RPA execution status for {execution_id}")
                return {"status": "In Progress", "progress": 60, "passed": 5, "failed": 2, "pending": 3}
                
            def get_execution_log(self, execution_id):
                st.info(f"[MOCK] Getting RPA execution log for {execution_id}")
                return {"log": "Mock RPA execution log"}
        
        return MockRPAApi()
        
    def _initialize_session_state(self):
        """Initialize session state variables for maintaining state between reruns."""
        if 'execution_runs' not in st.session_state:
            st.session_state.execution_runs = []
            
        if 'selected_test_cases' not in st.session_state:
            st.session_state.selected_test_cases = []
            
        if 'current_tab' not in st.session_state:
            st.session_state.current_tab = "Select Test Cases"
            
        if 'sharepoint_folders' not in st.session_state:
            # This would be populated from actual SharePoint folders once connected
            st.session_state.sharepoint_folders = ["Test Cases", "Automation Scripts", "Results"]
    
    def determine_execution_engine(self, test_case: Dict[str, Any]) -> str:
        """
        Determine which execution engine to use (RPA or UFT) based on the test case.
        
        Args:
            test_case: Test case information
            
        Returns:
            String indicating which engine to use: "RPA" or "UFT"
        """
        # This is a placeholder for the decision logic
        # In real implementation, this would analyze the test case metadata
        # and determine which engine is appropriate
        
        # Example decision logic (replace with actual logic):
        # - If test case has a tag or property indicating engine, use that
        # - If test case belongs to certain application/module, choose specific engine
        # - Default to RPA if not specified
        
        # For now, let's use a simple heuristic based on the test case ID pattern
        if "type" in test_case and isinstance(test_case["type"], str):
            if "UFT" in test_case["type"].upper():
                return "UFT"
            elif "RPA" in test_case["type"].upper():
                return "RPA"
        
        if "id" in test_case and isinstance(test_case["id"], str):
            if test_case["id"].startswith("UFT-") or test_case["id"].startswith("QTP-"):
                return "UFT"
            elif test_case["id"].startswith("RPA-") or test_case["id"].startswith("AA-"):
                return "RPA"
        
        # Default to RPA if no clear indicator
        # This should be updated based on project requirements
        return "RPA"
    
    def fetch_test_cases_from_sharepoint(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Fetch test cases from SharePoint folder.
        
        Args:
            folder_path: Path to SharePoint folder
            
        Returns:
            List of test cases with metadata
        """
        if not modules_imported:
            # Mock data for demonstration purposes
            return [
                {"id": f"RPA-{i}", "name": f"Test Login Functionality {i}", "type": "RPA Automated" if i % 3 == 0 else "Manual", 
                 "path": f"{folder_path}/Test Case {i}.xlsx", "last_executed": "2025-04-20", 
                 "last_status": "Passed" if i % 4 != 0 else "Failed"} 
                for i in range(1, 6)
            ] + [
                {"id": f"UFT-{i}", "name": f"Test Data Validation {i}", "type": "UFT Automated" if i % 3 == 0 else "Manual", 
                 "path": f"{folder_path}/Test Case {i+5}.xlsx", "last_executed": "2025-04-21", 
                 "last_status": "Passed" if i % 4 != 0 else "Failed"} 
                for i in range(1, 6)
            ]
        
        try:
            # When the SharePoint connector modules are implemented, this would use actual retrieval
            test_cases = self.document_retriever.get_files_in_folder(folder_path, file_extension=".xlsx")
            processed_test_cases = []
            
            for test_case in test_cases:
                # Process test case metadata and content
                file_content = self.document_retriever.download_file(test_case["file_path"])
                df = pd.read_excel(file_content)
                
                # Extract basic metadata
                test_case_info = {
                    "id": test_case.get("id", "Unknown"),
                    "name": test_case.get("name", "Unknown Test Case"),
                    "type": self._determine_test_case_type(df),
                    "path": test_case["file_path"],
                    "last_executed": test_case.get("last_modified", "Never"),
                    "last_status": "Not Executed"
                }
                processed_test_cases.append(test_case_info)
                
            return processed_test_cases
        except Exception as e:
            st.error(f"Error fetching test cases from SharePoint: {str(e)}")
            return []
    
    def _determine_test_case_type(self, test_case_df: pd.DataFrame) -> str:
        """
        Determine the type of test case based on the content of the Excel file.
        
        Args:
            test_case_df: DataFrame containing test case data
            
        Returns:
            String indicating the test case type (e.g., "Manual", "RPA Automated", "UFT Automated")
        """
        # Check if TYPE column exists
        if "TYPE" not in test_case_df.columns:
            return "Manual"  # Default to Manual if TYPE column doesn't exist
        
        # Get the first non-null value in the TYPE column
        types = test_case_df["TYPE"].dropna().astype(str).str.upper().tolist()
        
        if not types:
            return "Manual"  # Default to Manual if no type specified
        
        # Check for UFT indicators
        if any("UFT" in t for t in types) or any("QTP" in t for t in types):
            return "UFT Automated"
        
        # Check for RPA indicators
        if any("RPA" in t for t in types) or any("AUTOMATION ANYWHERE" in t for t in types) or any("AA" in t for t in types):
            return "RPA Automated"
        
        # Check for general automation indicators
        if any("AUTOMATED" in t for t in types) or any("AUTOMATION" in t for t in types):
            return "Automated"  # Generic automated type
        
        # Default to Manual
        return "Manual"
    
    def parse_excel_test_case(self, file_content) -> pd.DataFrame:
        """
        Parse Excel test case file into a DataFrame.
        
        Args:
            file_content: Content of the Excel file
            
        Returns:
            DataFrame containing test case data
        """
        try:
            df = pd.read_excel(file_content)
            
            # Check for expected columns
            expected_columns = [
                "SUBJECT", "TEST CASE", "TEST CASE NUMBER", "STEP NO", 
                "TEST STEP DESCRIPTION", "DATA", "REFERENCE VALUES", "VALUES", 
                "EXPECTED RESULT", "TRANS CODE", "TEST USER ID/ROLE", "STATUS", "TYPE"
            ]
            
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                st.warning(f"Warning: The following expected columns are missing: {', '.join(missing_columns)}")
            
            return df
        except Exception as e:
            st.error(f"Error parsing Excel file: {str(e)}")
            return pd.DataFrame()
    
    def execute_automated_tests(self, test_cases: List[Dict[str, Any]], execution_type: str = "RPA") -> str:
        """
        Execute automated tests using the appropriate API.
        
        Args:
            test_cases: List of test cases to execute
            execution_type: Type of execution ("RPA" or "UFT")
            
        Returns:
            Execution ID for the run
        """
        execution_id = str(uuid.uuid4())
        
        # Create execution run record
        execution_run = {
            "id": execution_id,
            "status": "In Progress",
            "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": "",
            "test_cases": test_cases,
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "pending": len(test_cases),
            "progress": 0,
            "execution_type": execution_type
        }
        
        try:
            if execution_type == "RPA":
                # RPA execution via API
                
                # 1. Update controller file with selected test cases
                controller_file_path = "path/to/rpa/controller.xlsx"  # Should come from configuration
                self.rpa_api.update_controller_file(controller_file_path, test_cases)
                
                # 2. Add test cases to execution queue
                self.rpa_api.add_test_cases_to_queue(test_cases, execution_id)
                
                # 3. Execute driver script
                driver_script_path = "path/to/rpa/driver.vbs"  # Should come from configuration
                self.rpa_api.execute_driver_script(driver_script_path, execution_id)
                
            elif execution_type == "UFT":
                # UFT execution via API
                
                # 1. Prepare UFT test set
                self.uft_api.create_test_set(execution_id, test_cases)
                
                # 2. Add test cases to UFT queue
                self.uft_api.add_test_cases_to_queue(test_cases, execution_id)
                
                # 3. Execute tests via UFT API
                self.uft_api.execute_tests(execution_id)
            
            # Register execution with tracker if available
            if modules_imported:
                self.execution_tracker.register_execution(execution_id, execution_run)
            
            # Add to session state
            st.session_state.execution_runs.append(execution_run)
            
            return execution_id
        except Exception as e:
            st.error(f"Error executing {execution_type} tests: {str(e)}")
            return ""
    
    def notify_manual_testers(self, test_cases: List[Dict[str, Any]], testers: List[str]) -> bool:
        """
        Notify testers about manual test execution.
        
        Args:
            test_cases: List of test cases to execute manually
            testers: List of tester email addresses
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not modules_imported:
            # Mock notification for demonstration
            st.info(f"Simulating notification to testers: {', '.join(testers)}")
            return True
        
        try:
            # When notification service is implemented
            subject = "Manual Test Execution Assignment"
            message = f"""
            You have been assigned the following test cases for manual execution:
            
            {', '.join([f"{tc['id']} - {tc['name']}" for tc in test_cases])}
            
            Please execute these tests and upload the results through the Testing Platform.
            """
            
            self.notification_manager.send_email_notification(
                recipients=testers,
                subject=subject,
                message=message,
                priority="High"
            )
            return True
        except Exception as e:
            st.error(f"Error notifying testers: {str(e)}")
            return False
    
    def abort_test_execution(self, execution_id: str) -> bool:
        """
        Abort an ongoing test execution.
        
        Args:
            execution_id: ID of the execution run to abort
            
        Returns:
            True if abort was successful, False otherwise
        """
        try:
            # Find the execution run
            execution_run = None
            for i, run in enumerate(st.session_state.execution_runs):
                if run["id"] == execution_id and run["status"] == "In Progress":
                    execution_run = run
                    break
            
            if not execution_run:
                st.error("Execution run not found or not in progress")
                return False
            
            # Abort based on execution type
            if execution_run.get("execution_type") == "UFT":
                self.uft_api.abort_execution(execution_id)
            else:  # Default to RPA
                self.rpa_api.abort_execution(execution_id)
            
            # Update execution run status
            for i, run in enumerate(st.session_state.execution_runs):
                if run["id"] == execution_id and run["status"] == "In Progress":
                    st.session_state.execution_runs[i]["status"] = "Aborted"
                    st.session_state.execution_runs[i]["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    break
                    
            return True
        except Exception as e:
            st.error(f"Error aborting test execution: {str(e)}")
            return False
    
    def update_execution_status(self):
        """Update status of ongoing execution runs by polling the APIs."""
        # In a mock implementation, we'll simulate progress
        # In a real implementation, this would poll the RPA and UFT APIs
        
        for i, run in enumerate(st.session_state.execution_runs):
            if run["status"] == "In Progress":
                execution_type = run.get("execution_type", "RPA")
                
                try:
                    # Get status from appropriate API
                    if execution_type == "UFT":
                        status_info = self.uft_api.get_execution_status(run["id"])
                    else:  # Default to RPA
                        status_info = self.rpa_api.get_execution_status(run["id"])
                    
                    # Update run with status information
                    if status_info:
                        st.session_state.execution_runs[i]["progress"] = status_info.get("progress", run["progress"])
                        st.session_state.execution_runs[i]["passed"] = status_info.get("passed", run["passed"])
                        st.session_state.execution_runs[i]["failed"] = status_info.get("failed", run["failed"])
                        st.session_state.execution_runs[i]["pending"] = status_info.get("pending", run["pending"])
                        
                        # If status indicates completion, update accordingly
                        if status_info.get("status") in ["Completed", "Aborted", "Failed"]:
                            st.session_state.execution_runs[i]["status"] = status_info["status"]
                            st.session_state.execution_runs[i]["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                except Exception as e:
                    # Log error but continue processing other runs
                    print(f"Error updating status for execution {run['id']}: {str(e)}")
                    
                    # For demonstration, simulate progress in case of API error
                    current_progress = run["progress"]
                    if current_progress < 100:
                        new_progress = min(current_progress + 10, 100)
                        st.session_state.execution_runs[i]["progress"] = new_progress
                        
                        # Update pass/fail counts based on progress
                        total = run["total_tests"]
                        completed = int(total * new_progress / 100)
                        # Simulate 70% pass rate
                        passed = int(completed * 0.7)
                        failed = completed - passed
                        pending = total - completed
                        
                        st.session_state.execution_runs[i]["passed"] = passed
                        st.session_state.execution_runs[i]["failed"] = failed
                        st.session_state.execution_runs[i]["pending"] = pending
                        
                        # Mark as completed if progress reaches 100%
                        if new_progress == 100:
                            st.session_state.execution_runs[i]["status"] = "Completed"
                            st.session_state.execution_runs[i]["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def show(self):
        """Display the Test Execution UI."""
        # Update execution status (mock implementation)
        self.update_execution_status()
        
        # Create the main layout
        st.title("Test Execution Module")
        
        # Create tabs for different sections of the execution module
        tabs = ["Select Test Cases", "Execution Dashboard", "Upload Manual Results"]
        
        # Use horizontal radio buttons for tabs
        st.session_state.current_tab = st.radio("", tabs, horizontal=True, index=tabs.index(st.session_state.current_tab))
        
        # Display the selected tab content
        if st.session_state.current_tab == "Select Test Cases":
            self._show_test_case_selection()
        elif st.session_state.current_tab == "Execution Dashboard":
            self._show_execution_dashboard()
        elif st.session_state.current_tab == "Upload Manual Results":
            self._show_manual_results_upload()
    
    def _show_test_case_selection(self):
        """Display the test case selection interface."""
        st.subheader("Select Test Cases for Execution")
        
        # Create two columns for the layout
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Source selection
            source = st.radio(
                "Select Test Case Source",
                ["SharePoint", "Upload Excel File"]
            )
            
            if source == "SharePoint":
                # SharePoint connection check
                if modules_imported:
                    connection_status = check_sharepoint_connection(
                        self.sharepoint_url, 
                        self.sharepoint_client_id, 
                        self.sharepoint_client_secret
                    )
                    
                    if connection_status:
                        st.success("Connected to SharePoint")
                    else:
                        st.error("Failed to connect to SharePoint")
                        st.info("Check .env file for correct SharePoint credentials")
                        return
                else:
                    st.info("SharePoint connection module not yet implemented")
                    st.success("Using mock SharePoint connection for demonstration")
                
                # Folder selection
                selected_folder = st.selectbox(
                    "Select SharePoint Folder",
                    st.session_state.sharepoint_folders
                )
                
                if st.button("Fetch Test Cases"):
                    with st.spinner("Fetching test cases from SharePoint..."):
                        test_cases = self.fetch_test_cases_from_sharepoint(selected_folder)
                        st.session_state.available_test_cases = test_cases
                        st.success(f"Found {len(test_cases)} test cases")
                
            else:  # Upload Excel File
                uploaded_file = st.file_uploader(
                    "Upload Test Case Excel File",
                    type=["xlsx", "xls"],
                    help="Upload an Excel file containing test cases"
                )
                
                if uploaded_file is not None:
                    with st.spinner("Processing uploaded file..."):
                        df = self.parse_excel_test_case(uploaded_file)
                        
                        if not df.empty:
                            # Extract unique test cases from the file
                            test_cases = []
                            for test_num in df["TEST CASE NUMBER"].unique():
                                subset = df[df["TEST CASE NUMBER"] == test_num]
                                test_case_type = "Manual"
                                
                                # Extract type if available
                                if "TYPE" in subset.columns:
                                    type_value = subset["TYPE"].iloc[0]
                                    if isinstance(type_value, str):
                                        type_value = type_value.upper()
                                        if "UFT" in type_value or "QTP" in type_value:
                                            test_case_type = "UFT Automated"
                                        elif "RPA" in type_value or "AA" in type_value:
                                            test_case_type = "RPA Automated"
                                        elif "AUTOMATED" in type_value:
                                            test_case_type = "Automated"
                                
                                test_cases.append({
                                    "id": test_num,
                                    "name": subset["TEST CASE"].iloc[0] if "TEST CASE" in subset.columns else f"Test Case {test_num}",
                                    "type": test_case_type,
                                    "path": uploaded_file.name,
                                    "last_executed": "Never",
                                    "last_status": "Not Executed"
                                })
                            
                            st.session_state.available_test_cases = test_cases
                            st.success(f"Processed {len(test_cases)} test cases from file")
        
        with col2:
            # Display available test cases if they exist
            if "available_test_cases" in st.session_state and st.session_state.available_test_cases:
                st.subheader("Available Test Cases")
                
                # Create a DataFrame for display
                test_case_df = pd.DataFrame(st.session_state.available_test_cases)
                
                # Filter options
                tc_types = ["All"] + sorted(test_case_df["type"].unique().tolist())
                selected_type = st.selectbox("Filter by Type", tc_types)
                
                # Apply filters
                filtered_df = test_case_df
                if selected_type != "All":
                    filtered_df = test_case_df[test_case_df["type"] == selected_type]
                
                # Display filtered test cases
                st.dataframe(filtered_df)
                
                # Add selection column for multi-select
                selection = st.multiselect(
                    "Select Test Cases for Execution",
                    options=filtered_df["id"].tolist(),
                    format_func=lambda x: f"{x} - {filtered_df[filtered_df['id'] == x]['name'].iloc[0]}"
                )
                
                # Filter and display selected test cases
                if selection:
                    st.session_state.selected_test_cases = [
                        tc for tc in st.session_state.available_test_cases if tc["id"] in selection
                    ]
                    
                    # Display selected test cases
                    st.write(f"Selected {len(selection)} test cases for execution")
                    
                    # Determine test case types
                    selected_types = set(tc["type"] for tc in st.session_state.selected_test_cases)
                    has_manual = any("MANUAL" in tc["type"].upper() for tc in st.session_state.selected_test_cases)
                    has_rpa = any("RPA" in tc["type"].upper() for tc in st.session_state.selected_test_cases)
                    has_uft = any("UFT" in tc["type"].upper() for tc in st.session_state.selected_test_cases)
                    has_generic_automated = any(
                        "AUTOMATED" in tc["type"].upper() and "RPA" not in tc["type"].upper() and "UFT" not in tc["type"].upper() 
                        for tc in st.session_state.selected_test_cases
                    )
                    
                    # Show execution configuration options
                    st.subheader("Execution Configuration")
                    
                    # Set execution mode options based on selection
                    exec_mode_options = []
                    if has_manual:
                        exec_mode_options.append("Manual Only")
                    
                    if has_rpa or has_uft or has_generic_automated:
                        exec_mode_options.append("Automated Only")
                    
                    if has_manual and (has_rpa or has_uft or has_generic_automated):
                        exec_mode_options.append("Both Manual and Automated")
                    
                    execution_mode = st.radio(
                        "Select Execution Mode",
                        options=exec_mode_options
                    )
                    
                    # Show execution engine selection if there are automated tests
                    execution_engine = None
                    if "Automated" in execution_mode:
                        # Determine which engines are available
                        engine_options = []
                        if has_rpa:
                            engine_options.append("RPA Only")
                        if has_uft:
                            engine_options.append("UFT Only")
                        if has_generic_automated:
                            engine_options.extend(["RPA Only", "UFT Only"])
                        if len(engine_options) > 1:
                            engine_options.append("Auto-detect (Recommended)")
                        
                        if engine_options:
                            execution_engine = st.radio(
                                "Select Execution Engine for Automated Tests",
                                options=engine_options
                            )
                    
                    # Show configuration based on execution mode and engine
                    if "Automated" in execution_mode:
                        st.subheader("Automated Execution Settings")
                        
                        if "RPA" in execution_engine or "Auto-detect" in execution_engine:
                            with st.expander("RPA Execution Configuration", expanded="Only" in execution_engine):
                                st.info("RPA Controller file will be updated with selected test cases")
                                
                                # Mock controller file path (would come from configuration)
                                rpa_controller_file = st.text_input(
                                    "RPA Controller File Path",
                                    value="path/to/rpa/controller.xlsx",
                                    disabled=True,
                                    key="rpa_controller_file"
                                )
                                
                                # Mock driver script path (would come from configuration)
                                rpa_driver_script = st.text_input(
                                    "RPA Driver Script Path",
                                    value="path/to/rpa/driver.vbs",
                                    disabled=True,
                                    key="rpa_driver_script"
                                )
                        
                        if "UFT" in execution_engine or "Auto-detect" in execution_engine:
                            with st.expander("UFT Execution Configuration", expanded="Only" in execution_engine):
                                st.info("UFT Test cases will be executed via the UFT API")
                                
                                # Mock UFT environment selection
                                uft_environment = st.selectbox(
                                    "Select UFT Environment",
                                    ["Development", "Test", "Staging", "Production"],
                                    key="uft_environment"
                                )
                                
                                # Mock UFT test set configuration
                                uft_test_set_name = st.text_input(
                                    "UFT Test Set Name",
                                    value=f"Generated_TestSet_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    key="uft_test_set_name"
                                )
                    
                    if "Manual" in execution_mode:
                        st.subheader("Manual Execution Settings")
                        
                        # Define testers to notify
                        testers = st.text_area(
                            "Tester Email Addresses (one per line)",
                            "tester1@example.com\ntester2@example.com"
                        )
                        
                        tester_list = [email.strip() for email in testers.split("\n") if email.strip()]
                    
                    # Add execution button
                    if st.button("Start Execution"):
                        # Process automated tests if applicable
                        if "Automated" in execution_mode:
                            # Extract automated test cases
                            rpa_test_cases = []
                            uft_test_cases = []
                            generic_test_cases = []
                            
                            for tc in st.session_state.selected_test_cases:
                                tc_type = tc["type"].upper()
                                if "MANUAL" not in tc_type:
                                    if "RPA" in tc_type:
                                        rpa_test_cases.append(tc)
                                    elif "UFT" in tc_type or "QTP" in tc_type:
                                        uft_test_cases.append(tc)
                                    elif "AUTOMATED" in tc_type:
                                        generic_test_cases.append(tc)
                            
                            # Determine which engine to use for generic automated tests
                            if generic_test_cases:
                                if execution_engine == "RPA Only":
                                    rpa_test_cases.extend(generic_test_cases)
                                elif execution_engine == "UFT Only":
                                    uft_test_cases.extend(generic_test_cases)
                                else:  # Auto-detect
                                    # Split generic tests between RPA and UFT based on simple heuristic
                                    for i, tc in enumerate(generic_test_cases):
                                        if i % 2 == 0:  # Simple alternating assignment
                                            rpa_test_cases.append(tc)
                                        else:
                                            uft_test_cases.append(tc)
                            
                            # Execute RPA tests if any
                            if rpa_test_cases and ("RPA" in execution_engine or "Auto-detect" in execution_engine):
                                execution_id = self.execute_automated_tests(rpa_test_cases, "RPA")
                                if execution_id:
                                    st.success(f"RPA test execution started with ID: {execution_id}")
                            
                            # Execute UFT tests if any
                            if uft_test_cases and ("UFT" in execution_engine or "Auto-detect" in execution_engine):
                                execution_id = self.execute_automated_tests(uft_test_cases, "UFT")
                                if execution_id:
                                    st.success(f"UFT test execution started with ID: {execution_id}")
                        
                        # Process manual tests if applicable
                        if "Manual" in execution_mode:
                            # Extract manual test cases
                            manual_test_cases = [
                                tc for tc in st.session_state.selected_test_cases 
                                if "MANUAL" in tc["type"].upper()
                            ]
                            
                            if manual_test_cases:
                                if self.notify_manual_testers(manual_test_cases, tester_list):
                                    st.success(f"Notification sent to {len(tester_list)} testers")
                                    
                                    # Add manual execution to session state
                                    execution_id = str(uuid.uuid4())
                                    execution_run = {
                                        "id": execution_id,
                                        "status": "Assigned",
                                        "start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "end_time": "",
                                        "test_cases": manual_test_cases,
                                        "total_tests": len(manual_test_cases),
                                        "passed": 0,
                                        "failed": 0,
                                        "pending": len(manual_test_cases),
                                        "progress": 0,
                                        "type": "Manual",
                                        "testers": tester_list,
                                        "execution_type": "Manual"
                                    }
                                    st.session_state.execution_runs.append(execution_run)
                        
                        # Switch to execution dashboard
                        st.session_state.current_tab = "Execution Dashboard"
                        st.experimental_rerun()
            else:
                st.info("Select a SharePoint folder and fetch test cases, or upload a test case file")
    
    def _show_execution_dashboard(self):
        """Display the execution dashboard interface."""
        st.subheader("Test Execution Dashboard")
        
        # Check if we have any execution runs
        if not st.session_state.execution_runs:
            st.info("No test executions found. Start a new execution from the 'Select Test Cases' tab.")
            return
        
        # Create tabs for Active Runs and Completed Runs
        run_tabs = st.tabs(["Active Runs", "Completed Runs"])
        
        # Active Runs tab
        with run_tabs[0]:
            active_runs = [run for run in st.session_state.execution_runs 
                           if run["status"] in ["In Progress", "Assigned"]]
            
            if not active_runs:
                st.info("No active test executions found.")
            else:
                # Add a refresh button to update execution status
                if st.button("Refresh Status", key="refresh_active"):
                    self.update_execution_status()
                    st.experimental_rerun()
                
                # Group active runs by execution type
                rpa_runs = [run for run in active_runs if run.get("execution_type", "") == "RPA"]
                uft_runs = [run for run in active_runs if run.get("execution_type", "") == "UFT"]
                manual_runs = [run for run in active_runs if run.get("execution_type", "") == "Manual"]
                other_runs = [run for run in active_runs if run.get("execution_type", "") not in ["RPA", "UFT", "Manual"]]
                
                # Display RPA runs if any
                if rpa_runs:
                    st.subheader("RPA Executions")
                    self._display_active_runs(rpa_runs)
                
                # Display UFT runs if any
                if uft_runs:
                    st.subheader("UFT Executions")
                    self._display_active_runs(uft_runs)
                
                # Display Manual runs if any
                if manual_runs:
                    st.subheader("Manual Executions")
                    self._display_active_runs(manual_runs)
                
                # Display other runs if any
                if other_runs:
                    st.subheader("Other Executions")
                    self._display_active_runs(other_runs)
        
        # Completed Runs tab
        with run_tabs[1]:
            completed_runs = [run for run in st.session_state.execution_runs 
                             if run["status"] in ["Completed", "Aborted", "Canceled"]]
            
            if not completed_runs:
                st.info("No completed test executions found.")
            else:
                # Filter options
                exec_types = ["All"] + sorted(set(run.get("execution_type", "Other") for run in completed_runs))
                selected_exec_type = st.selectbox("Filter by Execution Type", exec_types, key="filter_exec_type")
                
                status_types = ["All"] + sorted(set(run["status"] for run in completed_runs))
                selected_status = st.selectbox("Filter by Status", status_types, key="filter_status")
                
                # Apply filters
                filtered_runs = completed_runs
                if selected_exec_type != "All":
                    filtered_runs = [run for run in filtered_runs if run.get("execution_type", "Other") == selected_exec_type]
                if selected_status != "All":
                    filtered_runs = [run for run in filtered_runs if run["status"] == selected_status]
                
                # Create a summary table
                summary_data = []
                for run in filtered_runs:
                    summary_data.append({
                        "Execution ID": run["id"],
                        "Status": run["status"],
                        "Execution Type": run.get("execution_type", "Other"),
                        "Start Time": run["start_time"],
                        "End Time": run["end_time"],
                        "Total": run["total_tests"],
                        "Passed": run.get("passed", 0),
                        "Failed": run.get("failed", 0)
                    })
                
                # Display summary table
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df)
                    
                    # Allow detailed view of a specific execution
                    selected_run_id = st.selectbox(
                        "Select Execution for Details",
                        options=[run["id"] for run in filtered_runs],
                        format_func=lambda x: f"{x} - {next((r.get('execution_type', 'Other') for r in filtered_runs if r['id'] == x), '')} - {next((r['status'] for r in filtered_runs if r['id'] == x), '')}"
                    )
                    
                    if selected_run_id:
                        selected_run = next((run for run in filtered_runs if run["id"] == selected_run_id), None)
                        
                        if selected_run:
                            st.subheader(f"Execution Details: {selected_run_id}")
                            
                            # Display execution type badge
                            exec_type = selected_run.get("execution_type", "Other")
                            if exec_type == "RPA":
                                st.info("RPA Execution")
                            elif exec_type == "UFT":
                                st.success("UFT Execution")
                            elif exec_type == "Manual":
                                st.warning("Manual Execution")
                            else:
                                st.info(f"{exec_type} Execution")
                            
                            # Display metrics
                            metric_cols = st.columns(4)
                            with metric_cols[0]:
                                st.metric("Total", selected_run["total_tests"])
                            with metric_cols[1]:
                                st.metric("Passed", selected_run.get("passed", 0))
                            with metric_cols[2]:
                                st.metric("Failed", selected_run.get("failed", 0))
                            with metric_cols[3]:
                                duration = "N/A"
                                if selected_run["end_time"] and selected_run["start_time"]:
                                    try:
                                        start = datetime.datetime.strptime(selected_run["start_time"], "%Y-%m-%d %H:%M:%S")
                                        end = datetime.datetime.strptime(selected_run["end_time"], "%Y-%m-%d %H:%M:%S")
                                        duration = str(end - start)
                                    except:
                                        pass
                                st.metric("Duration", duration)
                            
                            # Show test case details
                            details_df = self.view_execution_details(selected_run_id)
                            st.dataframe(details_df)
                            
                            # Show visualization if there are results
                            if selected_run.get("passed", 0) > 0 or selected_run.get("failed", 0) > 0:
                                st.subheader("Results Visualization")
                                
                                # Create a simple pie chart
                                fig = px.pie(
                                    names=["Passed", "Failed"],
                                    values=[selected_run.get("passed", 0), selected_run.get("failed", 0)],
                                    color=["Passed", "Failed"],
                                    color_discrete_map={"Passed": "green", "Failed": "red"}
                                )
                                st.plotly_chart(fig)
                            
                            # Show analysis option for runs with failures
                            if selected_run.get("failed", 0) > 0:
                                if st.button("Analyze Failures", key=f"analyze_{selected_run_id}"):
                                    analysis = self.analyze_execution_failures(selected_run_id)
                                    
                                    if analysis["status"] == "Analysis completed":
                                        st.success("Analysis completed")
                                        
                                        # Common issues
                                        st.subheader("Common Issues Identified")
                                        for issue in analysis["common_issues"]:
                                            st.info(issue)
                                        
                                        # Recommendations
                                        st.subheader("Recommendations")
                                        for rec in analysis["recommendations"]:
                                            st.success(rec)
                                    else:
                                        st.info(analysis["status"])
                else:
                    st.info("No runs matching the selected filters.")           


    def _display_active_runs(self, runs):
        """Helper method to display active execution runs."""
        for run in runs:
            with st.expander(f"Execution ID: {run['id']} - Status: {run['status']}", expanded=True):
                # Display basic info
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Total Test Cases", run["total_tests"])
                with cols[1]:
                    st.metric("Start Time", run["start_time"])
                with cols[2]:
                    if "type" in run and run["type"] == "Manual":
                        st.metric("Type", "Manual")
                    else:
                        st.metric("Type", run.get("execution_type", "Automated"))
                
                # Show progress
                if run["status"] == "In Progress":
                    st.progress(run["progress"] / 100)
                    st.text(f"Progress: {run['progress']}% complete")
                    
                    # Show counts
                    count_cols = st.columns(3)
                    with count_cols[0]:
                        st.metric("Passed", run["passed"], delta=None)
                    with count_cols[1]:
                        st.metric("Failed", run["failed"], delta=None)
                    with count_cols[2]:
                        st.metric("Pending", run["pending"], delta=None)
                    
                    # Show actions
                    action_cols = st.columns(3)
                    with action_cols[0]:
                        if st.button(f"View Details #{run['id']}", key=f"view_{run['id']}"):
                            details_df = self.view_execution_details(run['id'])
                            st.dataframe(details_df)
                    with action_cols[1]:
                        if st.button(f"Abort Execution #{run['id']}", key=f"abort_{run['id']}"):
                            if self.abort_test_execution(run['id']):
                                st.success("Test execution aborted successfully")
                                st.experimental_rerun()
                    with action_cols[2]:
                        # Different action based on execution type
                        exec_type = run.get("execution_type", "RPA")
                        if exec_type == "UFT":
                            if st.button(f"View UFT Report #{run['id']}", key=f"uft_report_{run['id']}"):
                                st.info("UFT Test Report would be displayed here (Not implemented)")
                        elif exec_type == "RPA":
                            if st.button(f"View RPA Log #{run['id']}", key=f"rpa_log_{run['id']}"):
                                st.info("RPA Execution Log would be displayed here (Not implemented)")
                
                elif run["status"] == "Assigned":
                    # For manually assigned test cases
                    st.info(f"Manual test cases assigned to testers: {', '.join(run.get('testers', ['Not specified']))}")
                    st.info("Waiting for manual execution results to be uploaded")
                    
                    if st.button(f"Cancel Assignment #{run['id']}", key=f"cancel_{run['id']}"):
                        # Mark as canceled
                        for i, r in enumerate(st.session_state.execution_runs):
                            if r["id"] == run["id"]:
                                st.session_state.execution_runs[i]["status"] = "Canceled"
                                st.session_state.execution_runs[i]["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                break
                        st.success("Manual test assignment canceled")
                        st.experimental_rerun()
    
    def _show_manual_results_upload(self):
        """Display the manual results upload interface."""
        st.subheader("Upload Manual Test Results")
        
        # Get manual execution runs that have been assigned
        manual_runs = [run for run in st.session_state.execution_runs 
                      if (run.get("type") == "Manual" or run.get("execution_type") == "Manual") 
                      and run["status"] == "Assigned"]
        
        if not manual_runs:
            st.info("No manual test executions are currently assigned. Assign manual tests from 'Select Test Cases' tab.")
            return
        
        # Select execution run to upload results for
        selected_run_id = st.selectbox(
            "Select Manual Execution",
            options=[run["id"] for run in manual_runs],
            format_func=lambda x: f"{x} - {next((r['start_time'] for r in manual_runs if r['id'] == x), '')} ({next((r['total_tests'] for r in manual_runs if r['id'] == x), 0)} test cases)"
        )
        
        if selected_run_id:
            selected_run = next((run for run in manual_runs if run["id"] == selected_run_id), None)
            
            if selected_run:
                # Display information about the test cases
                st.info(f"Uploading results for {selected_run['total_tests']} test cases, assigned on {selected_run['start_time']}")
                
                # Option 1: Upload results file
                st.subheader("Option 1: Upload Results File")
                uploaded_file = st.file_uploader(
                    "Upload Test Results Excel File",
                    type=["xlsx", "xls"],
                    help="Upload an Excel file containing test results"
                )
                
                if uploaded_file is not None:
                    # Preview the file
                    with st.expander("Preview Uploaded File", expanded=True):
                        df = pd.read_excel(uploaded_file)
                        st.dataframe(df)
                    
                    # Extract result summary
                    st.subheader("Results Summary")
                    
                    # Attempt to extract pass/fail counts from the file
                    # This would be more sophisticated in a real implementation
                    # based on the specific format of the results file
                    passed = st.number_input("Number of Passed Tests", 0, selected_run["total_tests"], value=0)
                    failed = st.number_input("Number of Failed Tests", 0, selected_run["total_tests"], value=0)
                    blocked = st.number_input("Number of Blocked Tests", 0, selected_run["total_tests"], value=0)
                    not_executed = st.number_input("Number of Not Executed Tests", 0, selected_run["total_tests"], value=0)
                    
                    total_accounted = passed + failed + blocked + not_executed
                    
                    if total_accounted > selected_run["total_tests"]:
                        st.error("The sum of all test statuses cannot exceed the total number of tests")
                    elif total_accounted < selected_run["total_tests"]:
                        st.warning(f"You've accounted for {total_accounted} out of {selected_run['total_tests']} tests")
                    else:
                        st.success(f"All {selected_run['total_tests']} tests accounted for")
                    
                    # Upload button
                    if st.button("Upload Results to SharePoint"):
                        result_summary = {
                            "passed": passed,
                            "failed": failed,
                            "blocked": blocked,
                            "not_executed": not_executed,
                            "total": selected_run["total_tests"]
                        }
                        
                        # Read the file as bytes for uploading
                        uploaded_file.seek(0)
                        file_content = uploaded_file.read()
                        
                        if self.upload_manual_test_results(selected_run_id, file_content, result_summary):
                            st.success("Test results uploaded successfully")
                            # Switch to execution dashboard
                            st.session_state.current_tab = "Execution Dashboard"
                            st.experimental_rerun()
                
                # Option 2: Enter results manually
                st.subheader("Option 2: Enter Results Manually")
                
                # Create a form for manual entry
                with st.form("manual_results_form"):
                    # Get the test cases for this execution
                    test_cases = selected_run["test_cases"]
                    
                    # Create a dictionary to store results
                    results = {}
                    
                    for tc in test_cases:
                        st.write(f"**{tc['id']} - {tc['name']}**")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            status = st.radio(
                                f"Status for {tc['id']}",
                                ["Passed", "Failed", "Blocked", "Not Executed"],
                                key=f"status_{tc['id']}"
                            )
                        
                        with col2:
                            comments = st.text_area(
                                f"Comments for {tc['id']}",
                                key=f"comments_{tc['id']}"
                            )
                        
                        results[tc['id']] = {
                            "status": status,
                            "comments": comments
                        }
                    
                    # Submit button
                    submit_button = st.form_submit_button("Submit Manual Results")
                
                if submit_button:
                    # Count different test statuses
                    passed = sum(1 for tc_id, res in results.items() if res["status"] == "Passed")
                    failed = sum(1 for tc_id, res in results.items() if res["status"] == "Failed")
                    blocked = sum(1 for tc_id, res in results.items() if res["status"] == "Blocked")
                    not_executed = sum(1 for tc_id, res in results.items() if res["status"] == "Not Executed")
                    
                    # Create a results DataFrame
                    results_df = pd.DataFrame([
                        {
                            "TEST CASE NUMBER": tc_id,
                            "TEST CASE": next((tc["name"] for tc in test_cases if tc["id"] == tc_id), ""),
                            "STATUS": results[tc_id]["status"],
                            "COMMENTS": results[tc_id]["comments"]
                        }
                        for tc_id in results
                    ])
                    
                    # Convert to Excel for upload
                    excel_buffer = io.BytesIO()
                    results_df.to_excel(excel_buffer, index=False)
                    excel_content = excel_buffer.getvalue()
                    
                    # Create result summary
                    result_summary = {
                        "passed": passed,
                        "failed": failed,
                        "blocked": blocked,
                        "not_executed": not_executed,
                        "total": selected_run["total_tests"]
                    }
                    
                    if self.upload_manual_test_results(selected_run_id, excel_content, result_summary):
                        st.success("Manual test results submitted successfully")
                        # Switch to execution dashboard
                        st.session_state.current_tab = "Execution Dashboard"
                        st.experimental_rerun()


# Main function to run the Streamlit app
def main():
    # Set page config
    st.set_page_config(
        page_title="Watsonx IPG Testing - Test Execution",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Initialize and run the execution UI
    execution_ui = ExecutionUI()
    execution_ui.show()

if __name__ == "__main__":
    main()                 