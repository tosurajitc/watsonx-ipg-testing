import streamlit as st
from dashboard import show_dashboard
from requirements_ui import show_requirements
from test_generation_ui import show_test_generation
from repository_ui import show_repository
from execution_ui import show_execution
from analysis_ui import show_analysis
from automation_ui import show_automation
from report_ui import show_report
from settings_ui import show_settings
from state_management import init_session_state
from ui_utils import set_page_config
import mock_services  # Import the mock services


def main():
    # Initialize page configuration
    set_page_config(
        page_title="Watsonx for IPG Testing",
        page_icon="🧪",
        layout="wide"
    )
    
    # Initialize session state with mock data
    init_session_state()
    
    if "first_run" not in st.session_state:
        st.session_state.first_run = True
        st.session_state.current_test_cases = mock_services.get_test_cases()
        st.session_state.repository_loaded = True
        st.session_state.integration_status = mock_services.get_integration_status()
    
    # Application title
    st.title("Watsonx for IPG Testing")
    
    # Show a disclaimer about mock data
    st.warning("⚠️ This is a UI demonstration with mock data. Backend services are not functional.")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Create navigation options
    page = st.sidebar.radio(
        "Select a Module",
        ["Dashboard", "Requirements", "Test Generation", "Test Repository", 
         "Test Execution", "Analysis & Defects", "Code & Automation", 
         "Reporting", "Settings"]
    )
    
    # Display the selected page
    if page == "Dashboard":
        show_dashboard()
    elif page == "Requirements":
        show_requirements()
    elif page == "Test Generation":
        show_test_generation()
    elif page == "Test Repository":
        show_repository()
    elif page == "Test Execution":
        show_execution()
    elif page == "Analysis & Defects":
        show_analysis()
    elif page == "Code & Automation":
        show_automation()
    elif page == "Reporting":
        show_report()
    elif page == "Settings":
        show_settings()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("© 2025 Watsonx for IPG Testing")


if __name__ == "__main__":
    main()