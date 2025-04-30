import streamlit as st
import pandas as pd
import yaml
from typing import Dict, List, Any
import base64
import json



#################### Testing blocl



################### Testing block endss here

class SettingsUI:
    def __init__(self):
        """
        Initialize the Settings Module UI
        """
        # Load existing configurations
        self.connections_config = self._load_config('connections')
        self.rule_config = self._load_config('rules')
        self.automation_config = self._load_config('automation')
        self.notification_config = self._load_config('notifications')
        self.user_config = self._load_config('users')

    def _load_config(self, config_type: str) -> Dict:
        """
        Load configuration from a YAML file
        
        Args:
            config_type (str): Type of configuration to load
        
        Returns:
            Dict: Configuration dictionary
        """
        # Placeholder for actual configuration loading
        default_configs = {
            'connections': {
                'jira': {
                    'url': '',
                    'api_token': '',
                    'project_key': ''
                },
                'alm': {
                    'url': '',
                    'username': '',
                    'password': ''
                },
                'sharepoint': {
                    'url': '',
                    'client_id': '',
                    'tenant_id': ''
                }
            },
            'rules': {
                'test_case_owner': [
                    {
                        'module': 'Login',
                        'owner': 'QA Lead',
                        'criteria': 'Authentication module'
                    }
                ],
                'defect_assignment': [
                    {
                        'severity': 'High',
                        'component': 'Authentication',
                        'assignee': 'Senior Developer'
                    }
                ]
            },
            'automation': {
                'controller_file_path': '',
                'driver_script_path': '',
                'uft_library_path': ''
            },
            'notifications': {
                'email_recipients': [],
                'slack_webhooks': [],
                'events': {
                    'test_execution_complete': True,
                    'defect_created': True,
                    'test_case_modified': False
                }
            },
            'users': {
                'roles': [
                    {
                        'username': 'admin',
                        'role': 'Administrator',
                        'email': 'admin@company.com'
                    }
                ]
            }
        }
        return default_configs.get(config_type, {})

    def _save_config(self, config_type: str, config_data: Dict):
        """
        Save configuration to a file
        
        Args:
            config_type (str): Type of configuration to save
            config_data (Dict): Configuration data to save
        """
        # Placeholder for actual configuration saving
        st.success(f"{config_type.capitalize()} configuration saved successfully!")

    def render_connections_section(self):
        """
        Render Connections configuration section
        """
        st.subheader("Connections Configuration")
        
        # Tabs for different connection types
        tabs = st.tabs(["JIRA", "ALM", "SharePoint"])
        
        # JIRA Connection
        with tabs[0]:
            st.markdown("### JIRA Connection")
            jira_config = self.connections_config.get('jira', {})
            
            jira_url = st.text_input(
                "JIRA URL", 
                value=jira_config.get('url', ''),
                key="jira_url"
            )
            jira_api_token = st.text_input(
                "API Token", 
                value=jira_config.get('api_token', ''),
                type="password",
                key="jira_api_token"
            )
            jira_project_key = st.text_input(
                "Project Key", 
                value=jira_config.get('project_key', ''),
                key="jira_project_key"
            )
            
            if st.button("Test JIRA Connection"):
                # Placeholder for connection testing
                st.success("JIRA Connection Test Successful!")
        
        # ALM Connection
        with tabs[1]:
            st.markdown("### ALM Connection")
            alm_config = self.connections_config.get('alm', {})
            
            alm_url = st.text_input(
                "ALM URL", 
                value=alm_config.get('url', ''),
                key="alm_url"
            )
            alm_username = st.text_input(
                "Username", 
                value=alm_config.get('username', ''),
                key="alm_username"
            )
            alm_password = st.text_input(
                "Password", 
                value=alm_config.get('password', ''),
                type="password",
                key="alm_password"
            )
            
            if st.button("Test ALM Connection"):
                # Placeholder for connection testing
                st.success("ALM Connection Test Successful!")
        
        # SharePoint Connection
        with tabs[2]:
            st.markdown("### SharePoint Connection")
            sharepoint_config = self.connections_config.get('sharepoint', {})
            
            sharepoint_url = st.text_input(
                "SharePoint URL", 
                value=sharepoint_config.get('url', ''),
                key="sharepoint_url"
            )
            sharepoint_client_id = st.text_input(
                "Client ID", 
                value=sharepoint_config.get('client_id', ''),
                key="sharepoint_client_id"
            )
            sharepoint_tenant_id = st.text_input(
                "Tenant ID", 
                value=sharepoint_config.get('tenant_id', ''),
                key="sharepoint_tenant_id"
            )
            
            if st.button("Test SharePoint Connection"):
                # Placeholder for connection testing
                st.success("SharePoint Connection Test Successful!")
        
        # Save connections configuration
        if st.button("Save Connections Configuration"):
            updated_config = {
                'jira': {
                    'url': jira_url,
                    'api_token': jira_api_token,
                    'project_key': jira_project_key
                },
                'alm': {
                    'url': alm_url,
                    'username': alm_username,
                    'password': alm_password
                },
                'sharepoint': {
                    'url': sharepoint_url,
                    'client_id': sharepoint_client_id,
                    'tenant_id': sharepoint_tenant_id
                }
            }
            self._save_config('connections', updated_config)

    def render_rule_engine_section(self):
        """
        Render Rule Engine configuration section
        """
        st.subheader("Rule Engine Configuration")
        
        # Tabs for different rule types
        tabs = st.tabs(["Test Case Owner Rules", "Defect Assignment Rules"])
        
        # Test Case Owner Rules
        with tabs[0]:
            st.markdown("### Test Case Owner Assignment Rules")
            
            # Display existing rules
            df = pd.DataFrame(self.rule_config.get('test_case_owner', []))
            st.dataframe(df, use_container_width=True)
            
            # Add new rule
            st.markdown("#### Add New Test Case Owner Rule")
            new_module = st.text_input("Module/Component", key="test_case_owner_module")
            new_owner = st.text_input("Assigned Owner", key="test_case_owner_name")
            new_criteria = st.text_area("Assignment Criteria", key="test_case_owner_criteria")
            
            if st.button("Add Test Case Owner Rule"):
                if new_module and new_owner:
                    new_rule = {
                        'module': new_module,
                        'owner': new_owner,
                        'criteria': new_criteria
                    }
                    self.rule_config['test_case_owner'].append(new_rule)
                    self._save_config('rules', self.rule_config)
                    st.experimental_rerun()
                else:
                    st.warning("Module and Owner are required")
        
        # Defect Assignment Rules
        with tabs[1]:
            st.markdown("### Defect Assignment Rules")
            
            # Display existing rules
            df = pd.DataFrame(self.rule_config.get('defect_assignment', []))
            st.dataframe(df, use_container_width=True)
            
            # Add new rule
            st.markdown("#### Add New Defect Assignment Rule")
            severity_options = ["Low", "Medium", "High", "Critical"]
            new_severity = st.selectbox(
                "Defect Severity", 
                options=severity_options,
                key="defect_severity"
            )
            new_component = st.text_input("Component", key="defect_component")
            new_assignee = st.text_input("Assigned To", key="defect_assignee")
            
            if st.button("Add Defect Assignment Rule"):
                if new_severity and new_component and new_assignee:
                    new_rule = {
                        'severity': new_severity,
                        'component': new_component,
                        'assignee': new_assignee
                    }
                    self.rule_config['defect_assignment'].append(new_rule)
                    self._save_config('rules', self.rule_config)
                    st.experimental_rerun()
                else:
                    st.warning("All fields are required")

    def render_automation_settings(self):
        """
        Render Automation Settings configuration section
        """
        st.subheader("Automation Settings")
        
        # Automation paths configuration
        st.markdown("### Automation Paths")
        
        # Load existing paths
        auto_config = self.automation_config
        
        # Controller File Path
        controller_file_path = st.text_input(
            "Controller File Path", 
            value=auto_config.get('controller_file_path', ''),
            key="controller_file_path"
        )
        
        # Driver Script Path
        driver_script_path = st.text_input(
            "Driver Script Path", 
            value=auto_config.get('driver_script_path', ''),
            key="driver_script_path"
        )
        
        # UFT Library Path
        uft_library_path = st.text_input(
            "UFT Library Path", 
            value=auto_config.get('uft_library_path', ''),
            key="uft_library_path"
        )
        
        # Save Automation Settings
        if st.button("Save Automation Settings"):
            updated_config = {
                'controller_file_path': controller_file_path,
                'driver_script_path': driver_script_path,
                'uft_library_path': uft_library_path
            }
            self._save_config('automation', updated_config)

    def render_notification_settings(self):
        """
        Render Notification Settings configuration section
        """
        st.subheader("Notification Settings")
        
        # Notification configuration
        notif_config = self.notification_config
        
        # Email Recipients
        st.markdown("### Email Recipients")
        email_recipients = st.text_area(
            "Add Email Recipients (one per line)", 
            value="\n".join(notif_config.get('email_recipients', [])),
            key="email_recipients"
        )
        
        # Slack Webhooks
        st.markdown("### Slack Webhooks")
        slack_webhooks = st.text_area(
            "Add Slack Webhook URLs (one per line)", 
            value="\n".join(notif_config.get('slack_webhooks', [])),
            key="slack_webhooks"
        )
        
        # Event Notifications
        st.markdown("### Event Notification Preferences")
        events_config = notif_config.get('events', {})
        
        test_execution_complete = st.checkbox(
            "Notify on Test Execution Complete", 
            value=events_config.get('test_execution_complete', True),
            key="notify_test_execution"
        )
        
        defect_created = st.checkbox(
            "Notify on Defect Creation", 
            value=events_config.get('defect_created', True),
            key="notify_defect"
        )
        
        test_case_modified = st.checkbox(
            "Notify on Test Case Modification", 
            value=events_config.get('test_case_modified', False),
            key="notify_test_case"
        )
        
        # Save Notification Settings
        if st.button("Save Notification Settings"):
            updated_config = {
                'email_recipients': email_recipients.split('\n'),
                'slack_webhooks': slack_webhooks.split('\n'),
                'events': {
                    'test_execution_complete': test_execution_complete,
                    'defect_created': defect_created,
                    'test_case_modified': test_case_modified
                }
            }
            self._save_config('notifications', updated_config)

    def render_user_management(self):
        """
        Render User Management configuration section
        """
        st.subheader("User Management")
        
        # Display existing users
        st.markdown("### Existing Users")
        df = pd.DataFrame(self.user_config.get('roles', []))
        st.dataframe(df, use_container_width=True)
        
        # Add New User
        st.markdown("### Add New User")
        
        # User details input
        new_username = st.text_input("Username", key="new_username")
        new_email = st.text_input("Email", key="new_email")
        
        # Role selection
        role_options = ["Administrator", "Test Lead", "Tester", "Developer", "Viewer"]
        new_role = st.selectbox(
            "Role", 
            options=role_options,
            key="new_user_role"
        )
        
        # Add user button
        if st.button("Add User"):
            if new_username and new_email:
                new_user = {
                    'username': new_username,
                    'email': new_email,
                    'role': new_role
                }
                
                # Add to user configuration
                if 'roles' not in self.user_config:
                    self.user_config['roles'] = []
                
                self.user_config['roles'].append(new_user)
                self._save_config('users', self.user_config)
                st.experimental_rerun()
            else:
                st.warning("Username and Email are required")

    def render(self):
        """
        Render the entire Settings Module UI
        """
        st.title("Settings Module")
        
        # Create tabs for different settings
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Connections", 
            "Rule Engine", 
            "Automation Settings", 
            "Notifications", 
            "User Management"
        ])
        
        with tab1:
            self.render_connections_section()
        
        with tab2:
            self.render_rule_engine_section()
        
        with tab3:
            self.render_automation_settings()
        
        with tab4:
            self.render_notification_settings()
        
        with tab5:
            self.render_user_management()

def main():
    """
    Main function to run the Settings Module
    """
    settings_ui = SettingsUI()
    settings_ui.render()

if __name__ == "__main__":
    main()