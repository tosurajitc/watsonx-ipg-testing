# Watsonx IPG Testing

An agentic AI solution for Intelligent Test Automation including RPA execution.

## Project Overview

This project implements an AI-powered solution for automated software testing and quality assurance. It leverages Watson AI to generate, manage, and execute test cases, as well as process and analyze test results.

## CI/CD Pipeline

This project uses GitHub Actions for Continuous Integration and Continuous Deployment.

### Workflow Statuses

[![Continuous Integration](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/ci.yml)
[![Deploy to Development](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-dev.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-dev.yml)
[![Deploy to Test](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-test.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-test.yml)
[![Deploy to Production](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-prod.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-prod.yml)

### CI/CD Process

1. **Continuous Integration (CI)**: 
   - Triggered on pushes to `main` and `develop` branches and pull requests
   - Runs linting and all tests
   - Ensures code quality and functionality

2. **Continuous Deployment to Development**:
   - Triggered on pushes to the `develop` branch
   - Deploys the application to the development environment
   - Runs health checks after deployment

3. **Continuous Deployment to Test**:
   - Triggered on pushes to `release/*` branches
   - Deploys the application to the test environment
   - Runs end-to-end tests against the deployed application

4. **Continuous Deployment to Production**:
   - Triggered on pushes to the `main` branch and version tags
   - Requires manual approval
   - Deploys the application to the production environment
   - Includes automatic rollback on failure

## Branch Strategy

- `main`: Production code
- `develop`: Development code
- `feature/*`: Feature branches
- `release/*`: Release branches
- `hotfix/*`: Hotfix branches

## Getting Started

### Prerequisites

- Python 3.9+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/watsonx-ipg-testing.git

# Navigate to the project directory
cd watsonx-ipg-testing

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt
```

## Development

### Running Tests

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run end-to-end tests
pytest tests/e2e/
```

### Building Documentation

```bash
# Generate documentation
cd docs && make html
```

## Deployment

The application is deployed automatically through the CI/CD pipeline. However, you can also deploy manually:

```bash
# Deploy to development
./deployment/scripts/deploy.sh development

# Deploy to test
./deployment/scripts/deploy.sh test

# Deploy to production
./deployment/scripts/deploy.sh production
```

## Contributing

Please read [CONTRIBUTING.md](docs/developer/contributing.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the [LICENSE](LICENSE) file in the repository.