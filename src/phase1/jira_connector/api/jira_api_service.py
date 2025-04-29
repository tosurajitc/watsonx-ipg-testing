from fastapi import FastAPI, HTTPException
from phase1.jira_connector.defect_manager import DefectManager
from phase1.jira_connector.jira_auth import JiraAuth
from phase1.jira_connector.jira_parser import JiraParser
from phase1.jira_connector.story_retriever import StoryRetriever
from pydantic import BaseModel
from typing import Optional, Dict, List
import requests
import json

# ------------------------
# FastAPI Setup
# ------------------------

app = FastAPI(title="JIRA Operations REST API", version="1.0")


# ------------------------
# API Models
# ------------------------

class AuthDetails(BaseModel):
    base_url: str
    auth_token: str

class CreateDefectRequest(AuthDetails):
    project_key: str
    summary: str
    description: str
    issue_type: Optional[str] = "Bug"
    priority: Optional[str] = "Medium"

class UpdateDefectRequest(AuthDetails):
    issue_id: str
    fields: Dict

class GetDefectRequest(AuthDetails):
    issue_id: str

class UserStoryRequest(AuthDetails):
    jql: str

class JiraRawDataRequest(BaseModel):
    raw_data: dict

# ------------------------
# Endpoints
# ------------------------

@app.post("/jira/authenticate")
def check_jira_connection(request: AuthDetails, auth_method="api_token"):
    try:
        manager = JiraAuth(request.base_url, request.auth_token)        
        
        if auth_method == "api_token":
            auth = manager.get_jira_auth_token()
            token = auth
        elif auth_method == "oauth":
            access_token = manager.get_jira_oauth_access_token()
            token = access_token
        else:
            raise ValueError("Unsupported authentication method. Choose 'api_token' or 'oauth'.")
        
        return {"status": "success", "token": token}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/jira/create_defect")
def create_defect(request: CreateDefectRequest):
    try:
        manager = DefectManager(request.base_url, request.auth_token)
        result = manager.create_defect(
            project_key=request.project_key,
            summary=request.summary,
            description=request.description,
            issue_type=request.issue_type,
            priority=request.priority
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/jira/update_defect")
def update_defect(request: UpdateDefectRequest):
    try:
        manager = DefectManager(request.base_url, request.auth_token)
        result = manager.update_defect(
            issue_id=request.issue_id,
            fields=request.fields
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jira/get_defect")
def get_defect(base_url: str, auth_token: str, issue_id: str):
    try:
        manager = DefectManager(base_url, auth_token)
        defect = manager.get_defect(issue_id)
        return {"status": "success", "data": defect}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jira/get_user_stories")
def get_user_stories(request: UserStoryRequest):
    try:
        retriever = StoryRetriever(request.base_url, request.auth_token)
        # Define your JQL query (fetch user stories and business cases)
        
        jql_query = """
        project = YOURPROJECTKEY 
        AND issuetype in ("User Story", "Requirement", "Business Case")
        ORDER BY created DESC
        """

        user_stories = retriever.fetch_stories(jql_query, fields=["summary", "description", "issuetype"]) 
        return {"status": "success", "stories": user_stories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jira/parse_data")
def parse_data(request: JiraRawDataRequest):
    try:
        parser = JiraParser(request.raw_data)
        structured_data = parser.parse()
        return {"status": "success", "standardized_data": structured_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

