"""
Scenario API Service Module for the LLM Test Scenario Generator.

This module implements REST API endpoints for the scenario generation service.
It provides interfaces for generating, validating, and managing test scenarios.

Usage:
    # Run using FastAPI's uvicorn server
    uvicorn api.scenario_api_service:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import logging
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Union, Optional, Tuple

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends, Query, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import local modules (relative imports)
import sys
import os
# Add parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_test_scenario_generator.document_processor import DocumentProcessor
from llm_test_scenario_generator.llm_connector import LLMConnector
from llm_test_scenario_generator.scenario_generator import ScenarioGenerator
from llm_test_scenario_generator.scenario_validator import ScenarioValidator


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scenario_api.log")
    ]
)
logger = logging.getLogger("scenario_api")

# Initialize FastAPI app
app = FastAPI(
    title="Test Scenario Generator API",
    description="API for generating and validating test scenarios from requirements",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation

class RequirementModel(BaseModel):
    """Model for a single requirement."""
    id: Optional[str] = None
    text: str
    type: Optional[str] = "functional"
    priority: Optional[str] = None

class UserStoryModel(BaseModel):
    """Model for a user story."""
    role: str
    goal: str
    benefit: Optional[str] = None
    full_text: Optional[str] = None

class RequirementsModel(BaseModel):
    """Model for requirements input."""
    requirements: Optional[List[RequirementModel]] = []
    user_stories: Optional[List[UserStoryModel]] = []
    acceptance_criteria: Optional[List[str]] = []
    document_type: Optional[str] = "manual"
    raw_text: Optional[str] = None

class ScenarioGenerationConfigModel(BaseModel):
    """Model for scenario generation configuration."""
    num_scenarios: Optional[int] = 5
    detail_level: Optional[str] = "medium"
    priority_focus: Optional[str] = None
    custom_focus: Optional[List[str]] = None

class ValidationConfigModel(BaseModel):
    """Model for validation configuration."""
    strict_mode: Optional[bool] = False
    quality_threshold: Optional[float] = 0.7

class TestScenarioModel(BaseModel):
    """Model for a test scenario."""
    id: str
    title: str
    description: str
    priority: Optional[str] = None
    related_requirements: Optional[Union[List[str], str]] = None
    test_type: Optional[str] = None
    generation_timestamp: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    coverage: Optional[Dict[str, Any]] = None

class GenerationResponseModel(BaseModel):
    """Model for generation response."""
    scenarios: List[TestScenarioModel]
    metadata: Dict[str, Any]
    raw_llm_response: Optional[str] = None

class ValidationResponseModel(BaseModel):
    """Model for validation response."""
    valid: bool
    scenarios: List[Dict[str, Any]]
    metrics: Dict[str, Any]


# Global service instances
_document_processor = None
_scenario_generator = None
_scenario_validator = None

# Dependency injection for services
def get_document_processor():
    """Get or create document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor

def get_scenario_generator():
    """Get or create scenario generator instance."""
    global _scenario_generator
    if _scenario_generator is None:
        _scenario_generator = ScenarioGenerator()
    return _scenario_generator

def get_scenario_validator():
    """Get or create scenario validator instance."""
    global _scenario_validator
    if _scenario_validator is None:
        _scenario_validator = ScenarioValidator()
    return _scenario_validator


# Helper functions

async def process_uploaded_file(file: UploadFile) -> Dict[str, Any]:
    """
    Process an uploaded file to extract requirements.
    
    Args:
        file: Uploaded file
        
    Returns:
        Extracted requirements data
    """
    # Create temporary file to save the upload
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        temp_file_path = temp_file.name
        # Write uploaded file content to temporary file
        content = await file.read()
        temp_file.write(content)
    
    try:
        # Process the document
        processor = get_document_processor()
        requirements = processor.process_document(temp_file_path)
        return requirements
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


# API Routes

@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Test Scenario Generator API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/process-document", response_model=Dict[str, Any])
async def process_document(file: UploadFile = File(...)):
    """
    Process a document to extract requirements.
    
    Args:
        file: Uploaded document file
        
    Returns:
        Extracted requirements data
    """
    logger.info(f"Processing document: {file.filename}")
    
    try:
        requirements = await process_uploaded_file(file)
        return requirements
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/api/generate-from-document", response_model=GenerationResponseModel)
async def generate_from_document(
    config: ScenarioGenerationConfigModel = Depends(),
    file: UploadFile = File(...),
    generator: ScenarioGenerator = Depends(get_scenario_generator)
):
    """
    Generate test scenarios directly from a document.
    
    Args:
        config: Generation configuration
        file: Uploaded document file
        generator: Scenario generator instance
        
    Returns:
        Generated test scenarios
    """
    logger.info(f"Generating scenarios from document: {file.filename}")
    
    try:
        # Process uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            # Write uploaded file content to temporary file
            content = await file.read()
            temp_file.write(content)
        
        try:
            # Generate scenarios
            response = await generator.generate_scenarios_from_document(
                temp_file_path,
                num_scenarios=config.num_scenarios,
                detail_level=config.detail_level,
                priority_focus=config.priority_focus,
                custom_focus=config.custom_focus
            )
            return response
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error generating scenarios from document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating scenarios: {str(e)}")

@app.post("/api/generate-from-requirements", response_model=GenerationResponseModel)
async def generate_from_requirements(
    requirements: RequirementsModel,
    config: ScenarioGenerationConfigModel = Depends(),
    generator: ScenarioGenerator = Depends(get_scenario_generator)
):
    """
    Generate test scenarios from structured requirements data.
    
    Args:
        requirements: Requirements data
        config: Generation configuration
        generator: Scenario generator instance
        
    Returns:
        Generated test scenarios
    """
    logger.info("Generating scenarios from requirements data")
    
    try:
        # Convert pydantic model to dict
        requirements_dict = requirements.dict()
        
        # Generate scenarios
        response = await generator.generate_scenarios_from_requirements(
            requirements_dict,
            num_scenarios=config.num_scenarios,
            detail_level=config.detail_level,
            priority_focus=config.priority_focus,
            custom_focus=config.custom_focus
        )
        return response
    except Exception as e:
        logger.error(f"Error generating scenarios from requirements: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating scenarios: {str(e)}")

@app.post("/api/generate-from-text", response_model=GenerationResponseModel)
async def generate_from_text(
    text: str = Body(..., embed=True),
    config: ScenarioGenerationConfigModel = Depends(),
    generator: ScenarioGenerator = Depends(get_scenario_generator)
):
    """
    Generate test scenarios from raw text.
    
    Args:
        text: Raw text containing requirements
        config: Generation configuration
        generator: Scenario generator instance
        
    Returns:
        Generated test scenarios
    """
    logger.info("Generating scenarios from raw text")
    
    try:
        # Generate scenarios
        response = await generator.generate_scenarios_from_text(
            text,
            num_scenarios=config.num_scenarios,
            detail_level=config.detail_level,
            priority_focus=config.priority_focus,
            custom_focus=config.custom_focus
        )
        return response
    except Exception as e:
        logger.error(f"Error generating scenarios from text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating scenarios: {str(e)}")

@app.post("/api/validate-scenarios", response_model=ValidationResponseModel)
async def validate_scenarios(
    scenarios: List[TestScenarioModel],
    requirements: Optional[RequirementsModel] = None,
    config: ValidationConfigModel = Depends(),
    validator: ScenarioValidator = Depends(get_scenario_validator)
):
    """
    Validate test scenarios for completeness and testability.
    
    Args:
        scenarios: List of test scenarios to validate
        requirements: Optional requirements data for cross-validation
        config: Validation configuration
        validator: Scenario validator instance
        
    Returns:
        Validation results
    """
    logger.info(f"Validating {len(scenarios)} test scenarios")
    
    try:
        # Convert pydantic models to dicts
        scenarios_dict = [scenario.dict() for scenario in scenarios]
        requirements_dict = requirements.dict() if requirements else None
        
        # Validate scenarios
        validation_results = validator.validate_scenarios(
            scenarios_dict,
            requirements=requirements_dict,
            strict_mode=config.strict_mode
        )
        return validation_results
    except Exception as e:
        logger.error(f"Error validating scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating scenarios: {str(e)}")

@app.post("/api/suggest-improvements", response_model=Dict[str, List[str]])
async def suggest_improvements(
    scenario: TestScenarioModel,
    validator: ScenarioValidator = Depends(get_scenario_validator)
):
    """
    Suggest improvements for a test scenario.
    
    Args:
        scenario: Test scenario
        validator: Scenario validator instance
        
    Returns:
        List of improvement suggestions
    """
    logger.info(f"Suggesting improvements for scenario: {scenario.id}")
    
    try:
        # Validate the scenario
        scenario_dict = scenario.dict()
        validation_result = validator.validate_scenario(scenario_dict)
        
        # Get improvement suggestions
        suggestions = validator.suggest_improvements(scenario_dict, validation_result)
        
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error suggesting improvements: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error suggesting improvements: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Run the application if executed directly
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("API_DEBUG", "False").lower() in ("true", "1", "t")
    
    logger.info(f"Starting API server on {host}:{port} (debug={debug})")
    uvicorn.run("scenario_api_service:app", host=host, port=port, reload=debug)