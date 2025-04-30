from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the requirements API router
from src.phase1.llm_test_scenario_generator.api.requirements_api_service import include_router

app = FastAPI(title="Watsonx IPG Testing API")

# Add CORS middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the requirements router
include_router(app)

# Optional: Add a health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}