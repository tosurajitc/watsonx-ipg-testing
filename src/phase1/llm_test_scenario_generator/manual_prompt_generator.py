"""
Manual Prompt Generator Module

This module processes manual text input to generate test scenarios using LLM models.
It leverages the LLMConnector module without any fallback to hard-coded data.

Usage:
    from src.phase1.manual_prompt_generator import ManualPromptGenerator
    
    generator = ManualPromptGenerator()
    scenarios = await generator.generate_scenarios_from_text(
        "The system shall authenticate users with username and password.",
        num_scenarios=3,
        detail_level="medium"
    )
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from src.phase1.llm_test_scenario_generator.llm_connector import LLMConnector

# Configure logging
logger = logging.getLogger(__name__)

class ManualPromptGeneratorError(Exception):
    """Base exception class for all manual prompt generator errors."""
    pass

class InputValidationError(ManualPromptGeneratorError):
    """Exception raised when input validation fails."""
    pass

class LLMProcessingError(ManualPromptGeneratorError):
    """Exception raised when LLM processing fails."""
    pass

class ResponseParsingError(ManualPromptGeneratorError):
    """Exception raised when response parsing fails."""
    pass


class ManualPromptGenerator:
    """Class for generating test scenarios from manual text input using LLMs."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ManualPromptGenerator.

        Args:
            config: Optional configuration dictionary to override defaults
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Set up defaults if not in config
        self.max_input_length = self.config.get('max_input_length', 5000)
        self.min_input_length = self.config.get('min_input_length', 10)
        self.default_detail_level = self.config.get('default_detail_level', 'medium')
        self.default_scenario_count = self.config.get('default_scenario_count', 5)
        self.max_scenario_count = self.config.get('max_scenario_count', 10)
        
        # LLM Connector will be initialized when needed to avoid
        # unnecessary connection overhead
        self._llm_connector = None

    async def _get_llm_connector(self) -> LLMConnector:
        """
        Get or create the LLM connector instance.

        Returns:
            LLMConnector: Initialized LLM connector
        """
        if self._llm_connector is None:
            self._llm_connector = LLMConnector(self.config.get('llm_config'))
        return self._llm_connector

    async def generate_scenarios_from_text(
        self,
        text: str,
        num_scenarios: int = None,
        detail_level: str = None
    ) -> Dict[str, Any]:
        """
        Generate test scenarios from raw text input.

        Args:
            text: Raw text input containing requirements or specifications
            num_scenarios: Number of scenarios to generate (default based on config)
            detail_level: Level of detail for scenarios ("low", "medium", "high")

        Returns:
            Dictionary containing generated test scenarios and metadata

        Raises:
            InputValidationError: If input validation fails
            LLMProcessingError: If LLM processing fails
            ResponseParsingError: If response parsing fails
        """
        self.logger.info("Generating test scenarios from manual text input")
        
        # Use defaults if not provided
        num_scenarios = num_scenarios or self.default_scenario_count
        detail_level = detail_level or self.default_detail_level
        
        # Validate input
        self._validate_input(text, num_scenarios, detail_level)
        
        try:
            # Get LLM connector
            llm_connector = await self._get_llm_connector()
            
            # Generate scenario prompt
            system_prompt = self._create_system_prompt()
            user_prompt = self._create_user_prompt(text, num_scenarios, detail_level)
            
            # Send to LLM
            response = await llm_connector.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.4  # Slightly higher temperature for creative scenarios
            )
            
            # Parse response
            scenarios = self._parse_scenario_response(response["text"])
            
            # Create result structure
            result = {
                "scenarios": scenarios,
                "metadata": {
                    "num_requested": num_scenarios,
                    "num_generated": len(scenarios),
                    "detail_level": detail_level,
                    "input_length": len(text),
                    "model_used": llm_connector.model,
                    "elapsed_time": response.get("elapsed_time", -1)
                },
                "raw_llm_response": response["text"]
            }
            
            self.logger.info(
                f"Successfully generated {len(scenarios)} test scenarios " 
                f"(requested: {num_scenarios})"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating test scenarios: {str(e)}")
            
            # Re-raise as appropriate exception type
            if isinstance(e, ManualPromptGeneratorError):
                raise
            else:
                raise LLMProcessingError(f"Failed to process with LLM: {str(e)}")
        
    def _validate_input(
        self, 
        text: str, 
        num_scenarios: int,
        detail_level: str
    ) -> None:
        """
        Validate input parameters.

        Args:
            text: Input text to validate
            num_scenarios: Number of scenarios to validate
            detail_level: Detail level to validate

        Raises:
            InputValidationError: If validation fails
        """
        # Validate text
        if not text or not isinstance(text, str):
            raise InputValidationError("Input text is required and must be a string")
        
        text_length = len(text.strip())
        if text_length < self.min_input_length:
            raise InputValidationError(
                f"Input text is too short (minimum {self.min_input_length} characters)"
            )
        
        if text_length > self.max_input_length:
            raise InputValidationError(
                f"Input text is too long (maximum {self.max_input_length} characters)"
            )
        
        # Validate num_scenarios
        if not isinstance(num_scenarios, int) or num_scenarios < 1:
            raise InputValidationError("Number of scenarios must be a positive integer")
        
        if num_scenarios > self.max_scenario_count:
            raise InputValidationError(
                f"Number of scenarios exceeds maximum ({self.max_scenario_count})"
            )
        
        # Validate detail_level
        valid_detail_levels = ["low", "medium", "high"]
        if detail_level not in valid_detail_levels:
            raise InputValidationError(
                f"Detail level must be one of: {', '.join(valid_detail_levels)}"
            )

    def _create_system_prompt(self) -> str:
        """
        Create system prompt for test scenario generation.

        Returns:
            Formatted system prompt string
        """
        return """You are an expert test engineer specialized in converting software requirements into comprehensive test scenarios. Your task is to analyze the provided requirements and create detailed, testable scenarios that would verify the system works as expected.

Focus on:
1. Full coverage of functional and non-functional requirements
2. Edge cases and exception paths
3. Realistic user workflows
4. Clear, measurable outcomes
5. Scenarios that can be further broken down into specific test cases

Format each test scenario with:
- Test Scenario ID (TS-XXX-YY format)
- Title (concise description)
- Description (detailed explanation)
- Priority (High/Medium/Low based on business impact)"""

    def _create_user_prompt(
        self,
        text: str,
        num_scenarios: int,
        detail_level: str
    ) -> str:
        """
        Create user prompt for test scenario generation.

        Args:
            text: Input text containing requirements
            num_scenarios: Number of scenarios to generate
            detail_level: Level of detail for scenarios

        Returns:
            Formatted user prompt string
        """
        prompt = f"Please create {num_scenarios} test scenarios with {detail_level} level of detail based on the following requirements:\n\n"
        
        # Add the input text
        prompt += "REQUIREMENTS TEXT:\n"
        prompt += text
        prompt += "\n\n"
        
        # Add instructions based on detail level
        if detail_level == "low":
            prompt += "Create basic test scenarios covering the main functionality. Keep descriptions brief.\n\n"
        elif detail_level == "high":
            prompt += "Create comprehensive test scenarios with detailed descriptions. Cover edge cases, negative testing, and all possible user workflows.\n\n"
        else:  # medium
            prompt += "Create balanced test scenarios covering key functionality and common edge cases. Include clear descriptions.\n\n"
        
        prompt += """Format each test scenario as follows:

Test Scenario ID: TS-XXX-YY (where XXX relates to the requirement area)
Title: [Brief descriptive title]
Description: [Detailed description explaining what needs to be tested]
Priority: [High/Medium/Low]

Ensure each scenario is testable and has clear pass/fail criteria."""
        
        return prompt

    def _parse_scenario_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response to extract structured test scenarios.

        Args:
            response_text: Raw text response from LLM

        Returns:
            List of dictionaries containing structured test scenarios

        Raises:
            ResponseParsingError: If parsing fails
        """
        if not response_text or not isinstance(response_text, str):
            raise ResponseParsingError("Empty or invalid LLM response")
            
        scenarios = []
        current_scenario = {}
        
        # Define common field names and possible variations
        field_patterns = {
            "id": ["Test Scenario ID:", "Scenario ID:", "ID:"],
            "title": ["Title:"],
            "description": ["Description:"],
            "priority": ["Priority:"]
        }
        
        try:
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line starts a new scenario
                if any(pattern in line for pattern in field_patterns["id"]):
                    # Save previous scenario if it exists
                    if current_scenario and "id" in current_scenario:
                        scenarios.append(current_scenario)
                    
                    # Start new scenario
                    current_scenario = {}
                    for pattern in field_patterns["id"]:
                        if pattern in line:
                            current_scenario["id"] = line.split(pattern)[1].strip()
                            break
                
                # Process other fields
                else:
                    for field, patterns in field_patterns.items():
                        if field != "id":  # ID is handled separately above
                            for pattern in patterns:
                                if line.startswith(pattern):
                                    value = line.split(pattern)[1].strip()
                                    current_scenario[field] = value
                                    break
                    
                    # If not a field header, could be continuation of description
                    if "description" in current_scenario and not any(p in line for p in [item for sublist in field_patterns.values() for item in sublist]):
                        if not line.startswith("-") and not line[0].isdigit():
                            current_scenario["description"] += f" {line}"
            
            # Add the last scenario if it exists
            if current_scenario and "id" in current_scenario:
                scenarios.append(current_scenario)
            
            # Validation: Ensure we have at least one scenario
            if not scenarios:
                raise ResponseParsingError("No valid scenarios found in LLM response")
            
            # Validation: Ensure each scenario has required fields
            required_fields = ["id", "title", "description"]
            for scenario in scenarios:
                missing_fields = [field for field in required_fields if field not in scenario]
                if missing_fields:
                    self.logger.warning(
                        f"Scenario {scenario.get('id', 'unknown')} missing fields: {missing_fields}"
                    )
            
            return scenarios
            
        except Exception as e:
            if isinstance(e, ResponseParsingError):
                raise
            else:
                raise ResponseParsingError(f"Failed to parse LLM response: {str(e)}")

    async def close(self):
        """Close the LLM connector if it exists."""
        if self._llm_connector:
            await self._llm_connector.close()
            self._llm_connector = None

# Example usage (for documentation purposes)
if __name__ == "__main__":
    # This code won't run in the module but serves as an example
    async def example():
        generator = ManualPromptGenerator()
        
        try:
            scenarios = await generator.generate_scenarios_from_text(
                "The system shall authenticate users with username and password. " +
                "The system shall implement two-factor authentication. " +
                "The system shall lock accounts after 3 failed login attempts.",
                num_scenarios=3,
                detail_level="medium"
            )
            
            print(f"Generated {len(scenarios['scenarios'])} scenarios:")
            for scenario in scenarios['scenarios']:
                print(f"- {scenario['id']}: {scenario['title']}")
                
        except ManualPromptGeneratorError as e:
            print(f"Error: {str(e)}")
        finally:
            await generator.close()
            
    # asyncio.run(example())  # Uncomment to run the example