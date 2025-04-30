from fastapi import (
    APIRouter, 
    File, 
    UploadFile, 
    Form, 
    HTTPException, 
    Depends
)
from typing import Optional, Dict, Any
import io
import logging

# Import existing processors
from ..document_processor import DocumentProcessor
from ..scenario_generator import ScenarioGenerator
from ...jira_connector.story_retriever import StoryRetriever
from ...jira_connector.jira_auth import JiraAuth

# Configure logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/requirements", tags=["Requirements"])

# Initialize processors
doc_processor = DocumentProcessor()
scenario_generator = ScenarioGenerator()

@router.post("/manual-input")
async def process_manual_requirements(
    requirements_text: str = Form(...)
) -> Dict[str, Any]:
    """
    Process manually entered requirements text.
    
    Args:
        requirements_text (str): Requirements text input by user
    
    Returns:
        Dict containing processed requirements and generated scenarios
    """
    try:
        # Process raw text input
        requirements = doc_processor.process_raw_input(requirements_text)
        
        # Generate scenarios
        scenarios = await scenario_generator.generate_scenarios_from_text(
            requirements_text, 
            num_scenarios=5
        )
        
        return {
            "status": "success",
            "requirements": requirements,
            "scenarios": scenarios
        }
    except Exception as e:
        logger.error(f"Error processing manual requirements: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/file-upload")
async def process_requirements_file(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Process uploaded requirements file.
    
    Args:
        file (UploadFile): Uploaded file containing requirements
    
    Returns:
        Dict containing processed file requirements and generated scenarios
    """
    # Validate file size (10MB limit)
    file_size = await file.read()
    if len(file_size) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Max 10MB allowed.")
    
    try:
        # Temporarily save file
        file_bytes = io.BytesIO(file_size)
        
        # Process file using document processor
        requirements = doc_processor.process_document(file_bytes)
        
        # Generate scenarios from file content
        scenarios = await scenario_generator.generate_scenarios_from_document(
            file_bytes, 
            num_scenarios=5
        )
        
        return {
            "status": "success",
            "filename": file.filename,
            "requirements": requirements,
            "scenarios": scenarios
        }
    except Exception as e:
        logger.error(f"Error processing requirements file: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/jira-requirements")
async def fetch_jira_requirements(
    url: str = Form(...),
    project_key: str = Form(...),
    api_token: str = Form(...)
) -> Dict[str, Any]:
    """
    Fetch requirements from JIRA.
    
    Args:
        url (str): JIRA instance URL
        project_key (str): JIRA project key
        api_token (str): JIRA API token
    
    Returns:
        Dict containing JIRA requirements and generated scenarios
    """
    try:
        # Authenticate with JIRA
        auth = JiraAuth()
        auth_token = auth.get_jira_auth_token(url, api_token)
        
        # Retrieve stories
        retriever = StoryRetriever(url, auth_token)
        
        # Define JQL to fetch requirements
        jql_query = f"project = {project_key} AND issuetype in ('User Story', 'Requirement')"
        
        # Fetch requirements
        raw_requirements = retriever.fetch_stories(jql_query)
        
        # Parse requirements
        parsed_requirements = doc_processor.process_jira_export(raw_requirements)
        
        # Generate scenarios
        scenarios = await scenario_generator.generate_scenarios_from_jira(
            raw_requirements, 
            num_scenarios=5
        )
        
        return {
            "status": "success",
            "project_key": project_key,
            "requirements": parsed_requirements,
            "scenarios": scenarios
        }
    except Exception as e:
        logger.error(f"Error fetching JIRA requirements: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Function to include router in main FastAPI app
def include_router(app):
    app.include_router(router)