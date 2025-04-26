"""
Scenario Validator Module for the LLM Test Scenario Generator.

This module validates generated test scenarios for completeness and testability.
It ensures that generated scenarios meet quality standards and are suitable
for test case development.

Usage:
    validator = ScenarioValidator()
    validation_results = validator.validate_scenarios(scenarios)
"""

import re
import logging
from typing import Dict, List, Any, Union, Optional, Tuple, Set


class ScenarioValidator:
    """Class for validating test scenarios for completeness and testability."""

    # Required fields for a valid test scenario
    REQUIRED_FIELDS = ["id", "title", "description"]
    
    # Recommended fields for a comprehensive test scenario
    RECOMMENDED_FIELDS = ["priority", "related_requirements"]
    
    # Priority values
    VALID_PRIORITIES = ["high", "medium", "low"]
    
    # Test types
    VALID_TEST_TYPES = [
        "functional", "security", "performance", "usability", 
        "integration", "accessibility", "reliability", "compatibility"
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Scenario Validator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

    def setup_logging(self) -> None:
        """Configure logging for the scenario validator."""
        log_level = self.config.get('log_level', logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def validate_scenarios(
        self, 
        scenarios: List[Dict[str, Any]],
        requirements: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Validate a list of test scenarios.

        Args:
            scenarios: List of scenarios to validate
            requirements: Optional requirements data for cross-validation
            strict_mode: If True, any failure results in overall validation failure

        Returns:
            Dictionary containing validation results and metrics
        """
        self.logger.info(f"Validating {len(scenarios)} test scenarios")
        
        validation_results = {
            "valid": True,
            "scenarios": [],
            "metrics": {
                "total_scenarios": len(scenarios),
                "valid_scenarios": 0,
                "invalid_scenarios": 0,
                "issues_found": 0,
                "completeness_score": 0.0,
                "testability_score": 0.0,
                "coverage_score": 0.0,
                "overall_quality_score": 0.0
            }
        }
        
        # Validate each scenario
        for scenario in scenarios:
            scenario_result = self.validate_scenario(
                scenario, 
                requirements=requirements,
                strict_mode=strict_mode
            )
            
            validation_results["scenarios"].append(scenario_result)
            
            # Update metrics
            if scenario_result["valid"]:
                validation_results["metrics"]["valid_scenarios"] += 1
            else:
                validation_results["metrics"]["invalid_scenarios"] += 1
                validation_results["metrics"]["issues_found"] += len(scenario_result["issues"])
                
                # In strict mode, any invalid scenario makes the whole set invalid
                if strict_mode:
                    validation_results["valid"] = False
        
        # Calculate overall scores
        validation_results["metrics"] = self._calculate_metrics(
            validation_results["scenarios"], 
            validation_results["metrics"],
            requirements
        )
        
        # If not in strict mode, determine overall validity based on thresholds
        if not strict_mode:
            quality_threshold = self.config.get("quality_threshold", 0.7)
            validation_results["valid"] = (
                validation_results["metrics"]["overall_quality_score"] >= quality_threshold
            )
        
        self.logger.info(
            f"Validation complete. Valid: {validation_results['valid']}, "
            f"Quality score: {validation_results['metrics']['overall_quality_score']:.2f}"
        )
        
        return validation_results

    def validate_scenario(
        self, 
        scenario: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None,
        strict_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Validate a single test scenario.

        Args:
            scenario: Test scenario to validate
            requirements: Optional requirements data for cross-validation
            strict_mode: If True, any issue results in validation failure

        Returns:
            Dictionary containing validation results for the scenario
        """
        validation_result = {
            "id": scenario.get("id", "unknown"),
            "valid": True,
            "issues": [],
            "warnings": [],
            "metrics": {
                "completeness_score": 0.0,
                "testability_score": 0.0,
                "coverage_score": 0.0,
                "quality_score": 0.0
            }
        }
        
        # Validate required fields
        for field in self.REQUIRED_FIELDS:
            if field not in scenario or not scenario[field]:
                validation_result["issues"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Check recommended fields
        for field in self.RECOMMENDED_FIELDS:
            if field not in scenario or not scenario[field]:
                validation_result["warnings"].append(f"Missing recommended field: {field}")
        
        # Validate ID format (expected format: TS-XXX-YY)
        if "id" in scenario:
            id_pattern = r"^TS-[A-Z0-9]+-[0-9]+$"
            if not re.match(id_pattern, scenario["id"]):
                validation_result["warnings"].append(
                    f"ID format does not match expected pattern TS-XXX-YY: {scenario['id']}"
                )
        
        # Validate priority value
        if "priority" in scenario:
            priority = scenario["priority"].lower()
            if priority not in self.VALID_PRIORITIES:
                validation_result["warnings"].append(
                    f"Invalid priority value: {priority}. Expected one of: {', '.join(self.VALID_PRIORITIES)}"
                )
        
        # Validate test type if present
        if "test_type" in scenario:
            test_type = scenario["test_type"].lower()
            if test_type not in self.VALID_TEST_TYPES:
                validation_result["warnings"].append(
                    f"Unusual test type: {test_type}. Common types: {', '.join(self.VALID_TEST_TYPES)}"
                )
        
        # Validate description for testability
        if "description" in scenario:
            testability_issues = self._validate_description_testability(scenario["description"])
            validation_result["issues"].extend(testability_issues)
            
            if testability_issues and strict_mode:
                validation_result["valid"] = False
        
        # Validate related requirements (if requirements data is provided)
        if requirements and "related_requirements" in scenario and scenario["related_requirements"]:
            req_validation_issues = self._validate_related_requirements(
                scenario["related_requirements"],
                requirements
            )
            
            if req_validation_issues:
                validation_result["warnings"].extend(req_validation_issues)
        
        # Calculate scenario metrics
        validation_result["metrics"] = self._calculate_scenario_metrics(
            scenario, 
            validation_result["issues"],
            validation_result["warnings"],
            requirements
        )
        
        # In non-strict mode, determine validity based on quality score
        if not strict_mode:
            quality_threshold = self.config.get("scenario_quality_threshold", 0.6)
            validation_result["valid"] = validation_result["metrics"]["quality_score"] >= quality_threshold
        
        return validation_result

    def _validate_description_testability(self, description: str) -> List[str]:
        """
        Validate description for testability criteria.

        Args:
            description: Scenario description

        Returns:
            List of testability issues found
        """
        issues = []
        
        # Check description length (too short may lack detail)
        if len(description) < 30:
            issues.append("Description is too short to provide adequate testing guidance")
        
        # Check for testability aspects
        testability_aspects = [
            ("preconditions", ["precondition", "pre-condition", "prerequisite", "before"]),
            ("expected results", ["expect", "result", "outcome", "should", "must"]),
            ("clear steps", ["step", "perform", "execute", "do", "action"]),
            ("success criteria", ["success", "pass", "criteria", "verify", "validate", "check"])
        ]
        
        missing_aspects = []
        for aspect, keywords in testability_aspects:
            if not any(keyword in description.lower() for keyword in keywords):
                missing_aspects.append(aspect)
        
        if missing_aspects:
            issues.append(f"Description lacks key testability aspects: {', '.join(missing_aspects)}")
        
        # Check for ambiguous language
        ambiguous_terms = ["may", "might", "could", "should consider", "etc", "and so on", "and more"]
        found_ambiguous = [term for term in ambiguous_terms if term in description.lower()]
        
        if found_ambiguous:
            issues.append(f"Description contains ambiguous terms: {', '.join(found_ambiguous)}")
        
        return issues

    def _validate_related_requirements(
        self,
        related_requirements: Union[str, List[str]],
        requirements: Dict[str, Any]
    ) -> List[str]:
        """
        Validate that related requirements exist in the requirements data.

        Args:
            related_requirements: Related requirement IDs
            requirements: Requirements data

        Returns:
            List of validation issues found
        """
        issues = []
        
        # Convert to list if it's a string
        if isinstance(related_requirements, str):
            related_reqs = [req.strip() for req in related_requirements.replace(",", " ").split() if req.strip()]
        else:
            related_reqs = related_requirements
        
        # Extract requirement IDs from requirements data
        requirement_ids = set()
        if "requirements" in requirements:
            for req in requirements["requirements"]:
                if "id" in req:
                    requirement_ids.add(req["id"])
        
        # Check if related requirements exist
        for req_id in related_reqs:
            if req_id not in requirement_ids:
                issues.append(f"Referenced requirement not found in requirements data: {req_id}")
        
        return issues

    def _calculate_scenario_metrics(
        self,
        scenario: Dict[str, Any],
        issues: List[str],
        warnings: List[str],
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Calculate quality metrics for a scenario.

        Args:
            scenario: Test scenario
            issues: Validation issues
            warnings: Validation warnings
            requirements: Optional requirements data

        Returns:
            Dictionary of quality metrics
        """
        metrics = {
            "completeness_score": 0.0,
            "testability_score": 0.0,
            "coverage_score": 0.0,
            "quality_score": 0.0
        }
        
        # Calculate completeness score
        total_fields = len(self.REQUIRED_FIELDS) + len(self.RECOMMENDED_FIELDS)
        present_fields = sum(1 for field in self.REQUIRED_FIELDS if field in scenario and scenario[field])
        present_fields += sum(0.5 for field in self.RECOMMENDED_FIELDS if field in scenario and scenario[field])
        
        metrics["completeness_score"] = round(present_fields / total_fields, 2)
        
        # Calculate testability score
        testability_base = 1.0
        testability_deduction = len([issue for issue in issues if "testability" in issue.lower()]) * 0.2
        testability_warning_deduction = len([warning for warning in warnings if "test" in warning.lower()]) * 0.1
        
        metrics["testability_score"] = max(0.0, round(testability_base - testability_deduction - testability_warning_deduction, 2))
        
        # Calculate coverage score
        if requirements and "requirements" in requirements and "related_requirements" in scenario:
            total_reqs = len(requirements["requirements"])
            if total_reqs > 0 and isinstance(scenario["related_requirements"], (list, str)):
                if isinstance(scenario["related_requirements"], str):
                    related_reqs = [req.strip() for req in scenario["related_requirements"].replace(",", " ").split() if req.strip()]
                else:
                    related_reqs = scenario["related_requirements"]
                
                metrics["coverage_score"] = round(min(1.0, len(related_reqs) / (total_reqs * 0.2)), 2)
            else:
                metrics["coverage_score"] = 0.0
        else:
            # If no requirements data or no related requirements, use average value
            metrics["coverage_score"] = 0.5
        
        # Calculate overall quality score
        # Weightage: Completeness (40%), Testability (40%), Coverage (20%)
        metrics["quality_score"] = round(
            (metrics["completeness_score"] * 0.4) +
            (metrics["testability_score"] * 0.4) +
            (metrics["coverage_score"] * 0.2),
            2
        )
        
        return metrics

    def _calculate_metrics(
        self,
        scenario_results: List[Dict[str, Any]],
        existing_metrics: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate overall metrics for a set of scenarios.

        Args:
            scenario_results: Validation results for individual scenarios
            existing_metrics: Existing metrics to update
            requirements: Optional requirements data

        Returns:
            Updated metrics dictionary
        """
        metrics = existing_metrics.copy()
        
        # Skip calculation if no scenarios
        if not scenario_results:
            return metrics
        
        # Calculate average scores
        metrics["completeness_score"] = round(
            sum(s["metrics"]["completeness_score"] for s in scenario_results) / len(scenario_results),
            2
        )
        
        metrics["testability_score"] = round(
            sum(s["metrics"]["testability_score"] for s in scenario_results) / len(scenario_results),
            2
        )
        
        metrics["coverage_score"] = round(
            sum(s["metrics"]["coverage_score"] for s in scenario_results) / len(scenario_results),
            2
        )
        
        # Calculate overall quality score
        # Weightage: Completeness (35%), Testability (35%), Coverage (20%), Valid Scenario Ratio (10%)
        valid_ratio = metrics["valid_scenarios"] / max(1, metrics["total_scenarios"])
        
        metrics["overall_quality_score"] = round(
            (metrics["completeness_score"] * 0.35) +
            (metrics["testability_score"] * 0.35) +
            (metrics["coverage_score"] * 0.20) +
            (valid_ratio * 0.10),
            2
        )
        
        # Calculate requirements coverage if requirements data is provided
        if requirements and "requirements" in requirements and requirements["requirements"]:
            total_reqs = len(requirements["requirements"])
            covered_reqs = self._calculate_requirements_coverage(scenario_results, requirements)
            
            metrics["requirements_coverage"] = {
                "total_requirements": total_reqs,
                "covered_requirements": len(covered_reqs),
                "coverage_percentage": round((len(covered_reqs) / total_reqs) * 100, 1),
                "uncovered_requirements": [req["id"] for req in requirements["requirements"] 
                                         if "id" in req and req["id"] not in covered_reqs]
            }
        
        return metrics

    def _calculate_requirements_coverage(
        self,
        scenario_results: List[Dict[str, Any]],
        requirements: Dict[str, Any]
    ) -> Set[str]:
        """
        Calculate which requirements are covered by the scenarios.

        Args:
            scenario_results: Validation results for individual scenarios
            requirements: Requirements data

        Returns:
            Set of covered requirement IDs
        """
        covered_reqs = set()
        
        # Extract requirement IDs from scenarios
        for result in scenario_results:
            scenario = next((s for s in result.get("scenarios", []) if s.get("id") == result["id"]), {})
            if not scenario and "related_requirements" in result:
                scenario = result
                
            if "related_requirements" in scenario:
                related_reqs = scenario["related_requirements"]
                if isinstance(related_reqs, str):
                    req_ids = [req.strip() for req in related_reqs.replace(",", " ").split() if req.strip()]
                    covered_reqs.update(req_ids)
                elif isinstance(related_reqs, list):
                    covered_reqs.update(related_reqs)
        
        return covered_reqs

    def suggest_improvements(
        self, 
        scenario: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> List[str]:
        """
        Suggest improvements for a test scenario based on validation results.

        Args:
            scenario: Test scenario
            validation_result: Validation result for the scenario

        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Suggestions for missing fields
        for issue in validation_result.get("issues", []):
            if "Missing required field" in issue:
                field = issue.split(": ")[1]
                suggestions.append(f"Add the missing '{field}' field to the scenario")
        
        for warning in validation_result.get("warnings", []):
            if "Missing recommended field" in warning:
                field = warning.split(": ")[1]
                suggestions.append(f"Consider adding the '{field}' field to improve scenario quality")
        
        # Suggestions for testability issues
        testability_issues = [issue for issue in validation_result.get("issues", []) 
                             if "testability" in issue.lower()]
        
        if any("lacks key testability aspects" in issue for issue in testability_issues):
            for issue in testability_issues:
                if "lacks key testability aspects" in issue:
                    missing_aspects = issue.split(": ")[1]
                    for aspect in missing_aspects.split(", "):
                        if aspect == "preconditions":
                            suggestions.append("Add preconditions to clarify the state before test execution")
                        elif aspect == "expected results":
                            suggestions.append("Specify clear expected results to determine test success/failure")
                        elif aspect == "clear steps":
                            suggestions.append("Include clear steps or actions to perform during the test")
                        elif aspect == "success criteria":
                            suggestions.append("Define explicit success criteria for test validation")
        
        # Suggestions for ambiguous language
        if any("ambiguous terms" in issue for issue in testability_issues):
            suggestions.append("Replace ambiguous terms with specific, measurable language")
        
        # Suggestions for ID format
        id_warning = next((w for w in validation_result.get("warnings", []) if "ID format" in w), None)
        if id_warning:
            suggestions.append("Update the scenario ID to follow the TS-XXX-YY format")
        
        # Suggestions for priority
        priority_warning = next((w for w in validation_result.get("warnings", []) if "priority value" in w), None)
        if priority_warning:
            suggestions.append("Set priority to one of: high, medium, low")
        
        # Suggestions for description improvement
        if "description" in scenario and len(scenario["description"]) < 100:
            suggestions.append("Expand the description to provide more detailed testing guidance")
        
        return suggestions


# Example usage
if __name__ == "__main__":
    # Sample scenario for testing
    sample_scenario = {
        "id": "TS-AUTH-01",
        "title": "Valid User Authentication",
        "description": "Verify that users can successfully authenticate using valid credentials and OTP. The system should validate the username and password, then send an OTP to the registered mobile number.",
        "priority": "high",
        "related_requirements": ["REQ-1", "REQ-2"],
        "test_type": "functional"
    }
    
    # Initialize validator
    validator = ScenarioValidator()
    
    # Validate a single scenario
    result = validator.validate_scenario(sample_scenario)
    print(f"Scenario '{sample_scenario['id']}' validation result: {'Valid' if result['valid'] else 'Invalid'}")
    print(f"Issues: {result['issues']}")
    print(f"Warnings: {result['warnings']}")
    print(f"Quality Score: {result['metrics']['quality_score']}")
    
    # Get improvement suggestions
    suggestions = validator.suggest_improvements(sample_scenario, result)
    if suggestions:
        print("\nImprovement Suggestions:")
        for suggestion in suggestions:
            print(f"- {suggestion}")