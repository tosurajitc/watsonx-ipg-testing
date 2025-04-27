#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
from setuptools import find_packages, setup

# Package meta-data
NAME = 'watsonx-ipg-testing'
DESCRIPTION = 'Agentic AI solution for IPG testing using watsonx.ai'
URL = 'https://github.com/your-org/watsonx-ipg-testing'
EMAIL = 'your-email@example.com'
AUTHOR = 'Your Organization'
REQUIRES_PYTHON = '>=3.9.0'
VERSION = '0.1.0'

# Required packages for production
REQUIRED = [
    # Web framework
    'fastapi>=0.95.0',
    'uvicorn>=0.22.0',
    'pydantic>=1.10.7',
    
    # UI
    'streamlit>=1.22.0',
    'plotly>=5.14.1',
    'matplotlib>=3.7.1',
    
    # Database
    'sqlalchemy>=2.0.12',
    'psycopg2-binary>=2.9.6',
    'alembic>=1.10.4',
    
    # API integrations
    'requests>=2.29.0',
    'aiohttp>=3.8.4',
    'python-jose>=3.3.0',
    'passlib>=1.7.4',
    
    # Data processing
    'pandas>=2.0.1',
    'numpy>=1.24.3',
    'networkx>=3.1',
    
    # File handling
    'python-multipart>=0.0.6',
    'openpyxl>=3.1.2',
    'python-docx>=0.8.11',
    'PyPDF2>=3.0.1',
    
    # IBM Cloud & watsonx.ai
    'ibm-cloud-sdk-core>=3.16.0',
    'ibm-watson>=6.1.0',
    'ibm-cos-sdk>=2.12.0',
    
    # JIRA integration
    'jira>=3.5.0',
    
    # SharePoint integration
    'msal>=1.22.0',
    'office365-rest-python-client>=2.4.0',
    
    # Utilities
    'python-dotenv>=1.0.0',
    'pyyaml>=6.0',
    'tenacity>=8.2.2',
]

# Development and testing requirements
EXTRAS = {
    'dev': [
        'black>=23.3.0',
        'flake8>=6.0.0',
        'isort>=5.12.0',
        'mypy>=1.3.0',
        'pre-commit>=3.3.1',
    ],
    'test': [
        'pytest>=7.3.1',
        'pytest-cov>=4.1.0',
        'pytest-mock>=3.10.0',
        'pytest-asyncio>=0.21.0',
        'freezegun>=1.2.2',
        'httpx>=0.24.0',  # For FastAPI testing
    ],
    'docs': [
        'sphinx>=7.0.0',
        'sphinx-rtd-theme>=1.2.0',
        'myst-parser>=2.0.0',
    ],
}

# Include all extras in 'all'
EXTRAS['all'] = [item for sublist in EXTRAS.values() for item in sublist]

# The rest of the setup code
here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
    with open(os.path.join(here, project_slug, '__version__.py')) as f:
        exec(f.read(), about)
else:
    about['__version__'] = VERSION

setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license='Proprietary',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    # $ setup.py publish support
    cmdclass={
        # 'upload': UploadCommand,
    },
    entry_points={
        'console_scripts': [
            'watsonx-ipg=src.cli:main',
        ],
    },
)