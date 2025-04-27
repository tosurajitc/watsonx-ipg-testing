import sys
import platform

def print_package_info(package_name):
    try:
        module = __import__(package_name)
        print(f"{package_name.capitalize()} Version: {module.__version__}")
    except (ImportError, AttributeError):
        print(f"{package_name.capitalize()}: Not installed or version not detected")

def verify_installations():
    print("Python Environment Verification")
    print("-------------------------------")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    print("\nPackage Versions:")
    
    # Core Dependencies
    print_package_info('python_dotenv')
    print_package_info('requests')
    print_package_info('yaml')
    
    # Data Manipulation
    print_package_info('pandas')
    print_package_info('numpy')
    print_package_info('sqlalchemy')
    
    # Frontend
    print_package_info('streamlit')
    
    # Visualization
    print_package_info('plotly')
    print_package_info('matplotlib')
    
    # API
    print_package_info('fastapi')
    print_package_info('uvicorn')
    
    # Logging
    print_package_info('loguru')
    
    # Database
    print_package_info('psycopg2')
    
    # Cloud Platform
    print_package_info('ibm_cloud_sdk_core')
    print_package_info('ibm_platform_services')
    
    # AI
    print_package_info('ibm_watsonx_ai')
    
    # JIRA
    print_package_info('jira')
    
    # PDF Processing
    print_package_info('PyPDF2')
    print_package_info('mammoth')
    
    # Validation
    print_package_info('pydantic')

if __name__ == '__main__':
    verify_installations()