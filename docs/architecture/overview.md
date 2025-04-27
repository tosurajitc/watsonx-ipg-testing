# Watsonx for IPG Testing - Phase 1 APIs

This document provides a comprehensive overview of the API endpoints available in Phase 1 of the Watsonx for IPG Testing platform. These APIs enable integration between different system components and provide interfaces for external systems to interact with the platform.

## Table of Contents

- [Authentication](#authentication)
- [JIRA Connector API](#jira-connector-api)
- [LLM Test Scenario Generator API](#llm-test-scenario-generator-api)
- [Test Case Manager API](#test-case-manager-api)
- [SharePoint Connector API](#sharepoint-connector-api)
- [Coverage Analyzer API](#coverage-analyzer-api)
- [Streamlit UI API](#streamlit-ui-api)
- [System Configuration API](#system-configuration-api)
- [Test Data Manager API](#test-data-manager-api)
- [Notification Service API](#notification-service-api)
- [Cross-Module API Examples](#cross-module-api-examples)

## Authentication

All API endpoints require authentication through a JSON Web Token (JWT).

### Get Authentication Token

```
POST /api/v1/auth/token
```

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "access_token": "string",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Usage Example**:
```bash
curl -X POST "https://ipg-testing-api.example.com/api/v1/auth/token" \
     -H "Content-Type: application/json" \
     -d '{"username": "user@example.com", "password": "password123"}'
```

All subsequent API calls should include the Authorization header:
```
Authorization: Bearer {access_token}
```

---

## JIRA Connector API

The JIRA Connector API enables retrieving user stories, requirements, and business cases from JIRA, as well as creating and managing defects.

### Endpoints

#### Get User Stories

```
GET /api/v1/jira/stories
```

**Query Parameters**:
```
project: string (required) - JIRA project key
status: string - Filter by status (e.g., "Open", "In Progress")
sprint: string - Filter by sprint name
limit: integer - Maximum number of stories to return (default: 20)
offset: integer - Pagination offset (default: 0)
```

**Response**:
```json
{
  "stories": [
    {
      "id": "string",
      "key": "string",
      "summary": "string",
      "description": "string",
      "status": "string",
      "created_at": "datetime",
      "updated_at": "datetime",
      "assignee": "string",
      "reporter": "string",
      "sprint": "string",
      "story_points": "number",
      "acceptance_criteria": "string",
      "labels": ["string"]
    }
  ],
  "total": "integer",
  "offset": "integer",
  "limit": "integer"
}
```

#### Create Defect

```
POST /api/v1/jira/defects
```

**Request Body**:
```json
{
  "project": "string",
  "summary": "string",
  "description": "string",
  "priority": "string",
  "severity": "string",
  "steps_to_reproduce": "string",
  "environment": "string",
  "attachments": ["binary"],
  "assignee": "string",
  "labels": ["string"]
}
```

**Response**:
```json
{
  "id": "string",
  "key": "string",
  "url": "string",
  "status": "Created"
}
```

#### Get Defect Status

```
GET /api/v1/jira/defects/{defect_id}
```

**Path Parameters**:
```
defect_id: string (required) - The JIRA defect ID
```

**Response**:
```json
{
  "id": "string",
  "key": "string",
  "summary": "string",
  "description": "string",
  "status": "string",
  "priority": "string",
  "severity": "string",
  "assignee": "string",
  "reporter": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "comments": [
    {
      "id": "string",
      "author": "string",
      "body": "string",
      "created_at": "datetime"
    }
  ]
}
```

#### Update Defect

```
PUT /api/v1/jira/defects/{defect_id}
```

**Path Parameters**:
```
defect_id: string (required) - The JIRA defect ID
```

**Request Body**:
```json
{
  "summary": "string",
  "description": "string",
  "priority": "string",
  "severity": "string",
  "status": "string",
  "assignee": "string"
}
```

**Response**:
```json
{
  "id": "string",
  "key": "string",
  "status": "Updated"
}
```

---

## LLM Test Scenario Generator API

The LLM Test Scenario Generator API enables generating test scenarios from various input sources using the watsonx LLM.

### Endpoints

#### Generate Test Scenarios from JIRA Story

```
POST /api/v1/llm/generate/scenarios/jira
```

**Request Body**:
```json
{
  "story_key": "string",
  "detail_level": "enum(high, medium, low)",
  "coverage_focus": ["string"],
  "max_scenarios": "integer"
}
```

**Response**:
```json
{
  "request_id": "string",
  "scenarios": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "preconditions": "string",
      "expected_behavior": "string",
      "coverage_areas": ["string"],
      "priority": "enum(high, medium, low)",
      "source_story_key": "string"
    }
  ],
  "completion_status": "string",
  "processing_time": "number"
}
```

#### Generate Test Scenarios from Document

```
POST /api/v1/llm/generate/scenarios/document
```

**Request Body**:
```
multipart/form-data
- file: binary (required)
- detail_level: string (enum: high, medium, low)
- coverage_focus: string (comma-separated list)
- max_scenarios: integer
```

**Response**:
```json
{
  "request_id": "string",
  "scenarios": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "preconditions": "string",
      "expected_behavior": "string",
      "coverage_areas": ["string"],
      "priority": "enum(high, medium, low)",
      "source_document": "string"
    }
  ],
  "completion_status": "string",
  "processing_time": "number"
}
```

#### Generate Test Scenarios from Text

```
POST /api/v1/llm/generate/scenarios/text
```

**Request Body**:
```json
{
  "text": "string",
  "detail_level": "enum(high, medium, low)",
  "coverage_focus": ["string"],
  "max_scenarios": "integer"
}
```

**Response**:
```json
{
  "request_id": "string",
  "scenarios": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "preconditions": "string",
      "expected_behavior": "string",
      "coverage_areas": ["string"],
      "priority": "enum(high, medium, low)"
    }
  ],
  "completion_status": "string",
  "processing_time": "number"
}
```

#### Validate Scenario

```
POST /api/v1/llm/validate/scenario
```

**Request Body**:
```json
{
  "scenario": {
    "id": "string",
    "title": "string",
    "description": "string",
    "preconditions": "string",
    "expected_behavior": "string"
  }
}
```

**Response**:
```json
{
  "validity": "boolean",
  "issues": [
    {
      "type": "string",
      "description": "string",
      "severity": "enum(critical, major, minor)",
      "suggestion": "string"
    }
  ],
  "overall_quality_score": "number"
}
```

---

## Test Case Manager API

The Test Case Manager API enables generating detailed test cases from scenarios, refining existing test cases, and managing versions.

### Endpoints

#### Generate Test Cases from Scenarios

```
POST /api/v1/testcases/generate
```

**Request Body**:
```json
{
  "scenarios": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "preconditions": "string",
      "expected_behavior": "string"
    }
  ],
  "format": "enum(excel, json)",
  "detail_level": "enum(high, medium, low)",
  "include_data_variations": "boolean"
}
```

**Response**:
```json
{
  "request_id": "string",
  "test_cases": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "preconditions": "string",
      "scenario_id": "string",
      "steps": [
        {
          "step_number": "integer",
          "action": "string",
          "expected_result": "string",
          "test_data": "string"
        }
      ],
      "priority": "string",
      "estimated_duration": "string",
      "test_data_requirements": ["string"],
      "automation_feasibility": "string"
    }
  ],
  "excel_download_url": "string", // Only if format=excel
  "completion_status": "string"
}
```

#### Refine Existing Test Case

```
POST /api/v1/testcases/refine
```

**Request Body**:
```
multipart/form-data
- file: binary (required) - Test case file in Excel/Word format
- refinement_focus: string (optional, enum: completeness, clarity, data_variations, automation_readiness)
```

**Response**:
```json
{
  "request_id": "string",
  "original_test_case": {
    "id": "string",
    "title": "string",
    "steps_count": "integer"
  },
  "refinement_suggestions": [
    {
      "type": "enum(add, modify, remove, restructure)",
      "target": "string",
      "original_content": "string",
      "suggested_content": "string",
      "rationale": "string"
    }
  ],
  "refined_test_case": {
    "id": "string",
    "title": "string",
    "description": "string",
    "preconditions": "string",
    "steps": [
      {
        "step_number": "integer",
        "action": "string",
        "expected_result": "string",
        "test_data": "string"
      }
    ]
  },
  "excel_download_url": "string"
}
```

#### Check Test Case Obsolescence

```
POST /api/v1/testcases/check-obsolescence
```

**Request Body**:
```
multipart/form-data
- file: binary (required) - Test case file
- reference_requirements: string (optional) - Latest requirements text or reference
```

**Response**:
```json
{
  "is_obsolete": "boolean",
  "confidence_score": "number",
  "reasons": [
    {
      "description": "string",
      "severity": "enum(critical, major, minor)"
    }
  ],
  "recommendation": "string"
}
```

#### Create Test Case Version

```
POST /api/v1/testcases/versions
```

**Request Body**:
```json
{
  "test_case_id": "string",
  "version_number": "string",
  "description": "string",
  "content": "object", // Test case content
  "author": "string"
}
```

**Response**:
```json
{
  "test_case_id": "string",
  "version_id": "string",
  "version_number": "string",
  "created_at": "datetime",
  "status": "Created"
}
```

#### Get Test Case Version History

```
GET /api/v1/testcases/{test_case_id}/versions
```

**Path Parameters**:
```
test_case_id: string (required)
```

**Response**:
```json
{
  "test_case_id": "string",
  "title": "string",
  "versions": [
    {
      "version_id": "string",
      "version_number": "string",
      "description": "string",
      "author": "string",
      "created_at": "datetime"
    }
  ]
}
```

---

## SharePoint Connector API

The SharePoint Connector API enables document management for test cases and test execution reports in SharePoint.

### Endpoints

#### Upload Document to SharePoint

```
POST /api/v1/sharepoint/documents
```

**Request Body**:
```
multipart/form-data
- file: binary (required)
- folder_path: string (required)
- document_type: string (required, enum: test_case, execution_report, defect_report)
- metadata: json (optional)
```

**Response**:
```json
{
  "document_id": "string",
  "url": "string",
  "status": "Uploaded",
  "folder_path": "string",
  "file_name": "string"
}
```

#### Get Document from SharePoint

```
GET /api/v1/sharepoint/documents/{document_id}
```

**Path Parameters**:
```
document_id: string (required)
```

**Response**:
Binary file data with appropriate Content-Type header

#### Search Documents

```
GET /api/v1/sharepoint/documents/search
```

**Query Parameters**:
```
document_type: string (enum: test_case, execution_report, defect_report)
keyword: string
author: string
created_after: datetime
created_before: datetime
folder_path: string
limit: integer (default: 20)
offset: integer (default: 0)
```

**Response**:
```json
{
  "documents": [
    {
      "document_id": "string",
      "file_name": "string",
      "url": "string",
      "document_type": "string",
      "created_at": "datetime",
      "created_by": "string",
      "modified_at": "datetime",
      "modified_by": "string",
      "folder_path": "string",
      "metadata": "object"
    }
  ],
  "total": "integer",
  "offset": "integer",
  "limit": "integer"
}
```

#### Update Document Version

```
PUT /api/v1/sharepoint/documents/{document_id}/versions
```

**Path Parameters**:
```
document_id: string (required)
```

**Request Body**:
```
multipart/form-data
- file: binary (required)
- comment: string (optional)
```

**Response**:
```json
{
  "document_id": "string",
  "version_id": "string",
  "version_number": "string",
  "url": "string",
  "status": "Updated"
}
```

#### Get Document Versions

```
GET /api/v1/sharepoint/documents/{document_id}/versions
```

**Path Parameters**:
```
document_id: string (required)
```

**Response**:
```json
{
  "document_id": "string",
  "file_name": "string",
  "versions": [
    {
      "version_id": "string",
      "version_number": "string",
      "created_at": "datetime",
      "created_by": "string",
      "comment": "string",
      "url": "string"
    }
  ]
}
```

---

## Coverage Analyzer API

The Coverage Analyzer API enables comparing test cases with the repository to identify matches, gaps, and needs for updates.

### Endpoints

#### Compare with Repository

```
POST /api/v1/coverage/compare
```

**Request Body**:
```json
{
  "test_cases": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "steps": [
        {
          "step_number": "integer",
          "action": "string",
          "expected_result": "string"
        }
      ]
    }
  ],
  "repository_source": "enum(sharepoint, jira, alm)",
  "match_threshold": "number" // 0.0-1.0, default: 0.8
}
```

**Response**:
```json
{
  "summary": {
    "total_cases_compared": "integer",
    "exact_matches": "integer",
    "partial_matches": "integer",
    "new_cases": "integer"
  },
  "results": [
    {
      "test_case_id": "string",
      "test_case_title": "string",
      "match_status": "enum(exact_match, partial_match, new_case)",
      "match_score": "number",
      "repository_matches": [
        {
          "repository_id": "string",
          "repository_title": "string",
          "match_score": "number",
          "repository_type": "enum(manual, automated)",
          "repository_owner": "string",
          "differences": [
            {
              "type": "enum(missing_step, additional_step, modified_step)",
              "location": "string",
              "description": "string"
            }
          ]
        }
      ]
    }
  ]
}
```

#### Analyze Repository Coverage

```
POST /api/v1/coverage/analyze
```

**Request Body**:
```json
{
  "requirements": [
    {
      "id": "string",
      "title": "string",
      "description": "string"
    }
  ],
  "repository_source": "enum(sharepoint, jira, alm)"
}
```

**Response**:
```json
{
  "coverage_summary": {
    "total_requirements": "integer",
    "fully_covered": "integer",
    "partially_covered": "integer",
    "not_covered": "integer",
    "overall_coverage_percentage": "number"
  },
  "requirement_coverage": [
    {
      "requirement_id": "string",
      "requirement_title": "string",
      "coverage_status": "enum(fully_covered, partially_covered, not_covered)",
      "coverage_score": "number",
      "covering_test_cases": [
        {
          "test_case_id": "string",
          "test_case_title": "string",
          "match_score": "number"
        }
      ]
    }
  ],
  "gap_analysis": [
    {
      "requirement_id": "string",
      "requirement_aspect": "string",
      "coverage_gap": "string",
      "suggested_test_scenario": "string"
    }
  ]
}
```

#### Identify Coverage Gaps

```
POST /api/v1/coverage/gaps
```

**Request Body**:
```json
{
  "test_cases": [
    {
      "id": "string",
      "title": "string",
      "type": "enum(positive, negative, boundary, performance, security)",
      "coverage_areas": ["string"]
    }
  ],
  "feature_name": "string"
}
```

**Response**:
```json
{
  "gaps": [
    {
      "gap_type": "enum(missing_test_type, missing_coverage_area, insufficient_scenarios)",
      "description": "string",
      "severity": "enum(high, medium, low)",
      "suggested_additions": [
        {
          "test_type": "string",
          "scenario": "string",
          "rationale": "string"
        }
      ]
    }
  ],
  "coverage_metrics": {
    "positive_tests_percentage": "number",
    "negative_tests_percentage": "number",
    "boundary_tests_percentage": "number",
    "performance_tests_percentage": "number",
    "security_tests_percentage": "number",
    "overall_balance_score": "number"
  }
}
```

#### Get Repository Statistics

```
GET /api/v1/coverage/stats
```

**Query Parameters**:
```
repository_source: string (enum: sharepoint, jira, alm)
```

**Response**:
```json
{
  "total_test_cases": "integer",
  "automated_tests": "integer",
  "manual_tests": "integer",
  "automation_percentage": "number",
  "test_types_distribution": {
    "functional": "integer",
    "integration": "integer",
    "performance": "integer",
    "security": "integer",
    "usability": "integer",
    "compatibility": "integer",
    "other": "integer"
  },
  "top_test_owners": [
    {
      "owner": "string",
      "test_count": "integer"
    }
  ]
}
```

---

## Streamlit UI API

The Streamlit UI API provides endpoints to support the UI functionality and data requirements.

### Endpoints

#### Get UI Configuration

```
GET /api/v1/ui/config
```

**Response**:
```json
{
  "modules": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "enabled": "boolean",
      "icon": "string",
      "url_path": "string"
    }
  ],
  "user_preferences": {
    "theme": "string",
    "default_view": "string",
    "notifications_enabled": "boolean"
  },
  "feature_flags": {
    "feature_name": "boolean"
  }
}
```

#### Get Dashboard Data

```
GET /api/v1/ui/dashboard
```

**Response**:
```json
{
  "pending_tasks": [
    {
      "id": "string",
      "task_type": "enum(review_changes, approve_test_case, review_failed_test)",
      "title": "string",
      "created_at": "datetime",
      "priority": "enum(high, medium, low)",
      "link": "string"
    }
  ],
  "recent_activity": [
    {
      "id": "string",
      "activity_type": "enum(generation, execution, defect_creation)",
      "description": "string",
      "performed_by": "string",
      "performed_at": "datetime",
      "link": "string"
    }
  ],
  "test_execution_summary": {
    "total_executions": "integer",
    "pass_count": "integer",
    "fail_count": "integer",
    "blocked_count": "integer",
    "recent_executions": [
      {
        "id": "string",
        "name": "string",
        "status": "string",
        "executed_at": "datetime",
        "link": "string"
      }
    ]
  },
  "defect_summary": {
    "total_defects": "integer",
    "open_count": "integer",
    "in_progress_count": "integer",
    "closed_count": "integer",
    "recent_defects": [
      {
        "id": "string",
        "summary": "string",
        "status": "string",
        "priority": "string",
        "created_at": "datetime",
        "link": "string"
      }
    ]
  }
}
```

#### Get Test Case Preview

```
GET /api/v1/ui/test-case-preview/{test_case_id}
```

**Path Parameters**:
```
test_case_id: string (required)
```

**Response**:
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "preconditions": "string",
  "steps": [
    {
      "step_number": "integer",
      "action": "string",
      "expected_result": "string",
      "test_data": "string"
    }
  ],
  "owner": "string",
  "created_at": "datetime",
  "last_modified_at": "datetime",
  "type": "enum(manual, automated)",
  "status": "string",
  "test_data_status": "enum(available, needs_generation, not_applicable)"
}
```

#### Upload UI Document

```
POST /api/v1/ui/documents/upload
```

**Request Body**:
```
multipart/form-data
- file: binary (required)
- document_type: string (required, enum: requirements, test_case, execution_report)
- description: string (optional)
```

**Response**:
```json
{
  "document_id": "string",
  "file_name": "string",
  "status": "enum(uploaded, processing, processed, failed)",
  "preview_url": "string"
}
```

---

## System Configuration API

The System Configuration API enables managing system settings, rules, integration settings, and user management.

### Endpoints

#### Get System Configuration

```
GET /api/v1/config
```

**Response**:
```json
{
  "version": "string",
  "environment": "string",
  "integrations": {
    "jira": {
      "enabled": "boolean",
      "url": "string",
      "connection_status": "enum(connected, disconnected, error)"
    },
    "sharepoint": {
      "enabled": "boolean",
      "url": "string",
      "connection_status": "enum(connected, disconnected, error)"
    },
    "alm": {
      "enabled": "boolean",
      "url": "string",
      "connection_status": "enum(connected, disconnected, error)"
    },
    "watsonx": {
      "enabled": "boolean",
      "models": ["string"],
      "connection_status": "enum(connected, disconnected, error)"
    }
  },
  "features": {
    "feature_name": {
      "enabled": "boolean",
      "config": "object"
    }
  }
}
```

#### Update System Configuration

```
PUT /api/v1/config
```

**Request Body**:
```json
{
  "integrations": {
    "jira": {
      "enabled": "boolean",
      "url": "string",
      "api_token": "string"
    },
    "sharepoint": {
      "enabled": "boolean",
      "url": "string",
      "client_id": "string",
      "client_secret": "string"
    },
    "alm": {
      "enabled": "boolean",
      "url": "string",
      "username": "string",
      "password": "string"
    },
    "watsonx": {
      "enabled": "boolean",
      "api_key": "string",
      "preferred_model": "string"
    }
  },
  "features": {
    "feature_name": {
      "enabled": "boolean",
      "config": "object"
    }
  }
}
```

**Response**:
```json
{
  "status": "Updated",
  "updated_at": "datetime"
}
```

#### Get Rules

```
GET /api/v1/config/rules
```

**Response**:
```json
{
  "test_case_owner_rules": [
    {
      "id": "string",
      "name": "string",
      "criteria": {
        "application_module": "string",
        "test_type": "string",
        "complexity": "string"
      },
      "assigned_owner": "string",
      "priority": "integer"
    }
  ],
  "defect_assignment_rules": [
    {
      "id": "string",
      "name": "string",
      "criteria": {
        "component": "string",
        "severity": "string",
        "error_type": "string"
      },
      "assigned_role": "enum(developer, project_manager, qa_lead, defect_analyst)",
      "priority": "integer"
    }
  ]
}
```

#### Update Rules

```
PUT /api/v1/config/rules
```

**Request Body**:
```json
{
  "test_case_owner_rules": [
    {
      "id": "string",
      "name": "string",
      "criteria": {
        "application_module": "string",
        "test_type": "string",
        "complexity": "string"
      },
      "assigned_owner": "string",
      "priority": "integer"
    }
  ],
  "defect_assignment_rules": [
    {
      "id": "string",
      "name": "string",
      "criteria": {
        "component": "string",
        "severity": "string",
        "error_type": "string"
      },
      "assigned_role": "enum(developer, project_manager, qa_lead, defect_analyst)",
      "priority": "integer"
    }
  ]
}
```

**Response**:
```json
{
  "status": "Updated",
  "updated_at": "datetime"
}
```

#### Get Users

```
GET /api/v1/config/users
```

**Query Parameters**:
```
role: string
active: boolean
limit: integer (default: 20)
offset: integer (default: 0)
```

**Response**:
```json
{
  "users": [
    {
      "id": "string",
      "username": "string",
      "email": "string",
      "name": "string",
      "role": "string",
      "active": "boolean",
      "created_at": "datetime",
      "last_login": "datetime"
    }
  ],
  "total": "integer",
  "offset": "integer",
  "limit": "integer"
}
```

#### Create User

```
POST /api/v1/config/users
```

**Request Body**:
```json
{
  "username": "string",
  "email": "string",
  "name": "string",
  "role": "string",
  "password": "string",
  "active": "boolean"
}
```

**Response**:
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "name": "string",
  "role": "string",
  "active": "boolean",
  "created_at": "datetime"
}
```

---

## Test Data Manager API

The Test Data Manager API enables analyzing test data requirements, generating test data, and managing test data files.

### Endpoints

#### Analyze Test Data Requirements

```
POST /api/v1/testdata/analyze
```

**Request Body**:
```json
{
  "test_case": {
    "id": "string",
    "title": "string",
    "steps": [
      {
        "step_number": "integer",
        "action": "string",
        "expected_result": "string",
        "test_data": "string"
      }
    ]
  }
}
```

**Response**:
```json
{
  "test_data_requirements": [
    {
      "field_name": "string",
      "data_type": "string",
      "constraints": ["string"],
      "examples": ["string"],
      "step_references": ["integer"]
    }
  ],
  "dependencies": [
    {
      "source_field": "string",
      "dependent_field": "string",
      "relationship_type": "string",
      "description": "string"
    }
  ],
  "preprocessing_requirements": ["string"],
  "data_volume_requirements": {
    "min_records": "integer",
    "recommended_records": "integer"
  }
}
```

#### Generate Test Data

```
POST /api/v1/testdata/generate
```

**Request Body**:
```json
{
  "test_data_requirements": [
    {
      "field_name": "string",
      "data_type": "string",
      "constraints": ["string"],
      "examples": ["string"]
    }
  ],
  "record_count": "integer",
  "output_format": "enum(csv, json, excel)",
  "seed": "string" // Optional for reproducibility
}
```

**Response**:
```json
{
  "download_url": "string",
  "sample_data": [
    {
      "field_name": "value"
    }
  ],
  "generation_metadata": {
    "record_count": "integer",
    "generation_timestamp": "datetime",
    "format": "string"
  }
}
```

#### Check Test Data Availability

```
POST /api/v1/testdata/check-availability
```

**Request Body**:
```json
{
  "test_case_id": "string",
  "test_data_requirements": [
    {
      "field_name": "string",
      "data_type": "string",
      "constraints": ["string"]
    }
  ]
}
```

**Response**:
```json
{
  "available": "boolean",
  "matching_datasets": [
    {
      "dataset_id": "string",
      "name": "string",
      "compatibility_score": "number",
      "record_count": "integer",
      "last_updated": "datetime",
      "location": "string"
    }
  ],
  "missing_requirements": [
    {
      "field_name": "string",
      "reason": "string"
    }
  ]
}
```

#### Update Test Data File

```
PUT /api/v1/testdata/files/{file_id}
```

**Path Parameters**:
```
file_id: string (required)
```

**Request Body**:
```
multipart/form-data
- file: binary (required)
- description: string (optional)
```

**Response**:
```json
{
  "file_id": "string",
  "name": "string",
  "status": "Updated",
  "updated_at": "datetime"
}
```

#### Validate Test Data

```
POST /api/v1/testdata/validate
```

**Request Body**:
```
multipart/form-data
- file: binary (required)
- requirements: json (required) - Test data requirements in JSON format
```

**Response**:
```json
{
  "valid": "boolean",
  "validation_details": {
    "records_analyzed": "integer",
    "valid_records": "integer",
    "invalid_records": "integer",
    "field_validation": [
      {
        "field_name": "string",
        "valid_percentage": "number",
        "issues": [
          {
            "type": "enum(missing_value, invalid_format, constraint_violation)",
            "record_indices": ["integer"],
            "description": "string"
          }
        ]
      }
    ]
  }
}
```

---

## Notification Service API

The Notification Service API enables sending notifications to users based on events and managing notification preferences.

### Endpoints

#### Send Notification

```
POST /api/v1/notifications
```

**Request Body**:
```json
{
  "recipient_ids": ["string"],
  "notification_type": "enum(test_case_update, execution_complete, defect_created, owner_assignment, review_request)",
  "title": "string",
  "message": "string",
  "source_id": "string", // Related resource ID
  "priority": "enum(high, medium, low)",
  "action_url": "string" // Optional URL to direct user to
}
```

**Response**:
```json
{
  "notification_id": "string",
  "status": "enum(sent, queued, failed)",
  "recipient_count": "integer",
  "created_at": "datetime"
}
```

#### Get User Notifications

```
GET /api/v1/notifications/user
```

**Query Parameters**:
```
status: string (enum: all, unread, read)
limit: integer (default: 20)
offset: integer (default: 0)
```

**Response**:
```json
{
  "notifications": [
    {
      "id": "string",
      "notification_type": "string",
      "title": "string",
      "message": "string",
      "source_id": "string",
      "priority": "string",
      "action_url": "string",
      "created_at": "datetime",
      "read": "boolean",
      "read_at": "datetime"
    }
  ],
  "unread_count": "integer",
  "total": "integer",
  "offset": "integer",
  "limit": "integer"
}
```

#### Mark Notification as Read

```
PUT /api/v1/notifications/{notification_id}/read
```

**Path Parameters**:
```
notification_id: string (required)
```

**Response**:
```json
{
  "id": "string",
  "read": true,
  "read_at": "datetime"
}
```

#### Get Notification Preferences

```
GET /api/v1/notifications/preferences
```

**Response**:
```json
{
  "email_notifications": "boolean",
  "in_app_notifications": "boolean",
  "notification_preferences": {
    "test_case_update": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "execution_complete": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "defect_created": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "owner_assignment": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "review_request": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    }
  }
}
```

#### Update Notification Preferences

```
PUT /api/v1/notifications/preferences
```

**Request Body**:
```json
{
  "email_notifications": "boolean",
  "in_app_notifications": "boolean",
  "notification_preferences": {
    "test_case_update": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "execution_complete": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "defect_created": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "owner_assignment": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    },
    "review_request": {
      "enabled": "boolean",
      "email": "boolean",
      "in_app": "boolean"
    }
  }
}
```

**Response**:
```json
{
  "status": "Updated",
  "updated_at": "datetime"
}
```

#### Get Email Templates

```
GET /api/v1/notifications/templates
```

**Response**:
```json
{
  "templates": [
    {
      "id": "string",
      "name": "string",
      "notification_type": "string",
      "subject": "string",
      "preview": "string"
    }
  ]
}
```

#### Update Email Template

```
PUT /api/v1/notifications/templates/{template_id}
```

**Path Parameters**:
```
template_id: string (required)
```

**Request Body**:
```json
{
  "subject": "string",
  "content": "string",
  "variables": ["string"]
}
```

**Response**:
```json
{
  "id": "string",
  "name": "string",
  "status": "Updated",
  "updated_at": "datetime"
}
```

---

## Cross-Module API Examples

This section provides examples of common API workflows that span multiple modules.

### Generate Test Cases from JIRA Story and Compare with Repository

**Step 1**: Fetch a user story from JIRA
```
GET /api/v1/jira/stories?project=IPG&key=IPG-123
```

**Step 2**: Generate test scenarios from the story
```
POST /api/v1/llm/generate/scenarios/jira
{
  "story_key": "IPG-123",
  "detail_level": "high",
  "coverage_focus": ["functional", "usability"],
  "max_scenarios": 5
}
```

**Step 3**: Generate detailed test cases from scenarios
```
POST /api/v1/testcases/generate
{
  "scenarios": [...], // From previous response
  "format": "json",
  "detail_level": "high",
  "include_data_variations": true
}
```

**Step 4**: Compare generated test cases with repository
```
POST /api/v1/coverage/compare
{
  "test_cases": [...], // From previous response
  "repository_source": "sharepoint",
  "match_threshold": 0.8
}
```

**Step 5**: For new test cases, upload to SharePoint
```
POST /api/v1/sharepoint/documents
multipart/form-data
- file: Excel file with test cases
- folder_path: "/Test Cases/IPG/Sprint 10"
- document_type: "test_case"
- metadata: {"project": "IPG", "sprint": "10", "story": "IPG-123"}
```

**Step 6**: Send notification to test owner
```
POST /api/v1/notifications
{
  "recipient_ids": ["user123"],
  "notification_type": "owner_assignment",
  "title": "New Test Cases Assigned",
  "message": "5 new test cases have been generated for IPG-123 and assigned to you.",
  "source_id": "IPG-123",
  "priority": "medium",
  "action_url": "/test-cases?story=IPG-123"
}
```

### Test Execution Flow for Automated Tests

**Step 1**: Check test data availability
```
POST /api/v1/testdata/check-availability
{
  "test_case_id": "TC-456",
  "test_data_requirements": [...] // List of required data fields
}
```

**Step 2**: If test data is not available, generate it
```
POST /api/v1/testdata/generate
{
  "test_data_requirements": [...],
  "record_count": 10,
  "output_format": "csv"
}
```

**Step 3**: Trigger test execution (to be implemented in Phase 2)
```
POST /api/v2/execution/trigger
{
  "test_case_ids": ["TC-456"],
  "environment": "test",
  "controller_file": "path/to/controller.xlsx"
}
```

## Versioning

All API endpoints are versioned with the prefix `/api/v1/` to ensure backward compatibility as the system evolves. Future versions may be introduced with `/api/v2/`, etc.

## Error Handling

All API endpoints return standard HTTP status codes:

- 200: Success
- 400: Bad Request (invalid parameters)
- 401: Unauthorized (authentication required)
- 403: Forbidden (insufficient permissions)
- 404: Resource Not Found
- 500: Internal Server Error

Error responses follow this format:
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "string" // Optional
  }
}
```

## Rate Limiting

API endpoints are rate-limited to ensure system stability. Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1619348400
```

When rate limits are exceeded, the API returns a 429 Too Many Requests status code.

## Authentication and Authorization

All API endpoints require a valid JWT token (except for the token endpoint). See the [Authentication](#authentication) section for details.

Different API endpoints require different permissions:
- READ: View resources
- WRITE: Create and update resources
- ADMIN: Configure system settings, manage users, etc.

Permissions are assigned to users based on their roles.

## Further Reading

- [Phase 2 APIs Documentation](phase2_apis.md)
- [API Architecture Overview](../architecture/overview.md)
- [Developer Setup](../developer/setup.md)
- [Integration Guide](../developer/integration.md)