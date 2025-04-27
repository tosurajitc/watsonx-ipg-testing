# Watsonx IPG Testing

An advanced Agentic AI solution for Intelligent Test Automation including RPA execution.

## Project Overview

This project implements an AI-powered solution for automated software testing and quality assurance. It leverages IBM Watsonx AI to generate, manage, and execute test cases, process test results, and provide intelligent insights into the testing process.

## Key Features

- AI-driven test case generation
- Automated test execution
- Intelligent defect analysis
- RPA (Robotic Process Automation) integration
- Comprehensive test result tracking

## CI/CD Pipeline

This project uses GitHub Actions for Continuous Integration and Continuous Deployment.

### Workflow Statuses

[![Continuous Integration](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/ci.yml)
[![Deploy to Development](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-dev.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-dev.yml)
[![Deploy to Test](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-test.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-test.yml)
[![Deploy to Production](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-prod.yml/badge.svg)](https://github.com/yourusername/watsonx-ipg-testing/actions/workflows/cd-prod.yml)

## Project Structure

```
watsonx-ipg-testing/
├── src/                    # Source code
│   ├── phase1/             # First phase modules
│   ├── phase2/             # Second phase modules
│   └── common/             # Shared utilities
├── tests/                  # Test suites
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── e2e/                # End-to-end tests
├── config/                 # Configuration files
├── docs/                   # Documentation
├── deployment/             # Deployment scripts
└── requirements/           # Dependency requirements
```

## Prerequisites

- Python 3.9+
- pip
- virtualenv

## Setup and Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/watsonx-ipg-testing.git
cd watsonx-ipg-testing
```

2. Create and activate a virtual environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies
```bash
# Install base requirements
pip install -r requirements/base.txt

# Install development requirements
pip install -r requirements/dev.txt
```

4. Configure environment
- Copy `.env.example` to `.env`
- Fill in your specific configurations (API keys, credentials)

## Running the Application

```bash
# Run main application
python src/main.py

# Run specific module
python -m src.phase1.some_module
```

## Testing

```bash
# Run all tests
pytest tests/

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run end-to-end tests
pytest tests/e2e/
```

## Branch Strategy

- `main`: Stable production code
- `develop`: Active development
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `release/*`: Release preparation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the [PROJECT LICENSE]. See `LICENSE` for more information.

## Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/watsonx-ipg-testing](https://github.com/yourusername/watsonx-ipg-testing)