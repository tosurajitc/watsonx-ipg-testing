#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Rule Engine Module for the Watsonx IPG Testing platform.

This module provides rule-based logic for various system operations,
such as test case owner assignment, defect routing, and automation decisions.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union

# Setup logger
logger = logging.getLogger(__name__)

class AssignmentRules:
    """
    Class to manage and apply assignment rules for test cases, defects, etc.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the AssignmentRules with optional configuration.
        
        Args:
            config (Dict[str, Any], optional): Configuration for rules.
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Load rules from configuration or use defaults
        self.rules = self.config.get("rules", self._get_default_rules())
        
        self.logger.info("AssignmentRules initialized")
    
    def _get_default_rules(self) -> Dict[str, Any]:
        """
        Get default assignment rules.
        
        Returns:
            Dict[str, Any]: Default rules configuration.
        """
        # Default rules for test case ownership
        return {
            "test_case_ownership": {
                "default_owner": "unassigned",
                "module_owners": {
                    "Authentication": "auth_team_lead",
                    "Payments": "payments_team_lead",
                    "Reporting": "reporting_team_lead",
                    "Admin": "admin_team_lead",
                    "User Management": "user_mgmt_team_lead"
                },
                "priority_owners": {
                    "high": "senior_qa_engineer",
                    "critical": "qa_manager"
                }
            },
            "defect_assignment": {
                "default_assignee": "triage_engineer",
                "component_owners": {
                    "Frontend": "frontend_dev_lead",
                    "Backend": "backend_dev_lead",
                    "Database": "db_engineer",
                    "API": "api_engineer"
                },
                "severity_routing": {
                    "critical": "dev_manager",
                    "high": "senior_developer"
                }
            }
        }
    
    def get_owner_for_test_case(self, module: str, priority: str = "medium") -> str:
        """
        Determine the owner for a test case based on module and priority.
        
        Args:
            module (str): The module the test case belongs to.
            priority (str, optional): The test case priority.
            
        Returns:
            str: The determined owner.
        """
        # Get test case ownership rules
        ownership_rules = self.rules.get("test_case_ownership", {})
        
        # Check if there's a priority-based owner
        if priority.lower() in ownership_rules.get("priority_owners", {}):
            return ownership_rules["priority_owners"][priority.lower()]
        
        # Check if there's a module-based owner
        if module in ownership_rules.get("module_owners", {}):
            return ownership_rules["module_owners"][module]
        
        # Fall back to default owner
        return ownership_rules.get("default_owner", "unassigned")
    
    def get_assignee_for_defect(self, component: str, severity: str = "medium") -> str:
        """
        Determine the assignee for a defect based on component and severity.
        
        Args:
            component (str): The component the defect is in.
            severity (str, optional): The defect severity.
            
        Returns:
            str: The determined assignee.
        """
        # Get defect assignment rules
        assignment_rules = self.rules.get("defect_assignment", {})
        
        # Check if there's a severity-based assignee
        if severity.lower() in assignment_rules.get("severity_routing", {}):
            return assignment_rules["severity_routing"][severity.lower()]
        
        # Check if there's a component-based assignee
        if component in assignment_rules.get("component_owners", {}):
            return assignment_rules["component_owners"][component]
        
        # Fall back to default assignee
        return assignment_rules.get("default_assignee", "triage_engineer")
    
    def apply_rules(self, entity_type: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rules to an entity (test case, defect, etc.) and update it accordingly.
        
        Args:
            entity_type (str): Type of entity ("test_case", "defect", etc.).
            entity_data (Dict[str, Any]): Entity data.
            
        Returns:
            Dict[str, Any]: Updated entity data.
        """
        updated_data = entity_data.copy()
        
        if entity_type == "test_case":
            # Apply test case rules
            module = entity_data.get("module", "Unknown")
            priority = entity_data.get("priority", "medium")
            
            # Assign owner
            if "owner" not in entity_data or not entity_data["owner"]:
                owner = self.get_owner_for_test_case(module, priority)
                updated_data["owner"] = owner
                self.logger.info(f"Assigned owner '{owner}' to test case based on rules")
        
        elif entity_type == "defect":
            # Apply defect rules
            component = entity_data.get("component", "Unknown")
            severity = entity_data.get("severity", "medium")
            
            # Assign assignee
            if "assignee" not in entity_data or not entity_data["assignee"]:
                assignee = self.get_assignee_for_defect(component, severity)
                updated_data["assignee"] = assignee
                self.logger.info(f"Assigned '{assignee}' to defect based on rules")
        
        # Return the updated data
        return updated_data


# Get singleton instance of assignment rules
_assignment_rules_instance = None

def get_assignment_rules() -> AssignmentRules:
    """
    Get a singleton instance of the AssignmentRules.
    
    Returns:
        AssignmentRules: The assignment rules instance.
    """
    global _assignment_rules_instance
    
    if _assignment_rules_instance is None:
        _assignment_rules_instance = AssignmentRules()
    
    return _assignment_rules_instance


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Get assignment rules
    rules = get_assignment_rules()
    
    # Example test case
    test_case = {
        "module": "Payments",
        "priority": "high"
    }
    
    # Apply rules
    updated_test_case = rules.apply_rules("test_case", test_case)
    
    print(f"Original test case: {test_case}")
    print(f"Updated test case: {updated_test_case}")