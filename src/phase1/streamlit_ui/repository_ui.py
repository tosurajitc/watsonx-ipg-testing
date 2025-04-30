"""
Test Repository & Comparison Module for Watsonx IPG Testing

This module implements the UI for managing the central test case repository and handling comparisons
between suggested and existing test cases. It provides:
- Repository browser with connection status indicators
- Search and filter capabilities for test cases
- Comparison results display
- Actions for exact matches, partial matches, and new test cases
- Tracking lists for matched/modified/new cases
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import io
from typing import Dict, List, Any, Optional, Tuple

#######################################################
# PART 1: CORE SETUP AND BASIC REPOSITORY BROWSER
#######################################################

# Import modules needed for Part 1
from src.phase1.sharepoint_connector.sharepoint_auth import check_sharepoint_connection
from src.phase1.jira_connector.jira_auth import check_jira_connection
from src.phase2.alm_connector.alm_auth import check_alm_connection
from src.phase1.coverage_analyzer.comparison_engine import compare_test_cases
from src.phase1.test_data_manager.data_analyzer import check_test_data_availability
from src.phase1.notification_service.notification_manager import send_notification
from src.phase1.system_configuration.rule_engine import get_owner_by_rules
from src.phase1.test_case_manager.version_controller import create_new_version, mark_under_maintenance
import src.common.utils.ui_utils as ui_utils




#################### Testing blocl

import streamlit as st
import pandas as pd
import time
from ui_utils import show_info_message, show_success_message, show_error_message
from state_management import add_notification
import mock_services

def show_repository():
    """Display the repository and comparison module UI."""
    st.header("Test Repository & Comparison Module")
    
    # Create tabs for different functions
    tabs = st.tabs(["Repository Browser", "Comparison Results", "Tracking Lists"])
    
    with tabs[0]:
        show_repository_browser()
    
    with tabs[1]:
        show_comparison_results()
    
    with tabs[2]:
        show_tracking_lists()

def show_repository_browser():
    """Display the repository browser tab."""
    st.subheader("Repository Browser")
    
    # Connection status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sharepoint_status = st.session_state.integration_status.get("sharepoint", False)
        status_color = "green" if sharepoint_status else "red"
        st.markdown(f"SharePoint Connection: <span style='color:{status_color};'>{'Connected' if sharepoint_status else 'Disconnected'}</span>", unsafe_allow_html=True)
    
    with col2:
        jira_status = st.session_state.integration_status.get("jira", False)
        status_color = "green" if jira_status else "red"
        st.markdown(f"JIRA Connection: <span style='color:{status_color};'>{'Connected' if jira_status else 'Disconnected'}</span>", unsafe_allow_html=True)
    
    with col3:
        alm_status = st.session_state.integration_status.get("alm", False)
        status_color = "green" if alm_status else "red"
        st.markdown(f"ALM Connection: <span style='color:{status_color};'>{'Connected' if alm_status else 'Disconnected'}</span>", unsafe_allow_html=True)
    
    # Search and filter controls
    st.markdown("---")
    st.subheader("Search and Filter")
    
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input("Search by ID or Keyword", placeholder="Enter search term...")
    
    with col2:
        filter_options = st.multiselect(
            "Filter by",
            ["Status: Active", "Status: Under Maintenance", "Status: Obsolete", "Type: Manual", "Type: Automated"],
            default=["Status: Active"]
        )
    
    # Get test cases from mock data if not in session state
    if "current_test_cases" not in st.session_state or not st.session_state.current_test_cases:
        st.session_state.current_test_cases = mock_services.get_test_cases()
    
    # Display test cases
    test_cases = st.session_state.current_test_cases
    
    # Apply search filter if provided
    if search_term:
        test_cases = [tc for tc in test_cases if search_term.lower() in tc["id"].lower() or search_term.lower() in tc["title"].lower()]
    
    # Apply status/type filters
    if filter_options:
        filtered_test_cases = []
        for tc in test_cases:
            for filter_option in filter_options:
                if filter_option.startswith("Status:") and filter_option.split(": ")[1] == tc["status"]:
                    filtered_test_cases.append(tc)
                    break
                elif filter_option.startswith("Type:") and filter_option.split(": ")[1] == tc["type"]:
                    filtered_test_cases.append(tc)
                    break
        test_cases = filtered_test_cases
    
    # Create a dataframe for display
    if test_cases:
        test_cases_display = [{
            "ID": tc["id"],
            "Title": tc["title"],
            "Status": tc["status"],
            "Owner": tc["owner"],
            "Type": tc["type"],
            "Last Modified": "2025-04-22"  # Placeholder date
        } for tc in test_cases]
        
        test_cases_df = pd.DataFrame(test_cases_display)
        st.dataframe(test_cases_df, use_container_width=True)
    else:
        show_info_message("No test cases found matching the criteria.")
    
    # Refresh button
    if st.button("Refresh Repository", key="refresh_repo_button"):
        with st.spinner("Refreshing repository..."):
            # Simulate processing time
            time.sleep(1)
            st.session_state.current_test_cases = mock_services.get_test_cases()
            show_success_message("Repository refreshed successfully!")
            st.experimental_rerun()

def show_comparison_results():
    """Display the comparison results tab."""
    st.subheader("Comparison Results")
    
    # Check if we came from comparison in test generation module
    if "compare_result" in st.session_state and st.session_state["compare_result"]:
        # Show comparison results
        with st.spinner("Loading comparison results..."):
            # Simulate processing time
            time.sleep(1)
            
            # Use mock comparison data
            if "generated_test_cases" in st.session_state and st.session_state["generated_test_cases"]:
                # Take the first generated test case for demonstration
                test_case = st.session_state["generated_test_cases"][0]
                comparison_result = mock_services.compare_with_repository(test_case)
                
                st.subheader(f"Comparison for Test Case: {test_case['id']}")
                st.markdown(f"**Title:** {test_case['title']}")
                
                # Display result type prominently
                result_type = comparison_result["result"]
                if result_type == "Exact Match Found":
                    st.success(result_type)
                elif result_type == "Partial Match Found":
                    st.warning(result_type)
                else:  # New Test Case
                    st.info(result_type)
                
                # Display the comparison details
                if result_type in ["Exact Match Found", "Partial Match Found"]:
                    existing_case = comparison_result["existing_case"]
                    
                    st.markdown("### Existing Test Case Details")
                    st.write(f"**ID:** {existing_case['id']}")
                    st.write(f"**Title:** {existing_case['title']}")
                    st.write(f"**Status:** {existing_case['status']}")
                    st.write(f"**Owner:** {existing_case['owner']}")
                    st.write(f"**Type:** {existing_case['type']}")
                    
                    # Display differences if partial match
                    if result_type == "Partial Match Found" and comparison_result["differences"]:
                        st.markdown("### Differences")
                        for diff in comparison_result["differences"]:
                            st.markdown(f"- {diff}")
                
                # Actions based on result type
                st.markdown("---")
                st.subheader("Actions")
                
                if result_type == "Exact Match Found":
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Test Data Status**")
                        test_data_available = random.choice([True, False])
                        if test_data_available:
                            st.success("Test data available")
                            if st.button("Trigger Execution (with existing data)", key="trigger_exec_button"):
                                with st.spinner("Triggering execution..."):
                                    # Simulate processing time
                                    time.sleep(2)
                                    show_success_message("Execution triggered successfully!")
                                    add_notification(f"Triggered execution for {existing_case['id']}", "success")
                                    # Navigate to execution module
                                    st.session_state["page"] = "Test Execution"
                                    st.experimental_rerun()
                        else:
                            st.warning("Test data needs generation")
                            if st.button("Generate Data & Trigger Execution", key="gen_data_button"):
                                with st.spinner("Generating test data and triggering execution..."):
                                    # Simulate processing time
                                    time.sleep(3)
                                    show_success_message("Test data generated and execution triggered successfully!")
                                    add_notification(f"Generated data and triggered execution for {existing_case['id']}", "success")
                                    # Navigate to execution module
                                    st.session_state["page"] = "Test Execution"
                                    st.experimental_rerun()
                    
                    with col2:
                        if existing_case["type"] == "Manual":
                            if st.button("Notify Owner for Execution", key="notify_owner_button"):
                                with st.spinner("Sending notification..."):
                                    # Simulate processing time
                                    time.sleep(1)
                                    show_success_message(f"Notification sent to {existing_case['owner']} successfully!")
                                    add_notification(f"Notified {existing_case['owner']} to execute {existing_case['id']}", "info")
                        
                        if st.button("Update 'Matched' List", key="update_matched_button"):
                            with st.spinner("Updating matched list..."):
                                # Simulate processing time
                                time.sleep(1)
                                show_success_message("Matched list updated successfully!")
                                # Store in session state for tracking lists tab
                                if "matched_list" not in st.session_state:
                                    st.session_state["matched_list"] = []
                                st.session_state["matched_list"].append({
                                    "generated_id": test_case["id"],
                                    "matched_id": existing_case["id"],
                                    "title": existing_case["title"],
                                    "owner": existing_case["owner"],
                                    "type": existing_case["type"]
                                })
                
                elif result_type == "Partial Match Found":
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Notify Owner of Suggested Changes", key="notify_changes_button"):
                            with st.spinner("Sending notification..."):
                                # Simulate processing time
                                time.sleep(1)
                                show_success_message(f"Notification sent to {existing_case['owner']} successfully!")
                                add_notification(f"Notified {existing_case['owner']} of suggested changes for {existing_case['id']}", "info")
                        
                        if st.button("Upload New Version", key="upload_version_button"):
                            with st.spinner("Uploading new version..."):
                                # Simulate processing time
                                time.sleep(2)
                                # Mark as under maintenance if automated
                                if existing_case["type"] == "Automated":
                                    st.info(f"Test case {existing_case['id']} marked as 'Under Maintenance'")
                                show_success_message("New version uploaded successfully!")
                                add_notification(f"Uploaded new version of {existing_case['id']}", "success")
                    
                    with col2:
                        if st.button("Update 'Needs Modification' List", key="update_modification_button"):
                            with st.spinner("Updating needs modification list..."):
                                # Simulate processing time
                                time.sleep(1)
                                show_success_message("Needs modification list updated successfully!")
                                # Store in session state for tracking lists tab
                                if "modification_list" not in st.session_state:
                                    st.session_state["modification_list"] = []
                                st.session_state["modification_list"].append({
                                    "generated_id": test_case["id"],
                                    "existing_id": existing_case["id"],
                                    "title": existing_case["title"],
                                    "owner": existing_case["owner"],
                                    "differences": len(comparison_result["differences"])
                                })
                
                else:  # New Test Case
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### Owner Assignment Rule Preview")
                        st.info("Based on predefined rules, this test case will be assigned to: **John Doe**")
                        
                        if st.button("Upload to Repository & Assign Owner", key="upload_new_button"):
                            with st.spinner("Uploading to repository and assigning owner..."):
                                # Simulate processing time
                                time.sleep(2)
                                show_success_message("Test case uploaded and assigned successfully!")
                                add_notification(f"Created new test case {test_case['id']} and assigned to John Doe", "success")
                    
                    with col2:
                        if st.button("Update 'New' List", key="update_new_button"):
                            with st.spinner("Updating new list..."):
                                # Simulate processing time
                                time.sleep(1)
                                show_success_message("New list updated successfully!")
                                # Store in session state for tracking lists tab
                                if "new_list" not in st.session_state:
                                    st.session_state["new_list"] = []
                                st.session_state["new_list"].append({
                                    "id": test_case["id"],
                                    "title": test_case["title"],
                                    "assigned_to": "John Doe",
                                    "type": test_case["type"]
                                })
                
                # Clear the comparison result flag if user manually clicks a button
                if st.button("Clear Comparison", key="clear_comparison_button"):
                    del st.session_state["compare_result"]
                    show_info_message("Comparison cleared.")
                    st.experimental_rerun()
        
    else:
        st.info("No comparison results to display. Select test cases in the Test Generation module and click 'Compare with Repository'.")

def show_tracking_lists():
    """Display the tracking lists tab."""
    st.subheader("Tracking Lists")
    
    # Create tabs for different tracking lists
    tracking_tabs = st.tabs(["Matched Cases", "Cases Needing Modification", "Newly Added Cases"])
    
    with tracking_tabs[0]:
        st.subheader("Matched Cases")
        
        if "matched_list" in st.session_state and st.session_state["matched_list"]:
            matched_df = pd.DataFrame(st.session_state["matched_list"])
            st.dataframe(matched_df, use_container_width=True)
            
            if st.button("Export Matched List", key="export_matched_button"):
                with st.spinner("Exporting matched list..."):
                    # Simulate processing time
                    time.sleep(1)
                    show_success_message("Matched list exported successfully!")
                    st.download_button(
                        label="Download Matched List",
                        data=b"Mock Excel Data",  # Just a placeholder
                        file_name="matched_list.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("No matched cases in the tracking list yet.")
    
    with tracking_tabs[1]:
        st.subheader("Cases Needing Modification")
        
        if "modification_list" in st.session_state and st.session_state["modification_list"]:
            modification_df = pd.DataFrame(st.session_state["modification_list"])
            st.dataframe(modification_df, use_container_width=True)
            
            if st.button("Export Modification List", key="export_modification_button"):
                with st.spinner("Exporting modification list..."):
                    # Simulate processing time
                    time.sleep(1)
                    show_success_message("Modification list exported successfully!")
                    st.download_button(
                        label="Download Modification List",
                        data=b"Mock Excel Data",  # Just a placeholder
                        file_name="modification_list.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("No cases needing modification in the tracking list yet.")
    
    with tracking_tabs[2]:
        st.subheader("Newly Added Cases")
        
        if "new_list" in st.session_state and st.session_state["new_list"]:
            new_df = pd.DataFrame(st.session_state["new_list"])
            st.dataframe(new_df, use_container_width=True)
            
            if st.button("Export New List", key="export_new_button"):
                with st.spinner("Exporting new list..."):
                    # Simulate processing time
                    time.sleep(1)
                    show_success_message("New list exported successfully!")
                    st.download_button(
                        label="Download New List",
                        data=b"Mock Excel Data",  # Just a placeholder
                        file_name="new_list.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("No newly added cases in the tracking list yet.")

################### Testing block endss here



def display_repository_ui():
    """Main function to display the Test Repository & Comparison Module UI"""
    st.title("Test Repository & Comparison Module")
    
    # Create tabs for different sections
    tabs = st.tabs(["Repository Browser", "Comparison Results", "Tracking Lists"])
    
    with tabs[0]:
        display_repository_browser()
    
    with tabs[1]:
        display_comparison_results()
    
    with tabs[2]:
        display_tracking_lists()


def display_repository_browser():
    """Display the repository browser with connection status and filters"""
    st.header("Repository Browser")
    
    # Display connection status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sharepoint_status = check_sharepoint_connection()
        ui_utils.display_connection_status("SharePoint", sharepoint_status)
        
        if not sharepoint_status and st.button("Reconnect to SharePoint"):
            st.info("SharePoint reconnection will be implemented in Part 2")
    
    with col2:
        jira_status = check_jira_connection()
        ui_utils.display_connection_status("JIRA", jira_status)
    
    with col3:
        alm_status = check_alm_connection()
        ui_utils.display_connection_status("ALM", alm_status)
    
    # Basic search and filter section
    st.subheader("Search and Filter")
    
    with st.form("repository_search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            search_query = st.text_input("Search by ID or Keyword")
            
            repository_filter = st.multiselect(
                "Repository Source",
                ["SharePoint", "JIRA", "ALM"],
                default=["SharePoint"]
            )
        
        with col2:
            status_filter = st.multiselect(
                "Status",
                ["Active", "Under Maintenance", "Obsolete"],
                default=["Active"]
            )
            
            type_filter = st.multiselect(
                "Type",
                ["Manual", "Automated"],
                default=["Manual", "Automated"]
            )
        
        submitted = st.form_submit_button("Apply Filters")
    
    # Display test cases table if form was submitted
    if submitted:
        # Store filter state
        st.session_state.filter_applied = True
        st.session_state.current_filters = {
            "search_query": search_query,
            "repository_filter": repository_filter,
            "status_filter": status_filter,
            "type_filter": type_filter
        }
        
        # Call display function with filters
        display_test_cases_table(st.session_state.current_filters)
    elif 'filter_applied' in st.session_state and st.session_state.filter_applied:
        # Use stored filters if previously applied
        display_test_cases_table(st.session_state.current_filters)
    else:
        st.info("Use the filters above and click 'Apply Filters' to view test cases.")


def display_test_cases_table(filters: Dict[str, Any]):
    """Display the table of test cases with applied filters
    
    Args:
        filters: Dictionary containing filter parameters
    """
    with st.spinner("Fetching test cases..."):
        try:
            # In a real implementation, this would fetch data from repositories
            # For Part 1, we'll use a sample dataset
            df = fetch_test_cases(filters)
            
            if not df.empty:
                # Display the dataframe
                st.dataframe(
                    df,
                    column_config={
                        "ID": st.column_config.TextColumn("ID", width="small"),
                        "Title": st.column_config.TextColumn("Title", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "Owner": st.column_config.TextColumn("Owner", width="small"),
                        "Type": st.column_config.TextColumn("Type", width="small"),
                        "Last Modified": st.column_config.DateColumn("Last Modified", format="MM/DD/YYYY", width="small"),
                        "Repository": st.column_config.TextColumn("Repository", width="small")
                    },
                    hide_index=True,
                    height=400
                )
                
                # Display basic statistics
                st.caption(f"Found {len(df)} test cases matching your criteria")
                
                # Basic test case selection
                st.subheader("Test Case Actions")
                
                selected_test_id = st.selectbox(
                    "Select Test Case for Actions", 
                    df['ID'].tolist(),
                    format_func=lambda x: f"{x} - {df[df['ID'] == x]['Title'].values[0]}"
                )
                
                if selected_test_id:
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        if st.button("View Details"):
                            st.session_state.view_test_case = selected_test_id
                            st.info(f"View details functionality for {selected_test_id} will be implemented in Part 3")
                    
                    with action_col2:
                        if st.button("Compare with Repository"):
                            st.session_state.compare_test_case = selected_test_id
                            st.info(f"Comparison functionality for {selected_test_id} will be implemented in Parts 4-6")
                    
                    with action_col3:
                        if st.button("Export Test Case"):
                            export_test_case(selected_test_id)
            else:
                st.warning("No test cases found matching your criteria.")
        
        except Exception as e:
            st.error(f"Error retrieving test cases: {str(e)}")
            st.info("Please check your connection to the repositories and try again.")


def fetch_test_cases(filters: Dict[str, Any]) -> pd.DataFrame:
    """Fetch test cases based on filters
    
    In a real implementation, this would call appropriate connector modules.
    For Part 1, we'll return sample data.
    
    Args:
        filters: Dictionary containing filter parameters
    
    Returns:
        DataFrame containing filtered test cases
    """
    # Create sample data
    if 'test_cases_df' not in st.session_state:
        st.session_state.test_cases_df = create_sample_test_cases()
    
    df = st.session_state.test_cases_df.copy()
    
    # Apply filters
    if filters.get('search_query'):
        query = filters['search_query'].lower()
        df = df[df['ID'].astype(str).str.lower().str.contains(query) | 
                df['Title'].str.lower().str.contains(query)]
    
    if filters.get('repository_filter'):
        df = df[df['Repository'].isin(filters['repository_filter'])]
    
    if filters.get('status_filter'):
        df = df[df['Status'].isin(filters['status_filter'])]
    
    if filters.get('type_filter'):
        df = df[df['Type'].isin(filters['type_filter'])]
    
    return df


def export_test_case(test_id: str):
    """Export a test case to Excel
    
    Args:
        test_id: ID of the test case to export
    """
    # In a real implementation, this would fetch the test case and export it
    if 'test_cases_df' in st.session_state:
        df = st.session_state.test_cases_df
        test_case = df[df['ID'] == test_id]
        
        if not test_case.empty:
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                test_case.to_excel(writer, index=False)
            excel_data = output.getvalue()
            
            # Provide download button
            st.download_button(
                label="Download Test Case",
                data=excel_data,
                file_name=f"TestCase_{test_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success(f"Test case {test_id} exported successfully")
        else:
            st.error(f"Test case {test_id} not found")
    else:
        st.error("Test case data not available")


def create_sample_test_cases() -> pd.DataFrame:
    """Create a sample dataframe of test cases for demonstration
    
    Returns:
        DataFrame containing sample test cases
    """
    data = {
        'ID': ['TC1001', 'TC1002', 'TC1003', 'TC1004', 'TC1005', 'TC1006', 'TC1007', 'TC1008'],
        'Title': [
            'Login Authentication Test', 
            'User Profile Update Test',
            'Password Reset Test',
            'User Registration Test',
            'Logout Function Test',
            'Email Notification Test',
            'Payment Processing Test',
            'Search Functionality Test'
        ],
        'Status': [
            'Active', 
            'Active',
            'Under Maintenance',
            'Active',
            'Active',
            'Obsolete',
            'Active',
            'Active'
        ],
        'Owner': [
            'Jane Smith', 
            'John Doe',
            'Alice Brown',
            'Robert Lee',
            'Mary Johnson',
            'David Wilson',
            'Sarah Adams',
            'Michael Chen'
        ],
        'Type': [
            'Automated', 
            'Automated',
            'Manual',
            'Manual',
            'Automated',
            'Manual',
            'Automated',
            'Manual'
        ],
        'Last Modified': [
            '2025-04-10', 
            '2025-04-12',
            '2025-04-15',
            '2025-04-18',
            '2025-04-20',
            '2025-03-30',
            '2025-04-22',
            '2025-04-25'
        ],
        'Repository': [
            'SharePoint',
            'SharePoint',
            'JIRA',
            'SharePoint',
            'ALM',
            'SharePoint',
            'SharePoint',
            'JIRA'
        ]
    }
    
    df = pd.DataFrame(data)
    return df


def display_comparison_results():
    """Display comparison results between suggested and existing test cases
    This will be implemented in Part 4-6
    """
    st.info("Comparison Results functionality will be implemented in Parts 4-6")


def display_tracking_lists():
    """Display tracking lists for matched, modified, and new test cases
    This will be implemented in Part 7-8
    """
    st.info("Tracking Lists functionality will be implemented in Parts 7-8")


if __name__ == "__main__":
    # When run directly, display the repository UI
    st.set_page_config(page_title="Test Repository & Comparison Module", layout="wide")
    
    # Initialize session state for user
    if 'user_name' not in st.session_state:
        st.session_state.user_name = "Demo User"  # In real app, this would come from authentication
    
    display_repository_ui()

# PART 2: Advanced Repository Browser
# This part extends the basic repository browser with advanced functionality

# Add these imports to the existing imports section
from src.phase1.sharepoint_connector.api.sharepoint_api_service import (
    get_sharepoint_api_status,
    initialize_sharepoint_api_client
)
from src.phase1.coverage_analyzer.gap_analyzer import (
    analyze_coverage_gaps,
    suggest_new_test_cases
)
from src.phase1.coverage_analyzer.api.coverage_api_service import get_coverage_api_status


# This function should replace the basic display_repository_browser from Part 1
def display_repository_browser():
    """Display the repository browser with advanced features and filtering"""
    st.header("Repository Browser")
    
    # Display connection status indicators with enhanced functionality
    display_connection_status_panel()
    
    # Display repository statistics if connected to repositories
    if check_repository_availability():
        display_repository_statistics()
    
    # Advanced search and filter section
    st.subheader("Search and Filter")
    display_advanced_filter_panel()
    
    # Repository scanning and analysis tools
    if check_repository_availability():
        display_repository_scan_tools()
    
    # Display test cases based on filter state
    if 'filter_applied' in st.session_state and st.session_state.filter_applied:
        display_enhanced_test_cases_table(st.session_state.current_filters)
    else:
        st.info("Apply filters above to view test cases. Use advanced options for more specific searches.")


def display_connection_status_panel():
    """Display enhanced connection status panel with authentication options"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Check SharePoint connection with enhanced status
        sharepoint_status = check_sharepoint_connection()
        api_status = get_sharepoint_api_status()
        
        if sharepoint_status and api_status:
            ui_utils.display_connection_status("SharePoint", True, "Fully Connected")
        elif sharepoint_status:
            ui_utils.display_connection_status("SharePoint", True, "Connected (API Limited)")
        else:
            ui_utils.display_connection_status("SharePoint", False, "Disconnected")
        
        # Add authentication options if disconnected
        if not sharepoint_status and st.button("Connect to SharePoint"):
            with st.form("sharepoint_auth_form"):
                sp_url = st.text_input("SharePoint URL")
                sp_username = st.text_input("Username")
                sp_password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Connect")
                
                if submitted:
                    with st.spinner("Authenticating with SharePoint..."):
                        try:
                            # Call SharePoint authentication function
                            auth_result = authenticate_sharepoint(sp_url, sp_username, sp_password)
                            # Initialize the SharePoint API client
                            initialize_sharepoint_api_client(sp_url, auth_result)
                            st.success("Authentication successful!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Authentication failed: {str(e)}")
    
    with col2:
        # Check JIRA connection with enhanced status
        jira_status = check_jira_connection()
        ui_utils.display_connection_status("JIRA", jira_status)
        
        if not jira_status and st.button("Connect to JIRA"):
            st.info("JIRA authentication will be implemented in a future update")
    
    with col3:
        # Check ALM connection with enhanced status
        alm_status = check_alm_connection()
        ui_utils.display_connection_status("ALM", alm_status)
        
        if not alm_status and st.button("Connect to ALM"):
            st.info("ALM authentication will be implemented in a future update")


def check_repository_availability():
    """Check if at least one repository is available
    
    Returns:
        bool: True if at least one repository is connected
    """
    sharepoint_status = check_sharepoint_connection()
    jira_status = check_jira_connection()
    alm_status = check_alm_connection()
    
    return any([sharepoint_status, jira_status, alm_status])


def display_repository_statistics():
    """Display statistics about the test case repositories"""
    try:
        # Get repository statistics using Coverage Analyzer
        with st.spinner("Loading repository statistics..."):
            # In a real implementation, this would call the actual function
            # For now, we'll create mock statistics
            stats = get_mock_repository_statistics()
            
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            with stats_col1:
                st.metric("Total Test Cases", stats.get("total_test_cases", 0))
            with stats_col2:
                st.metric("Automated Tests", stats.get("automated_tests", 0))
            with stats_col3:
                st.metric("Manual Tests", stats.get("manual_tests", 0))
            with stats_col4:
                st.metric("Coverage Score", f"{stats.get('coverage_percentage', 0)}%")
    except Exception as e:
        st.warning(f"Could not load repository statistics: {str(e)}")


def get_mock_repository_statistics():
    """Create mock repository statistics for demonstration
    
    In a real implementation, this would call get_repository_statistics()
    
    Returns:
        Dict containing repository statistics
    """
    # Get totals from the sample test cases if available
    if 'test_cases_df' in st.session_state:
        df = st.session_state.test_cases_df
        total = len(df)
        automated = len(df[df['Type'] == 'Automated'])
        manual = len(df[df['Type'] == 'Manual'])
        active = len(df[df['Status'] == 'Active'])
        coverage = int((active / total) * 100) if total > 0 else 0
    else:
        # Default values if no data is available
        total = 120
        automated = 75
        manual = 45
        coverage = 85
    
    return {
        "total_test_cases": total,
        "automated_tests": automated,
        "manual_tests": manual,
        "active_test_cases": active if 'active' in locals() else 95,
        "coverage_percentage": coverage
    }


def display_advanced_filter_panel():
    """Display advanced filter options for the repository browser"""
    with st.form("advanced_repository_search_form"):
        # Basic filters section
        basic_col1, basic_col2 = st.columns(2)
        
        with basic_col1:
            search_query = st.text_input("Search by ID or Keyword")
            
            repository_filter = st.multiselect(
                "Repository Source",
                ["SharePoint", "JIRA", "ALM"],
                default=["SharePoint"]
            )
        
        with basic_col2:
            status_filter = st.multiselect(
                "Status",
                ["Active", "Under Maintenance", "Obsolete"],
                default=["Active"]
            )
            
            type_filter = st.multiselect(
                "Type",
                ["Manual", "Automated"],
                default=["Manual", "Automated"]
            )
        
        # Advanced filters in expander
        with st.expander("Advanced Filters", expanded=False):
            adv_col1, adv_col2 = st.columns(2)
            
            with adv_col1:
                owner_filter = st.text_input("Owner")
                
                date_range = st.date_input(
                    "Modified Date Range",
                    value=(datetime.now().date().replace(month=datetime.now().month-1), datetime.now().date()),
                    format="MM/DD/YYYY"
                )
            
            with adv_col2:
                keyword_filters = st.text_input("Keywords (comma separated)")
                exclude_keywords = st.text_input("Exclude Keywords (comma separated)")
                
                # Test execution status filter
                execution_status = st.multiselect(
                    "Execution Status",
                    ["Not Executed", "Passed", "Failed", "Blocked"],
                    default=[]
                )
            
            # Coverage filter
            coverage_threshold = st.slider("Minimum Coverage Percentage", 0, 100, 0)
        
        submitted = st.form_submit_button("Apply Filters")
    
    # Process form submission
    if submitted:
        # Store filter state
        st.session_state.filter_applied = True
        st.session_state.current_filters = {
            "search_query": search_query,
            "repository_filter": repository_filter,
            "status_filter": status_filter,
            "type_filter": type_filter,
            "owner_filter": owner_filter if 'owner_filter' in locals() else "",
            "date_range": date_range if 'date_range' in locals() else None,
            "keyword_filters": keyword_filters.split(",") if 'keyword_filters' in locals() and keyword_filters else [],
            "exclude_keywords": exclude_keywords.split(",") if 'exclude_keywords' in locals() and exclude_keywords else [],
            "execution_status": execution_status if 'execution_status' in locals() else [],
            "coverage_threshold": coverage_threshold if 'coverage_threshold' in locals() else 0
        }
        
        # Create a hash of the filters for caching
        import hashlib
        filter_hash = hashlib.md5(json.dumps(st.session_state.current_filters, sort_keys=True, default=str).encode()).hexdigest()
        st.session_state.last_filter_hash = filter_hash


def display_repository_scan_tools():
    """Display tools for scanning repositories and analyzing coverage"""
    with st.expander("Repository Scan Options", expanded=False):
        st.info("Scan repositories to update test case information and analyze coverage.")
        
        scan_col1, scan_col2, scan_col3 = st.columns(3)
        
        with scan_col1:
            if st.button("Scan SharePoint Repository"):
                with st.spinner("Scanning SharePoint repository..."):
                    # This would call the actual repository scanner in a real implementation
                    # For now, we'll simulate the operation
                    import time
                    time.sleep(2)  # Simulate processing time
                    
                    # Update the session state
                    st.session_state.last_scan_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Display success message
                    st.success("Scan complete! Test case repository updated.")
        
        with scan_col2:
            if st.button("Analyze Coverage Gaps"):
                with st.spinner("Analyzing coverage gaps..."):
                    # This would call the actual gap analyzer in a real implementation
                    # For now, we'll simulate the operation
                    import time
                    time.sleep(2)  # Simulate processing time
                    
                    # Create mock analysis results
                    gap_analysis = {
                        "gaps_found": 12,
                        "coverage_areas": {
                            "login_module": 95,
                            "user_management": 87,
                            "payment_processing": 68,
                            "reporting": 45
                        },
                        "recommendations": [
                            "Add more test cases for the reporting module",
                            "Enhance payment processing error scenario coverage"
                        ]
                    }
                    
                    # Store results in session state
                    st.session_state.gap_analysis = gap_analysis
                    
                    # Display summary
                    st.warning(f"Found {gap_analysis['gaps_found']} potential coverage gaps.")
                    
                    # Show detailed analysis in an expander
                    with st.expander("Gap Analysis Details", expanded=True):
                        st.subheader("Coverage by Area")
                        for area, coverage in gap_analysis['coverage_areas'].items():
                            st.markdown(f"**{area.replace('_', ' ').title()}**: {coverage}% covered")
                        
                        st.subheader("Recommendations")
                        for rec in gap_analysis['recommendations']:
                            st.markdown(f"- {rec}")
        
        with scan_col3:
            if st.button("Suggest New Test Cases"):
                with st.spinner("Generating test case suggestions..."):
                    # This would call the actual suggestion function in a real implementation
                    # For now, we'll simulate the operation
                    import time
                    time.sleep(2)  # Simulate processing time
                    
                    # Create mock suggestions
                    suggested_cases = [
                        {
                            "id": "SUG001",
                            "title": "Report Export Error Handling",
                            "description": "Test case to verify proper error handling when report export fails",
                            "priority": "High",
                            "module": "Reporting",
                            "gap_addressed": "Error handling in reporting module"
                        },
                        {
                            "id": "SUG002",
                            "title": "Payment Processing Timeout Recovery",
                            "description": "Test case to verify system recovery after payment processing timeout",
                            "priority": "Medium",
                            "module": "Payment",
                            "gap_addressed": "Payment processing error scenarios"
                        }
                    ]
                    
                    # Store suggestions in session state
                    st.session_state.suggested_cases = suggested_cases
                    
                    # Display suggestions
                    st.success(f"Generated {len(suggested_cases)} test case suggestions!")
                    
                    # Show suggestions in a table
                    suggestions_df = pd.DataFrame(suggested_cases)
                    st.dataframe(suggestions_df)
    
    # Display last scan time if available
    if 'last_scan_time' in st.session_state:
        st.caption(f"Last repository scan: {st.session_state.last_scan_time}")


def display_enhanced_test_cases_table(filters: Dict[str, Any]):
    """Display an enhanced table of test cases with applied filters
    
    Args:
        filters: Dictionary containing filter parameters
    """
    with st.spinner("Fetching test cases..."):
        try:
            # Fetch data based on filters
            df = fetch_test_cases_with_advanced_filters(filters)
            
            if not df.empty:
                # Enhance the dataframe with visual indicators
                display_df = enhance_test_case_display(df)
                
                # Display the enhanced dataframe
                st.dataframe(
                    display_df,
                    column_config={
                        "ID": st.column_config.TextColumn("ID", width="small"),
                        "Title": st.column_config.TextColumn("Title", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                        "Owner": st.column_config.TextColumn("Owner", width="small"),
                        "Type": st.column_config.TextColumn("Type", width="small"),
                        "Last Modified": st.column_config.DateColumn("Last Modified", format="MM/DD/YYYY", width="small"),
                        "Repository": st.column_config.TextColumn("Repository", width="small"),
                        "Coverage": st.column_config.TextColumn("Coverage", width="small") if "Coverage" in display_df.columns else None,
                        "Execution Status": st.column_config.TextColumn("Execution Status", width="small") if "Execution Status" in display_df.columns else None
                    },
                    hide_index=True,
                    height=400
                )
                
                # Display statistics about results
                stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
                with stats_col1:
                    st.metric("Total Results", len(df))
                with stats_col2:
                    automated_count = len(df[df['Type'] == 'Automated'])
                    st.metric("Automated", automated_count)
                with stats_col3:
                    manual_count = len(df[df['Type'] == 'Manual'])
                    st.metric("Manual", manual_count)
                with stats_col4:
                    active_count = len(df[df['Status'] == 'Active'])
                    st.metric("Active", active_count)
                
                # Export options
                if st.button("Export Results to Excel"):
                    # Create Excel file in memory
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    excel_data = output.getvalue()
                    
                    # Provide download button
                    st.download_button(
                        label="Download Excel File",
                        data=excel_data,
                        file_name=f"test_cases_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                # Test case selection for actions
                st.subheader("Test Case Actions")
                
                selected_test_id = st.selectbox(
                    "Select Test Case for Actions", 
                    df['ID'].tolist(),
                    format_func=lambda x: f"{x} - {df[df['ID'] == x]['Title'].values[0]}"
                )
                
                if selected_test_id:
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        if st.button("View Details"):
                            st.info(f"View details functionality for {selected_test_id} will be implemented in Part 3")
                    
                    with action_col2:
                        if st.button("Compare with Repository"):
                            st.info(f"Comparison functionality for {selected_test_id} will be implemented in Parts 4-6")
                    
                    with action_col3:
                        if st.button("View Coverage Analysis"):
                            st.info(f"Coverage analysis for {selected_test_id} will be implemented in Part 3")
            else:
                st.warning("No test cases found matching your criteria.")
        
        except Exception as e:
            st.error(f"Error retrieving test cases: {str(e)}")
            st.info("Please check your connection to the repositories and try again.")


def fetch_test_cases_with_advanced_filters(filters: Dict[str, Any]) -> pd.DataFrame:
    """Fetch test cases based on advanced filters
    
    Args:
        filters: Dictionary containing filter parameters
    
    Returns:
        DataFrame containing filtered test cases
    """
    # Create or retrieve sample data
    if 'test_cases_df' not in st.session_state:
        st.session_state.test_cases_df = create_sample_test_cases_enhanced()
    
    df = st.session_state.test_cases_df.copy()
    
    # Apply basic filters
    if filters.get('search_query'):
        query = filters['search_query'].lower()
        df = df[df['ID'].astype(str).str.lower().str.contains(query) | 
                df['Title'].str.lower().str.contains(query)]
    
    if filters.get('repository_filter'):
        df = df[df['Repository'].isin(filters['repository_filter'])]
    
    if filters.get('status_filter'):
        df = df[df['Status'].isin(filters['status_filter'])]
    
    if filters.get('type_filter'):
        df = df[df['Type'].isin(filters['type_filter'])]
    
    # Apply advanced filters
    if filters.get('owner_filter'):
        owner = filters['owner_filter'].lower()
        df = df[df['Owner'].str.lower().str.contains(owner)]
    
    if filters.get('date_range') and len(filters['date_range']) == 2:
        # Convert the datetime.date objects to pandas datetime format
        start_date = pd.to_datetime(filters['date_range'][0])
        end_date = pd.to_datetime(filters['date_range'][1])
        
        # Convert the 'Last Modified' column to datetime if it's not already
        if not pd.api.types.is_datetime64_dtype(df['Last Modified']):
            df['Last Modified'] = pd.to_datetime(df['Last Modified'])
        
        # Filter by date range
        df = df[(df['Last Modified'] >= start_date) & (df['Last Modified'] <= end_date)]
    
    if filters.get('keyword_filters'):
        for keyword in filters['keyword_filters']:
            if keyword.strip():  # Skip empty keywords
                df = df[df['Title'].str.lower().str.contains(keyword.lower()) | 
                        df['Description'].str.lower().str.contains(keyword.lower()) if 'Description' in df.columns else True]
    
    if filters.get('exclude_keywords'):
        for keyword in filters['exclude_keywords']:
            if keyword.strip():  # Skip empty keywords
                df = df[~df['Title'].str.lower().str.contains(keyword.lower()) & 
                        (~df['Description'].str.lower().str.contains(keyword.lower()) if 'Description' in df.columns else True)]
    
    if filters.get('execution_status') and len(filters['execution_status']) > 0 and 'Execution Status' in df.columns:
        df = df[df['Execution Status'].isin(filters['execution_status'])]
    
    if filters.get('coverage_threshold') > 0 and 'Coverage' in df.columns:
        df = df[df['Coverage'] >= filters['coverage_threshold']]
    
    return df


def enhance_test_case_display(df: pd.DataFrame) -> pd.DataFrame:
    """Enhance the test case dataframe with visual indicators
    
    Args:
        df: Original dataframe of test cases
    
    Returns:
        Enhanced dataframe with visual indicators
    """
    # Create a copy to avoid modifying the original
    enhanced_df = df.copy()
    
    # Add visual indicators for status
    if 'Status' in enhanced_df.columns:
        enhanced_df['Status'] = enhanced_df['Status'].apply(
            lambda x: f"{'✅' if x == 'Active' else '🔄' if x == 'Under Maintenance' else '❌'} {x}"
        )
    
    # Add visual indicators for execution status if it exists
    if 'Execution Status' in enhanced_df.columns:
        enhanced_df['Execution Status'] = enhanced_df['Execution Status'].apply(
            lambda x: f"{'✅' if x == 'Passed' else '❌' if x == 'Failed' else '⏳' if x == 'Not Executed' else '⚠️'} {x}"
        )
    
    # Add visual indicators for coverage if it exists
    if 'Coverage' in enhanced_df.columns:
        enhanced_df['Coverage'] = enhanced_df['Coverage'].apply(
            lambda x: f"{x}% {'🟢' if x >= 90 else '🟡' if x >= 70 else '🔴'}"
        )
    
    return enhanced_df


def create_sample_test_cases_enhanced() -> pd.DataFrame:
    """Create an enhanced sample dataframe of test cases for demonstration
    
    Returns:
        DataFrame containing sample test cases with additional columns
    """
    # Start with the basic sample data
    df = create_sample_test_cases()
    
    # Add description column
    descriptions = [
        "Verify user authentication with valid credentials",
        "Verify user can update profile information",
        "Verify password reset functionality",
        "Verify new user registration process",
        "Verify user logout functionality",
        "Verify email notifications are sent correctly",
        "Verify payment processing workflow",
        "Verify search functionality returns correct results"
    ]
    df['Description'] = descriptions
    
    # Add coverage column
    coverage_values = [95, 87, 75, 92, 88, 60, 82, 78]
    df['Coverage'] = coverage_values
    
    # Add execution status
    execution_statuses = [
        "Passed", "Failed", "Not Executed", "Passed", 
        "Blocked", "Not Executed", "Passed", "Not Executed"
    ]
    df['Execution Status'] = execution_statuses
    
    return df

#######################################################
# PART 3: TEST CASE DETAILS VIEW
#######################################################

# Import additional modules needed for Part 3
from src.phase1.sharepoint_connector.document_retriever import get_document_by_id
from src.phase1.sharepoint_connector.sharepoint_version_manager import get_version_history
from src.phase1.coverage_analyzer.gap_analyzer import get_coverage_metrics
from src.phase2.rpa_controller.controller_manager import schedule_test_execution
from src.phase1.test_data_manager.data_generator import generate_test_data


def display_test_case_details(test_id: str):
    """Display detailed view of a test case
    
    Args:
        test_id: ID of the test case to display
    """
    st.subheader(f"Test Case Details: {test_id}")
    
    with st.spinner("Loading test case details..."):
        try:
            # Fetch test case details
            test_case = fetch_test_case_details(test_id)
            
            if test_case:
                # Display test case information in tabs
                detail_tabs = st.tabs(["Overview", "Steps", "Version History", "Coverage Analysis", "Execution History"])
                
                with detail_tabs[0]:
                    display_test_case_overview(test_case)
                
                with detail_tabs[1]:
                    display_test_case_steps(test_case)
                
                with detail_tabs[2]:
                    display_version_history(test_case)
                
                with detail_tabs[3]:
                    display_coverage_analysis(test_case)
                
                with detail_tabs[4]:
                    display_execution_history(test_case)
                
                # Display action buttons
                display_test_case_actions(test_case)
            else:
                st.error(f"Could not retrieve details for test case {test_id}")
        
        except Exception as e:
            st.error(f"Error loading test case details: {str(e)}")


def fetch_test_case_details(test_id: str) -> Dict[str, Any]:
    """Fetch detailed information about a test case
    
    In a real implementation, this would call the appropriate connector module
    based on the repository where the test case is stored.
    
    Args:
        test_id: ID of the test case to fetch
    
    Returns:
        Dictionary containing test case details
    """
    # In a real implementation, this would determine the repository and call the appropriate connector
    # For now, we'll use sample data from session state
    if 'test_cases_df' in st.session_state:
        df = st.session_state.test_cases_df
        test_case_row = df[df['ID'] == test_id]
        
        if not test_case_row.empty:
            # Get the basic information from the dataframe
            basic_info = test_case_row.iloc[0].to_dict()
            
            # Add additional mock data for demonstration
            repository = basic_info.get('Repository', 'SharePoint')
            test_case_type = basic_info.get('Type', 'Manual')
            
            # Create enhanced test case details
            test_case = {
                **basic_info,
                'Description': f"Detailed description for {basic_info['Title']}",
                'Preconditions': "Application is running and user has valid credentials",
                'Steps': generate_mock_steps(test_id, test_case_type),
                'Version': "1.2",
                'Created Date': "2025-01-15",
                'Last Updated': basic_info.get('Last Modified', "2025-04-20"),
                'Tags': ["regression", "smoke-test", "ui"],
                'Priority': "High",
                'Version History': generate_mock_version_history(test_id),
                'Coverage': generate_mock_coverage_data(test_id),
                'Execution History': generate_mock_execution_history(test_id, test_case_type),
                'Related Requirements': ["REQ001", "REQ005"],
                'Attachments': ["screenshot1.png", "testdata.xlsx"]
            }
            
            return test_case
    
    # If we couldn't find the test case
    return None


def display_test_case_overview(test_case: Dict[str, Any]):
    """Display an overview of the test case details
    
    Args:
        test_case: Dictionary containing test case details
    """
    # Display test case metadata
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### {test_case['Title']}")
        st.markdown(f"**Description:** {test_case.get('Description', 'No description available')}")
        st.markdown(f"**ID:** {test_case['ID']}")
        st.markdown(f"**Repository:** {test_case.get('Repository', 'Unknown')}")
        st.markdown(f"**Status:** {test_case.get('Status', 'Unknown')}")
        st.markdown(f"**Owner:** {test_case.get('Owner', 'Unassigned')}")
    
    with col2:
        st.markdown(f"**Type:** {test_case.get('Type', 'Unknown')}")
        st.markdown(f"**Priority:** {test_case.get('Priority', 'Medium')}")
        st.markdown(f"**Created:** {test_case.get('Created Date', 'Unknown')}")
        st.markdown(f"**Last Updated:** {test_case.get('Last Updated', 'Unknown')}")
        st.markdown(f"**Version:** {test_case.get('Version', '1.0')}")
        
        # Display tags if available
        if 'Tags' in test_case and test_case['Tags']:
            tags_html = " ".join([f"<span style='background-color: #f0f0f0; padding: 2px 8px; border-radius: 10px; margin-right: 5px;'>{tag}</span>" for tag in test_case['Tags']])
            st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)
    
    # Display preconditions
    st.markdown("#### Preconditions")
    st.markdown(test_case.get('Preconditions', 'None specified'))
    
    # Display related requirements if available
    if 'Related Requirements' in test_case and test_case['Related Requirements']:
        st.markdown("#### Related Requirements")
        for req in test_case['Related Requirements']:
            st.markdown(f"- {req}")
    
    # Display attachments if available
    if 'Attachments' in test_case and test_case['Attachments']:
        st.markdown("#### Attachments")
        for attachment in test_case['Attachments']:
            st.markdown(f"- {attachment}")


def display_test_case_steps(test_case: Dict[str, Any]):
    """Display the steps of the test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Test Steps")
    
    if 'Steps' in test_case and test_case['Steps']:
        # Create a formatted table of steps
        steps_data = []
        
        for step in test_case['Steps']:
            steps_data.append({
                "Step #": step.get('number', ''),
                "Action": step.get('action', ''),
                "Expected Result": step.get('expected', ''),
                "Test Data": step.get('test_data', '')
            })
        
        # Display as a dataframe
        steps_df = pd.DataFrame(steps_data)
        st.dataframe(
            steps_df,
            column_config={
                "Step #": st.column_config.NumberColumn("Step #", width="small"),
                "Action": st.column_config.TextColumn("Action", width="medium"),
                "Expected Result": st.column_config.TextColumn("Expected Result", width="medium"),
                "Test Data": st.column_config.TextColumn("Test Data", width="medium")
            },
            hide_index=True
        )
    else:
        st.info("No steps defined for this test case.")


def display_version_history(test_case: Dict[str, Any]):
    """Display the version history of the test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Version History")
    
    if 'Version History' in test_case and test_case['Version History']:
        # Create a formatted table of versions
        versions_df = pd.DataFrame(test_case['Version History'])
        
        st.dataframe(
            versions_df,
            column_config={
                "version": st.column_config.TextColumn("Version", width="small"),
                "date": st.column_config.DateColumn("Date", format="MM/DD/YYYY", width="small"),
                "author": st.column_config.TextColumn("Author", width="medium"),
                "changes": st.column_config.TextColumn("Changes", width="large")
            },
            hide_index=True
        )
        
        # Add option to view differences
        if len(test_case['Version History']) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                version1 = st.selectbox(
                    "Select First Version", 
                    options=[v["version"] for v in test_case['Version History']],
                    key="version1"
                )
            
            with col2:
                version2 = st.selectbox(
                    "Select Second Version", 
                    options=[v["version"] for v in test_case['Version History']],
                    key="version2"
                )
            
            if st.button("Compare Versions"):
                if version1 != version2:
                    with st.spinner("Generating version comparison..."):
                        # In a real implementation, this would fetch and compare the versions
                        st.info(f"Version comparison between {version1} and {version2} will be added in a future update")
                else:
                    st.warning("Please select different versions to compare")
    else:
        st.info("No version history available for this test case.")


def display_coverage_analysis(test_case: Dict[str, Any]):
    """Display coverage analysis for the test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Coverage Analysis")
    
    if 'Coverage' in test_case and test_case['Coverage']:
        coverage = test_case['Coverage']
        
        # Display coverage score
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Overall Coverage", f"{coverage.get('overall', 0)}%")
        
        with col2:
            st.metric("Requirement Coverage", f"{coverage.get('requirements', 0)}%")
        
        with col3:
            st.metric("Function Coverage", f"{coverage.get('functional', 0)}%")
        
        # Display coverage details
        st.markdown("#### Coverage Details")
        
        if 'details' in coverage and coverage['details']:
            # Create a formatted table of coverage details
            details_df = pd.DataFrame(coverage['details'])
            
            st.dataframe(
                details_df,
                column_config={
                    "area": st.column_config.TextColumn("Area", width="medium"),
                    "coverage": st.column_config.ProgressColumn("Coverage", width="medium", format="%d%%", min_value=0, max_value=100),
                    "notes": st.column_config.TextColumn("Notes", width="large")
                },
                hide_index=True
            )
        
        # Display coverage gaps
        if 'gaps' in coverage and coverage['gaps']:
            st.markdown("#### Coverage Gaps")
            for gap in coverage['gaps']:
                st.markdown(f"- {gap}")
        
        # Display recommendations
        if 'recommendations' in coverage and coverage['recommendations']:
            st.markdown("#### Recommendations")
            for rec in coverage['recommendations']:
                st.markdown(f"- {rec}")
    else:
        st.info("No coverage analysis available for this test case.")


def display_execution_history(test_case: Dict[str, Any]):
    """Display execution history for the test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Execution History")
    
    if 'Execution History' in test_case and test_case['Execution History']:
        # Create a formatted table of execution history
        history_df = pd.DataFrame(test_case['Execution History'])
        
        # Add status indicator
        history_df['status_display'] = history_df['status'].apply(
            lambda x: f"{'✅' if x == 'Passed' else '❌' if x == 'Failed' else '⚠️' if x == 'Blocked' else '⏳'} {x}"
        )
        
        # Display the dataframe
        st.dataframe(
            history_df,
            column_config={
                "execution_id": st.column_config.TextColumn("Execution ID", width="medium"),
                "date": st.column_config.DateColumn("Date", format="MM/DD/YYYY", width="small"),
                "environment": st.column_config.TextColumn("Environment", width="small"),
                "status_display": st.column_config.TextColumn("Status", width="small"),
                "executed_by": st.column_config.TextColumn("Executed By", width="medium"),
                "duration": st.column_config.TextColumn("Duration", width="small")
            },
            hide_index=True
        )
        
        # Option to view execution details
        if len(test_case['Execution History']) > 0:
            selected_execution = st.selectbox(
                "Select Execution for Details", 
                options=[e["execution_id"] for e in test_case['Execution History']],
                format_func=lambda x: f"{x} - {next((e['date'] for e in test_case['Execution History'] if e['execution_id'] == x), '')}"
            )
            
            if st.button("View Execution Details"):
                # Find the selected execution
                execution = next((e for e in test_case['Execution History'] if e['execution_id'] == selected_execution), None)
                
                if execution:
                    with st.expander("Execution Details", expanded=True):
                        st.markdown(f"**Execution ID:** {execution['execution_id']}")
                        st.markdown(f"**Date:** {execution['date']}")
                        st.markdown(f"**Status:** {execution['status']}")
                        st.markdown(f"**Environment:** {execution['environment']}")
                        st.markdown(f"**Executed By:** {execution['executed_by']}")
                        st.markdown(f"**Duration:** {execution['duration']}")
                        
                        # Display execution results
                        if 'results' in execution and execution['results']:
                            st.markdown("#### Step Results")
                            results_df = pd.DataFrame(execution['results'])
                            
                            # Add status indicator
                            results_df['status_display'] = results_df['status'].apply(
                                lambda x: f"{'✅' if x == 'Passed' else '❌' if x == 'Failed' else '⚠️'} {x}"
                            )
                            
                            st.dataframe(
                                results_df,
                                column_config={
                                    "step": st.column_config.NumberColumn("Step #", width="small"),
                                    "status_display": st.column_config.TextColumn("Status", width="small"),
                                    "notes": st.column_config.TextColumn("Notes", width="large")
                                },
                                hide_index=True
                            )
                        
                        # Display any screenshots or attachments
                        if 'screenshots' in execution and execution['screenshots']:
                            st.markdown("#### Screenshots")
                            for screenshot in execution['screenshots']:
                                st.markdown(f"- {screenshot}")
    else:
        st.info("No execution history available for this test case.")


def display_test_case_actions(test_case: Dict[str, Any]):
    """Display action buttons for the test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Actions")
    
    # Create columns for actions
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Edit button
        if st.button("Edit Test Case"):
            st.session_state.edit_test_case = test_case['ID']
            st.info(f"Edit functionality for test case {test_case['ID']} will be implemented in a future update")
    
    with col2:
        # Execute button (for automated test cases)
        if test_case.get('Type') == 'Automated':
            if st.button("Execute Test"):
                with st.spinner("Preparing for test execution..."):
                    # Check if test data is available
                    test_data_available = check_test_data_availability(test_case['ID'])
                    
                    if test_data_available:
                        # Schedule execution with existing data
                        execution_id = schedule_automated_execution(test_case, use_existing_data=True)
                        st.success(f"Test execution scheduled! Execution ID: {execution_id}")
                    else:
                        # Ask if user wants to generate test data
                        if st.button("Generate Test Data & Execute"):
                            with st.spinner("Generating test data..."):
                                # Generate test data and then schedule execution
                                generate_test_data_for_testcase(test_case['ID'])
                                execution_id = schedule_automated_execution(test_case, use_existing_data=False)
                                st.success(f"Test data generated and execution scheduled! Execution ID: {execution_id}")
        else:
            # For manual test cases
            if st.button("Notify for Manual Execution"):
                with st.spinner(f"Notifying {test_case['Owner']}..."):
                    # Send notification to the owner
                    notification_sent = notify_owner_for_execution(test_case)
                    if notification_sent:
                        st.success(f"Notification sent to {test_case['Owner']}")
                    else:
                        st.error(f"Failed to send notification to {test_case['Owner']}")
    
    with col3:
        # Compare button
        if st.button("Compare with Repository"):
            st.session_state.compare_test_case = test_case['ID']
            st.info(f"Comparison functionality for {test_case['ID']} will be implemented in Parts 4-6")
    
    with col4:
        # Export button
        if st.button("Export Test Case"):
            export_detailed_test_case(test_case)


def schedule_automated_execution(test_case: Dict[str, Any], use_existing_data: bool = True) -> str:
    """Schedule the execution of an automated test case
    
    In a real implementation, this would call the RPA Controller module
    
    Args:
        test_case: Dictionary containing test case details
        use_existing_data: Whether to use existing test data or newly generated data
    
    Returns:
        Execution ID for the scheduled execution
    """
    # In a real implementation, this would call the RPA Controller module
    # For now, we'll create a mock execution ID
    import time
    execution_id = f"EX{int(time.time())}"
    
    # Add the execution to the history for demo purposes
    if 'Execution History' in test_case:
        new_execution = {
            "execution_id": execution_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "environment": "Test",
            "status": "Scheduled",
            "executed_by": st.session_state.user_name,
            "duration": "Pending"
        }
        
        test_case['Execution History'].insert(0, new_execution)
    
    return execution_id


def generate_test_data_for_testcase(test_id: str) -> bool:
    """Generate test data for a test case
    
    In a real implementation, this would call the Test Data Manager module
    
    Args:
        test_id: ID of the test case
    
    Returns:
        True if successful, False otherwise
    """
    # In a real implementation, this would call the Test Data Manager module
    # For now, we'll simulate success
    return True


def notify_owner_for_execution(test_case: Dict[str, Any]) -> bool:
    """Notify the owner to execute a manual test case
    
    In a real implementation, this would call the Notification Service module
    
    Args:
        test_case: Dictionary containing test case details
    
    Returns:
        True if notification was sent successfully, False otherwise
    """
    # In a real implementation, this would call the Notification Service module
    # For now, we'll simulate success
    return True


def export_detailed_test_case(test_case: Dict[str, Any]):
    """Export a detailed test case to Excel
    
    Args:
        test_case: Dictionary containing test case details
    """
    # Create a flattened version of the test case for Excel export
    flat_test_case = {
        "ID": test_case['ID'],
        "Title": test_case['Title'],
        "Description": test_case.get('Description', ''),
        "Status": test_case.get('Status', ''),
        "Type": test_case.get('Type', ''),
        "Owner": test_case.get('Owner', ''),
        "Repository": test_case.get('Repository', ''),
        "Priority": test_case.get('Priority', ''),
        "Version": test_case.get('Version', ''),
        "Created Date": test_case.get('Created Date', ''),
        "Last Updated": test_case.get('Last Updated', ''),
        "Preconditions": test_case.get('Preconditions', '')
    }
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    # Write basic information to one sheet and steps to another
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write basic information
        pd.DataFrame([flat_test_case]).to_excel(writer, sheet_name="Details", index=False)
        
        # Write steps if available
        if 'Steps' in test_case and test_case['Steps']:
            steps_df = pd.DataFrame(test_case['Steps'])
            steps_df.to_excel(writer, sheet_name="Steps", index=False)
        
        # Write version history if available
        if 'Version History' in test_case and test_case['Version History']:
            history_df = pd.DataFrame(test_case['Version History'])
            history_df.to_excel(writer, sheet_name="Version History", index=False)
        
        # Write execution history if available
        if 'Execution History' in test_case and test_case['Execution History']:
            exec_df = pd.DataFrame(test_case['Execution History'])
            exec_df.to_excel(writer, sheet_name="Execution History", index=False)
    
    # Provide download button
    st.download_button(
        label="Download Detailed Test Case",
        data=output.getvalue(),
        file_name=f"TestCase_{test_case['ID']}_Detailed.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.success(f"Detailed test case {test_case['ID']} exported successfully")


# Helper functions for generating mock data

def generate_mock_steps(test_id: str, test_type: str) -> List[Dict[str, Any]]:
    """Generate mock test steps for demonstration
    
    Args:
        test_id: ID of the test case
        test_type: Type of test case (Manual/Automated)
    
    Returns:
        List of test steps
    """
    # Create different steps based on the test ID
    if "Login" in test_id or "Authentication" in test_id:
        return [
            {"number": 1, "action": "Navigate to login page", "expected": "Login page is displayed", "test_data": "URL: /login"},
            {"number": 2, "action": "Enter valid username", "expected": "Username is accepted", "test_data": "Username: test_user"},
            {"number": 3, "action": "Enter valid password", "expected": "Password is accepted", "test_data": "Password: ******"},
            {"number": 4, "action": "Click login button", "expected": "User is logged in successfully", "test_data": ""},
            {"number": 5, "action": "Verify dashboard access", "expected": "Dashboard is displayed", "test_data": ""}
        ]
    elif "Profile" in test_id or "User" in test_id:
        return [
            {"number": 1, "action": "Login to the application", "expected": "User is logged in", "test_data": "Username: test_user, Password: ******"},
            {"number": 2, "action": "Navigate to profile page", "expected": "Profile page is displayed", "test_data": "URL: /profile"},
            {"number": 3, "action": "Update user information", "expected": "Information is updated", "test_data": "Name: Test User, Email: test@example.com"},
            {"number": 4, "action": "Save changes", "expected": "Changes are saved successfully", "test_data": ""},
            {"number": 5, "action": "Verify information is updated", "expected": "Updated information is displayed", "test_data": ""}
        ]
    elif "Payment" in test_id:
        return [
            {"number": 1, "action": "Navigate to payment page", "expected": "Payment page is displayed", "test_data": "URL: /payment"},
            {"number": 2, "action": "Enter payment details", "expected": "Payment details are accepted", "test_data": "Card: 4111111111111111, Exp: 12/25, CVV: 123"},
            {"number": 3, "action": "Submit payment", "expected": "Payment is processed", "test_data": "Amount: $99.99"},
            {"number": 4, "action": "Verify payment confirmation", "expected": "Confirmation is displayed", "test_data": ""},
            {"number": 5, "action": "Check payment status", "expected": "Status is 'Completed'", "test_data": ""}
        ]
    else:
        # Generic steps
        return [
            {"number": 1, "action": "Prepare test environment", "expected": "Environment is ready", "test_data": ""},
            {"number": 2, "action": "Perform main test action", "expected": "Action is executed successfully", "test_data": ""},
            {"number": 3, "action": "Verify results", "expected": "Expected results are observed", "test_data": ""},
            {"number": 4, "action": "Cleanup test environment", "expected": "Environment is restored", "test_data": ""}
        ]


def generate_mock_version_history(test_id: str) -> List[Dict[str, Any]]:
    """Generate mock version history for demonstration
    
    Args:
        test_id: ID of the test case
    
    Returns:
        List of version history entries
    """
    return [
        {"version": "1.2", "date": "2025-04-15", "author": "Jane Smith", "changes": "Updated expected results for step 3"},
        {"version": "1.1", "date": "2025-03-10", "author": "John Doe", "changes": "Added new step for verification"},
        {"version": "1.0", "date": "2025-01-15", "author": "Robert Lee", "changes": "Initial creation"}
    ]


def generate_mock_coverage_data(test_id: str) -> Dict[str, Any]:
    """Generate mock coverage data for demonstration
    
    Args:
        test_id: ID of the test case
    
    Returns:
        Dictionary containing coverage data
    """
    # Create coverage data based on the test ID
    if "Login" in test_id or "Authentication" in test_id:
        return {
            "overall": 92,
            "requirements": 95,
            "functional": 90,
            "details": [
                {"area": "Authentication Flow", "coverage": 95, "notes": "Good coverage of normal paths"},
                {"area": "Error Handling", "coverage": 85, "notes": "Some edge cases missing"},
                {"area": "Security Features", "coverage": 98, "notes": "Excellent security coverage"}
            ],
            "gaps": [
                "Missing test for account lockout after multiple failed attempts",
                "MFA verification not fully covered"
            ],
            "recommendations": [
                "Add test for account lockout scenario",
                "Enhance MFA testing coverage"
            ]
        }
    elif "Profile" in test_id or "User" in test_id:
        return {
            "overall": 85,
            "requirements": 90,
            "functional": 80,
            "details": [
                {"area": "Profile Management", "coverage": 88, "notes": "Good coverage of basic functionality"},
                {"area": "Data Validation", "coverage": 75, "notes": "Needs more boundary testing"},
                {"area": "UI Interactions", "coverage": 92, "notes": "Good UI test coverage"}
            ],
            "gaps": [
                "Limited testing of profile picture handling",
                "Missing validation for international addresses"
            ],
            "recommendations": [
                "Add tests for profile picture formats and sizes",
                "Enhance address validation testing"
            ]
        }
    else:
        # Generic coverage data
        return {
            "overall": 78,
            "requirements": 80,
            "functional": 75,
            "details": [
                {"area": "Core Functionality", "coverage": 85, "notes": "Good basic coverage"},
                {"area": "Error Handling", "coverage": 70, "notes": "Needs improvement"},
                {"area": "Edge Cases", "coverage": 65, "notes": "Limited edge case coverage"}
            ],
            "gaps": [
                "Limited error scenario testing",
                "Some edge cases not covered"
            ],
            "recommendations": [
                "Enhance error scenario testing",
                "Add more edge case tests"
            ]
        }


def generate_mock_execution_history(test_id: str, test_type: str) -> List[Dict[str, Any]]:
    """Generate mock execution history for demonstration
    
    Args:
        test_id: ID of the test case
        test_type: Type of test case (Manual/Automated)
    
    Returns:
        List of execution history entries
    """
    # Create different execution history based on the test type
    if test_type == "Automated":
        return [
            {
                "execution_id": "EX20250425001",
                "date": "2025-04-25",
                "environment": "Test",
                "status": "Passed",
                "executed_by": "Automation Service",
                "duration": "45s",
                "results": [
                    {"step": 1, "status": "Passed", "notes": "Completed in 5s"},
                    {"step": 2, "status": "Passed", "notes": "Completed in 10s"},
                    {"step": 3, "status": "Passed", "notes": "Completed in 15s"},
                    {"step": 4, "status": "Passed", "notes": "Completed in 10s"},
                    {"step": 5, "status": "Passed", "notes": "Completed in 5s"}
                ],
                "screenshots": ["login_page.png", "dashboard.png"]
            },
            {
                "execution_id": "EX20250410002",
                "date": "2025-04-10",
                "environment": "Test",
                "status": "Failed",
                "executed_by": "Automation Service",
                "duration": "38s",
                "results": [
                    {"step": 1, "status": "Passed", "notes": "Completed in 5s"},
                    {"step": 2, "status": "Passed", "notes": "Completed in 8s"},
                    {"step": 3, "status": "Failed", "notes": "Timeout waiting for response"},
                    {"step": 4, "status": "Skipped", "notes": "Skipped due to previous failure"},
                    {"step": 5, "status": "Skipped", "notes": "Skipped due to previous failure"}
                ],
                "screenshots": ["login_page.png", "error_screen.png"]
            },
            {
                "execution_id": "EX20250320003",
                "date": "2025-03-20",
                "environment": "Dev",
                "status": "Passed",
                "executed_by": "Automation Service",
                "duration": "42s",
                "results": [
                    {"step": 1, "status": "Passed", "notes": "Completed in 6s"},
                    {"step": 2, "status": "Passed", "notes": "Completed in 12s"},
                    {"step": 3, "status": "Passed", "notes": "Completed in 14s"},
                    {"step": 4, "status": "Passed", "notes": "Completed in 8s"},
                    {"step": 5, "status": "Passed", "notes": "Completed in 2s"}
                ],
                "screenshots": ["login_page.png", "dashboard.png"]
            }
        ]
    else:
        # Manual test case execution history
        return [
            {
                "execution_id": "MX20250422001",
                "date": "2025-04-22",
                "environment": "UAT",
                "status": "Passed",
                "executed_by": "Jane Smith",
                "duration": "15m",
                "results": [
                    {"step": 1, "status": "Passed", "notes": "Completed without issues"},
                    {"step": 2, "status": "Passed", "notes": "Entered all required information"},
                    {"step": 3, "status": "Passed", "notes": "System accepted the input"},
                    {"step": 4, "status": "Passed", "notes": "Confirmation displayed correctly"}
                ],
                "screenshots": ["step2_screenshot.png", "step4_screenshot.png"]
            },
            {
                "execution_id": "MX20250315002",
                "date": "2025-03-15",
                "environment": "QA",
                "status": "Failed",
                "executed_by": "John Doe",
                "duration": "20m",
                "results": [
                    {"step": 1, "status": "Passed", "notes": "Completed without issues"},
                    {"step": 2, "status": "Passed", "notes": "Entered all required information"},
                    {"step": 3, "status": "Failed", "notes": "System displayed unexpected error"},
                    {"step": 4, "status": "Skipped", "notes": "Skipped due to previous failure"}
                ],
                "screenshots": ["step2_screenshot.png", "error_screenshot.png"]
            }
        ]


# Update the existing display_test_cases_table function to integrate with the new test case details view
def update_test_cases_table_with_details_link():
    """
    This function isn't replacing any existing code.
    Instead, it should be used to update the implementation of display_test_cases_table
    or display_enhanced_test_cases_table to incorporate the new test case details view.
    """
    # Update the "View Details" button action in display_test_cases_table or display_enhanced_test_cases_table
    # to call display_test_case_details instead of showing a placeholder message
    
    # For example, in display_test_cases_table, replace:
    # if st.button("View Details"):
    #     st.session_state.view_test_case = selected_test_id
    #     st.info(f"View details functionality for {selected_test_id} will be implemented in Part 3")
    
    # With:
    # if st.button("View Details"):
    #     st.session_state.view_test_case = selected_test_id
    #     display_test_case_details(selected_test_id)
    
    # Similarly, update display_enhanced_test_cases_table if you're using that function
    pass


# Update the main display_repository_browser function to check for test case detail view requests
def check_for_test_case_detail_requests():
    """
    This function should be called at the beginning of display_repository_browser
    to check if a test case detail view has been requested.
    """
    # If a test case detail view has been requested, display it instead of the normal repository browser
    if 'view_test_case' in st.session_state and st.session_state.view_test_case:
        test_id = st.session_state.view_test_case
        
        # Add a back button
        if st.button("Back to Repository"):
            st.session_state.view_test_case = None
            st.rerun()
        
        # Display the test case details
        display_test_case_details(test_id)
        
        # Return True to indicate that we're displaying a test case detail view
        return True
    
    # Return False to indicate that we should display the normal repository browser
    return False


# This code integrates Part 3 with the existing repository browser implementation
# In real usage, you'd need to modify these functions:

# 1. Update display_repository_browser from Part 1/2 to include this at the beginning:
#    if check_for_test_case_detail_requests():
#        return

# 2. Update the "View Details" button action in display_test_cases_table or display_enhanced_test_cases_table:
#    if st.button("View Details"):
#        st.session_state.view_test_case = selected_test_id
#        st.rerun()  # This will trigger the check_for_test_case_detail_requests in the next render  
# 
# 
#######################################################
# PART 4: COMPARISON SETUP
#######################################################

# Import additional modules needed for Part 4
from src.phase1.sharepoint_connector.document_retriever import get_documents_by_filter
from src.phase1.llm_test_scenario_generator.scenario_generator import get_generated_scenarios
from src.phase1.coverage_analyzer.comparison_engine import prepare_comparison, get_comparison_settings
from src.phase1.test_case_manager.testcase_generator import get_generated_test_cases


def display_comparison_results():
    """Display comparison results between suggested and existing test cases"""
    st.header("Test Case Comparison")
    
    # Check if we're already in a specific comparison view
    if 'comparison_result' in st.session_state:
        # Display the appropriate comparison result view
        # (This will be implemented in Parts 5-6)
        st.info("Comparison result display will be implemented in Parts 5-6")
        
        # Add a button to return to comparison setup
        if st.button("Start New Comparison"):
            # Reset comparison state
            if 'comparison_result' in st.session_state:
                del st.session_state.comparison_result
            if 'comparison_details' in st.session_state:
                del st.session_state.comparison_details
            
            # Reload the page
            st.rerun()
    else:
        # Display the comparison setup interface
        display_comparison_setup()


def display_comparison_setup():
    """Display the interface for setting up a test case comparison"""
    # Create tabs for different comparison sources
    source_tabs = st.tabs([
        "Upload Test Case", 
        "Select from Generated", 
        "Select from Repository",
        "Manual Entry"
    ])
    
    with source_tabs[0]:
        setup_upload_comparison()
    
    with source_tabs[1]:
        setup_generated_comparison()
    
    with source_tabs[2]:
        setup_repository_comparison()
    
    with source_tabs[3]:
        setup_manual_comparison()
    
    # Display comparison settings if a test case has been selected
    if is_comparison_source_selected():
        display_comparison_settings()
        
        # Add button to start comparison
        if st.button("Run Comparison Analysis"):
            run_comparison_analysis()


def setup_upload_comparison():
    """Setup comparison with an uploaded test case file"""
    st.subheader("Upload Test Case File")
    
    # Instructions
    st.markdown("""
    Upload a test case file to compare with existing test cases in the repository.
    Supported formats: Excel (.xlsx, .xls), CSV (.csv), Word (.docx), JSON (.json)
    """)
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["xlsx", "xls", "csv", "docx", "json"],
        key="comparison_file_uploader"
    )
    
    if uploaded_file is not None:
        # Process the uploaded file
        with st.spinner("Processing uploaded test case..."):
            try:
                # Read the file content
                content = uploaded_file.read()
                
                # Save uploaded test case in session state
                st.session_state.comparison_source = {
                    "type": "uploaded",
                    "filename": uploaded_file.name,
                    "content": content,
                    "file_type": uploaded_file.name.split('.')[-1].lower()
                }
                
                # Parse and preview the file based on its type
                display_uploaded_file_preview(uploaded_file)
                
                # Indicate selection is complete
                st.success(f"File '{uploaded_file.name}' successfully processed for comparison")
            
            except Exception as e:
                st.error(f"Error processing uploaded file: {str(e)}")
                st.session_state.comparison_source = None


def display_uploaded_file_preview(uploaded_file):
    """Display a preview of the uploaded file
    
    Args:
        uploaded_file: The uploaded file object
    """
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    # Preview based on file type
    if file_extension in ['xlsx', 'xls']:
        # Parse Excel file
        import pandas as pd
        import io
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Read Excel into DataFrame
        df = pd.read_excel(io.BytesIO(uploaded_file.read()))
        
        # Store parsed data
        st.session_state.comparison_source["parsed_data"] = df.to_dict(orient='records')
        
        # Display preview
        st.subheader("File Preview")
        st.dataframe(df.head(5))
    
    elif file_extension == 'csv':
        # Parse CSV file
        import pandas as pd
        import io
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Read CSV into DataFrame
        df = pd.read_csv(io.BytesIO(uploaded_file.read()))
        
        # Store parsed data
        st.session_state.comparison_source["parsed_data"] = df.to_dict(orient='records')
        
        # Display preview
        st.subheader("File Preview")
        st.dataframe(df.head(5))
    
    elif file_extension == 'json':
        # Parse JSON file
        import json
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Read JSON data
        json_data = json.loads(uploaded_file.read().decode('utf-8'))
        
        # Store parsed data
        st.session_state.comparison_source["parsed_data"] = json_data
        
        # Display preview
        st.subheader("File Preview")
        st.json(json_data)
    
    elif file_extension == 'docx':
        # For Word documents, we'll need special processing
        st.subheader("Word Document")
        st.info("Word document detected. Content will be extracted for comparison.")
        
        # Mark that the file needs processing
        st.session_state.comparison_source["needs_processing"] = True
        
        # In a real implementation, you would extract text from the Word document
        # using a library like python-docx or a service
        
        # For now, show that we recognize it's a Word document
        st.caption(f"Filename: {uploaded_file.name}")
        st.caption("Word documents will be processed during comparison")


def setup_generated_comparison():
    """Setup comparison with a test case from the generated test cases"""
    st.subheader("Select Generated Test Case")
    
    # Retrieve generated test cases from generator module or session state
    generated_test_cases = get_generated_test_cases_list()
    
    if generated_test_cases:
        # Create a selectbox for choosing a generated test case
        selected_option = st.selectbox(
            "Select from recently generated test cases",
            options=range(len(generated_test_cases)),
            format_func=lambda i: f"{generated_test_cases[i]['id']} - {generated_test_cases[i]['title']}",
            key="generated_test_case_selector"
        )
        
        if selected_option is not None:
            # Get the selected test case
            selected_test_case = generated_test_cases[selected_option]
            
            # Save selection in session state
            st.session_state.comparison_source = {
                "type": "generated",
                "id": selected_test_case['id'],
                "test_case": selected_test_case
            }
            
            # Display preview
            st.subheader("Test Case Preview")
            display_test_case_preview(selected_test_case)
            
            # Indicate selection is complete
            st.success(f"Generated test case '{selected_test_case['id']}' selected for comparison")
    else:
        st.info("No generated test cases available. Please create test cases first using the Test Generation Module.")


def setup_repository_comparison():
    """Setup comparison with a test case from the repository"""
    st.subheader("Select Test Case from Repository")
    
    # Simple search field for repository test cases
    search_query = st.text_input("Search by ID or Title", key="repo_search_query")
    
    if search_query:
        with st.spinner("Searching repository..."):
            # Get matching test cases from repository
            matching_test_cases = search_repository_test_cases(search_query)
            
            if matching_test_cases:
                # Create a selectbox for choosing a test case
                selected_option = st.selectbox(
                    "Select test case",
                    options=range(len(matching_test_cases)),
                    format_func=lambda i: f"{matching_test_cases[i]['ID']} - {matching_test_cases[i]['Title']}",
                    key="repo_test_case_selector"
                )
                
                if selected_option is not None:
                    # Get the selected test case
                    selected_test_case = matching_test_cases[selected_option]
                    
                    # Save selection in session state
                    st.session_state.comparison_source = {
                        "type": "repository",
                        "id": selected_test_case['ID'],
                        "test_case": selected_test_case
                    }
                    
                    # Display preview
                    st.subheader("Test Case Preview")
                    display_test_case_preview(selected_test_case)
                    
                    # Indicate selection is complete
                    st.success(f"Repository test case '{selected_test_case['ID']}' selected for comparison")
            else:
                st.warning(f"No test cases found matching '{search_query}'")
    else:
        # If a test case ID was passed from the repository browser, use it
        if 'compare_test_case' in st.session_state and st.session_state.compare_test_case:
            test_id = st.session_state.compare_test_case
            
            # Fetch the test case details
            test_case = fetch_test_case_details(test_id)
            
            if test_case:
                # Save selection in session state
                st.session_state.comparison_source = {
                    "type": "repository",
                    "id": test_id,
                    "test_case": test_case
                }
                
                # Display preview
                st.subheader("Test Case Preview")
                display_test_case_preview(test_case)
                
                # Indicate selection is complete
                st.success(f"Repository test case '{test_id}' selected for comparison")
                
                # Clear the compare_test_case flag
                st.session_state.compare_test_case = None
            else:
                st.error(f"Could not retrieve details for test case {test_id}")
        else:
            st.info("Enter a search term to find test cases in the repository")


def setup_manual_comparison():
    """Setup comparison with manually entered test case information"""
    st.subheader("Enter Test Case Information")
    
    # Create a form for manual entry
    with st.form("manual_test_case_form"):
        title = st.text_input("Title")
        description = st.text_area("Description")
        
        # Test steps input
        st.subheader("Test Steps")
        
        # Determine number of steps
        num_steps = st.number_input("Number of Steps", min_value=1, max_value=10, value=3)
        
        steps = []
        for i in range(int(num_steps)):
            st.markdown(f"**Step {i+1}**")
            step_col1, step_col2 = st.columns(2)
            
            with step_col1:
                action = st.text_input(f"Action", key=f"action_{i}")
            
            with step_col2:
                expected = st.text_input(f"Expected Result", key=f"expected_{i}")
            
            steps.append({
                "number": i+1,
                "action": action,
                "expected": expected
            })
        
        submitted = st.form_submit_button("Create Test Case for Comparison")
        
        if submitted:
            # Create a manual test case
            test_case = {
                "id": f"MANUAL{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "Title": title,
                "Description": description,
                "Status": "Draft",
                "Type": "Manual",
                "Steps": steps,
                "Created Date": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Save in session state
            st.session_state.comparison_source = {
                "type": "manual",
                "id": test_case["id"],
                "test_case": test_case
            }
            
            # Display preview
            st.subheader("Test Case Preview")
            display_test_case_preview(test_case)
            
            # Indicate creation is complete
            st.success(f"Manual test case created for comparison")


def display_comparison_settings():
    """Display settings for test case comparison"""
    st.subheader("Comparison Settings")
    
    with st.expander("Comparison Configuration", expanded=True):
        # Get default settings
        default_settings = get_default_comparison_settings()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Similarity threshold
            similarity_threshold = st.slider(
                "Similarity Threshold (%)", 
                min_value=0, 
                max_value=100, 
                value=default_settings.get('similarity_threshold', 70),
                help="Minimum similarity score to consider a match"
            )
            
            # Repository sources to search
            repository_sources = st.multiselect(
                "Repository Sources",
                options=["SharePoint", "JIRA", "ALM"],
                default=default_settings.get('repository_sources', ["SharePoint"]),
                help="Select which repositories to search for matching test cases"
            )
        
        with col2:
            # Fields to compare
            comparison_fields = st.multiselect(
                "Fields to Compare",
                options=["Title", "Description", "Steps", "Expected Results", "Preconditions"],
                default=default_settings.get('comparison_fields', ["Title", "Steps", "Expected Results"]),
                help="Select which fields to include in the comparison"
            )
            
            # Comparison algorithm
            comparison_algorithm = st.selectbox(
                "Comparison Algorithm",
                options=["Semantic", "Keyword", "Hybrid"],
                index=["Semantic", "Keyword", "Hybrid"].index(default_settings.get('comparison_algorithm', "Hybrid")),
                help="Select the algorithm to use for comparison"
            )
        
        # Advanced settings
        with st.expander("Advanced Settings", expanded=False):
            # Maximum number of matches to return
            max_matches = st.number_input(
                "Maximum Matches",
                min_value=1,
                max_value=20,
                value=default_settings.get('max_matches', 5),
                help="Maximum number of potential matches to return"
            )
            
            # Weight for title comparison
            title_weight = st.slider(
                "Title Weight",
                min_value=0.0,
                max_value=1.0,
                value=default_settings.get('title_weight', 0.3),
                step=0.1,
                help="Weight to give the title when calculating similarity"
            )
            
            # Weight for steps comparison
            steps_weight = st.slider(
                "Steps Weight",
                min_value=0.0,
                max_value=1.0,
                value=default_settings.get('steps_weight', 0.5),
                step=0.1,
                help="Weight to give the steps when calculating similarity"
            )
            
            # Weight for expected results comparison
            expected_weight = st.slider(
                "Expected Results Weight",
                min_value=0.0,
                max_value=1.0,
                value=default_settings.get('expected_weight', 0.2),
                step=0.1,
                help="Weight to give the expected results when calculating similarity"
            )
        
        # Save settings in session state
        st.session_state.comparison_settings = {
            'similarity_threshold': similarity_threshold,
            'repository_sources': repository_sources,
            'comparison_fields': comparison_fields,
            'comparison_algorithm': comparison_algorithm,
            'max_matches': max_matches,
            'title_weight': title_weight,
            'steps_weight': steps_weight,
            'expected_weight': expected_weight
        }


def run_comparison_analysis():
    """Run the comparison analysis based on selected source and settings"""
    with st.spinner("Analyzing and comparing test cases..."):
        try:
            # Get source test case
            source = st.session_state.comparison_source
            
            # Get comparison settings
            settings = st.session_state.comparison_settings
            
            # Prepare for comparison
            prepared_source = prepare_comparison(source, settings)
            
            # This would call the actual comparison engine in a real implementation
            # For now, we'll simulate the comparison with mock results
            import time
            time.sleep(2)  # Simulate processing time
            
            # Generate mock comparison results
            results = generate_mock_comparison_results(prepared_source, settings)
            
            # Store results in session state
            st.session_state.comparison_details = results
            
            # Determine match type
            if results['best_match']['similarity_score'] >= settings['similarity_threshold']:
                if results['best_match']['similarity_score'] >= 95:
                    st.session_state.comparison_result = "exact"
                else:
                    st.session_state.comparison_result = "partial"
            else:
                st.session_state.comparison_result = "new"
            
            # Reload to show results
            st.rerun()
        
        except Exception as e:
            st.error(f"Error during comparison: {str(e)}")


# Helper functions

def is_comparison_source_selected():
    """Check if a comparison source has been selected
    
    Returns:
        bool: True if a source is selected, False otherwise
    """
    return 'comparison_source' in st.session_state and st.session_state.comparison_source is not None


def get_generated_test_cases_list():
    """Get the list of recently generated test cases
    
    In a real implementation, this would fetch from the generator module.
    
    Returns:
        List of generated test cases
    """
    # Check if we have cached test cases in session state
    if 'generated_test_cases' in st.session_state:
        return st.session_state.generated_test_cases
    
    # In a real implementation, this would call the test case generator module
    # For now, we'll create mock data
    generated_cases = [
        {
            "id": "GEN001",
            "title": "Login Authentication Test Case",
            "description": "Verify that users can log in with valid credentials",
            "type": "Automated",
            "steps": [
                {"number": 1, "action": "Navigate to login page", "expected": "Login page is displayed"},
                {"number": 2, "action": "Enter valid username", "expected": "Username is accepted"},
                {"number": 3, "action": "Enter valid password", "expected": "Password is accepted"},
                {"number": 4, "action": "Click login button", "expected": "User is logged in successfully"},
                {"number": 5, "action": "Verify dashboard access", "expected": "Dashboard is displayed"}
            ],
            "generation_date": "2025-04-25"
        },
        {
            "id": "GEN002",
            "title": "User Profile Update Test Case",
            "description": "Verify that users can update their profile information",
            "type": "Manual",
            "steps": [
                {"number": 1, "action": "Login to the application", "expected": "User is logged in"},
                {"number": 2, "action": "Navigate to profile page", "expected": "Profile page is displayed"},
                {"number": 3, "action": "Update user information", "expected": "Information is updated"},
                {"number": 4, "action": "Save changes", "expected": "Changes are saved successfully"},
                {"number": 5, "action": "Verify information is updated", "expected": "Updated information is displayed"}
            ],
            "generation_date": "2025-04-24"
        },
        {
            "id": "GEN003",
            "title": "Payment Processing Test Case",
            "description": "Verify that payment processing works correctly",
            "type": "Automated",
            "steps": [
                {"number": 1, "action": "Navigate to payment page", "expected": "Payment page is displayed"},
                {"number": 2, "action": "Enter payment details", "expected": "Payment details are accepted"},
                {"number": 3, "action": "Submit payment", "expected": "Payment is processed"},
                {"number": 4, "action": "Verify payment confirmation", "expected": "Confirmation is displayed"},
                {"number": 5, "action": "Check payment status", "expected": "Status is 'Completed'"}
            ],
            "generation_date": "2025-04-24"
        }
    ]
    
    # Cache in session state
    st.session_state.generated_test_cases = generated_cases
    
    return generated_cases


def search_repository_test_cases(query):
    """Search for test cases in the repository
    
    In a real implementation, this would query the repository connectors.
    
    Args:
        query: Search query string
    
    Returns:
        List of matching test cases
    """
    # In a real implementation, this would call the repository connector modules
    # For now, we'll filter the sample data
    if 'test_cases_df' in st.session_state:
        df = st.session_state.test_cases_df
        
        # Convert query to lowercase for case-insensitive matching
        query = query.lower()
        
        # Filter by ID or Title containing the query
        filtered_df = df[
            df['ID'].astype(str).str.lower().str.contains(query) | 
            df['Title'].str.lower().str.contains(query)
        ]
        
        # Convert to list of dictionaries
        matching_cases = filtered_df.to_dict('records')
        return matching_cases
    else:
        # If no data is available, return empty list
        return []


def display_test_case_preview(test_case):
    """Display a preview of a test case
    
    Args:
        test_case: Test case data to preview
    """
    # Display basic information
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**ID:** {test_case.get('id', test_case.get('ID', 'N/A'))}")
        st.markdown(f"**Title:** {test_case.get('title', test_case.get('Title', 'N/A'))}")
        st.markdown(f"**Type:** {test_case.get('type', test_case.get('Type', 'N/A'))}")
    
    with col2:
        st.markdown(f"**Description:** {test_case.get('description', test_case.get('Description', 'N/A'))}")
        
        # Show generation or creation date if available
        if 'generation_date' in test_case:
            st.markdown(f"**Generated:** {test_case['generation_date']}")
        elif 'Created Date' in test_case:
            st.markdown(f"**Created:** {test_case['Created Date']}")
    
    # Display steps if available
    steps = test_case.get('steps', test_case.get('Steps', []))
    if steps:
        st.markdown("**Steps:**")
        steps_df = pd.DataFrame(steps)
        
        # Ensure consistent column names
        if 'number' in steps[0]:
            steps_df = steps_df.rename(columns={
                'number': 'Step #',
                'action': 'Action',
                'expected': 'Expected Result'
            })
        
        st.dataframe(steps_df, hide_index=True)


def get_default_comparison_settings():
    """Get default settings for comparison
    
    In a real implementation, this would fetch from the comparison engine.
    
    Returns:
        Dictionary containing default comparison settings
    """
    # In a real implementation, this would call the comparison engine module
    # For now, we'll return mock default settings
    return {
        'similarity_threshold': 70,
        'repository_sources': ["SharePoint"],
        'comparison_fields': ["Title", "Steps", "Expected Results"],
        'comparison_algorithm': "Hybrid",
        'max_matches': 5,
        'title_weight': 0.3,
        'steps_weight': 0.5,
        'expected_weight': 0.2
    }


def generate_mock_comparison_results(source, settings):
    """Generate mock comparison results for demonstration
    
    In a real implementation, this would call the comparison engine.
    
    Args:
        source: Source test case for comparison
        settings: Comparison settings
    
    Returns:
        Dictionary containing comparison results
    """
    # In a real implementation, this would call the comparison engine module
    # For now, we'll create mock results
    
    # Determine source attributes
    source_id = source.get('id', 'unknown')
    source_type = source.get('type', 'unknown')
    
    # Generate different mock results based on source ID or type
    if "Login" in source_id or "Authentication" in str(source):
        # High similarity match
        best_match = {
            "id": "TC1001",
            "title": "Login Authentication Test",
            "similarity_score": 96,
            "match_confidence": 95,
            "matching_fields": ["Title", "Steps", "Expected Results"],
            "repository": "SharePoint",
            "owner": "Jane Smith",
            "type": "Automated",
            "has_test_data": True,
            "status": "Active"
        }
        
        result_type = "exact"
    elif "Profile" in source_id or "User" in str(source):
        # Partial match
        best_match = {
            "id": "TC1002",
            "title": "User Profile Update Test",
            "similarity_score": 82,
            "match_confidence": 85,
            "matching_fields": ["Title", "Steps"],
            "repository": "SharePoint",
            "owner": "John Doe",
            "type": "Automated",
            "has_test_data": False,
            "status": "Active"
        }
        
        result_type = "partial"
    else:
        # Low similarity match
        best_match = {
            "id": "TC1007",
            "title": "Payment Processing Test",
            "similarity_score": 67,
            "match_confidence": 60,
            "matching_fields": ["Title"],
            "repository": "SharePoint",
            "owner": "Sarah Adams",
            "type": "Automated",
            "has_test_data": True,
            "status": "Active"
        }
        
        result_type = "new"
    
    # Create differences if it's a partial match
    differences = []
    if result_type == "partial":
        differences = [
            {"type": "addition", "line": 3, "text": "Update profile picture"},
            {"type": "modification", "line": 4, "old": "Save changes", "new": "Click Save button and confirm changes"}
        ]
    
    # Create other potential matches
    other_matches = [
        {
            "id": "TC1008",
            "title": "Search Functionality Test",
            "similarity_score": 55,
            "match_confidence": 50,
            "matching_fields": ["Steps"],
            "repository": "JIRA",
            "owner": "Michael Chen",
            "type": "Manual"
        },
        {
            "id": "TC1003",
            "title": "Password Reset Test",
            "similarity_score": 45,
            "match_confidence": 40,
            "matching_fields": ["Expected Results"],
            "repository": "SharePoint",
            "owner": "Alice Brown",
            "type": "Manual"
        }
    ]
    
    # Create full results object
    results = {
        "source_case": source,
        "best_match": best_match,
        "other_matches": other_matches,
        "match_type": result_type,
        "differences": differences if result_type == "partial" else [],
        "comparison_settings": settings,
        "comparison_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "diff_report": generate_mock_diff_report(source, best_match, differences) if result_type == "partial" else None
    }
    
    return results


def generate_mock_diff_report(source, best_match, differences):
    """Generate a mock difference report for demonstration
    
    Args:
        source: Source test case
        best_match: Best matching test case
        differences: List of differences
    
    Returns:
        Dictionary containing difference report
    """
    return {
        "source_with_highlights": "<div>Step 1: Navigate to profile page</div><div>Step 2: Enter user information</div><div class='added'>Step 3: Update profile picture</div><div class='modified'>Step 4: Click Save button and confirm changes</div>",
        "target_with_highlights": "<div>Step 1: Navigate to profile page</div><div>Step 2: Enter user information</div><div class='modified'>Step 4: Save changes</div>",
        "summary": f"Found {len(differences)} differences between test cases",
        "total_steps_source": 4,
        "total_steps_target": 3
    }

#######################################################
# PART 5: COMPARISON RESULTS - EXACT MATCHES
#######################################################

# This code should be integrated into the existing display_comparison_results
# function from Part 4. The function below would replace the placeholder:
# st.info("Comparison result display will be implemented in Parts 5-6")

def display_comparison_result_view():
    """Display the appropriate comparison result view based on match type"""
    if 'comparison_result' not in st.session_state or 'comparison_details' not in st.session_state:
        st.error("No comparison results available. Please run a comparison first.")
        return
    
    # Get the comparison details
    result_type = st.session_state.comparison_result
    details = st.session_state.comparison_details
    
    # Add a back button
    if st.button("Back to Comparison Setup", key="back_to_setup"):
        # Reset comparison result state
        if 'comparison_result' in st.session_state:
            del st.session_state.comparison_result
        
        # Keep the source and settings for convenience
        st.rerun()
    
    # Create tabs for different views of the comparison results
    result_tabs = st.tabs([
        "Match Overview", 
        "Detailed Comparison", 
        "Actions"
    ])
    
    with result_tabs[0]:
        display_match_overview(result_type, details)
    
    with result_tabs[1]:
        display_detailed_comparison(result_type, details)
    
    with result_tabs[2]:
        if result_type == "exact":
            display_exact_match_actions(details)
        elif result_type == "partial":
            # This will be implemented in Part 6
            st.info("Partial match actions will be implemented in Part 6")
        else:  # result_type == "new"
            # This will be implemented in Part 6
            st.info("New test case actions will be implemented in Part 6")


def display_match_overview(result_type, details):
    """Display an overview of the comparison match
    
    Args:
        result_type: Type of match (exact, partial, new)
        details: Dictionary containing comparison details
    """
    st.subheader("Match Overview")
    
    # Display different content based on match type
    if result_type == "exact":
        st.success("✅ **Exact Match Found**")
        
        best_match = details.get('best_match', {})
        match_score = best_match.get('similarity_score', 0)
        match_confidence = best_match.get('match_confidence', 0)
        
        # Display match metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Similarity Score", f"{match_score}%")
        
        with col2:
            st.metric("Match Confidence", f"{match_confidence}%")
        
        with col3:
            st.metric("Matching Fields", len(best_match.get('matching_fields', [])))
        
        # Display source and matching test case summaries
        st.markdown("### Test Case Match")
        
        source_col, match_col = st.columns(2)
        
        with source_col:
            st.markdown("**Source Test Case**")
            display_test_case_summary(details.get('source_case', {}))
        
        with match_col:
            st.markdown("**Matching Test Case**")
            display_test_case_summary(best_match)
    
    elif result_type == "partial":
        # This will be implemented in Part 6
        st.warning("⚠️ **Partial Match Found**")
        st.info("Partial match overview will be implemented in Part 6")
    
    else:  # result_type == "new"
        # This will be implemented in Part 6
        st.info("🆕 **New Test Case**")
        st.info("New test case overview will be implemented in Part 6")
    
    # Display other potential matches if available
    if 'other_matches' in details and details['other_matches']:
        st.markdown("### Other Potential Matches")
        display_other_matches(details['other_matches'])


def display_test_case_summary(test_case):
    """Display a summary of a test case
    
    Args:
        test_case: Dictionary containing test case details
    """
    # Extract ID and title with appropriate fallbacks
    test_id = test_case.get('id', test_case.get('ID', 'N/A'))
    title = test_case.get('title', test_case.get('Title', 'N/A'))
    
    # Display basic information
    st.markdown(f"**ID:** {test_id}")
    st.markdown(f"**Title:** {title}")
    
    # Display type and status if available
    type_value = test_case.get('type', test_case.get('Type', 'Unknown'))
    st.markdown(f"**Type:** {type_value}")
    
    status_value = test_case.get('status', test_case.get('Status', 'Unknown'))
    st.markdown(f"**Status:** {status_value}")
    
    # Display repository and owner if available
    repository = test_case.get('repository', test_case.get('Repository', 'Unknown'))
    st.markdown(f"**Repository:** {repository}")
    
    owner = test_case.get('owner', test_case.get('Owner', 'Unassigned'))
    st.markdown(f"**Owner:** {owner}")
    
    # Display test data availability for automated tests
    if type_value == "Automated":
        has_test_data = test_case.get('has_test_data', False)
        test_data_status = "✅ Available" if has_test_data else "❌ Not Available"
        st.markdown(f"**Test Data:** {test_data_status}")


def display_other_matches(other_matches):
    """Display a table of other potential matches
    
    Args:
        other_matches: List of other potential matches
    """
    if not other_matches:
        st.info("No other potential matches found.")
        return
    
    # Create a DataFrame for display
    matches_data = []
    
    for match in other_matches:
        matches_data.append({
            "ID": match.get('id', 'N/A'),
            "Title": match.get('title', 'N/A'),
            "Similarity": f"{match.get('similarity_score', 0)}%",
            "Repository": match.get('repository', 'Unknown'),
            "Type": match.get('type', 'Unknown'),
            "Owner": match.get('owner', 'Unassigned')
        })
    
    # Convert to DataFrame
    matches_df = pd.DataFrame(matches_data)
    
    # Display as interactive table
    st.dataframe(
        matches_df,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Similarity": st.column_config.TextColumn("Similarity", width="small"),
            "Repository": st.column_config.TextColumn("Repository", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Owner": st.column_config.TextColumn("Owner", width="medium")
        },
        hide_index=True
    )
    
    # Option to view details of other matches
    selected_match_id = st.selectbox(
        "Select match to view details",
        options=[match["ID"] for match in matches_data],
        format_func=lambda x: f"{x} - {next((m['Title'] for m in matches_data if m['ID'] == x), '')}"
    )
    
    if selected_match_id and st.button("View Selected Match"):
        # Find the selected match
        selected_match = next((match for match in other_matches if match.get('id') == selected_match_id), None)
        
        if selected_match:
            with st.expander("Match Details", expanded=True):
                display_test_case_summary(selected_match)


def display_detailed_comparison(result_type, details):
    """Display detailed comparison between source and matched test cases
    
    Args:
        result_type: Type of match (exact, partial, new)
        details: Dictionary containing comparison details
    """
    st.subheader("Detailed Comparison")
    
    # Extract source and best match
    source_case = details.get('source_case', {})
    best_match = details.get('best_match', {})
    
    if result_type == "exact":
        # For exact matches, show side-by-side comparison
        st.markdown("### Side-by-Side Comparison")
        
        # Basic information comparison
        st.markdown("#### Basic Information")
        create_comparison_table(
            {
                "Title": source_case.get('title', source_case.get('Title', 'N/A')),
                "Description": source_case.get('description', source_case.get('Description', 'N/A')),
                "Type": source_case.get('type', source_case.get('Type', 'Unknown'))
            },
            {
                "Title": best_match.get('title', 'N/A'),
                "Description": best_match.get('description', 'N/A'),
                "Type": best_match.get('type', 'Unknown')
            },
            "Source Test Case",
            "Matching Test Case"
        )
        
        # Test steps comparison
        st.markdown("#### Test Steps")
        
        # Extract steps with appropriate fallbacks
        source_steps = source_case.get('steps', source_case.get('Steps', []))
        match_steps = best_match.get('steps', best_match.get('Steps', []))
        
        if source_steps and match_steps:
            # Create formatted DataFrames for steps
            source_steps_df = create_steps_dataframe(source_steps)
            match_steps_df = create_steps_dataframe(match_steps)
            
            # Display side by side
            step_col1, step_col2 = st.columns(2)
            
            with step_col1:
                st.markdown("**Source Test Steps**")
                st.dataframe(source_steps_df, hide_index=True)
            
            with step_col2:
                st.markdown("**Matching Test Steps**")
                st.dataframe(match_steps_df, hide_index=True)
        elif source_steps:
            st.info("Source test case has steps, but matching test case does not.")
            
            # Display just source steps
            source_steps_df = create_steps_dataframe(source_steps)
            st.markdown("**Source Test Steps**")
            st.dataframe(source_steps_df, hide_index=True)
        elif match_steps:
            st.info("Matching test case has steps, but source test case does not.")
            
            # Display just matching steps
            match_steps_df = create_steps_dataframe(match_steps)
            st.markdown("**Matching Test Steps**")
            st.dataframe(match_steps_df, hide_index=True)
        else:
            st.info("Neither test case has defined steps.")
        
        # Display matching fields
        st.markdown("#### Matching Fields")
        matching_fields = best_match.get('matching_fields', [])
        
        if matching_fields:
            st.markdown(", ".join(matching_fields))
        else:
            st.info("No specific matching fields identified.")
    
    elif result_type == "partial":
        # This will be implemented in Part 6
        st.info("Partial match detailed comparison will be implemented in Part 6")
    
    else:  # result_type == "new"
        # This will be implemented in Part 6
        st.info("New test case detailed comparison will be implemented in Part 6")
    
    # Display comparison settings
    with st.expander("Comparison Settings Used", expanded=False):
        show_comparison_settings(details.get('comparison_settings', {}))


def display_exact_match_actions(details):
    """Display actions for exact match results
    
    Args:
        details: Dictionary containing comparison details
    """
    st.subheader("Available Actions")
    
    # Get the matched test case
    best_match = details.get('best_match', {})
    test_case_id = best_match.get('id', 'Unknown')
    test_case_type = best_match.get('type', 'Unknown')
    
    # Display different actions based on test case type
    if test_case_type == "Automated":
        display_automated_test_actions(best_match)
    else:
        display_manual_test_actions(best_match)
    
    # Add tracking list option
    if st.button("Add to 'Matched Cases' List", key="add_to_matched"):
        # This would add the match to a tracking list
        add_to_matched_list(details)
        st.success(f"Added test case {test_case_id} to 'Matched Cases' list")
    
    # Option to export comparison report
    if st.button("Export Comparison Report", key="export_comparison"):
        export_comparison_report(details)


def display_automated_test_actions(test_case):
    """Display actions for automated test cases
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Automated Test Actions")
    
    # Check if test data is available
    has_test_data = test_case.get('has_test_data', False)
    
    if has_test_data:
        st.success("✅ Test data is available for this test case")
        
        # Add execution button
        if st.button("Trigger Execution with Existing Data", key="trigger_exec"):
            with st.spinner("Scheduling test execution..."):
                # This would call the RPA controller to schedule execution
                import time
                execution_id = f"EX{int(time.time())}"
                
                st.success(f"Execution scheduled successfully! Execution ID: {execution_id}")
                
                # Store in session state for tracking
                if 'scheduled_executions' not in st.session_state:
                    st.session_state.scheduled_executions = []
                
                st.session_state.scheduled_executions.append({
                    "execution_id": execution_id,
                    "test_case_id": test_case.get('id', 'Unknown'),
                    "schedule_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Scheduled"
                })
    else:
        st.warning("❌ Test data is not available for this test case")
        
        # Add generate and execute button
        if st.button("Generate Test Data & Execute", key="gen_data_exec"):
            with st.spinner("Generating test data..."):
                # This would call the Test Data Manager to generate data
                import time
                time.sleep(2)  # Simulate data generation
                
                # Then schedule execution
                execution_id = f"EX{int(time.time())}"
                
                st.success(f"Test data generated and execution scheduled! Execution ID: {execution_id}")
                
                # Store in session state for tracking
                if 'scheduled_executions' not in st.session_state:
                    st.session_state.scheduled_executions = []
                
                st.session_state.scheduled_executions.append({
                    "execution_id": execution_id,
                    "test_case_id": test_case.get('id', 'Unknown'),
                    "schedule_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Scheduled",
                    "data_generated": True
                })
    
    # Add additional options
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("View Test Case Details", key="view_tc_details"):
            # This would set up for viewing test case details
            st.session_state.view_test_case = test_case.get('id', 'Unknown')
            st.info(f"View details functionality will redirect to test case {test_case.get('id', 'Unknown')}")
    
    with action_col2:
        if st.button("View Execution History", key="view_exec_history"):
            # This would set up for viewing execution history
            with st.expander("Execution History", expanded=True):
                st.info(f"Execution history for test case {test_case.get('id', 'Unknown')} will be displayed here")


def display_manual_test_actions(test_case):
    """Display actions for manual test cases
    
    Args:
        test_case: Dictionary containing test case details
    """
    st.markdown("### Manual Test Actions")
    
    # Get owner information
    owner = test_case.get('owner', 'Unassigned')
    
    # Add notification button
    if st.button("Notify Owner for Execution", key="notify_owner"):
        with st.spinner(f"Sending notification to {owner}..."):
            # This would call the Notification Service to send notification
            import time
            time.sleep(1)  # Simulate notification sending
            
            st.success(f"Notification sent to {owner}")
            
            # Store in session state for tracking
            if 'sent_notifications' not in st.session_state:
                st.session_state.sent_notifications = []
            
            st.session_state.sent_notifications.append({
                "recipient": owner,
                "test_case_id": test_case.get('id', 'Unknown'),
                "send_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "execution_request"
            })
    
    # Add additional options
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("View Test Case Details", key="view_tc_details_manual"):
            # This would set up for viewing test case details
            st.session_state.view_test_case = test_case.get('id', 'Unknown')
            st.info(f"View details functionality will redirect to test case {test_case.get('id', 'Unknown')}")
    
    with action_col2:
        if st.button("Upload Test Results", key="upload_results"):
            # This would open a form for uploading test results
            with st.form("manual_results_form"):
                st.markdown(f"**Upload Test Results for: {test_case.get('id', 'Unknown')} - {test_case.get('title', 'Unknown')}**")
                
                # Test status selection
                status = st.selectbox(
                    "Execution Status",
                    options=["Passed", "Failed", "Blocked", "Not Executed"],
                    index=0
                )
                
                # Test execution details
                execution_date = st.date_input("Execution Date", value=datetime.now())
                executed_by = st.text_input("Executed By", value=st.session_state.get("user_name", ""))
                
                # Comments field
                comments = st.text_area("Comments")
                
                # File uploader for screenshots or evidence
                evidence_file = st.file_uploader("Upload Evidence (Screenshot, etc.)", type=["png", "jpg", "pdf"])
                
                submitted = st.form_submit_button("Submit Results")
                
                if submitted:
                    with st.spinner("Saving test results..."):
                        # This would call the appropriate service to save results
                        import time
                        time.sleep(1)  # Simulate saving
                        
                        st.success("Test results saved successfully!")


def add_to_matched_list(details):
    """Add the comparison match to the matched cases tracking list
    
    Args:
        details: Dictionary containing comparison details
    """
    # Get source and best match details
    source_case = details.get('source_case', {})
    best_match = details.get('best_match', {})
    
    # Create a record for the matched case
    matched_case = {
        "id": best_match.get('id', 'Unknown'),
        "title": best_match.get('title', 'Unknown'),
        "matched_with": source_case.get('id', source_case.get('ID', 'Unknown')),
        "status": "Pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "similarity": best_match.get('similarity_score', 0),
        "confidence": best_match.get('match_confidence', 0)
    }
    
    # Add to session state
    if 'matched_cases' not in st.session_state:
        st.session_state.matched_cases = []
    
    # Check if already in list
    if not any(case['id'] == matched_case['id'] and case['matched_with'] == matched_case['matched_with'] 
               for case in st.session_state.matched_cases):
        st.session_state.matched_cases.append(matched_case)


def export_comparison_report(details):
    """Export a comparison report to Excel
    
    Args:
        details: Dictionary containing comparison details
    """
    # Create a formatted report structure
    source_case = details.get('source_case', {})
    best_match = details.get('best_match', {})
    
    # Basic information for the report
    report_data = {
        "Comparison Time": details.get('comparison_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "Source ID": source_case.get('id', source_case.get('ID', 'Unknown')),
        "Source Title": source_case.get('title', source_case.get('Title', 'Unknown')),
        "Source Type": source_case.get('type', source_case.get('Type', 'Unknown')),
        "Match ID": best_match.get('id', 'Unknown'),
        "Match Title": best_match.get('title', 'Unknown'),
        "Match Type": best_match.get('type', 'Unknown'),
        "Similarity Score": best_match.get('similarity_score', 0),
        "Match Confidence": best_match.get('match_confidence', 0),
        "Matching Fields": ", ".join(best_match.get('matching_fields', [])),
        "Repository": best_match.get('repository', 'Unknown'),
        "Owner": best_match.get('owner', 'Unassigned')
    }
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write basic information
        pd.DataFrame([report_data]).to_excel(writer, sheet_name="Comparison Summary", index=False)
        
        # Write source test case details
        source_df = pd.DataFrame([{
            "ID": source_case.get('id', source_case.get('ID', 'Unknown')),
            "Title": source_case.get('title', source_case.get('Title', 'Unknown')),
            "Description": source_case.get('description', source_case.get('Description', 'Unknown')),
            "Type": source_case.get('type', source_case.get('Type', 'Unknown'))
        }])
        source_df.to_excel(writer, sheet_name="Source Test Case", index=False)
        
        # Write match test case details
        match_df = pd.DataFrame([{
            "ID": best_match.get('id', 'Unknown'),
            "Title": best_match.get('title', 'Unknown'),
            "Description": best_match.get('description', 'Unknown'),
            "Type": best_match.get('type', 'Unknown'),
            "Repository": best_match.get('repository', 'Unknown'),
            "Owner": best_match.get('owner', 'Unassigned'),
            "Status": best_match.get('status', 'Unknown')
        }])
        match_df.to_excel(writer, sheet_name="Matching Test Case", index=False)
        
        # Write source steps if available
        source_steps = source_case.get('steps', source_case.get('Steps', []))
        if source_steps:
            source_steps_df = create_steps_dataframe(source_steps)
            source_steps_df.to_excel(writer, sheet_name="Source Steps", index=False)
        
        # Write match steps if available
        match_steps = best_match.get('steps', best_match.get('Steps', []))
        if match_steps:
            match_steps_df = create_steps_dataframe(match_steps)
            match_steps_df.to_excel(writer, sheet_name="Match Steps", index=False)
        
        # Write comparison settings
        settings = details.get('comparison_settings', {})
        settings_df = pd.DataFrame([{k: str(v) for k, v in settings.items()}])
        settings_df.to_excel(writer, sheet_name="Comparison Settings", index=False)
    
    # Provide download button
    report_filename = f"Comparison_Report_{source_case.get('id', 'Source')}_{best_match.get('id', 'Match')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    
    st.download_button(
        label="Download Comparison Report",
        data=output.getvalue(),
        file_name=report_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# Helper functions

def create_comparison_table(source_data, match_data, source_label, match_label):
    """Create a comparison table between source and match data
    
    Args:
        source_data: Dictionary of source data
        match_data: Dictionary of match data
        source_label: Label for source column
        match_label: Label for match column
    """
    # Create a DataFrame with both sets of data
    comparison_data = []
    
    for key in source_data.keys():
        comparison_data.append({
            "Field": key,
            source_label: source_data.get(key, "N/A"),
            match_label: match_data.get(key, "N/A"),
            "Match": "✅" if source_data.get(key) == match_data.get(key) else "❌"
        })
    
    # Convert to DataFrame
    comparison_df = pd.DataFrame(comparison_data)
    
    # Display as a table
    st.dataframe(comparison_df, hide_index=True)


def create_steps_dataframe(steps):
    """Create a standardized DataFrame from test steps
    
    Args:
        steps: List of test steps
    
    Returns:
        DataFrame containing formatted steps
    """
    # Create a standardized representation of steps
    formatted_steps = []
    
    for step in steps:
        # Handle different possible key names
        step_num = step.get('number', step.get('Step #', ''))
        action = step.get('action', step.get('Action', ''))
        expected = step.get('expected', step.get('Expected Result', ''))
        test_data = step.get('test_data', step.get('Test Data', ''))
        
        formatted_steps.append({
            "Step #": step_num,
            "Action": action,
            "Expected Result": expected,
            "Test Data": test_data
        })
    
    # Convert to DataFrame
    return pd.DataFrame(formatted_steps)


def show_comparison_settings(settings):
    """Display the comparison settings used
    
    Args:
        settings: Dictionary containing comparison settings
    """
    st.markdown("**Comparison Configuration**")
    
    # Create readable format for settings
    for key, value in settings.items():
        if isinstance(value, list):
            st.markdown(f"**{key}:** {', '.join(str(v) for v in value)}")
        else:
            st.markdown(f"**{key}:** {value}")


# Integration with display_comparison_results in Part 4
# This code should replace the placeholder in display_comparison_results from Part 4
# At the position where it says:
# st.info("Comparison result display will be implemented in Parts 5-6")

# The updated display_comparison_results function would be:
"""
def display_comparison_results():
    st.header("Test Case Comparison")
    
    # Check if we're already in a specific comparison view
    if 'comparison_result' in st.session_state:
        # Display the appropriate comparison result view
        display_comparison_result_view()
        
        # Add a button to return to comparison setup
        if st.button("Start New Comparison"):
            # Reset comparison state
            if 'comparison_result' in st.session_state:
                del st.session_state.comparison_result
            if 'comparison_details' in st.session_state:
                del st.session_state.comparison_details
            
            # Reload the page
            st.rerun()
    else:
        # Display the comparison setup interface
        display_comparison_setup()
"""

#######################################################
# PART 6: COMPARISON RESULTS - PARTIAL & NEW MATCHES
#######################################################

# This is a continuation of Part 5, extending the display_comparison_result_view
# function to handle partial matches and new test cases

def display_partial_match_overview(details):
    """Display an overview of a partial match comparison
    
    Args:
        details: Dictionary containing comparison details
    """
    st.warning("⚠️ **Partial Match Found**")
    
    best_match = details.get('best_match', {})
    match_score = best_match.get('similarity_score', 0)
    match_confidence = best_match.get('match_confidence', 0)
    
    # Display match metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Similarity Score", f"{match_score}%")
    
    with col2:
        st.metric("Match Confidence", f"{match_confidence}%")
    
    with col3:
        differences = details.get('differences', [])
        st.metric("Differences Found", len(differences))
    
    # Display source and matching test case summaries
    st.markdown("### Test Case Match")
    
    source_col, match_col = st.columns(2)
    
    with source_col:
        st.markdown("**Source Test Case**")
        display_test_case_summary(details.get('source_case', {}))
    
    with match_col:
        st.markdown("**Matching Test Case**")
        display_test_case_summary(best_match)
    
    # Display identified differences
    st.markdown("### Identified Differences")
    display_differences(details.get('differences', []))


def display_new_test_case_overview(details):
    """Display an overview for a new test case (no significant match)
    
    Args:
        details: Dictionary containing comparison details
    """
    st.info("🆕 **New Test Case**")
    
    # Show best match info if available, but emphasize it's below threshold
    best_match = details.get('best_match', {})
    match_score = best_match.get('similarity_score', 0)
    
    if best_match and match_score > 0:
        st.markdown(f"Best potential match had a similarity score of **{match_score}%**, which is below the threshold.")
    else:
        st.markdown("No significant matches were found in the repository.")
    
    # Display source test case summary
    st.markdown("### Source Test Case")
    display_test_case_summary(details.get('source_case', {}))
    
    # Show repository statistics
    if 'repository_stats' in details:
        stats = details.get('repository_stats', {})
        
        st.markdown("### Repository Statistics")
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        
        with stats_col1:
            st.metric("Total Test Cases", stats.get('total_test_cases', 0))
        
        with stats_col2:
            st.metric("Repositories Searched", len(stats.get('repositories_searched', [])))
        
        with stats_col3:
            st.metric("Potential Matches Analyzed", stats.get('matches_analyzed', 0))
    
    # Show gap analysis if available
    if 'gap_analysis' in details:
        gap_analysis = details.get('gap_analysis', {})
        
        with st.expander("Coverage Gap Analysis", expanded=True):
            st.markdown("### Coverage Analysis")
            
            if 'coverage_areas' in gap_analysis:
                for area, coverage in gap_analysis.get('coverage_areas', {}).items():
                    st.markdown(f"**{area.replace('_', ' ').title()}**: {coverage}% covered")
            
            if 'recommendations' in gap_analysis:
                st.markdown("### Recommendations")
                for rec in gap_analysis.get('recommendations', []):
                    st.markdown(f"- {rec}")


def display_differences(differences):
    """Display the differences between source and matched test cases
    
    Args:
        differences: List of differences between test cases
    """
    if not differences:
        st.info("No specific differences outlined.")
        return
    
    # Create a formatted table of differences
    diff_data = []
    
    for diff in differences:
        diff_type = diff.get('type', '')
        line = diff.get('line', '')
        
        if diff_type == "addition":
            diff_data.append({
                "Type": "🟢 Addition",
                "Location": f"Step {line}",
                "Change": diff.get('text', ''),
                "Original": "N/A"
            })
        elif diff_type == "deletion":
            diff_data.append({
                "Type": "🔴 Deletion",
                "Location": f"Step {line}",
                "Change": "N/A",
                "Original": diff.get('text', '')
            })
        elif diff_type == "modification":
            diff_data.append({
                "Type": "🟠 Modification",
                "Location": f"Step {line}",
                "Change": diff.get('new', ''),
                "Original": diff.get('old', '')
            })
    
    # Convert to DataFrame
    diff_df = pd.DataFrame(diff_data)
    
    # Display as table
    st.dataframe(
        diff_df,
        column_config={
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Location": st.column_config.TextColumn("Location", width="small"),
            "Change": st.column_config.TextColumn("Change", width="medium"),
            "Original": st.column_config.TextColumn("Original", width="medium")
        },
        hide_index=True
    )
    
    # If there's a detailed diff report, show it
    if 'diff_report' in details and details['diff_report']:
        with st.expander("Visual Difference Report", expanded=False):
            st.markdown("### Visual Comparison")
            
            diff_report = details['diff_report']
            
            if 'source_with_highlights' in diff_report and 'target_with_highlights' in diff_report:
                st.markdown("#### Source Test Case (with highlights)")
                st.markdown(diff_report['source_with_highlights'], unsafe_allow_html=True)
                
                st.markdown("#### Target Test Case (with highlights)")
                st.markdown(diff_report['target_with_highlights'], unsafe_allow_html=True)
            
            if 'summary' in diff_report:
                st.markdown(f"**Summary**: {diff_report['summary']}")


def display_partial_match_detailed_comparison(details):
    """Display detailed comparison for partial matches
    
    Args:
        details: Dictionary containing comparison details
    """
    st.subheader("Detailed Comparison")
    
    # Extract source and best match
    source_case = details.get('source_case', {})
    best_match = details.get('best_match', {})
    
    # Basic information comparison
    st.markdown("#### Basic Information")
    create_comparison_table(
        {
            "Title": source_case.get('title', source_case.get('Title', 'N/A')),
            "Description": source_case.get('description', source_case.get('Description', 'N/A')),
            "Type": source_case.get('type', source_case.get('Type', 'Unknown'))
        },
        {
            "Title": best_match.get('title', 'N/A'),
            "Description": best_match.get('description', 'N/A'),
            "Type": best_match.get('type', 'Unknown')
        },
        "Source Test Case",
        "Matching Test Case"
    )
    
    # Test steps comparison with highlighting
    st.markdown("#### Test Steps Comparison")
    
    # Extract steps with appropriate fallbacks
    source_steps = source_case.get('steps', source_case.get('Steps', []))
    match_steps = best_match.get('steps', best_match.get('Steps', []))
    
    if source_steps and match_steps:
        # Get the differences for highlighting
        differences = details.get('differences', [])
        
        # Create DataFrames for steps with highlighting
        source_steps_df = create_steps_dataframe_with_highlights(source_steps, differences, "source")
        match_steps_df = create_steps_dataframe_with_highlights(match_steps, differences, "target")
        
        # Display side by side
        step_col1, step_col2 = st.columns(2)
        
        with step_col1:
            st.markdown("**Source Test Steps**")
            st.dataframe(source_steps_df, hide_index=True)
        
        with step_col2:
            st.markdown("**Matching Test Steps**")
            st.dataframe(match_steps_df, hide_index=True)
    else:
        st.info("Unable to compare steps directly. See the differences section for details.")
    
    # Display matching fields and non-matching fields
    matching_fields = best_match.get('matching_fields', [])
    
    match_col1, match_col2 = st.columns(2)
    
    with match_col1:
        st.markdown("#### Matching Fields")
        if matching_fields:
            st.markdown(", ".join(matching_fields))
        else:
            st.info("No specific matching fields identified.")
    
    with match_col2:
        st.markdown("#### Non-Matching Fields")
        # Determine which fields don't match
        all_fields = ["Title", "Description", "Steps", "Expected Results", "Preconditions"]
        non_matching = [field for field in all_fields if field not in matching_fields]
        
        if non_matching:
            st.markdown(", ".join(non_matching))
        else:
            st.success("All fields match.")
    
    # Display comparison settings
    with st.expander("Comparison Settings Used", expanded=False):
        show_comparison_settings(details.get('comparison_settings', {}))


def display_new_test_case_detailed_view(details):
    """Display detailed view for a new test case
    
    Args:
        details: Dictionary containing comparison details
    """
    st.subheader("Test Case Details")
    
    # Extract source case
    source_case = details.get('source_case', {})
    
    # Display full test case information
    st.markdown("### Basic Information")
    
    # Create info table
    info_data = {
        "Title": source_case.get('title', source_case.get('Title', 'N/A')),
        "Description": source_case.get('description', source_case.get('Description', 'N/A')),
        "Type": source_case.get('type', source_case.get('Type', 'Unknown'))
    }
    
    # Add additional fields if available
    if 'priority' in source_case:
        info_data["Priority"] = source_case['priority']
    
    if 'tags' in source_case:
        info_data["Tags"] = ", ".join(source_case['tags']) if isinstance(source_case['tags'], list) else source_case['tags']
    
    if 'preconditions' in source_case:
        info_data["Preconditions"] = source_case['preconditions']
    
    # Display as a single column table
    info_df = pd.DataFrame([info_data])
    st.dataframe(info_df.transpose().rename(columns={0: "Value"}), hide_index=False)
    
    # Test steps display
    st.markdown("### Test Steps")
    
    # Extract steps with appropriate fallbacks
    steps = source_case.get('steps', source_case.get('Steps', []))
    
    if steps:
        steps_df = create_steps_dataframe(steps)
        st.dataframe(steps_df, hide_index=True)
    else:
        st.info("No steps defined for this test case.")
    
    # If there are any potential matches despite being below threshold, show them
    other_matches = details.get('other_matches', [])
    
    if other_matches:
        st.markdown("### Closest Matches (Below Threshold)")
        display_other_matches(other_matches)


def display_partial_match_actions(details):
    """Display actions for partial match results
    
    Args:
        details: Dictionary containing comparison details
    """
    st.subheader("Available Actions")
    
    # Get the matched test case and differences
    best_match = details.get('best_match', {})
    test_case_id = best_match.get('id', 'Unknown')
    differences = details.get('differences', [])
    
    # Create options for handling the partial match
    st.markdown("### Action Options")
    
    action_option = st.radio(
        "How would you like to handle this partial match?",
        options=[
            "Create New Version of Existing Test Case", 
            "Create Brand New Test Case",
            "Notify Owner About Differences",
            "Take No Action"
        ],
        index=0
    )
    
    if action_option == "Create New Version of Existing Test Case":
        display_create_new_version_panel(details)
    
    elif action_option == "Create Brand New Test Case":
        display_create_new_test_case_panel(details)
    
    elif action_option == "Notify Owner About Differences":
        display_notify_owner_panel(details)
    
    else:  # Take No Action
        st.info("No action will be taken. You can still add this to the tracking list if desired.")
    
    # Add tracking list option
    if st.button("Add to 'Needs Modification' List", key="add_to_modification"):
        # This would add the match to a tracking list
        add_to_modification_list(details)
        st.success(f"Added test case {test_case_id} to 'Needs Modification' list")
    
    # Option to export comparison report
    if st.button("Export Comparison Report", key="export_comparison"):
        export_comparison_report(details)


def display_create_new_version_panel(details):
    """Display panel for creating a new version of the existing test case
    
    Args:
        details: Dictionary containing comparison details
    """
    st.markdown("### Create New Version")
    
    # Get the matched test case and source case
    best_match = details.get('best_match', {})
    source_case = details.get('source_case', {})
    differences = details.get('differences', [])
    
    # Information about the process
    st.info(
        "This will create a new version of the existing test case that incorporates the differences "
        "from the source test case. The previous version will be preserved in the version history."
    )
    
    # Options for the new version
    col1, col2 = st.columns(2)
    
    with col1:
        apply_all = st.checkbox("Apply All Differences", value=True)
        
        if not apply_all and differences:
            # Allow selecting which differences to apply
            selected_diffs = []
            
            for i, diff in enumerate(differences):
                diff_type = diff.get('type', '')
                line = diff.get('line', '')
                
                if diff_type == "addition":
                    selected = st.checkbox(
                        f"🟢 Addition at Step {line}: {diff.get('text', '')[:50]}...",
                        value=True,
                        key=f"select_diff_{i}"
                    )
                elif diff_type == "deletion":
                    selected = st.checkbox(
                        f"🔴 Deletion at Step {line}: {diff.get('text', '')[:50]}...",
                        value=True,
                        key=f"select_diff_{i}"
                    )
                elif diff_type == "modification":
                    selected = st.checkbox(
                        f"🟠 Modification at Step {line}: {diff.get('old', '')[:30]} → {diff.get('new', '')[:30]}...",
                        value=True,
                        key=f"select_diff_{i}"
                    )
                
                if selected:
                    selected_diffs.append(i)
    
    with col2:
        version_notes = st.text_area(
            "Version Notes",
            value=f"Applied changes from {source_case.get('id', 'source test case')}. {len(differences)} difference(s) identified.",
            height=150
        )
        
        # Set version status for automated test cases
        if best_match.get('type') == "Automated":
            maintenance_status = st.checkbox(
                "Mark as 'Under Maintenance'",
                value=True,
                help="For automated test cases, mark the old version as 'Under Maintenance' while the automated script is updated."
            )
    
    # Create new version button
    if st.button("Create New Version", key="create_version_btn"):
        with st.spinner("Creating new version..."):
            # Call the appropriate service to create the new version
            # In a real implementation, this would use the SharePoint Version Manager
            import time
            time.sleep(2)  # Simulate processing
            
            # Create a new version ID
            new_version_id = f"{best_match.get('id', 'TC')}v{datetime.now().strftime('%Y%m%d%H')}"
            
            # Simulate success
            st.success(f"New version created successfully: {new_version_id}")
            
            # If it's an automated test case and maintenance is checked, show additional message
            if best_match.get('type') == "Automated" and 'maintenance_status' in locals() and maintenance_status:
                st.info(f"The previous version has been marked as 'Under Maintenance'.")
            
            # Store in session state for tracking
            if 'created_versions' not in st.session_state:
                st.session_state.created_versions = []
            
            st.session_state.created_versions.append({
                "id": new_version_id,
                "original_id": best_match.get('id', 'Unknown'),
                "source_id": source_case.get('id', source_case.get('ID', 'Unknown')),
                "creation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "notes": version_notes,
                "applied_differences": "All" if apply_all else f"{len(selected_diffs)} of {len(differences)}"
            })


def display_create_new_test_case_panel(details):
    """Display panel for creating a brand new test case
    
    Args:
        details: Dictionary containing comparison details
    """
    st.markdown("### Create New Test Case")
    
    # Get the source case
    source_case = details.get('source_case', {})
    
    # Information about the process
    st.info(
        "This will create a brand new test case based on the source, "
        "without modifying any existing test cases."
    )
    
    # Form for creating a new test case
    with st.form("new_test_case_form"):
        # Pre-fill from source case
        title = st.text_input(
            "Title",
            value=source_case.get('title', source_case.get('Title', ''))
        )
        
        description = st.text_area(
            "Description",
            value=source_case.get('description', source_case.get('Description', ''))
        )
        
        # Test case metadata
        meta_col1, meta_col2, meta_col3 = st.columns(3)
        
        with meta_col1:
            test_type = st.selectbox(
                "Type",
                options=["Manual", "Automated"],
                index=0 if source_case.get('type', source_case.get('Type', '')) != "Automated" else 1
            )
        
        with meta_col2:
            priority = st.selectbox(
                "Priority",
                options=["Low", "Medium", "High", "Critical"],
                index=1  # Default to Medium
            )
        
        with meta_col3:
            repository = st.selectbox(
                "Repository",
                options=["SharePoint", "JIRA", "ALM"],
                index=0  # Default to SharePoint
            )
        
        # Owner assignment
        owner = st.text_input(
            "Owner",
            value=st.session_state.get("user_name", "")
        )
        
        # Tags
        tags = st.text_input(
            "Tags (comma-separated)",
            value=""
        )
        
        # Copy steps from source
        copy_steps = st.checkbox("Copy Steps from Source Test Case", value=True)
        
        submitted = st.form_submit_button("Create Test Case")
        
        if submitted:
            with st.spinner("Creating new test case..."):
                # Call the appropriate service to create the new test case
                # In a real implementation, this would use the Test Case Manager
                import time
                time.sleep(2)  # Simulate processing
                
                # Create a new test case ID
                new_test_id = f"TC{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Simulate success
                st.success(f"New test case created successfully: {new_test_id}")
                
                # Store in session state for tracking
                if 'new_test_cases' not in st.session_state:
                    st.session_state.new_test_cases = []
                
                # Process tags
                tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
                
                # Copy steps if selected
                steps = []
                if copy_steps:
                    steps = source_case.get('steps', source_case.get('Steps', []))
                
                st.session_state.new_test_cases.append({
                    "id": new_test_id,
                    "title": title,
                    "description": description,
                    "type": test_type,
                    "priority": priority,
                    "repository": repository,
                    "owner": owner,
                    "tags": tag_list,
                    "steps": steps,
                    "creation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "based_on": source_case.get('id', source_case.get('ID', 'Unknown'))
                })


def display_notify_owner_panel(details):
    """Display panel for notifying the owner about differences
    
    Args:
        details: Dictionary containing comparison details
    """
    st.markdown("### Notify Owner")
    
    # Get the matched test case and differences
    best_match = details.get('best_match', {})
    differences = details.get('differences', [])
    owner = best_match.get('owner', 'Unknown')
    
    # Information about the process
    st.info(
        f"This will send a notification to the test case owner ({owner}) "
        f"with information about the identified differences."
    )
    
    # Form for notification
    with st.form("notify_owner_form"):
        # Default subject
        subject = st.text_input(
            "Subject",
            value=f"Suggested Changes for Test Case {best_match.get('id', 'Unknown')}"
        )
        
        # Build default content
        default_content = f"""
Dear {owner},

The test comparison system has identified potential improvements for test case {best_match.get('id', 'Unknown')} - "{best_match.get('title', 'Unknown')}".

The following differences were found when comparing with another test case:

"""
        
        # Add differences to content
        for diff in differences:
            diff_type = diff.get('type', '')
            line = diff.get('line', '')
            
            if diff_type == "addition":
                default_content += f"- Addition at Step {line}: {diff.get('text', '')}\n"
            elif diff_type == "deletion":
                default_content += f"- Deletion at Step {line}: {diff.get('text', '')}\n"
            elif diff_type == "modification":
                default_content += f"- Modification at Step {line}: '{diff.get('old', '')}' → '{diff.get('new', '')}'\n"
        
        default_content += """
Please review these suggestions and update the test case if appropriate.

Thank you,
Test Repository & Comparison System
        """
        
        # Message content
        content = st.text_area(
            "Message",
            value=default_content,
            height=300
        )
        
        # Include comparison report
        include_report = st.checkbox("Include Comparison Report", value=True)
        
        submitted = st.form_submit_button("Send Notification")
        
        if submitted:
            with st.spinner(f"Sending notification to {owner}..."):
                # Call the Notification Service to send the notification
                # In a real implementation, this would use the Notification Service
                import time
                time.sleep(1)  # Simulate processing
                
                # Simulate success
                st.success(f"Notification sent to {owner} successfully!")
                
                # Store in session state for tracking
                if 'sent_notifications' not in st.session_state:
                    st.session_state.sent_notifications = []
                
                st.session_state.sent_notifications.append({
                    "recipient": owner,
                    "subject": subject,
                    "content_preview": content[:100] + "...",
                    "test_case_id": best_match.get('id', 'Unknown'),
                    "differences_count": len(differences),
                    "send_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "include_report": include_report
                })


def display_new_test_case_actions(details):
    """Display actions for new test case results
    
    Args:
        details: Dictionary containing comparison details
    """
    st.subheader("Available Actions")
    
    # Get the source case
    source_case = details.get('source_case', {})
    
    # Create options for handling the new test case
    st.markdown("### Action Options")
    
    action_option = st.radio(
        "How would you like to handle this new test case?",
        options=[
            "Create New Test Case", 
            "Assign to Coverage Gap",
            "Take No Action"
        ],
        index=0
    )
    
    if action_option == "Create New Test Case":
        display_create_new_test_case_panel(details)
    
    elif action_option == "Assign to Coverage Gap":
        display_assign_to_coverage_gap(details)
    
    else:  # Take No Action
        st.info("No action will be taken. You can still add this to the tracking list if desired.")
    
    # Add tracking list option
    if st.button("Add to 'New Cases' List", key="add_to_new"):
        # This would add the case to a tracking list
        add_to_new_list(details)
        st.success(f"Added test case to 'New Cases' list")
    
    # Option to export test case
    if st.button("Export Test Case", key="export_test_case"):
        export_test_case(source_case)


def display_assign_to_coverage_gap(details):
    """Display panel for assigning a new test case to a coverage gap
    
    Args:
        details: Dictionary containing comparison details
    """
    st.markdown("### Assign to Coverage Gap")
    
    # Get gap analysis if available
    gap_analysis = details.get('gap_analysis', {})
    
    if not gap_analysis or not gap_analysis.get('coverage_areas'):
        st.warning("No coverage gap analysis available. Please run a coverage analysis first.")
        return
    
    # Information about the process
    st.info(
        "This will assign the new test case to a coverage gap, "
        "helping to improve the overall test coverage."
    )
    
    # Coverage areas with low coverage
    coverage_areas = gap_analysis.get('coverage_areas', {})
    low_coverage_areas = {area: score for area, score in coverage_areas.items() if score < 90}
    
    if not low_coverage_areas:
        st.success("No significant coverage gaps found. All areas have at least 90% coverage.")
        return
    
    # Form for assigning to coverage gap
    with st.form("assign_gap_form"):
        # Select coverage area
        area_options = list(low_coverage_areas.keys())
        selected_area = st.selectbox(
            "Coverage Area",
            options=area_options,
            format_func=lambda x: f"{x.replace('_', ' ').title()} ({low_coverage_areas[x]}% covered)"
        )
        
        # Notes about assignment
        notes = st.text_area(
            "Assignment Notes",
            value=f"This test case addresses a coverage gap in the {selected_area.replace('_', ' ').title()} area."
        )
        
        # Suggest test case improvements
        suggest_improvements = st.checkbox("Suggest Test Case Improvements", value=True)
        
        if suggest_improvements:
            # Get recommendations for the selected area
            area_recommendations = [rec for rec in gap_analysis.get('recommendations', []) 
                                  if selected_area.lower() in rec.lower()]
            
            if area_recommendations:
                st.markdown("**Recommendations:**")
                for rec in area_recommendations:
                    st.markdown(f"- {rec}")
        
        submitted = st.form_submit_button("Assign to Gap")
        
        if submitted:
            with st.spinner("Assigning to coverage gap..."):
                # In a real implementation, this would call the Coverage Analyzer
                import time
                time.sleep(1)  # Simulate processing
                
                # Simulate success
                st.success(f"Successfully assigned to the {selected_area.replace('_', ' ').title()} coverage gap!")
                
                # Store in session state for tracking
                if 'gap_assignments' not in st.session_state:
                    st.session_state.gap_assignments = []
                
                st.session_state.gap_assignments.append({
                    "test_case_id": details.get('source_case', {}).get('id', 'Unknown'),
                    "coverage_area": selected_area,
                    "coverage_before": low_coverage_areas[selected_area],
                    "notes": notes,
                    "assignment_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })


def add_to_modification_list(details):
    """Add the comparison match to the cases needing modification tracking list
    
    Args:
        details: Dictionary containing comparison details
    """
    # Get source and best match details
    source_case = details.get('source_case', {})
    best_match = details.get('best_match', {})
    differences = details.get('differences', [])
    
    # Create a record for the case needing modification
    mod_case = {
        "id": best_match.get('id', 'Unknown'),
        "title": best_match.get('title', 'Unknown'),
        "suggested_changes": len(differences),
        "owner": best_match.get('owner', 'Unassigned'),
        "notification_status": "Pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "confidence": best_match.get('match_confidence', 0)
    }
    
# Add to session state
    if 'modification_cases' not in st.session_state:
        st.session_state.modification_cases = []
    
    # Check if already in list
    if not any(case['id'] == mod_case['id'] for case in st.session_state.modification_cases):
        st.session_state.modification_cases.append(mod_case)


def add_to_new_list(details):
    """Add the test case to the new cases tracking list
    
    Args:
        details: Dictionary containing comparison details
    """
    # Get source case details
    source_case = details.get('source_case', {})
    
    # Create a record for the new case
    new_case = {
        "id": source_case.get('id', source_case.get('ID', f"NEW{datetime.now().strftime('%Y%m%d%H%M%S')}")),
        "title": source_case.get('title', source_case.get('Title', 'Unknown')),
        "owner": st.session_state.get("user_name", "Unassigned"),
        "date_added": datetime.now().strftime("%Y-%m-%d"),
        "status": "Pending Upload"
    }
    
    # Add to session state
    if 'new_cases' not in st.session_state:
        st.session_state.new_cases = []
    
    # Check if already in list
    if not any(case['id'] == new_case['id'] for case in st.session_state.new_cases):
        st.session_state.new_cases.append(new_case)


def export_test_case(test_case):
    """Export a test case to Excel
    
    Args:
        test_case: Dictionary containing test case details
    """
    # Create a flattened version of the test case for Excel export
    flat_test_case = {
        "ID": test_case.get('id', test_case.get('ID', 'Unknown')),
        "Title": test_case.get('title', test_case.get('Title', 'Unknown')),
        "Description": test_case.get('description', test_case.get('Description', 'Unknown')),
        "Type": test_case.get('type', test_case.get('Type', 'Unknown'))
    }
    
    # Add other fields if available
    if 'priority' in test_case:
        flat_test_case["Priority"] = test_case['priority']
    
    if 'tags' in test_case:
        flat_test_case["Tags"] = ", ".join(test_case['tags']) if isinstance(test_case['tags'], list) else test_case['tags']
    
    if 'preconditions' in test_case:
        flat_test_case["Preconditions"] = test_case['preconditions']
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write basic information
        pd.DataFrame([flat_test_case]).to_excel(writer, sheet_name="Details", index=False)
        
        # Write steps if available
        steps = test_case.get('steps', test_case.get('Steps', []))
        if steps:
            steps_df = create_steps_dataframe(steps)
            steps_df.to_excel(writer, sheet_name="Steps", index=False)
    
    # Provide download button
    test_id = test_case.get('id', test_case.get('ID', 'NewTestCase'))
    
    st.download_button(
        label="Download Test Case",
        data=output.getvalue(),
        file_name=f"TestCase_{test_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.success(f"Test case exported successfully!")


def create_steps_dataframe_with_highlights(steps, differences, target_type):
    """Create a DataFrame from test steps with differences highlighted
    
    Args:
        steps: List of test steps
        differences: List of differences
        target_type: Either "source" or "target"
    
    Returns:
        DataFrame containing formatted steps with highlighting
    """
    # Create a standardized representation of steps
    formatted_steps = []
    
    for step in steps:
        # Handle different possible key names
        step_num = step.get('number', step.get('Step #', ''))
        action = step.get('action', step.get('Action', ''))
        expected = step.get('expected', step.get('Expected Result', ''))
        test_data = step.get('test_data', step.get('Test Data', ''))
        
        # Check if this step has differences
        highlight = False
        highlight_type = ""
        
        for diff in differences:
            diff_type = diff.get('type', '')
            line = diff.get('line', '')
            
            if line == step_num:
                highlight = True
                highlight_type = diff_type
                break
        
        # Apply highlighting based on difference type and target
        if highlight:
            if target_type == "source":
                if highlight_type == "addition":
                    action = f"🟢 {action}"
                elif highlight_type == "deletion":
                    action = f"🔴 {action}"
                elif highlight_type == "modification":
                    action = f"🟠 {action}"
            else:  # target
                if highlight_type == "addition":
                    action = f"⚪ {action}"  # Not present in target
                elif highlight_type == "deletion":
                    action = f"⚪ {action}"  # Only in target
                elif highlight_type == "modification":
                    action = f"🟠 {action}"  # Modified in source
        
        formatted_steps.append({
            "Step #": step_num,
            "Action": action,
            "Expected Result": expected,
            "Test Data": test_data
        })
    
    # Convert to DataFrame
    return pd.DataFrame(formatted_steps)


# Update the display_comparison_result_view function from Part 5 
# to incorporate partial and new match handling

def display_comparison_result_view():
    """Display the appropriate comparison result view based on match type"""
    if 'comparison_result' not in st.session_state or 'comparison_details' not in st.session_state:
        st.error("No comparison results available. Please run a comparison first.")
        return
    
    # Get the comparison details
    result_type = st.session_state.comparison_result
    details = st.session_state.comparison_details
    
    # Add a back button
    if st.button("Back to Comparison Setup", key="back_to_setup"):
        # Reset comparison result state
        if 'comparison_result' in st.session_state:
            del st.session_state.comparison_result
        
        # Keep the source and settings for convenience
        st.rerun()
    
    # Create tabs for different views of the comparison results
    result_tabs = st.tabs([
        "Match Overview", 
        "Detailed Comparison", 
        "Actions"
    ])
    
    with result_tabs[0]:
        # Display the appropriate overview based on match type
        if result_type == "exact":
            display_match_overview(result_type, details)
        elif result_type == "partial":
            display_partial_match_overview(details)
        else:  # result_type == "new"
            display_new_test_case_overview(details)
    
    with result_tabs[1]:
        # Display the appropriate detailed comparison based on match type
        if result_type == "exact":
            display_detailed_comparison(result_type, details)
        elif result_type == "partial":
            display_partial_match_detailed_comparison(details)
        else:  # result_type == "new"
            display_new_test_case_detailed_view(details)
    
    with result_tabs[2]:
        # Display the appropriate actions based on match type
        if result_type == "exact":
            display_exact_match_actions(details)
        elif result_type == "partial":
            display_partial_match_actions(details)
        else:  # result_type == "new"
            display_new_test_case_actions(details)


# The updated display_comparison_results function would now be:
"""
def display_comparison_results():
    st.header("Test Case Comparison")
    
    # Check if we're already in a specific comparison view
    if 'comparison_result' in st.session_state:
        # Display the appropriate comparison result view
        display_comparison_result_view()
        
        # Add a button to return to comparison setup
        if st.button("Start New Comparison"):
            # Reset comparison state
            if 'comparison_result' in st.session_state:
                del st.session_state.comparison_result
            if 'comparison_details' in st.session_state:
                del st.session_state.comparison_details
            
            # Reload the page
            st.rerun()
    else:
        # Display the comparison setup interface
        display_comparison_setup()
"""        

#######################################################
# PART 7: TRACKING LISTS - MATCHED AND MODIFIED CASES
#######################################################

# This code implements the tracking lists functionality for the repository_ui.py module,
# specifically focusing on matched cases and cases needing modification.

def display_tracking_lists():
    """Display tracking lists for matched, modified, and new test cases"""
    st.header("Tracking Lists")
    
    # Create tabs for different lists
    list_tabs = st.tabs(["Matched Cases", "Cases Needing Modification", "Newly Added Cases"])
    
    with list_tabs[0]:
        display_matched_cases()
    
    with list_tabs[1]:
        display_cases_needing_modification()
    
    with list_tabs[2]:
        # This will be implemented in Part 8
        st.info("Newly Added Cases list will be implemented in Part 8")


def display_matched_cases():
    """Display the list of matched test cases"""
    st.subheader("Matched Cases")
    
    # Initialize the matched cases list if not already in session state
    if 'matched_cases' not in st.session_state:
        st.session_state.matched_cases = []
    
    matched_cases = st.session_state.matched_cases
    
    # Add options to manage the list
    management_col1, management_col2 = st.columns([3, 1])
    
    with management_col1:
        st.markdown(f"**{len(matched_cases)}** test cases in the matched list")
    
    with management_col2:
        if st.button("Refresh", key="refresh_matched"):
            # In a real implementation, this might reload from persistent storage
            st.rerun()
    
    # Display filters if there are cases
    if matched_cases:
        with st.expander("Filters", expanded=False):
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                status_filter = st.multiselect(
                    "Status",
                    options=list(set(case.get('status', 'Pending') for case in matched_cases)),
                    default=list(set(case.get('status', 'Pending') for case in matched_cases))
                )
                
                min_similarity = st.slider(
                    "Minimum Similarity",
                    min_value=0,
                    max_value=100,
                    value=0,
                    step=5
                )
            
            with filter_col2:
                text_filter = st.text_input("Search by ID or Title")
                
                date_range = st.date_input(
                    "Date Range",
                    value=(
                        datetime.now().date().replace(day=1),  # First day of current month
                        datetime.now().date()
                    ),
                    format="MM/DD/YYYY"
                )
    
    # Display the list if there are matched cases
    if matched_cases:
        # Apply filters
        filtered_cases = []
        
        for case in matched_cases:
            # Skip if filtered by status
            if 'status_filter' in locals() and case.get('status', 'Pending') not in status_filter:
                continue
            
            # Skip if similarity is too low
            if 'min_similarity' in locals() and case.get('similarity', 0) < min_similarity:
                continue
            
            # Skip if doesn't match text filter
            if 'text_filter' in locals() and text_filter:
                if (text_filter.lower() not in case.get('id', '').lower() and
                    text_filter.lower() not in case.get('title', '').lower() and
                    text_filter.lower() not in case.get('matched_with', '').lower()):
                    continue
            
            # Skip if outside date range
            if 'date_range' in locals() and len(date_range) == 2:
                case_date = None
                try:
                    case_date = datetime.strptime(case.get('date', ''), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    # If date can't be parsed, use today's date as fallback
                    case_date = datetime.now().date()
                
                if case_date < date_range[0] or case_date > date_range[1]:
                    continue
            
            # If it passed all filters, add to filtered list
            filtered_cases.append(case)
        
        # Convert to DataFrame for display
        if filtered_cases:
            df = pd.DataFrame(filtered_cases)
            
            # Add formatted columns
            if 'similarity' in df.columns:
                df['Similarity'] = df['similarity'].apply(lambda x: f"{x}% {'🟢' if x >= 90 else '🟡' if x >= 70 else '🔴'}")
            
            if 'confidence' in df.columns:
                df['Confidence'] = df['confidence'].apply(lambda x: f"{x}% {'🟢' if x >= 90 else '🟡' if x >= 70 else '🔴'}")
            
            if 'status' in df.columns:
                df['Status'] = df['status'].apply(
                    lambda x: f"{'✅' if x == 'Executed' else '🔄' if x == 'In Progress' else '⏳'} {x}"
                )
            
            # Configure columns for display
            display_columns = {
                "id": "ID",
                "title": "Title",
                "matched_with": "Matched With",
                "date": "Date",
                "Status": "Status"
            }
            
            # Add similarity/confidence if available
            if 'Similarity' in df.columns:
                display_columns["Similarity"] = "Similarity"
            
            if 'Confidence' in df.columns:
                display_columns["Confidence"] = "Confidence"
            
            # Reorder and rename columns
            display_df = df.rename(columns=display_columns)[list(display_columns.values())]
            
            # Display as dataframe
            st.dataframe(
                display_df,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="medium"),
                    "Matched With": st.column_config.TextColumn("Matched With", width="small"),
                    "Date": st.column_config.DateColumn("Date", format="MM/DD/YYYY", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Similarity": st.column_config.TextColumn("Similarity", width="small"),
                    "Confidence": st.column_config.TextColumn("Confidence", width="small")
                },
                hide_index=True
            )
            
            # Bulk actions
            with st.expander("Bulk Actions", expanded=False):
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("Export All", key="export_all_matched"):
                        export_matched_cases(filtered_cases)
                
                with action_col2:
                    bulk_status = st.selectbox(
                        "Update Status",
                        options=["Pending", "In Progress", "Executed", "Cancelled"]
                    )
                    
                    if st.button("Apply Status", key="apply_status_matched"):
                        update_matched_cases_status(filtered_cases, bulk_status)
                        st.success(f"Updated status to {bulk_status} for {len(filtered_cases)} cases")
                        st.rerun()
                
                with action_col3:
                    if st.button("Clear All", key="clear_all_matched"):
                        if st.checkbox("Confirm clearing all filtered cases", key="confirm_clear_matched"):
                            clear_matched_cases(filtered_cases)
                            st.success(f"Cleared {len(filtered_cases)} cases from the list")
                            st.rerun()
            
            # Individual case actions
            st.subheader("Case Actions")
            
            selected_id = st.selectbox(
                "Select Test Case for Actions",
                options=[case['id'] for case in filtered_cases],
                format_func=lambda x: f"{x} - {next((case['title'] for case in filtered_cases if case['id'] == x), '')}"
            )
            
            if selected_id:
                # Get the selected case
                selected_case = next((case for case in filtered_cases if case['id'] == selected_id), None)
                
                if selected_case:
                    display_matched_case_actions(selected_case)
        else:
            st.info("No cases match the current filters.")
    else:
        st.info("No matched cases in the list yet. Compare test cases to add matches to this list.")
        
        # Show an example of how to add items
        with st.expander("How to Add Cases", expanded=True):
            st.markdown("""
            Matched cases are added to this list when:
            
            1. You find an exact match during test case comparison
            2. You manually add a match to the tracking list
            
            To add matches:
            1. Go to the "Repository Browser" tab
            2. Select a test case and click "Compare with Repository"
            3. Run the comparison
            4. When a match is found, click "Add to 'Matched Cases' List"
            """)


def display_cases_needing_modification():
    """Display the list of test cases needing modification"""
    st.subheader("Cases Needing Modification")
    
    # Initialize the modification cases list if not already in session state
    if 'modification_cases' not in st.session_state:
        st.session_state.modification_cases = []
    
    modification_cases = st.session_state.modification_cases
    
    # Add options to manage the list
    management_col1, management_col2 = st.columns([3, 1])
    
    with management_col1:
        st.markdown(f"**{len(modification_cases)}** test cases needing modification")
    
    with management_col2:
        if st.button("Refresh", key="refresh_mod"):
            # In a real implementation, this might reload from persistent storage
            st.rerun()
    
    # Display filters if there are cases
    if modification_cases:
        with st.expander("Filters", expanded=False):
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                notification_filter = st.multiselect(
                    "Notification Status",
                    options=list(set(case.get('notification_status', 'Pending') for case in modification_cases)),
                    default=list(set(case.get('notification_status', 'Pending') for case in modification_cases))
                )
                
                min_changes = st.number_input(
                    "Minimum Changes",
                    min_value=0,
                    value=0
                )
            
            with filter_col2:
                text_filter = st.text_input("Search by ID, Title or Owner")
                
                date_range = st.date_input(
                    "Date Range",
                    value=(
                        datetime.now().date().replace(day=1),  # First day of current month
                        datetime.now().date()
                    ),
                    format="MM/DD/YYYY"
                )
    
    # Display the list if there are cases
    if modification_cases:
        # Apply filters
        filtered_cases = []
        
        for case in modification_cases:
            # Skip if filtered by notification status
            if ('notification_filter' in locals() and 
                case.get('notification_status', 'Pending') not in notification_filter):
                continue
            
            # Skip if changes are too few
            if 'min_changes' in locals() and case.get('suggested_changes', 0) < min_changes:
                continue
            
            # Skip if doesn't match text filter
            if 'text_filter' in locals() and text_filter:
                if (text_filter.lower() not in case.get('id', '').lower() and
                    text_filter.lower() not in case.get('title', '').lower() and
                    text_filter.lower() not in case.get('owner', '').lower()):
                    continue
            
            # Skip if outside date range
            if 'date_range' in locals() and len(date_range) == 2:
                case_date = None
                try:
                    case_date = datetime.strptime(case.get('date', ''), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    # If date can't be parsed, use today's date as fallback
                    case_date = datetime.now().date()
                
                if case_date < date_range[0] or case_date > date_range[1]:
                    continue
            
            # If it passed all filters, add to filtered list
            filtered_cases.append(case)
        
        # Convert to DataFrame for display
        if filtered_cases:
            df = pd.DataFrame(filtered_cases)
            
            # Add formatted columns
            if 'confidence' in df.columns:
                df['Confidence'] = df['confidence'].apply(lambda x: f"{x}% {'🟢' if x >= 90 else '🟡' if x >= 70 else '🔴'}")
            
            if 'notification_status' in df.columns:
                df['Notification'] = df['notification_status'].apply(
                    lambda x: f"{'✅' if x == 'Sent' else '📨' if x == 'Reminder Sent' else '⏳'} {x}"
                )
            
            # Configure columns for display
            display_columns = {
                "id": "ID",
                "title": "Title",
                "suggested_changes": "Changes",
                "owner": "Owner",
                "Notification": "Notification",
                "date": "Date"
            }
            
            # Add confidence if available
            if 'Confidence' in df.columns:
                display_columns["Confidence"] = "Confidence"
            
            # Reorder and rename columns
            display_df = df.rename(columns=display_columns)[list(display_columns.values())]
            
            # Display as dataframe
            st.dataframe(
                display_df,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="medium"),
                    "Changes": st.column_config.NumberColumn("Changes", width="small"),
                    "Owner": st.column_config.TextColumn("Owner", width="medium"),
                    "Notification": st.column_config.TextColumn("Notification", width="small"),
                    "Date": st.column_config.DateColumn("Date", format="MM/DD/YYYY", width="small"),
                    "Confidence": st.column_config.TextColumn("Confidence", width="small")
                },
                hide_index=True
            )
            
            # Bulk actions
            with st.expander("Bulk Actions", expanded=False):
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("Export All", key="export_all_mod"):
                        export_modification_cases(filtered_cases)
                
                with action_col2:
                    if st.button("Send Bulk Reminders", key="send_bulk_reminders"):
                        # Get cases that need reminders (status is Pending)
                        reminder_cases = [case for case in filtered_cases 
                                         if case.get('notification_status', '') == 'Pending']
                        
                        if reminder_cases:
                            send_bulk_reminders(reminder_cases)
                            st.success(f"Sent reminders for {len(reminder_cases)} cases")
                            st.rerun()
                        else:
                            st.info("No cases need reminders (all have been notified already)")
                
                with action_col3:
                    if st.button("Clear All", key="clear_all_mod"):
                        if st.checkbox("Confirm clearing all filtered cases", key="confirm_clear_mod"):
                            clear_modification_cases(filtered_cases)
                            st.success(f"Cleared {len(filtered_cases)} cases from the list")
                            st.rerun()
            
            # Individual case actions
            st.subheader("Case Actions")
            
            selected_id = st.selectbox(
                "Select Test Case for Actions",
                options=[case['id'] for case in filtered_cases],
                format_func=lambda x: f"{x} - {next((case['title'] for case in filtered_cases if case['id'] == x), '')}"
            )
            
            if selected_id:
                # Get the selected case
                selected_case = next((case for case in filtered_cases if case['id'] == selected_id), None)
                
                if selected_case:
                    display_modification_case_actions(selected_case)
        else:
            st.info("No cases match the current filters.")
    else:
        st.info("No cases needing modification in the list yet. Compare test cases to add partial matches to this list.")
        
        # Show an example of how to add items
        with st.expander("How to Add Cases", expanded=True):
            st.markdown("""
            Cases needing modification are added to this list when:
            
            1. You find a partial match during test case comparison
            2. You manually add a case to the tracking list
            
            To add cases:
            1. Go to the "Repository Browser" tab
            2. Select a test case and click "Compare with Repository"
            3. Run the comparison
            4. When a partial match is found, click "Add to 'Needs Modification' List"
            """)


def display_matched_case_actions(case):
    """Display actions for a selected matched case
    
    Args:
        case: Dictionary containing matched case details
    """
    # Display case details in an expander
    with st.expander("Case Details", expanded=True):
        # Basic information
        st.markdown(f"**ID:** {case.get('id', 'Unknown')}")
        st.markdown(f"**Title:** {case.get('title', 'Unknown')}")
        st.markdown(f"**Matched With:** {case.get('matched_with', 'Unknown')}")
        st.markdown(f"**Date Added:** {case.get('date', 'Unknown')}")
        st.markdown(f"**Status:** {case.get('status', 'Pending')}")
        
        # Show similarity and confidence if available
        if 'similarity' in case:
            st.markdown(f"**Similarity:** {case['similarity']}%")
        
        if 'confidence' in case:
            st.markdown(f"**Confidence:** {case['confidence']}%")
    
    # Actions for the case
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        # View test case details
        if st.button("View Test Case", key=f"view_{case['id']}"):
            st.session_state.view_test_case = case['id']
            st.info(f"This will navigate to test case {case['id']} details view")
        
        # Status update
        new_status = st.selectbox(
            "Update Status",
            options=["Pending", "In Progress", "Executed", "Cancelled"],
            index=["Pending", "In Progress", "Executed", "Cancelled"].index(case.get('status', 'Pending')),
            key=f"status_{case['id']}"
        )
        
        if st.button("Update Status", key=f"update_{case['id']}"):
            update_matched_case_status(case, new_status)
            st.success(f"Updated status to {new_status}")
            st.rerun()
    
    with action_col2:
        # Compare again
        if st.button("Run New Comparison", key=f"compare_{case['id']}"):
            # This would set up to run a new comparison with this test case
            st.session_state.compare_test_case = case['id']
            st.info(f"This will navigate to comparison for test case {case['id']}")
        
        # Remove from list
        if st.button("Remove from List", key=f"remove_{case['id']}"):
            if st.checkbox(f"Confirm removal of {case['id']}", key=f"confirm_{case['id']}"):
                remove_matched_case(case)
                st.success(f"Removed {case['id']} from the list")
                st.rerun()


def display_modification_case_actions(case):
    """Display actions for a selected case needing modification
    
    Args:
        case: Dictionary containing case details
    """
    # Display case details in an expander
    with st.expander("Case Details", expanded=True):
        # Basic information
        st.markdown(f"**ID:** {case.get('id', 'Unknown')}")
        st.markdown(f"**Title:** {case.get('title', 'Unknown')}")
        st.markdown(f"**Owner:** {case.get('owner', 'Unassigned')}")
        st.markdown(f"**Suggested Changes:** {case.get('suggested_changes', 0)}")
        st.markdown(f"**Notification Status:** {case.get('notification_status', 'Pending')}")
        st.markdown(f"**Date Added:** {case.get('date', 'Unknown')}")
        
        # Show confidence if available
        if 'confidence' in case:
            st.markdown(f"**Confidence:** {case['confidence']}%")
    
    # Actions for the case
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        # View test case details
        if st.button("View Test Case", key=f"view_{case['id']}"):
            st.session_state.view_test_case = case['id']
            st.info(f"This will navigate to test case {case['id']} details view")
    
    with action_col2:
        # Send notification or reminder
        if case.get('notification_status', 'Pending') == 'Pending':
            if st.button("Send Notification", key=f"notify_{case['id']}"):
                send_modification_notification(case)
                st.success(f"Notification sent to {case.get('owner', 'Unknown')}")
                st.rerun()
        else:
            if st.button("Send Reminder", key=f"remind_{case['id']}"):
                send_modification_reminder(case)
                st.success(f"Reminder sent to {case.get('owner', 'Unknown')}")
                st.rerun()
    
    with action_col3:
        # Remove from list
        if st.button("Remove from List", key=f"remove_{case['id']}"):
            if st.checkbox(f"Confirm removal of {case['id']}", key=f"confirm_{case['id']}"):
                remove_modification_case(case)
                st.success(f"Removed {case['id']} from the list")
                st.rerun()
    
    # Additional actions
    st.markdown("### Additional Actions")
    
    action2_col1, action2_col2 = st.columns(2)
    
    with action2_col1:
        # Create new version
        if st.button("Create New Version", key=f"newver_{case['id']}"):
            st.info(f"This would start the process to create a new version of {case['id']}")
            
            # In a real implementation, this would navigate to or open the new version UI
            # For now, we'll just show an example form
            with st.form(f"newversion_form_{case['id']}"):
                st.markdown(f"**Creating New Version of {case['id']}**")
                
                version_notes = st.text_area(
                    "Version Notes",
                    value=f"Applied suggested changes. {case.get('suggested_changes', 0)} changes identified."
                )
                
                submitted = st.form_submit_button("Create Version")
                
                if submitted:
                    st.success(f"New version of {case['id']} created successfully!")
                    
                    # Update the case status
                    case['notification_status'] = 'Completed'
                    st.rerun()
    
    with action2_col2:
        # Compare again
        if st.button("Run New Comparison", key=f"compare_{case['id']}"):
            # This would set up to run a new comparison with this test case
            st.session_state.compare_test_case = case['id']
            st.info(f"This will navigate to comparison for test case {case['id']}")


# Helper functions for tracking lists

def export_matched_cases(cases):
    """Export matched cases to Excel
    
    Args:
        cases: List of matched cases to export
    """
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write cases to Excel
        df = pd.DataFrame(cases)
        df.to_excel(writer, sheet_name="Matched Cases", index=False)
    
    # Provide download button
    st.download_button(
        label="Download Matched Cases",
        data=output.getvalue(),
        file_name=f"matched_cases_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.success(f"Exported {len(cases)} matched cases")


def export_modification_cases(cases):
    """Export cases needing modification to Excel
    
    Args:
        cases: List of cases to export
    """
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write cases to Excel
        df = pd.DataFrame(cases)
        df.to_excel(writer, sheet_name="Modification Cases", index=False)
    
    # Provide download button
    st.download_button(
        label="Download Modification Cases",
        data=output.getvalue(),
        file_name=f"modification_cases_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.success(f"Exported {len(cases)} cases needing modification")


def update_matched_cases_status(cases, new_status):
    """Update the status of multiple matched cases
    
    Args:
        cases: List of cases to update
        new_status: New status to set
    """
    # Update each case in the list
    for case in cases:
        case_id = case.get('id')
        
        # Find and update the case in the session state
        for tracked_case in st.session_state.matched_cases:
            if tracked_case.get('id') == case_id:
                tracked_case['status'] = new_status
                break


def update_matched_case_status(case, new_status):
    """Update the status of a single matched case
    
    Args:
        case: Case to update
        new_status: New status to set
    """
    case_id = case.get('id')
    
    # Find and update the case in the session state
    for tracked_case in st.session_state.matched_cases:
        if tracked_case.get('id') == case_id:
            tracked_case['status'] = new_status
            break


def clear_matched_cases(cases):
    """Remove multiple matched cases from the tracking list
    
    Args:
        cases: List of cases to remove
    """
    # Get case IDs to remove
    case_ids = [case.get('id') for case in cases]
    
    # Filter out the cases from the session state
    st.session_state.matched_cases = [
        case for case in st.session_state.matched_cases
        if case.get('id') not in case_ids
    ]


def remove_matched_case(case):
    """Remove a single matched case from the tracking list
    
    Args:
        case: Case to remove
    """
    case_id = case.get('id')
    
    # Filter out the case from the session state
    st.session_state.matched_cases = [
        tracked_case for tracked_case in st.session_state.matched_cases
        if tracked_case.get('id') != case_id
    ]


def clear_modification_cases(cases):
    """Remove multiple cases needing modification from the tracking list
    
    Args:
        cases: List of cases to remove
    """
    # Get case IDs to remove
    case_ids = [case.get('id') for case in cases]
    
    # Filter out the cases from the session state
    st.session_state.modification_cases = [
        case for case in st.session_state.modification_cases
        if case.get('id') not in case_ids
    ]


def remove_modification_case(case):
    """Remove a single case needing modification from the tracking list
    
    Args:
        case: Case to remove
    """
    case_id = case.get('id')
    
    # Filter out the case from the session state
    st.session_state.modification_cases = [
        tracked_case for tracked_case in st.session_state.modification_cases
        if tracked_case.get('id') != case_id
    ]


def send_bulk_reminders(cases):
    """Send reminders to owners of multiple cases needing modification
    
    Args:
        cases: List of cases to send reminders for
    """
    # Send a reminder for each case
    for case in cases:
        send_modification_reminder(case)


def send_modification_notification(case):
    """Send a notification to the owner of a case needing modification
    
    Args:
        case: Case to send notification for
    """
    # In a real implementation, this would call the notification service
    # For now, we'll just update the case status
    case_id = case.get('id')
    
    # Find and update the case in the session state
    for tracked_case in st.session_state.modification_cases:
        if tracked_case.get('id') == case_id:
            tracked_case['notification_status'] = 'Sent'
            break


def send_modification_reminder(case):
    """Send a reminder to the owner of a case needing modification
    
    Args:
        case: Case to send reminder for
    """
    # In a real implementation, this would call the notification service
    # For now, we'll just update the case status
    case_id = case.get('id')
    
    # Find and update the case in the session state
    for tracked_case in st.session_state.modification_cases:
        if tracked_case.get('id') == case_id:
            tracked_case['notification_status'] = 'Reminder Sent'
            break


#######################################################
# PART 8: TRACKING LISTS - NEW CASES AND UTILITIES
#######################################################

# This code completes the tracking lists functionality for the repository_ui.py module,
# implementing the newly added cases list and utility functions.

def display_newly_added_cases():
    """Display the list of newly added test cases"""
    st.subheader("Newly Added Cases")
    
    # Initialize the new cases list if not already in session state
    if 'new_cases' not in st.session_state:
        st.session_state.new_cases = []
    
    new_cases = st.session_state.new_cases
    
    # Add options to manage the list
    management_col1, management_col2 = st.columns([3, 1])
    
    with management_col1:
        st.markdown(f"**{len(new_cases)}** newly added test cases")
    
    with management_col2:
        if st.button("Refresh", key="refresh_new"):
            # In a real implementation, this might reload from persistent storage
            st.rerun()
    
    # Display filters if there are cases
    if new_cases:
        with st.expander("Filters", expanded=False):
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                status_filter = st.multiselect(
                    "Status",
                    options=list(set(case.get('status', 'Pending Upload') for case in new_cases)),
                    default=list(set(case.get('status', 'Pending Upload') for case in new_cases))
                )
                
                owner_filter = st.text_input("Owner")
            
            with filter_col2:
                text_filter = st.text_input("Search by ID or Title")
                
                date_range = st.date_input(
                    "Date Range",
                    value=(
                        datetime.now().date().replace(day=1),  # First day of current month
                        datetime.now().date()
                    ),
                    format="MM/DD/YYYY"
                )
    
    # Display the list if there are new cases
    if new_cases:
        # Apply filters
        filtered_cases = []
        
        for case in new_cases:
            # Skip if filtered by status
            if 'status_filter' in locals() and case.get('status', 'Pending Upload') not in status_filter:
                continue
            
            # Skip if filtered by owner
            if 'owner_filter' in locals() and owner_filter:
                if owner_filter.lower() not in case.get('owner', '').lower():
                    continue
            
            # Skip if doesn't match text filter
            if 'text_filter' in locals() and text_filter:
                if (text_filter.lower() not in case.get('id', '').lower() and
                    text_filter.lower() not in case.get('title', '').lower()):
                    continue
            
            # Skip if outside date range
            if 'date_range' in locals() and len(date_range) == 2:
                case_date = None
                try:
                    case_date = datetime.strptime(case.get('date_added', ''), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    # If date can't be parsed, use today's date as fallback
                    case_date = datetime.now().date()
                
                if case_date < date_range[0] or case_date > date_range[1]:
                    continue
            
            # If it passed all filters, add to filtered list
            filtered_cases.append(case)
        
        # Convert to DataFrame for display
        if filtered_cases:
            df = pd.DataFrame(filtered_cases)
            
            # Add formatted status column
            if 'status' in df.columns:
                df['Status'] = df['status'].apply(
                    lambda x: f"{'📝' if x == 'Pending Upload' else '✅' if x == 'Uploaded' else '🔄' if x == 'In Progress' else '⏳'} {x}"
                )
            
            # Configure columns for display
            display_columns = {
                "id": "ID",
                "title": "Title",
                "owner": "Owner",
                "date_added": "Date Added",
                "Status": "Status"
            }
            
            # Reorder and rename columns
            display_df = df.rename(columns=display_columns)[list(display_columns.values())]
            
            # Display as dataframe
            st.dataframe(
                display_df,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="medium"),
                    "Owner": st.column_config.TextColumn("Owner", width="medium"),
                    "Date Added": st.column_config.DateColumn("Date Added", format="MM/DD/YYYY", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small")
                },
                hide_index=True
            )
            
            # Bulk actions
            with st.expander("Bulk Actions", expanded=False):
                action_col1, action_col2, action_col3 = st.columns(3)
                
                with action_col1:
                    if st.button("Export All", key="export_all_new"):
                        export_new_cases(filtered_cases)
                
                with action_col2:
                    bulk_status = st.selectbox(
                        "Update Status",
                        options=["Pending Upload", "In Progress", "Uploaded", "Cancelled"]
                    )
                    
                    if st.button("Apply Status", key="apply_status_new"):
                        update_new_cases_status(filtered_cases, bulk_status)
                        st.success(f"Updated status to {bulk_status} for {len(filtered_cases)} cases")
                        st.rerun()
                
                with action_col3:
                    if st.button("Clear All", key="clear_all_new"):
                        if st.checkbox("Confirm clearing all filtered cases", key="confirm_clear_new"):
                            clear_new_cases(filtered_cases)
                            st.success(f"Cleared {len(filtered_cases)} cases from the list")
                            st.rerun()
            
            # Bulk notifications
            with st.expander("Bulk Notifications", expanded=False):
                st.markdown("Send notifications to owners of new test cases")
                
                notify_col1, notify_col2 = st.columns(2)
                
                with notify_col1:
                    notify_subject = st.text_input(
                        "Notification Subject",
                        value="New Test Case Assignment"
                    )
                
                with notify_col2:
                    notify_template = st.selectbox(
                        "Notification Template",
                        options=["Standard Assignment", "Urgent Request", "FYI Only"]
                    )
                
                notify_message = st.text_area(
                    "Message (Optional)",
                    value="",
                    placeholder="Add any additional information for the notification"
                )
                
                if st.button("Send Bulk Notifications", key="send_bulk_new_notifications"):
                    send_bulk_new_case_notifications(filtered_cases, notify_subject, notify_template, notify_message)
                    st.success(f"Sent notifications for {len(filtered_cases)} new cases")
            
            # Individual case actions
            st.subheader("Case Actions")
            
            selected_id = st.selectbox(
                "Select Test Case for Actions",
                options=[case['id'] for case in filtered_cases],
                format_func=lambda x: f"{x} - {next((case['title'] for case in filtered_cases if case['id'] == x), '')}"
            )
            
            if selected_id:
                # Get the selected case
                selected_case = next((case for case in filtered_cases if case['id'] == selected_id), None)
                
                if selected_case:
                    display_new_case_actions(selected_case)
        else:
            st.info("No cases match the current filters.")
    else:
        st.info("No newly added cases in the list yet. Compare test cases to add new cases to this list.")
        
        # Show an example of how to add items
        with st.expander("How to Add Cases", expanded=True):
            st.markdown("""
            New cases are added to this list when:
            
            1. You find no significant matches during test case comparison
            2. You manually create a new test case from a partial match
            3. You manually add a case to the tracking list
            
            To add new cases:
            1. Go to the "Repository Browser" tab
            2. Select a test case and click "Compare with Repository"
            3. Run the comparison
            4. When no match is found, click "Add to 'New Cases' List"
            """)


def display_new_case_actions(case):
    """Display actions for a selected new case
    
    Args:
        case: Dictionary containing new case details
    """
    # Display case details in an expander
    with st.expander("Case Details", expanded=True):
        # Basic information
        st.markdown(f"**ID:** {case.get('id', 'Unknown')}")
        st.markdown(f"**Title:** {case.get('title', 'Unknown')}")
        st.markdown(f"**Owner:** {case.get('owner', 'Unassigned')}")
        st.markdown(f"**Date Added:** {case.get('date_added', 'Unknown')}")
        st.markdown(f"**Status:** {case.get('status', 'Pending Upload')}")
    
    # Actions for the case
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        # Upload to repository
        if st.button("Upload to Repository", key=f"upload_{case['id']}"):
            upload_new_case_to_repository(case)
    
    with action_col2:
        # Notify owner
        if st.button("Notify Owner", key=f"notify_{case['id']}"):
            notify_new_case_owner(case)
    
    with action_col3:
        # Remove from list
        if st.button("Remove from List", key=f"remove_{case['id']}"):
            if st.checkbox(f"Confirm removal of {case['id']}", key=f"confirm_{case['id']}"):
                remove_new_case(case)
                st.success(f"Removed {case['id']} from the list")
                st.rerun()
    
    # Status update
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        new_status = st.selectbox(
            "Update Status",
            options=["Pending Upload", "In Progress", "Uploaded", "Cancelled"],
            index=["Pending Upload", "In Progress", "Uploaded", "Cancelled"].index(case.get('status', 'Pending Upload')),
            key=f"status_{case['id']}"
        )
    
    with status_col2:
        if st.button("Update Status", key=f"update_{case['id']}"):
            update_new_case_status(case, new_status)
            st.success(f"Updated status to {new_status}")
            st.rerun()
    
    # Additional actions
    st.markdown("### Additional Actions")
    
    # Edit test case
    with st.expander("Edit Test Case", expanded=False):
        # Pre-fill with existing case data
        edit_title = st.text_input("Title", value=case.get('title', ''))
        edit_description = st.text_area("Description", value=case.get('description', ''))
        
        edit_col1, edit_col2 = st.columns(2)
        
        with edit_col1:
            edit_type = st.selectbox(
                "Type",
                options=["Manual", "Automated"],
                index=0 if case.get('type', '') != "Automated" else 1
            )
        
        with edit_col2:
            edit_owner = st.text_input("Owner", value=case.get('owner', ''))
        
        if st.button("Save Changes", key=f"save_{case['id']}"):
            # Update the case in the session state
            update_new_case_details(case, edit_title, edit_description, edit_type, edit_owner)
            st.success("Changes saved successfully")
            st.rerun()
    
    # Export
    if st.button("Export Test Case", key=f"export_{case['id']}"):
        export_single_new_case(case)


# Helper functions for managing new cases

def export_new_cases(cases):
    """Export new cases to Excel
    
    Args:
        cases: List of new cases to export
    """
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write cases to Excel
        df = pd.DataFrame(cases)
        df.to_excel(writer, sheet_name="New Cases", index=False)
    
    # Provide download button
    st.download_button(
        label="Download New Cases",
        data=output.getvalue(),
        file_name=f"new_cases_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.success(f"Exported {len(cases)} new cases")


def export_single_new_case(case):
    """Export a single new case to Excel
    
    Args:
        case: Case to export
    """
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write case to Excel
        df = pd.DataFrame([case])
        df.to_excel(writer, sheet_name="Test Case", index=False)
        
        # Add steps if available
        if 'steps' in case and case['steps']:
            steps_df = pd.DataFrame(case['steps'])
            steps_df.to_excel(writer, sheet_name="Steps", index=False)
    
    # Provide download button
    st.download_button(
        label="Download Test Case",
        data=output.getvalue(),
        file_name=f"test_case_{case['id']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.success(f"Exported test case {case['id']}")


def update_new_cases_status(cases, new_status):
    """Update the status of multiple new cases
    
    Args:
        cases: List of cases to update
        new_status: New status to set
    """
    # Update each case in the list
    for case in cases:
        case_id = case.get('id')
        
        # Find and update the case in the session state
        for tracked_case in st.session_state.new_cases:
            if tracked_case.get('id') == case_id:
                tracked_case['status'] = new_status
                break


def update_new_case_status(case, new_status):
    """Update the status of a single new case
    
    Args:
        case: Case to update
        new_status: New status to set
    """
    case_id = case.get('id')
    
    # Find and update the case in the session state
    for tracked_case in st.session_state.new_cases:
        if tracked_case.get('id') == case_id:
            tracked_case['status'] = new_status
            break


def update_new_case_details(case, title, description, test_type, owner):
    """Update the details of a new case
    
    Args:
        case: Case to update
        title: New title
        description: New description
        test_type: New test type
        owner: New owner
    """
    case_id = case.get('id')
    
    # Find and update the case in the session state
    for tracked_case in st.session_state.new_cases:
        if tracked_case.get('id') == case_id:
            tracked_case['title'] = title
            tracked_case['description'] = description
            tracked_case['type'] = test_type
            tracked_case['owner'] = owner
            break


def clear_new_cases(cases):
    """Remove multiple new cases from the tracking list
    
    Args:
        cases: List of cases to remove
    """
    # Get case IDs to remove
    case_ids = [case.get('id') for case in cases]
    
    # Filter out the cases from the session state
    st.session_state.new_cases = [
        case for case in st.session_state.new_cases
        if case.get('id') not in case_ids
    ]


def remove_new_case(case):
    """Remove a single new case from the tracking list
    
    Args:
        case: Case to remove
    """
    case_id = case.get('id')
    
    # Filter out the case from the session state
    st.session_state.new_cases = [
        tracked_case for tracked_case in st.session_state.new_cases
        if tracked_case.get('id') != case_id
    ]


def upload_new_case_to_repository(case):
    """Upload a new case to the repository
    
    Args:
        case: Case to upload
    """
    # In a real implementation, this would call the appropriate repository connector
    # For now, we'll simulate the process
    
    case_id = case.get('id')
    
    # Display a form for selecting repository and additional details
    with st.form(f"upload_form_{case_id}"):
        st.markdown(f"**Upload Test Case {case_id} to Repository**")
        
        repository = st.selectbox(
            "Target Repository",
            options=["SharePoint", "JIRA", "ALM"],
            index=0
        )
        
        folder = st.text_input(
            "Folder/Project",
            value="Test Cases"
        )
        
        add_tags = st.text_input(
            "Additional Tags (comma-separated)",
            value=""
        )
        
        submitted = st.form_submit_button("Upload")
        
        if submitted:
            with st.spinner(f"Uploading test case to {repository}..."):
                # Simulate upload process
                import time
                time.sleep(2)
                
                # Update case status to Uploaded
                for tracked_case in st.session_state.new_cases:
                    if tracked_case.get('id') == case_id:
                        tracked_case['status'] = "Uploaded"
                        tracked_case['repository'] = repository
                        if add_tags:
                            tracked_case['tags'] = add_tags.split(",")
                        break
                
                st.success(f"Test case {case_id} successfully uploaded to {repository}")
                
                # Show new permanent ID if one was assigned
                if repository == "JIRA" or repository == "ALM":
                    new_id = f"{repository[:2]}-{int(time.time())}"
                    st.info(f"New permanent ID assigned: {new_id}")
                    
                    # Update the ID in session state
                    for tracked_case in st.session_state.new_cases:
                        if tracked_case.get('id') == case_id:
                            tracked_case['permanent_id'] = new_id
                            break


def notify_new_case_owner(case):
    """Notify the owner of a new case
    
    Args:
        case: Case to notify about
    """
    # In a real implementation, this would call the notification service
    # For now, we'll simulate the process
    
    case_id = case.get('id')
    owner = case.get('owner', 'Unassigned')
    
    # Display a form for notification details
    with st.form(f"notify_form_{case_id}"):
        st.markdown(f"**Notify {owner} about Test Case {case_id}**")
        
        subject = st.text_input(
            "Subject",
            value=f"New Test Case Assignment: {case_id}"
        )
        
        content = st.text_area(
            "Message",
            value=f"""
Dear {owner},

You have been assigned a new test case: {case_id} - {case.get('title', '')}.

Please review the test case and take appropriate action.

Thank you,
Test Repository & Comparison System
            """
        )
        
        include_attachment = st.checkbox("Include Test Case as Attachment", value=True)
        
        submitted = st.form_submit_button("Send Notification")
        
        if submitted:
            with st.spinner(f"Sending notification to {owner}..."):
                # Simulate notification process
                import time
                time.sleep(1)
                
                # Update notification status
                for tracked_case in st.session_state.new_cases:
                    if tracked_case.get('id') == case_id:
                        tracked_case['notification_sent'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        break
                
                st.success(f"Notification sent to {owner}")


def send_bulk_new_case_notifications(cases, subject, template, message):
    """Send notifications to owners of multiple new cases
    
    Args:
        cases: List of cases to send notifications for
        subject: Notification subject
        template: Notification template to use
        message: Additional message to include
    """
    # Count successful notifications
    success_count = 0
    
    # Process each case
    for case in cases:
        owner = case.get('owner', '')
        case_id = case.get('id', '')
        
        # Skip cases with no owner
        if not owner or owner == 'Unassigned':
            continue
        
        # Build notification based on template
        if template == "Standard Assignment":
            content = f"""
Dear {owner},

You have been assigned a new test case: {case_id} - {case.get('title', '')}.

{message}

Thank you,
Test Repository & Comparison System
            """
        elif template == "Urgent Request":
            content = f"""
URGENT REQUEST

Dear {owner},

You have been assigned a new test case that requires immediate attention:
{case_id} - {case.get('title', '')}

{message}

Please prioritize this test case.

Thank you,
Test Repository & Comparison System
            """
        else:  # FYI Only
            content = f"""
FOR YOUR INFORMATION

Dear {owner},

A new test case has been created that may be relevant to your work:
{case_id} - {case.get('title', '')}

{message}

No immediate action is required, but please be aware of this new test case.

Thank you,
Test Repository & Comparison System
            """
        
        # In a real implementation, this would call the notification service
        # For now, we'll just update the notification status
        
        # Update notification status
        for tracked_case in st.session_state.new_cases:
            if tracked_case.get('id') == case_id:
                tracked_case['notification_sent'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                success_count += 1
                break
    
    # Return number of successful notifications
    return success_count


#######################################################
# UTILITY FUNCTIONS
#######################################################

def check_session_state_initialization():
    """Initialize necessary session state variables if they don't exist"""
    # Initialize user information
    if 'user_name' not in st.session_state:
        st.session_state.user_name = "Demo User"
    
    # Initialize tracking lists
    if 'matched_cases' not in st.session_state:
        st.session_state.matched_cases = []
    
    if 'modification_cases' not in st.session_state:
        st.session_state.modification_cases = []
    
    if 'new_cases' not in st.session_state:
        st.session_state.new_cases = []
    
    # Initialize navigation state
    if 'view_test_case' not in st.session_state:
        st.session_state.view_test_case = None
    
    if 'compare_test_case' not in st.session_state:
        st.session_state.compare_test_case = None
    
    # Initialize sample data if needed for demonstration
    initialize_sample_data()


def initialize_sample_data():
    """Initialize sample data for demonstration if lists are empty"""
    # Add sample matched cases if list is empty
    if not st.session_state.matched_cases:
        st.session_state.matched_cases = [
            {
                "id": "TC1001",
                "title": "Login Authentication Test",
                "matched_with": "GEN001",
                "status": "Executed",
                "date": "2025-04-20",
                "similarity": 98,
                "confidence": 95
            },
            {
                "id": "TC1005",
                "title": "Logout Function Test",
                "matched_with": "GEN005",
                "status": "Pending",
                "date": "2025-04-21",
                "similarity": 96,
                "confidence": 93
            }
        ]
    
    # Add sample modification cases if list is empty
    if not st.session_state.modification_cases:
        st.session_state.modification_cases = [
            {
                "id": "TC1002",
                "title": "User Profile Update Test",
                "suggested_changes": 2,
                "owner": "John Doe",
                "notification_status": "Sent",
                "date": "2025-04-23",
                "confidence": 85
            },
            {
                "id": "TC1007",
                "title": "Payment Processing Test",
                "suggested_changes": 3,
                "owner": "Alice Brown",
                "notification_status": "Pending",
                "date": "2025-04-24",
                "confidence": 75
            }
        ]
    
    # Add sample new cases if list is empty
    if not st.session_state.new_cases:
        st.session_state.new_cases = [
            {
                "id": "TC1020",
                "title": "API Authentication Test",
                "owner": "Mary Johnson",
                "date_added": "2025-04-24",
                "status": "Pending Upload",
                "description": "Test API authentication with valid and invalid credentials"
            },
            {
                "id": "TC1021",
                "title": "Database Backup Test",
                "owner": "Robert Lee",
                "date_added": "2025-04-25",
                "status": "Uploaded",
                "description": "Verify database backup functionality"
            }
        ]


def handle_errors(func):
    """Decorator for error handling
    
    Args:
        func: Function to wrap with error handling
    
    Returns:
        Wrapped function with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            
            # Log the error
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in {func.__name__}: {error_details}")
            
            # Provide recovery options
            st.info("Please try refreshing the page or contact support if the issue persists.")
    
    return wrapper


# Update the main function to use session state initialization and error handling

@handle_errors
def display_repository_ui_with_initialization():
    """Enhanced main function with initialization and error handling"""
    # Initialize session state
    check_session_state_initialization()
    
    # Display the UI
    st.title("Test Repository & Comparison Module")
    
    # Create tabs for different sections
    tabs = st.tabs(["Repository Browser", "Comparison Results", "Tracking Lists"])
    
    with tabs[0]:
        # Check if we're viewing a test case
        if 'view_test_case' in st.session_state and st.session_state.view_test_case:
            # Add a back button
            if st.button("Back to Repository"):
                st.session_state.view_test_case = None
                st.rerun()
            
            # Display test case details
            display_test_case_details(st.session_state.view_test_case)
        else:
            # Display the repository browser
            display_repository_browser()
    
    with tabs[1]:
        display_comparison_results()
    
    with tabs[2]:
        display_tracking_lists()


# Update the entry point to use the enhanced function

if __name__ == "__main__":
    # When run directly, display the repository UI with initialization and error handling
    st.set_page_config(page_title="Test Repository & Comparison Module", layout="wide")
    display_repository_ui_with_initialization()


# This completes Part 8 and the entire repository_ui.py module implementation.
# The module now provides a comprehensive UI for:
# 1. Browsing and managing test cases in the repository
# 2. Comparing test cases with various sources
# 3. Tracking matches, cases needing modification, and new test cases
# 4. Taking appropriate actions based on comparison results
# 5. Managing the entire test case lifecycle with proper error handling        