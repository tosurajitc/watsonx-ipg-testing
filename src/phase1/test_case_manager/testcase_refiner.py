#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Case Refiner Module for the Watsonx IPG Testing platform.

This module analyzes existing test cases to suggest improvements, additional details,
variations, and other refinements to enhance the robustness of the test coverage.
"""

import os
import pandas as pd
import logging
import json
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import re

# Import from src.common
from src.common.utils.file_utils import read_file, write_file
from src.common.logging.log_utils import setup_logger
from src.common.exceptions.custom_exceptions import (
    TestCaseNotFoundError,
    TestCaseFormatError,
    RefinementRuleError
)

# Setup logger
logger = logging.getLogger(__name__)

class TestCaseRefiner:
    """
    Class to analyze and refine existing test cases to improve coverage and robustness.
    """
    
    # Define standard columns for test cases
    TEST_CASE_COLUMNS = [
        "SUBJECT", "TEST CASE", "TEST CASE NUMBER", "STEP NO", 
        "TEST STEP DESCRIPTION", "DATA", "REFERENCE VALUES", "VALUES", 
        "EXPECTED RESULT", "TRANS CODE", "TEST USER ID/ROLE", "STATUS", "TYPE"
    ]
    
    # Define refinement indicators for various aspects of test cases
    REFINEMENT_INDICATORS = {
        "missing_data": ["DATA", "VALUES", "REFERENCE VALUES"],
        "vague_steps": ["TEST STEP DESCRIPTION"],
        "incomplete_results": ["EXPECTED RESULT"],
        "missing_roles": ["TEST USER ID/ROLE"],
        "transaction_code": ["TRANS CODE"]
    }
    
    def __init__(self, refinement_rules_path: str = None):
        """
        Initialize the TestCaseRefiner with optional refinement rules.
        
        Args:
            refinement_rules_path (str, optional): Path to the refinement rules JSON file.
        """
        self.refinement_rules_path = refinement_rules_path
        self.refinement_rules = {}
        self.logger = logging.getLogger(__name__)
        
        if refinement_rules_path and os.path.exists(refinement_rules_path):
            self._load_refinement_rules()
        
        self.logger.info(f"TestCaseRefiner initialized")
    
    def _load_refinement_rules(self):
        """
        Load refinement rules from the JSON file.
        
        Raises:
            RefinementRuleError: If the rules file cannot be loaded or is invalid.
        """
        try:
            with open(self.refinement_rules_path, 'r') as f:
                self.refinement_rules = json.load(f)
            
            self.logger.debug(f"Loaded refinement rules from {self.refinement_rules_path}")
        except Exception as e:
            self.logger.error(f"Failed to load refinement rules: {str(e)}")
            raise RefinementRuleError(f"Failed to load refinement rules: {str(e)}")
    
    def load_test_case(self, file_path: str) -> pd.DataFrame:
        """
        Load a test case from an Excel or Word file.
        
        Args:
            file_path (str): Path to the test case file.
            
        Returns:
            pd.DataFrame: The test case as a DataFrame.
            
        Raises:
            TestCaseNotFoundError: If the file doesn't exist.
            TestCaseFormatError: If the file format is unsupported or invalid.
        """
        if not os.path.exists(file_path):
            error_msg = f"Test case file not found: {file_path}"
            self.logger.error(error_msg)
            raise TestCaseNotFoundError(error_msg)
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext in ['.xlsx', '.xls']:
                # Load Excel file
                df = pd.read_excel(file_path)
                
                # Verify it has expected columns
                if not all(col in df.columns for col in ["TEST CASE NUMBER", "TEST STEP DESCRIPTION"]):
                    raise TestCaseFormatError(f"File does not appear to be a valid test case format: {file_path}")
                
                return df
                
            elif file_ext in ['.docx', '.doc']:
                # For Word files, more complex processing would be needed
                # This is a placeholder for actual Word document processing
                # Would likely use a library like python-docx
                
                self.logger.warning("Word file processing is limited. Consider converting to Excel format.")
                
                # Simplified approach: Create a dataframe with basic structure
                # In a real implementation, would parse the Word doc properly
                return pd.DataFrame(columns=self.TEST_CASE_COLUMNS)
                
            else:
                raise TestCaseFormatError(f"Unsupported file format: {file_ext}")
                
        except TestCaseFormatError:
            raise
        except Exception as e:
            error_msg = f"Failed to load test case file: {str(e)}"
            self.logger.error(error_msg)
            raise TestCaseFormatError(error_msg)
    
    def _validate_step_description(self, step_description: str) -> List[str]:
        """
        Validate a test step description and suggest improvements.
        
        Args:
            step_description (str): The test step description.
            
        Returns:
            List[str]: List of suggested improvements.
        """
        suggestions = []
        
        # Check for empty description
        if not step_description or len(step_description.strip()) == 0:
            suggestions.append("Step description is empty. Add a detailed description.")
            return suggestions
        
        # Check for vague language
        vague_terms = ["check", "verify", "ensure", "make sure", "do", "perform"]
        for term in vague_terms:
            if term in step_description.lower():
                suggestions.append(f"Step uses vague term '{term}'. Consider using more specific actions.")
        
        # Check for missing action verbs
        if not re.search(r"\b(click|enter|select|navigate|input|type|verify|validate|open|close|check|submit)\b", 
                        step_description.lower()):
            suggestions.append("Step may be missing a clear action verb. Include specific actions.")
        
        # Check for length/detail
        if len(step_description.split()) < 3:
            suggestions.append("Step description is too brief. Add more details.")
        
        # Apply any custom rules from refinement_rules if available
        if "step_description_rules" in self.refinement_rules:
            for rule in self.refinement_rules["step_description_rules"]:
                # Apply pattern matching or other rule logic here
                if "pattern" in rule and re.search(rule["pattern"], step_description, re.IGNORECASE):
                    suggestions.append(rule.get("suggestion", "Consider revising this step."))
        
        return suggestions
    
    def _validate_expected_result(self, expected_result: str) -> List[str]:
        """
        Validate an expected result and suggest improvements.
        
        Args:
            expected_result (str): The expected result description.
            
        Returns:
            List[str]: List of suggested improvements.
        """
        suggestions = []
        
        # Check for empty description
        if not expected_result or len(expected_result.strip()) == 0:
            suggestions.append("Expected result is empty. Add a detailed expected outcome.")
            return suggestions
        
        # Check for vague language
        vague_terms = ["works", "succeeds", "happens", "is done", "completed"]
        for term in vague_terms:
            if term in expected_result.lower():
                suggestions.append(f"Expected result uses vague term '{term}'. Be more specific about the outcome.")
        
        # Check for verifiability
        if not re.search(r"\b(displayed|shown|appears|contains|equals|is|should|must|will)\b", 
                        expected_result.lower()):
            suggestions.append("Expected result may not be clearly verifiable. Include specific verification criteria.")
        
        # Check for length/detail
        if len(expected_result.split()) < 3:
            suggestions.append("Expected result is too brief. Add more details about the outcome.")
        
        return suggestions
    
    def _validate_data_values(self, data: str, values: str, reference_values: str) -> List[str]:
        """
        Validate data, values, and reference values for a test step.
        
        Args:
            data (str): The data field.
            values (str): The values field.
            reference_values (str): The reference values field.
            
        Returns:
            List[str]: List of suggested improvements.
        """
        suggestions = []
        
        # Check for empty fields
        if not data or len(str(data).strip()) == 0:
            suggestions.append("Data field is empty. Consider adding test data information.")
        
        if not values or len(str(values).strip()) == 0:
            suggestions.append("Values field is empty. Consider adding specific test values.")
        
        # Check for test data patterns
        # For example, check if values appear to be test data placeholders
        placeholder_pattern = r"\{\{.*?\}\}|\[.*?\]|<.*?>"
        if isinstance(values, str) and re.search(placeholder_pattern, values):
            suggestions.append("Values field contains placeholders. Replace with actual test values.")
        
        return suggestions
    
    def analyze_test_case(self, test_case_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a test case and identify potential areas for refinement.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame.
            
        Returns:
            Dict[str, Any]: Analysis results with refinement suggestions.
        """
        analysis_results = {
            "test_case_info": {},
            "overall_assessment": {},
            "step_suggestions": [],
            "missing_test_variations": [],
            "general_suggestions": []
        }
        
        # Extract basic test case info
        try:
            # Get test case number and name (from the first row)
            first_row = test_case_df.iloc[0] if len(test_case_df) > 0 else None
            if first_row is not None:
                analysis_results["test_case_info"] = {
                    "test_case_number": first_row.get("TEST CASE NUMBER", "Unknown"),
                    "test_case_name": first_row.get("TEST CASE", "Unknown"),
                    "subject": first_row.get("SUBJECT", "Unknown"),
                    "type": first_row.get("TYPE", "Unknown"),
                    "total_steps": len(test_case_df)
                }
        except Exception as e:
            self.logger.warning(f"Could not extract test case info: {str(e)}")
        
        # Analyze each test step
        for index, row in test_case_df.iterrows():
            step_no = row.get("STEP NO", index + 1)
            step_description = str(row.get("TEST STEP DESCRIPTION", ""))
            expected_result = str(row.get("EXPECTED RESULT", ""))
            data = row.get("DATA", "")
            values = row.get("VALUES", "")
            reference_values = row.get("REFERENCE VALUES", "")
            
            step_suggestions = {
                "step_no": step_no,
                "suggestions": []
            }
            
            # Validate step description
            desc_suggestions = self._validate_step_description(step_description)
            if desc_suggestions:
                step_suggestions["suggestions"].extend([{
                    "field": "TEST STEP DESCRIPTION", 
                    "current_value": step_description,
                    "suggestions": desc_suggestions
                }])
            
            # Validate expected result
            result_suggestions = self._validate_expected_result(expected_result)
            if result_suggestions:
                step_suggestions["suggestions"].extend([{
                    "field": "EXPECTED RESULT", 
                    "current_value": expected_result,
                    "suggestions": result_suggestions
                }])
            
            # Validate data values
            data_suggestions = self._validate_data_values(data, values, reference_values)
            if data_suggestions:
                step_suggestions["suggestions"].extend([{
                    "field": "DATA/VALUES", 
                    "current_value": f"DATA: {data}, VALUES: {values}",
                    "suggestions": data_suggestions
                }])
            
            # Add to results if there are suggestions
            if step_suggestions["suggestions"]:
                analysis_results["step_suggestions"].append(step_suggestions)
        
        # Overall assessment
        total_steps = len(test_case_df)
        steps_with_issues = len(analysis_results["step_suggestions"])
        
        analysis_results["overall_assessment"] = {
            "total_steps": total_steps,
            "steps_with_issues": steps_with_issues,
            "issue_percentage": (steps_with_issues / total_steps * 100) if total_steps > 0 else 0,
            "completeness_score": self._calculate_completeness_score(test_case_df)
        }
        
        # Check for missing test variations
        analysis_results["missing_test_variations"] = self._suggest_test_variations(test_case_df)
        
        # Generate general suggestions
        analysis_results["general_suggestions"] = self._generate_general_suggestions(test_case_df)
        
        return analysis_results
    
    def _calculate_completeness_score(self, test_case_df: pd.DataFrame) -> float:
        """
        Calculate a completeness score for the test case based on filled fields.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame.
            
        Returns:
            float: Completeness score (0-100).
        """
        # These are the key columns we want to check for completeness
        key_columns = [
            "TEST STEP DESCRIPTION", "EXPECTED RESULT", 
            "DATA", "VALUES", "REFERENCE VALUES"
        ]
        
        # Initialize counters
        total_fields = len(test_case_df) * len(key_columns)
        filled_fields = 0
        
        # Count filled fields
        for col in key_columns:
            if col in test_case_df.columns:
                # Convert to string to handle non-string values
                filled_fields += test_case_df[col].astype(str).str.strip().str.len().gt(0).sum()
        
        # Calculate score (0-100)
        return (filled_fields / total_fields * 100) if total_fields > 0 else 0
    
    def _suggest_test_variations(self, test_case_df: pd.DataFrame) -> List[str]:
        """
        Suggest additional test variations that might be missing.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame.
            
        Returns:
            List[str]: Suggested test variations.
        """
        suggestions = []
        
        # Extract test case type and subject if available
        test_type = test_case_df.iloc[0].get("TYPE", "") if len(test_case_df) > 0 else ""
        subject = test_case_df.iloc[0].get("SUBJECT", "") if len(test_case_df) > 0 else ""
        
        # Look for negative test scenarios
        has_negative_tests = False
        for _, row in test_case_df.iterrows():
            step_desc = str(row.get("TEST STEP DESCRIPTION", "")).lower()
            expected = str(row.get("EXPECTED RESULT", "")).lower()
            
            # Look for negative test indicators
            negative_indicators = ["invalid", "error", "fail", "negative", "incorrect"]
            if any(ind in step_desc or ind in expected for ind in negative_indicators):
                has_negative_tests = True
                break
        
        if not has_negative_tests:
            suggestions.append("Consider adding negative test scenarios (invalid inputs, error conditions)")
        
        # Look for boundary test cases
        has_boundary_tests = False
        for _, row in test_case_df.iterrows():
            step_desc = str(row.get("TEST STEP DESCRIPTION", "")).lower()
            values = str(row.get("VALUES", "")).lower()
            
            # Look for boundary test indicators
            boundary_indicators = ["boundary", "limit", "max", "min", "maximum", "minimum"]
            if any(ind in step_desc or ind in values for ind in boundary_indicators):
                has_boundary_tests = True
                break
        
        if not has_boundary_tests:
            suggestions.append("Consider adding boundary test cases (min/max values, limits)")
        
        # Suggest variations based on test type
        if "functional" in str(test_type).lower():
            suggestions.append("Consider adding performance test scenarios if applicable")
        
        return suggestions
    
    def _generate_general_suggestions(self, test_case_df: pd.DataFrame) -> List[str]:
        """
        Generate general suggestions for improving the test case.
        
        Args:
            test_case_df (pd.DataFrame): The test case DataFrame.
            
        Returns:
            List[str]: General suggestions.
        """
        suggestions = []
        
        # Check test case structure
        step_numbers = test_case_df.get("STEP NO", pd.Series(range(1, len(test_case_df) + 1)))
        
        # Check for step number sequence
        expected_steps = list(range(1, len(test_case_df) + 1))
        actual_steps = [int(s) if pd.notna(s) and str(s).isdigit() else 0 for s in step_numbers]
        
        if actual_steps != expected_steps:
            suggestions.append("Step numbers are not in sequence. Consider renumbering steps.")
        
        # Check for consistency in structure
        if len(test_case_df) > 0:
            # Check for consistent test case number
            tc_numbers = test_case_df["TEST CASE NUMBER"].unique()
            if len(tc_numbers) > 1:
                suggestions.append(f"Multiple test case numbers found ({len(tc_numbers)}). Ensure consistency.")
            
            # Check for consistent subject
            subjects = test_case_df["SUBJECT"].unique()
            if len(subjects) > 1:
                suggestions.append(f"Multiple subjects found ({len(subjects)}). Ensure consistency.")
        
        # Check for test setup/teardown
        first_step = test_case_df.iloc[0]["TEST STEP DESCRIPTION"].lower() if len(test_case_df) > 0 else ""
        last_step = test_case_df.iloc[-1]["TEST STEP DESCRIPTION"].lower() if len(test_case_df) > 0 else ""
        
        setup_keywords = ["setup", "login", "initialize", "open", "navigate", "prepare"]
        teardown_keywords = ["teardown", "logout", "cleanup", "close", "exit"]
        
        has_setup = any(keyword in first_step for keyword in setup_keywords)
        has_teardown = any(keyword in last_step for keyword in teardown_keywords)
        
        if not has_setup:
            suggestions.append("Consider adding setup steps at the beginning (login, initialization, etc.)")
        
        if not has_teardown:
            suggestions.append("Consider adding teardown steps at the end (logout, cleanup, etc.)")
        
        return suggestions
    
    def suggest_refinements(self, test_case_path: str) -> Dict[str, Any]:
        """
        Analyze a test case file and suggest refinements.
        
        Args:
            test_case_path (str): Path to the test case file.
            
        Returns:
            Dict[str, Any]: Refinement suggestions.
            
        Raises:
            TestCaseNotFoundError: If the file doesn't exist.
            TestCaseFormatError: If the file format is invalid.
        """
        # Load the test case
        test_case_df = self.load_test_case(test_case_path)
        
        # Analyze and generate suggestions
        analysis_results = self.analyze_test_case(test_case_df)
        
        # Add file information
        analysis_results["file_info"] = {
            "file_path": test_case_path,
            "file_name": os.path.basename(test_case_path),
            "analysis_date": datetime.now().isoformat()
        }
        
        return analysis_results
    
    def apply_refinements(self, test_case_path: str, refinements: Dict[str, Any], output_path: str = None) -> str:
        """
        Apply refinements to a test case and save the refined version.
        
        Args:
            test_case_path (str): Path to the original test case file.
            refinements (Dict[str, Any]): Refinement data to apply.
            output_path (str, optional): Path to save the refined file. 
                                       If None, uses original path with '_refined' suffix.
            
        Returns:
            str: Path where the refined file was saved.
            
        Raises:
            TestCaseNotFoundError: If the file doesn't exist.
            TestCaseFormatError: If the file format is invalid.
        """
        # Load the test case
        test_case_df = self.load_test_case(test_case_path)
        
        # Apply refinements if provided
        if "step_refinements" in refinements:
            for step_refinement in refinements["step_refinements"]:
                step_no = step_refinement.get("step_no")
                field_updates = step_refinement.get("updates", {})
                
                # Find the row with this step number
                step_mask = test_case_df["STEP NO"] == step_no
                if step_mask.any():
                    # Update each field
                    for field, value in field_updates.items():
                        if field in test_case_df.columns:
                            test_case_df.loc[step_mask, field] = value
        
        # Generate output path if not provided
        if output_path is None:
            file_name, file_ext = os.path.splitext(test_case_path)
            output_path = f"{file_name}_refined{file_ext}"
        
        # Save the refined test case
        file_ext = os.path.splitext(output_path)[1].lower()
        
        if file_ext in ['.xlsx', '.xls']:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Save to Excel
            test_case_df.to_excel(output_path, index=False)
            
            self.logger.info(f"Refined test case saved to {output_path}")
        else:
            raise TestCaseFormatError(f"Unsupported output format: {file_ext}")
        
        return output_path
    
    def get_refinement_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of the refinement suggestions.
        
        Args:
            analysis_results (Dict[str, Any]): The analysis results.
            
        Returns:
            Dict[str, Any]: Summary of refinement suggestions.
        """
        summary = {
            "test_case_info": analysis_results.get("test_case_info", {}),
            "overall_assessment": analysis_results.get("overall_assessment", {}),
            "total_suggestions": 0,
            "suggestion_categories": {},
            "high_priority_suggestions": []
        }
        
        # Count step suggestions by category
        categories = {}
        for step in analysis_results.get("step_suggestions", []):
            for suggestion in step.get("suggestions", []):
                field = suggestion.get("field", "Other")
                
                if field not in categories:
                    categories[field] = 0
                
                categories[field] += len(suggestion.get("suggestions", []))
                summary["total_suggestions"] += len(suggestion.get("suggestions", []))
        
        summary["suggestion_categories"] = categories
        
        # Add other suggestion counts
        other_suggestions = len(analysis_results.get("missing_test_variations", [])) + \
                          len(analysis_results.get("general_suggestions", []))
        summary["total_suggestions"] += other_suggestions
        
        if "Other" not in categories:
            categories["Other"] = 0
        categories["Other"] += other_suggestions
        
        # Identify high priority suggestions
        high_priority = []
        
        # Step suggestions with critical issues
        for step in analysis_results.get("step_suggestions", []):
            for suggestion in step.get("suggestions", []):
                for detail in suggestion.get("suggestions", []):
                    if any(term in detail.lower() for term in ["empty", "missing", "critical", "invalid"]):
                        high_priority.append({
                            "step_no": step.get("step_no"),
                            "field": suggestion.get("field"),
                            "issue": detail
                        })
        
        # General suggestions with high importance
        for suggestion in analysis_results.get("general_suggestions", []):
            if any(term in suggestion.lower() for term in ["consistency", "sequence", "setup", "teardown"]):
                high_priority.append({
                    "step_no": "N/A",
                    "field": "General",
                    "issue": suggestion
                })
        
        summary["high_priority_suggestions"] = high_priority
        
        return summary

# If running as a script
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze and refine test cases")
    parser.add_argument("--test_case", required=True, help="Path to the test case file")
    parser.add_argument("--rules", help="Path to refinement rules JSON file (optional)")
    parser.add_argument("--output", help="Path to save the analysis results (optional)")
    parser.add_argument("--apply", action="store_true", help="Apply suggested refinements")
    parser.add_argument("--refined_output", help="Path to save the refined test case (required if --apply is set)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create refiner
    refiner = TestCaseRefiner(refinement_rules_path=args.rules)
    
    # Analyze test case
    analysis_results = refiner.suggest_refinements(args.test_case)
    
    # Get summary
    summary = refiner.get_refinement_summary(analysis_results)
    
    # Print summary
    print("\nTest Case Refinement Summary:")
    print(f"Test Case: {summary['test_case_info'].get('test_case_name', 'Unknown')}")
    print(f"Test Case Number: {summary['test_case_info'].get('test_case_number', 'Unknown')}")
    print(f"Total Steps: {summary['test_case_info'].get('total_steps', 0)}")
    print(f"Completeness Score: {summary['overall_assessment'].get('completeness_score', 0):.1f}%")
    print(f"Total Suggestions: {summary['total_suggestions']}")
    
    print("\nSuggestion Categories:")
    for category, count in summary["suggestion_categories"].items():
        print(f"  - {category}: {count}")
    
    print("\nHigh Priority Suggestions:")
    for suggestion in summary["high_priority_suggestions"]:
        print(f"  - Step {suggestion['step_no']} | {suggestion['field']}: {suggestion['issue']}")
    
    # Save analysis results if output path provided
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        print(f"\nDetailed analysis saved to: {args.output}")
    
    # Apply refinements if requested
    if args.apply:
        if not args.refined_output:
            print("\nError: --refined_output is required when --apply is set")
            exit(1)
        
        # In real application, would have UI for user to select which refinements to apply
        # Here, we'll just simulate with a placeholder refinement structure
        refinements = {
            "step_refinements": []
            # Would be populated from user selections
        }
        
        refined_path = refiner.apply_refinements(args.test_case, refinements, args.refined_output)
        print(f"\nRefined test case saved to: {refined_path}")