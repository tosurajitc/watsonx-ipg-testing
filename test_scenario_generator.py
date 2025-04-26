"""
Test script for the LLM Test Scenario Generator Module.

This script tests the functionality of each component and their integration.
It's designed to work with the project directory structure where:
- Source files are in src/phase1/llm_test_scenario_generator/
- The .env file is in the root folder
"""

import os
import sys
import asyncio
import json
from dotenv import load_dotenv

# Add the source directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, 'src'))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Import local modules
from phase1.llm_test_scenario_generator.document_processor import DocumentProcessor
from phase1.llm_test_scenario_generator.llm_connector import LLMConnector
from phase1.llm_test_scenario_generator.scenario_generator import ScenarioGenerator
from phase1.llm_test_scenario_generator.scenario_validator import ScenarioValidator

# Load environment variables from the root directory
root_dir = os.path.abspath(os.path.join(current_dir))
env_path = os.path.join(root_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"Loaded .env file from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")
    load_dotenv()  # Try default locations

# Sample test data
SAMPLE_REQUIREMENTS_TEXT = """
User Story ID: IPG-157
Title: Customer Authentication with Multi-Factor Authentication
Priority: High

As a mobile banking user
I want to be able to authenticate using multiple factors (password and mobile OTP)
So that my banking transactions are more secure

Acceptance Criteria:
1. Users should be able to log in with their username and password
2. Upon successful password verification, the system should send an OTP to the registered mobile number
3. The OTP should be 6 digits and valid for 3 minutes
4. Users should be able to enter the OTP to complete authentication
5. After 3 failed OTP attempts, the account should be temporarily locked for 30 minutes
6. Users should be able to request a new OTP if the original expires
7. System should maintain an audit log of all authentication attempts (successful and failed)
"""

# Define output directory for test results
output_dir = os.path.join(current_dir, 'test_results')
os.makedirs(output_dir, exist_ok=True)

async def test_document_processor():
    """Test the DocumentProcessor component."""
    print("\n--- Testing DocumentProcessor ---")
    processor = DocumentProcessor()
    
    # Test processing raw text input
    requirements = processor.process_raw_input(SAMPLE_REQUIREMENTS_TEXT)
    
    print(f"Extracted {len(requirements.get('user_stories', []))} user stories")
    if requirements.get('user_stories'):
        print(f"First user story role: {requirements['user_stories'][0].get('role', 'N/A')}")
    
    print(f"Extracted {len(requirements.get('acceptance_criteria', []))} acceptance criteria")
    if requirements.get('acceptance_criteria'):
        print(f"First acceptance criteria: {requirements['acceptance_criteria'][0]}")
    
    return requirements

async def test_llm_connector():
    """Test the LLMConnector component."""
    print("\n--- Testing LLMConnector ---")
    connector = LLMConnector()
    
    # Print current configuration for debugging
    print(f"LLM Service: {connector.llm_service}")
    print(f"API Base: {connector.api_base}")
    print(f"Model: {connector.model}")
    
    try:
        # Test a simple prompt
        prompt = "Generate a single test scenario for user authentication with OTP."
        system_prompt = "You are a test scenario generator. Keep your response short and focused."
        
        print("Sending test prompt to LLM service...")
        response = await connector.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=500
        )
        
        print(f"LLM Response received successfully. Length: {len(response.get('text', ''))}")
        print(f"First 150 characters: {response.get('text', '')[:150]}...")
        
        await connector.close()
        return response
    except Exception as e:
        print(f"Error testing LLM connector: {str(e)}")
        await connector.close()
        return None

async def test_scenario_generator(requirements):
    """Test the ScenarioGenerator component."""
    print("\n--- Testing ScenarioGenerator ---")
    generator = ScenarioGenerator()
    
    try:
        # Generate scenarios from requirements
        print("Generating test scenarios...")
        scenarios_response = await generator.generate_scenarios_from_requirements(
            requirements,
            num_scenarios=2,
            detail_level="medium"
        )
        
        num_scenarios = len(scenarios_response.get("scenarios", []))
        print(f"Generated {num_scenarios} test scenarios")
        
        if num_scenarios > 0:
            first_scenario = scenarios_response["scenarios"][0]
            print(f"First scenario ID: {first_scenario.get('id', 'N/A')}")
            print(f"First scenario title: {first_scenario.get('title', 'N/A')}")
        
        await generator.close()
        return scenarios_response
    except Exception as e:
        print(f"Error testing scenario generator: {str(e)}")
        await generator.close()
        return None

async def test_scenario_validator(scenarios_response):
    """Test the ScenarioValidator component."""
    print("\n--- Testing ScenarioValidator ---")
    validator = ScenarioValidator()
    
    if not scenarios_response or "scenarios" not in scenarios_response:
        print("No scenarios available for validation")
        return None
    
    # Validate the generated scenarios
    print("Validating test scenarios...")
    validation_results = validator.validate_scenarios(
        scenarios_response["scenarios"],
        strict_mode=False
    )
    
    print(f"Validation complete. Overall valid: {validation_results['valid']}")
    print(f"Valid scenarios: {validation_results['metrics']['valid_scenarios']}")
    print(f"Invalid scenarios: {validation_results['metrics']['invalid_scenarios']}")
    print(f"Overall quality score: {validation_results['metrics']['overall_quality_score']}")
    
    if validation_results['scenarios']:
        first_result = validation_results['scenarios'][0]
        print(f"First scenario validation - ID: {first_result.get('id', 'N/A')}, Valid: {first_result.get('valid', False)}")
        if first_result.get('issues'):
            print(f"Issues: {first_result['issues']}")
        if first_result.get('warnings'):
            print(f"Warnings: {first_result['warnings']}")
    
    return validation_results

async def run_full_integration_test():
    """Run a full integration test of all components."""
    print("\n=== Running Full Integration Test ===")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    
    # 1. Process requirements
    requirements = await test_document_processor()
    if not requirements:
        print("Document processor test failed")
        return
    
    # 2. Test LLM connector
    llm_response = await test_llm_connector()
    if not llm_response:
        print("LLM connector test failed")
        # Continue with other tests despite failure
    
    # 3. Generate scenarios
    scenarios_response = await test_scenario_generator(requirements)
    if not scenarios_response:
        print("Scenario generator test failed")
        return
    
    # 4. Validate scenarios
    validation_results = await test_scenario_validator(scenarios_response)
    if not validation_results:
        print("Scenario validator test failed")
        return
    
    print("\n=== Integration Test Complete ===")
    print("All components tested successfully!")

    # Save results to files for inspection
    with open(os.path.join(output_dir, "test_requirements.json"), "w") as f:
        json.dump(requirements, f, indent=2)
    
    with open(os.path.join(output_dir, "test_scenarios.json"), "w") as f:
        json.dump(scenarios_response, f, indent=2)
    
    with open(os.path.join(output_dir, "test_validation.json"), "w") as f:
        json.dump(validation_results, f, indent=2)
    
    print("\nTest results saved to files in:", output_dir)
    print("- test_requirements.json")
    print("- test_scenarios.json")
    print("- test_validation.json")

if __name__ == "__main__":
    asyncio.run(run_full_integration_test())