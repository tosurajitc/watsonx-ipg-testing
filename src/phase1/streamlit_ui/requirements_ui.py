"""
requirements_ui.py - Requirements Management for Watsonx IPG Testing Platform

This module provides the interface for inputting and processing requirements
to generate testable scenarios. It supports JIRA connection, file uploads,
and manual input options.
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time

# Mock data functions - replace with actual implementations in production
def fetch_jira_requirements(jira_url, project_key, issue_types, statuses, jql_query):
    """
    Fetch requirements from JIRA based on provided filters
    In production, this would use the JIRA API client
    """
    # Simulate API delay
    with st.spinner("Fetching data from JIRA..."):
        time.sleep(2)
    
    # Mock data
    requirements = [
        {"id": "IPG-101", "title": "User Login Authentication", "type": "Story", "status": "Ready for Testing", 
         "description": "As a user, I want to authenticate using my credentials so that I can access my account.", 
         "acceptance_criteria": "1. Valid credentials allow login\n2. Invalid credentials show error\n3. Locked accounts prevent login"},
        {"id": "IPG-102", "title": "Payment Processing", "type": "Story", "status": "In Development", 
         "description": "As a customer, I want to process payments using multiple methods so that I can complete my purchase.", 
         "acceptance_criteria": "1. Credit card payments work\n2. PayPal integration functions\n3. Payment errors are handled gracefully"},
        {"id": "IPG-103", "title": "User Profile Management", "type": "Epic", "status": "Ready for Testing", 
         "description": "As a user, I want to manage my profile information so that I can keep my details up-to-date.", 
         "acceptance_criteria": "1. Users can view profile\n2. Users can edit details\n3. Changes are saved correctly"},
        {"id": "IPG-104", "title": "Cart Checkout Flow", "type": "Story", "status": "Ready for Testing", 
         "description": "As a customer, I want a streamlined checkout process so that I can complete my purchase quickly.", 
         "acceptance_criteria": "1. Items in cart are displayed\n2. Shipping options work\n3. Order summary is accurate"},
        {"id": "IPG-105", "title": "Admin Dashboard", "type": "Epic", "status": "Backlog", 
         "description": "As an admin, I want a comprehensive dashboard so that I can monitor system activities.", 
         "acceptance_criteria": "1. User statistics are displayed\n2. System health metrics work\n3. Admin can access all controls"}
    ]
    
    if jql_query:
        # Simple mock filtering - in production would be handled by JQL
        filtered = []
        for req in requirements:
            if jql_query.lower() in req["title"].lower() or jql_query.lower() in req["description"].lower():
                filtered.append(req)
        requirements = filtered
    
    return pd.DataFrame(requirements)

def parse_uploaded_file(uploaded_file):
    """
    Parse uploaded requirements file based on its format
    Supports Word, Excel, PDF, and Text files
    """
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    # Simulate processing delay
    with st.spinner(f"Processing {file_type.upper()} file..."):
        time.sleep(2)
    
    # Mock parsing logic - would be replaced with actual parsers
    if file_type in ['doc', 'docx']:
        # Mock Word document parsing
        requirements = [
            {"id": "REQ-001", "title": "User Authentication", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall authenticate users via username and password.", 
             "priority": "High"},
            {"id": "REQ-002", "title": "Password Reset", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall allow users to reset their password via email.", 
             "priority": "Medium"},
            {"id": "REQ-003", "title": "Account Lockout", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall lock an account after 5 failed login attempts.", 
             "priority": "High"}
        ]
    elif file_type in ['xls', 'xlsx']:
        # Mock Excel parsing
        requirements = [
            {"id": "REQ-101", "title": "Payment Processing", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall process payments through multiple gateways.", 
             "priority": "Critical"},
            {"id": "REQ-102", "title": "Payment Confirmation", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall confirm successful payments via email.", 
             "priority": "High"},
            {"id": "REQ-103", "title": "Payment Failure Handling", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall provide clear error messages for failed payments.", 
             "priority": "High"}
        ]
    elif file_type == 'pdf':
        # Mock PDF parsing
        requirements = [
            {"id": "REQ-201", "title": "User Registration", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall allow new users to register with email verification.", 
             "priority": "High"},
            {"id": "REQ-202", "title": "Terms Acceptance", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall require users to accept terms and conditions during registration.", 
             "priority": "Medium"}
        ]
    else:  # Text files
        # Mock text parsing
        requirements = [
            {"id": "REQ-301", "title": "Search Functionality", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall provide search capability across all content.", 
             "priority": "Medium"},
            {"id": "REQ-302", "title": "Search Filters", "source": uploaded_file.name, "status": "Pending Analysis", 
             "description": "The system shall allow filtering search results by various criteria.", 
             "priority": "Low"}
        ]
    
    return pd.DataFrame(requirements)

def generate_scenarios(requirement_id):
    """
    Generate test scenarios from a requirement using AI
    This would call the LLM service in production
    """
    # Simulate AI processing
    with st.spinner("AI is generating test scenarios..."):
        time.sleep(3)
    
    # Mock generated scenarios
    if "login" in requirement_id.lower() or "auth" in requirement_id.lower():
        scenarios = [
            {"id": f"{requirement_id}-S1", "title": "Valid Login Credentials", 
             "description": "Test that a user can successfully log in with valid credentials"},
            {"id": f"{requirement_id}-S2", "title": "Invalid Username", 
             "description": "Test that appropriate error is shown when invalid username is entered"},
            {"id": f"{requirement_id}-S3", "title": "Invalid Password", 
             "description": "Test that appropriate error is shown when invalid password is entered"},
            {"id": f"{requirement_id}-S4", "title": "Account Lockout", 
             "description": "Test that account is locked after multiple failed attempts"},
            {"id": f"{requirement_id}-S5", "title": "Password Reset", 
             "description": "Test that password reset functionality works correctly"}
        ]
    elif "payment" in requirement_id.lower():
        scenarios = [
            {"id": f"{requirement_id}-S1", "title": "Credit Card Payment", 
             "description": "Test that payment can be processed with a valid credit card"},
            {"id": f"{requirement_id}-S2", "title": "PayPal Payment", 
             "description": "Test that payment can be processed through PayPal"},
            {"id": f"{requirement_id}-S3", "title": "Invalid Card Number", 
             "description": "Test that appropriate error is shown for invalid card numbers"},
            {"id": f"{requirement_id}-S4", "title": "Expired Card", 
             "description": "Test that appropriate error is shown for expired cards"},
            {"id": f"{requirement_id}-S5", "title": "Payment Confirmation", 
             "description": "Test that confirmation is sent after successful payment"}
        ]
    else:
        scenarios = [
            {"id": f"{requirement_id}-S1", "title": "Basic Functionality", 
             "description": "Test that the basic functionality works as expected"},
            {"id": f"{requirement_id}-S2", "title": "Edge Case Handling", 
             "description": "Test that edge cases are handled appropriately"},
            {"id": f"{requirement_id}-S3", "title": "Error Conditions", 
             "description": "Test that error conditions are handled gracefully"}
        ]
    
    return pd.DataFrame(scenarios)

def render_requirements_ui():
    """Render the requirements management UI"""
    st.markdown("<h2 class='sub-header'>Requirements Module</h2>", unsafe_allow_html=True)
    
    # Create tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["Connect to JIRA", "Upload File", "Manual Input"])
    
    # Tab 1: Connect to JIRA
    with tab1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Connect to JIRA")
        
        with st.form("jira_connection_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                jira_url = st.text_input("JIRA URL", value="https://jira.example.com")
                project_key = st.text_input("Project Key", value="IPG")
                auth_type = st.selectbox("Authentication Type", ["API Token", "OAuth", "Basic Auth"])
            
            with col2:
                if auth_type == "API Token":
                    st.text_input("API Token", type="password")
                elif auth_type == "OAuth":
                    st.text_input("OAuth Token", type="password")
                else:
                    st.text_input("Username")
                    st.text_input("Password", type="password")
            
            st.subheader("Filters")
            col1, col2 = st.columns(2)
            
            with col1:
                issue_types = st.multiselect(
                    "Issue Types",
                    ["Story", "Bug", "Task", "Epic", "Feature"],
                    default=["Story", "Epic"]
                )
                
                statuses = st.multiselect(
                    "Status",
                    ["Backlog", "Ready for Development", "In Development", "Ready for Testing", "Done"],
                    default=["Ready for Testing", "In Development"]
                )
            
            with col2:
                jql_query = st.text_area("Custom JQL Query (Optional)", height=124)
            
            submitted = st.form_submit_button("Fetch Requirements")
            
            if submitted:
                requirements_df = fetch_jira_requirements(
                    jira_url, project_key, issue_types, statuses, jql_query
                )
                
                # Store in session state for later use
                st.session_state.requirements_df = requirements_df
                st.session_state.requirements_source = "JIRA"
                st.success(f"Successfully fetched {len(requirements_df)} requirements from JIRA")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 2: Upload File
    with tab2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Upload Requirements File")
        
        st.info("Supported formats: Word (.doc, .docx), Excel (.xls, .xlsx), PDF (.pdf), Text (.txt)")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["doc", "docx", "xls", "xlsx", "pdf", "txt"],
            help="Upload a file containing requirements"
        )
        
        if uploaded_file is not None:
            requirements_df = parse_uploaded_file(uploaded_file)
            
            # Store in session state for later use
            st.session_state.requirements_df = requirements_df
            st.session_state.requirements_source = "File"
            st.success(f"Successfully parsed {len(requirements_df)} requirements from {uploaded_file.name}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tab 3: Manual Input
    with tab3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Manual Input")
        
        with st.form("manual_input_form"):
            manual_text = st.text_area(
                "Enter requirements below (one per line or paragraph)",
                height=200,
                help="Enter requirements in free text format"
            )
            
            submitted = st.form_submit_button("Process Manual Input")
            
            if submitted and manual_text:
                # Split by lines and create requirements
                lines = [line.strip() for line in manual_text.split('\n') if line.strip()]
                requirements = []
                
                for i, line in enumerate(lines):
                    requirements.append({
                        "id": f"MANUAL-{i+1:03d}",
                        "title": line[:50] + ("..." if len(line) > 50 else ""),
                        "source": "Manual Input",
                        "status": "Pending Analysis",
                        "description": line,
                        "priority": "Medium"
                    })
                
                requirements_df = pd.DataFrame(requirements)
                
                # Store in session state for later use
                st.session_state.requirements_df = requirements_df
                st.session_state.requirements_source = "Manual"
                st.success(f"Successfully processed {len(requirements_df)} requirements from manual input")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Display processed requirements if available
    if hasattr(st.session_state, 'requirements_df') and not st.session_state.requirements_df.empty:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("Processed Requirements")
        
        requirements_df = st.session_state.requirements_df
        
        # Add a filter
        filter_col1, filter_col2 = st.columns([3, 1])
        with filter_col1:
            filter_text = st.text_input("Filter requirements", "")
        with filter_col2:
            if 'status' in requirements_df.columns:
                filter_status = st.multiselect(
                    "Status",
                    options=requirements_df['status'].unique(),
                    default=requirements_df['status'].unique()
                )
            else:
                filter_status = []
        
        # Apply filters
        filtered_df = requirements_df
        if filter_text:
            mask = filtered_df.apply(lambda row: any(filter_text.lower() in str(val).lower() for val in row), axis=1)
            filtered_df = filtered_df[mask]
        
        if filter_status:
            filtered_df = filtered_df[filtered_df['status'].isin(filter_status)]
        
        # Display requirements table
        st.dataframe(filtered_df, use_container_width=True)
        
        # Actions for selected requirement
        st.subheader("Actions")
        
        selected_requirement = st.selectbox(
            "Select a requirement for actions:",
            options=requirements_df['id'].tolist(),
            format_func=lambda x: f"{x} - {requirements_df[requirements_df['id'] == x]['title'].values[0]}"
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Generate Scenarios/Test Cases", key="btn_generate"):
                scenarios_df = generate_scenarios(selected_requirement)
                st.session_state.scenarios_df = scenarios_df
                st.session_state.current_requirement = selected_requirement
                st.success(f"Generated {len(scenarios_df)} test scenarios for {selected_requirement}")
        
        with col2:
            if st.button("Link to Existing Test Cases", key="btn_link"):
                st.info("This would open the repository browser to link existing test cases")
                # In production, this would trigger a linking workflow
        
        with col3:
            if st.button("View Requirement Details", key="btn_view"):
                # Get the selected requirement details
                req_details = requirements_df[requirements_df['id'] == selected_requirement].iloc[0]
                
                # Create a details expander
                with st.expander(f"Details for {selected_requirement} - {req_details['title']}", expanded=True):
                    for col in req_details.index:
                        st.markdown(f"**{col}**: {req_details[col]}")
        
        # Display generated scenarios if available
        if hasattr(st.session_state, 'scenarios_df') and not st.session_state.scenarios_df.empty:
            if st.session_state.current_requirement == selected_requirement:
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                st.subheader(f"Generated Test Scenarios for {selected_requirement}")
                
                scenarios_df = st.session_state.scenarios_df
                st.dataframe(scenarios_df, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Export to Excel", key="btn_export"):
                        st.success("This would export scenarios to Excel in the predefined format")
                        # In production, this would trigger the export functionality
                
                with col2:
                    if st.button("Generate Detailed Test Cases", key="btn_detailed"):
                        st.session_state.current_page = "TestGeneration"
                        # In production, this would pass the scenarios to the test generation module
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    # For standalone testing
    st.set_page_config(page_title="Requirements - Watsonx IPG Testing", layout="wide")
    
    # Add custom CSS for standalone mode
    st.markdown("""
    <style>
        .main-header { font-size: 2.5rem; color: #0063B2; margin-bottom: 1rem; }
        .sub-header { font-size: 1.5rem; color: #444; margin-bottom: 1rem; }
        .card { padding: 1.5rem; border-radius: 0.5rem; background-color: #f8f9fa; 
                box-shadow: 0 0.15rem 0.5rem rgba(0, 0, 0, 0.1); margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for standalone testing
    if 'requirements_df' not in st.session_state:
        st.session_state.requirements_df = pd.DataFrame()
    if 'requirements_source' not in st.session_state:
        st.session_state.requirements_source = None
    if 'scenarios_df' not in st.session_state:
        st.session_state.scenarios_df = pd.DataFrame()
    if 'current_requirement' not in st.session_state:
        st.session_state.current_requirement = None
    
    render_requirements_ui()