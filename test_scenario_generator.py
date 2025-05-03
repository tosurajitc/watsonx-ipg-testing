# test_scenario_generator.py
"""
Test module to debug scenario generation issues.

This module adds detailed logging to help identify where 
test scenario generation is failing.

Usage:
    python test_scenario_generator.py "C:\path\to\your\file.docx"
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scenario_debug.log")
    ]
)
logger = logging.getLogger("scenario_debug")

# Add necessary paths to import the required modules
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
src_dir = os.path.join(parent_dir, 'src')
if os.path.exists(src_dir) and src_dir not in sys.path:
    sys.path.insert(0, src_dir)

def is_serializable(obj):
    """Test if an object is JSON serializable."""
    try:
        json.dumps(obj)
        return True, None
    except (TypeError, OverflowError) as e:
        return False, str(e)

async def test_document_processing(file_path):
    """Test document processing."""
    logger.info(f"=== TESTING DOCUMENT PROCESSING: {file_path} ===")
    
    try:
        # Import the document processor
        from src.phase1.llm_test_scenario_generator.document_processor import DocumentProcessor
        
        # Process the document
        logger.info("Creating DocumentProcessor instance")
        doc_processor = DocumentProcessor()
        
        logger.info(f"Processing document: {file_path}")
        requirements = doc_processor.process_document(file_path)
        
        logger.info("Document processed successfully")
        logger.info(f"Requirements type: {type(requirements)}")
        
        # Check if requirements is serializable
        is_req_serializable, error = is_serializable(requirements)
        logger.info(f"Requirements serializable: {is_req_serializable}")
        
        # Log requirements content
        if 'requirements' in requirements:
            logger.info(f"Number of extracted requirements: {len(requirements['requirements'])}")
        if 'user_stories' in requirements:
            logger.info(f"Number of user stories: {len(requirements['user_stories'])}")
        if 'raw_text' in requirements:
            logger.info(f"Raw text length: {len(requirements['raw_text'])}")
        
        return requirements
    except Exception as e:
        logger.error(f"Error in document processing: {str(e)}", exc_info=True)
        return None

async def test_scenario_generation_from_requirements(requirements):
    """Test generating scenarios from requirements."""
    logger.info("=== TESTING SCENARIO GENERATION FROM REQUIREMENTS ===")
    
    try:
        # Import the scenario generator
        from src.phase1.llm_test_scenario_generator.scenario_generator import ScenarioGenerator
        
        # Generate scenarios
        logger.info("Creating ScenarioGenerator instance")
        scenario_generator = ScenarioGenerator()
        
        logger.info("Generating scenarios from requirements")
        scenarios = await scenario_generator.generate_scenarios_from_requirements(
            requirements,
            num_scenarios=3,
            detail_level="medium"
        )
        
        logger.info("Scenarios generated successfully")
        logger.info(f"Scenarios type: {type(scenarios)}")
        
        # Check if scenarios is serializable
        is_scen_serializable, error = is_serializable(scenarios)
        logger.info(f"Scenarios serializable: {is_scen_serializable}")
        
        # Log scenarios content
        if 'scenarios' in scenarios:
            logger.info(f"Number of generated scenarios: {len(scenarios['scenarios'])}")
        
        return scenarios
    except Exception as e:
        logger.error(f"Error in scenario generation from requirements: {str(e)}", exc_info=True)
        return None

async def test_llm_connection():
    """Test LLM connection directly."""
    logger.info("=== TESTING LLM CONNECTION ===")
    
    try:
        # Import the LLM connector
        from src.phase1.llm_test_scenario_generator.llm_connector import LLMConnector
        
        # Create LLM connector
        logger.info("Creating LLMConnector instance")
        llm_connector = LLMConnector()
        
        # Test a simple prompt
        logger.info("Testing simple prompt")
        response = await llm_connector.generate_completion(
            prompt="Generate a simple test scenario for user login functionality",
            system_prompt="You are a test engineer. Generate a basic test scenario."
        )
        
        logger.info("LLM response received successfully")
        
        # Log the response
        if 'text' in response:
            logger.info(f"Response text preview: {response['text'][:100]}...")
        
        return response
    except Exception as e:
        logger.error(f"Error in LLM connection test: {str(e)}", exc_info=True)
        return None

async def run_tests(file_path):
    """Run all tests."""
    
    # Log system info
    logger.info(f"=== TEST STARTED AT {datetime.now().isoformat()} ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"File path: {file_path}")
    logger.info(f"File exists: {os.path.exists(file_path)}")
    
    try:
        # 1. Test document processing
        requirements = await test_document_processing(file_path)
        if requirements is None:
            logger.error("Document processing test failed, cannot continue")
            return
        
        # 2. Test scenario generation from requirements
        req_scenarios = await test_scenario_generation_from_requirements(requirements)
        
        # 3. Test LLM connection
        llm_response = await test_llm_connection()
        
        # Log final results
        logger.info("=== TEST RESULTS SUMMARY ===")
        logger.info(f"Document processing: {'SUCCESS' if requirements else 'FAILED'}")
        logger.info(f"Scenario generation from requirements: {'SUCCESS' if req_scenarios and 'scenarios' in req_scenarios else 'FAILED'}")
        logger.info(f"LLM connection test: {'SUCCESS' if llm_response and 'text' in llm_response else 'FAILED'}")
        
        # Results summary for display
        print("\n=== TEST RESULTS SUMMARY ===")
        print(f"Document processing: {'SUCCESS' if requirements else 'FAILED'}")
        print(f"  - Requirements found: {len(requirements.get('requirements', []))}")
        print(f"  - User stories found: {len(requirements.get('user_stories', []))}")
        print(f"  - Has raw text: {'Yes' if 'raw_text' in requirements else 'No'}")
        print(f"Scenario generation: {'SUCCESS' if req_scenarios and 'scenarios' in req_scenarios else 'FAILED'}")
        print(f"  - Scenarios generated: {len(req_scenarios.get('scenarios', [])) if req_scenarios else 0}")
        print(f"LLM connection: {'SUCCESS' if llm_response and 'text' in llm_response else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"Error in test execution: {str(e)}", exc_info=True)
    finally:
        logger.info(f"=== TEST ENDED AT {datetime.now().isoformat()} ===")

if __name__ == "__main__":
    # Simplified argument handling - get the file path directly
    if len(sys.argv) < 2:
        print("Usage: python test_scenario_generator.py <file_path>")
        sys.exit(1)
    
    # Get the file path (handles paths with spaces properly)
    file_path = sys.argv[1]
    
    # Run the tests
    asyncio.run(run_tests(file_path))