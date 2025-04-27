from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Import the core analysis modules
from match_classifier import TestCaseMatchClassifier
from comparison_engine import compare_test_cases, analyze_test_case_coverage
from gap_analyzer import TestCoverageGapAnalyzer

# Pydantic models for request validation
class TestCaseModel(BaseModel):
    task_id: Optional[str] = None
    task_name: str
    description: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    requirement_mapping: Optional[str] = None

class CoverageAnalysisRequest(BaseModel):
    new_test_cases: List[TestCaseModel]
    existing_test_cases: Optional[List[TestCaseModel]] = None
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class GapAnalysisRequest(BaseModel):
    requirements_file: Optional[str] = None
    test_cases_file: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="Test Coverage Analysis API",
    description="API for analyzing test case coverage, matching, and gap identification",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Dependency to get match classifier
def get_match_classifier():
    return TestCaseMatchClassifier()

@app.post("/api/v1/coverage/compare", 
          response_model=Dict[str, Any], 
          summary="Compare Test Cases")
async def compare_test_cases_endpoint(
    request: CoverageAnalysisRequest,
    classifier: TestCaseMatchClassifier = Depends(get_match_classifier)
):
    """
    Compare new test cases against existing test cases
    
    - Analyzes similarity between new and existing test cases
    - Provides match classifications and recommendations
    """
    try:
        # Prepare test cases (convert Pydantic models to dictionaries)
        new_test_cases = [case.dict() for case in request.new_test_cases]
        existing_test_cases = [case.dict() for case in request.existing_test_cases] if request.existing_test_cases else []
        
        # Perform comprehensive coverage analysis
        coverage_results = analyze_test_case_coverage(
            new_test_cases, 
            existing_test_cases, 
            request.similarity_threshold
        )
        
        # Generate detailed recommendations for each new test case
        detailed_recommendations = []
        for new_case in new_test_cases:
            # Find matches for this specific test case
            case_matches = compare_test_cases(
                new_case, 
                existing_test_cases, 
                request.similarity_threshold
            )
            
            # Generate recommendations
            recommendations = classifier.generate_match_recommendations(
                new_case, 
                case_matches
            )
            
            detailed_recommendations.append({
                'new_case': new_case,
                'recommendations': recommendations
            })
        
        # Combine results
        return {
            "coverage_analysis": coverage_results,
            "detailed_recommendations": detailed_recommendations
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/coverage/gap-analysis", 
          response_model=Dict[str, Any], 
          summary="Perform Gap Analysis")
async def gap_analysis_endpoint(
    request: GapAnalysisRequest
):
    """
    Perform comprehensive gap analysis on test cases and requirements
    
    - Identifies coverage gaps
    - Generates recommendations for improving test coverage
    """
    try:
        # Initialize Gap Analyzer with optional file paths
        gap_analyzer = TestCoverageGapAnalyzer(
            requirements_file=request.requirements_file,
            test_cases_file=request.test_cases_file
        )
        
        # Perform overall coverage analysis
        coverage_analysis = gap_analyzer.analyze_overall_coverage()
        
        # Generate gap recommendations
        gap_recommendations = gap_analyzer.generate_gap_recommendations()
        
        return {
            "coverage_analysis": coverage_analysis,
            "gap_recommendations": gap_recommendations
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/coverage/upload-file", 
          summary="Upload Test Cases or Requirements File")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Query(..., description="Type of file: 'requirements' or 'test_cases'")
):
    """
    Upload a CSV file for test cases or requirements
    
    - Supports uploading requirements or test cases files
    - Validates and stores the uploaded file
    """
    try:
        # Validate file type
        if file_type not in ['requirements', 'test_cases']:
            raise HTTPException(status_code=400, detail="Invalid file type. Must be 'requirements' or 'test_cases'")
        
        # Read file contents
        contents = await file.read()
        
        # Generate a unique filename
        import uuid
        filename = f"{file_type}_{uuid.uuid4()}.csv"
        
        # Save file to a designated upload directory
        upload_path = f"uploads/{filename}"
        with open(upload_path, "wb") as f:
            f.write(contents)
        
        return {
            "message": "File uploaded successfully",
            "filename": filename,
            "file_type": file_type
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health", summary="Health Check")
async def health_check():
    """
    Simple health check endpoint
    
    - Confirms the API is up and running
    """
    return {"status": "healthy", "message": "Coverage Analysis API is operational"}

# Example of running the service (typically in a separate script)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)