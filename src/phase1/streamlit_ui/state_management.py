import streamlit as st
from typing import Any, Dict, Optional, List, Union
import uuid
import json
from datetime import datetime, timedelta



#################### Testing blocl



################### Testing block endss here

class SessionStateManager:
    """
    Comprehensive session state management for the testing platform
    """
    
    @staticmethod
    def initialize_session_state():
        """
        Initialize default session state variables if not already set
        """
        # Initialize core application state
        default_states = {
            'user': {
                'is_authenticated': False,
                'username': None,
                'role': None,
                'last_login': None
            },
            'navigation': {
                'current_module': None,
                'previous_module': None
            },
            'active_projects': [],
            'recent_activities': [],
            'selected_items': {
                'test_cases': [],
                'defects': [],
                'requirements': []
            },
            'temporary_data': {},
            'preferences': {
                'theme': 'light',
                'notifications_enabled': True
            }
        }
        
        # Initialize each state variable if not exists
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def login(username: str, role: str):
        """
        Authenticate user and update session state
        
        Args:
            username (str): Username of the logged-in user
            role (str): User role
        """
        st.session_state['user'] = {
            'is_authenticated': True,
            'username': username,
            'role': role,
            'last_login': datetime.now()
        }

    @staticmethod
    def logout():
        """
        Clear user authentication and reset relevant session state
        """
        # Reset user state
        st.session_state['user'] = {
            'is_authenticated': False,
            'username': None,
            'role': None,
            'last_login': None
        }
        
        # Clear selected items and temporary data
        st.session_state['selected_items'] = {
            'test_cases': [],
            'defects': [],
            'requirements': []
        }
        st.session_state['temporary_data'] = {}

    @staticmethod
    def is_authenticated() -> bool:
        """
        Check if user is currently authenticated
        
        Returns:
            bool: Authentication status
        """
        return st.session_state['user']['is_authenticated']

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """
        Get current user information
        
        Returns:
            Optional[Dict[str, Any]]: User information or None
        """
        return st.session_state['user'] if SessionStateManager.is_authenticated() else None

    @staticmethod
    def update_navigation(current_module: str):
        """
        Update navigation state
        
        Args:
            current_module (str): Current active module
        """
        # Store previous module before updating
        if st.session_state['navigation']['current_module']:
            st.session_state['navigation']['previous_module'] = \
                st.session_state['navigation']['current_module']
        
        # Update current module
        st.session_state['navigation']['current_module'] = current_module

    @staticmethod
    def select_item(category: str, item_id: Union[str, int]):
        """
        Select an item and add to selected items
        
        Args:
            category (str): Category of item (test_cases, defects, requirements)
            item_id (Union[str, int]): ID of the selected item
        """
        # Ensure category exists
        if category not in st.session_state['selected_items']:
            st.session_state['selected_items'][category] = []
        
        # Add item if not already selected
        if item_id not in st.session_state['selected_items'][category]:
            st.session_state['selected_items'][category].append(item_id)

    @staticmethod
    def deselect_item(category: str, item_id: Union[str, int]):
        """
        Remove an item from selected items
        
        Args:
            category (str): Category of item
            item_id (Union[str, int]): ID of the item to deselect
        """
        if (category in st.session_state['selected_items'] and 
            item_id in st.session_state['selected_items'][category]):
            st.session_state['selected_items'][category].remove(item_id)

    @staticmethod
    def clear_selected_items(category: Optional[str] = None):
        """
        Clear selected items
        
        Args:
            category (Optional[str]): Specific category to clear. If None, clear all.
        """
        if category:
            st.session_state['selected_items'][category] = []
        else:
            st.session_state['selected_items'] = {
                'test_cases': [],
                'defects': [],
                'requirements': []
            }

    @staticmethod
    def store_temporary_data(key: str, value: Any, expires_in: Optional[int] = None):
        """
        Store temporary data with optional expiration
        
        Args:
            key (str): Unique key for the data
            value (Any): Data to store
            expires_in (Optional[int]): Expiration time in seconds
        """
        # Generate a unique identifier
        data_id = str(uuid.uuid4())
        
        # Store data with optional expiration
        st.session_state['temporary_data'][key] = {
            'id': data_id,
            'value': value,
            'expires_at': (datetime.now() + timedelta(seconds=expires_in)) if expires_in else None
        }

    @staticmethod
    def get_temporary_data(key: str) -> Optional[Any]:
        """
        Retrieve temporary data
        
        Args:
            key (str): Key of the data to retrieve
        
        Returns:
            Optional[Any]: Retrieved data or None
        """
        # Check if key exists and is not expired
        if key in st.session_state['temporary_data']:
            temp_data = st.session_state['temporary_data'][key]
            
            # Check expiration
            if temp_data['expires_at'] is None or datetime.now() < temp_data['expires_at']:
                return temp_data['value']
            else:
                # Remove expired data
                del st.session_state['temporary_data'][key]
        
        return None

    @staticmethod
    def delete_temporary_data(key: str):
        """
        Delete specific temporary data
        
        Args:
            key (str): Key of the data to delete
        """
        if key in st.session_state['temporary_data']:
            del st.session_state['temporary_data'][key]

    @staticmethod
    def cleanup_expired_temporary_data():
        """
        Remove all expired temporary data
        """
        current_time = datetime.now()
        keys_to_remove = [
            key for key, data in st.session_state['temporary_data'].items()
            if data['expires_at'] and current_time >= data['expires_at']
        ]
        
        for key in keys_to_remove:
            del st.session_state['temporary_data'][key]

    @staticmethod
    def add_recent_activity(activity: Dict[str, Any]):
        """
        Add an activity to recent activities
        
        Args:
            activity (Dict[str, Any]): Activity details
        """
        # Ensure activity has required fields
        activity.setdefault('timestamp', datetime.now())
        activity.setdefault('id', str(uuid.uuid4()))
        
        # Add to recent activities
        st.session_state['recent_activities'].insert(0, activity)
        
        # Limit recent activities to last 10
        st.session_state['recent_activities'] = \
            st.session_state['recent_activities'][:10]

def main():
    """
    Demonstrate session state management
    """
    st.title("Session State Management Demo")
    
    # Initialize session state
    SessionStateManager.initialize_session_state()
    
    # Login demonstration
    st.header("Authentication Demo")
    if not SessionStateManager.is_authenticated():
        username = st.text_input("Username")
        role = st.selectbox("Role", ["Tester", "Test Lead", "Administrator"])
        
        if st.button("Login"):
            SessionStateManager.login(username, role)
            st.success(f"Logged in as {username} with role {role}")
    else:
        user = SessionStateManager.get_current_user()
        st.write(f"Logged in as: {user['username']} (Role: {user['role']})")
        
        if st.button("Logout"):
            SessionStateManager.logout()
            st.info("Logged out successfully")
    
    # Temporary data demonstration
    st.header("Temporary Data Demo")
    temp_key = st.text_input("Temporary Data Key")
    temp_value = st.text_input("Temporary Data Value")
    
    if st.button("Store Temporary Data"):
        SessionStateManager.store_temporary_data(temp_key, temp_value, expires_in=60)
        st.success(f"Stored data for key: {temp_key}")
    
    if st.button("Retrieve Temporary Data"):
        retrieved_value = SessionStateManager.get_temporary_data(temp_key)
        if retrieved_value:
            st.write(f"Retrieved value: {retrieved_value}")
        else:
            st.warning("No data found or data expired")
    
    # Recent activities demonstration
    st.header("Recent Activities")
    if st.button("Add Sample Activity"):
        SessionStateManager.add_recent_activity({
            'type': 'test_execution',
            'description': 'Executed test case TC-001'
        })
    
    st.write("Recent Activities:", 
             st.session_state['recent_activities'])

if __name__ == "__main__":
    main()