"""
Scenario Generator Module for the LLM Test Scenario Generator.

This module generates test scenarios from processed requirements using LLM.
It integrates with document_processor.py to get requirements and llm_connector.py
to generate scenarios using LLM capabilities.

Usage:
    generator = ScenarioGenerator()
    scenarios = await generator.generate_scenarios_from_requirements(requirements)
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Union, Optional, Tuple

# Import local modules
from .document_processor import DocumentProcessor
from .llm_connector import LLMConnector


class ScenarioGenerator:
    """Class for generating test scenarios from requirements using LLM."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Scenario Generator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Initialize LLM connector
        self.llm_connector = LLMConnector(config)

    def setup_logging(self) -> None:
        """Configure logging for the scenario generator."""
        log_level = self.config.get('log_level', logging.INFO)
        self.logger.setLevel(log_level)
        
        # Create console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    async def generate_scenarios_from_requirements(
        self,
        requirements: Dict[str, Any],
        num_scenarios: Optional[int] = None,
        detail_level: Optional[str] = None,
        priority_focus: Optional[str] = None,
        custom_focus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate test scenarios from requirements.

        Args:
            requirements: Processed requirements data (from DocumentProcessor)
            num_scenarios: Number of scenarios to generate (default: from config or 5)
            detail_level: Detail level for scenarios ("low", "medium", "high")
            priority_focus: Focus on specific priority ("high", "medium", "low", or None for all)
            custom_focus: List of custom focus areas or keywords to emphasize

        Returns:
            Dictionary containing generated scenarios and metadata
        """
        self.logger.info("Generating test scenarios from requirements")
        
        # Apply default values from config if not provided
        num_scenarios = num_scenarios or self.config.get("default_num_scenarios", 5)
        detail_level = detail_level or self.config.get("default_detail_level", "medium")
        
        # Validate inputs
        if detail_level not in ["low", "medium", "high"]:
            self.logger.warning(f"Invalid detail level: {detail_level}. Using 'medium'.")
            detail_level = "medium"
        
        # Generate scenarios using LLM connector
        llm_response = await self.llm_connector.generate_test_scenarios(
            requirements, 
            num_scenarios=num_scenarios,
            detail_level=detail_level
        )
        
        # Apply post-processing and refinements
        enriched_scenarios = self._enrich_scenarios(
            llm_response["scenarios"],
            requirements,
            priority_focus,
            custom_focus
        )
        
        return {
            "scenarios": enriched_scenarios,
            "metadata": {
                **llm_response["metadata"],
                "priority_focus": priority_focus,
                "custom_focus": custom_focus
            },
            "raw_llm_response": llm_response.get("raw_llm_response", "")
        }

    async def generate_scenarios_from_document(
        self,
        document_path: str,
        num_scenarios: Optional[int] = None,
        detail_level: Optional[str] = None,
        priority_focus: Optional[str] = None,
        custom_focus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate test scenarios directly from a document.

        Args:
            document_path: Path to the document containing requirements
            num_scenarios: Number of scenarios to generate
            detail_level: Detail level for scenarios
            priority_focus: Focus on specific priority
            custom_focus: List of custom focus areas or keywords

        Returns:
            Dictionary containing generated scenarios and metadata
        """
        self.logger.info(f"Generating test scenarios from document: {document_path}")
        
        # Process document to extract requirements
        doc_processor = DocumentProcessor(self.config)
        requirements = doc_processor.process_document(document_path)
        
        # Generate scenarios from the extracted requirements
        return await self.generate_scenarios_from_requirements(
            requirements,
            num_scenarios,
            detail_level,
            priority_focus,
            custom_focus
        )
    
    async def generate_scenarios_from_jira(
        self,
        jira_data: Dict[str, Any],
        num_scenarios: Optional[int] = None,
        detail_level: Optional[str] = None,
        priority_focus: Optional[str] = None,
        custom_focus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate test scenarios from JIRA data.

        Args:
            jira_data: JIRA data containing requirements/user stories
            num_scenarios: Number of scenarios to generate
            detail_level: Detail level for scenarios
            priority_focus: Focus on specific priority
            custom_focus: List of custom focus areas or keywords

        Returns:
            Dictionary containing generated scenarios and metadata
        """
        self.logger.info("Generating test scenarios from JIRA data")
        
        # Process JIRA data to extract requirements
        doc_processor = DocumentProcessor(self.config)
        requirements = doc_processor.process_jira_export(jira_data)
        
        # Generate scenarios from the extracted requirements
        return await self.generate_scenarios_from_requirements(
            requirements,
            num_scenarios,
            detail_level,
            priority_focus,
            custom_focus
        )

    async def generate_scenarios_from_text(
        self,
        text: str,
        num_scenarios: Optional[int] = None,
        detail_level: Optional[str] = None,
        priority_focus: Optional[str] = None,
        custom_focus: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate test scenarios from raw text.

        Args:
            text: Raw text containing requirements
            num_scenarios: Number of scenarios to generate
            detail_level: Detail level for scenarios
            priority_focus: Focus on specific priority
            custom_focus: List of custom focus areas or keywords

        Returns:
            Dictionary containing generated scenarios and metadata
        """
        self.logger.info("Generating test scenarios from raw text")
        
        # Process raw text to extract requirements
        doc_processor = DocumentProcessor(self.config)
        requirements = doc_processor.process_raw_input(text)
        
        # Generate scenarios from the extracted requirements
        return await self.generate_scenarios_from_requirements(
            requirements,
            num_scenarios,
            detail_level,
            priority_focus,
            custom_focus
        )

    def _enrich_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        priority_focus: Optional[str] = None,
        custom_focus: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Enrich scenarios with additional information and adjustments.

        Args:
            scenarios: List of scenarios from LLM
            requirements: Original requirements data
            priority_focus: Priority to focus on
            custom_focus: Custom focus areas

        Returns:
            Enriched list of scenarios
        """
        enriched_scenarios = []
        
        for scenario in scenarios:
            # Make a copy to avoid modifying the original
            enriched = scenario.copy()
            
            # Add timestamp
            enriched["generation_timestamp"] = self._get_timestamp()
            
            # Apply priority focus filter if specified
            if priority_focus and "priority" in enriched:
                scenario_priority = enriched["priority"].lower()
                if priority_focus.lower() != scenario_priority:
                    continue  # Skip this scenario as it doesn't match the priority focus
            
            # Add custom focus areas if specified
            if custom_focus:
                enriched["focus_areas"] = self._determine_focus_areas(enriched, custom_focus)
            
            # Add coverage metrics
            enriched["coverage"] = self._calculate_coverage(enriched, requirements)
            
            # Normalize ID format if needed
            if "id" in enriched and not enriched["id"].startswith("TS-"):
                enriched["id"] = f"TS-{enriched['id']}"
            
            # Add test type (functional, performance, security, etc.)
            enriched["test_type"] = self._determine_test_type(enriched)
            
            # Clean up description if needed
            if "description" in enriched:
                enriched["description"] = self._clean_description(enriched["description"])
            
            enriched_scenarios.append(enriched)
            
        return enriched_scenarios

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def _determine_focus_areas(
        self, 
        scenario: Dict[str, Any],
        custom_focus: List[str]
    ) -> List[str]:
        """
        Determine which custom focus areas apply to this scenario.

        Args:
            scenario: Scenario data
            custom_focus: List of custom focus areas

        Returns:
            List of applicable focus areas
        """
        applicable_focus = []
        
        # Get the text content to check
        scenario_text = ""
        if "description" in scenario:
            scenario_text += scenario["description"] + " "
        if "title" in scenario:
            scenario_text += scenario["title"] + " "
        
        # Check each focus area
        for focus in custom_focus:
            if focus.lower() in scenario_text.lower():
                applicable_focus.append(focus)
                
        return applicable_focus

    def _calculate_coverage(
        self, 
        scenario: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate how much of the requirements this scenario covers.

        Args:
            scenario: Scenario data
            requirements: Requirements data

        Returns:
            Coverage metrics
        """
        coverage = {
            "requirements_covered": [],
            "coverage_percentage": 0.0
        }
        
        # Get related requirements if specified
        if "related_requirements" in scenario:
            related_reqs = scenario["related_requirements"]
            if isinstance(related_reqs, str):
                # Split by commas or spaces if it's a string
                related_reqs = [req.strip() for req in related_reqs.replace(",", " ").split() if req.strip()]
            
            # Add to coverage
            coverage["requirements_covered"] = related_reqs
            
            # Calculate percentage if requirements are available
            if requirements.get("requirements"):
                total_reqs = len(requirements["requirements"])
                if total_reqs > 0:
                    coverage["coverage_percentage"] = (len(related_reqs) / total_reqs) * 100
        
        return coverage

    def _determine_test_type(self, scenario: Dict[str, Any]) -> str:
        """
        Determine the test type based on scenario content.

        Args:
            scenario: Scenario data

        Returns:
            Test type (functional, security, performance, etc.)
        """
        # Default test type
        test_type = "functional"
        
        # Get the text content to check
        scenario_text = ""
        if "description" in scenario:
            scenario_text += scenario["description"].lower() + " "
        if "title" in scenario:
            scenario_text += scenario["title"].lower() + " "
        
        # Check for specific test types
        if any(term in scenario_text for term in ["security", "auth", "authentication", "authorization", "permission"]):
            test_type = "security"
        elif any(term in scenario_text for term in ["performance", "load", "stress", "speed", "response time"]):
            test_type = "performance"
        elif any(term in scenario_text for term in ["usability", "user experience", "ux", "ui", "interface"]):
            test_type = "usability"
        elif any(term in scenario_text for term in ["integration", "api", "interface", "communication"]):
            test_type = "integration"
        
        return test_type

    def _clean_description(self, description: str) -> str:
        """
        Clean and format the scenario description.

        Args:
            description: Original description

        Returns:
            Cleaned description
        """
        # Remove any extra whitespace
        description = " ".join(description.split())
        
        # Remove any markdown-style formatting that might have been added by the LLM
        description = description.replace("*", "").replace("#", "").replace("`", "")
        
        return description

    async def close(self):
        """Close connections and resources."""
        await self.llm_connector.close()


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        generator = ScenarioGenerator()
        
        # Example 1: Generate from raw text
        sample_requirements = """
        As a mobile banking user, I want to be able to authenticate using multiple factors (password and mobile OTP) so that my banking transactions are more secure.
        
        Acceptance Criteria:
        1. Users should be able to log in with their username and password
        2. Upon successful password verification, the system should send an OTP to the registered mobile number
        3. The OTP should be 6 digits and valid for 3 minutes
        4. Users should be able to enter the OTP to complete authentication
        5. After 3 failed OTP attempts, the account should be temporarily locked for 30 minutes
        """
        
        scenarios = await generator.generate_scenarios_from_text(
            sample_requirements,
            num_scenarios=3,
            detail_level="medium"
        )
        
        print(json.dumps(scenarios, indent=2))
        
        await generator.close()
    
    asyncio.run(example())