import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
import base64

# Import necessary modules (to be implemented or imported from other project modules)
# from src.phase2.error_processor.error_analyzer import analyze_failure
# from src.phase2.error_processor.defect_creator import create_defect
# from src.common.auth.auth_utils import get_current_user
# from src.phase2.alm_connector.alm_defect_manager import get_defect_tracker




####################### testig block starts here

import streamlit as st
import pandas as pd
import time
import random
from ui_utils import show_info_message, show_success_message, show_error_message
from state_management import add_notification
import mock_services

def show_analysis():
    """Display the analysis and defects module UI."""
    st.header("Analysis & Defects Module")
    
    # Create tabs for different functions
    tabs = st.tabs(["Failed Test Analysis", "Log Defect", "Defect Tracker"])
    
    with tabs[0]:
        show_failed_test_analysis()
    
    with tabs[1]:
        show_log_defect()
    
    with tabs[2]:
        show_defect_tracker()

def show_failed_test_analysis():
    """Display the failed test analysis tab."""
    st.subheader("Failed Test Analysis")
    
    # Check if we came from execution dashboard
    analyze_from_run = "analyze_run_id" in st.session_state
    
    if analyze_from_run:
        run_id = st.session_state["analyze_run_id"]
        st.info(f"Analyzing failures from execution run: {run_id}")
        
        # Create mock failed steps for the run
        execution_runs = st.session_state.get("execution_runs", mock_services.get_execution_runs())
        selected_run = next((run for run in execution_runs if run["id"] == run_id), None)
        
        if selected_run and selected_run["fail_count"] > 0:
            # Create mock failed steps
            test_cases = st.session_state.get("current_test_cases", mock_services.get_test_cases())
            failed_steps = []
            
            for _ in range(selected_run["fail_count"]):
                tc = random.choice(test_cases)
                step = random.choice(tc["steps"])
                
                failed_steps.append({
                    "Test Case ID": tc["id"],
                    "Step #": step["step_no"],
                    "Description": step["description"],
                    "Expected": step["expected"],
                    "Error Message": f"Element not found: {random.choice(['button', 'input', 'dropdown', 'checkbox'])}",
                    "Screenshot": "Available"
                })
            
            # Store in session state for further use
            st.session_state["failed_steps"] = failed_steps
            
            # Clear the flag
            del st.session_state["analyze_run_id"]
    
    # Get failed steps from session state or create empty list
    failed_steps = st.session_state.get("failed_steps", [])
    
    if failed_steps:
        # Display failed steps
        failed_df = pd.DataFrame(failed_steps)
        st.dataframe(failed_df, use_container_width=True)
        
        # Select a failed step for analysis
        selected_step = st.selectbox(
            "Select a Failed Step to Analyze",
            options=range(len(failed_steps)),
            format_func=lambda i: f"{failed_steps[i]['Test Case ID']} - Step {failed_steps[i]['Step #']}: {failed_steps[i]['Description'][:30]}..."
        )
        
        if st.button("Analyze Failure with AI", key="analyze_failure_button"):
            with st.spinner("Analyzing failure with AI..."):
                # Simulate processing time
                time.sleep(3)
                
                # Use mock function for analysis
                step_data = failed_steps[selected_step]
                analysis_result = mock_services.analyze_failure(step_data["Test Case ID"], step_data["Step #"])
                
                # Store in session state
                st.session_state["current_analysis"] = {
                    "step_data": step_data,
                    "analysis": analysis_result
                }
                
                show_success_message("Analysis complete!")
        
        # Display analysis results if available
        if "current_analysis" in st.session_state:
            st.markdown("---")
            st.subheader("AI Analysis Results")
            
            current = st.session_state["current_analysis"]
            step_data = current["step_data"]
            analysis = current["analysis"]
            
            st.markdown(f"### Analysis for {step_data['Test Case ID']} - Step {step_data['Step #']}")
            st.markdown(f"**Description:** {step_data['Description']}")
            st.markdown(f"**Expected:** {step_data['Expected']}")
            st.markdown(f"**Error Message:** {step_data['Error Message']}")
            
            st.markdown("### Potential Root Causes")
            for cause in analysis["potential_causes"]:
                st.markdown(f"- {cause}")
            
            st.markdown("### Suggested Remediation Steps")
            for step in analysis["remediation"]:
                st.markdown(f"- {step}")
            
            # Create defect button
            if st.button("Create Defect", key="create_defect_button"):
                # Navigate to log defect tab with pre-filled data
                st.session_state["prefill_defect"] = {
                    "test_case_id": step_data["Test Case ID"],
                    "step_no": step_data["Step #"],
                    "error_details": step_data["Error Message"],
                    "analysis": analysis
                }
                
                # Set active tab to Log Defect
                st.session_state["active_analysis_tab"] = 1
                st.experimental_rerun()
    else:
        st.info("No failed test steps to analyze. Run a test execution first or select failed tests to analyze.")

def show_log_defect():
    """Display the log defect tab."""
    st.subheader("Log Defect")
    
    # Check if we should be on this tab
    if "active_analysis_tab" in st.session_state and st.session_state["active_analysis_tab"] == 1:
        del st.session_state["active_analysis_tab"]
    
    # Check if we have pre-filled data
    prefilled = "prefill_defect" in st.session_state
    
    if prefilled:
        prefill_data = st.session_state["prefill_defect"]
        test_case_id = prefill_data["test_case_id"]
        step_no = prefill_data["step_no"]
        error_details = prefill_data["error_details"]
        analysis = prefill_data.get("analysis", None)
        
        # Get test case details
        test_case = mock_services.get_test_case_by_id(test_case_id)
        step = next((s for s in test_case["steps"] if s["step_no"] == step_no), None) if test_case else None
        
        st.info(f"Creating defect for failed test case: {test_case_id}, Step {step_no}")
    else:
        # Manual defect creation
        st.markdown("### Manual Defect Creation")
        
        # Test case selection
        test_cases = st.session_state.get("current_test_cases", mock_services.get_test_cases())
        test_case_id = st.selectbox(
            "Select Test Case",
            options=[tc["id"] for tc in test_cases],
            format_func=lambda x: f"{x}: {next((tc['title'] for tc in test_cases if tc['id'] == x), '')}"
        )
        
        test_case = mock_services.get_test_case_by_id(test_case_id)
        
        # Step selection
        steps = test_case["steps"] if test_case else []
        step_no = st.selectbox(
            "Select Step",
            options=[s["step_no"] for s in steps],
            format_func=lambda x: f"Step {x}: {next((s['description'] for s in steps if s['step_no'] == x), '')}"
        )
        
        step = next((s for s in steps if s["step_no"] == step_no), None) if steps else None
        
        # Error details
        error_details = st.text_area(
            "Error Details",
            placeholder="Describe the error that occurred",
            height=100
        )
        
        analysis = None
    
    # Create the defect form
    with st.form("defect_form"):
        st.markdown("### Defect Form")
        
        # Pre-filled summary if available
        if prefilled and test_case and step:
            default_summary = f"Test Case {test_case_id} failed at step {step_no}: {step['description']}"
        else:
            default_summary = ""
        
        summary = st.text_input(
            "Summary",
            value=default_summary
        )
        
        # Pre-filled steps to reproduce
        if prefilled and test_case and step:
            default_steps = f"""
            Test Case: {test_case_id} - {test_case['title']}
            Failed at Step {step_no}: {step['description']}
            Expected: {step['expected']}
            Error: {error_details}
            """
        else:
            default_steps = ""
        
        steps_to_reproduce = st.text_area(
            "Steps to Reproduce",
            value=default_steps,
            height=150
        )
        
        # Environment
        environment = st.text_input(
            "Environment",
            value="Test Environment"
        )
        
        # Severity and priority
        col1, col2 = st.columns(2)
        
        with col1:
            # Suggested severity if analysis available
            if analysis:
                suggested_severity = random.choice(["High", "Medium", "Low"])
                st.info(f"AI Suggested Severity: {suggested_severity}")
            
            severity = st.select_slider(
                "Severity",
                options=["Low", "Medium", "High", "Critical"],
                value="Medium"
            )
        
        with col2:
            priority = st.select_slider(
                "Priority",
                options=["Low", "Medium", "High"],
                value="Medium"
            )
        
        # Assignee selection
        assignee_options = ["John Developer", "Jane Developer", "QA Lead", "Project Manager", "Defect Analyst"]
        
        # Suggested assignee if analysis available
        if analysis:
            suggested_assignee = random.choice(assignee_options)
            st.info(f"Suggested Assignee (based on rules): {suggested_assignee}")
        
        assignee = st.selectbox(
            "Assignee",
            options=assignee_options,
            index=0 if analysis and "John Developer" == suggested_assignee else 0
        )
        
        # Attachments
        st.markdown("### Attachments")
        st.info("Screenshots of error will be automatically attached.")
        
        additional_attachments = st.file_uploader(
            "Additional Attachments",
            type=["jpg", "png", "pdf", "txt", "log"],
            accept_multiple_files=True
        )
        
        # Submit button
        submitted = st.form_submit_button("Submit Defect to JIRA/ALM")
        
        if submitted:
            with st.spinner("Creating defect..."):
                # Simulate processing time
                time.sleep(2)
                
                # Create mock defect
                if prefilled:
                    defect = mock_services.create_defect(
                        prefill_data["test_case_id"],
                        prefill_data["step_no"],
                        prefill_data["error_details"]
                    )
                else:
                    defect = mock_services.create_defect(
                        test_case_id,
                        step_no,
                        error_details
                    )
                
                if defect:
                    show_success_message(f"Defect created successfully! Defect ID: {defect['id']}")
                    add_notification(f"Created defect {defect['id']} for test case {test_case_id}", "success")
                    
                    # Clear prefill data if present
                    if "prefill_defect" in st.session_state:
                        del st.session_state["prefill_defect"]
                    
                    # Navigate to defect tracker
                    st.session_state["active_analysis_tab"] = 2
                    st.experimental_rerun()
                else:
                    show_error_message("Failed to create defect. Please try again.")

def show_defect_tracker():
    """Display the defect tracker tab."""
    st.subheader("Defect Tracker")
    
    # Check if we should be on this tab
    if "active_analysis_tab" in st.session_state and st.session_state["active_analysis_tab"] == 2:
        del st.session_state["active_analysis_tab"]
    
    # Get defects from mock service
    defects = mock_services.get_defects()
    
    if defects:
        # Create a dataframe for display
        defect_data = [{
            "ID": d["id"],
            "Summary": d["summary"],
            "Status": d["status"],
            "Severity": d["severity"],
            "Assignee": d["assignee"],
            "Created Date": d["created_date"][:10] if d["created_date"] else "N/A"
        } for d in defects]
        
        defect_df = pd.DataFrame(defect_data)
        st.dataframe(defect_df, use_container_width=True)
        
        # Filter controls
        st.markdown("### Filters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                options=["Open", "In Progress", "Closed"],
                default=[]
            )
        
        with col2:
            severity_filter = st.multiselect(
                "Severity",
                options=["Low", "Medium", "High"],
                default=[]
            )
        
        with col3:
            assignee_filter = st.multiselect(
                "Assignee",
                options=list(set(d["assignee"] for d in defects)),
                default=[]
            )
        
        # Apply filters
        filtered_defects = defects
        
        if status_filter:
            filtered_defects = [d for d in filtered_defects if d["status"] in status_filter]
        
        if severity_filter:
            filtered_defects = [d for d in filtered_defects if d["severity"] in severity_filter]
        
        if assignee_filter:
            filtered_defects = [d for d in filtered_defects if d["assignee"] in assignee_filter]
        
        # Show filtered results if filters applied
        if status_filter or severity_filter or assignee_filter:
            st.markdown("### Filtered Results")
            
            if filtered_defects:
                filtered_data = [{
                    "ID": d["id"],
                    "Summary": d["summary"],
                    "Status": d["status"],
                    "Severity": d["severity"],
                    "Assignee": d["assignee"],
                    "Created Date": d["created_date"][:10] if d["created_date"] else "N/A"
                } for d in filtered_defects]
                
                filtered_df = pd.DataFrame(filtered_data)
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.info("No defects match the selected filters.")
        
        # Refresh button
        if st.button("Refresh Defects", key="refresh_defects_button"):
            with st.spinner("Refreshing defects..."):
                # Simulate processing time
                time.sleep(1)
                show_success_message("Defects refreshed successfully!")
                st.experimental_rerun()
    else:
        st.info("No defects available. Create a defect first.")
####################### testing block ends here

class AnalysisAndDefectsUI:
    def __init__(self):
        """
        Initialize the Analysis and Defects UI module
        """
        self.failed_steps_data = None
        self.defect_tracker_data = None

    def load_failed_test_steps(self) -> List[Dict]:
        """
        Load failed test steps from recent executions
        
        Returns:
            List of dictionaries containing failed test step details
        """
        # Placeholder for actual implementation
        # In real scenario, this would fetch from execution logger or database
        return [
            {
                "test_case_id": "TC-001",
                "step_number": 3,
                "error_message": "Login button not clickable",
                "screenshot": None,  # Placeholder for screenshot
                "timestamp": "2025-04-28 14:30:45"
            },
            {
                "test_case_id": "TC-002", 
                "step_number": 2,
                "error_message": "Invalid credentials validation failed",
                "screenshot": None,
                "timestamp": "2025-04-28 15:15:22"
            }
        ]

    def display_failed_test_steps(self):
        """
        Display failed test steps in a Streamlit interface
        """
        st.subheader("Failed Test Steps")
        
        # Load failed steps
        failed_steps = self.load_failed_test_steps()
        
        # Create a DataFrame for display
        df = pd.DataFrame(failed_steps)
        
        # Display failed steps in a table
        st.dataframe(df, use_container_width=True)
        
        # Add AI Analysis for each failed step
        for index, step in enumerate(failed_steps):
            with st.expander(f"Analyze Failure: Test Case {step['test_case_id']} - Step {step['step_number']}"):
                self.display_ai_failure_analysis(step)

    def display_ai_failure_analysis(self, failed_step: Dict):
        """
        Display AI-powered failure analysis for a specific test step
        
        Args:
            failed_step (Dict): Details of the failed test step
        """
        # Placeholder for AI failure analysis
        # In real implementation, this would call error_analyzer
        st.markdown("### AI Failure Analysis")
        
        potential_causes = [
            "UI element not rendered correctly",
            "Timing issue with page load",
            "Unexpected authentication mechanism"
        ]
        
        suggested_steps = [
            "Check browser compatibility",
            "Add explicit wait conditions",
            "Verify authentication flow"
        ]
        
        st.markdown("#### Potential Root Causes:")
        for cause in potential_causes:
            st.markdown(f"- {cause}")
        
        st.markdown("#### Suggested Remediation Steps:")
        for step in suggested_steps:
            st.markdown(f"- {step}")
        
        # Create defect button
        if st.button(f"Create Defect for Test Case {failed_step['test_case_id']}"):
            self.display_defect_form(failed_step)

    def display_defect_form(self, failed_step: Dict):
        """
        Display defect logging form with pre-filled information
        
        Args:
            failed_step (Dict): Details of the failed test step
        """
        st.subheader("Log Defect")
        
        # Defect form with pre-filled information
        with st.form("defect_form"):
            # Pre-fill summary based on failed step
            summary = st.text_input(
                "Summary", 
                value=f"Test Case {failed_step['test_case_id']} failed at step {failed_step['step_number']}"
            )
            
            # Steps to reproduce
            steps_to_reproduce = st.text_area(
                "Steps to Reproduce", 
                value=f"""
1. Execute Test Case {failed_step['test_case_id']}
2. Reach step {failed_step['step_number']}
3. Observe failure: {failed_step['error_message']}
                """.strip()
            )
            
            # Severity selection with AI suggestion
            severity_options = ["Low", "Medium", "High", "Critical"]
            suggested_severity = "High"  # AI-suggested severity
            severity = st.selectbox(
                "Severity", 
                options=severity_options, 
                index=severity_options.index(suggested_severity)
            )
            
            # Priority selection
            priority_options = ["Low", "Medium", "High", "Urgent"]
            suggested_priority = "High"  # AI-suggested priority
            priority = st.selectbox(
                "Priority", 
                options=priority_options, 
                index=priority_options.index(suggested_priority)
            )
            
            # Environment details
            environment = st.text_input("Environment", value="Production")
            
            # Assignee (with predefined rule suggestion)
            assignee_options = ["Developer", "QA Lead", "Project Manager"]
            suggested_assignee = "QA Lead"
            assignee = st.selectbox(
                "Assignee", 
                options=assignee_options, 
                index=assignee_options.index(suggested_assignee)
            )
            
            # Screenshot upload (if available)
            screenshot = st.file_uploader("Attach Screenshot", type=["png", "jpg", "jpeg"])
            
            # Submit defect button
            submit_defect = st.form_submit_button("Submit Defect")
            
            if submit_defect:
                # Placeholder for actual defect creation logic
                st.success(f"Defect created and assigned to {assignee}")

    def display_defect_tracker(self):
        """
        Display defect tracker view with logged issues
        """
        st.subheader("Defect Tracker")
        
        # Placeholder defect data
        defect_data = [
            {
                "Defect ID": "DEF-001",
                "Test Case": "TC-001", 
                "Status": "Open", 
                "Severity": "High", 
                "Assignee": "QA Lead"
            },
            {
                "Defect ID": "DEF-002", 
                "Test Case": "TC-002", 
                "Status": "In Progress", 
                "Severity": "Medium", 
                "Assignee": "Developer"
            }
        ]
        
        # Create DataFrame and display
        df = pd.DataFrame(defect_data)
        st.dataframe(df, use_container_width=True)

    def render(self):
        """
        Render the entire Analysis & Defects Module UI
        """
        st.title("Analysis & Defects Module")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs([
            "Failed Test Analysis", 
            "Log Defect", 
            "Defect Tracker"
        ])
        
        with tab1:
            self.display_failed_test_steps()
        
        with tab2:
            # Option to manually log a defect
            st.subheader("Manual Defect Logging")
            manual_defect_button = st.button("Log New Defect")
            if manual_defect_button:
                # Display generic defect form without pre-filled test failure data
                self.display_defect_form({
                    "test_case_id": "N/A", 
                    "step_number": "N/A", 
                    "error_message": ""
                })
        
        with tab3:
            self.display_defect_tracker()

def main():
    """
    Main function to run the Analysis & Defects Module
    """
    analysis_ui = AnalysisAndDefectsUI()
    analysis_ui.render()

if __name__ == "__main__":
    main()