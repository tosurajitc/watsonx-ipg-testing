# Coding Standards

## Table of Contents

- [Introduction](#introduction)
- [Python Coding Standards](#python-coding-standards)
  - [Code Formatting](#code-formatting)
  - [Import Conventions](#import-conventions)
  - [Naming Conventions](#naming-conventions)
  - [Documentation](#documentation)
  - [Type Hints](#type-hints)
  - [Error Handling](#error-handling)
  - [Testing](#testing)
- [API Design](#api-design)
  - [RESTful API Conventions](#restful-api-conventions)
  - [API Documentation](#api-documentation)
  - [API Versioning](#api-versioning)
  - [Error Responses](#error-responses)
- [Database Practices](#database-practices)
  - [SQL Guidelines](#sql-guidelines)
  - [ORM Usage](#orm-usage)
  - [Migration Practices](#migration-practices)
- [Streamlit UI Practices](#streamlit-ui-practices)
  - [Component Organization](#component-organization)
  - [State Management](#state-management)
  - [UI Consistency](#ui-consistency)
- [Security Practices](#security-practices)
  - [Authentication and Authorization](#authentication-and-authorization)
  - [Data Protection](#data-protection)
  - [Secure Coding](#secure-coding)
- [Logging](#logging)
- [Performance Considerations](#performance-considerations)
- [Code Review Process](#code-review-process)
- [Version Control](#version-control)
  - [Branching Strategy](#branching-strategy)
  - [Commit Conventions](#commit-conventions)
  - [Pull Request Process](#pull-request-process)
- [CI/CD Integration](#cicd-integration)
- [Appendix: Tools and Resources](#appendix-tools-and-resources)

## Introduction

This document establishes the coding standards and best practices for the Watsonx for IPG Testing project. Adherence to these standards will ensure code quality, maintainability, and consistency across the project. These standards apply to all developers contributing to the codebase.

The primary goals of these standards are to:

1. Enhance code readability and maintainability
2. Promote code reuse and modularity
3. Ensure security and performance best practices
4. Facilitate collaboration among team members
5. Support the long-term evolution of the project

## Python Coding Standards

### Code Formatting

- **PEP 8**: Follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code.
- **Line Length**: Maximum line length is 88 characters (following Black's default).
- **Indentation**: Use 4 spaces for indentation, not tabs.
- **Formatters**: Use Black as the code formatter to ensure consistency.
- **Linting**: Use flake8 for linting with the following configuration:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203
```

- **Pre-commit Hooks**: Use pre-commit hooks to automatically check and format code before commits.

Example pre-commit configuration:

```yaml
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files

-   repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
    -   id: black

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-docstrings]
```

### Import Conventions

- Group imports in the following order, separated by a blank line:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports

```python
# Standard library imports
import json
import os
from datetime import datetime

# Third-party imports
import fastapi
import pydantic
import sqlalchemy

# Local application imports
from src.common.utils import file_utils
from src.phase1.jira_connector import jira_auth
```

- Avoid using `from module import *` as it creates unclear dependencies.
- Prefer absolute imports over relative imports.

### Naming Conventions

- **Variables, Functions, Methods**: Use `snake_case` for variables, functions, and methods.
- **Classes**: Use `PascalCase` for class names.
- **Constants**: Use `UPPER_CASE_WITH_UNDERSCORES` for constants.
- **Modules**: Use `lowercase_with_underscores` for module names.
- **Private Members**: Prefix private attributes and methods with a single underscore.
- **Name Clarity**: Choose descriptive names that communicate intent. Avoid abbreviations unless they are well-known.

```python
# Constants
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30

# Classes
class TestCaseGenerator:
    def __init__(self, config_path):
        self._config = self._load_config(config_path)  # Private attribute
    
    def _load_config(self, path):  # Private method
        """Load configuration from the specified path."""
        pass
    
    def generate_test_cases(self, scenarios):
        """Generate test cases from the provided scenarios."""
        pass
```

### Documentation

- **Docstrings**: Use Google-style docstrings for all modules, classes, methods, and functions.
- **Module Docstrings**: Include a docstring at the top of each module describing its purpose.
- **Function and Method Docstrings**: Include a description, Args, Returns, and Raises sections as applicable.

```python
def analyze_test_coverage(test_cases, requirements, threshold=0.8):
    """
    Analyze test coverage against requirements.
    
    Args:
        test_cases (List[TestCase]): List of test cases to analyze.
        requirements (List[Requirement]): List of requirements to check coverage against.
        threshold (float, optional): Minimum match score to consider a requirement covered.
            Defaults to 0.8.
    
    Returns:
        CoverageAnalysis: Object containing coverage metrics and gaps.
    
    Raises:
        ValueError: If threshold is not between 0 and 1.
    """
```

- **Comments**: Use comments sparingly and only to explain complex logic that isn't self-evident from the code.
- **TODO Comments**: Use `# TODO: description` format for temporary code or future improvement markers. Include a ticket reference when applicable.

### Type Hints

- Use type hints for function and method signatures.
- Use the typing module for complex types.
- For optional parameters, use Optional[type].

```python
from typing import Dict, List, Optional, Union

def process_test_results(
    results: List[Dict[str, Union[str, int]]],
    output_format: str = "json",
    include_details: Optional[bool] = None
) -> Dict[str, any]:
    """Process test results."""
    pass
```

### Error Handling

- Use specific exception types instead of catching generic exceptions.
- Create custom exception classes for application-specific errors.
- Include meaningful error messages that help with debugging.
- Log exceptions with appropriate context.

```python
class TestDataError(Exception):
    """Raised when there's an issue with test data processing."""
    pass

def validate_test_data(data_file):
    """Validate test data from file."""
    try:
        content = load_file(data_file)
        if not is_valid_format(content):
            raise TestDataError(f"Invalid data format in {data_file}")
        # Process file
    except FileNotFoundError:
        logger.error(f"Test data file not found: {data_file}")
        raise TestDataError(f"Test data file not found: {data_file}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in test data file {data_file}: {str(e)}")
        raise TestDataError(f"Invalid JSON in test data file: {str(e)}")
```

### Testing

- Use pytest as the testing framework.
- Write tests for all public functions and methods.
- Use fixtures to set up test data.
- Mock external dependencies.
- Aim for high test coverage (minimum 80%).
- Organize tests to mirror the structure of the source code.

```python
# tests/phase1/test_jira_connector.py
import pytest
from unittest.mock import Mock, patch
from src.phase1.jira_connector.story_retriever import StoryRetriever

@pytest.fixture
def mock_jira_client():
    """Create a mock JIRA client for testing."""
    client = Mock()
    client.search_issues.return_value = [
        Mock(key="JIRA-123", fields=Mock(summary="Test Story"))
    ]
    return client

def test_get_stories_by_project(mock_jira_client):
    """Test retrieving stories by project."""
    retriever = StoryRetriever(mock_jira_client)
    stories = retriever.get_stories_by_project("TEST")
    
    assert len(stories) == 1
    assert stories[0].key == "JIRA-123"
    assert stories[0].summary == "Test Story"
    mock_jira_client.search_issues.assert_called_once()
```

## API Design

### RESTful API Conventions

- Use resource-oriented URLs.
- Use HTTP methods appropriately:
  - GET for retrieving resources
  - POST for creating resources
  - PUT for updating resources
  - DELETE for removing resources
  - PATCH for partial updates
- Use appropriate HTTP status codes.

```
# Good API Endpoints
GET /api/v1/test-cases
GET /api/v1/test-cases/{id}
POST /api/v1/test-cases
PUT /api/v1/test-cases/{id}
DELETE /api/v1/test-cases/{id}

# Avoid
GET /api/v1/getTestCases
POST /api/v1/createTestCase
```

### API Documentation

- Document all API endpoints using OpenAPI/Swagger.
- Include descriptions, parameters, request/response schemas, and examples.
- Document error responses and codes.

Example FastAPI route with documentation:

```python
@router.post(
    "/test-cases",
    response_model=TestCaseResponse,
    status_code=201,
    summary="Create a new test case",
    description="Creates a new test case based on the provided data.",
    responses={
        201: {"description": "Test case created successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Unauthorized"},
    },
)
async def create_test_case(
    test_case: TestCaseCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new test case with the given data.
    
    The test case will be assigned to the current user by default.
    """
    result = test_case_service.create_test_case(test_case, current_user.id)
    return result
```

### API Versioning

- Include a version in the API path (e.g., `/api/v1/resources`).
- Maintain backward compatibility within a version.
- Document breaking changes between versions.

### Error Responses

- Use consistent error response format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "string or object"
  }
}
```

- Include appropriate HTTP status codes.
- Provide user-friendly error messages.

## Database Practices

### SQL Guidelines

- Use prepared statements to prevent SQL injection.
- Use explicit column names in queries instead of `SELECT *`.
- Create appropriate indexes for query optimization.
- Use transactions for operations that require atomicity.

### ORM Usage

- Use SQLAlchemy as the ORM.
- Define models in dedicated files.
- Use relationships to represent connections between entities.
- Use migrations for database schema changes.

```python
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    owner = relationship("User", back_populates="test_cases")
    steps = relationship("TestStep", back_populates="test_case", cascade="all, delete-orphan")
```

### Migration Practices

- Use Alembic for database migrations.
- Create migration scripts for each schema change.
- Test migrations on development environments before applying to production.
- Include both upgrade and downgrade scripts.

## Streamlit UI Practices

### Component Organization

- Organize Streamlit components by feature or page.
- Create reusable component functions.
- Use session state for maintaining state between reruns.

```python
def display_test_case_detail(test_case_id):
    """Display detailed view of a test case."""
    test_case = get_test_case(test_case_id)
    
    st.header(test_case.title)
    st.write(f"**Description**: {test_case.description}")
    
    st.subheader("Test Steps")
    for step in test_case.steps:
        with st.expander(f"Step {step.order}: {step.action[:50]}..."):
            st.write(f"**Action**: {step.action}")
            st.write(f"**Expected Result**: {step.expected_result}")
```

### State Management

- Use session state to store user data and UI state.
- Initialize session state keys at the start of the application.
- Use callbacks for state updates.

```python
def initialize_session_state():
    """Initialize session state variables."""
    if 'selected_test_case' not in st.session_state:
        st.session_state.selected_test_case = None
    if 'filter_criteria' not in st.session_state:
        st.session_state.filter_criteria = {}

def main():
    initialize_session_state()
    # Application UI
```

### UI Consistency

- Maintain consistent styling across pages.
- Use Streamlit themes for consistent appearance.
- Create helper functions for repeated UI patterns.

```python
def show_status_indicator(status):
    """Display a consistent status indicator based on status value."""
    if status == "Passed":
        st.success("Passed")
    elif status == "Failed":
        st.error("Failed")
    elif status == "Running":
        st.info("Running")
    else:
        st.warning(status)
```

## Security Practices

### Authentication and Authorization

- Use IBM Cloud IAM for authentication.
- Implement role-based access control.
- Use OAuth 2.0 for API authentication.
- Never store plain-text passwords or secrets.

### Data Protection

- Use encryption for sensitive data storage.
- Use HTTPS for all communications.
- Implement proper input validation.
- Apply the principle of least privilege.

### Secure Coding

- Sanitize all user inputs.
- Use secure dependencies and keep them updated.
- Implement rate limiting for APIs.
- Conduct regular security reviews.

```python
# Example of input validation
def process_user_input(input_data: str) -> str:
    """Process and sanitize user input."""
    # Validate input length
    if len(input_data) > 1000:
        raise ValueError("Input exceeds maximum allowed length")
    
    # Sanitize HTML/script content
    sanitized = html.escape(input_data)
    
    # Additional processing
    return sanitized
```

## Logging

- Use the Python logging module.
- Configure appropriate log levels based on environment.
- Include contextual information in log messages.
- Avoid logging sensitive information.

```python
import logging

# Module-level logger
logger = logging.getLogger(__name__)

def process_data(data, user_id):
    """Process data for the given user."""
    logger.info(f"Processing data for user {user_id}")
    try:
        result = transform_data(data)
        logger.debug(f"Data transformation complete for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Error processing data for user {user_id}: {str(e)}", exc_info=True)
        raise
```

## Performance Considerations

- Use connection pooling for database connections.
- Implement caching for expensive operations.
- Use pagination for large data sets.
- Profile code to identify bottlenecks.
- Consider async operations for I/O-bound tasks.

```python
# Example of paginated API endpoint
@router.get("/test-cases", response_model=List[TestCaseResponse])
async def get_test_cases(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
):
    """Get a paginated list of test cases."""
    return test_case_service.get_test_cases(skip=skip, limit=limit)
```

## Code Review Process

- All code changes must go through code review.
- Reviewers should check for:
  - Adherence to coding standards
  - Potential bugs and errors
  - Security vulnerabilities
  - Performance issues
  - Test coverage
- Address all comments before merging.

## Version Control

### Branching Strategy

- Use a feature branching workflow:
  - `main`: Production-ready code
  - `develop`: Integration branch for features
  - `feature/*`: Feature branches
  - `bugfix/*`: Bug fix branches
  - `release/*`: Release preparation branches

### Commit Conventions

- Use conventional commits format:
  - `feat: Add new feature`
  - `fix: Fix bug in component`
  - `chore: Update dependencies`
  - `docs: Update documentation`
  - `refactor: Refactor component`
  - `test: Add tests for component`

### Pull Request Process

1. Create a PR with a descriptive title and description.
2. Link related issues.
3. Ensure CI checks pass.
4. Request reviews from appropriate team members.
5. Address review comments.
6. Merge after approval.

## CI/CD Integration

- Use GitHub Actions for CI/CD pipeline.
- Run the following checks automatically:
  - Code linting (flake8)
  - Code formatting (black)
  - Type checking (mypy)
  - Unit tests (pytest)
  - Security scanning
- Deploy automatically to development after successful CI.
- Deploy to production through a manual approval process.

## Appendix: Tools and Resources

### Recommended Tools

- **Code Formatting**: Black
- **Linting**: flake8, pylint
- **Testing**: pytest
- **Type Checking**: mypy
- **Documentation**: Sphinx
- **Pre-commit Hooks**: pre-commit
- **Database ORM**: SQLAlchemy
- **API Framework**: FastAPI
- **UI Framework**: Streamlit

### Resources

- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Python Testing with pytest](https://pragprog.com/titles/bopytest/python-testing-with-pytest/)