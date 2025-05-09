#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Case Generator Module for the Watsonx IPG Testing platform.

This module generates detailed test cases from test scenarios provided by the LLM Test Scenario Generator Module.
It uses predefined Excel templates to structure the test cases according to organizational standards.
"""

import os
import pandas as pd
import logging
from typing import Dict, List, Any, Tuple, Optional, Union
import json
import uuid
from datetime import datetime

# Import from src.common
from src.common.utils.file_utils import read_file, write_file
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    TemplateNotFoundError, 
    ScenarioValidationError, 
    TestCaseGenerationError,
    LLMConnectionError,
    LLMResponseError    
)

# Import from other modules in phase1
from src.phase1.llm_test_scenario_generator.scenario_validator import ScenarioValidator
from src.phase1.test_case_manager.testcase_refiner import LLMHelper

# Setup logger
logger = logging.getLogger(__name__)

class TestCaseGenerator:
    """
    Class to generate detailed test cases from test scenarios using predefined templates.
    """
    
    # Define standard columns for test cases
    TEST_CASE_COLUMNS = [
        "SUBJECT", "TEST CASE", "TEST CASE NUMBER", "STEP NO", 
        "TEST STEP DESCRIPTION", "DATA", "REFERENCE VALUES", "VALUES", 
        "EXPECTED RESULT", "TRANS CODE", "TEST USER ID/ROLE", "STATUS", "TYPE"
    ]
    
    def __init__(self, template_path: str = None):
        """
        Initialize the TestCaseGenerator with a template path.
        
        Args:
            template_path (str, optional): Path to the Excel template file. If None, uses default template.
        """
        self.template_path = template_path or os.path.join(
            os.path.dirname(__file__), "../../../templates/report/test_case_template.xlsx"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"TestCaseGenerator initialized with template: {self.template_path}")
        
        # Validate template exists
        if not os.path.exists(self.template_path):
            self.logger.error(f"Template not found at {self.template_path}")
            raise TemplateNotFoundError(f"Template not found at {self.template_path}")
    
    def load_template(self) -> pd.DataFrame:
        """
        Load the Excel template for test cases.
        
        Returns:
            pd.DataFrame: DataFrame representing the template.
        """
        try:
            df = pd.read_excel(self.template_path)
            self.logger.debug(f"Template loaded successfully with columns: {df.columns.tolist()}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to load template: {str(e)}")
            raise TemplateNotFoundError(f"Failed to load template: {str(e)}")
    
    def validate_test_case_structure(self, test_case_df: pd.DataFrame) -> bool:
        """
        Validate that the generated test case DataFrame has the required structure.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame to validate.
            
        Returns:
            bool: True if valid, False otherwise.
            
        Raises:
            TestCaseGenerationError: If validation fails.
        """
        # Check if all required columns are present
        missing_columns = [col for col in self.TEST_CASE_COLUMNS if col not in test_case_df.columns]
        
        if missing_columns:
            error_msg = f"Generated test case is missing required columns: {missing_columns}"
            self.logger.error(error_msg)
            raise TestCaseGenerationError(error_msg)
        
        # Ensure there's at least one row of data
        if len(test_case_df) == 0:
            error_msg = "Generated test case has no data rows."
            self.logger.error(error_msg)
            raise TestCaseGenerationError(error_msg)
            
        return True
    
    def generate_test_case_from_scenario(self, scenario: Dict[str, Any]) -> pd.DataFrame:
        """
        Generate a detailed test case from a test scenario.
        
        Args:
            scenario (Dict[str, Any]): The test scenario data.
            
        Returns:
            pd.DataFrame: The generated test case as a DataFrame.
            
        Raises:
            ScenarioValidationError: If the scenario is invalid.
            TestCaseGenerationError: If test case generation fails.
        """
        # Validate the scenario first
        try:
            validator = ScenarioValidator()
            validation_result = validator.validate_scenario(scenario)
            if not validation_result['valid']:
                raise Exception(f"Invalid scenario: {validation_result['issues']}")
        except Exception as e:
            self.logger.error(f"Invalid scenario format: {str(e)}")
            raise ScenarioValidationError(f"Invalid scenario format: {str(e)}")
        
        try:
            # Load template
            template_df = self.load_template()
            
            # Extract relevant information from scenario
            subject = scenario.get('subject', 'Unknown')
            scenario_name = scenario.get('name', 'Unknown')
            scenario_steps = scenario.get('steps', [])
            
            # Generate a unique test case number if not provided
            test_case_number = scenario.get('id', f"TC-{uuid.uuid4().hex[:8].upper()}")
            
            # Create test case rows
            test_case_data = []
            
            for step_idx, step in enumerate(scenario_steps, 1):
                # Create a row for each step
                row = {
                    "SUBJECT": subject,
                    "TEST CASE": scenario_name,
                    "TEST CASE NUMBER": test_case_number,
                    "STEP NO": step_idx,
                    "TEST STEP DESCRIPTION": step.get('description', ''),
                    "DATA": step.get('data', ''),
                    "REFERENCE VALUES": step.get('reference_values', ''),
                    "VALUES": step.get('values', ''),
                    "EXPECTED RESULT": step.get('expected_result', ''),
                    "TRANS CODE": step.get('trans_code', ''),
                    "TEST USER ID/ROLE": step.get('test_user', ''),
                    "STATUS": "Not Executed",  # Default status
                    "TYPE": scenario.get('type', 'Functional')  # Default type
                }
                test_case_data.append(row)
            
            # Create DataFrame
            test_case_df = pd.DataFrame(test_case_data)
            
            # Validate the generated test case
            self.validate_test_case_structure(test_case_df)
            
            self.logger.info(f"Successfully generated test case with {len(test_case_data)} steps")
            return test_case_df
            
        except Exception as e:
            self.logger.error(f"Failed to generate test case: {str(e)}")
            raise TestCaseGenerationError(f"Failed to generate test case: {str(e)}")
    



    # Add this new method to the TestCaseGenerator class
    def generate_test_case_from_prompt(self, prompt: str) -> pd.DataFrame:
        """
        Generate a test case from a simple text prompt using LLM.
        
        Args:
            prompt (str): Simple text prompt like "Generate login test cases for Admin user"
            
        Returns:
            pd.DataFrame: The generated test case as a DataFrame.
            
        Raises:
            TestCaseGenerationError: If test case generation fails.
        """
        try:
            self.logger.info(f"Generating test case from prompt: '{prompt}'")
            
            # Use LLM helper to get test case structure
            llm_helper = LLMHelper()
            test_case_data = llm_helper.generate_test_case_structure(prompt)
            
            # Extract steps from the structure
            steps = test_case_data.get("steps", [])
            if not steps:
                raise TestCaseGenerationError("The LLM did not generate any test steps. Cannot create a test case without steps.")
            
            # Create test case rows
            test_case_rows = []
            
            # Add each step as a row
            for step in steps:
                row = {
                    "SUBJECT": test_case_data.get("SUBJECT", ""),
                    "TEST CASE": test_case_data.get("TEST CASE", ""),
                    "TEST CASE NUMBER": test_case_data.get("TEST CASE NUMBER", ""),
                    "STEP NO": step.get("STEP NO", ""),
                    "TEST STEP DESCRIPTION": step.get("TEST STEP DESCRIPTION", ""),
                    "DATA": step.get("DATA", ""),
                    "REFERENCE VALUES": step.get("REFERENCE VALUES", ""),
                    "VALUES": step.get("VALUES", ""),
                    "EXPECTED RESULT": step.get("EXPECTED RESULT", ""),
                    "TRANS CODE": step.get("TRANS CODE", ""),
                    "TEST USER ID/ROLE": step.get("TEST USER ID/ROLE", ""),
                    "STATUS": step.get("STATUS", ""),
                    "TYPE": test_case_data.get("TYPE", "")
                }
                test_case_rows.append(row)
            
            # Create DataFrame
            test_case_df = pd.DataFrame(test_case_rows)
            
            # Validate the generated test case
            self.validate_test_case_structure(test_case_df)
            
            self.logger.info(f"Successfully generated test case with {len(test_case_rows)} steps from prompt")
            return test_case_df
            
        except LLMConnectionError as e:
            self.logger.error(f"LLM connection error: {str(e)}")
            raise TestCaseGenerationError(f"Failed to connect to LLM service: {str(e)}")
            
        except LLMResponseError as e:
            self.logger.error(f"LLM response error: {str(e)}")
            raise TestCaseGenerationError(f"The LLM failed to generate a valid test case: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate test case from prompt: {str(e)}")
            raise TestCaseGenerationError(f"Failed to generate test case from prompt: {str(e)}")
    


    def generate_test_cases_batch(self, scenarios: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
        """
        Generate multiple test cases from a list of scenarios.
        
        Args:
            scenarios (List[Dict[str, Any]]): List of test scenarios.
            
        Returns:
            Dict[str, pd.DataFrame]: Dictionary mapping scenario IDs to test case DataFrames.
        """
        test_cases = {}
        
        for scenario in scenarios:
            try:
                scenario_id = scenario.get('id', str(uuid.uuid4()))
                test_case_df = self.generate_test_case_from_scenario(scenario)
                test_cases[scenario_id] = test_case_df
            except Exception as e:
                self.logger.warning(f"Failed to generate test case for scenario {scenario.get('id', 'unknown')}: {str(e)}")
                # Continue with other scenarios
        
        self.logger.info(f"Generated {len(test_cases)} test cases from {len(scenarios)} scenarios")
        return test_cases
    
    def save_test_case_to_excel(self, test_case_df: pd.DataFrame, output_path: str) -> str:
        """
        Save the generated test case to an Excel file.
        
        Args:
            test_case_df (pd.DataFrame): Test case DataFrame.
            output_path (str): Path to save the Excel file.
            
        Returns:
            str: Path where the file was saved.
            
        Raises:
            Exception: If saving fails.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save to Excel
            test_case_df.to_excel(output_path, index=False)
            
            self.logger.info(f"Test case saved to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to save test case to Excel: {str(e)}")
            raise Exception(f"Failed to save test case to Excel: {str(e)}")
    
    def process_scenario_file(self, scenario_file_path: str, output_dir: str = None) -> List[str]:
        """
        Process a file containing test scenarios and generate test cases.
        
        Args:
            scenario_file_path (str): Path to the scenario file (JSON or Excel).
            output_dir (str, optional): Directory to save the generated test cases.
                                     If None, saves in the same directory as the scenario file.
            
        Returns:
            List[str]: Paths to the generated test case files.
            
        Raises:
            FileNotFoundError: If the scenario file doesn't exist.
            ValueError: If the file format is unsupported.
        """
        if not os.path.exists(scenario_file_path):
            raise FileNotFoundError(f"Scenario file not found: {scenario_file_path}")
        
        # Determine file format
        file_ext = os.path.splitext(scenario_file_path)[1].lower()
        
        # Load scenarios based on file format
        scenarios = []
        
        if file_ext == '.json':
            with open(scenario_file_path, 'r') as f:
                data = json.load(f)
                
                # Handle both single scenario and list of scenarios
                if isinstance(data, list):
                    scenarios = data
                else:
                    scenarios = [data]
        
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(scenario_file_path)
            
            # Convert DataFrame to list of dictionaries
            scenarios = df.to_dict('records')
        
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Set output directory
        if output_dir is None:
            output_dir = os.path.dirname(scenario_file_path)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate test cases
        output_files = []
        test_cases = self.generate_test_cases_batch(scenarios)
        
        for scenario_id, test_case_df in test_cases.items():
            # Generate output filename
            output_filename = f"TestCase_{scenario_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save test case
            self.save_test_case_to_excel(test_case_df, output_path)
            output_files.append(output_path)
        
        return output_files

# If running as a script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test cases from scenarios")
    parser.add_argument("--scenario_file", required=True, help="Path to the scenario file")
    parser.add_argument("--template", help="Path to the template file (optional)")
    parser.add_argument("--output_dir", help="Directory to save the generated test cases (optional)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create generator
    generator = TestCaseGenerator(template_path=args.template)
    
    # Process scenario file
    output_files = generator.process_scenario_file(args.scenario_file, args.output_dir)
    
    print(f"Generated {len(output_files)} test case files:")
    for output_file in output_files:
        print(f" - {output_file}")