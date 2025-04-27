"""
app.py - Main Entry Point for Watsonx IPG Testing Platform

This module serves as the main application entry point that integrates all UI modules.
It handles navigation, authentication, and overall application structure.
"""
import streamlit as st
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to allow importing from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import UI modules
# These will be developed in separate files
from dashboard import render_dashboard
from requirements_ui import render_requirements_ui
from test_generation_ui import render_test_generation_ui
from repository_ui import render_repository_ui
from execution_ui import render_execution_ui
from analysis_ui import render_analysis_ui
from automation_ui import render_automation_ui
from report_ui import render_report_ui
from settings_ui import render_settings_ui

# Import utilities
try:
    from common.logging.log_utils import setup_logger
    from common.auth.auth_utils import authenticate_user, verify_session
    from common.utils.file_utils import create_temp_directory
except ImportError:
    # For standalone development before integration
    st.error("Common utilities not found. Running in standalone mode with limited functionality.")
    
    def setup_logger():
        return None
        
    def authenticate_user(username, password):
        return username == "admin" and password == "password"
        
    def verify_session():
        return True
        
    def create_temp_directory():
        return "/tmp"

# Initialize logger
logger = setup_logger()

# Set page configuration
st.set_page_config(
    page_title="Watsonx IPG Testing Platform",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for custom styling
def load_css():
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #0063B2;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.5rem;
            color: #444;
            margin-bottom: 1rem;
        }
        .card {
            padding: 1.5rem;
            border-radius: 0.5rem;
            background-color: #f8f9fa;
            box-shadow: 0 0.15rem 0.5rem rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
        }
        .status-success {
            color: green;
            font-weight: bold;
        }
        .status-warning {
            color: orange;
            font-weight: bold;
        }
        .status-error {
            color: red;
            font-weight: bold;
        }
        .sidebar .sidebar-content {
            background-color: #f1f3f6;
        }
        .stButton>button {
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
    if 'temp_dir' not in st.session_state:
        st.session_state.temp_dir = create_temp_directory()
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()

def login_form():
    """Display login form and handle authentication"""
    st.markdown("<h1 class='main-header'>Watsonx IPG Testing Platform</h1>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

def display_header():
    """Display the application header with user info and notifications"""
    col1, col2, col3 = st.columns([6, 3, 1])
    
    with col1:
        st.markdown("<h1 class='main-header'>Watsonx IPG Testing Platform</h1>", unsafe_allow_html=True)
    
    with col2:
        st.text(f"Logged in as: {st.session_state.username}")
        st.text(f"Last activity: {st.session_state.last_activity.strftime('%H:%M:%S')}")
    
    with col3:
        notification_count = len(st.session_state.notifications)
        if st.button(f"🔔 {notification_count}"):
            st.session_state.current_page = "Notifications"
    
    st.divider()

def display_sidebar():
    """Display sidebar navigation menu"""
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50?text=WatsonxIPG", width=200)
        st.divider()
        
        # Main navigation
        st.subheader("Main Navigation")
        if st.button("📊 Dashboard", key="nav_dashboard"):
            st.session_state.current_page = "Dashboard"
        if st.button("📝 Requirements", key="nav_requirements"):
            st.session_state.current_page = "Requirements"
        if st.button("✏️ Test Generation", key="nav_testgen"):
            st.session_state.current_page = "TestGeneration"
        if st.button("📚 Repository", key="nav_repository"):
            st.session_state.current_page = "Repository"
        if st.button("▶️ Execution", key="nav_execution"):
            st.session_state.current_page = "Execution"
        if st.button("🔍 Analysis & Defects", key="nav_analysis"):
            st.session_state.current_page = "Analysis")
        if st.button("💻 Automation", key="nav_automation"):
            st.session_state.current_page = "Automation"
        if st.button("📊 Reports", key="nav_reports"):
            st.session_state.current_page = "Reports"
        
        st.divider()
        
        # User menu
        st.subheader("User Menu")
        if st.button("⚙️ Settings", key="nav_settings"):
            st.session_state.current_page = "Settings"
        if st.button("🚪 Logout", key="nav_logout"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.experimental_rerun()
        
        # System status
        st.divider()
        st.subheader("System Status")
        st.markdown("🟢 JIRA: Connected")
        st.markdown("🟢 SharePoint: Connected")
        st.markdown("🟠 ALM: Limited Access")

def show_notifications():
    """Display notifications page"""
    st.subheader("Notifications")
    if not st.session_state.notifications:
        st.info("No new notifications")
    else:
        for i, notification in enumerate(st.session_state.notifications):
            with st.expander(f"{notification['title']} - {notification['time'].strftime('%H:%M:%S')}"):
                st.write(notification['message'])
                if st.button("Mark as Read", key=f"read_{i}"):
                    st.session_state.notifications.pop(i)
                    st.experimental_rerun()

def route_to_page():
    """Route to the selected page based on session state"""
    current_page = st.session_state.current_page
    
    if current_page == "Dashboard":
        render_dashboard()
    elif current_page == "Requirements":
        render_requirements_ui()
    elif current_page == "TestGeneration":
        render_test_generation_ui()
    elif current_page == "Repository":
        render_repository_ui()
    elif current_page == "Execution":
        render_execution_ui()
    elif current_page == "Analysis":
        render_analysis_ui()
    elif current_page == "Automation":
        render_automation_ui()
    elif current_page == "Reports":
        render_report_ui()
    elif current_page == "Settings":
        render_settings_ui()
    elif current_page == "Notifications":
        show_notifications()
    else:
        st.error(f"Unknown page: {current_page}")
        st.session_state.current_page = "Dashboard"

def main():
    """Main application entry point"""
    # Load custom CSS
    load_css()
    
    # Initialize session state
    initialize_session_state()
    
    # Check if user is authenticated
    if not st.session_state.authenticated:
        login_form()
    else:
        # Update last activity timestamp
        st.session_state.last_activity = datetime.now()
        
        # Display header and sidebar
        display_header()
        display_sidebar()
        
        # Route to the appropriate page
        route_to_page()

# Run the app
if __name__ == "__main__":
    main()