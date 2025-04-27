# Watsonx for IPG Testing - Phase 1 Architecture

## Table of Contents

- [Overview](#overview)
- [Business Requirements](#business-requirements)
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Integration Points](#integration-points)
- [Technology Stack](#technology-stack)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Phase 1 Limitations and Future Enhancements](#phase-1-limitations-and-future-enhancements)

## Overview

The Watsonx for IPG Testing solution is an AI-powered platform designed to transform the traditional testing process for the IPG (Intelligent Process Gateway) system. Phase 1 focuses on the initial capabilities to automate test case generation, comparison, refinement, and management, laying the groundwork for the RPA-based test execution that will be implemented in Phase 2.

This architecture document specifically addresses Phase 1 components, integrations, and workflows, providing a comprehensive view of how the system will translate business requirements into test cases, manage test repositories, and prepare for test execution.

## Business Requirements

Phase 1 of the solution addresses the following key business requirements:

1. **Automated Test Case Generation**:
   - Process user stories, requirements, and business cases from various input sources (JIRA, documents)
   - Translate business requirements into clear, testable scenarios using watsonx LLM capabilities
   - Generate detailed test cases in a predefined Excel format with sufficient information for execution

2. **Test Case Repository Management**:
   - Compare newly generated test cases with existing test case repository
   - Identify exact matches, partial matches requiring modification, and entirely new test cases
   - Maintain versioning of test cases in SharePoint/JIRA/ALM

3. **Test Case Refinement**:
   - Review and refine test cases by adding more details and variations
   - Identify potential gaps or inconsistencies in existing test cases
   - Determine obsolescence of test cases and notify owners for review

4. **Test Data Management**:
   - Verify availability of test data for automated test cases
   - Generate test data when required for test execution

5. **Notification and Assignment**:
   - Assign test cases to owners based on predefined rules
   - Notify relevant stakeholders about test case updates, required modifications, or manual execution needs

6. **Streamlined User Experience**:
   - Provide an intuitive web-based interface for testers and test managers
   - Enable easy input of requirements and display of generated test cases
   - Support manual reviews and approvals where necessary

## System Architecture

Phase 1 of the Watsonx for IPG Testing solution follows a modular, microservices-based architecture to ensure scalability, maintainability, and flexibility. The architecture consists of several interconnected modules, each responsible for specific functionality within the overall testing workflow.

### High-Level Architecture Diagram

The following diagram illustrates the IBM Cloud-based architecture for the Watsonx for IPG Testing solution:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                Web-Based UI (Streamlit on IBM Cloud ROKS)                 │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
┌─────────────────▼─────────────────┐  ┌─────────────▼─────────────────────┐
│     IBM API Connect Gateway       │  │      IBM Cloud IAM                │
└─────────────────┬─────────────────┘  └───────────────────────────────────┘
                  │
┌─────────────────┼─────────────────────────────────────────────────────────┐
│                 │      Core Business Logic Layer (IBM Cloud ROKS)         │
│  ┌──────────────▼────────────┐   ┌───────────────────────────────────┐   │
│  │  JIRA Connector Module    │   │  LLM Test Scenario Generator      │   │
│  └──────────────┬────────────┘   └───────────────┬───────────────────┘   │
│                 │                                │                        │
│  ┌──────────────▼────────────┐   ┌───────────────▼───────────────────┐   │
│  │  Test Case Manager        │◄──┤  Coverage Analyzer                │   │
│  └──────────────┬────────────┘   └───────────────┬───────────────────┘   │
│                 │                                │                        │
│  ┌──────────────▼────────────┐   ┌───────────────▼───────────────────┐   │
│  │  SharePoint Connector     │   │  Test Data Manager                │   │
│  └──────────────┬────────────┘   └───────────────┬───────────────────┘   │
│                 │                                │                        │
│  ┌──────────────▼────────────┐   ┌───────────────▼───────────────────┐   │
│  │  System Configuration     │   │  Notification Service              │   │
│  └──────────────┬────────────┘   └───────────────────────────────────┘   │
└─────────────────┼─────────────────────────────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────────────────────────────┐
│                         IBM Cloud Services Layer                           │
│  ┌──────────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │  IBM Databases for   │  │  IBM Cloud        │  │  IBM Cloud        │   │
│  │  PostgreSQL          │  │  Object Storage   │  │  Key Protect      │   │
│  └──────────────────────┘  └───────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌──────────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │    IBM watsonx.ai    │  │  IBM Cloud Logs   │  │  IBM Monitoring   │   │
│  └──────────────────────┘  └───────────────────┘  └───────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────────────────────────────┐
│                         External Integration Layer                         │
│  ┌──────────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │      JIRA API        │  │  SharePoint API   │  │      ALM API      │   │
│  └──────────────────────┘  └───────────────────┘  └───────────────────┘   │
│                                                                            │
│  ┌──────────────────────┐                                                  │
│  │  Email Services      │                                                  │
│  └──────────────────────┘                                                  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Principles

1. **Modularity**: Each component is designed as a separate module with well-defined interfaces to facilitate independent development, testing, and maintenance.

2. **API-First Design**: All interactions between components are through RESTful APIs, allowing for flexibility in implementation and future extensions.

3. **Statelessness**: Core business logic components are designed to be stateless, with state maintained in the database, enabling horizontal scaling.

4. **Loose Coupling**: Modules communicate through well-defined APIs, reducing interdependencies and allowing components to evolve independently.

5. **Data Isolation**: Each module manages its own data store needs, with a shared database schema for overlapping concerns.

6. **Security by Design**: Authentication, authorization, and data protection mechanisms are built into the architecture from the ground up.

7. **Extensibility**: The architecture is designed to easily accommodate the Phase 2 additions for RPA-based test execution.

## Core Components

### 1. JIRA Connector Module

**Purpose**: Interfaces with JIRA to retrieve user stories, requirements, and business cases, and to create and manage defects.

**Key Components**:
- **JIRA Authentication Service**: Manages authentication with JIRA using API tokens or OAuth.
- **Story Retriever**: Fetches user stories and requirements from JIRA projects.
- **Defect Manager**: Creates and updates defects in JIRA.
- **JIRA Parser**: Converts JIRA issue fields into standardized internal formats.

**Functionality**:
- Retrieve user stories based on various filters (project, sprint, status)
- Parse structured and unstructured data from JIRA issues
- Create and update defects with appropriate metadata
- Track defect status and updates

### 2. LLM Test Scenario Generator Module

**Purpose**: Leverages watsonx LLM capabilities to generate testable scenarios from various input sources.

**Key Components**:
- **Document Processor**: Handles various input formats (Word, Excel, PDF, Text).
- **LLM Connector**: Interfaces with watsonx API for generating test scenarios.
- **Scenario Generator**: Converts requirements into structured test scenarios.
- **Scenario Validator**: Validates generated scenarios for completeness and testability.

**Functionality**:
- Process documents in various formats to extract requirements
- Convert structured and unstructured requirements into test scenarios
- Ensure scenarios are clear, testable, and aligned with business requirements
- Generate appropriate level of detail based on configuration

### 3. Test Case Manager Module

**Purpose**: Generates detailed test cases from scenarios and manages test case revisions and metadata.

**Key Components**:
- **TestCase Generator**: Creates detailed test cases from scenarios.
- **TestCase Refiner**: Enhances test cases with additional details and variations.
- **Version Controller**: Manages test case versions and revisions.
- **Metadata Manager**: Handles test case metadata and relationships.

**Functionality**:
- Generate detailed test cases with steps, expected results, and test data requirements
- Refine existing test cases to improve quality and coverage
- Track test case versions and revisions
- Maintain test case metadata and relationships to requirements

### 4. SharePoint Connector Module

**Purpose**: Interfaces with SharePoint for document management of test cases and execution reports.

**Key Components**:
- **SharePoint Authentication**: Manages authentication with SharePoint.
- **Document Uploader**: Uploads test case documents and reports to SharePoint.
- **Document Retriever**: Retrieves and searches documents from SharePoint.
- **SharePoint Version Manager**: Manages document versioning in SharePoint.

**Functionality**:
- Upload test case documents to appropriate SharePoint locations
- Retrieve test cases and templates from SharePoint
- Maintain document versioning and metadata
- Search for documents based on various criteria

### 5. Coverage Analyzer Module

**Purpose**: Compares newly generated test cases with existing repository to identify matches, gaps, and needed updates.

**Key Components**:
- **Repository Scanner**: Scans the existing test case repository.
- **Comparison Engine**: Compares test cases to identify similarities and differences.
- **Match Classifier**: Classifies matches as exact, partial, or new.
- **Gap Analyzer**: Identifies coverage gaps in test suite.

**Functionality**:
- Compare new test cases with existing repository
- Identify exact matches, partial matches, and new test cases
- Generate reports on test coverage gaps
- Provide recommendations for test suite improvement

### 6. Streamlit UI Module

**Purpose**: Provides a user-friendly web interface for interacting with the system.

**Key Components**:
- **Dashboard**: Overview of testing activities and status.
- **TestCase UI**: Interface for test case generation and management.
- **Execution UI**: Interface for test execution planning and monitoring.
- **Report UI**: Interface for viewing and generating reports.

**Functionality**:
- Display dashboard with key metrics and pending actions
- Provide interfaces for requirements input and test case generation
- Support review and approval workflows
- Display test case comparison results and coverage analysis

### 7. System Configuration Module

**Purpose**: Manages system settings, rules, and integration configurations.

**Key Components**:
- **Config Manager**: Handles system-wide configuration settings.
- **Rule Engine**: Manages and applies business rules for assignments and workflows.
- **Integration Settings**: Manages external system integration configurations.
- **User Manager**: Handles user accounts and permissions.

**Functionality**:
- Manage system configuration settings
- Define and apply business rules for assignments
- Configure external system integrations
- Manage user accounts, roles, and permissions

### 8. Test Data Manager Module

**Purpose**: Analyzes test data requirements, generates test data, and manages test data files.

**Key Components**:
- **Data Analyzer**: Analyzes test cases to identify data requirements.
- **Data Generator**: Generates test data based on requirements.
- **Data File Manager**: Manages test data files and their relationships to test cases.
- **Data Validator**: Validates test data against requirements.

**Functionality**:
- Analyze test cases to determine data requirements
- Generate appropriate test data based on requirements
- Manage and organize test data files
- Validate test data against requirements

### 9. Notification Service Module

**Purpose**: Manages notifications to users about assignments, updates, and actions required.

**Key Components**:
- **Notification Manager**: Coordinates notification generation and delivery.
- **Email Service**: Sends email notifications to users.
- **Notification Dashboard**: Displays in-app notifications.
- **Template Manager**: Manages notification templates.

**Functionality**:
- Generate notifications based on system events
- Deliver notifications via email and in-app channels
- Manage notification preferences and templates
- Track notification status and responses

## Data Flow

### Test Case Generation Flow

1. **Input Acquisition**:
   - User submits requirements through JIRA integration or document upload
   - System parses input into standardized format

2. **Scenario Generation**:
   - LLM Test Scenario Generator processes requirements
   - Watsonx generates testable scenarios
   - Scenarios are validated for completeness and testability

3. **Test Case Creation**:
   - Test Case Manager converts scenarios to detailed test cases
   - Test data requirements are identified
   - Test cases are formatted according to predefined templates

4. **Repository Comparison**:
   - Coverage Analyzer compares test cases with existing repository
   - Test cases are classified as exact matches, partial matches, or new

5. **Repository Update**:
   - Exact matches: Update matching list
   - Partial matches: Notify owner, upload new version, update list
   - New test cases: Assign owner, upload to repository, update list

6. **Notification**:
   - Notification Service alerts relevant stakeholders
   - Test case owners receive assignments
   - Approvers are notified of pending reviews

### Test Case Refinement Flow

1. **Test Case Selection**:
   - User selects test case for refinement
   - System retrieves test case from repository

2. **AI Analysis**:
   - LLM analyzes test case for improvement opportunities
   - System identifies gaps, inconsistencies, or opportunities for enhancement

3. **Suggestion Generation**:
   - System generates specific suggestions for refinement
   - Side-by-side comparison shows original and refined versions

4. **User Review**:
   - User reviews suggestions and makes decisions
   - User can accept, modify, or reject suggestions

5. **Repository Update**:
   - Approved changes are incorporated into test case
   - New version is uploaded to repository
   - Owner is notified of changes

### Test Data Management Flow

1. **Data Requirement Analysis**:
   - System analyzes test case to identify data requirements
   - Data types, constraints, and volumes are determined

2. **Data Availability Check**:
   - System checks if suitable test data is already available
   - If available, data is linked to test case

3. **Data Generation**:
   - If required data is not available, system generates new data
   - Generated data is validated against requirements

4. **Data Storage**:
   - Generated data is stored in appropriate repository
   - Data is linked to relevant test cases

## Integration Points

### JIRA Integration

- **Authentication**: OAuth or API tokens
- **Data Exchange**: REST API
- **Functionality**:
  - Fetch user stories and requirements
  - Create and update defects
  - Link test cases to requirements
  - Update issue status and comments

### SharePoint Integration

- **Authentication**: OAuth or App-only authentication
- **Data Exchange**: SharePoint REST API or Microsoft Graph API
- **Functionality**:
  - Upload and retrieve documents
  - Manage document versions
  - Search for documents
  - Maintain document metadata

### ALM Integration

- **Authentication**: Basic authentication or API tokens
- **Data Exchange**: REST API or SDK
- **Functionality**:
  - Upload and retrieve test cases
  - Update test case status
  - Link test cases to requirements
  - Fetch test execution reports

### Watsonx Integration

- **Authentication**: API keys
- **Data Exchange**: REST API
- **Functionality**:
  - Submit prompts for scenario generation
  - Process LLM responses
  - Fine-tune outputs based on feedback
  - Leverage various models based on task requirements

### Email Service Integration

- **Protocol**: SMTP
- **Authentication**: Username/password or OAuth
- **Functionality**:
  - Send user notifications
  - Deliver test summary reports
  - Provide action links for quick response

## Technology Stack

Based on the defined technology stack requirements, the following components will be used for Phase 1:

### User Interface Layer

- **Frontend Framework**: 
  - Streamlit - Open-source Python library for creating web applications with minimal code
  - Deployment on IBM Cloud Kubernetes Service (ROKS)

- **UI Components**:
  - Python Streamlit Components - Custom and pre-built components to enhance UI functionality
  - Open-source with no additional licenses needed

- **Visualization**:
  - Plotly, Matplotlib - Python libraries for creating interactive data visualizations and charts

### Application Layer

- **Integration & Orchestration**:
  - FastAPI - Modern, high-performance web framework for building APIs with Python
  - Deployed on IBM Cloud Kubernetes Service (ROKS) Worker Nodes

- **LLM Test Scenario Generator**:
  - watsonx.ai with Llama LLM - High priority component accessing IBM watsonx.ai via IBM Cloud
  - Core AI functionality for test scenario generation

- **Test Case Manager**:
  - Python, pandas - Custom module for managing test case lifecycle
  - Standard Python libraries with no additional licensing

- **Coverage Analyzer**:
  - Python, NetworkX - Analyzes test coverage across requirements
  - Uses open-source NetworkX for relationship mapping

### Integration Services

- **JIRA Connector**:
  - JIRA REST API - High priority integration for requirement and defect management
  - Requires JIRA licenses with API access

- **SharePoint Connector**:
  - Microsoft Graph API - Medium priority for document management
  - Requires Microsoft 365 license with appropriate API permissions

- **Notification Service**:
  - SMTP, Microsoft Graph API - Medium priority for notification delivery
  - Uses standard SMTP for emails and Microsoft Graph for Teams notifications

### Data Layer

- **Relational Database**:
  - PostgreSQL on IBM Cloud - Medium priority managed database for structured data storage
  - Available as an IBM Cloud service (Databases for PostgreSQL)

- **Object Storage**:
  - IBM Cloud Object Storage / MinIO - High priority for storing test artifacts and large files
  - IBM Cloud service with various pricing tiers, starting with basic tier

- **Test Data Manager**:
  - Python, pandas, SQLAlchemy - Manages test data generation and preparation
  - Uses open-source Python libraries

### AI & Analytics

- **Core LLM**:
  - watsonx.ai with Llama LLM - High priority Large Language Model for test generation and analysis
  - Requires IBM watsonx.ai subscription with appropriate model access

- **Metrics Service**:
  - Python, pandas, NumPy - Collects and analyzes testing metrics
  - Uses standard open-source Python libraries

### DevOps & Infrastructure

- **Cloud Platform**:
  - IBM Cloud - High priority primary cloud platform hosting all services
  - Requires IBM Cloud account with appropriate subscription level

- **Container Management**:
  - IBM Cloud Kubernetes Service - High priority orchestration for containerized components
  - IBM Cloud service with various pricing tiers based on cluster size

- **CI/CD Pipeline**:
  - GitHub Actions - Handles automated building, testing, and deployment
  - Integrated with IBM Cloud DevSecOps (Tekton-Based Application Lifecycle)

- **Monitoring & Logging**:
  - IBM Cloud Monitoring - Medium priority for system monitoring and log aggregation
  - IBM Cloud Logs for centralized logging

- **API Management**:
  - IBM API Connect - High priority for managing, securing, and analyzing API usage
  - IBM Cloud service with tiered pricing

### Security

- **Authentication**:
  - IBM Cloud IAM - High priority for identity and access management
  - Included with IBM Cloud

- **Encryption**:
  - IBM Cloud Key Protect - High priority for managing encryption keys for sensitive data
  - IBM Cloud service with usage-based pricing

## Security Architecture

Security for the Watsonx for IPG Testing solution is built on IBM Cloud's enterprise-grade security services and best practices for secure application development.

### Authentication and Authorization

- **User Authentication**:
  - IBM Cloud IAM (Identity and Access Management) for authentication services
  - Integration with enterprise SSO via IBM Cloud IAM
  - Multi-factor authentication through IBM Cloud IAM for sensitive operations

- **API Security**:
  - IBM API Connect for API management and security
  - Rate limiting and throttling through IBM API Connect
  - Request signing and validation for secure integrations

- **Authorization**:
  - Role-based access control (RBAC) implemented through IBM Cloud IAM
  - Resource-level permissions managed through IBM Cloud IAM policies
  - Attribute-based access control for fine-grained permissions

### Data Protection

- **Data in Transit**:
  - TLS/SSL for all communications enforced at the IBM API Connect layer
  - API payloads encryption for sensitive data

- **Data at Rest**:
  - IBM Cloud Databases for PostgreSQL with encryption enabled
  - IBM Cloud Object Storage with encryption for file storage
  - IBM Cloud Key Protect for managing encryption keys

- **Sensitive Information Handling**:
  - Credential management through IBM Cloud Key Protect
  - PII data masking and redaction policies
  - Secure parameter handling in IBM Cloud services

### Security Monitoring and Compliance

- **Logging and Auditing**:
  - IBM Cloud Logs for comprehensive activity logging
  - IBM Cloud Activity Tracker for audit trails on sensitive operations
  - IBM Cloud Security Center for centralized security monitoring

- **Vulnerability Management**:
  - IBM Security Compliance Center for security posture management
  - Dependency vulnerability monitoring through IBM Cloud DevSecOps
  - Secure coding practices validated through automated code scanning

## Deployment Architecture

The Watsonx for IPG Testing solution is deployed on IBM Cloud infrastructure, leveraging IBM Cloud Kubernetes Service (ROKS) for container orchestration and various IBM Cloud services for supporting functionalities.

### Development Environment

- Containerized deployment with Docker on IBM Cloud Kubernetes Service (ROKS)
- Integration with IBM Cloud DevSecOps toolchain
- Mock services for external dependencies
- Development instance of IBM watsonx.ai for LLM capabilities

### Test Environment

- IBM Cloud Kubernetes Service (ROKS) deployment
- Integration with IBM Cloud DevSecOps pipeline
- Test data segregation with separate IBM Cloud Object Storage buckets
- Performance testing using IBM Cloud Monitoring

### Production Environment

- High-availability IBM Cloud Kubernetes Service (ROKS) deployment
- Autoscaling for workload fluctuations using IBM Cloud Kubernetes Service capabilities
- Disaster recovery leveraging IBM Cloud backup and recovery services
- Monitoring and alerting through IBM Cloud Monitoring

### Deployment Topology

```
┌───────────────────────────────────────────────────────────────┐
│                     IBM API Connect Gateway                   │
└─────────────────────────────────┬─────────────────────────────┘
                                   │
          ┌───────────────────────┴───────────────────────┐
          │          IBM Cloud Kubernetes Service         │
          │                                               │
┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│   Web UI Pods     │  │   API Pods        │  │   Worker Pods     │
│  (Streamlit)      │  │  (FastAPI)        │  │  (Background      │
│                   │  │                   │  │   Processing)      │
└─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
       ┌─────────────────────────┴─────────────────────────┐
       │                                                    │
┌──────▼───────┐  ┌──────▼───────┐  ┌───────▼────────┐  ┌──▼───────────┐
│ IBM Cloud    │  │ IBM Cloud    │  │ IBM watsonx.ai │  │ IBM Cloud    │
│ Databases for│  │ Object       │  │                │  │ Key Protect  │
│ PostgreSQL   │  │ Storage      │  │                │  │              │
└──────────────┘  └──────────────┘  └────────────────┘  └──────────────┘
```

## Phase 1 Limitations and Future Enhancements

### Current Limitations

1. **Manual Test Execution**: Phase 1 does not include automated test execution through RPA, which will be addressed in Phase 2.

2. **Limited AI Analysis of Failed Tests**: While test case generation leverages AI, detailed analysis of failed tests will be enhanced in future phases.

3. **Basic Reporting**: Initial reporting capabilities focus on essential metrics, with more advanced analytics planned for future phases.

4. **Integration Constraints**: Phase 1 focuses on primary integrations (JIRA, SharePoint, ALM), with additional integrations planned for future phases.

### Future Enhancements (Phase 2 and Beyond)

1. **RPA Integration**: Automated test execution using RPA tools like Automation Anywhere.

2. **Advanced Error Analysis**: AI-powered analysis of test failures to suggest potential root causes.

3. **Expanded Code Generation**: More sophisticated code generation for automated test scripts.

4. **Enhanced Analytics**: Advanced reporting and predictive analytics for test outcomes and quality metrics.

5. **Continuous Learning**: Feedback loops to improve scenario generation and test case quality over time.

## Conclusion

The Phase 1 architecture of the Watsonx for IPG Testing solution provides a solid foundation for AI-driven test case generation, comparison, and management. By leveraging watsonx's LLM capabilities, the system can intelligently convert business requirements into comprehensive test cases, streamlining the testing process and improving test coverage.

The modular design enables independent development and deployment of components, while the API-first approach ensures flexibility and extensibility. This architecture positions the system well for the Phase 2 expansion to include RPA-based test execution, creating a comprehensive end-to-end testing solution.

As the system evolves, the architecture will be refined based on user feedback, performance metrics, and changing business requirements, ensuring continuous improvement and alignment with organizational testing needs.