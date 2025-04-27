# Developer Setup Guide

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Local Development Environment Setup](#local-development-environment-setup)
  - [Python Environment Setup](#python-environment-setup)
  - [Code Repository Setup](#code-repository-setup)
  - [Environment Variables](#environment-variables)
  - [Pre-commit Hooks](#pre-commit-hooks)
- [IBM Cloud Setup](#ibm-cloud-setup)
  - [IBM Cloud CLI Installation](#ibm-cloud-cli-installation)
  - [IBM Cloud Authentication](#ibm-cloud-authentication)
  - [IBM Cloud Kubernetes Service (ROKS) Setup](#ibm-cloud-kubernetes-service-roks-setup)
- [Database Setup](#database-setup)
  - [Local PostgreSQL Setup](#local-postgresql-setup)
  - [IBM Cloud Databases for PostgreSQL Configuration](#ibm-cloud-databases-for-postgresql-configuration)
- [IBM watsonx.ai Access](#ibm-watsonxai-access)
  - [API Key Creation](#api-key-creation)
  - [Testing watsonx.ai Connectivity](#testing-watsonxai-connectivity)
- [External Service Integration](#external-service-integration)
  - [JIRA Integration Setup](#jira-integration-setup)
  - [SharePoint Integration Setup](#sharepoint-integration-setup)
  - [ALM Integration Setup](#alm-integration-setup)
- [Running the Application Locally](#running-the-application-locally)
  - [Running the Backend API](#running-the-backend-api)
  - [Running the Streamlit UI](#running-the-streamlit-ui)
- [Running Tests](#running-tests)
- [Deployment Process](#deployment-process)
- [Troubleshooting](#troubleshooting)
- [Appendix: Additional Resources](#appendix-additional-resources)

## Introduction

This guide provides step-by-step instructions for setting up a development environment for the Watsonx for IPG Testing project. It covers both local development setup and configuration of IBM Cloud resources necessary for development and testing.

## Prerequisites

Before you begin, ensure you have the following:

- **Development Tools**:
  - Python 3.9 or higher
  - Git
  - Docker and Docker Compose
  - IDE of your choice (VS Code, PyCharm, etc.)
  - PostgreSQL client (optional for direct database access)
  
- **Access Credentials**:
  - IBM Cloud account with appropriate permissions
  - GitHub access to the project repository
  - JIRA API credentials (for integration development)
  - SharePoint API credentials (for integration development)
  - ALM API credentials (for integration development)

## Local Development Environment Setup

### Python Environment Setup

1. **Install Python 3.9+**:
   
   - **Ubuntu/Debian**:
     ```bash
     sudo apt update
     sudo apt install python3.9 python3.9-dev python3.9-venv python3-pip
     ```
   
   - **macOS** (using Homebrew):
     ```bash
     brew install python@3.9
     ```
   
   - **Windows**:
     Download and install from [python.org](https://www.python.org/downloads/)

2. **Create a Virtual Environment**:
   ```bash
   # Navigate to your project directory
   mkdir -p ~/projects/watsonx-ipg-testing
   cd ~/projects/watsonx-ipg-testing
   
   # Create virtual environment
   python3.9 -m venv venv
   
   # Activate the virtual environment
   # On Linux/macOS:
   source venv/bin/activate
   
   # On Windows:
   # venv\Scripts\activate
   ```

3. **Verify Python Version**:
   ```bash
   python --version
   # Should output Python 3.9.x
   ```

### Code Repository Setup

1. **Clone the Repository**:
   ```bash
   # Ensure you're in your projects directory and venv is activated
   git clone https://github.com/your-org/watsonx-ipg-testing.git .
   ```

2. **Install Development Dependencies**:
   ```bash
   pip install -r requirements/dev.txt
   ```

### Environment Variables

1. **Create Environment Variables File**:
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` File** with your specific configuration values:
   ```
   # Development Environment Settings
   ENVIRONMENT=development
   DEBUG=True
   
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ipg_testing_dev
   DB_USER=developer
   DB_PASSWORD=devpassword
   
   # IBM Cloud Configuration
   IBM_CLOUD_APIKEY=your_ibm_cloud_api_key
   IBM_CLOUD_REGION=us-south
   
   # watsonx.ai Configuration
   WATSONX_API_KEY=your_watsonx_api_key
   WATSONX_URL=https://us-south.ml.cloud.ibm.com/ml/v1-beta/generation/text
   WATSONX_MODEL=llama-2-70b-chat
   
   # Integration Settings
   JIRA_URL=https://your-jira-instance.atlassian.net
   JIRA_API_TOKEN=your_jira_api_token
   JIRA_USER_EMAIL=your_jira_email
   
   SHAREPOINT_CLIENT_ID=your_sharepoint_client_id
   SHAREPOINT_CLIENT_SECRET=your_sharepoint_client_secret
   SHAREPOINT_TENANT_ID=your_sharepoint_tenant_id
   SHAREPOINT_SITE_URL=https://your-company.sharepoint.com/sites/ipg-testing
   
   # Optional ALM Connection
   ALM_URL=https://your-alm-instance.com
   ALM_USERNAME=your_alm_username
   ALM_PASSWORD=your_alm_password
   ```

### Pre-commit Hooks

1. **Install Pre-commit**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Run Pre-commit on All Files** (first-time setup):
   ```bash
   pre-commit run --all-files
   ```

## IBM Cloud Setup

### IBM Cloud CLI Installation

1. **Install IBM Cloud CLI**:
   
   - **Linux/macOS**:
     ```bash
     curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
     ```
   
   - **macOS** (alternative method):
     ```bash
     brew install ibm-cloud-cli
     ```
   
   - **Windows**:
     Download and run the installer from [IBM Cloud CLI](https://cloud.ibm.com/docs/cli?topic=cli-install-ibmcloud-cli)

2. **Install Required Plugins**:
   ```bash
   ibmcloud plugin install kubernetes-service
   ibmcloud plugin install container-registry
   ibmcloud plugin install container-service
   ```

### IBM Cloud Authentication

1. **Log in to IBM Cloud**:
   ```bash
   ibmcloud login -a https://cloud.ibm.com
   ```
   
   If using an API key:
   ```bash
   ibmcloud login -a https://cloud.ibm.com --apikey YOUR_API_KEY
   ```

2. **Select Your Region and Resource Group**:
   ```bash
   ibmcloud target -r us-south -g your-resource-group
   ```

### IBM Cloud Kubernetes Service (ROKS) Setup

1. **Set Up Kubernetes Configuration**:
   ```bash
   # Get your cluster information
   ibmcloud ks clusters
   
   # Configure kubectl to use your cluster
   ibmcloud ks cluster config --cluster your-cluster-name
   
   # Verify connection
   kubectl get nodes
   ```

2. **Configure Container Registry Access**:
   ```bash
   # Log in to IBM Container Registry
   ibmcloud cr login
   
   # Create a namespace if needed
   ibmcloud cr namespace-add watsonx-ipg-testing
   ```

## Database Setup

### Local PostgreSQL Setup

1. **Install PostgreSQL** (if not using Docker):
   
   - **Ubuntu/Debian**:
     ```bash
     sudo apt update
     sudo apt install postgresql postgresql-contrib
     ```
   
   - **macOS**:
     ```bash
     brew install postgresql
     brew services start postgresql
     ```
   
   - **Windows**:
     Download and install from [PostgreSQL website](https://www.postgresql.org/download/windows/)

2. **Create Database and User**:
   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql
   
   # In PostgreSQL shell
   CREATE DATABASE ipg_testing_dev;
   CREATE USER developer WITH ENCRYPTED PASSWORD 'devpassword';
   GRANT ALL PRIVILEGES ON DATABASE ipg_testing_dev TO developer;
   \q
   ```

3. **Using Docker for PostgreSQL** (Alternative Approach):
   ```bash
   # Create a docker-compose.yml file with PostgreSQL configuration
   cat > docker-compose.local.yml << EOF
   version: '3.8'
   services:
     postgres:
       image: postgres:14
       environment:
         POSTGRES_DB: ipg_testing_dev
         POSTGRES_USER: developer
         POSTGRES_PASSWORD: devpassword
       ports:
         - "5432:5432"
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
   volumes:
     postgres_data:
   EOF
   
   # Start PostgreSQL container
   docker-compose -f docker-compose.local.yml up -d
   ```

### IBM Cloud Databases for PostgreSQL Configuration

1. **Create or Access PostgreSQL Instance**:
   - Navigate to IBM Cloud Console
   - Go to Databases → PostgreSQL
   - Create a new instance or select existing one
   - Note connection information

2. **Configure SSL Certificates** (if required):
   ```bash
   # Download certificate from IBM Cloud Console
   # Place in project's certs directory
   mkdir -p certs
   # Copy the downloaded certificate to the certs directory
   ```

3. **Update Environment Variables** for IBM Cloud Database:
   ```
   # IBM Cloud PostgreSQL (Production/Staging)
   # Uncomment and update these values when connecting to IBM Cloud DB
   # DB_HOST=your-postgresql-hostname.databases.appdomain.cloud
   # DB_PORT=30389  # Your specific port
   # DB_NAME=ibmclouddb
   # DB_USER=ibm_cloud_user
   # DB_PASSWORD=your_db_password
   # DB_CERT_PATH=./certs/postgresql.crt
   ```

## IBM watsonx.ai Access

### API Key Creation

1. **Generate API Key for watsonx.ai**:
   - Navigate to IBM Cloud Console
   - Go to Manage → Access (IAM) → API keys
   - Create a new API key with appropriate permissions for watsonx.ai
   - Save the API key securely

2. **Configure Project for watsonx.ai**:
   - Update the `.env` file with your watsonx.ai API key and URL
   - Set the preferred model name

### Testing watsonx.ai Connectivity

1. **Run the Connection Test Script**:
   ```bash
   # Activate your virtual environment if not already active
   source venv/bin/activate
   
   # Run the test script
   python scripts/test_watsonx_connection.py
   ```

2. **Expected Output**:
   ```
   Testing connection to watsonx.ai...
   Connection successful!
   Available models: ['llama-2-70b-chat', 'flan-ul2', ...]
   ```

## External Service Integration

### JIRA Integration Setup

1. **Generate JIRA API Token**:
   - Log in to your Atlassian account
   - Go to Account Settings → Security → Create and manage API tokens
   - Create a new API token and note it down

2. **Configure JIRA Integration**:
   - Update the `.env` file with your JIRA URL, email, and API token
   - Test connectivity with the JIRA test script:
     ```bash
     python scripts/test_jira_connection.py
     ```

### SharePoint Integration Setup

1. **Register Application in Azure AD**:
   - Go to Azure Portal → Azure Active Directory → App registrations
   - Register a new application
   - Set up required permissions for SharePoint
   - Note Client ID, Client Secret, and Tenant ID

2. **Configure SharePoint Integration**:
   - Update the `.env` file with your SharePoint credentials
   - Test connectivity:
     ```bash
     python scripts/test_sharepoint_connection.py
     ```

### ALM Integration Setup

1. **Obtain ALM API Credentials**:
   - Contact your ALM administrator for API access credentials
   - Note the ALM URL, username, and password or API key

2. **Configure ALM Integration**:
   - Update the `.env` file with ALM connection details
   - Test connectivity:
     ```bash
     python scripts/test_alm_connection.py
     ```

## Running the Application Locally

### Running the Backend API

1. **Start the API Server**:
   ```bash
   # Make sure you're in the project root directory with virtual environment activated
   python -m src.main
   ```
   
   The API will be available at: http://localhost:8000

2. **Access the API Documentation**:
   
   Open your browser and navigate to: http://localhost:8000/docs

### Running the Streamlit UI

1. **Start the Streamlit Application**:
   ```bash
   # In a new terminal, with virtual environment activated
   cd src/phase1/streamlit_ui
   streamlit run app.py
   ```
   
   The Streamlit UI will be available at: http://localhost:8501

## Running Tests

1. **Run All Tests**:
   ```bash
   pytest
   ```

2. **Run Tests with Coverage Report**:
   ```bash
   pytest --cov=src tests/
   ```

3. **Run Specific Test Modules**:
   ```bash
   # Run tests for a specific module
   pytest tests/unit/phase1/test_jira_connector.py
   
   # Run tests for a specific test class
   pytest tests/unit/phase1/test_jira_connector.py::TestJiraConnector
   
   # Run a specific test
   pytest tests/unit/phase1/test_jira_connector.py::TestJiraConnector::test_get_stories
   ```

## Deployment Process

1. **Local Development** → **CI/CD Pipeline** → **Test Environment** → **Production**

2. **Manual Deployment to IBM Cloud Kubernetes**:
   ```bash
   # Build container image
   docker build -t us.icr.io/watsonx-ipg-testing/app:latest .
   
   # Push to IBM Container Registry
   docker push us.icr.io/watsonx-ipg-testing/app:latest
   
   # Apply Kubernetes configuration
   kubectl apply -f deployment/kubernetes/
   ```

3. **Automated Deployment via CI/CD Pipeline**:
   - Push changes to the GitHub repository
   - GitHub Actions pipeline automatically builds and tests
   - On successful tests, deploys to test environment
   - Production deployment requires manual approval

## Troubleshooting

### Common Issues and Solutions

1. **Database Connection Issues**:
   - Check PostgreSQL service status: `sudo service postgresql status`
   - Verify environment variables in `.env`
   - Ensure firewall allows connection to database port

2. **IBM Cloud Connection Problems**:
   - Verify API key has correct permissions
   - Check for correct region configuration: `ibmcloud target`
   - Ensure VPN is connected if required by your network policies

3. **watsonx.ai API Errors**:
   - Verify API key is valid and not expired
   - Check quota limits for the watsonx.ai service
   - Ensure the model name is correct and available

4. **Integration Service Connectivity**:
   - Check network connectivity to external services
   - Verify API credentials in `.env`
   - Check for IP restrictions on external service APIs

5. **Container Build Issues**:
   - Clear Docker cache: `docker system prune -a`
   - Ensure Docker daemon is running
   - Check for disk space issues

### Getting Help

If you encounter issues not covered in this guide:

1. Check the project's internal documentation in the `docs/` directory
2. Review IBM Cloud documentation for service-specific issues
3. Contact the development team or DevOps support
4. Submit an issue in the project's GitHub repository

## Appendix: Additional Resources

### Documentation Links

- [Project Architecture Documentation](./architecture/overview.md)
- [API Documentation](./api/phase1_apis.md)
- [Coding Standards](./developer/coding_standards.md)
- [IBM Cloud Documentation](https://cloud.ibm.com/docs)
- [watsonx.ai Documentation](https://dataplatform.cloud.ibm.com/docs/content/wsj/analyze-data/fm-overview.html)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Useful Scripts

The project includes several utility scripts in the `scripts/` directory:

- `setup_dev_env.sh`: Automated setup of development environment
- `test_connections.py`: Test all external service connections
- `reset_local_db.py`: Reset the local development database
- `generate_test_data.py`: Generate sample test data for development

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run the dev environment setup script
./scripts/setup_dev_env.sh
```